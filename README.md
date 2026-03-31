# DOT Docs

DOT Docs is an Amplifier bundle that generates DOT graph documentation of codebases using multi-agent [Parallax Discovery](https://github.com/bkrabach/amplifier-bundle-parallax-discovery) investigation. It produces structured, version-tracked architectural diagrams for a team knowledge base — automatically detecting what changed since the last run and investigating only what's needed.

## Features

- **Tier-based discovery** — classifies repos as FULL, WAVE, PATCH, or SKIP based on git history since the last run
- **Parallel agent investigation** — three specialist agents (code-tracer, behavior-observer, integration-mapper) examine each repo from different perspectives
- **Synthesis with quality gates** — a dot-author agent produces DOT graphs reviewed by a diagram-reviewer before acceptance
- **Provenance tracking** — every generated DOT file records the source commit SHA and generation timestamp
- **Content-hash deduplication** — skips writing unchanged DOT output even when the pipeline re-runs
- **Stale repo reconciliation** — detects orphaned output directories when repos are removed from a profile (never deletes — humans decide)

## Prerequisites

- [Amplifier CLI](https://github.com/microsoft/amplifier) installed
- The following bundles are included automatically via `bundle.md`:
  - [amplifier-foundation](https://github.com/microsoft/amplifier-foundation)
  - [amplifier-bundle-dot-graph](https://github.com/microsoft/amplifier-bundle-dot-graph)
  - [amplifier-bundle-parallax-discovery](https://github.com/bkrabach/amplifier-bundle-parallax-discovery)

## Installation

```bash
amplifier bundle add "git+https://github.com/bkrabach/amplifier-bundle-dot-docs@main#subdirectory=behaviors/dot-docs.yaml" --app
```

## Usage

1. **Create a profile** — define a `profile.yaml` listing the repos to document:

   ```yaml
   github_handle: your-handle
   repos:
     - name: my-service
     - name: my-library
   ```

2. **Clone repos** — ensure all listed repos are cloned under a single parent directory.

3. **Run discovery** — execute the discovery recipe with the three required context parameters:

   ```bash
   amplifier recipes execute recipes/dotfiles-discovery.yaml \
     --context '{
       "profile_path": "/path/to/profile.yaml",
       "dotfiles_root": "/path/to/dotfiles/output",
       "repos_root": "/path/to/repos"
     }'
   ```

## How It Works

The pipeline runs in three stages:

1. **Prescan** — reads the profile, determines each repo's investigation tier from git history, and runs a structural prescan for Tier 1/2 repos to select investigation topics.
2. **Investigate** — dispatches Parallax Discovery agents (code-tracer, behavior-observer, integration-mapper) in parallel. A lead-investigator reconciles their findings into a unified investigation report.
3. **Synthesize** — a dot-author agent produces DOT graph output from investigation findings. A diagram-reviewer quality gate validates the graph before acceptance. Content hashes are computed for deduplication, metadata is written, and stale repos are reconciled.

## Output Structure

```
<dotfiles_root>/<repo-name>/
  overview.dot              # Main architectural DOT graph
  .investigation/           # Raw investigation findings
    code-tracer.md
    behavior-observer.md
    integration-mapper.md
    reconciled.md
  .discovery/               # Pipeline metadata
    last-run.json           # Timestamp, tier, commit hash, status
    manifest.json           # Topics investigated, DOT files produced
    content-hash.txt        # SHA-256 of overview.dot for deduplication
```

## Usage Patterns

- **Team Sweep** (built) — run discovery across all repos in a team profile on a schedule or on-demand
- **Repo-Owner Hook** (future) — trigger discovery for a single repo on push via CI/CD webhook
- **User Sweep** (future) — personal variant scoped to an individual contributor's repos

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

---

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
