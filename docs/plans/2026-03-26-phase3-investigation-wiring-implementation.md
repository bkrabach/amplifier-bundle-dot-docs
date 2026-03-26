# Phase 3: Investigation Recipe + Discovery Wiring — Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Create `recipes/dotfiles-investigate.yaml` (the bespoke Documentation Wave recipe with six steps), write full test coverage for it, wire it into `dotfiles-discovery.yaml` by adding the `investigate-repos` step, fix the broken `topics` flow to synthesis, and add the missing `agent:` field to the `tier3-analysis` step.

**Architecture:** The `dotfiles-investigate.yaml` recipe is a self-contained sub-recipe called once per active repo. It runs three sequential parallel waves of Parallax Discovery agents (code-tracer, behavior-observer, integration-mapper) across all selected topics, then runs lead-investigator reconciliation, then emits an `investigation_manifest` JSON blob for downstream synthesis to consume. Tier 3 repos skip behavior-observer and integration-mapper (code-tracer only). The discovery recipe calls this recipe in a new `investigate-repos` foreach step between prescan and the approval gate.

**Tech Stack:** Python, pytest, YAML (PyYAML), git

**Prerequisites:** Phase 1 and Phase 2 must be complete. Specifically:
- `bundle.md` must include `parallax-discovery` (Phase 1)
- `context/prescan-prompt.md` must exist (Phase 2)
- `recipes/dotfiles-prescan.yaml` must be the upgraded 2-step version (Phase 2)

**Working directory for all commands:** `/home/bkrabach/dev/dot-docs/dot-docs/`

---

## Orientation

Before starting, read these files:

- `recipes/dotfiles-discovery.yaml` — pay attention to:
  - Stage 2 `investigation` steps: `process-repos` and `prescan-repos` (you will add `investigate-repos` after `prescan-repos`, before the `approval:` block)
  - Stage 3 `synthesis` step `run-synthesis` context: `topics: "{{repo_entry.topics}}"` — this is broken and must be fixed to `topics: "{{investigation_results}}"`
  - Stage 3 step `tier3-analysis` — it has `type: "agent"` but no `agent:` field
- `tests/test_discovery_recipe.py` — existing test classes; you will add new classes after them
- `tests/test_investigation_recipe.py` — does **not exist yet**; you will create it

**Key recipe engine facts:**
- `foreach` steps that have `collect: "name"` gather their results into an array named `name`
- An agent step inside a `foreach` block uses `agent: "namespace:agentname"` to specify which agent runs
- `on_error: continue` means a single loop iteration failure does not abort the whole foreach
- The `parallel: 3` setting means up to 3 iterations run concurrently
- `condition:` on a foreach step means the entire step is skipped if the condition is false at the time the step starts

**Open question note:** The `select-topics` step in the investigate recipe uses `type: "agent"` without an `agent:` field. The design says a generic agent is sufficient. If the recipe engine requires an explicit `agent:` field on all agent steps, add `agent: "foundation:explorer"` as a fallback. The tests do NOT assert the `agent:` field for `select-topics` — only for the three parallax wave steps and the lead-investigator step.

---

## Task 1: Create test file for investigation recipe (RED)

**Files:**
- Create: `tests/test_investigation_recipe.py`

**Step 1: Create the file**

Create `tests/test_investigation_recipe.py` with the following content:

```python
"""Tests for the dotfiles-investigate.yaml recipe structure.

RED phase: Written before the recipe file exists.
Verifies structure, step order, agent assignments, conditions, and output contracts.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

BUNDLE_ROOT = Path(__file__).parent.parent


class TestInvestigationRecipeExists:
    """Verify the recipe file exists and has correct top-level metadata."""

    @pytest.fixture
    def recipe_path(self) -> Path:
        return BUNDLE_ROOT / "recipes" / "dotfiles-investigate.yaml"

    @pytest.fixture
    def recipe_data(self, recipe_path: Path) -> dict:
        return yaml.safe_load(recipe_path.read_text())

    def test_file_exists(self, recipe_path: Path) -> None:
        assert recipe_path.exists(), (
            f"dotfiles-investigate.yaml not found at {recipe_path}"
        )

    def test_valid_yaml(self, recipe_path: Path) -> None:
        data = yaml.safe_load(recipe_path.read_text())
        assert data is not None, "dotfiles-investigate.yaml is empty or null"

    def test_recipe_name(self, recipe_data: dict) -> None:
        assert recipe_data.get("name") == "dotfiles-investigate", (
            f"recipe name must be 'dotfiles-investigate', got: {recipe_data.get('name')!r}"
        )

    def test_has_required_context_repo_path(self, recipe_data: dict) -> None:
        ctx = recipe_data.get("context", {})
        assert "repo_path" in ctx, "context must include repo_path"

    def test_has_required_context_investigation_dir(self, recipe_data: dict) -> None:
        ctx = recipe_data.get("context", {})
        assert "investigation_dir" in ctx, "context must include investigation_dir"

    def test_has_required_context_tier(self, recipe_data: dict) -> None:
        ctx = recipe_data.get("context", {})
        assert "tier" in ctx, "context must include tier"


class TestInvestigationRecipeSteps:
    """Verify the 6-step structure, step order, agents, and conditions."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        path = BUNDLE_ROOT / "recipes" / "dotfiles-investigate.yaml"
        return yaml.safe_load(path.read_text())

    def _get_all_steps(self, recipe_data: dict) -> list:
        steps = list(recipe_data.get("steps", []))
        for stage in recipe_data.get("stages", []):
            steps.extend(stage.get("steps", []))
        return steps

    def _get_step(self, recipe_data: dict, step_id: str) -> dict:
        return next(
            (s for s in self._get_all_steps(recipe_data) if s.get("id") == step_id),
            {}
        )

    def _step_index(self, recipe_data: dict, step_id: str) -> int:
        ids = [s.get("id") for s in self._get_all_steps(recipe_data)]
        try:
            return ids.index(step_id)
        except ValueError:
            return -1

    # --- Step existence ---

    def test_has_prepare_workspace_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "prepare-workspace")
        assert step, "must have step id: prepare-workspace"
        assert step.get("type") == "bash", "prepare-workspace must be type: bash"

    def test_has_select_topics_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "select-topics")
        assert step, "must have step id: select-topics"
        assert step.get("type") == "agent", "select-topics must be type: agent"
        assert step.get("parse_json") is True, "select-topics must have parse_json: true"
        assert step.get("output"), "select-topics must have an output field"

    def test_has_build_topic_paths_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "build-topic-paths")
        assert step, "must have step id: build-topic-paths"
        assert step.get("type") == "bash", "build-topic-paths must be type: bash"
        assert step.get("parse_json") is True, "build-topic-paths must have parse_json: true"

    def test_has_wave1_code_tracers_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-code-tracers")
        assert step, "must have step id: wave1-code-tracers"

    def test_has_wave1_behavior_observers_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-behavior-observers")
        assert step, "must have step id: wave1-behavior-observers"

    def test_has_wave1_integration_mappers_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-integration-mappers")
        assert step, "must have step id: wave1-integration-mappers"

    def test_has_lead_investigator_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "lead-investigator")
        assert step, "must have step id: lead-investigator"

    def test_has_build_manifest_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "build-manifest")
        assert step, "must have step id: build-manifest"
        assert step.get("type") == "bash", "build-manifest must be type: bash"
        assert step.get("parse_json") is True, "build-manifest must have parse_json: true"

    # --- Step order ---

    def test_prepare_workspace_comes_first(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "prepare-workspace") == 0, (
            "prepare-workspace must be the first step"
        )

    def test_select_topics_before_build_topic_paths(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "select-topics") < \
               self._step_index(recipe_data, "build-topic-paths"), (
            "select-topics must come before build-topic-paths"
        )

    def test_build_topic_paths_before_code_tracers(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "build-topic-paths") < \
               self._step_index(recipe_data, "wave1-code-tracers"), (
            "build-topic-paths must come before wave1-code-tracers"
        )

    def test_code_tracers_before_lead_investigator(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "wave1-code-tracers") < \
               self._step_index(recipe_data, "lead-investigator"), (
            "wave1-code-tracers must come before lead-investigator"
        )

    def test_lead_investigator_before_build_manifest(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "lead-investigator") < \
               self._step_index(recipe_data, "build-manifest"), (
            "lead-investigator must come before build-manifest"
        )

    # --- Agent assignments ---

    def test_code_tracers_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-code-tracers")
        assert step.get("agent") == "parallax-discovery:code-tracer", (
            f"wave1-code-tracers must have agent: parallax-discovery:code-tracer, "
            f"got: {step.get('agent')!r}"
        )

    def test_behavior_observers_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-behavior-observers")
        assert step.get("agent") == "parallax-discovery:behavior-observer", (
            f"wave1-behavior-observers must have agent: parallax-discovery:behavior-observer, "
            f"got: {step.get('agent')!r}"
        )

    def test_integration_mappers_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-integration-mappers")
        assert step.get("agent") == "parallax-discovery:integration-mapper", (
            f"wave1-integration-mappers must have agent: parallax-discovery:integration-mapper, "
            f"got: {step.get('agent')!r}"
        )

    def test_lead_investigator_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "lead-investigator")
        assert step.get("agent") == "parallax-discovery:lead-investigator", (
            f"lead-investigator must have agent: parallax-discovery:lead-investigator, "
            f"got: {step.get('agent')!r}"
        )

    # --- Parallel settings ---

    def test_code_tracers_parallel_3(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-code-tracers")
        assert step.get("parallel") == 3, (
            f"wave1-code-tracers must have parallel: 3, got: {step.get('parallel')!r}"
        )

    def test_behavior_observers_parallel_3(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-behavior-observers")
        assert step.get("parallel") == 3, (
            f"wave1-behavior-observers must have parallel: 3, got: {step.get('parallel')!r}"
        )

    def test_integration_mappers_parallel_3(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-integration-mappers")
        assert step.get("parallel") == 3, (
            f"wave1-integration-mappers must have parallel: 3, got: {step.get('parallel')!r}"
        )

    # --- Tier conditions ---

    def test_code_tracers_has_no_tier_condition(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-code-tracers")
        assert "condition" not in step, (
            "wave1-code-tracers must NOT have a condition — it runs for ALL tiers"
        )

    def test_behavior_observers_has_tier3_condition(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-behavior-observers")
        condition = step.get("condition", "")
        assert condition, "wave1-behavior-observers must have a condition (skip Tier 3)"
        assert "3" in condition, (
            f"wave1-behavior-observers condition must reference tier 3, got: {condition!r}"
        )

    def test_integration_mappers_has_tier3_condition(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-integration-mappers")
        condition = step.get("condition", "")
        assert condition, "wave1-integration-mappers must have a condition (skip Tier 3)"
        assert "3" in condition, (
            f"wave1-integration-mappers condition must reference tier 3, got: {condition!r}"
        )

    # --- Output contracts ---

    def test_lead_investigator_has_reconciliation_output(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "lead-investigator")
        assert step.get("output") == "reconciliation", (
            f"lead-investigator must have output: reconciliation, got: {step.get('output')!r}"
        )

    def test_build_manifest_has_investigation_manifest_output(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "build-manifest")
        assert step.get("output") == "investigation_manifest", (
            f"build-manifest must have output: investigation_manifest, "
            f"got: {step.get('output')!r}"
        )
```

**Step 2: Run the tests to verify they fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_investigation_recipe.py -v
```

Expected output: **FAILED** — first failure is `dotfiles-investigate.yaml not found`

---

## Task 2: Create dotfiles-investigate.yaml (GREEN)

**Files:**
- Create: `recipes/dotfiles-investigate.yaml`

**Step 1: Create the file**

Create `recipes/dotfiles-investigate.yaml` with the following content:

```yaml
name: "dotfiles-investigate"
description: >
  Bespoke Documentation Wave investigation for a single repository.
  Dispatches Parallax Discovery triplicate agents (code-tracer,
  behavior-observer, integration-mapper) per topic, then runs
  lead-investigator reconciliation. Tier 3 skips behavior-observer
  and integration-mapper (code-tracer only).
version: "1.0.0"
tags: [dotfiles, investigation, parallax, documentation]

# Investigation Recipe
#
# Input contract:
#   repo_path        — required: absolute path to the repository on disk
#   investigation_dir — required: root for all investigation artifacts
#   topics_hint      — optional: topic objects from prescan [{name, slug, rationale}]
#   tier             — required: "1"=FULL, "2"=WAVE, "3"=PATCH
#
# Output contract:
#   investigation_manifest — JSON blob with:
#     { investigation_dir, tier, topics, reconciliation, wave1_dir }
#   Populated investigation_dir (synthesis uses find *.dot)
#
# Steps:
#   1. prepare-workspace     — create investigation directory tree (bash)
#   2. select-topics         — agent selects 1-6 topics (agent)
#   3. build-topic-paths     — enrich topics with pre-resolved dir paths (bash)
#   4a. wave1-code-tracers   — HOW: code-tracer per topic (parallax agent, all tiers)
#   4b. wave1-behavior-observers — WHAT: behavior-observer per topic (Tier 1+2 only)
#   4c. wave1-integration-mappers — WHERE/WHY: integration-mapper per topic (Tier 1+2 only)
#   5. lead-investigator     — reconciliation across all agent outputs (parallax agent)
#   6. build-manifest        — emit investigation_manifest JSON (bash)

context:
  repo_path: ""           # required — absolute path to the repository
  investigation_dir: ""   # required — root for all investigation artifacts
  topics_hint: []         # optional — topic objects from prescan
  tier: "1"               # required — 1=FULL, 2=WAVE, 3=PATCH

steps:
  # --------------------------------------------------------------------------
  # Step 1: Prepare investigation workspace
  # Creates the directory tree before any agents write to it.
  # --------------------------------------------------------------------------
  - id: "prepare-workspace"
    type: "bash"
    timeout: 15
    command: |
      mkdir -p "{{investigation_dir}}/wave-1"
      mkdir -p "{{investigation_dir}}/foreman-notes"
      echo "Workspace ready: {{investigation_dir}}"

  # --------------------------------------------------------------------------
  # Step 2: Select topics (agent-driven, documentation-shaped)
  # Uses prescan-prompt.md to select topics toward the three documentation
  # perspectives. Returns a JSON array of {name, slug, rationale} objects.
  # --------------------------------------------------------------------------
  - id: "select-topics"
    type: "agent"
    output: "topics"
    parse_json: true
    timeout: 600
    prompt: |
      @dot-docs:context/prescan-prompt.md

      ## Investigation Context

      Repository: {{repo_path}}
      Topics hint from prescan: {{topics_hint}}
      Tier: {{tier}}

      Select topics shaped toward the three documentation perspectives:
      architecture, execution flows, and state/data models.

      Follow the tier calibration in the guidelines above.
      Return ONLY the JSON array — no markdown, no code fence.

  # --------------------------------------------------------------------------
  # Step 3: Build per-topic paths and pre-create directories
  # Enriches each topic object with resolved directory paths.
  # Agents use these pre-resolved paths — no path computation needed.
  # --------------------------------------------------------------------------
  - id: "build-topic-paths"
    type: "bash"
    output: "topics_with_paths"
    parse_json: true
    timeout: 30
    command: |
      python3 << 'EOF'
      import json
      import os

      topics_raw = '''{{topics}}'''
      try:
          topics = json.loads(topics_raw)
      except Exception:
          import ast
          topics = ast.literal_eval(topics_raw)

      inv = "{{investigation_dir}}/wave-1"
      result = []

      for t in topics:
          slug = t.get("slug", t.get("name", "unknown").lower().replace(" ", "-"))
          base = inv + "/" + slug
          code_tracer_dir   = base + "/agent-1-code-tracer"
          behavior_dir      = base + "/agent-2-behavior-observer"
          integration_dir   = base + "/agent-3-integration-mapper"

          os.makedirs(code_tracer_dir, exist_ok=True)
          os.makedirs(behavior_dir, exist_ok=True)
          os.makedirs(integration_dir, exist_ok=True)

          result.append({
              **t,
              "slug":             slug,
              "team_dir":         base,
              "code_tracer_dir":  code_tracer_dir,
              "behavior_dir":     behavior_dir,
              "integration_dir":  integration_dir,
          })

      print(json.dumps(result))
      EOF

  # --------------------------------------------------------------------------
  # Step 4a: Code Tracers — HOW (all tiers, all topics in parallel)
  # Traces actual execution paths. Cites exact file:line for every claim.
  # Runs for ALL tiers — even Tier 3 (PATCH) gets a code-tracer pass.
  # --------------------------------------------------------------------------
  - id: "wave1-code-tracers"
    foreach: "{{topics_with_paths}}"
    as: "topic"
    parallel: 3
    collect: "trace_results"
    agent: "parallax-discovery:code-tracer"
    timeout: 1800
    prompt: |
      You are Agent 1 (Code Tracer) for a documentation investigation.

      Topic: {{topic.name}}
      Repository: {{repo_path}}
      Write ALL output files to: {{topic.code_tracer_dir}}/

      Your role: HOW does this actually work in the code?

      Trace actual execution paths using LSP (goToDefinition, findReferences, hover)
      for precise navigation. Cite exact file:line for every claim you make.

      DOCUMENTATION FOCUS: Produce a high-quality DOT diagram suitable for a team
      knowledge base. Prioritize clarity and accuracy — this is documentation, not
      a bug investigation.

      Required output files (write each to {{topic.code_tracer_dir}}/):
        findings.md   — narrative analysis with file:line citations
        evidence.md   — structured citation table (file | line | claim)
        diagram.dot   — GraphViz diagram (150-200 lines, rendered legend, cluster subgraphs)
        unknowns.md   — what you could not determine and why

      Use context_depth="none". Investigate from primary sources only.

  # --------------------------------------------------------------------------
  # Step 4b: Behavior Observers — WHAT (Tier 1 and 2 only)
  # Examines actual instances. Catalogs structure and quantifies patterns.
  # SKIPPED for Tier 3 (PATCH) — condition prevents execution.
  # --------------------------------------------------------------------------
  - id: "wave1-behavior-observers"
    condition: "{{tier}} != '3'"
    foreach: "{{topics_with_paths}}"
    as: "topic"
    parallel: 3
    collect: "behavior_results"
    agent: "parallax-discovery:behavior-observer"
    timeout: 1800
    prompt: |
      You are Agent 2 (Behavior Observer) for a documentation investigation.

      Topic: {{topic.name}}
      Repository: {{repo_path}}
      Write ALL output files to: {{topic.behavior_dir}}/

      Your role: WHAT does this look like in practice?

      Examine 10+ real instances. Catalog structure and quantify patterns.
      Look at what actually exists — not what documentation claims should exist.

      DOCUMENTATION FOCUS: Produce a high-quality DOT diagram for the team knowledge
      base. Surface the dominant patterns clearly.

      Required output files (write each to {{topic.behavior_dir}}/):
        findings.md   — narrative analysis
        catalog.md    — structured inventory (10+ instances examined)
        patterns.md   — cross-cutting patterns with frequencies
        diagram.dot   — GraphViz diagram (rendered legend, cluster subgraphs)
        unknowns.md   — what you could not determine

      Use context_depth="none". Investigate from primary sources only.

  # --------------------------------------------------------------------------
  # Step 4c: Integration Mappers — WHERE/WHY (Tier 1 and 2 only)
  # Maps cross-boundary connections. Asks: how does this compose architecturally?
  # SKIPPED for Tier 3 (PATCH) — condition prevents execution.
  # --------------------------------------------------------------------------
  - id: "wave1-integration-mappers"
    condition: "{{tier}} != '3'"
    foreach: "{{topics_with_paths}}"
    as: "topic"
    parallel: 3
    collect: "integration_results"
    agent: "parallax-discovery:integration-mapper"
    timeout: 1800
    prompt: |
      You are Agent 3 (Integration Mapper) for a documentation investigation.

      Topic: {{topic.name}}
      Repository: {{repo_path}}
      Write ALL output files to: {{topic.integration_dir}}/

      Your role: WHERE do things connect, and WHY does that matter architecturally?

      Map how mechanisms integrate across component boundaries. Ask: "How does this
      compose with every other mechanism?" Look at the spaces between mechanisms.

      DOCUMENTATION FOCUS: Produce a high-quality DOT diagram capturing the
      cross-boundary integration for the team knowledge base.

      Required output files (write each to {{topic.integration_dir}}/):
        integration-map.md  — cross-boundary analysis (primary deliverable)
        diagram.dot         — GraphViz integration diagram
        unknowns.md         — unresolved cross-boundary questions

      Use context_depth="none". Investigate from primary sources only.

  # --------------------------------------------------------------------------
  # Step 5: Lead Investigator reconciliation
  # Reads ALL agent artifacts from Wave 1 and identifies cross-cutting insights,
  # discrepancies between agents, and the best diagram per topic.
  # --------------------------------------------------------------------------
  - id: "lead-investigator"
    agent: "parallax-discovery:lead-investigator"
    output: "reconciliation"
    timeout: 2400
    prompt: |
      You are the Lead Investigator. Read ALL agent artifacts from Wave 1.

      Investigation workspace: {{investigation_dir}}/wave-1/
      Topics investigated: {{topics_with_paths}}
      Write your output to: {{investigation_dir}}/foreman-notes/reconciliation.md

      For each topic, read all available agents' findings.md and diagram.dot files.
      (Behavior observer and integration mapper may be absent for Tier 3 repos — that
      is expected. Work with what is available.)

      Identify:
      1. Cross-cutting insights that emerge from comparing perspectives
      2. Discrepancies between agents (track as D-01, D-02, etc.)
      3. Which agent's diagram.dot is the BEST representation for each topic
      4. Convergent findings (multiple agents agree — high confidence)

      DO NOT resolve discrepancies by picking the "more plausible" answer. Track
      every discrepancy with its ID. Reconciliation is synthesis, not arbitration.

      Write reconciliation.md with these exact sections:
        ## Summary
        ## Per-Topic Findings (one subsection per topic — name the best diagram file)
        ## Cross-Cutting Insights
        ## Discrepancies (D-01, D-02, ...)
        ## Open Questions

  # --------------------------------------------------------------------------
  # Step 6: Build investigation manifest for downstream synthesis
  # Emits a structured JSON blob that synthesis reads to know where everything is.
  # --------------------------------------------------------------------------
  - id: "build-manifest"
    type: "bash"
    output: "investigation_manifest"
    parse_json: true
    timeout: 30
    command: |
      python3 << 'EOF'
      import json
      from pathlib import Path

      topics_raw = '''{{topics_with_paths}}'''
      try:
          topics = json.loads(topics_raw)
      except Exception:
          import ast
          topics = ast.literal_eval(topics_raw)

      inv = Path("{{investigation_dir}}")

      manifest = {
          "investigation_dir": "{{investigation_dir}}",
          "tier": "{{tier}}",
          "topics": topics,
          "reconciliation": str(inv / "foreman-notes" / "reconciliation.md"),
          "wave1_dir": str(inv / "wave-1"),
      }
      print(json.dumps(manifest))
      EOF
```

**Step 2: Run the tests to verify they pass**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_investigation_recipe.py -v
```

Expected output: **All tests PASSED**

> **If `test_code_tracers_has_no_tier_condition` fails:** This means the `wave1-code-tracers` step inadvertently has a `condition:` key. Remove it — code-tracers run for all tiers.

---

## Task 3: Run full test suite and commit the investigation recipe

**Step 1: Run the full suite**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -q
```

Expected: All tests pass. Zero failures.

**Step 2: Commit**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && \
  git add recipes/dotfiles-investigate.yaml tests/test_investigation_recipe.py && \
  git commit -m "feat: add dotfiles-investigate.yaml bespoke documentation wave recipe with full test coverage"
```

---

## Task 4: Write failing tests for discovery pipeline wiring (RED)

**Files:**
- Modify: `tests/test_discovery_recipe.py`

**Step 1: Append the new test class**

Open `tests/test_discovery_recipe.py` and append the following class **after all existing content**:

```python
class TestDiscoveryInvestigationWiring:
    """Verify dotfiles-discovery.yaml has the investigate-repos step and correct wiring."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        path = BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml"
        return yaml.safe_load(path.read_text())

    def _get_all_steps(self, recipe_data: dict) -> list:
        steps = list(recipe_data.get("steps", []))
        for stage in recipe_data.get("stages", []):
            steps.extend(stage.get("steps", []))
        return steps

    def _get_step(self, recipe_data: dict, step_id: str) -> dict:
        return next(
            (s for s in self._get_all_steps(recipe_data) if s.get("id") == step_id),
            {}
        )

    def test_has_investigate_repos_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "investigate-repos")
        assert step, (
            "dotfiles-discovery.yaml must have a step with id: investigate-repos. "
            "Add it to Stage 2 (investigation) after prescan-repos."
        )

    def test_investigate_repos_calls_investigate_recipe(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "investigate-repos")
        assert step, "investigate-repos step not found"
        recipe_ref = step.get("recipe", "")
        assert "dotfiles-investigate" in recipe_ref, (
            f"investigate-repos must reference dotfiles-investigate.yaml, "
            f"got recipe: {recipe_ref!r}"
        )

    def test_investigate_repos_has_on_error_continue(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "investigate-repos")
        assert step, "investigate-repos step not found"
        assert step.get("on_error") == "continue", (
            "investigate-repos must have on_error: continue — one bad repo must not "
            "kill the rest"
        )

    def test_investigate_repos_has_collect(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "investigate-repos")
        assert step, "investigate-repos step not found"
        assert step.get("collect") == "investigation_results", (
            f"investigate-repos must have collect: investigation_results, "
            f"got: {step.get('collect')!r}"
        )

    def test_investigate_repos_comes_after_prescan_repos(self, recipe_data: dict) -> None:
        steps = self._get_all_steps(recipe_data)
        ids = [s.get("id") for s in steps]
        assert "prescan-repos" in ids, "prescan-repos step not found"
        assert "investigate-repos" in ids, "investigate-repos step not found"
        assert ids.index("prescan-repos") < ids.index("investigate-repos"), (
            "investigate-repos must come after prescan-repos"
        )

    def test_run_synthesis_topics_from_investigation_results(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "run-synthesis")
        assert step, "run-synthesis step not found"
        ctx = step.get("context", {})
        topics_value = ctx.get("topics", "")
        assert "investigation_results" in str(topics_value), (
            f"run-synthesis context.topics must reference investigation_results, "
            f"got: {topics_value!r}. "
            f"This was previously broken as {{{{repo_entry.topics}}}} — fix it."
        )

    def test_tier3_analysis_has_agent_field(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "tier3-analysis")
        assert step, "tier3-analysis step not found"
        assert step.get("agent"), (
            "tier3-analysis step must have an agent: field. "
            "Add agent: dot-graph:dot-author"
        )
```

**Step 2: Run the tests to verify they fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_discovery_recipe.py::TestDiscoveryInvestigationWiring -v
```

Expected output: **FAILED** — first failure is `dotfiles-discovery.yaml must have a step with id: investigate-repos`

---

## Task 5: Wire investigate-repos into dotfiles-discovery.yaml (GREEN)

**Files:**
- Modify: `recipes/dotfiles-discovery.yaml`

This task makes **three surgical edits** to the existing file. Read the file first to confirm line numbers match expectations.

---

### Edit 1: Add `investigate-repos` step to Stage 2

In `recipes/dotfiles-discovery.yaml`, find Stage 2 (`investigation`). It has two steps: `process-repos` and `prescan-repos`. The `prescan-repos` step ends with `timeout: 600`, followed by the stage's `approval:` block.

Add the following YAML block **after the `prescan-repos` step** and **before the `approval:` key**:

```yaml
      # ------------------------------------------------------------------------
      # Step 3: Run documentation-focused investigation per repo
      # Dispatches dotfiles-investigate for each active repo (Tier 1+).
      # on_error: continue — one bad repo does not abort the rest.
      # ------------------------------------------------------------------------
      - id: "investigate-repos"
        foreach: "{{tier_plan}}"
        as: "repo_entry"
        condition: "{{repo_entry.tier}} >= 1"
        collect: "investigation_results"
        type: "recipe"
        recipe: "@dot-docs:recipes/dotfiles-investigate.yaml"
        context:
          repo_path: "{{repo_entry.repo_path}}"
          investigation_dir: "{{repo_entry.output_dir}}/.investigation"
          topics_hint: "{{prescan_results}}"
          tier: "{{repo_entry.tier}}"
        on_error: continue
        timeout: 7200
```

> **Indentation note:** The `- id:` must be indented to match the other steps in the `steps:` list (6 spaces — same as `- id: "process-repos"` and `- id: "prescan-repos"`).

---

### Edit 2: Fix `topics` in `run-synthesis` context

In Stage 3 (`synthesis`), find the `run-synthesis` step. Its `context:` block currently has:

```yaml
          topics: "{{repo_entry.topics}}"
```

Replace that one line with:

```yaml
          topics: "{{investigation_results}}"
```

> **Why this was broken:** `{{repo_entry.topics}}` refers to a field that doesn't exist on the tier_plan entries. The actual topic data now lives in `investigation_results`, which is the collected output of the `investigate-repos` foreach loop.

---

### Edit 3: Add `agent:` to `tier3-analysis` step

In Stage 3 (`synthesis`), find the `tier3-analysis` step. It currently looks like:

```yaml
      - id: "tier3-analysis"
        foreach: "{{tier_plan}}"
        as: "repo_entry"
        condition: "{{repo_entry.tier}} == 3"
        collect: "analysis_results"
        type: "agent"
        output: "tier3_analysis"
        timeout: 600
        prompt: |
```

Add the `agent:` field immediately after `type: "agent"`:

```yaml
      - id: "tier3-analysis"
        foreach: "{{tier_plan}}"
        as: "repo_entry"
        condition: "{{repo_entry.tier}} == 3"
        collect: "analysis_results"
        type: "agent"
        agent: "dot-graph:dot-author"
        output: "tier3_analysis"
        timeout: 600
        prompt: |
```

---

**Run the tests to verify all three edits pass:**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_discovery_recipe.py::TestDiscoveryInvestigationWiring -v
```

Expected output: **All tests PASSED**

---

## Task 6: Run full test suite and commit discovery wiring

**Step 1: Run the full suite**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -q
```

Expected: All tests pass. Zero failures.

> **If tests fail:** The most likely causes are:
> 1. YAML indentation error in the edited `dotfiles-discovery.yaml` — check that all steps are indented consistently (the `- id:` for `investigate-repos` should be at the same indent level as `- id: "prescan-repos"`)
> 2. An existing test that checks `topics: "{{repo_entry.topics}}"` by its exact string — update that test to check for `investigation_results` instead
> 3. A YAML parse error from the new step — run `python3 -c "import yaml; yaml.safe_load(open('recipes/dotfiles-discovery.yaml').read()); print('OK')"` to check

**Step 2: Commit**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && \
  git add recipes/dotfiles-discovery.yaml tests/test_discovery_recipe.py && \
  git commit -m "feat: wire investigate-repos into discovery pipeline, fix topics flow, add tier3-analysis agent field"
```

---

## Task 7: Final validation

**Step 1: Confirm the YAML files parse cleanly**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python3 << 'EOF'
import yaml
from pathlib import Path

files = [
    "recipes/dotfiles-discovery.yaml",
    "recipes/dotfiles-investigate.yaml",
    "recipes/dotfiles-synthesis.yaml",
    "recipes/dotfiles-prescan.yaml",
]

for f in files:
    path = Path(f)
    try:
        data = yaml.safe_load(path.read_text())
        assert data is not None
        print(f"  OK: {f}")
    except Exception as e:
        print(f"  FAIL: {f} — {e}")
EOF
```

Expected: `OK` for all four files.

**Step 2: Confirm test count is growing**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -q --co | tail -5
```

Expected: The test count is higher than before Phase 1 (was 173). The new tests from all three phases should be visible.

**Step 3: Check recent commits**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && git log --oneline -10
```

Expected: At least 8 commits from all three phases, newest first. No stray uncommitted changes.

---

## Phase 3 Complete

At the end of this phase:
- `recipes/dotfiles-investigate.yaml` — 6-step recipe created: `prepare-workspace` → `select-topics` → `build-topic-paths` → `wave1-code-tracers` → `wave1-behavior-observers` (tier 1/2) → `wave1-integration-mappers` (tier 1/2) → `lead-investigator` → `build-manifest` ✓
- `tests/test_investigation_recipe.py` — full structural test coverage for the investigate recipe ✓
- `recipes/dotfiles-discovery.yaml` — `investigate-repos` step added to Stage 2 with `on_error: continue` ✓
- `recipes/dotfiles-discovery.yaml` — `run-synthesis` context now reads `topics` from `investigation_results` ✓
- `recipes/dotfiles-discovery.yaml` — `tier3-analysis` step has `agent: "dot-graph:dot-author"` ✓
- All pre-existing tests still pass ✓

**The investigation recipe design is now fully implemented across all three phases.**

---

## Appendix: What "integration testing" looks like

The test suite validates structure and wiring. It does NOT execute agents. To verify the pipeline end-to-end, a developer would run:

```bash
amplifier recipes execute @dot-docs:recipes/dotfiles-discovery.yaml \
  --context '{
    "profile_path": "/path/to/profile.yaml",
    "dotfiles_root": "/path/to/output",
    "repos_root": "/path/to/repos"
  }'
```

This is the developer's own integration test on a real repo. It is out of scope for this test suite.
