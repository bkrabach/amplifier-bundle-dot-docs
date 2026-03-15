"""Metadata persistence for dotfiles discovery runs.

Manages two JSON files inside each repo's ``.discovery/`` directory:

- ``last-run.json``  — records the previous discovery run (commit hash, tier, timestamp)
- ``manifest.json``  — records the DOT files produced and investigation topics

These files are read during ``determine-tiers`` to compute change-based tier
assignments, and written during ``write-metadata`` after synthesis completes.

# TODO: Add schema versioning and migration helpers once the metadata format
# stabilises across multiple releases.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class LastRunMetadata:
    """Record of a single completed discovery run.

    Parameters
    ----------
    timestamp:
        ISO-8601 UTC timestamp of when the run completed.
    tier:
        Investigation tier that was executed (1, 2, or 3).
    commit_hash:
        HEAD commit SHA recorded at the start of the run.
    wave_count:
        Number of investigation waves completed.
    status:
        Final status string, e.g. ``"completed"`` or ``"partial"``.
    reason:
        Human-readable reason for the tier assignment.
    """

    timestamp: str
    tier: int
    commit_hash: str
    wave_count: int
    status: str
    reason: str | None = None


@dataclass
class ManifestMetadata:
    """Index of artefacts produced during a discovery run.

    Parameters
    ----------
    topics:
        Investigation topics covered during the run.
    dot_files_produced:
        Basenames of ``.dot`` files written to the output directory.
    """

    topics: list[str] = field(default_factory=list)
    dot_files_produced: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

_LAST_RUN_FILENAME = "last-run.json"
_MANIFEST_FILENAME = "manifest.json"
_FORCE_TIER_FILENAME = "force-tier.json"


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def read_last_run(discovery_dir: str | Path) -> LastRunMetadata | None:
    """Read the last-run metadata record for a repository.

    Parameters
    ----------
    discovery_dir:
        Path to the ``.discovery/`` directory inside the repo's output folder.

    Returns
    -------
    LastRunMetadata or None
        The previous run record, or ``None`` if no record exists yet.
    """
    path = Path(discovery_dir) / _LAST_RUN_FILENAME
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return LastRunMetadata(
            timestamp=data.get("timestamp", ""),
            tier=int(data.get("tier", 1)),
            commit_hash=data.get("commit_hash", ""),
            wave_count=int(data.get("wave_count", 0)),
            status=data.get("status", "completed"),
            reason=data.get("reason"),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def get_force_tier(discovery_dir: str | Path) -> int | None:
    """Return a forced tier override, if one is configured.

    A ``force-tier.json`` file with ``{"tier": N}`` inside the
    ``.discovery/`` directory overrides normal change-based tier detection.
    The file is not consumed (deleted) automatically; the caller is
    responsible for removing it after use if desired.

    Parameters
    ----------
    discovery_dir:
        Path to the ``.discovery/`` directory inside the repo's output folder.

    Returns
    -------
    int or None
        The forced tier value, or ``None`` if no override is configured.
    """
    path = Path(discovery_dir) / _FORCE_TIER_FILENAME
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tier = data.get("tier")
        if tier is not None:
            return int(tier)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass
    return None


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def write_last_run(discovery_dir: str | Path, metadata: LastRunMetadata) -> None:
    """Write the last-run metadata record to disk.

    Creates the ``.discovery/`` directory if it does not already exist.

    Parameters
    ----------
    discovery_dir:
        Path to the ``.discovery/`` directory inside the repo's output folder.
    metadata:
        The run record to persist.
    """
    discovery_dir = Path(discovery_dir)
    discovery_dir.mkdir(parents=True, exist_ok=True)
    path = discovery_dir / _LAST_RUN_FILENAME
    path.write_text(json.dumps(asdict(metadata), indent=2, ensure_ascii=False), encoding="utf-8")


def write_manifest(discovery_dir: str | Path, manifest: ManifestMetadata) -> None:
    """Write the manifest record to disk.

    Creates the ``.discovery/`` directory if it does not already exist.

    Parameters
    ----------
    discovery_dir:
        Path to the ``.discovery/`` directory inside the repo's output folder.
    manifest:
        The manifest record to persist.
    """
    discovery_dir = Path(discovery_dir)
    discovery_dir.mkdir(parents=True, exist_ok=True)
    path = discovery_dir / _MANIFEST_FILENAME
    path.write_text(json.dumps(asdict(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
