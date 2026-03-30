"""Tests for dotfiles_discovery.reconciliation module.

RED phase: These tests are written BEFORE the module exists.
They verify the interface and behavior of reconciliation.py.

Expected result: all FAILED with ModuleNotFoundError until
tools/dotfiles_discovery/reconciliation.py is created.
"""

from __future__ import annotations

from pathlib import Path


class TestImport:
    """Verify the module and its public symbols are importable."""

    def test_module_importable(self) -> None:
        import dotfiles_discovery.reconciliation  # noqa: F401

    def test_find_orphaned_dirs_importable(self) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs  # noqa: F401

    def test_format_reconciliation_warning_importable(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning  # noqa: F401


class TestFindOrphanedDirs:
    """Verify find_orphaned_dirs() returns correct orphaned directory names.

    Function signature: find_orphaned_dirs(profile_repos: list[str], dotfiles_dir: Path) -> list[str]
    """

    def test_returns_empty_when_all_dirs_in_profile(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "repo-b").mkdir()
        result = find_orphaned_dirs(["repo-a", "repo-b"], tmp_path)
        assert result == []

    def test_returns_orphan_when_dir_not_in_profile(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "old-repo").mkdir()
        result = find_orphaned_dirs(["repo-a"], tmp_path)
        assert result == ["old-repo"]

    def test_returns_multiple_orphans_sorted(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "stale-z").mkdir()
        (tmp_path / "stale-a").mkdir()
        result = find_orphaned_dirs(["repo-a"], tmp_path)
        assert result == ["stale-a", "stale-z"]

    def test_ignores_files_not_directories(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "some-file.txt").write_text("not a directory")
        result = find_orphaned_dirs(["repo-a"], tmp_path)
        assert result == []

    def test_returns_empty_when_dotfiles_dir_missing(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        nonexistent = tmp_path / "does_not_exist"
        result = find_orphaned_dirs(["repo-a"], nonexistent)
        assert result == []

    def test_returns_empty_when_profile_is_empty_and_no_dirs(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        result = find_orphaned_dirs([], tmp_path)
        assert result == []

    def test_all_dirs_orphaned_when_profile_empty(self, tmp_path: Path) -> None:
        from dotfiles_discovery.reconciliation import find_orphaned_dirs

        (tmp_path / "repo-a").mkdir()
        (tmp_path / "repo-b").mkdir()
        result = find_orphaned_dirs([], tmp_path)
        assert result == ["repo-a", "repo-b"]


class TestFormatReconciliationWarning:
    """Verify format_reconciliation_warning() returns correctly formatted warning strings."""

    def test_empty_orphans_returns_empty_string(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning([])
        assert result == ""

    def test_single_orphan_mentions_repo_name(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning(["old-repo"])
        assert "old-repo" in result

    def test_multiple_orphans_all_mentioned(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning(["alpha", "beta", "gamma"])
        assert "alpha" in result
        assert "beta" in result
        assert "gamma" in result

    def test_warning_mentions_no_delete(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning(["old-repo"])
        lower = result.lower()
        assert "review" in lower or "remove" in lower or "delete" in lower

    def test_warning_contains_word_warning(self) -> None:
        from dotfiles_discovery.reconciliation import format_reconciliation_warning

        result = format_reconciliation_warning(["old-repo"])
        lower = result.lower()
        assert "warning" in lower
