"""Reconciliation utilities for dotfiles discovery.

Pure-function module — no global state, no file writes, no subprocess calls.

Functions:
    find_orphaned_dirs: Find directories on disk that have no profile entry.
    format_reconciliation_warning: Format a human-readable warning for orphans.
"""

from __future__ import annotations

from pathlib import Path


def find_orphaned_dirs(profile_repos: list[str], dotfiles_dir: Path) -> list[str]:
    """Find directories in dotfiles_dir that have no matching profile entry.

    Args:
        profile_repos: List of repo names from the profile.
        dotfiles_dir: Directory to scan for orphaned repo directories.

    Returns:
        Sorted list of directory names that exist on disk but not in the profile.
        Returns empty list if dotfiles_dir does not exist.
    """
    if not dotfiles_dir.exists():
        return []

    profile_set = set(profile_repos)
    on_disk = {
        entry.name
        for entry in dotfiles_dir.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    }
    orphans = on_disk - profile_set
    return sorted(orphans)


def format_reconciliation_warning(orphans: list[str]) -> str:
    """Format a warning message for orphaned directories.

    Args:
        orphans: List of orphaned directory names.

    Returns:
        Empty string if no orphans, otherwise a multi-line warning string.
        The warning includes a header, one line per orphan, and a call to action.
    """
    if not orphans:
        return ""

    lines = [
        "WARNING: The following output directories have no matching profile entry:",
    ]
    for name in orphans:
        lines.append(f"  - {name}")
    lines.append("Review these directories and remove them if the repo is no longer tracked.")

    return "\n".join(lines)
