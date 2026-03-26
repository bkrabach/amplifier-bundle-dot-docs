"""Tests for synthesis agent prompt and synthesis recipe artifacts.

RED phase: These tests are written BEFORE the files exist.
They verify the content and structure of the artifacts once created.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

# All paths are relative to this file's location (dot-docs/tests/)
# The artifacts live in the parent directory (dot-docs/)
BUNDLE_ROOT = Path(__file__).parent.parent


class TestSynthesisPrompt:
    """Verify dot-docs/context/synthesis-prompt.md exists with required content."""

    @pytest.fixture
    def prompt_path(self) -> Path:
        return BUNDLE_ROOT / "context" / "synthesis-prompt.md"

    def test_file_exists(self, prompt_path: Path) -> None:
        assert prompt_path.exists(), f"synthesis-prompt.md not found at {prompt_path}"

    def test_file_is_nonempty(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert len(content.strip()) > 100, "synthesis-prompt.md appears empty"

    def test_input_section_describes_raw_dot_files(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Must describe raw DOT files as input
        assert "raw" in content.lower() or "DOT" in content, (
            "Input section does not mention raw DOT files"
        )
        assert "investigation" in content.lower(), (
            "Input section does not mention investigation workspace"
        )

    def test_input_section_mentions_topics(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "topic" in content.lower(), "Input section does not mention topics"

    def test_input_section_mentions_repo_path(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "repo" in content.lower(), "Input section does not mention repo path"

    def test_task_read_all_raw_dot_files(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Must instruct agent to read ALL raw DOT files
        assert "all" in content.lower() or "ALL" in content, (
            "Task does not instruct reading ALL raw DOT files"
        )
        assert ".dot" in content or "DOT" in content, "Task does not mention reading DOT files"

    def test_task_reconcile_overlapping_content(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Must instruct reconciling overlapping content
        assert (
            "reconcile" in content.lower()
            or "overlap" in content.lower()
            or "merge" in content.lower()
        ), "Task does not mention reconciling/merging overlapping content"

    def test_task_choose_overview_perspective(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "overview" in content.lower(), "Task does not mention choosing overview perspective"
        assert "perspective" in content.lower() or "heuristic" in content.lower(), (
            "Task does not mention perspective or heuristic"
        )

    def test_overview_perspective_heuristic_composition(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Composition systems → architecture/composition
        assert "composition" in content.lower(), (
            "Overview perspective heuristic does not mention composition systems"
        )
        assert "architecture" in content.lower(), (
            "Overview perspective heuristic does not mention architecture"
        )

    def test_overview_perspective_heuristic_execution(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Execution engines → execution flow or state machine
        assert "execution" in content.lower(), (
            "Overview perspective heuristic does not mention execution engines"
        )
        assert "state machine" in content.lower() or "state-machine" in content.lower(), (
            "Overview perspective heuristic does not mention state machine"
        )

    def test_overview_perspective_heuristic_library(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Libraries/toolkits → architecture/dependency
        assert "librar" in content.lower() or "toolkit" in content.lower(), (
            "Overview perspective heuristic does not mention libraries/toolkits"
        )
        assert "dependency" in content.lower() or "dependencies" in content.lower(), (
            "Overview perspective heuristic does not mention dependency"
        )

    def test_overview_perspective_heuristic_bugs(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Repos with confirmed bugs → diagram that best annotates them
        assert "bug" in content.lower() or "issue" in content.lower(), (
            "Overview perspective heuristic does not mention confirmed bugs"
        )
        assert "annotate" in content.lower() or "annotation" in content.lower(), (
            "Overview perspective heuristic does not mention annotating bugs"
        )

    def test_references_dot_quality_standards(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "dot-quality-standards" in content or "quality-standards" in content, (
            "synthesis-prompt.md does not reference dot-quality-standards.md"
        )

    def test_output_overview_dot_mandatory(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "overview.dot" in content, "Output requirements do not mention overview.dot"
        assert "mandatory" in content.lower() or "MANDATORY" in content, (
            "overview.dot is not marked as mandatory"
        )

    def test_output_overview_dot_line_counts(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "150" in content and "250" in content, (
            "overview.dot line count targets (150-250) not found in synthesis prompt"
        )

    def test_output_overview_dot_size_limit(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "15KB" in content or "15 KB" in content, (
            "overview.dot size limit (15KB) not found in synthesis prompt"
        )

    def test_output_overview_dot_rendered_legend(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "legend" in content.lower(), "overview.dot rendered legend requirement not mentioned"

    def test_output_overview_dot_red_for_issues(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "red" in content.lower(), (
            "overview.dot red-for-known-issues requirement not mentioned"
        )

    def test_output_detail_files_optional(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # All detail files should be present and marked optional
        detail_files = [
            "architecture.dot",
            "sequence.dot",
            "state-machines.dot",
            "integration.dot",
        ]
        for fname in detail_files:
            assert fname in content, f"Detail file '{fname}' not mentioned in output requirements"
        assert "optional" in content.lower() or "OPTIONAL" in content, (
            "Detail files are not marked as optional"
        )

    def test_output_detail_files_line_counts(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "200" in content and "400" in content, (
            "Detail file line count targets (200-400) not found in synthesis prompt"
        )

    def test_detail_files_cluster_names_match_overview(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Detail files must use subgraph names matching overview.dot clusters
        assert "cluster" in content.lower() or "subgraph" in content.lower(), (
            "No mention of cluster/subgraph name matching between overview and detail files"
        )
        assert "overview" in content.lower(), (
            "Detail files requirement does not reference overview.dot"
        )

    def test_antipatterns_no_copying_raw_output(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "copy" in content.lower() or "raw" in content.lower(), (
            "Anti-pattern 'no copying one agent's raw output' not mentioned"
        )

    def test_antipatterns_overview_max_250_lines(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "250" in content, "Anti-pattern 'no exceeding 250 lines in overview' not mentioned"

    def test_antipatterns_no_multiline_labels(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "multi-line" in content.lower() or "multiline" in content.lower(), (
            "Anti-pattern 'no multi-line inline doc labels' not mentioned"
        )

    def test_antipatterns_max_80_nodes(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "80" in content, "Anti-pattern 'no >80 nodes' not mentioned"

    def test_antipatterns_no_splines_ortho(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "splines" in content.lower() or "ortho" in content.lower(), (
            "Anti-pattern 'no splines=ortho' not mentioned"
        )

    def test_antipatterns_no_comment_only_legends(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "comment" in content.lower() and "legend" in content.lower(), (
            "Anti-pattern 'no comment-only legends' not mentioned"
        )

    # --- New tests for Reconciliation Methodology, Quality Checklist, Skills to Load ---

    def test_reconciliation_methodology_subsection_exists(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "Reconciliation Methodology" in content, (
            "synthesis-prompt.md does not contain 'Reconciliation Methodology' subsection"
        )

    def test_reconciliation_phase_introspect(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "Introspect" in content, "Reconciliation Methodology missing Phase 1: Introspect"

    def test_reconciliation_phase_represent(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "Represent" in content, "Reconciliation Methodology missing Phase 2: Represent"

    def test_reconciliation_phase_reconcile(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "Reconcile" in content, "Reconciliation Methodology missing Phase 3: Reconcile"

    def test_reconciliation_phase_surface(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "Surface" in content, "Reconciliation Methodology missing Phase 4: Surface"

    def test_anti_rationalization_table_exists(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "Anti-Rationalization" in content, (
            "synthesis-prompt.md does not contain Anti-Rationalization Table"
        )

    def test_anti_rationalization_table_has_seven_entries(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # The 7 rationalizations from the dot-as-analysis skill
        rationalizations = [
            "probably exists",
            "close enough",
            "works in practice",
            "internal",
            "error path is obvious",
            "infrastructure",
            "legend later",
        ]
        for phrase in rationalizations:
            assert phrase.lower() in content.lower(), (
                f"Anti-Rationalization Table missing entry for: '{phrase}'"
            )

    def test_quality_checklist_orphan_nodes(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "orphan" in content.lower(), "Quality Checklist missing item about orphan nodes"

    def test_quality_checklist_isolated_clusters(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "isolated cluster" in content.lower(), (
            "Quality Checklist missing item about isolated clusters"
        )

    def test_quality_checklist_legend_completeness(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        # Must mention legend completeness as a distinct checklist item beyond existing legend check
        assert "legend" in content.lower() and "complete" in content.lower(), (
            "Quality Checklist missing legend completeness item"
        )

    def test_skills_to_load_section_exists(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "Skills to Load" in content, (
            "synthesis-prompt.md does not contain 'Skills to Load' section"
        )

    def test_skills_to_load_dot_syntax(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "dot-syntax" in content, "Skills to Load section does not reference dot-syntax skill"

    def test_skills_to_load_dot_patterns(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "dot-patterns" in content, (
            "Skills to Load section does not reference dot-patterns skill"
        )

    def test_skills_to_load_dot_quality(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "dot-quality" in content, (
            "Skills to Load section does not reference dot-quality skill"
        )

    def test_skills_to_load_dot_as_analysis(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "dot-as-analysis" in content, (
            "Skills to Load section does not reference dot-as-analysis skill"
        )

    def test_skills_to_load_dot_graph_intelligence(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "dot-graph-intelligence" in content, (
            "Skills to Load section does not reference dot-graph-intelligence skill"
        )

    def test_reconciliation_methodology_present(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "Introspect" in content, "Reconciliation methodology does not mention 'Introspect'"
        assert "Reconcile" in content, "Reconciliation methodology does not mention 'Reconcile'"
        assert "Surface" in content, "Reconciliation methodology does not mention 'Surface'"

    def test_anti_rationalization_table_present(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "rationalization" in content.lower(), (
            "Anti-rationalization table is not present in synthesis-prompt.md"
        )
        assert "close enough" in content.lower(), (
            "Anti-rationalization table does not contain 'close enough' entry"
        )

    def test_dot_graph_skill_references(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "dot-syntax" in content, "synthesis-prompt.md does not reference dot-syntax skill"
        assert "dot-quality" in content, "synthesis-prompt.md does not reference dot-quality skill"
        assert "dot-as-analysis" in content, (
            "synthesis-prompt.md does not reference dot-as-analysis skill"
        )


class TestSynthesisRecipe:
    """Verify dot-docs/recipes/dotfiles-synthesis.yaml has valid structure."""

    @pytest.fixture
    def recipe_path(self) -> Path:
        return BUNDLE_ROOT / "recipes" / "dotfiles-synthesis.yaml"

    @pytest.fixture
    def recipe_data(self, recipe_path: Path) -> dict:
        content = recipe_path.read_text()
        return yaml.safe_load(content)

    def test_file_exists(self, recipe_path: Path) -> None:
        assert recipe_path.exists(), f"dotfiles-synthesis.yaml not found at {recipe_path}"

    def test_valid_yaml(self, recipe_path: Path) -> None:
        content = recipe_path.read_text()
        data = yaml.safe_load(content)
        assert data is not None, "YAML file is empty or null"

    def test_recipe_name(self, recipe_data: dict) -> None:
        assert recipe_data.get("name") == "dotfiles-synthesis", (
            f"Recipe name is '{recipe_data.get('name')}', expected 'dotfiles-synthesis'"
        )

    def test_recipe_version(self, recipe_data: dict) -> None:
        assert "version" in recipe_data, "Recipe version missing"
        assert recipe_data["version"] == "0.1.0", (
            f"Recipe version is '{recipe_data['version']}', expected '0.1.0'"
        )

    def test_recipe_tags(self, recipe_data: dict) -> None:
        assert "tags" in recipe_data, "Recipe tags missing"
        tags = recipe_data["tags"]
        assert "dotfiles" in tags, "Tag 'dotfiles' missing"
        assert "synthesis" in tags, "Tag 'synthesis' missing"
        assert "dot-generation" in tags, "Tag 'dot-generation' missing"

    def test_recipe_context_required_fields(self, recipe_data: dict) -> None:
        assert "context" in recipe_data, "Recipe context missing"
        ctx = recipe_data["context"]
        required_fields = ["investigation_dir", "repo_path", "output_dir", "topics"]
        for field in required_fields:
            assert field in ctx, f"context.{field} missing from recipe context"

    def test_recipe_has_six_steps(self, recipe_data: dict) -> None:
        assert "steps" in recipe_data, "Recipe steps missing"
        steps = recipe_data["steps"]
        assert len(steps) == 6, f"Expected 6 steps, got {len(steps)}"

    def test_step1_inventory_dots(self, recipe_data: dict) -> None:
        step1 = recipe_data["steps"][0]
        assert step1.get("id") == "inventory-dots", (
            f"Step 1 id is '{step1.get('id')}', expected 'inventory-dots'"
        )
        assert step1.get("type") == "bash", f"Step 1 type is '{step1.get('type')}', expected 'bash'"

    def test_step1_finds_dot_files(self, recipe_data: dict) -> None:
        step1 = recipe_data["steps"][0]
        script = step1.get("script", step1.get("command", ""))
        assert ".dot" in script or "dot" in script.lower(), (
            "Step 1 bash script does not find .dot files"
        )

    def test_step1_finds_reconciliation_files(self, recipe_data: dict) -> None:
        step1 = recipe_data["steps"][0]
        script = step1.get("script", step1.get("command", ""))
        assert "reconciliation" in script.lower(), (
            "Step 1 bash script does not find reconciliation.md files"
        )

    def test_step1_output_key(self, recipe_data: dict) -> None:
        step1 = recipe_data["steps"][0]
        output = step1.get("output", None)
        assert output == "dot_inventory", f"Step 1 output is '{output}', expected 'dot_inventory'"

    def test_step2_prepare_output(self, recipe_data: dict) -> None:
        step2 = recipe_data["steps"][1]
        assert step2.get("id") == "prepare-output", (
            f"Step 2 id is '{step2.get('id')}', expected 'prepare-output'"
        )
        assert step2.get("type") == "bash", f"Step 2 type is '{step2.get('type')}', expected 'bash'"

    def test_step2_creates_output_dir(self, recipe_data: dict) -> None:
        step2 = recipe_data["steps"][1]
        script = step2.get("script", step2.get("command", ""))
        assert "output_dir" in script or "{{output_dir}}" in script, (
            "Step 2 bash script does not create output_dir"
        )
        assert "mkdir" in script or "makedirs" in script, "Step 2 bash script does not use mkdir"

    def test_step2_creates_discovery_subdir(self, recipe_data: dict) -> None:
        step2 = recipe_data["steps"][1]
        script = step2.get("script", step2.get("command", ""))
        assert ".discovery" in script, "Step 2 bash script does not create .discovery subdirectory"

    def test_step2_output_key(self, recipe_data: dict) -> None:
        step2 = recipe_data["steps"][1]
        output = step2.get("output", None)
        assert output == "output_ready", f"Step 2 output is '{output}', expected 'output_ready'"

    def test_step3_synthesize(self, recipe_data: dict) -> None:
        step3 = recipe_data["steps"][2]
        assert step3.get("id") == "synthesize", (
            f"Step 3 id is '{step3.get('id')}', expected 'synthesize'"
        )
        # Step 3 is a prompt/agent step
        step_type = step3.get("type", "")
        assert step_type in ("prompt", "agent"), (
            f"Step 3 type is '{step_type}', expected 'prompt' or 'agent'"
        )

    def test_step3_references_synthesis_prompt(self, recipe_data: dict) -> None:
        step3 = recipe_data["steps"][2]
        step_content = str(step3)
        assert "synthesis-prompt" in step_content, "Step 3 does not reference synthesis-prompt.md"

    def test_step3_output_key(self, recipe_data: dict) -> None:
        step3 = recipe_data["steps"][2]
        output = step3.get("output", None)
        assert output == "synthesis_summary", (
            f"Step 3 output is '{output}', expected 'synthesis_summary'"
        )

    def test_step3_timeout(self, recipe_data: dict) -> None:
        step3 = recipe_data["steps"][2]
        assert step3.get("timeout") == 1800, (
            f"Step 3 timeout is '{step3.get('timeout')}', expected 1800"
        )

    def test_step4_quality_review(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        assert step4.get("id") == "quality-review", (
            f"Step 4 id is '{step4.get('id')}', expected 'quality-review'"
        )
        assert step4.get("type") == "agent", (
            f"Step 4 type is '{step4.get('type')}', expected 'agent'"
        )

    def test_step4_review_output_key(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        output = step4.get("output", None)
        assert output == "review_verdict", f"Step 4 output is '{output}', expected 'review_verdict'"

    def test_step4_review_mentions_quality(self, recipe_data: dict) -> None:
        step4 = recipe_data["steps"][3]
        prompt = step4.get("prompt", "")
        assert "PASS" in prompt or "FAIL" in prompt or "verdict" in prompt.lower(), (
            "Step 4 quality-review prompt does not mention PASS/WARN/FAIL verdict"
        )

    def test_step5_fix_if_failed(self, recipe_data: dict) -> None:
        step5 = recipe_data["steps"][4]
        assert step5.get("id") == "fix-if-failed", (
            f"Step 5 id is '{step5.get('id')}', expected 'fix-if-failed'"
        )
        assert step5.get("type") == "agent", (
            f"Step 5 type is '{step5.get('type')}', expected 'agent'"
        )

    def test_step5_references_review_verdict(self, recipe_data: dict) -> None:
        step5 = recipe_data["steps"][4]
        condition = str(step5.get("condition", ""))
        assert "FAIL" in condition and "review_verdict" in condition, (
            f"Step 5 condition '{condition}' does not check for FAIL in review_verdict"
        )

    def test_step5_has_max_iterations(self, recipe_data: dict) -> None:
        step5 = recipe_data["steps"][4]
        assert step5.get("max_iterations") == 3, (
            f"Step 5 max_iterations is '{step5.get('max_iterations')}', expected 3"
        )

    def test_step6_validate_output(self, recipe_data: dict) -> None:
        step6 = recipe_data["steps"][5]
        assert step6.get("id") == "validate-output", (
            f"Step 6 id is '{step6.get('id')}', expected 'validate-output'"
        )
        assert step6.get("type") == "bash", f"Step 6 type is '{step6.get('type')}', expected 'bash'"

    def test_step6_imports_validate_with_dot_graph(self, recipe_data: dict) -> None:
        step6 = recipe_data["steps"][5]
        script = step6.get("script", step6.get("command", ""))
        assert "validate_with_dot_graph" in script, (
            "Step 6 bash script does not import validate_with_dot_graph"
        )

    def test_step6_validates_overview_dot(self, recipe_data: dict) -> None:
        step6 = recipe_data["steps"][5]
        script = step6.get("script", step6.get("command", ""))
        assert "overview.dot" in script, "Step 6 bash script does not validate overview.dot"

    def test_step6_output_key(self, recipe_data: dict) -> None:
        step6 = recipe_data["steps"][5]
        output = step6.get("output", None)
        assert output == "validation_result", (
            f"Step 6 output is '{output}', expected 'validation_result'"
        )

    def test_recipe_no_final_output(self, recipe_data: dict) -> None:
        assert "final_output" not in recipe_data, (
            "Recipe must not have top-level 'final_output' key (unknown/invalid key)"
        )


class TestSynthesisRecipeYAMLValidation:
    """Validates the YAML file using the spec's validation command."""

    def test_yaml_validation_script(self) -> None:
        """Mimics: python3 -c 'import yaml; ...' validation."""
        recipe_path = BUNDLE_ROOT / "recipes" / "dotfiles-synthesis.yaml"
        script = """
import yaml, os
with open(os.environ['RECIPE_PATH']) as f:
    data = yaml.safe_load(f)
assert data['name'] == 'dotfiles-synthesis', f"name mismatch: {data.get('name')}"
assert len(data['steps']) == 6, f"expected 6 steps, got {len(data['steps'])}"
print("VALIDATION PASSED")
"""
        result = subprocess.run(
            ["python3", "-c", script],
            capture_output=True,
            text=True,
            env={**os.environ, "RECIPE_PATH": str(recipe_path)},
        )
        assert result.returncode == 0, (
            f"YAML validation script failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "VALIDATION PASSED" in result.stdout


class TestSynthesisAgentFields:
    """Verify all agent steps in dotfiles-synthesis.yaml have explicit agent: fields."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        path = BUNDLE_ROOT / "recipes" / "dotfiles-synthesis.yaml"
        return yaml.safe_load(path.read_text())

    def _get_step(self, recipe_data: dict, step_id: str) -> dict:
        """Find a step by id, searching both top-level steps and stage steps."""
        all_steps = list(recipe_data.get("steps", []))
        for stage in recipe_data.get("stages", []):
            all_steps.extend(stage.get("steps", []))
        return next((s for s in all_steps if s.get("id") == step_id), {})

    def test_synthesize_step_has_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "synthesize")
        assert step, "synthesize step not found in dotfiles-synthesis.yaml"
        assert step.get("agent") == "dot-graph:dot-author", (
            f"synthesize step must have agent: dot-graph:dot-author, got: {step.get('agent')!r}"
        )

    def test_quality_review_step_has_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "quality-review")
        assert step, "quality-review step not found in dotfiles-synthesis.yaml"
        assert step.get("agent") == "dot-graph:diagram-reviewer", (
            f"quality-review step must have agent: dot-graph:diagram-reviewer, got: {step.get('agent')!r}"
        )

    def test_fix_if_failed_step_has_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "fix-if-failed")
        assert step, "fix-if-failed step not found in dotfiles-synthesis.yaml"
        assert step.get("agent") == "dot-graph:dot-author", (
            f"fix-if-failed step must have agent: dot-graph:dot-author, got: {step.get('agent')!r}"
        )


class TestDotQualityStandards:
    """Verify context/dot-quality-standards.md exists with the required @mention."""

    @pytest.fixture
    def standards_path(self) -> Path:
        return BUNDLE_ROOT / "context" / "dot-quality-standards.md"

    def test_file_exists(self, standards_path: Path) -> None:
        assert standards_path.exists(), (
            f"dot-quality-standards.md not found at {standards_path}"
        )

    def test_references_dot_graph_quality_skill(self, standards_path: Path) -> None:
        content = standards_path.read_text()
        assert "@dot-graph:skills/dot-quality" in content, (
            "dot-quality-standards.md must contain: @dot-graph:skills/dot-quality"
        )
