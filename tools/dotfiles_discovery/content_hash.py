"""Content hashing for DOT graph files.

Pure functions for computing stable hashes that ignore volatile attributes
(generated_at) while remaining sensitive to structural changes (source_sha,
graph topology, etc.).

No global state, no file writes, no subprocess calls.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


def compute_dot_hash(content: str) -> str:
    """Return a stable SHA-256 hex digest of *content*.

    Strips the *value* of ``generated_at`` attributes before hashing so that
    timestamp-only regenerations do not appear as content changes.  The
    ``generated_at`` key itself and all other attributes (including
    ``source_sha``) are left intact.

    Args:
        content: Raw DOT file contents as a string.

    Returns:
        64-character lowercase hex string.
    """
    normalized = re.sub(r'generated_at="[^"]*"', 'generated_at=""', content)
    return hashlib.sha256(normalized.encode()).hexdigest()


def should_update(existing_path: Path, new_content: str) -> bool:
    """Return *True* if the file at *existing_path* should be (re-)written.

    Compares the stable hash of *new_content* against the stable hash of the
    file currently on disk.  Returns *True* when:

    * ``existing_path`` does not exist, or
    * the hashes differ (i.e. the content has meaningfully changed).

    Args:
        existing_path: Path to the file on disk (may not exist).
        new_content:   The content that would be written.

    Returns:
        ``True`` if the file should be written/overwritten, ``False`` otherwise.
    """
    if not existing_path.exists():
        return True
    existing_content = existing_path.read_text()
    return compute_dot_hash(new_content) != compute_dot_hash(existing_content)
