"""Structural change detection for dotfiles discovery.

Determines the investigation tier for a repository based on git history
since the last discovery run.

Tier assignments:
    -1 — SKIP: repository not found on disk
     0 — SKIP: no changes since last discovery
     1 — FULL: full Parallax Discovery (no prior run or major structural change)
     2 — WAVE: single-wave investigation (structural changes detected)
     3 — PATCH: targeted investigation (minor/file-level changes only)

# TODO: The current implementation uses a simplified heuristic based on
# commit count and file type changes. A future version should use richer
# signals such as: dependency file changes (pyproject.toml, Cargo.toml),
# new directory creation, and deleted modules.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChangeResult:
    """Result from change detection analysis.

    Parameters
    ----------
    tier:
        Investigation tier (-1, 0, 1, 2, or 3).
    reason:
        Human-readable explanation for the tier assignment.
    current_commit:
        HEAD commit hash of the repository, or None if unavailable.
    """

    tier: int
    reason: str
    current_commit: str | None


def detect_changes(repo_path: str | Path, last_commit: str | None) -> ChangeResult:
    """Detect changes in a repository and assign an investigation tier.

    Compares the current HEAD against ``last_commit`` (the hash recorded
    from the previous discovery run). If ``last_commit`` is None, assumes
    no prior run and assigns Tier 1 (full investigation).

    Parameters
    ----------
    repo_path:
        Path to the git repository root.
    last_commit:
        Commit hash from the last discovery run, or None for first run.

    Returns
    -------
    ChangeResult
        Tier assignment with reason and current HEAD commit.
    """
    repo_path = Path(repo_path)

    # Get current HEAD commit
    head_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    current_commit = head_result.stdout.strip() if head_result.returncode == 0 else None

    # No prior run → full investigation
    if last_commit is None:
        return ChangeResult(
            tier=1,
            reason="No prior discovery run — full investigation required",
            current_commit=current_commit,
        )

    # No new commits → skip
    if current_commit and current_commit == last_commit:
        return ChangeResult(
            tier=0,
            reason="No commits since last discovery",
            current_commit=current_commit,
        )

    # Count commits since last run
    log_result = subprocess.run(
        ["git", "rev-list", "--count", f"{last_commit}..HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    commit_count = 0
    if log_result.returncode == 0:
        try:
            commit_count = int(log_result.stdout.strip())
        except ValueError:
            commit_count = 0

    # Check for structural changes (new/deleted files, directory structure)
    diff_result = subprocess.run(
        ["git", "diff", "--name-status", f"{last_commit}..HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    structural_indicators = {
        "pyproject.toml",
        "Cargo.toml",
        "package.json",
        "go.mod",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
    }
    has_structural_change = False
    added_or_deleted = 0

    if diff_result.returncode == 0:
        for line in diff_result.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            status, filename = parts[0], parts[1]
            if status in ("A", "D"):
                added_or_deleted += 1
            if any(ind in filename for ind in structural_indicators):
                has_structural_change = True

    # Assign tier based on change signals
    if has_structural_change or commit_count > 20 or added_or_deleted > 10:
        return ChangeResult(
            tier=2,
            reason=(
                f"Structural changes detected: {commit_count} commits, "
                f"{added_or_deleted} files added/deleted"
            ),
            current_commit=current_commit,
        )

    if commit_count > 0:
        return ChangeResult(
            tier=3,
            reason=f"Minor changes: {commit_count} commits, {added_or_deleted} files added/deleted",
            current_commit=current_commit,
        )

    return ChangeResult(
        tier=0,
        reason="No meaningful changes detected",
        current_commit=current_commit,
    )
