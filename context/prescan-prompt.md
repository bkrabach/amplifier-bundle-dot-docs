# Prescan Topic Selection

You are selecting investigation topics for a documentation run. Your goal is to identify 1–6 high-signal topics that, when investigated, will produce the most useful architectural documentation for this repository. Choose topics that illuminate how the system actually works, not just how it is organized.

## Repository Metadata

The following metadata was gathered by the previous step (structural prescan). Use it to inform your topic selection — directory layout, language breakdown, file counts, and any recognized entry points or configuration files are all available to you.

## Topic Selection Guidelines

Select topics that best illuminate the repository from these three documentation perspectives:

1. **Architecture perspective** — module boundaries, composition, key interfaces, wiring between components, and external integrations. Choose this when the codebase has distinct layers or service boundaries worth mapping.

2. **Execution flows perspective** — primary happy-path through the system, lifecycle events (startup, shutdown, error), and background tasks or scheduled work. Choose this when understanding how the system runs matters as much as how it is structured.

3. **State / Data models perspective** — key enums, data model schemas, and state machine transitions. Choose this when the system's behavior is governed by data shapes or explicit state transitions.

You do not need to cover all three perspectives — pick the topics that will produce the highest-value documentation for this particular repository.

## Output Format

Return a JSON array only. No markdown, no code fence, no explanation — just the raw JSON array.

Each object in the array must have exactly these fields:

- `name` — human-readable topic label (e.g., "Recipe Execution Flow")
- `slug` — kebab-case identifier used as directory name (e.g., "recipe-execution-flow")
- `rationale` — one sentence explaining why this topic is worth investigating

Example:

[
  {
    "name": "Recipe Execution Flow",
    "slug": "recipe-execution-flow",
    "rationale": "Understanding how recipes are parsed and dispatched is central to all agent orchestration in this system."
  }
]

## Calibration by Repo Complexity and Tier

Scale the number of topics to the repository's complexity and the requested investigation tier:

- **Tier 3 (PATCH)** — 1–2 topics. Focus only on the single most important mechanism.
- **Tier 2 (WAVE)** — 3–4 topics. Cover the primary architecture and one or two key flows.
- **Tier 1 (FULL)** — 4–6 topics. Provide broad coverage across architecture, execution, and state perspectives.

When in doubt, fewer higher-quality topics are better than many shallow ones.

Prefer mechanism-based topic names (e.g., "Bundle Composition", "Session Lifecycle") over directory names (e.g., "src/core", "lib/utils"). Mechanism names produce documentation that is useful regardless of how the codebase is reorganized.
