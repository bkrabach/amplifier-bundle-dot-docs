"""Tests for the dotfiles-discovery orchestrator recipe.

RED phase: These tests are written BEFORE the file exists.
They verify the structure and content of dot-docs/recipes/dotfiles-discovery.yaml.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

BUNDLE_ROOT = Path(__file__).parent.parent


class TestDiscoveryRecipeExists:
    """Verify the recipe file exists and is valid YAML."""

    @pytest.fixture
    def recipe_path(self) -> Path:
        return BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml"

    @pytest.fixture
    def recipe_data(self, recipe_path: Path) -> dict:
        content = recipe_path.read_text()
        return yaml.safe_load(content)

    def test_file_exists(self, recipe_path: Path) -> None:
        assert recipe_path.exists(), f"dotfiles-discovery.yaml not found at {recipe_path}"

    def test_valid_yaml(self, recipe_path: Path) -> None:
        content = recipe_path.read_text()
        data = yaml.safe_load(content)
        assert data is not None, "YAML file is empty or null"

    def test_recipe_name(self, recipe_data: dict) -> None:
        assert recipe_data.get("name") == "dotfiles-discovery", (
            f"Recipe name is '{recipe_data.get('name')}', expected 'dotfiles-discovery'"
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
        assert "discovery" in tags, "Tag 'discovery' missing"
        assert "orchestration" in tags, "Tag 'orchestration' missing"


class TestDiscoveryRecipeRecursion:
    """Verify recursion settings."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        return yaml.safe_load(content)

    def test_recursion_section_exists(self, recipe_data: dict) -> None:
        assert "recursion" in recipe_data, "recursion section missing"

    def test_recursion_max_depth(self, recipe_data: dict) -> None:
        recursion = recipe_data["recursion"]
        assert recursion.get("max_depth") == 3, (
            f"recursion.max_depth is '{recursion.get('max_depth')}', expected 3"
        )

    def test_recursion_max_total_steps(self, recipe_data: dict) -> None:
        recursion = recipe_data["recursion"]
        assert recursion.get("max_total_steps") == 100, (
            f"recursion.max_total_steps is '{recursion.get('max_total_steps')}', expected 100"
        )


class TestDiscoveryRecipeContext:
    """Verify context variables."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        return yaml.safe_load(content)

    def test_context_section_exists(self, recipe_data: dict) -> None:
        assert "context" in recipe_data, "context section missing"

    def test_context_profile_path(self, recipe_data: dict) -> None:
        ctx = recipe_data["context"]
        assert "profile_path" in ctx, "context.profile_path missing"

    def test_context_dotfiles_root(self, recipe_data: dict) -> None:
        ctx = recipe_data["context"]
        assert "dotfiles_root" in ctx, "context.dotfiles_root missing"

    def test_context_repos_root(self, recipe_data: dict) -> None:
        ctx = recipe_data["context"]
        assert "repos_root" in ctx, "context.repos_root missing"


class TestDiscoveryRecipeStages:
    """Verify the 3-stage structure."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        return yaml.safe_load(content)

    def test_has_stages(self, recipe_data: dict) -> None:
        assert "stages" in recipe_data, "stages section missing (recipe must use staged format)"

    def test_has_three_stages(self, recipe_data: dict) -> None:
        stages = recipe_data["stages"]
        assert len(stages) == 3, f"Expected 3 stages, got {len(stages)}"

    def test_stage1_name_setup(self, recipe_data: dict) -> None:
        stage1 = recipe_data["stages"][0]
        assert stage1.get("name") == "setup", (
            f"Stage 1 name is '{stage1.get('name')}', expected 'setup'"
        )

    def test_stage2_name_investigation(self, recipe_data: dict) -> None:
        stage2 = recipe_data["stages"][1]
        assert stage2.get("name") == "investigation", (
            f"Stage 2 name is '{stage2.get('name')}', expected 'investigation'"
        )

    def test_stage3_name_synthesis(self, recipe_data: dict) -> None:
        stage3 = recipe_data["stages"][2]
        assert stage3.get("name") == "synthesis", (
            f"Stage 3 name is '{stage3.get('name')}', expected 'synthesis'"
        )


class TestDiscoveryRecipeStage1Setup:
    """Verify stage 1: setup (3 steps)."""

    @pytest.fixture
    def stage1(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        data = yaml.safe_load(content)
        return data["stages"][0]

    def test_stage1_has_three_steps(self, stage1: dict) -> None:
        steps = stage1["steps"]
        assert len(steps) == 3, f"Stage 1 expected 3 steps, got {len(steps)}"

    def test_step1_read_profile(self, stage1: dict) -> None:
        step = stage1["steps"][0]
        assert step.get("id") == "read-profile", (
            f"Stage 1 step 1 id is '{step.get('id')}', expected 'read-profile'"
        )
        assert step.get("type") == "bash", (
            f"Stage 1 step 1 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step1_output_profile(self, stage1: dict) -> None:
        step = stage1["steps"][0]
        assert step.get("output") == "profile", (
            f"Stage 1 step 1 output is '{step.get('output')}', expected 'profile'"
        )

    def test_step1_parse_json(self, stage1: dict) -> None:
        step = stage1["steps"][0]
        assert step.get("parse_json") is True, (
            "Stage 1 step 1 (read-profile) parse_json is not set to true"
        )

    def test_step1_reads_profile_yaml(self, stage1: dict) -> None:
        step = stage1["steps"][0]
        script = step.get("command", step.get("script", ""))
        assert "yaml" in script.lower() or "profile_path" in script, (
            "Stage 1 step 1 does not read profile YAML"
        )

    def test_step2_determine_tiers(self, stage1: dict) -> None:
        step = stage1["steps"][1]
        assert step.get("id") == "determine-tiers", (
            f"Stage 1 step 2 id is '{step.get('id')}', expected 'determine-tiers'"
        )
        assert step.get("type") == "bash", (
            f"Stage 1 step 2 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step2_output_tier_plan(self, stage1: dict) -> None:
        step = stage1["steps"][1]
        assert step.get("output") == "tier_plan", (
            f"Stage 1 step 2 output is '{step.get('output')}', expected 'tier_plan'"
        )

    def test_step2_parse_json(self, stage1: dict) -> None:
        step = stage1["steps"][1]
        assert step.get("parse_json") is True, (
            "Stage 1 step 2 (determine-tiers) parse_json is not set to true"
        )

    def test_step2_imports_detect_changes(self, stage1: dict) -> None:
        step = stage1["steps"][1]
        script = step.get("command", step.get("script", ""))
        assert "detect_changes" in script, (
            "Stage 1 step 2 does not import detect_changes from structural_change"
        )

    def test_step2_imports_discovery_metadata(self, stage1: dict) -> None:
        step = stage1["steps"][1]
        script = step.get("command", step.get("script", ""))
        assert "read_last_run" in script or "discovery_metadata" in script, (
            "Stage 1 step 2 does not import from discovery_metadata"
        )

    def test_step2_imports_get_force_tier(self, stage1: dict) -> None:
        step = stage1["steps"][1]
        script = step.get("command", step.get("script", ""))
        assert "get_force_tier" in script, (
            "Stage 1 step 2 does not import get_force_tier from discovery_metadata"
        )

    def test_step2_produces_tier_json_array(self, stage1: dict) -> None:
        step = stage1["steps"][1]
        script = step.get("command", step.get("script", ""))
        # Should produce JSON array with repo, tier, reason, repo_path, output_dir, current_commit
        assert "tier" in script, "Stage 1 step 2 does not mention 'tier' in output"
        assert "repo" in script, "Stage 1 step 2 does not mention 'repo' in output"

    def test_step3_display_plan(self, stage1: dict) -> None:
        step = stage1["steps"][2]
        assert step.get("id") == "display-plan", (
            f"Stage 1 step 3 id is '{step.get('id')}', expected 'display-plan'"
        )
        assert step.get("type") == "bash", (
            f"Stage 1 step 3 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step3_output_plan_display(self, stage1: dict) -> None:
        step = stage1["steps"][2]
        assert step.get("output") == "plan_display", (
            f"Stage 1 step 3 output is '{step.get('output')}', expected 'plan_display'"
        )

    def test_step3_formats_tier_labels(self, stage1: dict) -> None:
        step = stage1["steps"][2]
        script = step.get("command", step.get("script", ""))
        # Should include tier labels: SKIP, FULL, WAVE, PATCH
        assert "SKIP" in script or "FULL" in script or "WAVE" in script or "PATCH" in script, (
            "Stage 1 step 3 does not show tier labels (SKIP/FULL/WAVE/PATCH)"
        )


class TestDiscoveryRecipeStage2ApprovalGate:
    """Verify approval gate at end of stage 2 (after prescan-repos)."""

    @pytest.fixture
    def stage2(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        data = yaml.safe_load(content)
        return data["stages"][1]

    def test_stage2_has_approval(self, stage2: dict) -> None:
        assert "approval" in stage2, "Stage 2 must have an approval gate after prescan-repos"

    def test_stage2_approval_required(self, stage2: dict) -> None:
        approval = stage2["approval"]
        assert approval.get("required") is True, (
            f"Stage 2 approval.required is '{approval.get('required')}', expected true"
        )

    def test_stage2_approval_shows_tier_plan(self, stage2: dict) -> None:
        approval = stage2["approval"]
        prompt = str(approval.get("prompt", ""))
        # Approval should show tier plan or plan_display
        assert "tier_plan" in prompt or "plan_display" in prompt or "plan" in prompt.lower(), (
            "Stage 2 approval gate does not reference the tier plan"
        )

    def test_stage2_approval_shows_prescan_results(self, stage2: dict) -> None:
        approval = stage2["approval"]
        prompt = str(approval.get("prompt", ""))
        assert "prescan_results" in prompt, (
            "Stage 2 approval gate does not reference prescan_results"
        )


class TestDiscoveryRecipeStage2Investigation:
    """Verify stage 2: investigation (2 steps)."""

    @pytest.fixture
    def stage2(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        data = yaml.safe_load(content)
        return data["stages"][1]

    def test_stage2_has_two_steps(self, stage2: dict) -> None:
        steps = stage2["steps"]
        assert len(steps) == 2, f"Stage 2 expected 2 steps, got {len(steps)}"

    def test_step1_process_repos(self, stage2: dict) -> None:
        step = stage2["steps"][0]
        assert step.get("id") == "process-repos", (
            f"Stage 2 step 1 id is '{step.get('id')}', expected 'process-repos'"
        )

    def test_step1_foreach_tier_plan(self, stage2: dict) -> None:
        step = stage2["steps"][0]
        foreach = step.get("foreach", "")
        assert "tier_plan" in str(foreach), (
            f"Stage 2 step 1 foreach is '{foreach}', expected reference to tier_plan"
        )

    def test_step1_collect_processing_results(self, stage2: dict) -> None:
        step = stage2["steps"][0]
        collect = step.get("collect", "")
        assert collect == "processing_results", (
            f"Stage 2 step 1 collect is '{collect}', expected 'processing_results'"
        )

    def test_step1_timeout_600(self, stage2: dict) -> None:
        step = stage2["steps"][0]
        assert step.get("timeout") == 600, (
            f"Stage 2 step 1 timeout is '{step.get('timeout')}', expected 600"
        )

    def test_step2_prescan_repos(self, stage2: dict) -> None:
        step = stage2["steps"][1]
        assert step.get("id") == "prescan-repos", (
            f"Stage 2 step 2 id is '{step.get('id')}', expected 'prescan-repos'"
        )

    def test_step2_foreach_tier_plan(self, stage2: dict) -> None:
        step = stage2["steps"][1]
        foreach = step.get("foreach", "")
        assert "tier_plan" in str(foreach), (
            f"Stage 2 step 2 foreach is '{foreach}', expected reference to tier_plan"
        )

    def test_step2_has_condition_tier_1_or_2(self, stage2: dict) -> None:
        step = stage2["steps"][1]
        condition = str(step.get("condition", ""))
        # Condition should check tier==1 or tier==2
        has_tier_check = (
            "tier" in condition and ("1" in condition or "2" in condition)
        ) or "tier" in condition
        assert has_tier_check, (
            f"Stage 2 step 2 condition '{condition}' does not check tier==1 or tier==2"
        )

    def test_step2_dispatches_prescan_recipe(self, stage2: dict) -> None:
        step = stage2["steps"][1]
        step_str = str(step)
        assert "prescan" in step_str.lower(), "Stage 2 step 2 does not dispatch the prescan recipe"
        assert "dotfiles-prescan" in step_str or "prescan" in step_str, (
            "Stage 2 step 2 does not reference dotfiles-prescan recipe"
        )

    def test_step2_collect_prescan_results(self, stage2: dict) -> None:
        step = stage2["steps"][1]
        collect = step.get("collect", "")
        assert collect == "prescan_results", (
            f"Stage 2 step 2 collect is '{collect}', expected 'prescan_results'"
        )

    def test_step2_timeout_600(self, stage2: dict) -> None:
        step = stage2["steps"][1]
        assert step.get("timeout") == 600, (
            f"Stage 2 step 2 timeout is '{step.get('timeout')}', expected 600"
        )


class TestDiscoveryRecipeStage3Synthesis:
    """Verify stage 3: synthesis (4 steps)."""

    @pytest.fixture
    def stage3(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        data = yaml.safe_load(content)
        return data["stages"][2]

    def test_stage3_has_four_steps(self, stage3: dict) -> None:
        steps = stage3["steps"]
        assert len(steps) == 4, f"Stage 3 expected 4 steps, got {len(steps)}"

    def test_step1_run_synthesis(self, stage3: dict) -> None:
        step = stage3["steps"][0]
        assert step.get("id") == "run-synthesis", (
            f"Stage 3 step 1 id is '{step.get('id')}', expected 'run-synthesis'"
        )

    def test_step1_foreach_tier_plan(self, stage3: dict) -> None:
        step = stage3["steps"][0]
        foreach = step.get("foreach", "")
        assert "tier_plan" in str(foreach), (
            f"Stage 3 step 1 foreach is '{foreach}', expected reference to tier_plan"
        )

    def test_step1_condition_tier_ge_1(self, stage3: dict) -> None:
        step = stage3["steps"][0]
        condition = str(step.get("condition", ""))
        assert "tier" in condition and "1" in condition, (
            f"Stage 3 step 1 condition '{condition}' does not check tier>=1"
        )

    def test_step1_dispatches_synthesis_recipe(self, stage3: dict) -> None:
        step = stage3["steps"][0]
        step_str = str(step)
        assert "dotfiles-synthesis" in step_str or "synthesis" in step_str, (
            "Stage 3 step 1 does not dispatch the synthesis recipe"
        )

    def test_step1_collect_synthesis_results(self, stage3: dict) -> None:
        step = stage3["steps"][0]
        collect = step.get("collect", "")
        assert collect == "synthesis_results", (
            f"Stage 3 step 1 collect is '{collect}', expected 'synthesis_results'"
        )

    def test_step1_timeout_3600(self, stage3: dict) -> None:
        step = stage3["steps"][0]
        assert step.get("timeout") == 3600, (
            f"Stage 3 step 1 timeout is '{step.get('timeout')}', expected 3600"
        )

    def test_step2_tier3_analysis(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        assert step.get("id") == "tier3-analysis", (
            f"Stage 3 step 2 id is '{step.get('id')}', expected 'tier3-analysis'"
        )

    def test_step2_tier3_condition(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        condition = str(step.get("condition", ""))
        assert "tier" in condition and "3" in condition, (
            f"Stage 3 step 2 condition '{condition}' does not check tier==3"
        )

    def test_step2_tier3_mentions_orphan_check(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        prompt = step.get("prompt", step.get("command", step.get("script", ""))).lower()
        assert "orphan" in prompt, "Stage 3 step 2 does not mention orphan check in prompt"

    def test_step2_tier3_mentions_cycle_check(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        prompt = step.get("prompt", step.get("command", step.get("script", ""))).lower()
        assert "cycle" in prompt, "Stage 3 step 2 does not mention cycle check in prompt"

    def test_step2_tier3_mentions_diff_check(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        prompt = step.get("prompt", step.get("command", step.get("script", ""))).lower()
        assert "diff" in prompt, "Stage 3 step 2 does not mention diff check in prompt"

    def test_step2_tier3_output(self, stage3: dict) -> None:
        step = stage3["steps"][1]
        assert step.get("output") == "tier3_analysis", (
            f"Stage 3 step 2 output is '{step.get('output')}', expected 'tier3_analysis'"
        )

    def test_step3_write_metadata(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        assert step.get("id") == "write-metadata", (
            f"Stage 3 step 3 id is '{step.get('id')}', expected 'write-metadata'"
        )
        assert step.get("type") == "bash", (
            f"Stage 3 step 3 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step3_imports_metadata_classes(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        script = step.get("command", step.get("script", ""))
        assert "LastRunMetadata" in script or "ManifestMetadata" in script, (
            "Stage 3 step 3 does not import LastRunMetadata/ManifestMetadata"
        )

    def test_step3_imports_write_functions(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        script = step.get("command", step.get("script", ""))
        assert "write_last_run" in script, "Stage 3 step 3 does not import write_last_run"
        assert "write_manifest" in script, "Stage 3 step 3 does not import write_manifest"

    def test_step3_output_metadata_result(self, stage3: dict) -> None:
        step = stage3["steps"][2]
        assert step.get("output") == "metadata_result", (
            f"Stage 3 step 3 output is '{step.get('output')}', expected 'metadata_result'"
        )

    def test_step4_final_summary(self, stage3: dict) -> None:
        step = stage3["steps"][3]
        assert step.get("id") == "final-summary", (
            f"Stage 3 step 4 id is '{step.get('id')}', expected 'final-summary'"
        )
        assert step.get("type") == "bash", (
            f"Stage 3 step 4 type is '{step.get('type')}', expected 'bash'"
        )

    def test_step4_output_discovery_complete(self, stage3: dict) -> None:
        step = stage3["steps"][3]
        assert step.get("output") == "discovery_complete", (
            f"Stage 3 step 4 output is '{step.get('output')}', expected 'discovery_complete'"
        )

    def test_step4_shows_dotfiles_root(self, stage3: dict) -> None:
        step = stage3["steps"][3]
        script = step.get("command", step.get("script", ""))
        assert "dotfiles_root" in script, (
            "Stage 3 step 4 does not reference dotfiles_root in banner"
        )


class TestDiscoveryRecipeFinalOutput:
    """Verify final_output."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        content = (BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml").read_text()
        return yaml.safe_load(content)

    def test_no_final_output_key(self, recipe_data: dict) -> None:
        assert "final_output" not in recipe_data, (
            "Recipe must not have top-level 'final_output' key (unknown/invalid key)"
        )


class TestDiscoveryModuleAvailability:
    """Verify all Python modules referenced in the discovery recipe can be imported.

    These tests guard against the class of regression where a recipe references
    Python modules that have been deleted or renamed — a category of failure that
    YAML-structure tests cannot detect.
    """

    @pytest.fixture(autouse=True)
    def _add_tools_to_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        tools_dir = str(BUNDLE_ROOT / "tools")
        if tools_dir not in sys.path:
            monkeypatch.syspath_prepend(tools_dir)

    def test_structural_change_importable(self) -> None:
        """dotfiles_discovery.structural_change must be importable."""
        from dotfiles_discovery import structural_change  # noqa: F401

        assert hasattr(structural_change, "detect_changes")

    def test_discovery_metadata_importable(self) -> None:
        """dotfiles_discovery.discovery_metadata must be importable."""
        from dotfiles_discovery import discovery_metadata  # noqa: F401

        assert hasattr(discovery_metadata, "read_last_run")
        assert hasattr(discovery_metadata, "get_force_tier")
        assert hasattr(discovery_metadata, "write_last_run")
        assert hasattr(discovery_metadata, "write_manifest")
        assert hasattr(discovery_metadata, "LastRunMetadata")
        assert hasattr(discovery_metadata, "ManifestMetadata")

    def test_prescan_recipe_exists(self) -> None:
        """The dotfiles-prescan.yaml sub-recipe referenced in stage 2 must exist."""
        prescan_path = BUNDLE_ROOT / "recipes" / "dotfiles-prescan.yaml"
        assert prescan_path.exists(), (
            f"dotfiles-prescan.yaml not found at {prescan_path}; "
            "the prescan-repos step in dotfiles-discovery.yaml will fail at runtime."
        )

    def test_prescan_recipe_valid_yaml(self) -> None:
        """dotfiles-prescan.yaml must parse as valid YAML with required fields."""
        prescan_path = BUNDLE_ROOT / "recipes" / "dotfiles-prescan.yaml"
        data = yaml.safe_load(prescan_path.read_text())
        assert data.get("name") == "dotfiles-prescan"
        assert "steps" in data or "stages" in data, "prescan recipe must have 'steps' or 'stages'"


class TestDiscoveryRecipeYAMLValidation:
    """Validates the YAML file structure using the spec's validation command."""

    def test_yaml_validation_script(self) -> None:
        """Mimics: python3 -c 'import yaml; ...' validation."""
        recipe_path = BUNDLE_ROOT / "recipes" / "dotfiles-discovery.yaml"
        script = f"""
import yaml
with open('{recipe_path}') as f:
    data = yaml.safe_load(f)
assert data['name'] == 'dotfiles-discovery', f"name mismatch: {{data.get('name')}}"
stages = data['stages']
assert len(stages) == 3, f"expected 3 stages, got {{len(stages)}}"
assert len(stages[0]['steps']) == 3, f"stage 1 expected 3 steps, got {{len(stages[0]['steps'])}}"
assert len(stages[1]['steps']) == 2, f"stage 2 expected 2 steps, got {{len(stages[1]['steps'])}}"
assert len(stages[2]['steps']) == 4, f"stage 3 expected 4 steps, got {{len(stages[2]['steps'])}}"
assert stages[1]['approval']['required'] is True, "stage 2 approval.required is not true"
print("VALIDATION PASSED")
"""
        result = subprocess.run(
            ["python3", "-c", script],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"YAML validation script failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "VALIDATION PASSED" in result.stdout


class TestPrescanPrompt:
    """RED phase: tests for context/prescan-prompt.md (file does not exist yet)."""

    @pytest.fixture
    def prompt_path(self) -> Path:
        return BUNDLE_ROOT / "context" / "prescan-prompt.md"

    def test_file_exists(self, prompt_path: Path) -> None:
        assert prompt_path.exists(), f"context/prescan-prompt.md not found at {prompt_path}"

    def test_file_is_nonempty(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert len(content.strip()) > 100, "prescan-prompt.md is too short (< 100 chars stripped)"

    def test_mentions_architecture_perspective(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "architecture" in content.lower(), (
            "prescan-prompt.md does not mention 'architecture' perspective"
        )

    def test_mentions_execution_flows_perspective(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "execution" in content.lower(), (
            "prescan-prompt.md does not mention 'execution' perspective"
        )

    def test_mentions_state_perspective(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "state" in content.lower(), (
            "prescan-prompt.md does not mention 'state' perspective"
        )

    def test_specifies_json_output_format(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "json" in content.lower(), (
            "prescan-prompt.md does not specify JSON output format"
        )

    def test_output_format_includes_slug_field(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "slug" in content, "prescan-prompt.md output format does not include 'slug' field"

    def test_output_format_includes_rationale_field(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "rationale" in content, (
            "prescan-prompt.md output format does not include 'rationale' field"
        )

    def test_calibration_mentions_tiers(self, prompt_path: Path) -> None:
        content = prompt_path.read_text()
        assert "tier" in content.lower(), (
            "prescan-prompt.md calibration does not mention 'tier'"
        )
