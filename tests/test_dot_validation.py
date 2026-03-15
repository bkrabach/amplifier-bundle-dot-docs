"""Tests for DOT file validation utilities."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import INVALID_DOT, VALID_DOT
from dotfiles_discovery.dot_validation import (
    DotFileValidation,
    EnhancedValidationResult,
    check_line_count,
    validate_dot_file,
    validate_dot_syntax,
    validate_with_dot_graph,
)

HAS_GRAPHVIZ = shutil.which("dot") is not None


# ---------------------------------------------------------------------------
# TestValidateDotSyntax
# ---------------------------------------------------------------------------


class TestValidateDotSyntax:
    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_valid_dot_passes(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(VALID_DOT)
        result = validate_dot_syntax(str(dot_file))
        assert result.valid_syntax is True
        assert result.syntax_error is None

    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_invalid_dot_fails(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "broken.dot"
        dot_file.write_text(INVALID_DOT)
        result = validate_dot_syntax(str(dot_file))
        assert result.valid_syntax is False
        assert result.syntax_error is not None

    def test_missing_file_returns_error(self) -> None:
        result = validate_dot_syntax("/nonexistent/path/to/file.dot")
        assert result.valid_syntax is False
        assert result.syntax_error is not None
        assert "not found" in result.syntax_error

    def test_graphviz_not_available_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(VALID_DOT)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        result = validate_dot_syntax(str(dot_file))
        assert result.valid_syntax is False
        assert result.syntax_error is not None
        assert "graphviz" in result.syntax_error


# ---------------------------------------------------------------------------
# TestCheckLineCount
# ---------------------------------------------------------------------------


class TestCheckLineCount:
    def test_in_range(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text("\n" * 200)
        result = check_line_count(str(dot_file))
        assert result.line_count == 200
        assert result.in_range is True  # default range 150-300

    def test_too_few_lines(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text("\n" * 50)
        result = check_line_count(str(dot_file))
        assert result.line_count == 50
        assert result.in_range is False

    def test_too_many_lines(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text("\n" * 500)
        result = check_line_count(str(dot_file))
        assert result.line_count == 500
        assert result.in_range is False

    def test_custom_range(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text("\n" * 100)
        result = check_line_count(str(dot_file), min_lines=50, max_lines=150)
        assert result.line_count == 100
        assert result.in_range is True


# ---------------------------------------------------------------------------
# TestValidateDotFile
# ---------------------------------------------------------------------------


class TestValidateDotFile:
    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_valid_file_passes_all_checks(self, tmp_path: Path) -> None:
        # Pad VALID_DOT to ~180 lines with comment padding lines
        padding = "// padding\n" * 165
        dot_content = VALID_DOT + padding
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(dot_content)
        result = validate_dot_file(str(dot_file))
        assert result.valid_syntax is True
        assert result.line_count_in_range is True

    @pytest.mark.skipif(not HAS_GRAPHVIZ, reason="graphviz not installed")
    def test_invalid_file_reports_syntax_error(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "broken.dot"
        dot_file.write_text(INVALID_DOT)
        result = validate_dot_file(str(dot_file))
        assert result.valid_syntax is False

    def test_missing_file_returns_graceful_result(self) -> None:
        result = validate_dot_file("/nonexistent/path/to/missing.dot")
        assert result.valid_syntax is False
        assert result.syntax_error is not None
        assert result.line_count == 0
        assert result.line_count_in_range is False
        assert result.render_ok is False


# ---------------------------------------------------------------------------
# TestEnhancedValidationResult
# ---------------------------------------------------------------------------


class TestEnhancedValidationResult:
    """Unit tests for the EnhancedValidationResult dataclass properties."""

    def _make_basic(
        self,
        valid_syntax: bool = True,
        line_count_in_range: bool = True,
    ) -> DotFileValidation:
        return DotFileValidation(
            valid_syntax=valid_syntax,
            syntax_error=None if valid_syntax else "syntax error",
            line_count=200,
            line_count_in_range=line_count_in_range,
            render_ok=valid_syntax,
        )

    def test_is_valid_when_syntax_passes(self) -> None:
        basic = self._make_basic(valid_syntax=True)
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=None,
        )
        assert result.is_valid is True

    def test_is_not_valid_when_syntax_fails(self) -> None:
        basic = self._make_basic(valid_syntax=False)
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=None,
        )
        assert result.is_valid is False

    def test_has_warnings_when_line_count_out_of_range(self) -> None:
        basic = self._make_basic(line_count_in_range=False)
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=None,
        )
        assert result.has_warnings is True

    def test_has_warnings_when_structural_issues(self) -> None:
        basic = self._make_basic()
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=True,
            structural_issues=["orphan node detected"],
            quality_warnings=None,
            dot_graph_error=None,
        )
        assert result.has_warnings is True

    def test_has_warnings_when_quality_warnings(self) -> None:
        basic = self._make_basic()
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=True,
            structural_issues=None,
            quality_warnings=["missing legend"],
            dot_graph_error=None,
        )
        assert result.has_warnings is True

    def test_no_warnings_when_clean(self) -> None:
        basic = self._make_basic(valid_syntax=True, line_count_in_range=True)
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=None,
        )
        assert result.has_warnings is False

    def test_dot_graph_available_defaults_false(self) -> None:
        basic = self._make_basic()
        result = EnhancedValidationResult(
            basic=basic,
            dot_graph_available=False,
            structural_issues=None,
            quality_warnings=None,
            dot_graph_error=None,
        )
        assert result.dot_graph_available is False


# ---------------------------------------------------------------------------
# TestValidateWithDotGraph
# ---------------------------------------------------------------------------


class TestValidateWithDotGraph:
    """Tests for validate_with_dot_graph().

    dot_graph is not installed in this environment, so all tests exercise the
    ImportError fallback path where dot_graph_available is False.
    """

    def test_falls_back_when_dot_graph_not_installed(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(VALID_DOT)
        result = validate_with_dot_graph(str(dot_file))
        # dot_graph not installed → ImportError fallback
        assert result.dot_graph_available is False
        # basic validation still ran and produced a non-null result
        assert result.basic is not None

    def test_returns_enhanced_result_type(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(VALID_DOT)
        result = validate_with_dot_graph(str(dot_file))
        assert isinstance(result, EnhancedValidationResult)

    def test_basic_validation_runs_on_missing_file(self) -> None:
        result = validate_with_dot_graph("/nonexistent/path/to/missing.dot")
        assert result.basic is not None
        assert result.basic.valid_syntax is False
        assert result.basic.syntax_error is not None

    def test_is_valid_reflects_basic_syntax(self, tmp_path: Path) -> None:
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(VALID_DOT)
        result = validate_with_dot_graph(str(dot_file))
        assert result.is_valid == result.basic.valid_syntax

    def test_line_count_preserved_in_enhanced_result(self, tmp_path: Path) -> None:
        content = "// line\n" * 200
        dot_file = tmp_path / "test.dot"
        dot_file.write_text(content)
        result = validate_with_dot_graph(str(dot_file))
        assert result.basic.line_count == 200
