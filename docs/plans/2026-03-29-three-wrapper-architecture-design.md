# Three-Wrapper Architecture Design

## Goal

Define the architecture for three usage patterns of the dot-docs codebase documentation pipeline, all sharing the same core engine and writing to one parameterized target repo.

## Background

The `bkrabach/amplifier-bundle-dot-docs` pipeline is built and verified end-to-end. It runs multi-agent Parallax Discovery investigation on repos and synthesizes DOT graph documentation. The core engine (`dotfiles-investigate.yaml` → `dotfiles-synthesis.yaml`) takes one repo, produces one `overview.dot`.

This design extends it to support three triggering patterns — all writing to the same target repo. The design was validated by a four-expert panel:

- **Crusty Old Engineer (COE)** — skeptical architectural review
- **Zen Architect** — structural assessment
- **Recipe Author** — recipe plumbing feasibility
- **Foundation Expert** — bundle composition patterns

## Approach

One core engine, three wrappers, one target repo. The guiding principle is "same core, different wrappers" — maintain a single investigation and synthesis pipeline, and vary only the triggering mechanism. The target repo is always passed as a parameter, never hardcoded.

CI integration is deferred. The core engine and Team Sweep wrapper are built and working today.

## Architecture

### Core Engine (built and verified)

```
dotfiles-investigate.yaml → dotfiles-synthesis.yaml
```

**Input:** `repo_path`, `investigation_dir`, `tier`, `topics_hint`
**Output:** `overview.dot` (150–250 lines), `.investigation/` audit trail, `.discovery/last-run.json`

### Three Wrappers

All wrappers write to the same target repo, passed as a parameter.

**Parameters (all wrappers):**

- `target_repo` — the repo where dotfiles accumulate (passed as parameter, never hardcoded)
- `target_path` — subdirectory structure within target (default: `dotfiles/<owner>/<repo>/`)

| Pattern | Where it runs | Trigger | Input | What it does |
|---|---|---|---|---|
| **Team Sweep** (built) | From the target repo or a working directory | Manual or cron | `profile.yaml` listing repos | Loops over profile, detects tiers, runs core per repo, commits to target |
| **Repo-Owner Hook** (future) | GH Action in an individual source repo | Push to main (with path filters) | The repo itself | Runs core on self, commits overview.dot to target repo |
| **User Sweep** (future) | User's machine | Manual | GitHub handle | `gh repo list` → temp profile → clone missing → run Team Sweep |

### Wrapper Decomposition

```
Core engine (built):
  investigate.yaml + synthesis.yaml → one repo_path in, one overview.dot out

Three wrappers (same target repo, passed as parameter):
  1. Team Sweep (built)   — profile.yaml → loop → core per repo → commit to target
  2. Repo-Owner Hook      — GH Action in source repo → core on self → commit to target
  3. User Sweep           — gh repo list → temp profile → Team Sweep
```

The Repo-Owner Hook bypasses `dotfiles-discovery.yaml` entirely — it calls the core directly since it already knows which repo and doesn't need tier detection (something just changed).

## Components

### Core Engine Output (per repo)

Written to `<target_path>/<owner>/<repo>/`:

```
amplifier-bundle-ui-studio/
├── overview.dot              ← The polished output
├── .investigation/           ← Raw investigation artifacts (audit trail)
│   ├── wave-1/
│   │   ├── <topic-slug>/
│   │   │   ├── agent-1-code-tracer/
│   │   │   ├── agent-2-behavior-observer/
│   │   │   └── agent-3-integration-mapper/
│   │   └── ...
│   └── foreman-notes/
│       └── reconciliation.md
└── .discovery/
    ├── last-run.json         ← Commit hash for tier detection on next run
    └── manifest.json
```

### COE-Recommended Operational Fixes

Three changes to the core engine that apply regardless of which wrapper invokes it. These were recommended by the Crusty Old Engineer during expert panel review.

#### Provenance in DOT Output

Every generated `overview.dot` gets two graph-level attributes:

```dot
graph [source_sha="abc123def", generated_at="2026-03-29T14:00:00Z"]
```

Added by the `build-manifest` step (already a bash step with access to `git rev-parse HEAD`). Zero cost, answers "how fresh is this?" for anyone reading the docs.

#### Content-Hash Before Commit

Before writing results to the target repo, compute a hash of the DOT content (stripping the `generated_at` timestamp so only semantic content is compared). If the hash matches what's already committed, skip the write.

Rationale: Prevents spurious diffs when the pipeline re-runs on an unchanged repo and the LLM produces semantically equivalent but textually different output. Git history stays meaningful.

#### Stale Repo Reconciliation

The Team Sweep wrapper (and only that wrapper, since it owns the full profile) adds a final step: compare the repos in `profile.yaml` to the subdirectories in `dotfiles/<handle>/`. Any directory that has no corresponding profile entry gets flagged (not auto-deleted — just logged with a warning).

Handles repos that get renamed, archived, or removed from the profile. Deletion is a human decision.

## Data Flow

```
[profile.yaml / GH Action / gh repo list]
        │
        ▼
   ┌─────────┐
   │ Wrapper  │  (Team Sweep / Repo-Owner Hook / User Sweep)
   └────┬────┘
        │  repo_path, tier, topics_hint
        ▼
   ┌──────────────────┐
   │ Core Engine       │
   │  investigate.yaml │ → multi-agent Parallax Discovery
   │  synthesis.yaml   │ → DOT graph synthesis
   └────────┬─────────┘
            │  overview.dot + artifacts
            ▼
   ┌────────────────────┐
   │ Content-hash check  │  (skip write if unchanged)
   └────────┬───────────┘
            │
            ▼
   ┌─────────────────┐
   │ Target Repo      │  dotfiles/<owner>/<repo>/overview.dot
   │ (parameterized)  │
   └─────────────────┘
```

## Error Handling

- **Content-hash mismatch**: If the DOT output is semantically equivalent to what's already committed, the write is skipped silently. No error, no noise.
- **Stale repos**: Flagged with a warning log, never auto-deleted. Human reviews and decides.
- **Repo-Owner Hook thundering herd** (future): Mitigated by `repository_dispatch` — source repos fire events, target repo owns one workflow that processes them serially.

## Testing Strategy

The core engine is already tested end-to-end. The operational fixes (provenance, content-hash, reconciliation) will each need:

- **Provenance**: Assert `source_sha` and `generated_at` attributes exist in generated DOT output.
- **Content-hash**: Unit test that identical semantic content (with different timestamps) produces the same hash and skips the write.
- **Reconciliation**: Unit test that compares a profile against a directory listing and flags orphaned directories.

## Future Wrapper Notes (deferred from implementation)

### Repo-Owner Hook (GH Action)

When built, the GH Action template should:

- Live in `templates/github-actions/dotfiles-update.yml` within the dot-docs bundle (per foundation-expert recommendation)
- Use path filters on the trigger — don't regenerate docs on README typos or test-only changes
- Add concurrency group with `cancel-in-progress: true` per repo to avoid stacking runs
- Use a single PAT or GitHub App token (org secret) for write access to the target repo
- Commit directly to the target repo's main branch (no PRs)

Key COE concerns to address when building:

- **Thundering herd**: If 20 repos trigger simultaneously (shared dependency update), all try to commit to the same target. Mitigate with `repository_dispatch` — source repos fire events, target repo owns one workflow that processes them serially.
- **Cost control**: Centralize the LLM API key as an org-level secret. Consider a nightly schedule instead of push-triggered for most repos.
- **Opt-in model**: Require a `dot-docs: enabled` repo topic or label before the Action fires. Prevents accidental runs on repos that shouldn't be documented.

### User Sweep

When built:

- A thin script or recipe: `gh repo list <user> --limit 100` → filter by size/privacy → generate temp profile → clone missing repos → call `dotfiles-discovery.yaml`
- Live in `scripts/` within the dot-docs bundle
- Should have explicit flags: `--max-size-mb`, `--skip-private`, `--max-repos` (conservative defaults, opt-in to larger scope)
- If it grows into a proper CLI, promote to a `pyproject.toml` entry point

### CI Implementation Approach (when ready)

The recipe-author and foundation-expert disagreed on the approach. Two viable options documented for future decision:

**Option A: Amplifier CLI + recipes in CI with caching** — Same recipes run in CI as locally. Needs `uv tool install amplifier` + GH Actions cache for `~/.amplifier/cache/`. One codebase to maintain.

**Option B: Standalone Python script using SDK** — A `ci_pipeline.py` that uses `amplifier-core` directly, loads agent prompts from .md files. Simpler CI setup but two codepaths (recipes for interactive, SDK for CI).

Decision deferred until CI implementation is prioritized.

## Open Questions

1. **Where does the target repo live?** Passed as parameter — but does the team have a convention for the repo name/org? (e.g., `<org>/team-knowledge-base`, `<org>/dotfiles`, etc.)

2. **Should `.investigation/` artifacts go to the target repo?** They're large (399 files for ui-studio). The `overview.dot` is small. Options: commit only `overview.dot` + `.discovery/`, or commit everything. Size vs. audit trail tradeoff.

3. **Profile.yaml schema formalization** — Currently ad-hoc. Should there be a schema definition in the bundle for validation?

4. **Non-deterministic synthesis** — The COE flagged that same repo + SHA may produce different DOT output across runs. The content-hash check mitigates spurious diffs but doesn't solve the root non-determinism. Is this acceptable for documentation?
