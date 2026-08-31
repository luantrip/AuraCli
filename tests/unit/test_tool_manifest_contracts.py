"""Contract tests for generated tool metadata."""

from __future__ import annotations

from aura_cli.core.tool_manifest import TOOL_MANIFEST


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
