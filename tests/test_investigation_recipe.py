"""Tests for the dotfiles-investigate.yaml recipe structure.

RED phase: Written before the recipe file exists.
Verifies structure, step order, agent assignments, conditions, and output contracts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

BUNDLE_ROOT = Path(__file__).parent.parent


class TestInvestigationRecipeExists:
    """Verify the recipe file exists and has correct top-level metadata."""

    @pytest.fixture
    def recipe_path(self) -> Path:
        return BUNDLE_ROOT / "recipes" / "dotfiles-investigate.yaml"

    @pytest.fixture
    def recipe_data(self, recipe_path: Path) -> dict:
        return yaml.safe_load(recipe_path.read_text())

    def test_file_exists(self, recipe_path: Path) -> None:
        assert recipe_path.exists(), f"dotfiles-investigate.yaml not found at {recipe_path}"

    def test_valid_yaml(self, recipe_data: dict) -> None:
        assert recipe_data is not None, "dotfiles-investigate.yaml is empty or null"

    def test_recipe_name(self, recipe_data: dict) -> None:
        assert recipe_data.get("name") == "dotfiles-investigate", (
            f"recipe name must be 'dotfiles-investigate', got: {recipe_data.get('name')!r}"
        )

    def test_has_required_context_repo_path(self, recipe_data: dict) -> None:
        ctx = recipe_data.get("context", {})
        assert "repo_path" in ctx, "context must include repo_path"

    def test_has_required_context_investigation_dir(self, recipe_data: dict) -> None:
        ctx = recipe_data.get("context", {})
        assert "investigation_dir" in ctx, "context must include investigation_dir"

    def test_has_required_context_tier(self, recipe_data: dict) -> None:
        ctx = recipe_data.get("context", {})
        assert "tier" in ctx, "context must include tier"


class TestInvestigationRecipeSteps:
    """Verify the 6-step structure, step order, agents, and conditions."""

    @pytest.fixture
    def recipe_data(self) -> dict:
        path = BUNDLE_ROOT / "recipes" / "dotfiles-investigate.yaml"
        return yaml.safe_load(path.read_text())

    def _get_all_steps(self, recipe_data: dict) -> list:
        steps = list(recipe_data.get("steps", []))
        for stage in recipe_data.get("stages", []):
            steps.extend(stage.get("steps", []))
        return steps

    def _get_step(self, recipe_data: dict, step_id: str) -> dict:
        return next((s for s in self._get_all_steps(recipe_data) if s.get("id") == step_id), {})

    def _step_index(self, recipe_data: dict, step_id: str) -> int:
        ids = [s.get("id") for s in self._get_all_steps(recipe_data)]
        try:
            return ids.index(step_id)
        except ValueError:
            return -1

    # --- Step existence ---

    def test_has_prepare_workspace_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "prepare-workspace")
        assert step, "must have step id: prepare-workspace"
        assert step.get("type") == "bash", "prepare-workspace must be type: bash"

    def test_has_select_topics_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "select-topics")
        assert step, "must have step id: select-topics"
        assert step.get("type") == "agent", "select-topics must be type: agent"
        assert step.get("parse_json") is True, "select-topics must have parse_json: true"
        assert step.get("output"), "select-topics must have an output field"

    def test_has_build_topic_paths_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "build-topic-paths")
        assert step, "must have step id: build-topic-paths"
        assert step.get("type") == "bash", "build-topic-paths must be type: bash"
        assert step.get("parse_json") is True, "build-topic-paths must have parse_json: true"

    def test_has_wave1_code_tracers_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-code-tracers")
        assert step, "must have step id: wave1-code-tracers"

    def test_has_wave1_behavior_observers_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-behavior-observers")
        assert step, "must have step id: wave1-behavior-observers"

    def test_has_wave1_integration_mappers_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-integration-mappers")
        assert step, "must have step id: wave1-integration-mappers"

    def test_has_lead_investigator_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "lead-investigator")
        assert step, "must have step id: lead-investigator"

    def test_has_build_manifest_step(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "build-manifest")
        assert step, "must have step id: build-manifest"
        assert step.get("type") == "bash", "build-manifest must be type: bash"
        assert step.get("parse_json") is True, "build-manifest must have parse_json: true"

    # --- Step order ---

    def test_prepare_workspace_comes_first(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "prepare-workspace") == 0, (
            "prepare-workspace must be the first step"
        )

    def test_select_topics_before_build_topic_paths(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "select-topics") < self._step_index(
            recipe_data, "build-topic-paths"
        ), "select-topics must come before build-topic-paths"

    def test_build_topic_paths_before_code_tracers(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "build-topic-paths") < self._step_index(
            recipe_data, "wave1-code-tracers"
        ), "build-topic-paths must come before wave1-code-tracers"

    def test_code_tracers_before_lead_investigator(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "wave1-code-tracers") < self._step_index(
            recipe_data, "lead-investigator"
        ), "wave1-code-tracers must come before lead-investigator"

    def test_lead_investigator_before_build_manifest(self, recipe_data: dict) -> None:
        assert self._step_index(recipe_data, "lead-investigator") < self._step_index(
            recipe_data, "build-manifest"
        ), "lead-investigator must come before build-manifest"

    # --- Agent assignments ---

    def test_code_tracers_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-code-tracers")
        assert step.get("agent") == "parallax-discovery:code-tracer", (
            f"wave1-code-tracers must have agent: parallax-discovery:code-tracer, "
            f"got: {step.get('agent')!r}"
        )

    def test_behavior_observers_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-behavior-observers")
        assert step.get("agent") == "parallax-discovery:behavior-observer", (
            f"wave1-behavior-observers must have agent: parallax-discovery:behavior-observer, "
            f"got: {step.get('agent')!r}"
        )

    def test_integration_mappers_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-integration-mappers")
        assert step.get("agent") == "parallax-discovery:integration-mapper", (
            f"wave1-integration-mappers must have agent: parallax-discovery:integration-mapper, "
            f"got: {step.get('agent')!r}"
        )

    def test_lead_investigator_agent(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "lead-investigator")
        assert step.get("agent") == "parallax-discovery:lead-investigator", (
            f"lead-investigator must have agent: parallax-discovery:lead-investigator, "
            f"got: {step.get('agent')!r}"
        )

    # --- Parallel settings ---

    def test_code_tracers_parallel_3(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-code-tracers")
        assert step.get("parallel") == 3, (
            f"wave1-code-tracers must have parallel: 3, got: {step.get('parallel')!r}"
        )

    def test_behavior_observers_parallel_3(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-behavior-observers")
        assert step.get("parallel") == 3, (
            f"wave1-behavior-observers must have parallel: 3, got: {step.get('parallel')!r}"
        )

    def test_integration_mappers_parallel_3(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-integration-mappers")
        assert step.get("parallel") == 3, (
            f"wave1-integration-mappers must have parallel: 3, got: {step.get('parallel')!r}"
        )

    # --- Tier conditions ---

    def test_code_tracers_has_no_tier_condition(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-code-tracers")
        assert "condition" not in step, (
            "wave1-code-tracers must NOT have a condition — it runs for ALL tiers"
        )

    def test_behavior_observers_has_tier3_condition(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-behavior-observers")
        condition = step.get("condition", "")
        assert condition, "wave1-behavior-observers must have a condition (skip Tier 3)"
        assert "3" in condition, (
            f"wave1-behavior-observers condition must reference tier 3, got: {condition!r}"
        )

    def test_integration_mappers_has_tier3_condition(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "wave1-integration-mappers")
        condition = step.get("condition", "")
        assert condition, "wave1-integration-mappers must have a condition (skip Tier 3)"
        assert "3" in condition, (
            f"wave1-integration-mappers condition must reference tier 3, got: {condition!r}"
        )

    # --- Output contracts ---

    def test_lead_investigator_has_reconciliation_output(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "lead-investigator")
        assert step.get("output") == "reconciliation", (
            f"lead-investigator must have output: reconciliation, got: {step.get('output')!r}"
        )

    def test_build_manifest_has_investigation_manifest_output(self, recipe_data: dict) -> None:
        step = self._get_step(recipe_data, "build-manifest")
        assert step.get("output") == "investigation_manifest", (
            f"build-manifest must have output: investigation_manifest, got: {step.get('output')!r}"
        )
