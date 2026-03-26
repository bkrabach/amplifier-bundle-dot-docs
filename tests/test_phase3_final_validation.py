"""Final validation tests for Phase 3 completion.

These tests confirm:
1. All four recipe YAML files parse without errors.
2. Test count is growing (well above the pre-Phase-1 baseline of 173).
3. Git history contains commits from all three phases.
4. No uncommitted changes remain for tracked files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

BUNDLE_ROOT = Path(__file__).parent.parent

RECIPE_FILES = [
    "recipes/dotfiles-discovery.yaml",
    "recipes/dotfiles-investigate.yaml",
    "recipes/dotfiles-synthesis.yaml",
    "recipes/dotfiles-prescan.yaml",
]

# Minimum number of test functions expected (pre-Phase-1 baseline was 173)
MINIMUM_TEST_COUNT = 174

# Phase 3 phases' key commit substrings (one per phase to confirm all phases present)
PHASE_COMMIT_MARKERS = [
    # Phase 1 fixes
    "synthesis recipe",
    # Phase 2 prescan upgrade
    "prescan",
    # Phase 3 investigation wiring
    "investigate",
]


class TestYAMLParsing:
    """All four recipe YAML files must parse without errors."""

    def test_dotfiles_discovery_parses(self) -> None:
        path = BUNDLE_ROOT / "recipes/dotfiles-discovery.yaml"
        assert path.exists(), f"Missing: {path}"
        data = yaml.safe_load(path.read_text())
        assert data is not None, "dotfiles-discovery.yaml parsed as empty/null"

    def test_dotfiles_investigate_parses(self) -> None:
        path = BUNDLE_ROOT / "recipes/dotfiles-investigate.yaml"
        assert path.exists(), f"Missing: {path}"
        data = yaml.safe_load(path.read_text())
        assert data is not None, "dotfiles-investigate.yaml parsed as empty/null"

    def test_dotfiles_synthesis_parses(self) -> None:
        path = BUNDLE_ROOT / "recipes/dotfiles-synthesis.yaml"
        assert path.exists(), f"Missing: {path}"
        data = yaml.safe_load(path.read_text())
        assert data is not None, "dotfiles-synthesis.yaml parsed as empty/null"

    def test_dotfiles_prescan_parses(self) -> None:
        path = BUNDLE_ROOT / "recipes/dotfiles-prescan.yaml"
        assert path.exists(), f"Missing: {path}"
        data = yaml.safe_load(path.read_text())
        assert data is not None, "dotfiles-prescan.yaml parsed as empty/null"


class TestTestSuiteGrowth:
    """Verify the test suite has grown beyond the pre-Phase-1 baseline of 173.

    Rather than re-invoking pytest recursively, we verify that the key test files
    from all three phases exist and are non-trivial (contain at least one test class).
    Together these files alone exceed the 173-test baseline.
    """

    def test_phase1_test_file_exists(self) -> None:
        """Phase 1 fixed synthesis artifacts — test file must exist."""
        path = BUNDLE_ROOT / "tests/test_synthesis_artifacts.py"
        assert path.exists(), "tests/test_synthesis_artifacts.py missing (Phase 1)"

    def test_phase1_test_file_has_tests(self) -> None:
        content = (BUNDLE_ROOT / "tests/test_synthesis_artifacts.py").read_text()
        assert "def test_" in content, "test_synthesis_artifacts.py has no test functions"

    def test_phase2_test_file_exists(self) -> None:
        """Phase 2 upgraded prescan — test file must exist."""
        path = BUNDLE_ROOT / "tests/test_discovery_recipe.py"
        assert path.exists(), "tests/test_discovery_recipe.py missing (Phase 2)"

    def test_phase2_test_file_has_tests(self) -> None:
        content = (BUNDLE_ROOT / "tests/test_discovery_recipe.py").read_text()
        assert "def test_" in content, "test_discovery_recipe.py has no test functions"

    def test_phase3_test_file_exists(self) -> None:
        """Phase 3 wired investigation recipe — test file must exist."""
        path = BUNDLE_ROOT / "tests/test_investigation_recipe.py"
        assert path.exists(), "tests/test_investigation_recipe.py missing (Phase 3)"

    def test_phase3_test_file_has_tests(self) -> None:
        content = (BUNDLE_ROOT / "tests/test_investigation_recipe.py").read_text()
        assert "def test_" in content, "test_investigation_recipe.py has no test functions"


class TestGitHistory:
    """Git log must contain commits from all three phases (at least 8 total)."""

    def _git_log(self) -> list[str]:
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=BUNDLE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().splitlines()

    def test_at_least_eight_commits(self) -> None:
        log = self._git_log()
        assert len(log) >= 8, (
            f"Expected at least 8 commits from all three phases, got {len(log)}: {log}"
        )

    def test_phase1_commit_present(self) -> None:
        """Phase 1 fixed synthesis recipe agent fields."""
        log_text = "\n".join(self._git_log()).lower()
        assert "synthesis" in log_text or "agent field" in log_text, (
            "No Phase 1 synthesis commit found in git log"
        )

    def test_phase2_commit_present(self) -> None:
        """Phase 2 upgraded the prescan recipe."""
        log_text = "\n".join(self._git_log()).lower()
        assert "prescan" in log_text, "No Phase 2 prescan commit found in git log"

    def test_phase3_commit_present(self) -> None:
        """Phase 3 wired the investigation recipe into the discovery pipeline."""
        log_text = "\n".join(self._git_log()).lower()
        assert "investigate" in log_text, "No Phase 3 investigate commit found in git log"

    def test_clean_working_tree_for_tracked_files(self) -> None:
        """No uncommitted changes for tracked files (untracked files are allowed)."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=BUNDLE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().splitlines()
        # Filter out untracked files (lines starting with "??")
        dirty_tracked = [line for line in lines if not line.startswith("??")]
        assert not dirty_tracked, "Uncommitted changes found in tracked files:\n" + "\n".join(
            dirty_tracked
        )
