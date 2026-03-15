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
