# COE Operational Fixes Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Add three COE-recommended operational fixes to the dot-docs core engine: provenance attributes in DOT output, content-hash deduplication before commit, and stale repo reconciliation in Team Sweep.

**Architecture:** The core engine (`dotfiles-investigate.yaml` → `dotfiles-synthesis.yaml`) gets provenance data threaded through from `build-manifest` to the synthesis agent prompt. Two new pure-function Python modules (`content_hash.py`, `reconciliation.py`) are added to `tools/dotfiles_discovery/` following the existing module pattern, then wired into `dotfiles-discovery.yaml` as new bash steps.

**Tech Stack:** Python 3.12, pytest, PyYAML, YAML recipe format (Amplifier)

**Working directory for all commands:** `/home/bkrabach/dev/dot-docs/dot-docs`

---

## Pre-flight

Before starting, verify the test suite baseline:

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/ -q
```

Note any pre-existing failures — they are not your responsibility to fix. Only tests you introduce in this plan must be green.

---

## Task 1: Fix 1 — Write failing tests for synthesis recipe provenance

**Files:**
- Modify: `tests/test_synthesis_artifacts.py` (append new class at the end)

**Step 1: Append the new test class to `tests/test_synthesis_artifacts.py`**

Read the current end of the file first, then append after line 649:

```python


class TestSynthesisRecipeProvenance:
    """Verify dotfiles-synthesis.yaml carries source_sha through to the synthesize prompt.

    RED phase: these tests fail until Fix 1 is implemented.
    """

    @pytest.fixture
    def recipe_data(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-synthesis.yaml").read_text()
        return yaml.safe_load(content)

    def test_context_has_source_sha(self, recipe_data: dict) -> None:
        context = recipe_data.get("context", {})
        assert "source_sha" in context, (
            "dotfiles-synthesis.yaml context must have a 'source_sha' key"
        )

    def test_synthesize_prompt_mentions_source_sha(self, recipe_data: dict) -> None:
        steps = recipe_data.get("steps", [])
        synth = next((s for s in steps if s.get("id") == "synthesize"), None)
        assert synth is not None, "synthesize step not found in dotfiles-synthesis.yaml"
        prompt = synth.get("prompt", "")
        assert "source_sha" in prompt, (
            "synthesize step prompt must mention 'source_sha' so the agent includes it "
            "as a DOT graph attribute"
        )

    def test_synthesize_prompt_mentions_generated_at(self, recipe_data: dict) -> None:
        steps = recipe_data.get("steps", [])
        synth = next((s for s in steps if s.get("id") == "synthesize"), None)
        assert synth is not None, "synthesize step not found in dotfiles-synthesis.yaml"
        prompt = synth.get("prompt", "")
        assert "generated_at" in prompt, (
            "synthesize step prompt must mention 'generated_at' so the agent includes it "
            "as a DOT graph attribute"
        )

    def test_synthesize_prompt_shows_provenance_format(self, recipe_data: dict) -> None:
        steps = recipe_data.get("steps", [])
        synth = next((s for s in steps if s.get("id") == "synthesize"), None)
        assert synth is not None, "synthesize step not found in dotfiles-synthesis.yaml"
        prompt = synth.get("prompt", "")
        # Agent must see the DOT syntax it should produce
        assert "graph [" in prompt, (
            "synthesize step prompt must show the DOT 'graph [...]' attribute syntax "
            "for the agent to replicate"
        )
```

**Step 2: Run to verify tests fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_synthesis_artifacts.py::TestSynthesisRecipeProvenance -v
```

Expected: 4 FAILED — `source_sha` not yet in synthesis recipe context or prompt.

---

## Task 2: Fix 1 — Implement synthesis recipe provenance

**Files:**
- Modify: `recipes/dotfiles-synthesis.yaml` (context section + synthesize step prompt)
- Modify: `recipes/dotfiles-investigate.yaml` (build-manifest step)
- Modify: `recipes/dotfiles-discovery.yaml` (run-synthesis context)

**Step 1: Add `source_sha` to `dotfiles-synthesis.yaml` context**

In `recipes/dotfiles-synthesis.yaml`, find the `context:` block (currently around line 37–42):

```yaml
context:
  investigation_dir: ""  # required — path to investigation workspace containing raw .dot files
  repo_path: ""          # required — absolute path to the repository being documented
  output_dir: ""         # required — where to write overview.dot and detail files
  topics: []             # required — list of topics investigated (e.g. ["module_architecture"])
  review_feedback: ""    # internal — populated by quality-review step on re-reviews
```

Replace with:

```yaml
context:
  investigation_dir: ""  # required — path to investigation workspace containing raw .dot files
  repo_path: ""          # required — absolute path to the repository being documented
  output_dir: ""         # required — where to write overview.dot and detail files
  topics: []             # required — list of topics investigated (e.g. ["module_architecture"])
  review_feedback: ""    # internal — populated by quality-review step on re-reviews
  source_sha: ""         # optional — git SHA of the source repo at investigation time
```

**Step 2: Update the `synthesize` step prompt to include provenance instruction**

In `recipes/dotfiles-synthesis.yaml`, find the `synthesize` step prompt (starts around line 97):

```yaml
    prompt: |
      You are synthesizing DOT graph documentation for the repository at: {{repo_path}}

      Investigation workspace: {{investigation_dir}}
      Output directory: {{output_dir}}
      Topics investigated: {{topics}}

      Inventory of files available for synthesis:
      {{dot_inventory}}

      @dot-docs:context/synthesis-prompt.md
```

Replace with:

```yaml
    prompt: |
      You are synthesizing DOT graph documentation for the repository at: {{repo_path}}

      Investigation workspace: {{investigation_dir}}
      Output directory: {{output_dir}}
      Topics investigated: {{topics}}
      Source SHA: {{source_sha}}

      Inventory of files available for synthesis:
      {{dot_inventory}}

      ## Provenance Attributes (Required)
      Every DOT file you produce MUST include provenance as graph-level attributes.
      Add this line immediately after the opening `digraph {` or `graph {` line:

          graph [source_sha="{{source_sha}}", generated_at="<current ISO 8601 timestamp>"]

      Replace `<current ISO 8601 timestamp>` with the actual UTC time when you write the file
      (format: YYYY-MM-DDTHH:MM:SSZ). This is mandatory — reviewers will fail any DOT file
      that omits these attributes.

      @dot-docs:context/synthesis-prompt.md
```

**Step 3: Add `source_sha` capture to `build-manifest` in `dotfiles-investigate.yaml`**

In `recipes/dotfiles-investigate.yaml`, find the `build-manifest` python script section (around line 354). The manifest dict currently reads:

```python
      manifest = {
          "investigation_dir": investigation_dir,
          "tier": tier,
          "topics": topics,
          "reconciliation": reconciliation,
          "wave1_dir": str(Path(investigation_dir) / "wave-1"),
      }
```

Replace with:

```python
      import subprocess
      source_sha_result = subprocess.run(
          ["git", "rev-parse", "HEAD"],
          cwd="{{repo_path}}",
          capture_output=True,
          text=True,
      )
      source_sha = source_sha_result.stdout.strip() if source_sha_result.returncode == 0 else ""

      manifest = {
          "investigation_dir": investigation_dir,
          "tier": tier,
          "topics": topics,
          "reconciliation": reconciliation,
          "wave1_dir": str(Path(investigation_dir) / "wave-1"),
          "source_sha": source_sha,
      }
```

> **Note:** `subprocess` is already imported at the top of the same heredoc script (line 318). Do not add a second `import subprocess` — instead, move the `source_sha` block to after the existing import by placing it just before the `manifest = {` line.

**Step 4: Add `source_sha` to `run-synthesis` context in `dotfiles-discovery.yaml`**

In `recipes/dotfiles-discovery.yaml`, find the `run-synthesis` step (around line 398–409):

```yaml
      - id: "run-synthesis"
        foreach: "{{tier_filters.synthesis}}"
        as: "repo_entry"
        collect: "synthesis_results"
        type: "recipe"
        recipe: "/home/bkrabach/dev/dot-docs/dot-docs/recipes/dotfiles-synthesis.yaml"
        context:
          investigation_dir: "{{repo_entry.output_dir}}/.investigation"
          repo_path: "{{repo_entry.repo_path}}"
          output_dir: "{{repo_entry.output_dir}}"
          topics: "{{investigation_results}}"
        timeout: 3600
```

Replace the `context:` block with:

```yaml
        context:
          investigation_dir: "{{repo_entry.output_dir}}/.investigation"
          repo_path: "{{repo_entry.repo_path}}"
          output_dir: "{{repo_entry.output_dir}}"
          topics: "{{investigation_results}}"
          source_sha: "{{repo_entry.current_commit}}"
```

> **Note:** `current_commit` is already set on every `tier_plan` entry in the `detect-tiers` bash step — it comes from `git rev-parse HEAD` run there. No additional recipe changes are needed to populate it.

**Step 5: Run tests to verify Fix 1 passes**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_synthesis_artifacts.py::TestSynthesisRecipeProvenance -v
```

Expected: 4 PASSED.

**Step 6: Commit Fix 1**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
git add recipes/dotfiles-synthesis.yaml recipes/dotfiles-investigate.yaml recipes/dotfiles-discovery.yaml tests/test_synthesis_artifacts.py
git commit -m "feat: add provenance attributes (source_sha, generated_at) to DOT synthesis"
```

---

## Task 3: Fix 2 — Write failing tests for `content_hash.py`

**Files:**
- Create: `tests/test_content_hash.py`

**Step 1: Create `tests/test_content_hash.py`**

```python
"""Tests for tools/dotfiles_discovery/content_hash.py.

RED phase: these tests fail until content_hash.py is implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

BUNDLE_ROOT = Path(__file__).parent.parent


class TestImport:
    """Verify the module can be imported."""

    def test_module_importable(self) -> None:
        from dotfiles_discovery import content_hash  # noqa: F401

    def test_compute_dot_hash_importable(self) -> None:
        from dotfiles_discovery.content_hash import compute_dot_hash  # noqa: F401

    def test_should_update_importable(self) -> None:
        from dotfiles_discovery.content_hash import should_update  # noqa: F401


class TestComputeDotHash:
    """Verify compute_dot_hash produces stable, timestamp-insensitive hashes."""

    def test_returns_hex_string(self) -> None:
        from dotfiles_discovery.content_hash import compute_dot_hash

        result = compute_dot_hash('digraph G { a -> b; }')
        assert isinstance(result, str), "compute_dot_hash must return a string"
        assert len(result) == 64, "SHA-256 hex digest must be 64 characters"

    def test_identical_content_produces_identical_hash(self) -> None:
        from dotfiles_discovery.content_hash import compute_dot_hash

        content = 'digraph G {\n  graph [label="Test"];\n  a -> b;\n}'
        assert compute_dot_hash(content) == compute_dot_hash(content), (
            "Same content must always hash to the same value"
        )

    def test_different_generated_at_produces_same_hash(self) -> None:
        from dotfiles_discovery.content_hash import compute_dot_hash

        base = 'digraph G {\n  graph [source_sha="abc123", generated_at="{ts}"];\n  a -> b;\n}'
        h1 = compute_dot_hash(base.format(ts="2026-01-01T00:00:00Z"))
        h2 = compute_dot_hash(base.format(ts="2026-06-15T12:34:56Z"))
        assert h1 == h2, (
            "Different generated_at timestamps must not affect the hash — "
            "only semantic content changes should produce a different hash"
        )

    def test_different_source_sha_produces_different_hash(self) -> None:
        from dotfiles_discovery.content_hash import compute_dot_hash

        h1 = compute_dot_hash('digraph G {\n  graph [source_sha="aaa"];\n  a -> b;\n}')
        h2 = compute_dot_hash('digraph G {\n  graph [source_sha="bbb"];\n  a -> b;\n}')
        assert h1 != h2, (
            "Different source_sha values must produce different hashes"
        )

    def test_different_graph_structure_produces_different_hash(self) -> None:
        from dotfiles_discovery.content_hash import compute_dot_hash

        h1 = compute_dot_hash('digraph G { a -> b; }')
        h2 = compute_dot_hash('digraph G { a -> c; }')
        assert h1 != h2, (
            "Different graph structure must produce different hashes"
        )

    def test_empty_content_does_not_raise(self) -> None:
        from dotfiles_discovery.content_hash import compute_dot_hash

        result = compute_dot_hash("")
        assert isinstance(result, str), "Empty content must still return a string hash"


class TestShouldUpdate:
    """Verify should_update correctly compares new content against existing file."""

    def test_missing_file_returns_true(self, tmp_path: Path) -> None:
        from dotfiles_discovery.content_hash import should_update

        nonexistent = tmp_path / "overview.dot"
        assert should_update("digraph G { a -> b; }", nonexistent) is True, (
            "should_update must return True when the existing file does not exist"
        )

    def test_identical_content_returns_false(self, tmp_path: Path) -> None:
        from dotfiles_discovery.content_hash import should_update

        content = 'digraph G {\n  graph [source_sha="abc"];\n  a -> b;\n}'
        existing = tmp_path / "overview.dot"
        existing.write_text(content)
        assert should_update(content, existing) is False, (
            "should_update must return False when content is semantically identical"
        )

    def test_same_content_different_timestamp_returns_false(self, tmp_path: Path) -> None:
        from dotfiles_discovery.content_hash import should_update

        template = 'digraph G {{\n  graph [source_sha="abc", generated_at="{ts}"];\n  a -> b;\n}}'
        existing = tmp_path / "overview.dot"
        existing.write_text(template.format(ts="2026-01-01T00:00:00Z"))
        new_content = template.format(ts="2026-06-15T12:34:56Z")
        assert should_update(new_content, existing) is False, (
            "should_update must return False when only the timestamp changed"
        )

    def test_changed_structure_returns_true(self, tmp_path: Path) -> None:
        from dotfiles_discovery.content_hash import should_update

        existing = tmp_path / "overview.dot"
        existing.write_text('digraph G { a -> b; }')
        assert should_update('digraph G { a -> c; }', existing) is True, (
            "should_update must return True when graph structure changed"
        )
```

**Step 2: Run to verify tests fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_content_hash.py -v
```

Expected: all FAILED with `ModuleNotFoundError: No module named 'dotfiles_discovery.content_hash'`.

---

## Task 4: Fix 2 — Implement `content_hash.py`

**Files:**
- Create: `tools/dotfiles_discovery/content_hash.py`

**Step 1: Create `tools/dotfiles_discovery/content_hash.py`**

```python
"""Content hash utilities for dotfiles discovery.

Computes semantic hashes of DOT file content, stripping volatile attributes
like generated_at timestamps so that only meaningful content changes trigger
a re-commit to the target repository.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


def compute_dot_hash(content: str) -> str:
    """Compute a SHA-256 hash of DOT content with timestamps stripped.

    Strips the ``generated_at`` attribute value before hashing so that
    re-runs with identical graph structure but different timestamps
    produce the same hash.

    Parameters
    ----------
    content:
        Raw DOT file content as a string.

    Returns
    -------
    str
        Hex-encoded SHA-256 digest (64 characters).
    """
    # Normalize generated_at="<any value>" → generated_at="" so timestamps
    # don't affect the hash. The key is preserved; only the value is erased.
    normalized = re.sub(r'generated_at="[^"]*"', 'generated_at=""', content)
    return hashlib.sha256(normalized.encode()).hexdigest()


def should_update(new_content: str, existing_path: Path) -> bool:
    """Determine whether the target file should be updated.

    Compares the semantic content hash of ``new_content`` against the
    existing file at ``existing_path``. Returns ``True`` if the file is
    missing or if the content has meaningfully changed.

    Parameters
    ----------
    new_content:
        Newly generated DOT content.
    existing_path:
        Path to the existing file on disk (may not exist).

    Returns
    -------
    bool
        ``True`` if the file should be written; ``False`` if content is
        semantically equivalent to what is already on disk.
    """
    if not existing_path.exists():
        return True
    existing_content = existing_path.read_text()
    return compute_dot_hash(new_content) != compute_dot_hash(existing_content)
```

**Step 2: Run tests to verify implementation passes**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_content_hash.py -v
```

Expected: all PASSED.

---

## Task 5: Fix 2 — Wire `check-content-hash` step into discovery recipe

**Files:**
- Modify: `tests/test_discovery_recipe.py` (append new class)
- Modify: `recipes/dotfiles-discovery.yaml` (add step to synthesis stage)

**Step 1: Append a new test class to `tests/test_discovery_recipe.py`**

Read the current end of the file (currently line 842), then append:

```python


class TestDiscoveryContentHashStep:
    """Verify dotfiles-discovery.yaml has a check-content-hash step in the synthesis stage.

    RED phase: fails until the step is added.
    """

    @pytest.fixture
    def recipe_data(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        return yaml.safe_load(content)

    @staticmethod
    def _get_all_steps(recipe_data: dict) -> list:
        steps: list = []
        if "steps" in recipe_data:
            steps.extend(recipe_data["steps"])
        for stage in recipe_data.get("stages", []):
            steps.extend(stage.get("steps", []))
        return steps

    @staticmethod
    def _get_step(recipe_data: dict, step_id: str) -> dict | None:
        for step in TestDiscoveryContentHashStep._get_all_steps(recipe_data):
            if step.get("id") == step_id:
                return step
        return None

    def test_has_check_content_hash_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "check-content-hash")
        assert step is not None, (
            "dotfiles-discovery.yaml must have a step with id: check-content-hash"
        )

    def test_check_content_hash_is_bash(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "check-content-hash")
        assert step is not None, "check-content-hash step not found"
        assert step.get("type") == "bash", (
            "check-content-hash step must be type: bash"
        )

    def test_check_content_hash_references_content_hash_module(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "check-content-hash")
        assert step is not None, "check-content-hash step not found"
        command = step.get("command", "")
        assert "content_hash" in command, (
            "check-content-hash step command must reference the content_hash module"
        )

    def test_check_content_hash_references_should_update(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "check-content-hash")
        assert step is not None, "check-content-hash step not found"
        command = step.get("command", "")
        assert "should_update" in command, (
            "check-content-hash step command must call should_update()"
        )

    def test_check_content_hash_after_run_synthesis(self, recipe_data: dict) -> None:
        all_steps = self._get_all_steps(recipe_data)
        ids = [s.get("id") for s in all_steps]
        assert "run-synthesis" in ids, "run-synthesis step not found"
        assert "check-content-hash" in ids, "check-content-hash step not found"
        assert ids.index("run-synthesis") < ids.index("check-content-hash"), (
            "check-content-hash must come after run-synthesis"
        )
```

**Step 2: Run to verify tests fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_discovery_recipe.py::TestDiscoveryContentHashStep -v
```

Expected: 5 FAILED — step does not exist yet.

**Step 3: Add `check-content-hash` step to `dotfiles-discovery.yaml`**

In `recipes/dotfiles-discovery.yaml`, in the `synthesis` stage, find the `tier3-analysis` step (after `run-synthesis`). Add the new step immediately after `run-synthesis` and before `tier3-analysis`:

```yaml
      # ------------------------------------------------------------------------
      # Step 1b: Content-hash check — skip logging spurious diffs
      # Compares each newly written overview.dot against its stored hash.
      # Logs whether content changed (future commit steps can check this).
      # ------------------------------------------------------------------------
      - id: "check-content-hash"
        type: "bash"
        on_error: continue
        command: |
          python3 << 'EOF'
          import sys
          import json
          import ast
          from pathlib import Path

          sys.path.insert(0, "{{bundle_root}}/tools")
          from dotfiles_discovery.content_hash import compute_dot_hash, should_update

          synthesis_repos_raw = '{{tier_filters.synthesis}}'
          try:
              synthesis_repos = json.loads(synthesis_repos_raw)
          except Exception:
              synthesis_repos = ast.literal_eval(synthesis_repos_raw)

          results = []
          for repo_entry in synthesis_repos:
              output_dir = Path(repo_entry.get("output_dir", ""))
              overview = output_dir / "overview.dot"
              hash_file = output_dir / ".discovery" / "content-hash.txt"

              if not overview.exists():
                  results.append({"repo": repo_entry.get("repo"), "status": "no-output"})
                  continue

              new_content = overview.read_text()
              new_hash = compute_dot_hash(new_content)

              if hash_file.exists():
                  old_hash = hash_file.read_text().strip()
                  changed = new_hash != old_hash
              else:
                  changed = True

              # Persist hash for next run
              hash_file.parent.mkdir(parents=True, exist_ok=True)
              hash_file.write_text(new_hash)

              status = "changed" if changed else "unchanged"
              results.append({"repo": repo_entry.get("repo"), "status": status})
              print(f"[content-hash] {repo_entry.get('repo')}: {status}")

          summary = {
              "changed": sum(1 for r in results if r["status"] == "changed"),
              "unchanged": sum(1 for r in results if r["status"] == "unchanged"),
              "no_output": sum(1 for r in results if r["status"] == "no-output"),
          }
          print(f"\nContent hash summary: {json.dumps(summary)}")
          EOF
        output: "content_hash_results"
        timeout: 60
```

> **Placement:** This step goes in the `synthesis` stage's `steps` list, directly after `run-synthesis` and before `tier3-analysis`. The YAML stage block for `synthesis` starts at the line `- name: "synthesis"` (around line 393).

> **Note on `bundle_root`:** The command uses `sys.path.insert(0, "{{bundle_root}}/tools")` — replace `{{bundle_root}}` with the hardcoded absolute path `/home/bkrabach/dev/dot-docs/dot-docs` if the `bundle_root` context variable is not already defined in the recipe. Check whether `dotfiles_root` can be used to derive the tools path, or hard-code the absolute path as the other recipe steps already do for recipe paths.

**Step 4: Run tests to verify Fix 2 recipe step passes**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_discovery_recipe.py::TestDiscoveryContentHashStep -v
```

Expected: 5 PASSED.

**Step 5: Commit Fix 2**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
git add tools/dotfiles_discovery/content_hash.py tests/test_content_hash.py tests/test_discovery_recipe.py recipes/dotfiles-discovery.yaml
git commit -m "feat: add content-hash deduplication step and content_hash utility module"
```

---

## Task 6: Fix 3 — Write failing tests for `reconciliation.py`

**Files:**
- Create: `tests/test_reconciliation.py`

**Step 1: Create `tests/test_reconciliation.py`**

```python
"""Tests for tools/dotfiles_discovery/reconciliation.py.

RED phase: these tests fail until reconciliation.py is implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

BUNDLE_ROOT = Path(__file__).parent.parent


class TestImport:
    """Verify the module can be imported."""

    def test_module_importable(self) -> None:
        from dotfiles_discovery import reconciliation  # noqa: F401

    def test_find_orphaned_dirs_importable(self) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs  # noqa: F401

    def test_format_reconciliation_warning_importable(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning  # noqa: F401


class TestFindOrphanedDirs:
    """Verify find_orphaned_dirs correctly identifies stale output directories."""

    def test_returns_empty_when_all_dirs_in_profile(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "repo-b").mkdir()
        result = find_orphaned_dirs(["repo-a", "repo-b"], tmp_path)
        assert result == [], (
            "No orphans expected when all directories match the profile"
        )

    def test_returns_orphan_when_dir_not_in_profile(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "old-repo").mkdir()
        result = find_orphaned_dirs(["repo-a"], tmp_path)
        assert result == ["old-repo"], (
            "old-repo is on disk but not in profile — must be returned as orphan"
        )

    def test_returns_multiple_orphans_sorted(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "stale-z").mkdir()
        (tmp_path / "stale-a").mkdir()
        result = find_orphaned_dirs(["repo-a"], tmp_path)
        assert result == ["stale-a", "stale-z"], (
            "Multiple orphans must be returned in sorted order"
        )

    def test_ignores_files_not_directories(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "some-file.txt").write_text("not a dir")
        result = find_orphaned_dirs(["repo-a"], tmp_path)
        assert result == [], (
            "Files must not be counted as orphaned directories"
        )

    def test_returns_empty_when_dotfiles_dir_missing(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        nonexistent = tmp_path / "dotfiles"
        result = find_orphaned_dirs(["repo-a"], nonexistent)
        assert result == [], (
            "Missing dotfiles_dir must return empty list, not raise an error"
        )

    def test_returns_empty_when_profile_is_empty_and_no_dirs(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        result = find_orphaned_dirs([], tmp_path)
        assert result == [], (
            "Empty profile with empty directory must return empty list"
        )

    def test_all_dirs_orphaned_when_profile_empty(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "repo-b").mkdir()
        result = find_orphaned_dirs([], tmp_path)
        assert result == ["repo-a", "repo-b"], (
            "All directories must be orphans when profile is empty"
        )


class TestFormatReconciliationWarning:
    """Verify format_reconciliation_warning produces correct human-readable output."""

    def test_empty_orphans_returns_empty_string(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning([])
        assert result == "", (
            "No orphans — warning must be empty string"
        )

    def test_single_orphan_mentions_repo_name(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning(["old-repo"])
        assert "old-repo" in result, (
            "Warning must mention the orphaned directory name"
        )

    def test_multiple_orphans_all_mentioned(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning(["alpha", "beta", "gamma"])
        assert "alpha" in result, "Warning must mention 'alpha'"
        assert "beta" in result, "Warning must mention 'beta'"
        assert "gamma" in result, "Warning must mention 'gamma'"

    def test_warning_mentions_no_delete(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning(["old-repo"])
        lower = result.lower()
        assert "review" in lower or "remove" in lower or "delete" in lower, (
            "Warning must tell the human to take action (review, remove, or delete)"
        )

    def test_warning_contains_word_warning(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning(["old-repo"])
        assert "WARNING" in result or "warning" in result.lower(), (
            "Output must contain the word WARNING to stand out in logs"
        )
```

**Step 2: Run to verify tests fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_reconciliation.py -v
```

Expected: all FAILED with `ModuleNotFoundError: No module named 'dotfiles_discovery.reconciliation'`.

---

## Task 7: Fix 3 — Implement `reconciliation.py` and wire discovery step

**Files:**
- Create: `tools/dotfiles_discovery/reconciliation.py`
- Modify: `tests/test_discovery_recipe.py` (append new class)
- Modify: `recipes/dotfiles-discovery.yaml` (add step at end of cleanup stage)

**Step 1: Create `tools/dotfiles_discovery/reconciliation.py`**

```python
"""Stale repo reconciliation for the Team Sweep dotfiles pipeline.

Compares the repos listed in a profile against the directories that
exist under the dotfiles output root. Reports any directories that
no longer have a corresponding profile entry so a human can decide
whether to archive or delete them.
"""

from __future__ import annotations

from pathlib import Path


def find_orphaned_dirs(profile_repos: list[str], dotfiles_dir: Path) -> list[str]:
    """Find output directories that no longer have a matching profile entry.

    Parameters
    ----------
    profile_repos:
        List of repo names (slugs, e.g. ``"my-repo"``) from the profile.
    dotfiles_dir:
        Directory containing one subdirectory per documented repo.

    Returns
    -------
    list[str]
        Sorted list of directory names that exist on disk but are not
        present in ``profile_repos``. Empty list if no orphans found or
        if ``dotfiles_dir`` does not exist.
    """
    if not dotfiles_dir.exists():
        return []
    profile_set = set(profile_repos)
    on_disk = {d.name for d in dotfiles_dir.iterdir() if d.is_dir()}
    return sorted(on_disk - profile_set)


def format_reconciliation_warning(orphans: list[str]) -> str:
    """Format orphaned directory names into a human-readable warning.

    Parameters
    ----------
    orphans:
        List of directory names returned by :func:`find_orphaned_dirs`.

    Returns
    -------
    str
        Multi-line WARNING string. Empty string if ``orphans`` is empty.
    """
    if not orphans:
        return ""
    lines = [
        "WARNING: The following output directories have no matching profile entry:",
        *(f"  - {name}" for name in orphans),
        "Review these directories and remove them if the repo is no longer tracked.",
    ]
    return "\n".join(lines)
```

**Step 2: Run reconciliation tests to verify they pass**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_reconciliation.py -v
```

Expected: all PASSED.

**Step 3: Append reconciliation step test class to `tests/test_discovery_recipe.py`**

Read the current end of `tests/test_discovery_recipe.py`, then append after the last line:

```python


class TestDiscoveryReconciliationStep:
    """Verify dotfiles-discovery.yaml has a reconcile-stale-repos step at the end.

    RED phase: fails until the step is added to the recipe.
    """

    @pytest.fixture
    def recipe_data(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        return yaml.safe_load(content)

    @staticmethod
    def _get_all_steps(recipe_data: dict) -> list:
        steps: list = []
        if "steps" in recipe_data:
            steps.extend(recipe_data["steps"])
        for stage in recipe_data.get("stages", []):
            steps.extend(stage.get("steps", []))
        return steps

    @staticmethod
    def _get_step(recipe_data: dict, step_id: str) -> dict | None:
        for step in TestDiscoveryReconciliationStep._get_all_steps(recipe_data):
            if step.get("id") == step_id:
                return step
        return None

    def test_has_reconcile_stale_repos_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "reconcile-stale-repos")
        assert step is not None, (
            "dotfiles-discovery.yaml must have a step with id: reconcile-stale-repos"
        )

    def test_reconcile_step_is_bash(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "reconcile-stale-repos")
        assert step is not None, "reconcile-stale-repos step not found"
        assert step.get("type") == "bash", (
            "reconcile-stale-repos step must be type: bash"
        )

    def test_reconcile_step_has_on_error_continue(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "reconcile-stale-repos")
        assert step is not None, "reconcile-stale-repos step not found"
        assert step.get("on_error") == "continue", (
            "reconcile-stale-repos must have on_error: continue so a reconciliation "
            "failure never blocks the pipeline"
        )

    def test_reconcile_step_references_reconciliation_module(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "reconcile-stale-repos")
        assert step is not None, "reconcile-stale-repos step not found"
        command = step.get("command", "")
        assert "reconciliation" in command, (
            "reconcile-stale-repos command must import from the reconciliation module"
        )

    def test_reconcile_step_references_find_orphaned_dirs(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "reconcile-stale-repos")
        assert step is not None, "reconcile-stale-repos step not found"
        command = step.get("command", "")
        assert "find_orphaned_dirs" in command, (
            "reconcile-stale-repos command must call find_orphaned_dirs()"
        )

    def test_reconcile_step_after_final_summary(self, recipe_data: dict) -> None:
        all_steps = self._get_all_steps(recipe_data)
        ids = [s.get("id") for s in all_steps]
        assert "final-summary" in ids, "final-summary step not found"
        assert "reconcile-stale-repos" in ids, "reconcile-stale-repos step not found"
        assert ids.index("final-summary") < ids.index("reconcile-stale-repos"), (
            "reconcile-stale-repos must come after final-summary"
        )
```

**Step 4: Run to verify new tests fail**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_discovery_recipe.py::TestDiscoveryReconciliationStep -v
```

Expected: all FAILED — step not yet in the recipe.

**Step 5: Add `reconcile-stale-repos` step to `dotfiles-discovery.yaml`**

In `recipes/dotfiles-discovery.yaml`, find the `final-summary` step in Stage 3 (around line 562). The file ends at line 593 with `timeout: 30`. Add the new step immediately after `final-summary` (after the line `timeout: 30` that closes `final-summary`):

```yaml

      # ------------------------------------------------------------------------
      # Step 5: Reconcile stale repos — warn about orphaned output directories
      # Compares profile repos against on-disk directories in dotfiles_root.
      # Logs warnings for directories that no longer have a profile entry.
      # Never deletes anything — humans decide what to do with orphans.
      # ------------------------------------------------------------------------
      - id: "reconcile-stale-repos"
        type: "bash"
        on_error: continue
        command: |
          python3 << 'EOF'
          import sys
          import yaml
          from pathlib import Path

          sys.path.insert(0, "/home/bkrabach/dev/dot-docs/dot-docs/tools")
          from dotfiles_discovery.reconciliation import find_orphaned_dirs, format_reconciliation_warning

          profile_path = Path("{{profile_path}}")
          dotfiles_root = Path("{{dotfiles_root}}")

          # Read the profile to get the list of tracked repos
          try:
              profile = yaml.safe_load(profile_path.read_text())
              repos = profile.get("repos", [])
              # repos may be a list of strings or a list of dicts with a "repo" key
              if repos and isinstance(repos[0], dict):
                  repo_names = [r.get("repo", "").split("/")[-1] for r in repos]
              else:
                  repo_names = [str(r).split("/")[-1] for r in repos]
          except Exception as exc:
              print(f"WARNING: Could not read profile at {profile_path}: {exc}")
              repo_names = []

          orphans = find_orphaned_dirs(repo_names, dotfiles_root)
          warning = format_reconciliation_warning(orphans)

          if warning:
              print("")
              print(warning)
              print("")
          else:
              print("Reconciliation: all output directories match the profile. No orphans found.")
          EOF
        output: "reconciliation_result"
        timeout: 30
```

**Step 6: Run tests to verify Fix 3 recipe step passes**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/test_discovery_recipe.py::TestDiscoveryReconciliationStep -v
```

Expected: all PASSED.

**Step 7: Commit Fix 3**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
git add tools/dotfiles_discovery/reconciliation.py tests/test_reconciliation.py tests/test_discovery_recipe.py recipes/dotfiles-discovery.yaml
git commit -m "feat: add stale repo reconciliation step and reconciliation utility module"
```

---

## Task 8: Full test suite verification

**Step 1: Run the complete test suite**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
python -m pytest tests/ -v
```

**Step 2: Verify all tests introduced in this plan pass**

The following test classes must all be GREEN:

| Test file | Class |
|---|---|
| `tests/test_synthesis_artifacts.py` | `TestSynthesisRecipeProvenance` (4 tests) |
| `tests/test_content_hash.py` | `TestImport`, `TestComputeDotHash`, `TestShouldUpdate` (all) |
| `tests/test_discovery_recipe.py` | `TestDiscoveryContentHashStep` (5 tests) |
| `tests/test_reconciliation.py` | `TestImport`, `TestFindOrphanedDirs`, `TestFormatReconciliationWarning` (all) |
| `tests/test_discovery_recipe.py` | `TestDiscoveryReconciliationStep` (6 tests) |

Any pre-existing failures in other test classes that were already failing before you started are not your responsibility.

**Step 3: If any new tests are red, diagnose and fix before proceeding**

Re-read the failing test carefully, then re-read the corresponding implementation. Fix the implementation only — do not weaken the test.

**Step 4: Final commit if any fixes were made**

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs
git add -A
git commit -m "fix: resolve remaining test failures from COE operational fixes"
```

---

## Implementation Notes

### Source SHA flow (Fix 1)

```
dotfiles-investigate.yaml
  build-manifest step
    → git rev-parse HEAD from repo_path
    → source_sha added to manifest JSON output

dotfiles-discovery.yaml
  run-synthesis step
    → source_sha: "{{repo_entry.current_commit}}"
    → (current_commit is already populated by detect-tiers bash step)

dotfiles-synthesis.yaml
  context: source_sha: ""
  synthesize step prompt
    → "Source SHA: {{source_sha}}"
    → Instruction to include graph [source_sha="...", generated_at="..."]
```

### Content hash flow (Fix 2)

```
After synthesis writes overview.dot:
  check-content-hash step
    → reads overview.dot from output_dir
    → compute_dot_hash() strips generated_at value, SHA-256 hashes remainder
    → compares against .discovery/content-hash.txt (previous run's hash)
    → logs "changed" or "unchanged"
    → writes new hash to .discovery/content-hash.txt for next run
```

### Reconciliation flow (Fix 3)

```
After final-summary:
  reconcile-stale-repos step
    → reads profile.yaml to get tracked repo names
    → lists subdirectories of dotfiles_root
    → find_orphaned_dirs() = on-disk dirs NOT in profile
    → format_reconciliation_warning() → printed to logs
    → never deletes, never fails the pipeline (on_error: continue)
```

### Constraint: Never weaken tests

If a test is inconvenient to pass, fix the implementation. Tests are the specification.

### Constraint: No side effects in Python modules

`content_hash.py` and `reconciliation.py` are pure-function modules — no global state, no file writes, no subprocess calls. All I/O happens in the recipe bash steps.
