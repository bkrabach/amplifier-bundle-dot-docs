# Dotfiles Discovery System Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Build Python utilities, Amplifier recipes, and agent prompts that produce accurate, agent-readable DOT (Graphviz) graph representations of repos, organized per-person in a team knowledge base.

**Architecture:** A discovery orchestrator recipe (outer loop) determines which tier of investigation each repo needs, dispatches the Parallax Discovery recipe (inner loop, already exists) for the actual investigation, then runs a synthesis step to produce the final DOT files. Three Python utility modules handle structural change detection, DOT file validation, and discovery metadata tracking. Agent prompts in `context/*.md` files encode the DOT quality standards and investigation heuristics.

**Tech Stack:** Python 3.12, pytest, dataclasses, subprocess (for git/graphviz), Amplifier recipe YAML, Graphviz DOT format

**Design Document:** `docs/plans/2026-03-12-dotfiles-discovery-design.md`

---

## Prerequisites

Run these once before starting:

```bash
# Install Graphviz (needed for DOT syntax validation)
sudo apt-get update && sudo apt-get install -y graphviz

# Verify
dot -V
# Expected: dot - graphviz version X.Y.Z

# Verify pytest is available
pytest --version
# Expected: pytest 9.0.2

# Create the full directory tree
cd /home/bkrabach/dev/dot-docs
mkdir -p dot-docs/{tools/dotfiles_discovery,recipes,context,tests/fixtures/mock-repo,docs/plans}
```

---

## Task 0: Project Scaffold

**Files:**
- Create: `dot-docs/pyproject.toml`
- Create: `dot-docs/tools/dotfiles_discovery/__init__.py`
- Create: `dot-docs/tests/__init__.py`
- Create: `dot-docs/tests/conftest.py`

**Step 1: Create pyproject.toml**

This configures the Python package so pytest can find our modules.

Create `dot-docs/pyproject.toml`:

```toml
[project]
name = "dotfiles-discovery"
version = "0.1.0"
description = "DOT graph discovery tooling for Amplifier repos"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["tools"]
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100
```

**Step 2: Create the package init**

Create `dot-docs/tools/dotfiles_discovery/__init__.py`:

```python
"""Dotfiles discovery utilities for the dot-docs bundle."""
```

**Step 3: Create the test package init**

Create `dot-docs/tests/__init__.py`:

```python
```

(Empty file. Pytest needs it to resolve imports.)

**Step 4: Create conftest.py with shared git fixtures**

Create `dot-docs/tests/conftest.py`:

```python
"""Shared test fixtures for dotfiles-discovery tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in the given repo directory."""
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def git_commit(repo: Path, message: str = "Update") -> str:
    """Stage all changes and commit. Return the new commit hash."""
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", message)
    result = _run_git(repo, "rev-parse", "HEAD")
    return result.stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with a Python package structure and initial commit.

    Returns the repo root path. The repo contains:
      - README.md
      - pyproject.toml
      - src/core/__init__.py
      - src/core/main.py
      - src/utils/__init__.py
      - src/utils/helpers.py
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create a realistic small project
    (repo / "README.md").write_text("# Test Repo\n")
    (repo / "pyproject.toml").write_text('[project]\nname = "test-repo"\nversion = "0.1.0"\n')

    core = repo / "src" / "core"
    core.mkdir(parents=True)
    (core / "__init__.py").write_text("")
    (core / "main.py").write_text("def main():\n    pass\n")

    utils = repo / "src" / "utils"
    utils.mkdir(parents=True)
    (utils / "__init__.py").write_text("")
    (utils / "helpers.py").write_text("def helper():\n    pass\n")

    _run_git(repo, "init")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "Initial commit")

    return repo


VALID_DOT = """\
digraph overview {
    rankdir=LR;
    label="Test System Overview";

    subgraph cluster_legend {
        label="Legend";
        style=dashed;
        legend_mod [label="Module" shape=box];
        legend_proc [label="Process" shape=ellipse];
    }

    subgraph cluster_core {
        label="Core";
        style=filled;
        fillcolor="#f0f0f0";
        core_main [label="main\\nEntry point" shape=box];
        core_state [label="AppState" shape=cylinder];
    }

    subgraph cluster_utils {
        label="Utilities";
        style=filled;
        fillcolor="#f0f8ff";
        utils_helpers [label="helpers\\nShared utils" shape=box];
    }

    core_main -> core_state [label="reads"];
    core_main -> utils_helpers [label="imports" style=dashed];
}
"""

INVALID_DOT = """\
digraph broken {
    this is not valid DOT syntax !!!
    missing_semicolons
    [[[
}
"""
```

**Step 5: Verify the scaffold**

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest --collect-only 2>&1
```
Expected: `no tests ran` (nothing to collect yet, but no import errors)

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "chore: scaffold dot-docs bundle with pyproject.toml and test fixtures"
```

---

## Task 1: Structural Change Detector

**Files:**
- Test: `dot-docs/tests/test_structural_change.py`
- Create: `dot-docs/tools/dotfiles_discovery/structural_change.py`

### Step 1: Write the failing tests

Create `dot-docs/tests/test_structural_change.py`:

```python
"""Tests for the structural change detector."""

from __future__ import annotations

from pathlib import Path

from conftest import git_commit

from dotfiles_discovery.structural_change import detect_changes


class TestTierSelection:
    """Test that the correct discovery tier is recommended."""

    def test_no_previous_run_returns_tier_1(self, git_repo: Path) -> None:
        """First-ever run (no last_commit) should recommend full discovery."""
        result = detect_changes(git_repo, last_commit=None)
        assert result.tier == 1
        assert "no previous" in result.reason.lower()
        assert result.current_commit  # should be a non-empty hash

    def test_same_commit_returns_tier_0_skip(self, git_repo: Path) -> None:
        """Unchanged repo should recommend skipping."""
        head = git_commit(git_repo, "Add a file")  # ensure we have a known commit
        (git_repo / "src" / "core" / "extra.py").write_text("x = 1\n")
        head = git_commit(git_repo, "Extra file")

        result = detect_changes(git_repo, last_commit=head)
        assert result.tier == 0
        assert "no changes" in result.reason.lower()

    def test_minor_changes_return_tier_3(self, git_repo: Path) -> None:
        """Small edits to existing files should recommend targeted update."""
        head = git_commit(git_repo, "Baseline")
        # Modify one existing file (well under 20% churn)
        (git_repo / "src" / "core" / "main.py").write_text("def main():\n    return 42\n")
        git_commit(git_repo, "Minor edit")

        result = detect_changes(git_repo, last_commit=head)
        assert result.tier == 3
        assert result.churn_percentage < 20.0
        assert len(result.changed_files) >= 1

    def test_high_churn_returns_tier_2(self, git_repo: Path) -> None:
        """Changing >20% of tracked files should recommend single-wave refresh."""
        # Add enough files so the initial set is meaningful
        for i in range(10):
            (git_repo / "src" / "core" / f"mod_{i}.py").write_text(f"val = {i}\n")
        head = git_commit(git_repo, "Add many modules")

        # Now change most of them (>20%)
        for i in range(10):
            (git_repo / "src" / "core" / f"mod_{i}.py").write_text(f"val = {i * 100}\n")
        git_commit(git_repo, "Rewrite all modules")

        result = detect_changes(git_repo, last_commit=head)
        assert result.tier == 2
        assert result.churn_percentage > 20.0

    def test_new_module_added_returns_tier_2(self, git_repo: Path) -> None:
        """Adding a new Python package (with __init__.py) is a structural change."""
        head = git_commit(git_repo, "Baseline")

        # Add a new package
        new_pkg = git_repo / "src" / "newpkg"
        new_pkg.mkdir(parents=True)
        (new_pkg / "__init__.py").write_text("")
        (new_pkg / "feature.py").write_text("def feat():\n    pass\n")
        git_commit(git_repo, "Add new package")

        result = detect_changes(git_repo, last_commit=head)
        assert result.tier == 2
        assert "src/newpkg" in result.modules_added

    def test_module_removed_returns_tier_2(self, git_repo: Path) -> None:
        """Removing a Python package is a structural change."""
        head = git_commit(git_repo, "Baseline")

        # Remove the utils package
        import shutil

        shutil.rmtree(git_repo / "src" / "utils")
        git_commit(git_repo, "Remove utils package")

        result = detect_changes(git_repo, last_commit=head)
        assert result.tier == 2
        assert "src/utils" in result.modules_removed

    def test_non_source_files_ignored(self, git_repo: Path) -> None:
        """Changes to non-source files (images, docs) should not affect tier."""
        head = git_commit(git_repo, "Baseline")

        # Add non-source files only
        (git_repo / "logo.png").write_bytes(b"\x89PNG")
        (git_repo / "notes.txt").write_text("some notes\n")
        (git_repo / "data.csv").write_text("a,b,c\n1,2,3\n")
        git_commit(git_repo, "Add non-source files")

        result = detect_changes(git_repo, last_commit=head)
        # No tracked source files changed, so should be skip (tier 0) or tier 3
        # with 0 changed tracked files
        assert result.tier in (0, 3)
        assert len(result.changed_files) == 0


class TestChangeDetectionResult:
    """Test result metadata is populated correctly."""

    def test_current_commit_is_populated(self, git_repo: Path) -> None:
        result = detect_changes(git_repo, last_commit=None)
        assert len(result.current_commit) == 40  # full SHA-1 hash

    def test_changed_files_listed(self, git_repo: Path) -> None:
        head = git_commit(git_repo, "Baseline")
        (git_repo / "src" / "core" / "main.py").write_text("# changed\n")
        git_commit(git_repo, "Edit main")

        result = detect_changes(git_repo, last_commit=head)
        assert "src/core/main.py" in result.changed_files
```

### Step 2: Run tests to verify they fail

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/test_structural_change.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'dotfiles_discovery.structural_change'`

### Step 3: Write the implementation

Create `dot-docs/tools/dotfiles_discovery/structural_change.py`:

```python
"""Structural change detector for dotfiles discovery tiered refresh.

Analyzes git history to determine which discovery tier a repo needs:
  Tier 0 (skip)   — no changes since last discovery
  Tier 1 (full)   — no previous discovery run exists
  Tier 2 (wave)   — structural changes detected (new/removed modules, >20% churn)
  Tier 3 (patch)  — minor changes only
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# File extensions considered "source code" for change detection
SOURCE_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".rs", ".ts", ".js", ".go",
})

# Config filenames that signal project structure
CONFIG_FILENAMES: frozenset[str] = frozenset({
    "pyproject.toml", "Cargo.toml", "package.json",
    "setup.py", "setup.cfg",
})

# Config/bundle extensions also tracked
CONFIG_EXTENSIONS: frozenset[str] = frozenset({
    ".yaml", ".yml", ".toml",
})

# Everything we consider a "tracked" file for churn calculation
TRACKED_EXTENSIONS: frozenset[str] = SOURCE_EXTENSIONS | CONFIG_EXTENSIONS

# Filenames that mark a "module root" (adding/removing one = structural change)
MODULE_MARKERS: frozenset[str] = frozenset({
    "__init__.py", "Cargo.toml", "package.json",
})

# Churn threshold — above this percentage, changes are "structural"
CHURN_THRESHOLD: float = 20.0


@dataclass
class ChangeDetectionResult:
    """Result of structural change detection for a repository."""

    tier: int  # 0=skip, 1=full, 2=single-wave, 3=targeted
    reason: str
    current_commit: str
    changed_files: list[str] = field(default_factory=list)
    total_tracked_files: int = 0
    churn_percentage: float = 0.0
    modules_added: list[str] = field(default_factory=list)
    modules_removed: list[str] = field(default_factory=list)


def detect_changes(
    repo_path: str | Path,
    last_commit: str | None,
) -> ChangeDetectionResult:
    """Detect structural changes in a repo and recommend a discovery tier.

    Args:
        repo_path: Path to the git repository root.
        last_commit: Commit hash from the last discovery run, or None if first run.

    Returns:
        ChangeDetectionResult with the recommended tier and supporting data.
    """
    repo = Path(repo_path)
    current_commit = _git_head(repo)

    # No previous run → Tier 1 (full discovery)
    if last_commit is None:
        return ChangeDetectionResult(
            tier=1,
            reason="No previous discovery run found",
            current_commit=current_commit,
        )

    # Same commit → Skip
    if current_commit == last_commit:
        return ChangeDetectionResult(
            tier=0,
            reason="No changes since last discovery",
            current_commit=current_commit,
        )

    # Get changed files with their statuses
    diff_entries = _git_diff_name_status(repo, last_commit, current_commit)

    # Filter to tracked source/config files only
    tracked_entries = [
        (status, path)
        for status, path in diff_entries
        if _is_tracked_file(path)
    ]
    tracked_changed = [path for _, path in tracked_entries]

    # If no tracked files changed, it's effectively a skip
    if not tracked_changed:
        return ChangeDetectionResult(
            tier=0,
            reason="No changes to tracked source/config files",
            current_commit=current_commit,
        )

    # Count total tracked files in the repo at HEAD
    total_tracked = _count_tracked_files(repo)

    # Detect module-level additions and removals
    modules_added = [
        str(Path(path).parent)
        for status, path in tracked_entries
        if status == "A" and Path(path).name in MODULE_MARKERS
    ]
    modules_removed = [
        str(Path(path).parent)
        for status, path in tracked_entries
        if status == "D" and Path(path).name in MODULE_MARKERS
    ]

    # Calculate churn percentage
    churn = (len(tracked_changed) / total_tracked * 100) if total_tracked > 0 else 0.0

    # Structural change? → Tier 2
    is_structural = bool(modules_added) or bool(modules_removed) or churn > CHURN_THRESHOLD

    if is_structural:
        reasons = []
        if modules_added:
            reasons.append(f"modules added: {', '.join(modules_added)}")
        if modules_removed:
            reasons.append(f"modules removed: {', '.join(modules_removed)}")
        if churn > CHURN_THRESHOLD:
            reasons.append(f"churn {churn:.1f}% exceeds {CHURN_THRESHOLD}% threshold")
        return ChangeDetectionResult(
            tier=2,
            reason=f"Structural changes: {'; '.join(reasons)}",
            current_commit=current_commit,
            changed_files=tracked_changed,
            total_tracked_files=total_tracked,
            churn_percentage=churn,
            modules_added=modules_added,
            modules_removed=modules_removed,
        )

    # Minor changes → Tier 3
    return ChangeDetectionResult(
        tier=3,
        reason=f"Minor changes: {len(tracked_changed)} files ({churn:.1f}% churn)",
        current_commit=current_commit,
        changed_files=tracked_changed,
        total_tracked_files=total_tracked,
        churn_percentage=churn,
    )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git_head(repo: Path) -> str:
    """Get the current HEAD commit hash (full 40-char SHA)."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_diff_name_status(
    repo: Path, from_commit: str, to_commit: str
) -> list[tuple[str, str]]:
    """Get (status, filepath) tuples for files changed between two commits.

    Status codes: A=added, D=deleted, M=modified.
    Renames are split into a D + A pair.
    """
    result = subprocess.run(
        ["git", "diff", "--name-status", from_commit, to_commit],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    entries: list[tuple[str, str]] = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status_code = parts[0][0]  # First char: A, D, M, R, C, etc.
        if status_code == "R" and len(parts) >= 3:
            # Rename: treat as delete old + add new
            entries.append(("D", parts[1]))
            entries.append(("A", parts[2]))
        elif len(parts) >= 2:
            entries.append((status_code, parts[1]))
    return entries


def _is_tracked_file(filepath: str) -> bool:
    """Check if a filepath matches our tracked extensions or config filenames."""
    p = Path(filepath)
    return p.suffix in TRACKED_EXTENSIONS or p.name in CONFIG_FILENAMES


def _count_tracked_files(repo: Path) -> int:
    """Count tracked files with relevant extensions in the repo at HEAD."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    count = 0
    for filepath in result.stdout.strip().splitlines():
        if _is_tracked_file(filepath):
            count += 1
    return count
```

### Step 4: Run tests to verify they pass

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/test_structural_change.py -v
```
Expected: All 9 tests PASS

### Step 5: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "feat: structural change detector with tier recommendation logic"
```

---

## Task 2: DOT Validation Utilities

**Files:**
- Test: `dot-docs/tests/test_dot_validation.py`
- Create: `dot-docs/tools/dotfiles_discovery/dot_validation.py`

### Step 1: Write the failing tests

Create `dot-docs/tests/test_dot_validation.py`:

```python
"""Tests for DOT file validation utilities."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import INVALID_DOT, VALID_DOT

from dotfiles_discovery.dot_validation import (
    check_line_count,
    validate_dot_file,
    validate_dot_syntax,
)

HAS_GRAPHVIZ = shutil.which("dot") is not None


class TestValidateDotSyntax:
    """Test Graphviz DOT syntax validation."""

    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_valid_dot_passes(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "valid.dot"
        dot_file.write_text(VALID_DOT)
        result = validate_dot_syntax(dot_file)
        assert result.valid_syntax is True
        assert result.syntax_error is None

    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_invalid_dot_fails(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "broken.dot"
        dot_file.write_text(INVALID_DOT)
        result = validate_dot_syntax(dot_file)
        assert result.valid_syntax is False
        assert result.syntax_error is not None

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        result = validate_dot_syntax(tmp_path / "nonexistent.dot")
        assert result.valid_syntax is False
        assert "not found" in result.syntax_error.lower()

    def test_graphviz_not_available_returns_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """If graphviz is not installed, return a clear error instead of crashing."""
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(VALID_DOT)
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        result = validate_dot_syntax(dot_file)
        assert result.valid_syntax is False
        assert "graphviz" in result.syntax_error.lower()


class TestCheckLineCount:
    """Test DOT file line count checking."""

    def test_in_range(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "ok.dot"
        dot_file.write_text("\n".join(f"  line {i};" for i in range(200)))
        result = check_line_count(dot_file)
        assert result.line_count == 200
        assert result.in_range is True

    def test_too_few_lines(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "short.dot"
        dot_file.write_text("\n".join(f"  line {i};" for i in range(50)))
        result = check_line_count(dot_file)
        assert result.line_count == 50
        assert result.in_range is False

    def test_too_many_lines(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "long.dot"
        dot_file.write_text("\n".join(f"  line {i};" for i in range(500)))
        result = check_line_count(dot_file)
        assert result.line_count == 500
        assert result.in_range is False

    def test_custom_range(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "custom.dot"
        dot_file.write_text("\n".join(f"  line {i};" for i in range(100)))
        result = check_line_count(dot_file, min_lines=50, max_lines=150)
        assert result.in_range is True


class TestValidateDotFile:
    """Test the combined validation function."""

    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_valid_file_passes_all_checks(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "good.dot"
        # Pad valid DOT to reach the 150-line minimum
        padded = VALID_DOT.rstrip("\n") + "\n"
        lines = padded.splitlines()
        # Add comment lines to reach ~180 lines
        while len(lines) < 180:
            lines.insert(-1, f"    // padding line {len(lines)}")
        dot_file.write_text("\n".join(lines) + "\n")

        result = validate_dot_file(dot_file)
        assert result.valid_syntax is True
        assert result.line_count_in_range is True

    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_invalid_file_reports_syntax_error(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "bad.dot"
        dot_file.write_text(INVALID_DOT)
        result = validate_dot_file(dot_file)
        assert result.valid_syntax is False
```

### Step 2: Run tests to verify they fail

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/test_dot_validation.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'dotfiles_discovery.dot_validation'`

### Step 3: Write the implementation

Create `dot-docs/tools/dotfiles_discovery/dot_validation.py`:

```python
"""DOT file validation utilities for dotfiles discovery.

Validates Graphviz DOT files for:
  - Syntax correctness (via `dot -Tsvg`)
  - Line count within target range (default 150-300)
  - SVG render produces non-zero bounding box
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SyntaxResult:
    """Result of DOT syntax validation."""

    valid_syntax: bool
    syntax_error: str | None = None
    svg_path: str | None = None


@dataclass
class LineCountResult:
    """Result of line count check."""

    line_count: int
    in_range: bool
    min_lines: int = 150
    max_lines: int = 300


@dataclass
class DotFileValidation:
    """Combined validation result for a DOT file."""

    valid_syntax: bool
    syntax_error: str | None
    line_count: int
    line_count_in_range: bool
    render_ok: bool
    render_error: str | None = None


def validate_dot_syntax(dot_path: str | Path) -> SyntaxResult:
    """Validate DOT file syntax by running it through Graphviz.

    Shells out to `dot -Tsvg` to check if the file is valid Graphviz.
    Returns a SyntaxResult with details.

    Handles gracefully:
      - File not found
      - Graphviz not installed
      - Invalid DOT syntax
    """
    dot_path = Path(dot_path)

    if not dot_path.exists():
        return SyntaxResult(valid_syntax=False, syntax_error=f"File not found: {dot_path}")

    if shutil.which("dot") is None:
        return SyntaxResult(
            valid_syntax=False,
            syntax_error="Graphviz 'dot' command not found. Install with: apt-get install graphviz",
        )

    svg_path = dot_path.with_suffix(".svg")
    try:
        subprocess.run(
            ["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return SyntaxResult(valid_syntax=True, svg_path=str(svg_path))
    except subprocess.CalledProcessError as exc:
        error_msg = exc.stderr.strip() or exc.stdout.strip() or "Unknown syntax error"
        return SyntaxResult(valid_syntax=False, syntax_error=error_msg)
    except subprocess.TimeoutExpired:
        return SyntaxResult(valid_syntax=False, syntax_error="Graphviz timed out (>30s)")


def check_line_count(
    dot_path: str | Path,
    min_lines: int = 150,
    max_lines: int = 300,
) -> LineCountResult:
    """Check that a DOT file's line count falls within the target range.

    Args:
        dot_path: Path to the DOT file.
        min_lines: Minimum acceptable line count (default 150).
        max_lines: Maximum acceptable line count (default 300).
    """
    dot_path = Path(dot_path)
    line_count = len(dot_path.read_text().splitlines())
    return LineCountResult(
        line_count=line_count,
        in_range=min_lines <= line_count <= max_lines,
        min_lines=min_lines,
        max_lines=max_lines,
    )


def check_svg_render(svg_path: str | Path) -> tuple[bool, str | None]:
    """Check that an SVG file has a non-zero bounding box (actually rendered something).

    Returns (ok, error_message).
    """
    svg_path = Path(svg_path)
    if not svg_path.exists():
        return False, f"SVG file not found: {svg_path}"

    content = svg_path.read_text()

    # Check for width/height attributes that are non-zero
    # Graphviz SVGs have: <svg width="NNpt" height="NNpt" ...>
    if 'width="0' in content or 'height="0' in content:
        return False, "SVG has zero-width or zero-height bounding box"

    # Check the file has actual content (not just the XML header)
    if len(content) < 200:
        return False, f"SVG file suspiciously small ({len(content)} bytes)"

    return True, None


def validate_dot_file(
    dot_path: str | Path,
    min_lines: int = 150,
    max_lines: int = 300,
) -> DotFileValidation:
    """Run all validation checks on a DOT file.

    Combines syntax validation, line count check, and SVG render check.
    """
    dot_path = Path(dot_path)

    # Syntax check
    syntax = validate_dot_syntax(dot_path)

    # Line count check (even if syntax failed — still useful info)
    if dot_path.exists():
        lc = check_line_count(dot_path, min_lines, max_lines)
        line_count = lc.line_count
        line_count_in_range = lc.in_range
    else:
        line_count = 0
        line_count_in_range = False

    # Render check (only if syntax passed and SVG was produced)
    render_ok = False
    render_error = None
    if syntax.valid_syntax and syntax.svg_path:
        render_ok, render_error = check_svg_render(syntax.svg_path)
    elif not syntax.valid_syntax:
        render_error = "Skipped: syntax validation failed"

    return DotFileValidation(
        valid_syntax=syntax.valid_syntax,
        syntax_error=syntax.syntax_error,
        line_count=line_count,
        line_count_in_range=line_count_in_range,
        render_ok=render_ok,
        render_error=render_error,
    )
```

### Step 4: Run tests to verify they pass

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/test_dot_validation.py -v
```
Expected: All tests PASS (graphviz-dependent tests may be skipped if graphviz isn't installed)

### Step 5: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "feat: DOT file validation utilities (syntax, line count, render check)"
```

---

## Task 3: Discovery Metadata Manager

**Files:**
- Test: `dot-docs/tests/test_discovery_metadata.py`
- Create: `dot-docs/tools/dotfiles_discovery/discovery_metadata.py`

### Step 1: Write the failing tests

Create `dot-docs/tests/test_discovery_metadata.py`:

```python
"""Tests for the discovery metadata manager."""

from __future__ import annotations

import json
from pathlib import Path

from dotfiles_discovery.discovery_metadata import (
    LastRunMetadata,
    ManifestMetadata,
    get_force_tier,
    read_last_run,
    read_manifest,
    write_last_run,
    write_manifest,
)


class TestLastRunMetadata:
    """Test reading and writing .discovery/last-run.json."""

    def test_write_and_read_round_trip(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / ".discovery"
        meta = LastRunMetadata(
            timestamp="2026-03-12T19:00:00",
            tier=1,
            commit_hash="abc123def456" * 3 + "abcd",  # 40 chars
            wave_count=3,
            status="completed",
        )
        write_last_run(discovery_dir, meta)
        loaded = read_last_run(discovery_dir)
        assert loaded is not None
        assert loaded.timestamp == meta.timestamp
        assert loaded.tier == meta.tier
        assert loaded.commit_hash == meta.commit_hash
        assert loaded.wave_count == meta.wave_count
        assert loaded.status == meta.status

    def test_read_missing_returns_none(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / ".discovery"
        assert read_last_run(discovery_dir) is None

    def test_skipped_status(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / ".discovery"
        meta = LastRunMetadata(
            timestamp="2026-03-12T19:00:00",
            tier=0,
            commit_hash="",
            wave_count=0,
            status="skipped",
            reason="clone failed",
        )
        write_last_run(discovery_dir, meta)
        loaded = read_last_run(discovery_dir)
        assert loaded is not None
        assert loaded.status == "skipped"
        assert loaded.reason == "clone failed"

    def test_creates_directory_if_missing(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / "nested" / ".discovery"
        meta = LastRunMetadata(
            timestamp="2026-03-12T19:00:00",
            tier=1,
            commit_hash="a" * 40,
            wave_count=3,
            status="completed",
        )
        write_last_run(discovery_dir, meta)
        assert (discovery_dir / "last-run.json").exists()


class TestManifestMetadata:
    """Test reading and writing .discovery/manifest.json."""

    def test_write_and_read_round_trip(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / ".discovery"
        meta = ManifestMetadata(
            topics=["module architecture", "execution flows", "state machines"],
            agent_count=9,
            dot_files_produced=["overview.dot", "architecture.dot", "sequence.dot"],
            overview_perspective="architecture",
        )
        write_manifest(discovery_dir, meta)
        loaded = read_manifest(discovery_dir)
        assert loaded is not None
        assert loaded.topics == meta.topics
        assert loaded.agent_count == meta.agent_count
        assert loaded.dot_files_produced == meta.dot_files_produced
        assert loaded.overview_perspective == meta.overview_perspective

    def test_read_missing_returns_none(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / ".discovery"
        assert read_manifest(discovery_dir) is None


class TestForceTierOverride:
    """Test the force_tier mechanism in last-run.json."""

    def test_force_tier_present(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / ".discovery"
        meta = LastRunMetadata(
            timestamp="2026-03-12T19:00:00",
            tier=3,
            commit_hash="a" * 40,
            wave_count=1,
            status="completed",
            force_tier=1,
        )
        write_last_run(discovery_dir, meta)
        assert get_force_tier(discovery_dir) == 1

    def test_force_tier_absent(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / ".discovery"
        meta = LastRunMetadata(
            timestamp="2026-03-12T19:00:00",
            tier=3,
            commit_hash="a" * 40,
            wave_count=1,
            status="completed",
        )
        write_last_run(discovery_dir, meta)
        assert get_force_tier(discovery_dir) is None

    def test_force_tier_no_file(self, tmp_path: Path) -> None:
        discovery_dir = tmp_path / ".discovery"
        assert get_force_tier(discovery_dir) is None

    def test_force_tier_in_raw_json(self, tmp_path: Path) -> None:
        """Verify force_tier is written to the actual JSON on disk."""
        discovery_dir = tmp_path / ".discovery"
        discovery_dir.mkdir(parents=True)
        meta = LastRunMetadata(
            timestamp="2026-03-12T19:00:00",
            tier=2,
            commit_hash="b" * 40,
            wave_count=1,
            status="completed",
            force_tier=1,
        )
        write_last_run(discovery_dir, meta)
        raw = json.loads((discovery_dir / "last-run.json").read_text())
        assert raw["force_tier"] == 1
```

### Step 2: Run tests to verify they fail

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/test_discovery_metadata.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'dotfiles_discovery.discovery_metadata'`

### Step 3: Write the implementation

Create `dot-docs/tools/dotfiles_discovery/discovery_metadata.py`:

```python
"""Discovery metadata manager for dotfiles discovery.

Reads and writes the .discovery/ directory contents:
  - last-run.json  — timestamp, tier used, commit hash, wave count, status
  - manifest.json  — topics investigated, agent count, files produced
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class LastRunMetadata:
    """Metadata about the most recent discovery run for a repo."""

    timestamp: str
    tier: int
    commit_hash: str
    wave_count: int
    status: str  # "completed", "failed", "skipped"
    reason: str | None = None
    force_tier: int | None = None


@dataclass
class ManifestMetadata:
    """Metadata about what was investigated and produced."""

    topics: list[str] = field(default_factory=list)
    agent_count: int = 0
    dot_files_produced: list[str] = field(default_factory=list)
    overview_perspective: str = ""


def write_last_run(discovery_dir: str | Path, metadata: LastRunMetadata) -> Path:
    """Write last-run.json to the .discovery/ directory.

    Creates the directory if it doesn't exist.
    Returns the path to the written file.
    """
    discovery_dir = Path(discovery_dir)
    discovery_dir.mkdir(parents=True, exist_ok=True)

    filepath = discovery_dir / "last-run.json"
    data = asdict(metadata)
    # Remove None values for cleaner JSON
    data = {k: v for k, v in data.items() if v is not None}
    filepath.write_text(json.dumps(data, indent=2) + "\n")
    return filepath


def read_last_run(discovery_dir: str | Path) -> LastRunMetadata | None:
    """Read last-run.json from the .discovery/ directory.

    Returns None if the file doesn't exist.
    """
    filepath = Path(discovery_dir) / "last-run.json"
    if not filepath.exists():
        return None

    data = json.loads(filepath.read_text())
    return LastRunMetadata(
        timestamp=data["timestamp"],
        tier=data["tier"],
        commit_hash=data["commit_hash"],
        wave_count=data["wave_count"],
        status=data["status"],
        reason=data.get("reason"),
        force_tier=data.get("force_tier"),
    )


def write_manifest(discovery_dir: str | Path, metadata: ManifestMetadata) -> Path:
    """Write manifest.json to the .discovery/ directory.

    Creates the directory if it doesn't exist.
    Returns the path to the written file.
    """
    discovery_dir = Path(discovery_dir)
    discovery_dir.mkdir(parents=True, exist_ok=True)

    filepath = discovery_dir / "manifest.json"
    filepath.write_text(json.dumps(asdict(metadata), indent=2) + "\n")
    return filepath


def read_manifest(discovery_dir: str | Path) -> ManifestMetadata | None:
    """Read manifest.json from the .discovery/ directory.

    Returns None if the file doesn't exist.
    """
    filepath = Path(discovery_dir) / "manifest.json"
    if not filepath.exists():
        return None

    data = json.loads(filepath.read_text())
    return ManifestMetadata(
        topics=data.get("topics", []),
        agent_count=data.get("agent_count", 0),
        dot_files_produced=data.get("dot_files_produced", []),
        overview_perspective=data.get("overview_perspective", ""),
    )


def get_force_tier(discovery_dir: str | Path) -> int | None:
    """Check if a force_tier override is set in last-run.json.

    Returns the forced tier number, or None if not set or file doesn't exist.
    """
    metadata = read_last_run(discovery_dir)
    if metadata is None:
        return None
    return metadata.force_tier
```

### Step 4: Run tests to verify they pass

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/test_discovery_metadata.py -v
```
Expected: All 9 tests PASS

### Step 5: Run all Phase 1 tests together

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/ -v
```
Expected: All tests from Tasks 1, 2, and 3 PASS

### Step 6: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "feat: discovery metadata manager (last-run.json, manifest.json, force_tier)"
```

---

## Task 4: DOT Quality Standards + Pre-scan Prompt + Recipe

**Files:**
- Create: `dot-docs/context/dot-quality-standards.md`
- Create: `dot-docs/context/prescan-prompt.md`
- Create: `dot-docs/recipes/dotfiles-prescan.yaml`

### Step 1: Write the DOT quality standards reference

This file is loaded by agent prompts to enforce consistent DOT output quality.

Create `dot-docs/context/dot-quality-standards.md`:

```markdown
# DOT File Quality Standards

These standards govern all DOT (Graphviz) files produced by the dotfiles discovery system.

## The `overview.dot` Contract (mandatory, one per repo)

### Size & Readability
- **Target: 150-250 lines, under 15KB**
- Must render standalone as a readable image at normal viewing size — no "wall of nodes"
- Must be agent-scannable in minimal tokens — concise node labels, not inline documentation

### Structure
- Uses `cluster` subgraphs for logical groupings
- Includes a **rendered legend subgraph** (not comment-only) explaining shapes and edge styles
- Node IDs use `snake_case` prefixed by their cluster (e.g., `core_main`, `utils_helpers`)

### Shape Vocabulary (use consistently)

| Shape | Meaning | Example |
|-------|---------|---------|
| `box` | Module / package | A Python package or Rust crate |
| `ellipse` | Process / function | An execution entry point |
| `component` | Orchestrator | A system that coordinates others |
| `hexagon` | Hook / interceptor | A point where behavior is injected |
| `diamond` | Decision / transform | A branch point or data transformation |
| `cylinder` | State store | Persistent state, database, config store |
| `note` | Config file | YAML, TOML, or other configuration |
| `box3d` | External dependency | Something outside this repo |

### Edge Style Semantics

| Style | Meaning |
|-------|---------|
| `solid` | Declared / direct dependency |
| `dashed` | Runtime / optional dependency |
| `dotted` | Coordinator-mediated / indirect |
| `bold` | Critical path |

### Issue Annotation
- Confirmed bugs get `color=red` on their nodes and edges
- Suspected issues get `color=orange`
- Include a brief label on red edges describing the issue

## Detail File Standards (`architecture.dot`, `sequence.dot`, etc.)

- **Target: 200-400 lines each**
- Use `subgraph` names that match clusters in `overview.dot` for traceability
- Extensive edge labels — cross-boundary edges show what data crosses and in which direction
- Follow the same shape vocabulary and edge style semantics as overview.dot

## Anti-patterns (DO NOT do these)

1. **Node labels with multi-line inline documentation** — keep labels to name + one-liner + key metric. Put detail in the detail files.
2. **More than ~80 nodes in a single graph** — split into overview + detail files.
3. **`splines=ortho` with high node counts** — causes Graphviz rendering issues. Use `splines=true` or `splines=polyline` instead.
4. **Comment-only legends** — always use a rendered `cluster_legend` subgraph so the legend appears in the visual output.
5. **Inline prose in DOT comments** — DOT files are diagrams, not documentation. Keep comments to structural markers only.
```

### Step 2: Write the pre-scan agent prompt

Create `dot-docs/context/prescan-prompt.md`:

```markdown
# Pre-scan Agent Prompt

You are analyzing a repository to determine which investigation topics are relevant for producing DOT graph documentation.

## Your Input

You will be given:
- The repo's directory structure
- The repo's package configuration (pyproject.toml, Cargo.toml, package.json, or equivalent)
- The repo's README (if present)

## Your Task

Determine which of these four investigation topics are relevant for this repo:

1. **module_architecture** — Module boundaries, dependencies, composition graph. **Always relevant** for every repo.

2. **execution_flows** — Key execution paths, lifecycle sequences, entry points. Relevant when the repo has:
   - CLI entry points or `__main__.py`
   - Server/API handlers
   - Orchestrators, runners, or pipeline executors
   - `main()` functions or equivalent entry points

3. **state_machines** — State enums, transitions, data model relationships. Relevant when the repo has:
   - Enum classes representing states (e.g., `Status`, `Phase`, `Stage`)
   - Data models with lifecycle transitions
   - Event systems or message-driven architectures
   - State management patterns (stores, reducers, state machines)

4. **integration** — Cross-boundary data flows, what crosses module boundaries. Relevant when the repo has:
   - More than 3 packages/modules with inter-dependencies
   - Plugin or extension architectures
   - Bundle/composition systems
   - Cross-boundary data transformations

## Your Output

Produce a JSON array of topic strings. Always include `"module_architecture"`. Include the others only when the repo's content warrants them.

**Example for a simple utility library (2 modules, no state):**
```json
["module_architecture"]
```

**Example for a complex orchestrator (8 modules, state machine, CLI):**
```json
["module_architecture", "execution_flows", "state_machines", "integration"]
```

Output ONLY the JSON array. No prose, no markdown wrapping — just the array.
```

### Step 3: Write the pre-scan recipe

Create `dot-docs/recipes/dotfiles-prescan.yaml`:

```yaml
# Dotfiles Pre-scan — Topic Selection for a Single Repository
# Analyzes a repo's structure and determines which investigation topics
# are relevant for DOT graph generation.
#
# Usage:
#   amplifier run "execute dot-docs:recipes/dotfiles-prescan.yaml with repo_path='/path/to/repo'"
#
# Output: topics (JSON array of topic strings)

name: "dotfiles-prescan"
description: "Analyze a repo and determine which investigation topics to pursue"
version: "0.1.0"
author: "dot-docs bundle"
tags: ["dotfiles", "prescan", "topic-selection"]

context:
  repo_path: ""  # Required: path to the repository to analyze

steps:
  # Step 1: Gather repo metadata for the prescan agent
  - id: "gather-metadata"
    type: "bash"
    command: |
      REPO="{{repo_path}}"

      echo "=== DIRECTORY STRUCTURE ==="
      # Show top 3 levels of directory tree, excluding hidden dirs and common noise
      find "$REPO" -maxdepth 3 -type f \
        -not -path '*/.git/*' \
        -not -path '*/__pycache__/*' \
        -not -path '*/.venv/*' \
        -not -path '*/node_modules/*' \
        -not -path '*/.investigation/*' \
        | sort

      echo ""
      echo "=== PACKAGE CONFIG ==="
      # Print the first package config found
      for cfg in pyproject.toml Cargo.toml package.json setup.py setup.cfg; do
        if [ -f "$REPO/$cfg" ]; then
          echo "--- $cfg ---"
          cat "$REPO/$cfg"
          echo ""
        fi
      done

      echo ""
      echo "=== README ==="
      for readme in README.md README.rst README.txt README; do
        if [ -f "$REPO/$readme" ]; then
          head -100 "$REPO/$readme"
          break
        fi
      done

      echo ""
      echo "=== PYTHON PACKAGES (directories with __init__.py) ==="
      find "$REPO" -name "__init__.py" -not -path '*/.git/*' -not -path '*/.venv/*' \
        | sed 's|/__init__.py||' | sort

      echo ""
      echo "=== STATE-LIKE PATTERNS ==="
      # Quick scan for enums, state classes, status fields
      grep -rl --include="*.py" -E "(class \w+(State|Status|Phase|Stage)|Enum\)|@dataclass)" "$REPO" 2>/dev/null \
        | head -20 || echo "(none found)"

      echo ""
      echo "=== ENTRY POINTS ==="
      # Check for CLI entry points, __main__.py, main() functions
      grep -rl --include="*.py" -E "(def main|__main__|entry_points|console_scripts)" "$REPO" 2>/dev/null \
        | head -20 || echo "(none found)"
    output: "repo_metadata"

  # Step 2: Agent analyzes metadata and produces topic list
  - id: "select-topics"
    prompt: |
      ## Repository Pre-scan for DOT Documentation

      Analyze this repository's structure and determine which investigation topics
      are relevant for producing DOT graph documentation.

      **Repository path:** {{repo_path}}

      ### Repository Metadata

      {{repo_metadata}}

      ### Instructions

      @dot-docs:context/prescan-prompt.md

      Remember: output ONLY a JSON array of topic strings. No prose.
    output: "topics"
    parse_json: true
    timeout: 300

final_output: "topics"
```

### Step 4: Validate the recipe YAML syntax

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python3 -c "
import yaml
for f in ['recipes/dotfiles-prescan.yaml']:
    with open(f) as fh:
        data = yaml.safe_load(fh)
    print(f'{f}: OK — name={data[\"name\"]}, {len(data[\"steps\"])} steps')
"
```
Expected: `recipes/dotfiles-prescan.yaml: OK — name=dotfiles-prescan, 2 steps`

### Step 5: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "feat: DOT quality standards, pre-scan agent prompt, and pre-scan recipe"
```

---

## Task 5: Synthesis Prompt + Recipe

**Files:**
- Create: `dot-docs/context/synthesis-prompt.md`
- Create: `dot-docs/recipes/dotfiles-synthesis.yaml`

### Step 1: Write the synthesis agent prompt

Create `dot-docs/context/synthesis-prompt.md`:

```markdown
# Synthesis Agent Prompt

You are producing the final DOT graph documentation for a repository. You have access to all raw DOT files produced during investigation and must synthesize them into a coherent set of output files.

## Your Input

You will receive:
- All raw DOT files from the investigation workspace (one per agent per topic)
- The list of topics that were investigated
- The repo path for reference

## Your Task

1. **Read ALL raw DOT files** from the investigation workspace
2. **Reconcile overlapping content** — where multiple agents produced diagrams covering the same components, merge the best elements from each
3. **Choose the overview perspective** — decide which perspective best represents this repo's defining characteristic
4. **Produce `overview.dot`** — the single top-level file that any agent or human should read first
5. **Produce detail files** as warranted — `architecture.dot`, `sequence.dot`, `state-machines.dot`, `integration.dot`

## Choosing the Overview Perspective

The overview is NOT just a copy of one agent's output. It is a **synthesized** view that incorporates the best insights from all agents, corrections from verification/adversarial waves (if any), and your judgment about what best represents this repo.

Heuristic for which perspective to lead with:
- **Composition systems** (bundles, configs, wiring) → lead with architecture/composition
- **Execution engines** (orchestrators, pipelines, CLI tools) → lead with execution flow or state machine
- **Libraries/toolkits** (types, adapters, utilities) → lead with architecture/dependency
- **Repos with confirmed bugs** → lead with whichever diagram best annotates them

## Quality Standards

You MUST follow these standards. Read them carefully:

@dot-docs:context/dot-quality-standards.md

## Output Requirements

Write these files to the output directory:

### `overview.dot` (MANDATORY)
- 150-250 lines, under 15KB
- Follows ALL quality standards above
- Includes rendered legend subgraph
- Uses the shape vocabulary and edge style semantics consistently
- Annotates known issues with red nodes/edges

### Detail files (OPTIONAL — produce only if the repo warrants them)
- `architecture.dot` — module boundaries, dependencies, composition (200-400 lines)
- `sequence.dot` — key execution flows, lifecycle sequences (200-400 lines)
- `state-machines.dot` — state enums, transitions, data models (200-400 lines)
- `integration.dot` — cross-boundary data flows (200-400 lines)

Each detail file must use `subgraph` names that correspond to clusters in `overview.dot` so an agent can trace between them.

## What NOT To Do

- Do NOT produce `overview.dot` as a copy of one agent's raw output — synthesize
- Do NOT exceed 250 lines in overview.dot — split detail into the other files
- Do NOT use multi-line inline documentation in node labels
- Do NOT put more than ~80 nodes in any single graph
- Do NOT use `splines=ortho` with high node counts
- Do NOT use comment-only legends — use rendered `cluster_legend` subgraphs
```

### Step 2: Write the synthesis recipe

Create `dot-docs/recipes/dotfiles-synthesis.yaml`:

```yaml
# Dotfiles Synthesis — Produce Final DOT Files from Investigation Output
# Takes raw DOT files from a Parallax Discovery investigation and synthesizes
# them into the final overview.dot + detail files.
#
# Usage:
#   amplifier run "execute dot-docs:recipes/dotfiles-synthesis.yaml with
#     investigation_dir='/path/to/.investigation'
#     repo_path='/path/to/repo'
#     output_dir='/path/to/dotfiles/handle/repo'
#     topics='[\"module_architecture\", \"execution_flows\"]'"
#
# Output: synthesis_summary (text summary of what was produced)

name: "dotfiles-synthesis"
description: "Synthesize investigation DOT outputs into final overview.dot and detail files"
version: "0.1.0"
author: "dot-docs bundle"
tags: ["dotfiles", "synthesis", "dot-generation"]

context:
  investigation_dir: ""  # Required: path to the investigation workspace
  repo_path: ""          # Required: path to the original repository
  output_dir: ""         # Required: where to write the final DOT files
  topics: []             # Required: list of topics that were investigated

steps:
  # Step 1: Inventory all raw DOT files from the investigation
  - id: "inventory-dots"
    type: "bash"
    command: |
      INV="{{investigation_dir}}"
      echo "=== RAW DOT FILES ==="
      find "$INV" -name "*.dot" -type f | sort
      echo ""
      echo "=== RECONCILIATION DOCUMENTS ==="
      find "$INV" -name "reconciliation.md" -type f | sort
      echo ""
      echo "=== INVESTIGATION STRUCTURE ==="
      find "$INV" -maxdepth 3 -type d | sort
    output: "dot_inventory"

  # Step 2: Ensure output directory exists
  - id: "prepare-output"
    type: "bash"
    command: |
      mkdir -p "{{output_dir}}"
      mkdir -p "{{output_dir}}/.discovery"
      echo "Output directory ready: {{output_dir}}"
    output: "output_ready"

  # Step 3: Synthesis agent reads all DOT files and produces final output
  - id: "synthesize"
    prompt: |
      ## DOT Synthesis Assignment

      Produce the final DOT graph documentation for this repository.

      **Repository:** {{repo_path}}
      **Investigation workspace:** {{investigation_dir}}
      **Output directory:** {{output_dir}}
      **Topics investigated:** {{topics}}

      ### Available Investigation Artifacts

      {{dot_inventory}}

      ### Instructions

      @dot-docs:context/synthesis-prompt.md

      ### Steps

      1. Read ALL DOT files listed above from the investigation workspace
      2. Read any reconciliation documents for corrections and cross-cutting insights
      3. Synthesize the findings into final DOT files
      4. Write `overview.dot` to {{output_dir}}/overview.dot (MANDATORY)
      5. Write any warranted detail files to {{output_dir}}/ (OPTIONAL)

      After writing all files, respond with a summary of:
      - Which files you produced and their line counts
      - Which perspective you chose for the overview and why
      - Any issues or bugs annotated in the diagrams
    output: "synthesis_summary"
    timeout: 1800

  # Step 4: Validate the produced DOT files
  - id: "validate-output"
    type: "bash"
    command: |
      python3 << 'PYEOF'
      import sys
      sys.path.insert(0, "{{__recipe_dir__}}/../tools")

      from pathlib import Path
      from dotfiles_discovery.dot_validation import validate_dot_file

      output_dir = Path("{{output_dir}}")
      overview = output_dir / "overview.dot"

      if not overview.exists():
          print("FATAL: overview.dot was not produced!")
          sys.exit(1)

      result = validate_dot_file(overview)

      print(f"overview.dot validation:")
      print(f"  Syntax valid: {result.valid_syntax}")
      print(f"  Line count: {result.line_count}")
      print(f"  Line count in range: {result.line_count_in_range}")
      print(f"  Render OK: {result.render_ok}")

      if not result.valid_syntax:
          print(f"  ERROR: {result.syntax_error}")
          sys.exit(1)

      if not result.line_count_in_range:
          print(f"  WARNING: Line count {result.line_count} outside 150-300 range")

      # Validate detail files too
      for name in ["architecture.dot", "sequence.dot", "state-machines.dot", "integration.dot"]:
          detail = output_dir / name
          if detail.exists():
              dr = validate_dot_file(detail, min_lines=50, max_lines=400)
              status = "OK" if dr.valid_syntax else f"ERROR: {dr.syntax_error}"
              print(f"{name}: {dr.line_count} lines — {status}")

      print("\nValidation complete.")
      PYEOF
    output: "validation_result"

final_output: "synthesis_summary"
```

### Step 3: Validate the recipe YAML syntax

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python3 -c "
import yaml
for f in ['recipes/dotfiles-synthesis.yaml']:
    with open(f) as fh:
        data = yaml.safe_load(fh)
    print(f'{f}: OK — name={data[\"name\"]}, {len(data[\"steps\"])} steps')
"
```
Expected: `recipes/dotfiles-synthesis.yaml: OK — name=dotfiles-synthesis, 4 steps`

### Step 4: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "feat: synthesis agent prompt and synthesis recipe"
```

---

## Task 6: Discovery Orchestrator Recipe

**Files:**
- Create: `dot-docs/recipes/dotfiles-discovery.yaml`

### Step 1: Write the outer-loop orchestrator recipe

This is the main entry point. It reads a profile, iterates repos, determines tiers, dispatches investigations, and runs synthesis.

Create `dot-docs/recipes/dotfiles-discovery.yaml`:

```yaml
# Dotfiles Discovery Orchestrator — Per-Person DOT Documentation Pipeline
# Manages the full lifecycle of DOT graph generation for a person's repos.
#
# Reads a person's profile to get their list of repos, determines which tier
# of investigation each repo needs, dispatches the appropriate investigation,
# and runs synthesis to produce the final DOT files.
#
# Usage:
#   amplifier run "execute dot-docs:recipes/dotfiles-discovery.yaml with
#     profile_path='/path/to/profile.yaml'
#     dotfiles_root='/path/to/dotfiles/handle'
#     repos_root='/path/to/cloned/repos'"
#
# Tiers:
#   1: Full Parallax Discovery (3 waves, approval gates) — first-ever run
#   2: Single-wave refresh (Wave 1 + synthesis, auto-approved) — structural changes
#   3: Targeted update (single agent patches subgraphs) — minor changes
#   0: Skip — no changes since last run

name: "dotfiles-discovery"
description: "Orchestrate DOT graph generation for all of a person's Amplifier repos"
version: "0.1.0"
author: "dot-docs bundle"
tags: ["dotfiles", "discovery", "orchestration"]

recursion:
  max_depth: 3
  max_total_steps: 100

context:
  profile_path: ""    # Required: path to the person's profile.yaml
  dotfiles_root: ""   # Required: root of this person's dotfiles dir (e.g., dotfiles/bkrabach)
  repos_root: ""      # Required: where repos are cloned locally

stages:
  # ==========================================================================
  # STAGE 1: Setup — Read profile, enumerate repos, determine tiers
  # ==========================================================================
  - name: "setup"
    steps:
      # Read the profile to get the list of repos
      - id: "read-profile"
        type: "bash"
        command: |
          python3 << 'PYEOF'
          import json, yaml
          from pathlib import Path

          profile_path = Path("{{profile_path}}")
          if not profile_path.exists():
              print(json.dumps({"error": f"Profile not found: {profile_path}"}))
          else:
              with open(profile_path) as f:
                  profile = yaml.safe_load(f)
              repos = profile.get("repos", [])
              print(json.dumps({"repos": repos, "handle": profile.get("github_handle", "unknown")}))
          PYEOF
        output: "profile"
        parse_json: true

      # For each repo, determine the discovery tier needed
      - id: "determine-tiers"
        type: "bash"
        command: |
          python3 << 'PYEOF'
          import json, sys
          sys.path.insert(0, "{{__recipe_dir__}}/../tools")

          from pathlib import Path
          from dotfiles_discovery.structural_change import detect_changes
          from dotfiles_discovery.discovery_metadata import read_last_run, get_force_tier

          repos = json.loads("""{{profile.repos}}""") if isinstance("{{profile.repos}}", str) else {{profile.repos}}
          repos_root = Path("{{repos_root}}")
          dotfiles_root = Path("{{dotfiles_root}}")

          plan = []
          for repo_name in repos:
              repo_path = repos_root / repo_name
              repo_dotfiles = dotfiles_root / repo_name
              discovery_dir = repo_dotfiles / ".discovery"

              if not repo_path.exists():
                  plan.append({
                      "repo": repo_name,
                      "tier": -1,
                      "reason": f"Repo not found at {repo_path}",
                      "repo_path": str(repo_path),
                      "output_dir": str(repo_dotfiles),
                  })
                  continue

              # Check for force_tier override
              forced = get_force_tier(discovery_dir)
              if forced is not None:
                  plan.append({
                      "repo": repo_name,
                      "tier": forced,
                      "reason": f"Forced to tier {forced} via last-run.json",
                      "repo_path": str(repo_path),
                      "output_dir": str(repo_dotfiles),
                  })
                  continue

              # Read last run metadata for the commit hash
              last_run = read_last_run(discovery_dir)
              last_commit = last_run.commit_hash if last_run and last_run.status == "completed" else None

              result = detect_changes(repo_path, last_commit)
              plan.append({
                  "repo": repo_name,
                  "tier": result.tier,
                  "reason": result.reason,
                  "repo_path": str(repo_path),
                  "output_dir": str(repo_dotfiles),
                  "current_commit": result.current_commit,
              })

          print(json.dumps(plan))
          PYEOF
        output: "tier_plan"
        parse_json: true

      # Display the tier plan for the user
      - id: "display-plan"
        type: "bash"
        command: |
          python3 << 'PYEOF'
          import json

          plan = json.loads("""{{tier_plan}}""")
          tier_labels = {-1: "SKIP (not found)", 0: "SKIP (unchanged)", 1: "FULL", 2: "WAVE", 3: "PATCH"}

          print("=" * 60)
          print("  DOTFILES DISCOVERY — TIER PLAN")
          print("=" * 60)
          for entry in plan:
              label = tier_labels.get(entry["tier"], f"TIER {entry['tier']}")
              print(f"  [{label:>18}] {entry['repo']}")
              print(f"                      {entry['reason']}")
          print("=" * 60)
          PYEOF
        output: "plan_display"

  # ==========================================================================
  # STAGE 2: Investigation — Process each repo at its determined tier
  # Approval gate lets the user review the tier plan before proceeding.
  # ==========================================================================
  - name: "investigation"
    steps:
      # Process each repo according to its tier
      - id: "process-repos"
        foreach: "{{tier_plan}}"
        as: "repo_entry"
        parallel: false
        type: "bash"
        command: |
          python3 << 'PYEOF'
          import json

          entry = json.loads("""{{repo_entry}}""")
          tier = entry["tier"]
          repo = entry["repo"]

          if tier <= 0:
              print(f"Skipping {repo}: {entry['reason']}")
          elif tier == 1:
              print(f"TIER 1 — Full Parallax Discovery for {repo}")
              print(f"  Dispatch: parallax-discovery recipe against {entry['repo_path']}")
              print(f"  Output: {entry['output_dir']}")
          elif tier == 2:
              print(f"TIER 2 — Single-wave refresh for {repo}")
              print(f"  Dispatch: Wave 1 triplicates + synthesis against {entry['repo_path']}")
          elif tier == 3:
              print(f"TIER 3 — Targeted update for {repo}")
              print(f"  Dispatch: single agent diff-patch against {entry['repo_path']}")

          print(json.dumps({"processed": repo, "tier": tier}))
          PYEOF
        collect: "processing_results"
        timeout: 600

      # For Tier 1 repos: run pre-scan to determine topics
      - id: "prescan-repos"
        foreach: "{{tier_plan}}"
        as: "repo_entry"
        parallel: false
        condition: "{{repo_entry.tier}} == 1 or {{repo_entry.tier}} == 2"
        type: "recipe"
        recipe: "@dot-docs:recipes/dotfiles-prescan.yaml"
        context:
          repo_path: "{{repo_entry.repo_path}}"
        collect: "prescan_results"
        timeout: 600

    approval:
      required: true
      prompt: |
        ## Discovery Plan Ready

        The tier plan and pre-scan results are ready for review.

        ### Tier Plan
        {{plan_display}}

        ### What to Review
        - Are the tier assignments correct?
        - Should any repos be forced to a different tier?
        - Are the pre-scan topic selections appropriate?

        **APPROVE** to proceed with investigation and synthesis.
        **DENY** to stop.

  # ==========================================================================
  # STAGE 3: Synthesis & Post-processing
  # Run synthesis for each investigated repo, validate output, write metadata.
  # ==========================================================================
  - name: "synthesis"
    steps:
      # Run synthesis for each repo that was investigated
      - id: "run-synthesis"
        foreach: "{{tier_plan}}"
        as: "repo_entry"
        parallel: false
        condition: "{{repo_entry.tier}} >= 1"
        type: "recipe"
        recipe: "@dot-docs:recipes/dotfiles-synthesis.yaml"
        context:
          investigation_dir: "{{repo_entry.repo_path}}/.investigation"
          repo_path: "{{repo_entry.repo_path}}"
          output_dir: "{{repo_entry.output_dir}}"
          topics: "{{prescan_results}}"
        collect: "synthesis_results"
        timeout: 3600

      # Write discovery metadata for each processed repo
      - id: "write-metadata"
        type: "bash"
        command: |
          python3 << 'PYEOF'
          import json, sys
          from datetime import datetime, timezone
          sys.path.insert(0, "{{__recipe_dir__}}/../tools")

          from pathlib import Path
          from dotfiles_discovery.discovery_metadata import (
              LastRunMetadata, ManifestMetadata,
              write_last_run, write_manifest,
          )

          plan = json.loads("""{{tier_plan}}""")

          for entry in plan:
              tier = entry["tier"]
              if tier <= 0:
                  continue

              output_dir = Path(entry["output_dir"])
              discovery_dir = output_dir / ".discovery"

              # Count produced DOT files
              dot_files = [f.name for f in output_dir.glob("*.dot")] if output_dir.exists() else []

              write_last_run(discovery_dir, LastRunMetadata(
                  timestamp=datetime.now(timezone.utc).isoformat(),
                  tier=tier,
                  commit_hash=entry.get("current_commit", ""),
                  wave_count=3 if tier == 1 else (1 if tier == 2 else 0),
                  status="completed",
              ))

              write_manifest(discovery_dir, ManifestMetadata(
                  topics=[],  # Will be populated from prescan results
                  agent_count=18 if tier == 1 else (9 if tier == 2 else 1),
                  dot_files_produced=dot_files,
                  overview_perspective="",  # Set by synthesis agent
              ))

              print(f"Metadata written for {entry['repo']}: {len(dot_files)} DOT files")

          print("All metadata written.")
          PYEOF
        output: "metadata_result"

      # Final summary
      - id: "final-summary"
        type: "bash"
        command: |
          echo "============================================"
          echo "  DOTFILES DISCOVERY — COMPLETE"
          echo "============================================"
          echo ""
          echo "  Dotfiles root: {{dotfiles_root}}"
          echo ""
          echo "  {{metadata_result}}"
          echo ""
          echo "============================================"
        output: "discovery_complete"

final_output: "discovery_complete"
```

### Step 2: Validate the recipe YAML syntax

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && python3 -c "
import yaml
with open('recipes/dotfiles-discovery.yaml') as f:
    data = yaml.safe_load(f)
print(f'OK — name={data[\"name\"]}, {len(data[\"stages\"])} stages')
for stage in data['stages']:
    print(f'  stage: {stage[\"name\"]} — {len(stage[\"steps\"])} steps')
"
```
Expected:
```
OK — name=dotfiles-discovery, 3 stages
  stage: setup — 3 steps
  stage: investigation — 2 steps
  stage: synthesis — 3 steps
```

### Step 3: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "feat: discovery orchestrator recipe with tier-based dispatch"
```

---

## Task 7: Fixture Repo

**Files:**
- Create: `dot-docs/tests/fixtures/mock-repo/pyproject.toml`
- Create: `dot-docs/tests/fixtures/mock-repo/README.md`
- Create: `dot-docs/tests/fixtures/mock-repo/src/orchestrator/__init__.py`
- Create: `dot-docs/tests/fixtures/mock-repo/src/orchestrator/runner.py`
- Create: `dot-docs/tests/fixtures/mock-repo/src/orchestrator/state.py`
- Create: `dot-docs/tests/fixtures/mock-repo/src/processor/__init__.py`
- Create: `dot-docs/tests/fixtures/mock-repo/src/processor/transform.py`
- Create: `dot-docs/tests/fixtures/mock-repo/src/utils/__init__.py`
- Create: `dot-docs/tests/fixtures/mock-repo/src/utils/helpers.py`
- Create: `dot-docs/tests/fixtures/mock-repo/bundles/default.yaml`
- Create: `dot-docs/tests/fixtures/mock-repo/bundles/advanced.yaml`

### Step 1: Create the mock repo files

This fixture represents a small but realistic repo with 3 Python packages, a state enum, CLI entry points, and 2 bundle configs — enough structure to exercise all 4 investigation topics.

Create `dot-docs/tests/fixtures/mock-repo/pyproject.toml`:

```toml
[project]
name = "mock-system"
version = "0.1.0"
description = "A mock system for testing dotfiles discovery"
requires-python = ">=3.11"

[project.scripts]
mock-run = "orchestrator.runner:main"
mock-transform = "processor.transform:cli"
```

Create `dot-docs/tests/fixtures/mock-repo/README.md`:

```markdown
# Mock System

A small orchestration system with three components:

- **orchestrator** — Manages pipeline execution lifecycle with state transitions
- **processor** — Data transformation and validation pipeline
- **utils** — Shared helper functions used across components

## Architecture

The orchestrator reads bundle configs, manages state transitions through
`Pending → Running → Completed/Failed`, and dispatches work to the processor.
The processor applies transforms defined in the bundle config. Both components
use shared utilities for logging and validation.
```

Create `dot-docs/tests/fixtures/mock-repo/src/orchestrator/__init__.py`:

```python
"""Orchestrator package — manages pipeline execution lifecycle."""

from orchestrator.state import PipelineState

__all__ = ["PipelineState"]
```

Create `dot-docs/tests/fixtures/mock-repo/src/orchestrator/runner.py`:

```python
"""Pipeline runner — the main entry point for execution."""

from __future__ import annotations

from orchestrator.state import PipelineState, Transition
from processor.transform import apply_transforms
from utils.helpers import load_config, validate_input


def main() -> None:
    """CLI entry point: load config, validate, run pipeline."""
    config = load_config("bundles/default.yaml")
    pipeline = Pipeline(config)
    pipeline.run()


class Pipeline:
    """Orchestrates a sequence of transforms with state tracking."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.state = PipelineState.PENDING
        self.results: list[dict] = []

    def run(self) -> None:
        """Execute the pipeline through its state transitions."""
        self.state = Transition.advance(self.state)  # PENDING → RUNNING

        data = self.config.get("input_data", {})
        if not validate_input(data):
            self.state = PipelineState.FAILED
            return

        transforms = self.config.get("transforms", [])
        self.results = apply_transforms(data, transforms)
        self.state = Transition.advance(self.state)  # RUNNING → COMPLETED
```

Create `dot-docs/tests/fixtures/mock-repo/src/orchestrator/state.py`:

```python
"""Pipeline state machine — defines lifecycle states and transitions."""

from __future__ import annotations

from enum import Enum


class PipelineState(Enum):
    """Lifecycle states for a pipeline execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Transition:
    """State transition logic for the pipeline."""

    VALID_TRANSITIONS: dict[PipelineState, list[PipelineState]] = {
        PipelineState.PENDING: [PipelineState.RUNNING],
        PipelineState.RUNNING: [PipelineState.COMPLETED, PipelineState.FAILED],
        PipelineState.COMPLETED: [],
        PipelineState.FAILED: [PipelineState.PENDING],  # retry
    }

    @staticmethod
    def advance(current: PipelineState) -> PipelineState:
        """Move to the next valid state. Raises ValueError if no valid transition."""
        valid = Transition.VALID_TRANSITIONS.get(current, [])
        if not valid:
            raise ValueError(f"No valid transition from {current}")
        return valid[0]

    @staticmethod
    def can_transition(current: PipelineState, target: PipelineState) -> bool:
        """Check if a specific transition is valid."""
        return target in Transition.VALID_TRANSITIONS.get(current, [])
```

Create `dot-docs/tests/fixtures/mock-repo/src/processor/__init__.py`:

```python
"""Processor package — data transformation pipeline."""
```

Create `dot-docs/tests/fixtures/mock-repo/src/processor/transform.py`:

```python
"""Data transformation module — applies configured transforms to data."""

from __future__ import annotations

from utils.helpers import validate_input


def cli() -> None:
    """CLI entry point for standalone transform execution."""
    print("Transform CLI — use mock-run for full pipeline")


def apply_transforms(data: dict, transforms: list[dict]) -> list[dict]:
    """Apply a sequence of transforms to the input data.

    Each transform is a dict with 'type' and 'params' keys.
    Returns a list of result dicts, one per transform applied.
    """
    results = []
    for transform in transforms:
        t_type = transform.get("type", "identity")
        params = transform.get("params", {})

        if t_type == "filter":
            result = _apply_filter(data, params)
        elif t_type == "map":
            result = _apply_map(data, params)
        else:
            result = {"type": "identity", "output": data}

        results.append(result)
    return results


def _apply_filter(data: dict, params: dict) -> dict:
    """Filter data based on a key and allowed values."""
    key = params.get("key", "")
    allowed = params.get("allowed", [])
    filtered = {k: v for k, v in data.items() if k == key and v in allowed}
    return {"type": "filter", "output": filtered}


def _apply_map(data: dict, params: dict) -> dict:
    """Transform data values using a mapping."""
    mapping = params.get("mapping", {})
    mapped = {k: mapping.get(v, v) for k, v in data.items()}
    return {"type": "map", "output": mapped}
```

Create `dot-docs/tests/fixtures/mock-repo/src/utils/__init__.py`:

```python
"""Utils package — shared helpers used across components."""
```

Create `dot-docs/tests/fixtures/mock-repo/src/utils/helpers.py`:

```python
"""Shared helper functions for config loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_config(config_path: str) -> dict:
    """Load a YAML configuration file.

    Args:
        config_path: Path to the YAML file, relative to the project root.

    Returns:
        Parsed configuration as a dictionary.
    """
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def validate_input(data: dict) -> bool:
    """Validate that input data has required fields.

    Returns True if the data is valid, False otherwise.
    """
    if not isinstance(data, dict):
        return False
    # Minimal validation: data must be non-empty
    return len(data) > 0
```

Create `dot-docs/tests/fixtures/mock-repo/bundles/default.yaml`:

```yaml
# Default bundle configuration for the mock system
name: "default"
description: "Standard processing pipeline with basic transforms"

input_data:
  source: "file"
  format: "json"

transforms:
  - type: "filter"
    params:
      key: "status"
      allowed: ["active", "pending"]
  - type: "map"
    params:
      mapping:
        active: "processed"
        pending: "queued"
```

Create `dot-docs/tests/fixtures/mock-repo/bundles/advanced.yaml`:

```yaml
# Advanced bundle configuration with additional processing stages
name: "advanced"
description: "Extended pipeline with multi-stage transforms and retry logic"

input_data:
  source: "api"
  format: "json"
  retry_count: 3

transforms:
  - type: "filter"
    params:
      key: "priority"
      allowed: ["high", "critical"]
  - type: "map"
    params:
      mapping:
        high: "elevated"
        critical: "immediate"
  - type: "identity"
```

### Step 2: Verify the fixture structure

Run:
```bash
find /home/bkrabach/dev/dot-docs/dot-docs/tests/fixtures/mock-repo -type f | sort
```
Expected:
```
.../mock-repo/README.md
.../mock-repo/bundles/advanced.yaml
.../mock-repo/bundles/default.yaml
.../mock-repo/pyproject.toml
.../mock-repo/src/orchestrator/__init__.py
.../mock-repo/src/orchestrator/runner.py
.../mock-repo/src/orchestrator/state.py
.../mock-repo/src/processor/__init__.py
.../mock-repo/src/processor/transform.py
.../mock-repo/src/utils/__init__.py
.../mock-repo/src/utils/helpers.py
```
(11 files total)

### Step 3: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "feat: fixture mock-repo with 3 packages, state machine, and bundle configs"
```

---

## Task 8: End-to-End Integration Test

**Files:**
- Create: `dot-docs/tests/test_end_to_end.py`

This test exercises the Python infrastructure components together: structural change detection → metadata management → DOT validation. It does NOT invoke the LLM-powered recipes (those require a live Amplifier session to test manually).

### Step 1: Write the integration test

Create `dot-docs/tests/test_end_to_end.py`:

```python
"""End-to-end integration test for dotfiles discovery infrastructure.

Tests the full Python toolchain working together:
  1. Structural change detection on the fixture mock-repo
  2. Metadata creation and management
  3. DOT validation on a synthesized overview.dot

Does NOT test the LLM-powered recipes (prescan, synthesis, orchestrator).
Those are tested by running the recipes manually against a real repo.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from conftest import VALID_DOT, git_commit

from dotfiles_discovery.discovery_metadata import (
    LastRunMetadata,
    ManifestMetadata,
    get_force_tier,
    read_last_run,
    read_manifest,
    write_last_run,
    write_manifest,
)
from dotfiles_discovery.dot_validation import validate_dot_file
from dotfiles_discovery.structural_change import detect_changes

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "mock-repo"

HAS_GRAPHVIZ = shutil.which("dot") is not None

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


@pytest.fixture
def mock_repo(tmp_path: Path) -> Path:
    """Create a git repo from the fixture mock-repo files."""
    repo = tmp_path / "mock-system"
    shutil.copytree(FIXTURES_DIR, repo)
    env = {**os.environ, **GIT_ENV}
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, env=env)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo, check=True, capture_output=True, env=env,
    )
    return repo


@pytest.fixture
def dotfiles_dir(tmp_path: Path) -> Path:
    """Create a temporary dotfiles output directory."""
    d = tmp_path / "dotfiles" / "testuser" / "mock-system"
    d.mkdir(parents=True)
    return d


class TestFullPipeline:
    """Test the complete infrastructure pipeline end-to-end."""

    def test_first_run_detects_tier_1(self, mock_repo: Path) -> None:
        """A repo with no prior discovery should be tier 1."""
        result = detect_changes(mock_repo, last_commit=None)
        assert result.tier == 1
        assert result.current_commit
        assert len(result.current_commit) == 40

    def test_tier_1_then_write_metadata_then_skip(
        self, mock_repo: Path, dotfiles_dir: Path
    ) -> None:
        """After a full run, the same commit should be a skip."""
        # Step 1: Detect tier 1 (first run)
        result = detect_changes(mock_repo, last_commit=None)
        assert result.tier == 1

        # Step 2: Simulate completed discovery by writing metadata
        discovery_dir = dotfiles_dir / ".discovery"
        write_last_run(
            discovery_dir,
            LastRunMetadata(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tier=1,
                commit_hash=result.current_commit,
                wave_count=3,
                status="completed",
            ),
        )
        write_manifest(
            discovery_dir,
            ManifestMetadata(
                topics=["module_architecture", "execution_flows", "state_machines", "integration"],
                agent_count=18,
                dot_files_produced=["overview.dot", "architecture.dot"],
                overview_perspective="architecture",
            ),
        )

        # Step 3: Read back metadata
        last_run = read_last_run(discovery_dir)
        assert last_run is not None
        assert last_run.status == "completed"
        assert last_run.tier == 1

        manifest = read_manifest(discovery_dir)
        assert manifest is not None
        assert len(manifest.topics) == 4

        # Step 4: Same commit should now skip
        result2 = detect_changes(mock_repo, last_commit=last_run.commit_hash)
        assert result2.tier == 0

    def test_minor_edit_triggers_tier_3(
        self, mock_repo: Path, dotfiles_dir: Path
    ) -> None:
        """A small edit after a completed run should trigger tier 3."""
        env = {**os.environ, **GIT_ENV}

        # Record the initial commit
        initial_result = detect_changes(mock_repo, last_commit=None)
        initial_commit = initial_result.current_commit

        # Make a minor edit
        (mock_repo / "src" / "utils" / "helpers.py").write_text(
            "# Updated\ndef load_config(path):\n    pass\n"
        )
        subprocess.run(["git", "add", "."], cwd=mock_repo, check=True, capture_output=True, env=env)
        subprocess.run(
            ["git", "commit", "-m", "Minor edit"],
            cwd=mock_repo, check=True, capture_output=True, env=env,
        )

        # Should be tier 3 (minor change)
        result = detect_changes(mock_repo, last_commit=initial_commit)
        assert result.tier == 3

    def test_new_package_triggers_tier_2(
        self, mock_repo: Path, dotfiles_dir: Path
    ) -> None:
        """Adding a new Python package should trigger tier 2."""
        env = {**os.environ, **GIT_ENV}

        initial_result = detect_changes(mock_repo, last_commit=None)
        initial_commit = initial_result.current_commit

        # Add a new package
        new_pkg = mock_repo / "src" / "analytics"
        new_pkg.mkdir(parents=True)
        (new_pkg / "__init__.py").write_text("")
        (new_pkg / "metrics.py").write_text("def track():\n    pass\n")
        subprocess.run(["git", "add", "."], cwd=mock_repo, check=True, capture_output=True, env=env)
        subprocess.run(
            ["git", "commit", "-m", "Add analytics package"],
            cwd=mock_repo, check=True, capture_output=True, env=env,
        )

        result = detect_changes(mock_repo, last_commit=initial_commit)
        assert result.tier == 2
        assert "src/analytics" in result.modules_added

    def test_force_tier_override(
        self, mock_repo: Path, dotfiles_dir: Path
    ) -> None:
        """Setting force_tier should override the normal tier detection."""
        initial_result = detect_changes(mock_repo, last_commit=None)

        discovery_dir = dotfiles_dir / ".discovery"
        write_last_run(
            discovery_dir,
            LastRunMetadata(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tier=3,
                commit_hash=initial_result.current_commit,
                wave_count=1,
                status="completed",
                force_tier=1,
            ),
        )

        # The metadata says force_tier=1
        assert get_force_tier(discovery_dir) == 1

    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_dot_validation_on_valid_file(self, dotfiles_dir: Path) -> None:
        """A well-formed DOT file should pass all validation checks."""
        # Pad the valid DOT to reach the line count target
        lines = VALID_DOT.splitlines()
        while len(lines) < 180:
            lines.insert(-1, f"    // padding line {len(lines)}")
        padded_dot = "\n".join(lines) + "\n"

        dot_file = dotfiles_dir / "overview.dot"
        dot_file.write_text(padded_dot)

        result = validate_dot_file(dot_file)
        assert result.valid_syntax is True
        assert result.line_count_in_range is True
        assert result.render_ok is True

    def test_complete_lifecycle(
        self, mock_repo: Path, dotfiles_dir: Path
    ) -> None:
        """Full lifecycle: detect → investigate → write metadata → detect again."""
        env = {**os.environ, **GIT_ENV}

        # Phase 1: First run — tier 1
        r1 = detect_changes(mock_repo, last_commit=None)
        assert r1.tier == 1

        # Phase 2: Simulate discovery completion
        discovery_dir = dotfiles_dir / ".discovery"
        write_last_run(discovery_dir, LastRunMetadata(
            timestamp=datetime.now(timezone.utc).isoformat(),
            tier=1,
            commit_hash=r1.current_commit,
            wave_count=3,
            status="completed",
        ))

        # Phase 3: No changes — skip
        r2 = detect_changes(mock_repo, last_commit=r1.current_commit)
        assert r2.tier == 0

        # Phase 4: Minor edit — tier 3
        (mock_repo / "src" / "orchestrator" / "runner.py").write_text("# v2\n")
        subprocess.run(["git", "add", "."], cwd=mock_repo, check=True, capture_output=True, env=env)
        subprocess.run(
            ["git", "commit", "-m", "v2"],
            cwd=mock_repo, check=True, capture_output=True, env=env,
        )
        r3 = detect_changes(mock_repo, last_commit=r1.current_commit)
        assert r3.tier == 3

        # Phase 5: Update metadata after tier 3 run
        write_last_run(discovery_dir, LastRunMetadata(
            timestamp=datetime.now(timezone.utc).isoformat(),
            tier=3,
            commit_hash=r3.current_commit,
            wave_count=0,
            status="completed",
        ))

        # Phase 6: Add new package — tier 2
        new_pkg = mock_repo / "src" / "reporting"
        new_pkg.mkdir(parents=True)
        (new_pkg / "__init__.py").write_text("")
        subprocess.run(["git", "add", "."], cwd=mock_repo, check=True, capture_output=True, env=env)
        subprocess.run(
            ["git", "commit", "-m", "Add reporting"],
            cwd=mock_repo, check=True, capture_output=True, env=env,
        )
        r4 = detect_changes(mock_repo, last_commit=r3.current_commit)
        assert r4.tier == 2
        assert "src/reporting" in r4.modules_added


class TestMockRepoFixtureStructure:
    """Verify the mock-repo fixture has the expected shape."""

    def test_fixture_has_three_packages(self) -> None:
        packages = list(FIXTURES_DIR.glob("src/*/__init__.py"))
        package_names = sorted(p.parent.name for p in packages)
        assert package_names == ["orchestrator", "processor", "utils"]

    def test_fixture_has_state_enum(self) -> None:
        state_file = FIXTURES_DIR / "src" / "orchestrator" / "state.py"
        assert state_file.exists()
        content = state_file.read_text()
        assert "class PipelineState(Enum)" in content

    def test_fixture_has_entry_points(self) -> None:
        pyproject = FIXTURES_DIR / "pyproject.toml"
        assert pyproject.exists()
        content = pyproject.read_text()
        assert "mock-run" in content
        assert "mock-transform" in content

    def test_fixture_has_bundle_configs(self) -> None:
        bundles = list(FIXTURES_DIR.glob("bundles/*.yaml"))
        bundle_names = sorted(b.stem for b in bundles)
        assert bundle_names == ["advanced", "default"]

    def test_fixture_has_readme(self) -> None:
        assert (FIXTURES_DIR / "README.md").exists()
```

### Step 2: Run the integration tests

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/test_end_to_end.py -v
```
Expected: All tests PASS

### Step 3: Run the full test suite

Run:
```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/ -v
```
Expected: All tests across all 4 test files PASS

### Step 4: Commit

```bash
cd /home/bkrabach/dev/dot-docs && git add dot-docs/ && git commit -m "feat: end-to-end integration test and mock-repo fixture verification"
```

---

## Final Verification

After all tasks are complete, run the full test suite one last time:

```bash
cd /home/bkrabach/dev/dot-docs/dot-docs && pytest tests/ -v --tb=short
```

Expected output: All tests pass. The count should be approximately:
- `test_structural_change.py` — 9 tests
- `test_dot_validation.py` — 8 tests (some may skip without graphviz)
- `test_discovery_metadata.py` — 9 tests
- `test_end_to_end.py` — 11 tests

**Total: ~37 tests, 0 failures**

Verify the file structure:
```bash
find /home/bkrabach/dev/dot-docs/dot-docs -type f | grep -v __pycache__ | sort
```

Expected files (26 total):
```
dot-docs/context/dot-quality-standards.md
dot-docs/context/prescan-prompt.md
dot-docs/context/synthesis-prompt.md
dot-docs/docs/plans/2026-03-12-dotfiles-discovery-implementation.md
dot-docs/pyproject.toml
dot-docs/recipes/dotfiles-discovery.yaml
dot-docs/recipes/dotfiles-prescan.yaml
dot-docs/recipes/dotfiles-synthesis.yaml
dot-docs/tests/__init__.py
dot-docs/tests/conftest.py
dot-docs/tests/fixtures/mock-repo/README.md
dot-docs/tests/fixtures/mock-repo/bundles/advanced.yaml
dot-docs/tests/fixtures/mock-repo/bundles/default.yaml
dot-docs/tests/fixtures/mock-repo/pyproject.toml
dot-docs/tests/fixtures/mock-repo/src/orchestrator/__init__.py
dot-docs/tests/fixtures/mock-repo/src/orchestrator/runner.py
dot-docs/tests/fixtures/mock-repo/src/orchestrator/state.py
dot-docs/tests/fixtures/mock-repo/src/processor/__init__.py
dot-docs/tests/fixtures/mock-repo/src/processor/transform.py
dot-docs/tests/fixtures/mock-repo/src/utils/__init__.py
dot-docs/tests/fixtures/mock-repo/src/utils/helpers.py
dot-docs/tests/test_discovery_metadata.py
dot-docs/tests/test_dot_validation.py
dot-docs/tests/test_end_to_end.py
dot-docs/tests/test_structural_change.py
dot-docs/tools/dotfiles_discovery/__init__.py
dot-docs/tools/dotfiles_discovery/discovery_metadata.py
dot-docs/tools/dotfiles_discovery/dot_validation.py
dot-docs/tools/dotfiles_discovery/structural_change.py
```

## Commit History

After completing all tasks, `git log --oneline` should show:

```
feat: end-to-end integration test and mock-repo fixture verification
feat: fixture mock-repo with 3 packages, state machine, and bundle configs
feat: discovery orchestrator recipe with tier-based dispatch
feat: synthesis agent prompt and synthesis recipe
feat: DOT quality standards, pre-scan agent prompt, and pre-scan recipe
feat: discovery metadata manager (last-run.json, manifest.json, force_tier)
feat: DOT file validation utilities (syntax, line count, render check)
feat: structural change detector with tier recommendation logic
chore: scaffold dot-docs bundle with pyproject.toml and test fixtures
```

## What's Deferred (NOT in this plan)

- `bundle.md` manifest (the dot-docs bundle identity file)
- `team_knowledge` bundle integration
- Cross-repo DOT references
- SVG/PNG rendering alongside DOT source
- Parallelism across repos in the orchestrator
- Auto-approve confidence scoring for Tier 2 recipes
- Tier 2 and Tier 3 recipe dispatch (the orchestrator logs intent but currently only dispatches Tier 1 fully)
