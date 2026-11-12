"""Contract tests for generated tool metadata."""

from __future__ import annotations

from aura_cli.core.tool_manifest import TOOL_MANIFEST


def test_vision_tools_are_discoverable_with_correct_effects() -> None:
    """F-P2-3 — vision tools were runtime-callable but missing from the catalog.

    They are now registered by discovery and present in the manifest. Read-only
    inspections (view_image, describe_url_visual) are read_only; take_screenshot
    may write a file, so it stays mutating.
    """
    by_name = {entry["name"]: entry for entry in TOOL_MANIFEST}
    for name in ("view_image", "take_screenshot", "describe_url_visual"):
        assert name in by_name, name
    assert by_name["view_image"]["effect"] == "read_only"
    assert by_name["describe_url_visual"]["effect"] == "read_only"
    assert by_name["take_screenshot"]["effect"] == "mutating"


def test_internal_agent_helper_is_not_exposed_as_a_tool() -> None:
    """``schemas_for_categories`` is an internal helper on the specialized
    agents (it selects tool schemas by category for the agent itself). Reflection
    once captured it as ``<agent>_schemas_for_categories`` and listed four phantom
    tools. Neither the generated manifest nor the runtime filter may resurface it.
    """
    names = [entry["name"] for entry in TOOL_MANIFEST]
    offenders = [name for name in names if name.endswith("schemas_for_categories")]
    assert offenders == [], offenders

    from scripts.tool_discovery import _is_reflection_artifact

    for agent in ("code_agent", "test_agent", "refactor_agent", "review_agent"):
        assert _is_reflection_artifact(f"{agent}_schemas_for_categories")
    assert _is_reflection_artifact("schemas_for_categories")


def test_paint_tool_schema_matches_public_signature_name() -> None:
    entry = next(item for item in TOOL_MANIFEST if item["name"] == "paint_generate_art")
    properties = entry["schema"]["function"]["parameters"]["properties"]

    assert "output_format" in properties
    assert "format" not in properties


def test_registry_and_capability_matrix_preserve_manifest_risk() -> None:
    from aura_cli.core.service_registry import (
        get_capability_matrix,
        get_service_registry,
    )

    manifest_entry = next(
        item for item in TOOL_MANIFEST if item["name"] == "write_file"
    )
    descriptor = get_service_registry().get_tool("write_file")
    capability = get_capability_matrix().require("write_file")
    expected_risk = "low" if manifest_entry["effect"] == "read_only" else "medium"

    assert descriptor is not None
    assert descriptor.risk == expected_risk
    assert capability.risk == expected_risk
    assert capability.effect == manifest_entry["effect"]
