# Phase 1: Foundation Fixes — Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Fix three broken agent steps in the synthesis recipe, create the missing quality-standards context file, add the parallax-discovery bundle dependency, and update the awareness doc — making the existing pipeline runnable end-to-end.

**Architecture:** The synthesis recipe has three `type: "agent"` steps (`synthesize`, `quality-review`, `fix-if-failed`) that are missing their `agent:` fields, causing the recipe engine to fail. This phase patches those fields, creates `context/dot-quality-standards.md` (a one-line shim that fixes a broken `@mention` in `synthesis-prompt.md`), registers the `parallax-discovery` bundle in `bundle.md`, and updates `context/dot-docs-awareness.md` to mention the forthcoming investigate recipe.

**Tech Stack:** Python, pytest, YAML (PyYAML), git

**Prerequisites:** None — this is Phase 1.

**Working directory for all commands:** `/home/bkrabach/dev/dot-docs/dot-docs/`

---

## Orientation

Before starting, read these files to orient yourself:

- `recipes/dotfiles-synthesis.yaml` — note that `synthesize` (line 93), `quality-review` (line 116), and `fix-if-failed` (line 149) all have `type: "agent"` but no `agent:` field
- `tests/test_synthesis_artifacts.py` — existing test class is `TestSynthesisPrompt`; you will add new classes after it
- `bundle.md` — currently includes `amplifier-foundation`, `amplifier-bundle-dot-graph`, and `dot-docs:behaviors/dot-docs`
- `context/dot-docs-awareness.md` — lists three recipes; you will add a fourth

**How tests are structured:** `BUNDLE_ROOT = Path(__file__).parent.parent` is defined at the top of each test file. Tests are class-based. Use `yaml.safe_load(path.read_text())` to load YAML files.

---

## Task 1: Write failing tests for synthesis agent fields (RED)

**Files:**
- Modify: `tests/test_synthesis_artifacts.py`

**Step 1: Append the new test class to the end of the file**

Open `tests/test_synthesis_artifacts.py` and append the following class **after all existing content**:

```python
class TestSynthesisAgentFields:
    """Verify all agent steps in dotfiles-synthesis.yaml have explicit agent: fields."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        path = BUNDLE_ROOT / "recipes" / "dotfiles-synthesis.yaml"
        return yaml.safe_load(path.read_text())

    def _get_step(self, recipe_data: dict, step_id: str) -> dict:
        """Find a step by id, searching both top-level steps and stage steps."""
        all_steps = list(recipe_data.get("steps", []))
        for stage in recipe_data.get("stages", []):
            all_steps.extend(stage.get("steps", []))
        return next((s for s in all_steps if s.get("id") == step_id), {})

    def test_synthesize_step_has_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "synthesize")
        assert step, "synthesize step not found in dotfiles-synthesis.yaml"
        assert step.get("agent") == "dot-graph:dot-author", (
            f"synthesize step must have agent: dot-graph:dot-author, got: {step.get('agent')!r}"
        )

    def test_quality_review_step_has_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "quality-review")
        assert step, "quality-review step not found in dotfiles-synthesis.yaml"
        assert step.get("agent") == "dot-graph:diagram-reviewer", (
            f"quality-review step must have agent: dot-graph:diagram-reviewer, got: {step.get('agent')!r}"
        )

    def test_fix_if_failed_step_has_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "fix-if-failed")
        assert step, "fix-if-failed step not found in dotfiles-synthesis.yaml"
        assert step.get("agent") == "dot-graph:dot-author", (
            f"fix-if-failed step must have agent: dot-graph:dot-author, got: {step.get('agent')!r}"
        )
```

**Step 2: Run the tests to verify they fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py::TestSynthesisAgentFields -v
```

Expected output: **3 FAILED** — each test shows `AssertionError: synthesize step must have agent: dot-graph:dot-author, got: None` (or similar).

---

## Task 2: Add agent fields to the synthesis recipe (GREEN)

**Files:**
- Modify: `recipes/dotfiles-synthesis.yaml`

**Step 1: Add `agent: "dot-graph:dot-author"` to the `synthesize` step**

In `recipes/dotfiles-synthesis.yaml`, find the `synthesize` step (around line 93). It looks like:

```yaml
  - id: "synthesize"
    type: "agent"
    prompt: |
```

Change it to:

```yaml
  - id: "synthesize"
    type: "agent"
    agent: "dot-graph:dot-author"
    prompt: |
```

**Step 2: Add `agent: "dot-graph:diagram-reviewer"` to the `quality-review` step**

Find the `quality-review` step (around line 116). It looks like:

```yaml
  - id: "quality-review"
    type: "agent"
    prompt: |
```

Change it to:

```yaml
  - id: "quality-review"
    type: "agent"
    agent: "dot-graph:diagram-reviewer"
    prompt: |
```

**Step 3: Add `agent: "dot-graph:dot-author"` to the `fix-if-failed` step**

Find the `fix-if-failed` step (around line 149). It looks like:

```yaml
  - id: "fix-if-failed"
    type: "agent"
    condition: "'FAIL' in '{{review_verdict}}'"
```

Change it to:

```yaml
  - id: "fix-if-failed"
    type: "agent"
    agent: "dot-graph:dot-author"
    condition: "'FAIL' in '{{review_verdict}}'"
```

**Step 4: Run the tests to verify they pass**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py::TestSynthesisAgentFields -v
```

Expected output: **3 PASSED**

---

## Task 3: Commit synthesis agent fields

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && \
  git add recipes/dotfiles-synthesis.yaml tests/test_synthesis_artifacts.py && \
  git commit -m "fix: add agent fields to synthesis recipe steps (synthesize, quality-review, fix-if-failed)"
```

---

## Task 4: Write failing tests for dot-quality-standards.md (RED)

**Files:**
- Modify: `tests/test_synthesis_artifacts.py`

**Step 1: Append the new test class**

Append the following class **after `TestSynthesisAgentFields`** in `tests/test_synthesis_artifacts.py`:

```python
class TestDotQualityStandards:
    """Verify context/dot-quality-standards.md exists with the required @mention."""

    @pytest.fixture
    def standards_path(self) -> Path:
        return BUNDLE_ROOT / "context" / "dot-quality-standards.md"

    def test_file_exists(self, standards_path: Path) -> None:
        assert standards_path.exists(), (
            f"dot-quality-standards.md not found at {standards_path}"
        )

    def test_references_dot_graph_quality_skill(self, standards_path: Path) -> None:
        content = standards_path.read_text()
        assert "@dot-graph:skills/dot-quality" in content, (
            "dot-quality-standards.md must contain: @dot-graph:skills/dot-quality"
        )
```

**Step 2: Run the tests to verify they fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py::TestDotQualityStandards -v
```

Expected output: **FAILED** — `dot-quality-standards.md not found`

---

## Task 5: Create dot-quality-standards.md (GREEN)

**Files:**
- Create: `context/dot-quality-standards.md`

**Step 1: Create the file**

Create `context/dot-quality-standards.md` with exactly this content (one line, no trailing blank line):

```
@dot-graph:skills/dot-quality
```

**Step 2: Run the tests to verify they pass**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py::TestDotQualityStandards -v
```

Expected output: **2 PASSED**

---

## Task 6: Commit the quality standards file

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && \
  git add context/dot-quality-standards.md tests/test_synthesis_artifacts.py && \
  git commit -m "fix: create dot-quality-standards.md to resolve broken @mention in synthesis-prompt.md"
```

---

## Task 7: Write failing test for bundle.md parallax-discovery dependency (RED)

**Files:**
- Modify: `tests/test_synthesis_artifacts.py`

**Step 1: Append the new test class**

Append after `TestDotQualityStandards`:

```python
class TestBundleDependencies:
    """Verify bundle.md declares required bundle dependencies."""

    @pytest.fixture
    def bundle_content(self) -> str:
        return (BUNDLE_ROOT / "bundle.md").read_text()

    def test_parallax_discovery_included(self, bundle_content: str) -> None:
        assert "amplifier-bundle-parallax-discovery" in bundle_content, (
            "bundle.md must include amplifier-bundle-parallax-discovery. "
            "Add it to the 'includes:' block."
        )
```

**Step 2: Run the test to verify it fails**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py::TestBundleDependencies -v
```

Expected output: **FAILED** — `bundle.md must include amplifier-bundle-parallax-discovery`

---

## Task 8: Add parallax-discovery to bundle.md (GREEN)

**Files:**
- Modify: `bundle.md`

**Step 1: Add the bundle line**

In `bundle.md`, find the `includes:` block:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-dot-graph@main
  - bundle: dot-docs:behaviors/dot-docs
```

Add the parallax-discovery line **after** the dot-graph line:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-dot-graph@main
  - bundle: git+https://github.com/bkrabach/amplifier-bundle-parallax-discovery@main
  - bundle: dot-docs:behaviors/dot-docs
```

> **⚠️ Open question:** The `bkrabach/` org is the currently known location. If integration testing shows a 404, check whether the bundle has moved to `microsoft/amplifier-bundle-parallax-discovery`. The test only checks that the string `amplifier-bundle-parallax-discovery` appears — it will pass with either org prefix.

**Step 2: Run the test to verify it passes**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py::TestBundleDependencies -v
```

Expected output: **PASSED**

---

## Task 9: Commit the bundle dependency

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && \
  git add bundle.md tests/test_synthesis_artifacts.py && \
  git commit -m "feat: add parallax-discovery bundle dependency to dot-docs bundle.md"
```

---

## Task 10: Write failing test for awareness doc (RED)

**Files:**
- Modify: `tests/test_synthesis_artifacts.py`

**Step 1: Append the new test class**

Append after `TestBundleDependencies`:

```python
class TestAwarenessDocument:
    """Verify context/dot-docs-awareness.md mentions all four recipes including the new investigate recipe."""

    @pytest.fixture
    def awareness_content(self) -> str:
        return (BUNDLE_ROOT / "context" / "dot-docs-awareness.md").read_text()

    def test_mentions_investigate_recipe(self, awareness_content: str) -> None:
        assert "dotfiles-investigate" in awareness_content, (
            "dot-docs-awareness.md must mention the dotfiles-investigate recipe. "
            "Add a bullet for it under 'Available Recipes'."
        )
```

**Step 2: Run the test to verify it fails**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py::TestAwarenessDocument -v
```

Expected output: **FAILED** — `dot-docs-awareness.md must mention the dotfiles-investigate recipe`

---

## Task 11: Update the awareness document (GREEN)

**Files:**
- Modify: `context/dot-docs-awareness.md`

**Step 1: Add the investigate recipe bullet**

In `context/dot-docs-awareness.md`, the current `## Available Recipes` section has three bullets. Add a fourth bullet **after the prescan bullet and before the synthesis bullet** (insert in logical pipeline order):

```markdown
- **dotfiles-investigate** (`dot-docs:recipes/dotfiles-investigate.yaml`) — Dispatches Parallax Discovery triplicate agents (code-tracer, behavior-observer, integration-mapper) against a single repository and writes raw investigation artifacts to the investigation workspace. Called by dotfiles-discovery for Tier 1 and Tier 2 repos. Tier 3 repos run code-tracer only.
```

The final `## Available Recipes` section should read:

```markdown
## Available Recipes

Invoke these via the `recipes` tool:

- **dotfiles-discovery** (`dot-docs:recipes/dotfiles-discovery`) — Orchestrates the full discovery pipeline: scans repos, determines investigation tier, dispatches Parallax Discovery, synthesizes DOT output
- **dotfiles-prescan** (`dot-docs:recipes/dotfiles-prescan`) — Pre-scans repository architecture to determine which investigation topics are relevant
- **dotfiles-investigate** (`dot-docs:recipes/dotfiles-investigate.yaml`) — Dispatches Parallax Discovery triplicate agents (code-tracer, behavior-observer, integration-mapper) against a single repository and writes raw investigation artifacts to the investigation workspace. Called by dotfiles-discovery for Tier 1 and Tier 2 repos. Tier 3 repos run code-tracer only.
- **dotfiles-synthesis** (`dot-docs:recipes/dotfiles-synthesis`) — Synthesizes raw DOT investigation output from multiple agents into polished, canonical graph files with quality gate review loop
```

**Step 2: Run the test to verify it passes**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py::TestAwarenessDocument -v
```

Expected output: **PASSED**

---

## Task 12: Run full test suite and commit

**Step 1: Run full suite to confirm nothing broke**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -q
```

Expected output: All tests pass. Count will be higher than 173 (new tests added in this phase). Zero failures.

**Step 2: Commit**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && \
  git add context/dot-docs-awareness.md tests/test_synthesis_artifacts.py && \
  git commit -m "docs: update awareness doc to mention dotfiles-investigate recipe"
```

**Step 3: Verify recent commits look clean**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && git log --oneline -5
```

Expected: Four clean commits from this phase, newest first.

---

## Phase 1 Complete

At the end of this phase:
- `recipes/dotfiles-synthesis.yaml` — all three agent steps have `agent:` fields ✓
- `context/dot-quality-standards.md` — exists with `@dot-graph:skills/dot-quality` ✓
- `bundle.md` — includes `amplifier-bundle-parallax-discovery` ✓
- `context/dot-docs-awareness.md` — mentions `dotfiles-investigate` ✓
- All pre-existing tests still pass ✓
- New `TestSynthesisAgentFields`, `TestDotQualityStandards`, `TestBundleDependencies`, `TestAwarenessDocument` classes added to `tests/test_synthesis_artifacts.py` ✓

**Continue with Phase 2:** `docs/plans/2026-03-26-phase2-prescan-upgrade-implementation.md`
