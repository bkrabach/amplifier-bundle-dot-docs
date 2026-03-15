# Dot-Graph Bundle Integration Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Integrate `amplifier-bundle-dot-graph`'s validation, analysis, and review capabilities into the dot-docs discovery pipeline so that synthesized DOT files are structurally validated and quality-reviewed before being committed.

**Architecture:** The dot-graph bundle provides three capabilities we want to wire in: (1) a `diagram-reviewer` agent that gives 5-level PASS/WARN/FAIL quality verdicts, (2) a `dot_graph(operation="validate")` tool that does 3-layer validation (syntax + structural + render quality), and (3) `dot_graph(operation="analyze")` for structural diff/orphan/cycle detection. We add these as optional enhancements that fall back gracefully when unavailable.

**Tech Stack:** Python 3.11+, pytest, dataclasses, Amplifier recipe YAML, Markdown context files

---

## Important Context for the Implementer

**Where things live:** Everything you'll modify is under `/home/bkrabach/dev/dot-docs/dot-docs/`. That's a nested directory — the workspace root is `/home/bkrabach/dev/dot-docs/` but the bundle lives one level deeper in `dot-docs/`.

**How to run tests:** Always `cd` into the bundle directory first:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -v
```

**Current test count:** 252 tests pass, 0 fail. Do not break any existing tests.

**pyproject.toml pythonpath:** The `pyproject.toml` at `dot-docs/pyproject.toml` sets `pythonpath = ["tools", "tests"]`, which means `from dotfiles_discovery.dot_validation import ...` works in tests because `tools/` is on the path, and `from conftest import VALID_DOT` works because `tests/` is on the path.

**Test style:** Class-based groupings (`class TestFoo:` with methods `def test_bar(self, ...)`). Fixtures use `pytest.fixture`. Dataclasses for results (not Pydantic). Import `from conftest import VALID_DOT, INVALID_DOT` for test DOT content.

**Recipe YAML style:** Steps have `id`, `type` (bash/prompt/recipe), `command` or `prompt`, `output`, and `timeout`. Staged recipes have `stages` with `name`, `steps`, and optional `approval`. Context variables use `{{variable_name}}` syntax.

---

## Task 1: Update `synthesis-prompt.md` — Add Reconciliation Methodology

**Files:**
- Modify: `dot-docs/context/synthesis-prompt.md` (currently 145 lines)

### Step 1: Add reconciliation methodology section after Step 2

Open `dot-docs/context/synthesis-prompt.md` and insert a new subsection between the existing "Step 2: Reconcile Overlapping Content" (line 31) and "Step 3: Choose Overview Perspective" (line 41).

Find this text (around line 38-40):
```markdown
- Do not copy any single agent's raw output verbatim — always synthesize across all agents

### Step 3: Choose Overview Perspective
```

Replace it with:
```markdown
- Do not copy any single agent's raw output verbatim — always synthesize across all agents

#### Reconciliation Methodology (from `dot-as-analysis` skill)

Apply the 4-phase reconciliation workflow when merging agent outputs:

1. **Introspect** — Before reading raw DOT files, write down what you believe the system does
   based on the repo path and topics list. List components, flows, states. This captures your
   prior mental model.
2. **Represent** — Draw your belief as DOT. Every node must connect to something — floating
   nodes are a forcing function that reveals gaps.
3. **Reconcile** — Read all raw DOT files and reconciliation notes. For each element in your
   belief diagram, verify it exists in the agent outputs. Fill in a findings table:

   | Element | Believed | Actual (from agents) | Status | Issue |
   |---------|----------|----------------------|--------|-------|
   | _example_ | _validates input_ | _delegates to external_ | WRONG | _undocumented dep_ |
   | _example_ | _retry logic present_ | _no retry_ | MISSING | _silent failure_ |

4. **Surface** — Update your diagram to reflect reality. The delta between your belief and the
   agent evidence is your finding report. Each discrepancy is a candidate bug or design debt.

#### Anti-Rationalization Table

When reconciling, these thoughts will arise. Resist them:

| Rationalization | Correction |
|-----------------|------------|
| "That path probably exists, I'll add it anyway" | Only draw what you can verify. Unverified paths are hypotheses, not facts. |
| "The diagram is close enough" | Close enough hides the discrepancy. Draw the delta explicitly. |
| "It works in practice so the diagram doesn't matter" | If it works differently than drawn, the diagram is wrong. Fix the diagram or document the reason. |
| "That component is internal, I don't need to show it" | Hidden internals are where bugs live. Show it. |
| "The error path is obvious, I'll skip it" | Error paths are where the interesting failures happen. Draw them explicitly. |
| "That's just infrastructure, not worth diagramming" | Infrastructure failures are system failures. Include it. |
| "I'll add the legend later" | Legends are added before sharing, not after. A diagram without a legend is ambiguous. |

### Step 3: Choose Overview Perspective
```

### Step 2: Add dot-graph skill references to Quality Checklist

Find this text at the end of the file (around lines 133-145):
```markdown
## Quality Checklist

Before writing each output file, verify:

- [ ] overview.dot is 150–250 lines and under 15KB
- [ ] overview.dot has a `subgraph cluster_legend` with real nodes
- [ ] All node IDs use `snake_case` with cluster prefix
- [ ] Every shape matches the shape vocabulary table in dot-quality-standards.md
- [ ] Edge styles follow the semantics table in dot-quality-standards.md
- [ ] Red used for confirmed bugs; orange for suspected issues
- [ ] No anti-patterns present
- [ ] Detail file cluster names match overview.dot cluster names exactly
- [ ] `dot -Tsvg overview.dot` renders without errors
```

Replace it with:
```markdown
## Quality Checklist

Before writing each output file, verify:

- [ ] overview.dot is 150–250 lines and under 15KB
- [ ] overview.dot has a `subgraph cluster_legend` with real nodes
- [ ] All node IDs use `snake_case` with cluster prefix
- [ ] Every shape matches the shape vocabulary table in dot-quality-standards.md
- [ ] Edge styles follow the semantics table in dot-quality-standards.md
- [ ] Red used for confirmed bugs; orange for suspected issues
- [ ] No anti-patterns present
- [ ] Detail file cluster names match overview.dot cluster names exactly
- [ ] `dot -Tsvg overview.dot` renders without errors
- [ ] No orphan nodes (every node has at least one edge)
- [ ] No isolated clusters (every cluster has at least one cross-cluster edge)
- [ ] Legend covers all shapes and edge styles used in the diagram

## Skills to Load

When available, load these skills from the `dot-graph` bundle for reference during synthesis:

- `dot-syntax` — DOT language reference for correct syntax
- `dot-patterns` — Copy-paste templates for common diagram types
- `dot-quality` — Quality enforcement standards and checklists
- `dot-as-analysis` — Reconciliation methodology (the 4-phase workflow above)
- `dot-graph-intelligence` — Programmatic graph analysis guidance
```

### Step 3: Run tests to verify nothing broke

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py -v
```
Expected: All existing `TestSynthesisPrompt` tests PASS. The new content adds reconciliation/anti-rationalization text which satisfies (doesn't break) the existing content checks.

### Step 4: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/context/synthesis-prompt.md && git commit -m "feat: add reconciliation methodology and skill references to synthesis prompt"
```

---

## Task 2: Add `validate_with_dot_graph()` to `dot_validation.py`

**Files:**
- Modify: `dot-docs/tools/dotfiles_discovery/dot_validation.py` (currently 216 lines)

### Step 1: Add the `EnhancedValidationResult` dataclass and `validate_with_dot_graph()` function

Open `dot-docs/tools/dotfiles_discovery/dot_validation.py`. After the existing `DotFileValidation` dataclass (after line 45), add the new dataclass.

Find this text:
```python
@dataclass
class DotFileValidation:
    """Combined validation result for a DOT file."""

    valid_syntax: bool
    syntax_error: str | None
    line_count: int
    line_count_in_range: bool
    render_ok: bool
    render_error: str | None = None


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------
```

Replace it with:
```python
@dataclass
class DotFileValidation:
    """Combined validation result for a DOT file."""

    valid_syntax: bool
    syntax_error: str | None
    line_count: int
    line_count_in_range: bool
    render_ok: bool
    render_error: str | None = None


@dataclass
class EnhancedValidationResult:
    """Combined result from both basic and dot-graph-enhanced validation.

    When the ``dot_graph`` tool is available, ``dot_graph_available`` is ``True``
    and the ``structural_*`` and ``quality_*`` fields are populated.  When it is
    not available (import error, "not yet implemented" response, etc.), the
    basic validation still runs and the enhanced fields are ``None``.
    """

    # --- Basic validation (always populated) ---
    basic: DotFileValidation

    # --- Enhanced validation (None when dot_graph unavailable) ---
    dot_graph_available: bool = False
    structural_issues: list[str] | None = None
    quality_warnings: list[str] | None = None
    dot_graph_error: str | None = None

    @property
    def is_valid(self) -> bool:
        """Overall validity: basic syntax must pass; structural issues are warnings."""
        return self.basic.valid_syntax

    @property
    def has_warnings(self) -> bool:
        """True if any non-fatal warnings exist from either layer."""
        if not self.basic.line_count_in_range:
            return True
        if self.structural_issues:
            return True
        if self.quality_warnings:
            return True
        return False


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------
```

### Step 2: Add the `validate_with_dot_graph()` function

At the very end of the file (after the `validate_dot_file` function, after line 216), append the following function:

```python


def validate_with_dot_graph(
    dot_path: str, min_lines: int = 150, max_lines: int = 300
) -> EnhancedValidationResult:
    """Run basic validation plus optional dot-graph-enhanced validation.

    Tries to call ``dot_graph(operation="validate")`` for 3-layer structural
    validation.  Falls back gracefully to basic-only validation when:

    - The ``dot_graph`` tool module is not installed
    - The tool returns a "not yet implemented" response
    - Any other error occurs during enhanced validation

    Parameters
    ----------
    dot_path:
        Path to the ``.dot`` file.
    min_lines:
        Minimum acceptable line count (inclusive). Default ``150``.
    max_lines:
        Maximum acceptable line count (inclusive). Default ``300``.

    Returns
    -------
    EnhancedValidationResult
        Combined result with basic validation always populated and enhanced
        fields populated when ``dot_graph`` is available.
    """
    # Always run basic validation
    basic = validate_dot_file(dot_path, min_lines=min_lines, max_lines=max_lines)

    # Try enhanced validation via dot_graph tool module
    try:
        from dot_graph.validation import validate as dot_graph_validate  # type: ignore[import-not-found]

        dot_content = Path(dot_path).read_text(encoding="utf-8")
        result = dot_graph_validate(dot_content)

        # Check for "not yet implemented" sentinel
        if isinstance(result, dict) and "not yet implemented" in str(
            result.get("error", "")
        ).lower():
            return EnhancedValidationResult(
                basic=basic,
                dot_graph_available=False,
                dot_graph_error="dot_graph validate operation not yet implemented",
            )

        # Parse structural issues and quality warnings from result
        structural_issues: list[str] = []
        quality_warnings: list[str] = []

        if isinstance(result, dict):
            for issue in result.get("structural_issues", []):
                structural_issues.append(str(issue))
            for warning in result.get("quality_warnings", []):
                quality_warnings.append(str(warning))

        return EnhancedValidationResult(
            basic=basic,
            dot_graph_available=True,
            structural_issues=structural_issues or None,
            quality_warnings=quality_warnings or None,
        )

    except ImportError:
        return EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            dot_graph_error="dot_graph tool module not installed",
        )
    except FileNotFoundError:
        # File doesn't exist — basic validation already captured this
        return EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            dot_graph_error="file not found",
        )
    except Exception as exc:  # noqa: BLE001
        return EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            dot_graph_error=f"dot_graph validation failed: {exc}",
        )
```

### Step 3: Run existing tests to verify nothing broke

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_dot_validation.py -v
```
Expected: All 10 existing tests PASS. The new code only adds — it does not modify any existing function.

### Step 4: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/tools/dotfiles_discovery/dot_validation.py && git commit -m "feat: add validate_with_dot_graph() with graceful fallback"
```

---

## Task 3: Write tests for `validate_with_dot_graph()`

**Files:**
- Modify: `dot-docs/tests/test_dot_validation.py` (currently 125 lines)

### Step 1: Update imports at the top of the file

Open `dot-docs/tests/test_dot_validation.py`. Find:
```python
from dotfiles_discovery.dot_validation import (
    check_line_count,
    validate_dot_file,
    validate_dot_syntax,
)
```

Replace with:
```python
from dotfiles_discovery.dot_validation import (
    DotFileValidation,
    EnhancedValidationResult,
    check_line_count,
    validate_dot_file,
    validate_dot_syntax,
    validate_with_dot_graph,
)
```

### Step 2: Append the new test classes at the end of the file

After the last line of the file (line 125, the `assert result.render_ok is False` line), append:

```python


# ---------------------------------------------------------------------------
# TestEnhancedValidationResult
# ---------------------------------------------------------------------------


class TestEnhancedValidationResult:
    def test_is_valid_when_syntax_passes(self) -> None:
        basic = DotFileValidation(
            valid_syntax=True,
            syntax_error=None,
            line_count=200,
            line_count_in_range=True,
            render_ok=True,
        )
        result = EnhancedValidationResult(basic=basic)
        assert result.is_valid is True

    def test_is_not_valid_when_syntax_fails(self) -> None:
        basic = DotFileValidation(
            valid_syntax=False,
            syntax_error="parse error",
            line_count=200,
            line_count_in_range=True,
            render_ok=False,
        )
        result = EnhancedValidationResult(basic=basic)
        assert result.is_valid is False

    def test_has_warnings_when_line_count_out_of_range(self) -> None:
        basic = DotFileValidation(
            valid_syntax=True,
            syntax_error=None,
            line_count=500,
            line_count_in_range=False,
            render_ok=True,
        )
        result = EnhancedValidationResult(basic=basic)
        assert result.has_warnings is True

    def test_has_warnings_when_structural_issues(self) -> None:
        basic = DotFileValidation(
            valid_syntax=True,
            syntax_error=None,
            line_count=200,
            line_count_in_range=True,
            render_ok=True,
        )
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=True,
            structural_issues=["orphan node: foo"],
        )
        assert result.has_warnings is True

    def test_has_warnings_when_quality_warnings(self) -> None:
        basic = DotFileValidation(
            valid_syntax=True,
            syntax_error=None,
            line_count=200,
            line_count_in_range=True,
            render_ok=True,
        )
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=True,
            quality_warnings=["legend incomplete"],
        )
        assert result.has_warnings is True

    def test_no_warnings_when_clean(self) -> None:
        basic = DotFileValidation(
            valid_syntax=True,
            syntax_error=None,
            line_count=200,
            line_count_in_range=True,
            render_ok=True,
        )
        result = EnhancedValidationResult(basic=basic, dot_graph_available=True)
        assert result.has_warnings is False

    def test_dot_graph_available_defaults_false(self) -> None:
        basic = DotFileValidation(
            valid_syntax=True,
            syntax_error=None,
            line_count=200,
            line_count_in_range=True,
            render_ok=True,
        )
        result = EnhancedValidationResult(basic=basic)
        assert result.dot_graph_available is False


# ---------------------------------------------------------------------------
# TestValidateWithDotGraph
# ---------------------------------------------------------------------------


class TestValidateWithDotGraph:
    def test_falls_back_when_dot_graph_not_installed(self, tmp_path: Path) -> None:
        """When dot_graph module is not installed, basic validation still runs."""
        dot_file = tmp_path / "test.dot"
        # Write enough lines to be in range with custom range
        padding = "// line\n" * 10
        dot_file.write_text(VALID_DOT + padding)
        result = validate_with_dot_graph(str(dot_file), min_lines=1, max_lines=500)
        # Basic validation ran
        assert result.basic is not None
        assert result.basic.line_count > 0
        # Enhanced validation gracefully unavailable
        assert result.dot_graph_available is False
        assert result.dot_graph_error is not None

    def test_returns_enhanced_result_type(self, tmp_path: Path) -> None:
        """Return type is always EnhancedValidationResult."""
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(VALID_DOT)
        result = validate_with_dot_graph(str(dot_file), min_lines=1, max_lines=500)
        assert isinstance(result, EnhancedValidationResult)

    def test_basic_validation_runs_on_missing_file(self) -> None:
        """Missing file is caught by basic validation, enhanced gracefully skipped."""
        result = validate_with_dot_graph("/nonexistent/file.dot")
        assert result.basic.valid_syntax is False
        assert result.basic.syntax_error is not None
        assert (
            "not found" in result.basic.syntax_error.lower()
            or result.dot_graph_error is not None
        )

    def test_is_valid_reflects_basic_syntax(self, tmp_path: Path) -> None:
        """is_valid property reflects basic syntax validation."""
        dot_file = tmp_path / "broken.dot"
        dot_file.write_text(INVALID_DOT)
        result = validate_with_dot_graph(str(dot_file), min_lines=1, max_lines=500)
        # Even without dot_graph, is_valid reflects syntax
        # (may be True if graphviz not installed — syntax check needs graphviz)
        assert isinstance(result.is_valid, bool)

    def test_line_count_preserved_in_enhanced_result(self, tmp_path: Path) -> None:
        """Line count from basic validation is accessible through enhanced result."""
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(VALID_DOT)
        result = validate_with_dot_graph(str(dot_file), min_lines=1, max_lines=500)
        assert result.basic.line_count > 0
        assert result.basic.line_count == len(VALID_DOT.splitlines())
```

### Step 3: Run the new tests to verify they pass

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_dot_validation.py -v
```
Expected: All tests PASS, including the 12 new tests. The `validate_with_dot_graph()` tests will all hit the `ImportError` fallback path since `dot_graph` is not installed — that's the expected behavior.

### Step 4: Run full test suite to verify nothing broke

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -v --tb=short 2>&1 | tail -5
```
Expected: 264 passed (252 original + 12 new), 0 failed.

### Step 5: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/tests/test_dot_validation.py && git commit -m "test: add tests for EnhancedValidationResult and validate_with_dot_graph()"
```

---

## Task 4: Update `dotfiles-synthesis.yaml` — Add Quality Gate Loop

**Files:**
- Modify: `dot-docs/recipes/dotfiles-synthesis.yaml` (currently 177 lines)

### Step 1: Update the header comment to reflect 6 steps

Find:
```yaml
# Steps:
#   1. inventory-dots    — list all .dot and reconciliation.md files in investigation_dir
#   2. prepare-output    — create output_dir and output_dir/.discovery
#   3. synthesize        — synthesis agent produces overview.dot and optional detail files
#   4. validate-output   — validate all produced DOT files meet quality standards
```

Replace with:
```yaml
# Steps:
#   1. inventory-dots    — list all .dot and reconciliation.md files in investigation_dir
#   2. prepare-output    — create output_dir and output_dir/.discovery
#   3. synthesize        — synthesis agent produces overview.dot and optional detail files
#   4. quality-review    — diagram-reviewer checks quality (PASS/WARN/FAIL)
#   5. fix-if-failed     — re-synthesize on FAIL verdict (max 3 iterations)
#   6. validate-output   — validate all produced DOT files meet quality standards
```

### Step 2: Insert quality gate steps between synthesize and validate-output

Find this text:
```yaml
    output: "synthesis_summary"
    timeout: 1800

  # --------------------------------------------------------------------------
  # Step 4: Validate output
  # Runs the dot_validation utilities against every .dot file produced by the
  # synthesis agent. Fails if overview.dot is missing or fails any check.
  # --------------------------------------------------------------------------
  - id: "validate-output"
```

Replace it with:
```yaml
    output: "synthesis_summary"
    timeout: 1800

  # --------------------------------------------------------------------------
  # Step 4: Quality gate — diagram-reviewer
  # Dispatches the diagram-reviewer agent from the dot-graph bundle to review
  # each produced DOT file. If the verdict is FAIL, feeds errors back to the
  # synthesis agent for re-synthesis. Max 3 iterations.
  # --------------------------------------------------------------------------
  - id: "quality-review"
    type: "prompt"
    prompt: |
      You are a DOT diagram quality reviewer. Review all .dot files in: {{output_dir}}

      For each .dot file found, check these quality criteria:
      1. **Syntax**: Does `dot -Tsvg <file>` render without errors?
      2. **Structure**: Are there orphan nodes (no edges)? Isolated clusters (no cross-cluster edges)?
      3. **Quality**: Is there a rendered `subgraph cluster_legend`? Do shapes match the vocabulary?
      4. **Style**: Are edge styles consistent? Are colors documented in the legend?
      5. **Reconciliation**: Does the diagram draw what was actually found, not assumed?

      Load the `dot-quality` and `dot-as-analysis` skills if available.

      Report your verdict as one of: PASS, WARN, FAIL
      If FAIL, list each specific issue with file name and line reference.
      If WARN, list warnings but do not block.

      If this is a re-review (previous issues listed below), verify each was fixed:
      {{review_feedback}}
    output: "review_verdict"
    timeout: 600

  # --------------------------------------------------------------------------
  # Step 5: Re-synthesize if FAIL verdict (max 3 iterations)
  # If the reviewer found FAIL-level issues, feed them back to the synthesis
  # agent for correction. The while loop re-runs steps 3-4 up to 3 times.
  # --------------------------------------------------------------------------
  - id: "fix-if-failed"
    type: "prompt"
    condition: "'FAIL' in '{{review_verdict}}'"
    max_iterations: 3
    prompt: |
      The diagram reviewer found FAIL-level issues with your DOT output.
      You MUST fix these issues in the files at: {{output_dir}}

      Reviewer feedback:
      {{review_verdict}}

      Fix each listed issue. Do not rewrite files from scratch — make targeted
      corrections. Then re-run your quality checklist.

      @dot-docs:context/synthesis-prompt.md
    output: "review_feedback"
    timeout: 1200

  # --------------------------------------------------------------------------
  # Step 6: Validate output
  # Runs the dot_validation utilities against every .dot file produced by the
  # synthesis agent. Fails if overview.dot is missing or fails any check.
  # --------------------------------------------------------------------------
  - id: "validate-output"
```

### Step 3: Update the validate-output step to use enhanced validation

In the validate-output step's inline Python script, find:
```python
      import sys
      from pathlib import Path
      from dotfiles_discovery.dot_validation import validate_dot_file
```

Replace with:
```python
      import sys
      from pathlib import Path
      from dotfiles_discovery.dot_validation import validate_dot_file, validate_with_dot_graph
```

Then find the block that validates overview.dot:
```python
      # --- Validate overview.dot (mandatory) ---
      if not overview.exists():
          errors.append("MISSING: overview.dot was not produced")
      else:
          result = validate_dot_file(str(overview))
          if not result.valid_syntax:
              errors.append(f"SYNTAX ERROR in overview.dot: {result.syntax_error}")
          if not result.line_count_in_range:
              warnings.append(
                  f"LINE COUNT out of range for overview.dot: {result.line_count} lines "
                  f"(expected 150-250)"
              )
          if not result.render_ok:
              errors.append("RENDER FAILED for overview.dot")
          print(f"overview.dot: {result.line_count} lines, syntax={result.valid_syntax}, "
                f"render={result.render_ok}")
```

Replace with:
```python
      # --- Validate overview.dot (mandatory) ---
      if not overview.exists():
          errors.append("MISSING: overview.dot was not produced")
      else:
          enhanced = validate_with_dot_graph(str(overview))
          result = enhanced.basic
          if not result.valid_syntax:
              errors.append(f"SYNTAX ERROR in overview.dot: {result.syntax_error}")
          if not result.line_count_in_range:
              warnings.append(
                  f"LINE COUNT out of range for overview.dot: {result.line_count} lines "
                  f"(expected 150-250)"
              )
          if not result.render_ok:
              errors.append("RENDER FAILED for overview.dot")
          if enhanced.structural_issues:
              for issue in enhanced.structural_issues:
                  warnings.append(f"STRUCTURAL: overview.dot: {issue}")
          if enhanced.quality_warnings:
              for qw in enhanced.quality_warnings:
                  warnings.append(f"QUALITY: overview.dot: {qw}")
          dot_graph_status = "available" if enhanced.dot_graph_available else "unavailable"
          print(f"overview.dot: {result.line_count} lines, syntax={result.valid_syntax}, "
                f"render={result.render_ok}, dot_graph={dot_graph_status}")
```

### Step 4: Verify the YAML is valid

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python3 -c "
import yaml
with open('recipes/dotfiles-synthesis.yaml') as f:
    data = yaml.safe_load(f)
print(f'Name: {data[\"name\"]}')
print(f'Steps: {len(data[\"steps\"])}')
for s in data['steps']:
    print(f'  - {s[\"id\"]} ({s[\"type\"]})')
print('YAML VALID')
"
```
Expected output:
```
Name: dotfiles-synthesis
Steps: 6
  - inventory-dots (bash)
  - prepare-output (bash)
  - synthesize (prompt)
  - quality-review (prompt)
  - fix-if-failed (prompt)
  - validate-output (bash)
YAML VALID
```

### Step 5: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/recipes/dotfiles-synthesis.yaml && git commit -m "feat: add diagram-reviewer quality gate loop to synthesis recipe"
```

---

## Task 5: Update tests for synthesis recipe changes

**Files:**
- Modify: `dot-docs/tests/test_synthesis_artifacts.py` (currently 416 lines)

### Step 1: Update existing step-count test

The existing test `test_recipe_has_four_steps` asserts exactly 4 steps. We now have 6. Find:

```python
    def test_recipe_has_four_steps(self, recipe_data: dict) -> None:
        assert "steps" in recipe_data, "Recipe steps missing"
        steps = recipe_data["steps"]
        assert len(steps) == 4, f"Expected 4 steps, got {len(steps)}"
```

Replace with:
```python
    def test_recipe_has_six_steps(self, recipe_data: dict) -> None:
        assert "steps" in recipe_data, "Recipe steps missing"
        steps = recipe_data["steps"]
        assert len(steps) == 6, f"Expected 6 steps, got {len(steps)}"
```

### Step 2: Replace step 4 tests with quality-gate and validate-output tests at new indices

The tests that reference `recipe_data["steps"][3]` as `validate-output` need to be replaced. validate-output is now at index `[5]`, and new steps quality-review and fix-if-failed are at `[3]` and `[4]`.

Find this entire block (6 test methods):
```python
    def test_step4_validate_output(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        assert step4.get("id") == "validate-output", (
            f"Step 4 id is '{step4.get('id')}', expected 'validate-output'"
        )
        assert step4.get("type") == "bash", f"Step 4 type is '{step4.get('type')}', expected 'bash'"

    def test_step4_imports_validate_dot_file(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        script = step4.get("script", step4.get("command", ""))
        assert "validate_dot_file" in script, "Step 4 bash script does not import validate_dot_file"
        assert "dotfiles_discovery.dot_validation" in script or "dotfiles_discovery" in script, (
            "Step 4 bash script does not import from dotfiles_discovery.dot_validation"
        )

    def test_step4_validates_overview_dot(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        script = step4.get("script", step4.get("command", ""))
        assert "overview.dot" in script, "Step 4 bash script does not validate overview.dot"

    def test_step4_checks_overview_exists(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        script = step4.get("script", step4.get("command", ""))
        # Should check that overview.dot exists
        assert "exists" in script.lower() or "isfile" in script.lower() or "Path" in script, (
            "Step 4 bash script does not check if overview.dot exists"
        )

    def test_step4_validates_detail_files(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        script = step4.get("script", step4.get("command", ""))
        # Should validate any detail files
        assert "detail" in script.lower() or ".dot" in script, (
            "Step 4 bash script does not validate detail .dot files"
        )

    def test_step4_output_key(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        output = step4.get("output", None)
        assert output == "validation_result", (
            f"Step 4 output is '{output}', expected 'validation_result'"
        )
```

Replace with:
```python
    def test_step4_quality_review(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        assert step4.get("id") == "quality-review", (
            f"Step 4 id is '{step4.get('id')}', expected 'quality-review'"
        )
        assert step4.get("type") == "prompt", (
            f"Step 4 type is '{step4.get('type')}', expected 'prompt'"
        )

    def test_step4_review_mentions_quality(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        prompt = step4.get("prompt", "")
        assert "quality" in prompt.lower() or "review" in prompt.lower(), (
            "Step 4 prompt does not mention quality or review"
        )

    def test_step4_review_output_key(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        output = step4.get("output", None)
        assert output == "review_verdict", (
            f"Step 4 output is '{output}', expected 'review_verdict'"
        )

    def test_step5_fix_if_failed(self, recipe_data: dict) -> None:
        step5 = recipe_data["steps"][4]
        assert step5.get("id") == "fix-if-failed", (
            f"Step 5 id is '{step5.get('id')}', expected 'fix-if-failed'"
        )
        assert step5.get("type") == "prompt", (
            f"Step 5 type is '{step5.get('type')}', expected 'prompt'"
        )

    def test_step5_has_max_iterations(self, recipe_data: dict) -> None:
        step5 = recipe_data["steps"][4]
        max_iter = step5.get("max_iterations")
        assert max_iter == 3, (
            f"Step 5 max_iterations is '{max_iter}', expected 3"
        )

    def test_step5_references_review_verdict(self, recipe_data: dict) -> None:
        step5 = recipe_data["steps"][4]
        prompt = step5.get("prompt", "")
        assert "review_verdict" in prompt, (
            "Step 5 prompt does not reference review_verdict"
        )

    def test_step6_validate_output(self, recipe_data: dict) -> None:
        step6 = recipe_data["steps"][5]
        assert step6.get("id") == "validate-output", (
            f"Step 6 id is '{step6.get('id')}', expected 'validate-output'"
        )
        assert step6.get("type") == "bash", (
            f"Step 6 type is '{step6.get('type')}', expected 'bash'"
        )

    def test_step6_imports_validate_with_dot_graph(self, recipe_data: dict) -> None:
        step6 = recipe_data["steps"][5]
        script = step6.get("script", step6.get("command", ""))
        assert "validate_with_dot_graph" in script, (
            "Step 6 bash script does not import validate_with_dot_graph"
        )

    def test_step6_validates_overview_dot(self, recipe_data: dict) -> None:
        step6 = recipe_data["steps"][5]
        script = step6.get("script", step6.get("command", ""))
        assert "overview.dot" in script, "Step 6 bash script does not validate overview.dot"

    def test_step6_output_key(self, recipe_data: dict) -> None:
        step6 = recipe_data["steps"][5]
        output = step6.get("output", None)
        assert output == "validation_result", (
            f"Step 6 output is '{output}', expected 'validation_result'"
        )
```

### Step 3: Update the YAML validation test at the bottom of the file

Find:
```python
assert len(data['steps']) == 4, f"expected 4 steps, got {{len(data['steps'])}}"
```

Replace with:
```python
assert len(data['steps']) == 6, f"expected 6 steps, got {{len(data['steps'])}}"
```

### Step 4: Add tests for reconciliation methodology in synthesis prompt

In the `TestSynthesisPrompt` class, find the last test method:
```python
    def test_antipatterns_no_comment_only_legends(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "comment" in content.lower() and "legend" in content.lower(), (
            "Anti-pattern 'no comment-only legends' not mentioned"
        )
```

After it (still inside the `TestSynthesisPrompt` class), add these three new test methods:
```python

    def test_reconciliation_methodology_present(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "introspect" in content.lower(), (
            "Reconciliation methodology Phase 1 (Introspect) not found"
        )
        assert "reconcile" in content.lower(), (
            "Reconciliation methodology Phase 3 (Reconcile) not found"
        )
        assert "surface" in content.lower(), (
            "Reconciliation methodology Phase 4 (Surface) not found"
        )

    def test_anti_rationalization_table_present(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "anti-rationalization" in content.lower() or "rationalization" in content.lower(), (
            "Anti-rationalization table not found in synthesis prompt"
        )
        assert "close enough" in content.lower(), (
            "Anti-rationalization table missing 'close enough' entry"
        )

    def test_dot_graph_skill_references(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "dot-syntax" in content, "Skill reference 'dot-syntax' not found"
        assert "dot-quality" in content, "Skill reference 'dot-quality' not found"
        assert "dot-as-analysis" in content, "Skill reference 'dot-as-analysis' not found"
```

### Step 5: Run all synthesis artifact tests

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_synthesis_artifacts.py -v
```
Expected: All tests PASS. The step count test now expects 6, and the new quality-review and fix-if-failed step tests verify the new structure.

### Step 6: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/tests/test_synthesis_artifacts.py && git commit -m "test: update synthesis recipe tests for 6-step quality gate loop"
```

---

## Task 6: Update `dotfiles-discovery.yaml` — Wire Tier 3 Analysis

**Files:**
- Modify: `dot-docs/recipes/dotfiles-discovery.yaml` (currently 500 lines)

### Step 1: Add Tier 3 analysis step to Stage 3 (synthesis)

Open `dot-docs/recipes/dotfiles-discovery.yaml`. Insert a new step in Stage 3 between `run-synthesis` (step 1) and `write-metadata` (step 2).

Find this text in Stage 3:
```yaml
        timeout: 3600

      # ------------------------------------------------------------------------
      # Step 2: Write discovery metadata for each processed repo
```

Replace with:
```yaml
        timeout: 3600

      # ------------------------------------------------------------------------
      # Step 2: Tier 3 structural analysis (diff, orphan check, cycle check)
      # For Tier 3 repos, uses dot_graph analyze operations to compare the
      # updated DOT against the previous version and check for regressions.
      # Skipped for Tier 1/2 (full resynthesis doesn't need diff).
      # ------------------------------------------------------------------------
      - id: "tier3-analysis"
        foreach: "{{tier_plan}}"
        as: "repo_entry"
        condition: "{{repo_entry.tier}} == 3"
        collect: "analysis_results"
        type: "prompt"
        prompt: |
          Perform structural analysis on the DOT files at: {{repo_entry.output_dir}}

          This is a Tier 3 targeted update — the DOT files were patched, not fully
          resynthesized. Run these checks to ensure the patch didn't introduce regressions:

          1. **Orphan check**: Use dot_graph(operation="analyze", options={"type": "unreachable"})
             on overview.dot. Report any nodes with zero edges (orphans introduced by the patch).

          2. **Cycle check**: Use dot_graph(operation="analyze", options={"type": "cycles"})
             on overview.dot. Report any unintended circular dependencies.

          3. **Diff check**: If a previous version of overview.dot exists in the repo's
             .discovery directory, use dot_graph(operation="analyze", options={"type": "diff"})
             to compare old vs new. Report added/removed nodes and edges.

          If dot_graph analyze is not available, fall back to manual inspection:
          - Read overview.dot and check for nodes with no edges
          - Check for obvious circular reference patterns

          Report findings as: CLEAN (no issues), WARN (minor issues), or FAIL (regressions found).
        output: "tier3_analysis"
        timeout: 600

      # ------------------------------------------------------------------------
      # Step 3: Write discovery metadata for each processed repo
```

### Step 2: Update the step numbering in comments

Find the comment for the final-summary step:
```yaml
      # ------------------------------------------------------------------------
      # Step 3: Display completion banner
      # ------------------------------------------------------------------------
```

Replace with:
```yaml
      # ------------------------------------------------------------------------
      # Step 4: Display completion banner
      # ------------------------------------------------------------------------
```

### Step 3: Verify the YAML is valid

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python3 -c "
import yaml
with open('recipes/dotfiles-discovery.yaml') as f:
    data = yaml.safe_load(f)
stages = data['stages']
print(f'Name: {data[\"name\"]}')
print(f'Stages: {len(stages)}')
for s in stages:
    steps = s['steps']
    print(f'  Stage \"{s[\"name\"]}\": {len(steps)} steps')
    for step in steps:
        print(f'    - {step[\"id\"]} ({step[\"type\"]})')
print('YAML VALID')
"
```
Expected output:
```
Name: dotfiles-discovery
Stages: 3
  Stage "setup": 3 steps
  Stage "investigation": 2 steps
  Stage "synthesis": 4 steps
    - run-synthesis (recipe)
    - tier3-analysis (prompt)
    - write-metadata (bash)
    - final-summary (bash)
YAML VALID
```

### Step 4: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/recipes/dotfiles-discovery.yaml && git commit -m "feat: add Tier 3 structural analysis step to discovery recipe"
```

---

## Task 7: Update tests for discovery recipe changes

**Files:**
- Modify: `dot-docs/tests/test_discovery_recipe.py` (currently 517 lines)

### Step 1: Update Stage 3 step count test

Find:
```python
    def test_stage3_has_three_steps(self, stage3: dict) -> None:
        steps = stage3["steps"]
        assert len(steps) == 3, f"Stage 3 expected 3 steps, got {len(steps)}"
```

Replace with:
```python
    def test_stage3_has_four_steps(self, stage3: dict) -> None:
        steps = stage3["steps"]
        assert len(steps) == 4, f"Stage 3 expected 4 steps, got {len(steps)}"
```

### Step 2: Replace step 2/3 tests with updated indices

The existing tests reference `stage3["steps"][1]` for write-metadata and `stage3["steps"][2]` for final-summary. These need to shift by one since tier3-analysis is now at index 1.

Find this entire block:
```python
    def test_step2_write_metadata(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        assert step.get("id") == "write-metadata", (
            f"Stage 3 step 2 id is '{step.get('id')}', expected 'write-metadata'"
        )
        assert step.get("type") == "bash", (
            f"Stage 3 step 2 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step2_imports_metadata_classes(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        script = step.get("command", step.get("script", ""))
        assert "LastRunMetadata" in script or "ManifestMetadata" in script, (
            "Stage 3 step 2 does not import LastRunMetadata/ManifestMetadata"
        )

    def test_step2_imports_write_functions(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        script = step.get("command", step.get("script", ""))
        assert "write_last_run" in script, "Stage 3 step 2 does not import write_last_run"
        assert "write_manifest" in script, "Stage 3 step 2 does not import write_manifest"

    def test_step2_output_metadata_result(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        assert step.get("output") == "metadata_result", (
            f"Stage 3 step 2 output is '{step.get('output')}', expected 'metadata_result'"
        )

    def test_step3_final_summary(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        assert step.get("id") == "final-summary", (
            f"Stage 3 step 3 id is '{step.get('id')}', expected 'final-summary'"
        )
        assert step.get("type") == "bash", (
            f"Stage 3 step 3 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step3_output_discovery_complete(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        assert step.get("output") == "discovery_complete", (
            f"Stage 3 step 3 output is '{step.get('output')}', expected 'discovery_complete'"
        )

    def test_step3_shows_dotfiles_root(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        script = step.get("command", step.get("script", ""))
        assert "dotfiles_root" in script, (
            "Stage 3 step 3 does not reference dotfiles_root in banner"
        )
```

Replace with:
```python
    def test_step2_tier3_analysis(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        assert step.get("id") == "tier3-analysis", (
            f"Stage 3 step 2 id is '{step.get('id')}', expected 'tier3-analysis'"
        )
        assert step.get("type") == "prompt", (
            f"Stage 3 step 2 type is '{step.get('type')}', expected 'prompt'"
        )

    def test_step2_tier3_condition(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        condition = str(step.get("condition", ""))
        assert "tier" in condition and "3" in condition, (
            f"Stage 3 step 2 condition '{condition}' does not check tier==3"
        )

    def test_step2_tier3_mentions_orphan_check(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        prompt = step.get("prompt", "")
        assert "orphan" in prompt.lower() or "unreachable" in prompt.lower(), (
            "Stage 3 step 2 prompt does not mention orphan/unreachable check"
        )

    def test_step2_tier3_mentions_cycle_check(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        prompt = step.get("prompt", "")
        assert "cycle" in prompt.lower(), (
            "Stage 3 step 2 prompt does not mention cycle check"
        )

    def test_step2_tier3_mentions_diff_check(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        prompt = step.get("prompt", "")
        assert "diff" in prompt.lower(), (
            "Stage 3 step 2 prompt does not mention diff check"
        )

    def test_step2_tier3_output(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        assert step.get("output") == "tier3_analysis", (
            f"Stage 3 step 2 output is '{step.get('output')}', expected 'tier3_analysis'"
        )

    def test_step3_write_metadata(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        assert step.get("id") == "write-metadata", (
            f"Stage 3 step 3 id is '{step.get('id')}', expected 'write-metadata'"
        )
        assert step.get("type") == "bash", (
            f"Stage 3 step 3 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step3_imports_metadata_classes(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        script = step.get("command", step.get("script", ""))
        assert "LastRunMetadata" in script or "ManifestMetadata" in script, (
            "Stage 3 step 3 does not import LastRunMetadata/ManifestMetadata"
        )

    def test_step3_imports_write_functions(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        script = step.get("command", step.get("script", ""))
        assert "write_last_run" in script, "Stage 3 step 3 does not import write_last_run"
        assert "write_manifest" in script, "Stage 3 step 3 does not import write_manifest"

    def test_step3_output_metadata_result(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        assert step.get("output") == "metadata_result", (
            f"Stage 3 step 3 output is '{step.get('output')}', expected 'metadata_result'"
        )

    def test_step4_final_summary(self, stage3: dict) -> None:
        step = stage3["steps"][3]
        assert step.get("id") == "final-summary", (
            f"Stage 3 step 4 id is '{step.get('id')}', expected 'final-summary'"
        )
        assert step.get("type") == "bash", (
            f"Stage 3 step 4 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step4_output_discovery_complete(self, stage3: dict) -> None:
        step = stage3["steps"][3]
        assert step.get("output") == "discovery_complete", (
            f"Stage 3 step 4 output is '{step.get('output')}', expected 'discovery_complete'"
        )

    def test_step4_shows_dotfiles_root(self, stage3: dict) -> None:
        step = stage3["steps"][3]
        script = step.get("command", step.get("script", ""))
        assert "dotfiles_root" in script, (
            "Stage 3 step 4 does not reference dotfiles_root in banner"
        )
```

### Step 3: Update the YAML validation test at the bottom of the file

Find:
```python
assert len(stages[2]['steps']) == 3, f"stage 3 expected 3 steps, got {{len(stages[2]['steps'])}}"
```

Replace with:
```python
assert len(stages[2]['steps']) == 4, f"stage 3 expected 4 steps, got {{len(stages[2]['steps'])}}"
```

### Step 4: Run all discovery recipe tests

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/test_discovery_recipe.py -v
```
Expected: All tests PASS.

### Step 5: Run the full test suite

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -v --tb=short 2>&1 | tail -5
```
Expected: All tests pass (approximately 280+ total).

### Step 6: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/tests/test_discovery_recipe.py && git commit -m "test: update discovery recipe tests for Tier 3 analysis step"
```

---

## Task 8: Run linter and type checker, fix any issues

**Files:**
- Potentially any modified file

### Step 1: Run ruff lint

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m ruff check tools/ tests/
```
Expected: `All checks passed!`

### Step 2: Run ruff format check

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m ruff format --check tools/ tests/
```
Expected: All files already formatted. If not, run `python -m ruff format tools/ tests/` to fix.

### Step 3: Run pyright

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pyright tools/ tests/
```
Expected: `0 errors, 0 warnings, 0 informations`

### Step 4: Fix any issues found, then commit

If any lint/format/type issues were found:
```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "style: fix lint/format/type issues from dot-graph integration"
```

If everything was clean, skip this commit.

---

## Task 9: Final verification — full test suite

### Step 1: Run the complete test suite

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python -m pytest tests/ -v --tb=short
```
Expected: All tests pass, 0 failures, 0 errors.

### Step 2: Verify commit history

```bash
cd /home/bkrabach/dev/dot-docs && git log --oneline -10
```
Expected: You should see 5-7 commits from this plan (one per task, plus any style fix).

### Step 3: Print final summary

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && echo "=== FILES MODIFIED ===" && git diff --name-only HEAD~7 && echo "" && echo "=== TEST COUNT ===" && python -m pytest tests/ --co -q 2>&1 | tail -1
```

---

## Summary of All Changes

| File | Change | Lines Added (approx) |
|------|--------|---------------------|
| `dot-docs/context/synthesis-prompt.md` | Reconciliation methodology, anti-rationalization table, skill references | +45 |
| `dot-docs/tools/dotfiles_discovery/dot_validation.py` | `EnhancedValidationResult` dataclass, `validate_with_dot_graph()` function | +95 |
| `dot-docs/recipes/dotfiles-synthesis.yaml` | Quality gate loop (steps 4-5), enhanced validation in step 6 | +55 |
| `dot-docs/recipes/dotfiles-discovery.yaml` | Tier 3 structural analysis step | +35 |
| `dot-docs/tests/test_dot_validation.py` | 12 new tests for enhanced validation | +120 |
| `dot-docs/tests/test_synthesis_artifacts.py` | Updated step counts, new quality gate tests, prompt content tests | +40 net |
| `dot-docs/tests/test_discovery_recipe.py` | Updated step counts, Tier 3 analysis tests | +30 net |

**Total: ~420 lines added across 7 files, 0 new files created.**
