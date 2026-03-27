# Investigation Recipe Design

## Goal

Complete the `bkrabach/amplifier-bundle-dot-docs` bundle so a developer can run it end-to-end to populate a team knowledge base with DOT graph documentation of their repositories.

## Background

The dot-docs pipeline currently jumps from prescan directly to synthesis with nothing to synthesize. The `investigate-repos` step is absent from `dotfiles-discovery.yaml`, `dotfiles-synthesis.yaml` has three agent steps missing their `agent:` fields, and `dotfiles-prescan.yaml` uses a heuristic bash scan with an explicit TODO requesting replacement. This design closes all three gaps in one coherent change set.

## Approach

A new `dotfiles-investigate.yaml` sub-recipe implements a **bespoke Documentation Wave**: the Parallax Discovery triplicate agents (code-tracer, behavior-observer, integration-mapper) run with documentation-focused prompting across all selected topics, followed by automated lead-investigator reconciliation. No approval gates inside the investigation. Tier-based depth control skips the last two waves for Tier 3 repos. This pattern was validated empirically during the design session.

## Architecture

The full pipeline becomes:

```
Read Profile → Detect Tiers → Prescan (upgraded)
  ↓ [Approval gate — review tier plan]
Investigate (new) → Synthesize (fixed) → Write Metadata
```

### New Files

| File | Purpose |
|------|---------|
| `recipes/dotfiles-investigate.yaml` | The bespoke Documentation Wave — three sequential parallel waves + lead investigator reconciliation |
| `context/prescan-prompt.md` | Guides the prescan agent to select topics toward three documentation perspectives |
| `context/dot-quality-standards.md` | One-line shim: `@dot-graph:skills/dot-quality`. Fixes broken @mention in synthesis-prompt.md |

### Changed Files

| File | Change |
|------|--------|
| `bundle.md` | Add parallax-discovery bundle include |
| `recipes/dotfiles-prescan.yaml` | Upgrade from heuristic bash to two-step (bash metadata + agent) |
| `recipes/dotfiles-discovery.yaml` | Add `investigate-repos` step; fix topics flow to synthesis |
| `recipes/dotfiles-synthesis.yaml` | Add `agent:` fields to three agent steps |
| `context/dot-docs-awareness.md` | Add one bullet for the new investigation recipe |
| Tests | Update existing tests; add `test_investigation_recipe.py` |

### Unchanged

Python tooling (`structural_change.py`, `dot_validation.py`, `discovery_metadata.py`), `behaviors/dot-docs.yaml`.

## Components

### `recipes/dotfiles-investigate.yaml`

A six-step sub-recipe. Called once per repo from `investigate-repos` in the discovery recipe.

**Input contract:** `repo_path`, `investigation_dir`, `topics_hint` (from prescan), `tier`  
**Output contract:** `investigation_manifest` (structured index) + populated `investigation_dir` (file-based, synthesis uses `find *.dot`)

**Step 1 — Prepare workspace (bash):** Creates `.investigation/wave-1/` and `foreman-notes/` subdirectories inside `investigation_dir`.

**Step 2 — Select topics (agent):** Reads repo metadata using `@dot-docs:context/prescan-prompt.md` as context. Returns 4–6 topics for Tier 1/2 or 1–2 topics for Tier 3 as a structured JSON array. Topics shaped toward architecture, execution flows, and state machines. No named agent required; a generic agent with prescan-prompt.md loaded is sufficient.

**Step 3 — Build topic paths (bash):** Enriches the topics list with pre-resolved directory paths for each agent. Pre-creates per-topic subdirectories (e.g. `{{slug}}/agent-1-code-tracer/`). Prevents agents from having to compute paths.

**Steps 4a, 4b, 4c — Three parallel waves:** Each is a `foreach` + `parallel: 3` loop across all topics:

| Step | Agent | Tier condition |
|------|-------|----------------|
| 4a | `parallax-discovery:code-tracer` | none — runs all tiers |
| 4b | `parallax-discovery:behavior-observer` | `"{{tier}} != '3'"` |
| 4c | `parallax-discovery:integration-mapper` | `"{{tier}} != '3'"` |

Each agent writes to its pre-created directory, uses `context_depth="none"` for genuine independence, and is prompted with a documentation focus ("produce a high-quality DOT diagram for documentation, not bug-hunting"). Required artifacts per agent: `findings.md`, `diagram.dot`, plus any role-specific files.

**Step 5 — Lead investigator reconciliation:** `parallax-discovery:lead-investigator` reads all agent outputs, identifies cross-cutting insights, notes the best diagram per topic, writes `foreman-notes/reconciliation.md`. Automated — no approval gate.

**Step 6 — Build manifest (bash):** Outputs `investigation_manifest` JSON: topic list with paths and reconciliation location. Both the structured manifest and `investigation_dir` are passed forward to synthesis.

**Expected timing:**

| Tier | Description | Estimated time/repo |
|------|-------------|---------------------|
| Tier 1 | Full — all three waves | 50–70 min |
| Tier 2 | Wave — all three waves, fewer topics | 25–35 min |
| Tier 3 | Patch — code-tracer only | 15–20 min |

### `context/prescan-prompt.md`

Guides the prescan agent to identify topics mapping to three documentation perspectives:

1. **Architecture** — module boundaries, composition, key interfaces
2. **Execution flows** — key runtime paths, lifecycle sequences
3. **State / Data models** — state machines, data schemas, key enumerations

Calibration by repo complexity:
- Simple repo (e.g. amplifier-bundle-modes, 2 modules): ~3 topics, one per perspective
- Complex system (e.g. amplifier-resolve, 27K LOC): 4–6 topics covering the most important concerns

### `context/dot-quality-standards.md`

Single-line file:

```
@dot-graph:skills/dot-quality
```

Fixes the broken `@mention` in `synthesis-prompt.md` at line 101. The dot-graph bundle is already included in `bundle.md`, so this resolves correctly.

## Data Flow

```
prescan (bash)
  → scan_metadata (JSON)
    → prescan agent (prescan-prompt.md)
      → topics_hint [{name, slug, rationale}]
        → investigate-repos foreach
          → per-repo: dotfiles-investigate.yaml
            → code-tracer wave (all topics, parallel)
            → behavior-observer wave (tier 1/2, parallel)
            → integration-mapper wave (tier 1/2, parallel)
            → lead-investigator (reconciliation.md)
            → investigation_manifest {topics + paths}
              → dotfiles-synthesis.yaml
                → dot-author synthesizes DOT diagram
                  → diagram-reviewer quality check (max 3 retries)
                    → write metadata
```

The `topics` field in `run-synthesis` context is fixed to read from `{{investigation_result.investigation_manifest.topics}}` — this was previously broken, receiving an empty list.

## Error Handling

**Guiding principle:** Partial results are better than a full abort. One bad repo should not kill the rest.

**Repo level:** `investigate-repos` uses `on_error: continue`. Failed repos are skipped in synthesis; their metadata entries get `status: "error"`.

**Agent level:** If one topic's agent fails partway through a foreach wave, the schema collects what completed and continues. Subsequent waves still run for successful topics. Lead investigator is instructed to work with available artifacts and note any gaps.

**Synthesis level:** The existing `quality-review → fix-if-failed` loop handles reviewer FAIL verdicts (max 3 iterations). After 3 retries the step writes whatever it has and continues — a partial diagram is better than nothing. The `validate-output` bash step reports what was produced without aborting.

**Per-step timeouts:**

| Step | Timeout |
|------|---------|
| Topic selection agent | 600s |
| Each triplicate foreach loop (4a / 4b / 4c) | 1800s (30 min) |
| Lead investigator | 2400s (40 min) |
| Synthesis | 1800s |
| Diagram reviewer | 600s |

**Not handled:** If the parallax-discovery bundle fails to load (e.g. network error), the run fails. Bundle availability is a pre-flight concern, not runtime.

## Testing Strategy

**Existing Python tooling unit tests (173 tests):** No changes. Tooling modules are already well-covered and no new Python code is being added.

**Updated recipe structure tests:**

- `tests/test_discovery_recipe.py` — add tests:
  - `investigate-repos` step exists with correct structure
  - Tier-based conditions are present
  - `investigation_manifest` is correctly passed through to synthesis

- `tests/test_synthesis_artifacts.py` — add tests:
  - `synthesize` step has `agent: "dot-graph:dot-author"`
  - `quality-review` step has `agent: "dot-graph:diagram-reviewer"`
  - `fix-if-failed` step has `agent: "dot-graph:dot-author"`

**New recipe structure tests — `tests/test_investigation_recipe.py`:**

- Recipe loads and validates cleanly
- Has exactly 6 steps in correct order
- Code-tracer loop has no tier condition
- Behavior-observer and integration-mapper loops have `{{tier}} != '3'` condition
- All three agent loops use `parallel: 3` (not `true`)
- Lead investigator step produces a `reconciliation` output
- Manifest step produces `investigation_manifest` with correct fields

**Out of scope:** End-to-end execution with real agents. That is the developer's integration test when they first run it. The test suite validates structure and wiring, not AI agent behavior.

## Open Questions

1. **Bundle org for parallax-discovery:** Does it live at `github.com/microsoft/amplifier-bundle-parallax-discovery` or `github.com/bkrabach/amplifier-bundle-parallax-discovery`? The amplifier-expert found it cached from `bkrabach/` but MODULES.md may list a different org. Verify before wiring `bundle.md`.

2. **Prescan agent step without a named agent:** The topic-selection step in the investigation recipe does not need a named agent — generic reasoning is sufficient. Verify that the recipe engine allows an agent step without an `agent:` field, or assign `foundation:explorer` as a fallback if a name is required.

3. **`tier3-analysis` step missing `agent:` field:** This step in `dotfiles-discovery.yaml` Stage 3 (runs quality checks for Tier 3 repos — orphan node check, cycle detection, diff) also lacks an `agent:` field. Assign `dot-graph:dot-author` or `self` before the overall fix is complete.
