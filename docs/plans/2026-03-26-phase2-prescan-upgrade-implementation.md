# Phase 2: Prescan Upgrade — Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Replace the heuristic bash prescan with a two-step prescan (bash metadata gather + agent topic selection), guided by a new `context/prescan-prompt.md` that steers the agent toward three documentation perspectives: architecture, execution flows, and state/data models.

**Architecture:** The existing `dotfiles-prescan.yaml` has a single bash step (`detect-topics`) that heuristically scans for Python `__init__.py` files and returns up to 5 directory names as "topics." These names are poor choices for documentation — they reflect code structure, not documentation concerns. The upgrade replaces this with: (1) a rich bash step that gathers repo metadata (top-level structure, README excerpt, language fingerprint, build manifests), then (2) an agent step that reads that metadata plus `prescan-prompt.md` and returns structured topic objects shaped toward the three documentation perspectives. The heuristic bash step is renamed `gather-metadata`; the agent step is new and called `select-topics`.

**Tech Stack:** Python, pytest, YAML (PyYAML), git

**Prerequisites:** Phase 1 must be complete. Specifically: `bundle.md` must already include `parallax-discovery` (added in Phase 1), and `context/dot-quality-standards.md` must exist.

**Working directory for all commands:** `/home/bkrabach/dev/dot-docs/dot-docs/`

---

## Orientation

Before starting, read these two files:

- `recipes/dotfiles-prescan.yaml` — the existing file has a single bash step `detect-topics` with `output: "prescan_result"` and `parse_json: true`. You will **replace** this file entirely.
- `tests/test_discovery_recipe.py` — the existing test classes are `TestDiscoveryRecipeExists` and `TestDiscoveryRecipeRecursion`. You will add new classes after them.

The three documentation perspectives that must appear in `prescan-prompt.md`:
1. **Architecture** — module boundaries, composition, key interfaces
2. **Execution flows** — key runtime paths, lifecycle sequences
3. **State / Data models** — state machines, data schemas, key enumerations

---

## Task 1: Write failing tests for prescan-prompt.md (RED)

**Files:**
- Modify: `tests/test_discovery_recipe.py`

**Step 1: Append the new test class**

Open `tests/test_discovery_recipe.py` and append the following class **after all existing content**:

```python
class TestPrescanPrompt:
    """Verify context/prescan-prompt.md exists with all required sections."""

    @pytest.fixture
    def prompt_path(self) -> Path:
        return BUNDLE_ROOT / "context" / "prescan-prompt.md"

    def test_file_exists(self, prompt_path: Path) -> None:
        assert prompt_path.exists(), (
            f"context/prescan-prompt.md not found at {prompt_path}"
        )

    def test_file_is_nonempty(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert len(content.strip()) > 100, "prescan-prompt.md appears too short"

    def test_mentions_architecture_perspective(self, prompt_path: Path) -> None:
        content = prompt_path.read_text().lower()
        assert "architecture" in content, (
            "prescan-prompt.md must describe the Architecture documentation perspective"
        )

    def test_mentions_execution_flows_perspective(self, prompt_path: Path) -> None:
        content = prompt_path.read_text().lower()
        assert "execution" in content, (
            "prescan-prompt.md must describe the Execution flows documentation perspective"
        )

    def test_mentions_state_perspective(self, prompt_path: Path) -> None:
        content = prompt_path.read_text().lower()
        assert "state" in content, (
            "prescan-prompt.md must describe the State/Data models documentation perspective"
        )

    def test_specifies_json_output_format(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "json" in content.lower(), (
            "prescan-prompt.md must specify JSON as the output format"
        )

    def test_output_format_includes_slug_field(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "slug" in content, (
            "prescan-prompt.md output format must include a 'slug' field (kebab-case topic ID)"
        )

    def test_output_format_includes_rationale_field(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "rationale" in content, (
            "prescan-prompt.md output format must include a 'rationale' field"
        )

    def test_calibration_mentions_tiers(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "tier" in content.lower(), (
            "prescan-prompt.md must mention tier-based calibration (Tier 1/2/3)"
        )
```

**Step 2: Run the tests to verify they fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_discovery_recipe.py::TestPrescanPrompt -v
```

Expected output: **FAILED** — first failure is `context/prescan-prompt.md not found`

---

## Task 2: Create prescan-prompt.md (GREEN)

**Files:**
- Create: `context/prescan-prompt.md`

**Step 1: Create the file**

Create `context/prescan-prompt.md` with exactly the following content:

```markdown
# Prescan Topic Selection

You are selecting investigation topics for a codebase documentation pipeline. Your
goal is to identify 3-6 topics that, when investigated, will produce the most useful
architectural documentation for a team knowledge base.

## Repository Metadata

The repository metadata below was gathered by the previous step. Use it to understand
the codebase structure before selecting topics.

## Topic Selection Guidelines

Select topics that map to these three documentation perspectives:

**Architecture perspective** — What exists and how it is composed:
- Module boundaries, package structure, key dependencies
- How components wire together (config files, dependency injection, service registry)
- External system integrations

**Execution flows perspective** — How things run at runtime:
- The primary happy-path flow from input to output
- Key lifecycle events (startup, request, shutdown)
- Background tasks, event loops, scheduled work

**State / Data models perspective** — What states things can be in:
- Key enums and their values
- Data model schemas and relationships
- State machine transitions

## Output Format

Return ONLY a JSON array. No markdown, no explanation, no code fence. Just the array:

[
  {
    "name": "Human-readable topic name",
    "slug": "kebab-case-slug",
    "rationale": "One sentence: why this topic matters for documentation"
  }
]

## Calibration by Repo Complexity and Tier

- **Tier 3 (PATCH — minor changes):** 1-2 topics max, focused on the changed area only
- **Tier 2 (WAVE — structural changes):** 3-4 topics covering the changed subsystems
- **Tier 1 (FULL — no prior run):** 4-6 topics covering the full architecture

Prefer topics that represent distinct mechanisms, not directory names. A topic like
"plugin-loading-lifecycle" is better than "plugins". Aim for topics that will produce
meaningfully different DOT diagrams from each other.
```

**Step 2: Run the tests to verify they pass**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_discovery_recipe.py::TestPrescanPrompt -v
```

Expected output: **All tests PASSED**

---

## Task 3: Commit prescan-prompt.md

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && \
  git add context/prescan-prompt.md tests/test_discovery_recipe.py && \
  git commit -m "feat: add prescan-prompt.md for agent-driven topic selection toward documentation perspectives"
```

---

## Task 4: Write failing tests for the upgraded prescan recipe structure (RED)

**Files:**
- Modify: `tests/test_discovery_recipe.py`

**Step 1: Append the new test class**

Append the following class **after `TestPrescanPrompt`** in `tests/test_discovery_recipe.py`:

```python
class TestPrescanRecipeStructure:
    """Verify dotfiles-prescan.yaml has the upgraded 2-step structure."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        path = BUNDLE_ROOT / "recipes" / "dotfiles-prescan.yaml"
        return yaml.safe_load(path.read_text())

    def _get_all_steps(self, recipe_data: dict) -> list:
        """Return all steps from top-level and all stages."""
        steps = list(recipe_data.get("steps", []))
        for stage in recipe_data.get("stages", []):
            steps.extend(stage.get("steps", []))
        return steps

    def _get_step(self, recipe_data: dict, step_id: str) -> dict:
        return next(
            (s for s in self._get_all_steps(recipe_data) if s.get("id") == step_id),
            {}
        )

    def test_has_gather_metadata_bash_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "gather-metadata")
        assert step, (
            "dotfiles-prescan.yaml must have a bash step with id: gather-metadata. "
            "Rename or replace the existing detect-topics step."
        )
        assert step.get("type") == "bash", "gather-metadata step must be type: bash"

    def test_gather_metadata_has_parse_json(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "gather-metadata")
        assert step, "gather-metadata step not found"
        assert step.get("parse_json") is True, (
            "gather-metadata step must have parse_json: true"
        )

    def test_gather_metadata_has_output(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "gather-metadata")
        assert step, "gather-metadata step not found"
        assert step.get("output") == "scan_metadata", (
            "gather-metadata step must have output: scan_metadata"
        )

    def test_has_select_topics_agent_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "select-topics")
        assert step, (
            "dotfiles-prescan.yaml must have an agent step with id: select-topics"
        )
        assert step.get("type") == "agent", "select-topics step must be type: agent"

    def test_select_topics_references_prescan_prompt(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "select-topics")
        assert step, "select-topics step not found"
        prompt = step.get("prompt", "")
        assert "prescan-prompt" in prompt, (
            "select-topics step prompt must reference prescan-prompt.md via @dot-docs:context/prescan-prompt"
        )

    def test_select_topics_has_parse_json(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "select-topics")
        assert step, "select-topics step not found"
        assert step.get("parse_json") is True, (
            "select-topics step must have parse_json: true to parse the JSON array output"
        )

    def test_select_topics_has_output(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "select-topics")
        assert step, "select-topics step not found"
        assert step.get("output") == "prescan_result", (
            "select-topics step must have output: prescan_result "
            "(downstream discover recipe reads prescan_results from this field)"
        )

    def test_select_topics_references_scan_metadata(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "select-topics")
        assert step, "select-topics step not found"
        prompt = step.get("prompt", "")
        assert "scan_metadata" in prompt, (
            "select-topics prompt must reference {{scan_metadata}} from the gather-metadata step"
        )

    def test_gather_metadata_comes_before_select_topics(self, recipe_data: dict) -> None:
        steps = self._get_all_steps(recipe_data)
        ids = [s.get("id") for s in steps]
        assert "gather-metadata" in ids, "gather-metadata step not found"
        assert "select-topics" in ids, "select-topics step not found"
        assert ids.index("gather-metadata") < ids.index("select-topics"), (
            "gather-metadata must appear before select-topics in the recipe"
        )
```

**Step 2: Run the tests to verify they fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_discovery_recipe.py::TestPrescanRecipeStructure -v
```

Expected output: **FAILED** — first failure is `dotfiles-prescan.yaml must have a bash step with id: gather-metadata`

---

## Task 5: Replace dotfiles-prescan.yaml with the upgraded 2-step recipe (GREEN)

**Files:**
- Modify: `recipes/dotfiles-prescan.yaml`

**Step 1: Replace the entire file contents**

Overwrite `recipes/dotfiles-prescan.yaml` with the following content:

```yaml
name: "dotfiles-prescan"
description: >
  Pre-scan a repository to select documentation investigation topics using
  agent-driven topic selection shaped toward three documentation perspectives:
  architecture, execution flows, and state/data models.
version: "0.2.0"
tags: [dotfiles, prescan, topic-selection]

# Pre-scan Recipe (upgraded)
#
# Two-step pipeline:
#   1. gather-metadata (bash) — fast structural scan, no LLM
#   2. select-topics (agent)  — reads metadata, returns topic objects
#
# Context inputs:
#   repo_path — absolute path to the repository on disk
#
# Outputs:
#   prescan_result — JSON array of topic objects:
#     [{"name": "...", "slug": "...", "rationale": "..."}, ...]

context:
  repo_path: ""   # required — absolute path to the repository on disk

steps:
  # --------------------------------------------------------------------------
  # Step 1: Gather repo metadata (bash — fast, no LLM)
  # Produces a JSON object with top-level structure, README excerpt,
  # language fingerprint, and build manifest list.
  # --------------------------------------------------------------------------
  - id: "gather-metadata"
    type: "bash"
    output: "scan_metadata"
    parse_json: true
    timeout: 30
    command: |
      python3 << 'EOF'
      import json
      import os
      from pathlib import Path

      repo_path = Path("{{repo_path}}")
      result = {
          "repo_path": str(repo_path),
          "repo_name": repo_path.name,
          "top_level": [],
          "readme_excerpt": "",
          "languages": {},
          "build_manifests": [],
          "error": None,
      }

      if not repo_path.exists():
          result["error"] = f"Repository not found: {repo_path}"
          print(json.dumps(result))
          exit(0)

      # Top-level directories and files (skip hidden)
      try:
          entries = sorted(repo_path.iterdir())
          result["top_level"] = [
              {"name": e.name, "type": "dir" if e.is_dir() else "file"}
              for e in entries
              if not e.name.startswith(".")
          ][:30]
      except Exception as e:
          result["error"] = str(e)

      # README excerpt (first 2000 chars)
      for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
          readme = repo_path / readme_name
          if readme.exists():
              result["readme_excerpt"] = readme.read_text(errors="replace")[:2000]
              break

      # Detect build manifests
      for manifest in ["pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle"]:
          if (repo_path / manifest).exists():
              result["build_manifests"].append(manifest)

      # Count files by extension (top 10, skip hidden dirs)
      langs = {}
      for f in repo_path.rglob("*"):
          if not f.is_file():
              continue
          # Skip hidden directories
          if any(part.startswith(".") for part in f.relative_to(repo_path).parts):
              continue
          ext = f.suffix.lower()
          if ext:
              langs[ext] = langs.get(ext, 0) + 1
      result["languages"] = dict(sorted(langs.items(), key=lambda x: -x[1])[:10])

      print(json.dumps(result))
      EOF

  # --------------------------------------------------------------------------
  # Step 2: Agent-driven topic selection
  # Reads repo metadata and selects topics shaped toward the three
  # documentation perspectives defined in prescan-prompt.md.
  # --------------------------------------------------------------------------
  - id: "select-topics"
    type: "agent"
    output: "prescan_result"
    parse_json: true
    timeout: 600
    prompt: |
      @dot-docs:context/prescan-prompt.md

      ## Repository Metadata

      Repository name: {{scan_metadata.repo_name}}
      Repository path: {{scan_metadata.repo_path}}

      Top-level structure:
      {{scan_metadata.top_level}}

      README excerpt (first 2000 chars):
      {{scan_metadata.readme_excerpt}}

      Build manifests detected: {{scan_metadata.build_manifests}}

      File counts by extension (top 10): {{scan_metadata.languages}}

      Error (if any from metadata scan): {{scan_metadata.error}}

      ## Your Task

      Select investigation topics for this repository following the guidelines above.
      Return ONLY the JSON array — no markdown, no code fence, just the raw JSON.
```

**Step 2: Run the tests to verify they pass**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_discovery_recipe.py::TestPrescanRecipeStructure -v
```

Expected output: **All tests PASSED**

---

## Task 6: Run full test suite and commit prescan upgrade

**Step 1: Run the full test suite**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -q
```

Expected output: All tests pass. Zero failures. (Count will be higher than Phase 1 exit count due to new `TestPrescanPrompt` and `TestPrescanRecipeStructure` tests.)

> **If existing tests fail:** The most likely cause is that an existing test checks that `detect-topics` step exists by name. If so, find the failing test, read it carefully, and update it to check for `gather-metadata` instead.

**Step 2: Commit**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && \
  git add recipes/dotfiles-prescan.yaml tests/test_discovery_recipe.py && \
  git commit -m "feat: upgrade prescan to 2-step agent-driven topic selection (gather-metadata + select-topics)"
```

---

## Phase 2 Complete

At the end of this phase:
- `context/prescan-prompt.md` — exists, describes 3 documentation perspectives, specifies JSON array output with `name`/`slug`/`rationale` fields, includes tier-based calibration ✓
- `recipes/dotfiles-prescan.yaml` — upgraded to 2 steps: `gather-metadata` (bash) + `select-topics` (agent) ✓
- `select-topics` step outputs `prescan_result` with `parse_json: true` ✓
- New `TestPrescanPrompt` and `TestPrescanRecipeStructure` test classes added ✓
- All pre-existing tests still pass ✓

**Continue with Phase 3:** `docs/plans/2026-03-26-phase3-investigation-wiring-implementation.md`
