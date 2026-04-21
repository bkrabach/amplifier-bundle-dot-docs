"""DOT file validation utilities — syntax checking, line count, and SVG render quality."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SyntaxResult:
    """Result of a DOT syntax validation check."""

    valid_syntax: bool
    syntax_error: str | None = None
    svg_path: str | None = None


@dataclass
class LineCountResult:
    """Result of a line count range check."""

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


@dataclass
class EnhancedValidationResult:
    """Validation result enriched with optional dot_graph structural analysis."""

    basic: DotFileValidation
    dot_graph_available: bool
    structural_issues: list[str] | None
    quality_warnings: list[str] | None
    dot_graph_error: str | None

    @property
    def is_valid(self) -> bool:
        """True when the DOT file has valid syntax (delegates to basic)."""
        return self.basic.valid_syntax

    @property
    def has_warnings(self) -> bool:
        """True when line count is out of range, or structural/quality issues exist."""
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


def validate_dot_syntax(dot_path: str) -> SyntaxResult:
    """Validate DOT file syntax by running ``dot -Tsvg``.

    Parameters
    ----------
    dot_path:
        Path to the ``.dot`` file to validate.

    Returns
    -------
    SyntaxResult
        ``valid_syntax=True`` and ``svg_path`` set on success; ``valid_syntax=False``
        with a descriptive ``syntax_error`` on any failure.
    """
    path = Path(dot_path)

    # Check file exists
    if not path.exists():
        return SyntaxResult(valid_syntax=False, syntax_error=f"File not found: {dot_path}")

    # Check graphviz is available
    if shutil.which("dot") is None:
        return SyntaxResult(
            valid_syntax=False,
            syntax_error="graphviz is not installed or 'dot' is not on PATH",
        )

    svg_path = str(path.with_suffix(".svg"))
    try:
        subprocess.run(
            ["dot", "-Tsvg", str(path), "-o", svg_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() if exc.stderr else "dot command failed"
        return SyntaxResult(valid_syntax=False, syntax_error=error)
    except subprocess.TimeoutExpired:
        return SyntaxResult(
            valid_syntax=False, syntax_error="dot command timed out after 30 seconds"
        )

    return SyntaxResult(valid_syntax=True, syntax_error=None, svg_path=svg_path)


def check_line_count(dot_path: str, min_lines: int = 150, max_lines: int = 300) -> LineCountResult:
    """Count lines in a DOT file and check whether the count falls within a range.

    Parameters
    ----------
    dot_path:
        Path to the ``.dot`` file.  **Precondition:** the file must exist; a
        missing path raises ``FileNotFoundError``.  Use :func:`validate_dot_file`
        for a composite check that handles missing files gracefully.
    min_lines:
        Minimum acceptable line count (inclusive). Default ``150``.
    max_lines:
        Maximum acceptable line count (inclusive). Default ``300``.

    Returns
    -------
    LineCountResult
        Populated with the actual count and a boolean indicating range membership.
    """
    content = Path(dot_path).read_text(encoding="utf-8")
    count = len(content.splitlines())
    return LineCountResult(
        line_count=count,
        in_range=min_lines <= count <= max_lines,
        min_lines=min_lines,
        max_lines=max_lines,
    )


def check_svg_render(svg_path: str) -> tuple[bool, str | None]:
    """Check whether a rendered SVG looks valid.

    Validates existence, non-zero bounding box, and minimum file size.

    Parameters
    ----------
    svg_path:
        Path to the SVG file produced by ``dot -Tsvg``.

    Returns
    -------
    tuple[bool, str | None]
        ``(True, None)`` when the SVG passes all checks; ``(False, error_message)``
        otherwise.
    """
    path = Path(svg_path)

    if not path.exists():
        return False, f"SVG file not found: {svg_path}"

    content = path.read_text(encoding="utf-8", errors="replace")

    # Check minimum file size (>200 bytes)
    stat_result = path.stat()
    if stat_result.st_size <= 200:
        return False, f"SVG file too small ({stat_result.st_size} bytes), likely empty render"

    # Check for zero-width or zero-height bounding box.
    # Graphviz SVGs use 'pt' units (e.g. width="72pt"); these patterns cover
    # all known zero-dimension cases produced by the dot renderer.
    if 'width="0"' in content or 'height="0"' in content:
        return False, "SVG has zero-width or zero-height bounding box"
    if 'width="0pt"' in content or 'height="0pt"' in content:
        return False, "SVG has zero-width or zero-height bounding box"

    return True, None


def validate_dot_file(
    dot_path: str, min_lines: int = 150, max_lines: int = 300
) -> DotFileValidation:
    """Run all validation checks on a DOT file.

    Runs syntax validation, line count check, and (if syntax passed) SVG render
    quality check.

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
    DotFileValidation
        Combined result from all checks.
    """
    syntax_result = validate_dot_syntax(dot_path)

    # Guard: if file is missing, check_line_count would raise — return a coherent result
    if not Path(dot_path).exists():
        return DotFileValidation(
            valid_syntax=False,
            syntax_error=syntax_result.syntax_error,
            line_count=0,
            line_count_in_range=False,
            render_ok=False,
            render_error=None,
        )

    line_result = check_line_count(dot_path, min_lines=min_lines, max_lines=max_lines)

    render_ok = False
    render_error: str | None = None
    if syntax_result.valid_syntax and syntax_result.svg_path:
        render_ok, render_error = check_svg_render(syntax_result.svg_path)

    return DotFileValidation(
        valid_syntax=syntax_result.valid_syntax,
        syntax_error=syntax_result.syntax_error,
        line_count=line_result.line_count,
        line_count_in_range=line_result.in_range,
        render_ok=render_ok,
        render_error=render_error,
    )


def validate_with_dot_graph(
    dot_path: str, min_lines: int = 150, max_lines: int = 300
) -> EnhancedValidationResult:
    """Run basic validation plus optional dot_graph structural analysis.

    Always runs :func:`validate_dot_file` for syntax, line count, and render
    checks.  Then attempts to import ``dot_graph.validation`` and run its
    ``validate`` function for structural and quality analysis.  If the module
    is not installed, returns a 'not yet implemented' sentinel, raises
    ``FileNotFoundError``, or raises any other exception, the function falls
    back gracefully to basic-only results.

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
        Combined result from basic and (when available) structural analysis.
    """
    basic = validate_dot_file(dot_path, min_lines=min_lines, max_lines=max_lines)

    # Attempt dot_graph structural validation
    try:
        from dot_graph.validation import validate as dot_graph_validate  # type: ignore[import]
    except (ImportError, TypeError):
        return EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=None,
        )

    try:
        dg_result: dict = dot_graph_validate(dot_path)
    except FileNotFoundError:
        return EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=None,
        )
    except Exception as exc:  # noqa: BLE001
        return EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=str(exc),
        )

    # Handle 'not yet implemented' sentinel
    if dg_result.get("status") == "not yet implemented":
        return EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=None,
        )

    structural_issues: list[str] | None = dg_result.get("structural_issues") or None
    quality_warnings: list[str] | None = dg_result.get("quality_warnings") or None

    return EnhancedValidationResult(
        basic=basic,
        dot_graph_available=True,
        structural_issues=structural_issues,
        quality_warnings=quality_warnings,
        dot_graph_error=None,
    )
