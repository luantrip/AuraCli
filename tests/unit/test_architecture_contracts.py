"""Repository-level ratchets for architecture contracts already established."""

from __future__ import annotations

import ast
from pathlib import Path

from aura_cli.adk.agent import AgentConfig as AdkAgentConfig
from aura_cli.adk.agent import AgentResponse as AdkAgentResponse
from aura_cli.adk.tools import ToolResult as AdkToolResult
from aura_cli.application.agents import AgentConfig, AgentResponse, ToolResult
import aura_cli.cli.function_call_handler as function_call_handler

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOT = REPOSITORY_ROOT / "aura_cli"


def _python_sources() -> list[Path]:
    return sorted(PRODUCT_ROOT.rglob("*.py"))


def test_product_never_imports_pickle() -> None:
    violations: list[str] = []
    for source in _python_sources():
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".", 1)[0]}
            else:
                continue
            if "pickle" in imported:
                violations.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert violations == []


def test_registry_execution_has_one_production_authority() -> None:
    owners: list[str] = []
    for source in _python_sources():
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            owner = node.func.value
            if (
                node.func.attr == "execute_tool"
                and isinstance(owner, ast.Name)
                and owner.id == "registry"
            ):
                owners.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert owners == ["aura_cli/cli/tool_execution.py"]


def test_legacy_manual_core_tool_registry_does_not_return() -> None:
    assert not (PRODUCT_ROOT / "core" / "tools_registry.py").exists()


def test_product_does_not_depend_on_build_scripts() -> None:
    violations: list[str] = []
    for source in _python_sources():
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".", 1)[0]}
            else:
                continue
            if "scripts" in imported:
                violations.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert violations == []


def test_product_consumers_use_canonical_semantic_surface() -> None:
    allowed_implementation = PRODUCT_ROOT / "core" / "memory_advanced"
    allowed_facade = PRODUCT_ROOT / "core" / "semantic"
    violations: list[str] = []
    for source in _python_sources():
        if source.is_relative_to(allowed_implementation) or source.is_relative_to(
            allowed_facade
        ):
            continue
        if "aura_cli.core.memory_advanced" in source.read_text(encoding="utf-8"):
            violations.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert violations == []


def test_memory_synchronizer_is_injected_into_product_consumers() -> None:
    authority = PRODUCT_ROOT / "application" / "workspace" / "memory_sync.py"
    violations = [
        str(source.relative_to(REPOSITORY_ROOT))
        for source in _python_sources()
        if source != authority
        and "get_memory_synchronizer(" in source.read_text(encoding="utf-8")
    ]
    assert violations == []


def test_cloud_provider_aggregate_remains_a_thin_compatibility_surface() -> None:
    aggregate = (
        PRODUCT_ROOT / "core" / "ops_tools" / "infrastructure" / "cloud_providers.py"
    )
    tree = ast.parse(aggregate.read_text(encoding="utf-8"), filename=str(aggregate))
    declarations = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert declarations == []


def test_nonfunctional_production_mock_framework_does_not_return() -> None:
    assert not (PRODUCT_ROOT / "core" / "testing" / "mocking.py").exists()


def test_adk_core_translation_does_not_call_current_core_types_legacy() -> None:
    sources = [
        PRODUCT_ROOT / "core" / "agents" / "adk_wrapper.py",
        PRODUCT_ROOT / "core" / "agents" / "agent_orchestrator.py",
    ]
    violations = [
        str(source.relative_to(REPOSITORY_ROOT))
        for source in sources
        if "legacy" in source.read_text(encoding="utf-8").casefold()
    ]
    assert violations == []


def test_function_call_handler_keeps_its_small_public_surface() -> None:
    assert function_call_handler.__all__ == [
        "execute_tool_call",
        "process_function_calls_loop",
    ]


def test_every_production_app_loop_call_injects_runtime_services() -> None:
    violations: list[str] = []
    for source in _python_sources():
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Call):
                continue
            factory = node.func.func
            if not (
                isinstance(factory, ast.Name) and factory.id == "_get_app_loop_class"
            ):
                continue
            keywords = {keyword.arg for keyword in node.keywords}
            if "runtime_services" not in keywords:
                violations.append(
                    f"{source.relative_to(REPOSITORY_ROOT)}:{node.lineno}"
                )

    assert violations == []


def test_agent_adapters_share_application_contracts() -> None:
    from aura_cli.core.agents.interface import AgentConfig as CoreAgentConfig
    from aura_cli.core.agents.interface import AgentResponse as CoreAgentResponse

    assert AdkAgentConfig is CoreAgentConfig is AgentConfig
    assert AdkAgentResponse is CoreAgentResponse is AgentResponse
    assert AdkToolResult is ToolResult


def test_application_layer_does_not_import_ui_adapters() -> None:
    violations: list[str] = []
    application_root = PRODUCT_ROOT / "application"
    for source in sorted(application_root.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            imported = [module] if module else names
            if any(
                name.startswith(("aura_cli.cli", "aura_cli.tui")) for name in imported
            ):
                violations.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert violations == []


def test_application_layer_does_not_import_other_aura_layers() -> None:
    violations: list[str] = []
    application_root = PRODUCT_ROOT / "application"
    forbidden = ("aura_cli.core", "aura_cli.cli", "aura_cli.tui", "aura_cli.adk")
    for source in sorted(application_root.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            imported = [module] if module else names
            if any(name.startswith(forbidden) for name in imported):
                violations.append(
                    f"{source.relative_to(REPOSITORY_ROOT)}:{node.lineno}"
                )

    assert violations == []


def test_execution_runtime_does_not_render_directly() -> None:
    """Lifecycle producers must emit state; only presentation adapters render it."""
    roots = [
        PRODUCT_ROOT / "application",
        PRODUCT_ROOT / "core" / "agi",
        PRODUCT_ROOT / "cli" / "workers",
    ]
    allowed = {PRODUCT_ROOT / "application" / "paint" / "ansi_art_document.py"}
    forbidden = (
        ".render_info(",
        ".render_warning(",
        ".render_error(",
        ".render_success(",
        ".notify(",
        "console.print(",
    )
    violations = [
        str(source.relative_to(REPOSITORY_ROOT))
        for root in roots
        for source in root.rglob("*.py")
        if source not in allowed
        and any(token in source.read_text(encoding="utf-8") for token in forbidden)
    ]
    assert violations == []


def test_legacy_operational_feedback_has_no_productive_consumer() -> None:
    allowed = {
        PRODUCT_ROOT / "application" / "agents" / "__init__.py",
        PRODUCT_ROOT / "application" / "agents" / "operational_feedback.py",
        PRODUCT_ROOT / "core" / "events" / "operational_feedback.py",
    }
    violations = [
        str(source.relative_to(REPOSITORY_ROOT))
        for source in _python_sources()
        if source not in allowed
        and "operational_feedback import" in source.read_text(encoding="utf-8")
    ]
    assert violations == []


def test_every_visual_capability_declares_required_contracts() -> None:
    from aura_cli.application.presentation.visual_governance import (
        VISUAL_CAPABILITIES,
        audit_visual_capabilities,
    )
    from aura_cli.application.presentation.work_items import WorkItemKind

    assert set(VISUAL_CAPABILITIES) == set(WorkItemKind)
    assert audit_visual_capabilities() == ()


def test_adk_runtime_does_not_use_obsolete_contract_converters() -> None:
    source = PRODUCT_ROOT / "core" / "agents" / "adk_bridge.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    calls = {
        f"{node.func.value.id}.{node.func.attr}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in {"ADKConfigAdapter", "ADKResponseAdapter"}
    }

    assert calls == set()


def test_agent_workflows_share_one_lifecycle_state_contract() -> None:
    from aura_cli.application.agents.workflow import WorkflowState
    from aura_cli.core.agents.agent_workflow import WorkflowStatus

    assert WorkflowStatus is WorkflowState


def test_memory_bridge_is_not_used_by_product_consumers() -> None:
    consumers: list[str] = []
    for source in _python_sources():
        if source.name == "memory_bridge.py":
            continue
        text = source.read_text(encoding="utf-8")
        if "core.agents.memory_bridge" in text or "get_memory_bridge" in text:
            consumers.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert consumers == []


def test_headless_paint_does_not_import_tui_engine() -> None:
    source = PRODUCT_ROOT / "core" / "tools" / "paint_agent_headless.py"
    text = source.read_text(encoding="utf-8")
    assert "aura_cli.application.paint.ansi_art_document" in text
    assert "aura_cli.tui.tools.paint" not in text


def test_removed_tui_paint_document_facade_does_not_return() -> None:
    assert not (
        PRODUCT_ROOT / "tui" / "tools" / "paint" / "ansi_art_document.py"
    ).exists()


def test_tui_paint_action_is_only_a_compatibility_facade() -> None:
    from aura_cli.application.paint.action import Action
    from aura_cli.tui.tools.paint.action import Action as TuiAction

    assert TuiAction is Action


def test_productive_paint_consumers_use_application_action() -> None:
    violations: list[str] = []
    paint_root = PRODUCT_ROOT / "tui" / "tools" / "paint"
    facade = paint_root / "action.py"
    for source in sorted(paint_root.rglob("*.py")):
        if source == facade:
            continue
        text = source.read_text(encoding="utf-8")
        if "tui.tools.paint.action" in text or "from .action import" in text:
            violations.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert violations == []


def test_tui_paint_host_does_not_mutate_document_matrices_directly() -> None:
    source = PRODUCT_ROOT / "tui" / "tools" / "paint" / "paint.py"
    text = source.read_text(encoding="utf-8")

    assert "self.image.ch[" not in text
    assert "self.image.st[" not in text


def test_core_ui_token_port_does_not_import_cli_adapter() -> None:
    source = PRODUCT_ROOT / "core" / "ui_bridge.py"
    assert "aura_cli.cli" not in source.read_text(encoding="utf-8")


def test_productive_adk_consumers_use_application_registry() -> None:
    allowed = {
        "aura_cli/core/agents/__init__.py",
        "aura_cli/core/agents/adk_bridge.py",
    }
    violations: list[str] = []
    for source in _python_sources():
        relative = str(source.relative_to(REPOSITORY_ROOT))
        if relative in allowed:
            continue
        text = source.read_text(encoding="utf-8")
        if "ADKBridgeFactory" in text or "_ensure_adk_bridge" in text:
            violations.append(relative)

    assert violations == []


def test_agi_execution_receives_presentation_through_ports() -> None:
    source = PRODUCT_ROOT / "core" / "agi" / "execution.py"
    assert "aura_cli.cli" not in source.read_text(encoding="utf-8")


def test_migrated_confirmation_and_git_modules_do_not_import_cli() -> None:
    migrated = [
        PRODUCT_ROOT / "core" / "agents" / "specialized_agents" / "ops_code_agent.py",
        PRODUCT_ROOT / "core" / "ops_tools" / "git" / "__init__.py",
        PRODUCT_ROOT / "core" / "tools" / "human_intervention_adapter.py",
        PRODUCT_ROOT / "core" / "embeddings" / "client.py",
        PRODUCT_ROOT / "core" / "llm" / "base.py",
        PRODUCT_ROOT / "core" / "tools" / "dev_tools.py",
        PRODUCT_ROOT / "core" / "tools" / "file_system.py",
        PRODUCT_ROOT / "core" / "agents" / "agent_orchestrator.py",
        PRODUCT_ROOT / "core" / "tools" / "checkpoint_tools.py",
        PRODUCT_ROOT / "core" / "ui_panel.py",
    ]
    for source in migrated:
        assert "aura_cli.cli" not in source.read_text(encoding="utf-8")


def test_core_never_imports_presentation_adapters() -> None:
    violations: list[str] = []
    for source in sorted((PRODUCT_ROOT / "core").rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            imported = [module] if module else names
            if any(
                name.startswith(("aura_cli.cli", "aura_cli.tui")) for name in imported
            ):
                violations.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert violations == []


def test_tui_direct_core_dependencies_do_not_expand() -> None:
    """Freeze known adapter dependencies while ports replace them incrementally."""
    allowed = {
        "aura_cli/tui/__init__.py",
        "aura_cli/tui/app.py",
        "aura_cli/tui/core/cache_manager.py",
        "aura_cli/tui/core/event_bus.py",
        "aura_cli/tui/core/sync_manager.py",
        "aura_cli/tui/mount_runtime.py",
        "aura_cli/tui/screens/context_selector.py",
        "aura_cli/tui/screens/diff_confirmation_screen.py",
        "aura_cli/tui/services/token_usage_snapshot.py",
        "aura_cli/tui/services/tui_session_service.py",
        "aura_cli/tui/theme_loader.py",
        "aura_cli/tui/tools/__init__.py",
        "aura_cli/tui/tools/file_manager/__init__.py",
        "aura_cli/tui/tools/paint/paint.py",
        "aura_cli/tui/tools/paint/recent_files.py",
        "aura_cli/tui/widgets/history/browser_panel.py",
        "aura_cli/tui/widgets/history/session_store.py",
        "aura_cli/tui/widgets/imagination_panel.py",
        "aura_cli/tui/widgets/memory_browser.py",
        "aura_cli/tui/widgets/settings/api_keys_section.py",
        "aura_cli/tui/widgets/settings_panel.py",
        "aura_cli/tui/widgets/snippets.py",
        "aura_cli/tui/widgets/status.py",
    }
    consumers: set[str] = set()
    for source in sorted((PRODUCT_ROOT / "tui").rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            imported = [module] if module else names
            if any(name.startswith("aura_cli.core") for name in imported):
                consumers.add(str(source.relative_to(REPOSITORY_ROOT)))

    assert consumers == allowed


def test_specialized_adk_agents_use_application_runtime_ports() -> None:
    source = PRODUCT_ROOT / "adk" / "specialized.py"
    assert "aura_cli.core" not in source.read_text(encoding="utf-8")


def test_adk_never_imports_core_implementations() -> None:
    violations: list[str] = []
    for source in sorted((PRODUCT_ROOT / "adk").rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            imported = [module] if module else names
            if any(name.startswith("aura_cli.core") for name in imported):
                violations.append(str(source.relative_to(REPOSITORY_ROOT)))

    assert violations == []


def _adapter_import_violations(adapter: str, forbidden: str) -> list[str]:
    violations: list[str] = []
    for source in sorted((PRODUCT_ROOT / adapter).rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            imported = [module] if module else names
            if any(name.startswith(f"aura_cli.{forbidden}") for name in imported):
                violations.append(
                    f"{source.relative_to(REPOSITORY_ROOT)}:{node.lineno}"
                )
    return violations


def test_cli_and_tui_adapters_do_not_import_each_other() -> None:
    assert _adapter_import_violations("cli", "tui") == []
    assert _adapter_import_violations("tui", "cli") == []


def test_service_registry_execution_only_occurs_inside_guard_pipeline() -> None:
    """No production consumer may bypass cli.tool_execution guards."""
    violations: list[str] = []
    allowed = PRODUCT_ROOT / "cli" / "tool_execution.py"
    for source in _python_sources():
        if source == allowed or source.name == "service_registry.py":
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "execute_tool"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "registry"
            ):
                violations.append(
                    f"{source.relative_to(REPOSITORY_ROOT)}:{node.lineno}"
                )

    assert violations == []


def test_aura_artifact_roots_are_not_constructed_outside_layout() -> None:
    """Aura-owned roots must be obtained from ArtifactLayout/core.paths."""
    violations: list[str] = []
    allowed = PRODUCT_ROOT / "application" / "artifacts.py"
    for source in _python_sources():
        if source == allowed:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            hardcoded = False
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                hardcoded = (
                    node.func.id == "Path"
                    and bool(node.args)
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                    and node.args[0].value.startswith(".aura")
                )
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                hardcoded = (
                    isinstance(node.right, ast.Constant) and node.right.value == ".aura"
                )
            if hardcoded:
                violations.append(
                    f"{source.relative_to(REPOSITORY_ROOT)}:{node.lineno}"
                )

    assert violations == []


def test_glyph_vocabulary_parity_cli_and_tui() -> None:
    """G4 — CLI and TUI must render the SAME glyph for each shared semantic token.

    `application/presentation/glyph_vocabulary.SHARED_GLYPHS` is the single source
    of truth. This ratchet fails CI when either surface drifts (historically the
    TUI used ◉/▶ for AGI/OPS and ⬡ for IDLE, colliding with the AGI hexagon).
    """
    from aura_cli.application.presentation.glyph_vocabulary import SHARED_GLYPHS
    from aura_cli.cli.ui.constants import UIIcons
    import aura_cli.tui.constants as tui_constants

    missing_cli: list[str] = []
    missing_tui: list[str] = []
    cli_drift: list[str] = []
    tui_drift: list[str] = []

    for token, canonical in SHARED_GLYPHS.items():
        if not hasattr(UIIcons, token):
            missing_cli.append(token)
        elif getattr(UIIcons, token) != canonical:
            cli_drift.append(
                f"{token}: canonical={canonical!r} cli={getattr(UIIcons, token)!r}"
            )
        if not hasattr(tui_constants, token):
            missing_tui.append(token)
        elif getattr(tui_constants, token) != canonical:
            tui_drift.append(
                f"{token}: canonical={canonical!r} tui={getattr(tui_constants, token)!r}"
            )

    assert missing_cli == [], f"CLI UIIcons missing shared tokens: {missing_cli}"
    assert missing_tui == [], f"TUI constants missing shared tokens: {missing_tui}"
    assert cli_drift == [], f"CLI glyphs drifted from canonical: {cli_drift}"
    assert tui_drift == [], f"TUI glyphs drifted from canonical: {tui_drift}"


def _tui_color_fallbacks() -> dict[str, str]:
    """Extract declared COLOR_* fallbacks from tui/constants.py via AST.

    The TUI resolves `COLOR_X = _get_color("x", "<fallback>")` from the live
    ThemeManager at import time, so the runtime attribute reflects the active
    theme, not the declared base palette. Reading the second `_get_color`
    argument from source gives the stable, theme-independent base value.
    """
    tui_constants = PRODUCT_ROOT / "tui" / "constants.py"
    tree = ast.parse(tui_constants.read_text(encoding="utf-8"))
    fallbacks: dict[str, str] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_get_color"
            and len(node.args) == 2
            and all(isinstance(arg, ast.Constant) for arg in node.args)
        ):
            fallbacks[node.args[0].value] = node.args[1].value
    return fallbacks


def test_color_palette_parity_cli_and_tui() -> None:
    """G5 — CLI and TUI must share the SAME base color for each semantic token.

    `application/presentation/color_palette.SHARED_PALETTE` is the single source
    of truth for the severity + brand palette. The CLI side is `UIStyles._DEFAULTS`
    (static base, pre theme override); the TUI side is the declared `_get_color`
    fallback. Typographic emphasis tokens (title/label/code) are surface-private
    and intentionally excluded.
    """
    from aura_cli.application.presentation.color_palette import SHARED_PALETTE
    from aura_cli.cli.ui.constants import UIStyles

    tui_fallbacks = _tui_color_fallbacks()

    missing_cli: list[str] = []
    missing_tui: list[str] = []
    cli_drift: list[str] = []
    tui_drift: list[str] = []

    for token, canonical in SHARED_PALETTE.items():
        if token not in UIStyles._DEFAULTS:
            missing_cli.append(token)
        elif UIStyles._DEFAULTS[token] != canonical:
            cli_drift.append(
                f"{token}: canonical={canonical!r} cli={UIStyles._DEFAULTS[token]!r}"
            )
        if token not in tui_fallbacks:
            missing_tui.append(token)
        elif tui_fallbacks[token] != canonical:
            tui_drift.append(
                f"{token}: canonical={canonical!r} tui={tui_fallbacks[token]!r}"
            )

    assert missing_cli == [], (
        f"CLI UIStyles._DEFAULTS missing palette tokens: {missing_cli}"
    )
    assert missing_tui == [], f"TUI _get_color missing palette tokens: {missing_tui}"
    assert cli_drift == [], f"CLI palette drifted from canonical: {cli_drift}"
    assert tui_drift == [], f"TUI palette drifted from canonical: {tui_drift}"


def test_tool_render_has_no_legacy_grouped_panel_consumer() -> None:
    """G6 — the LEGACY grouped tool-render mode (ToolExecutionPanel) must stay
    unreachable: no product code may populate it via `.add_tool(...)`.

    The canonical tool-call presenter (`tool_display_adapter.present_tool_call`)
    now offers two modes only (compact inline, full header). `ToolExecutionPanel`
    is dead (its only populator — the adapter's `panel_enabled` branch — was
    removed) and kept solely as an inert LEGACY surface. This ratchet fails CI if
    anyone re-wires the grouped panel by calling `add_tool` on it, or if the
    canonical adapter starts importing the LEGACY module again.

    `live_dashboard` has an unrelated `DashboardState.add_tool`, matched by
    receiver name to avoid a false positive.
    """
    # 1) The canonical adapter must not import the LEGACY panel module.
    adapter = PRODUCT_ROOT / "cli" / "ui" / "tool_display_adapter.py"
    assert "tool_execution_panel" not in adapter.read_text(encoding="utf-8"), (
        "tool_display_adapter must not reference the LEGACY tool_execution_panel"
    )

    # 2) No product code may call `<tool panel>.add_tool(...)`. The only legitimate
    #    `.add_tool` lives on the dashboard state object, excluded by receiver.
    allowed_add_tool = {
        PRODUCT_ROOT / "cli" / "ui" / "live_dashboard.py",  # DashboardState.add_tool
    }
    violations: list[str] = []
    for source in _python_sources():
        if source in allowed_add_tool:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_tool"
            ):
                violations.append(
                    f"{source.relative_to(REPOSITORY_ROOT)}:{node.lineno}"
                )

    assert violations == [], (
        f"LEGACY grouped tool panel re-wired via add_tool: {violations}"
    )


def test_status_state_has_single_owning_sink() -> None:
    """G3 — current status is mutated through ONE owning sink only.

    `StatsTracker` (core/stats.py) owns the `current_status` field and exposes
    `set_status(...)` as the single mutation entry point; display surfaces
    (CLI StatusManager/StatusBar, TUI status widgets) must READ this state, never
    assign a competing status field. This ratchet fails CI if any module outside
    the owner assigns `*.current_status`, which would fork the status sink and
    reintroduce the "StatusBar + panel + footer disagree" class of bug.
    """
    owner = PRODUCT_ROOT / "core" / "stats.py"
    violations: list[str] = []
    for source in _python_sources():
        if source == owner:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, ast.AugAssign):
                targets = [node.target]
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "current_status"
                ):
                    violations.append(
                        f"{source.relative_to(REPOSITORY_ROOT)}:{node.lineno}"
                    )

    assert violations == [], (
        f"status sink forked — assign current_status only via StatsTracker: {violations}"
    )


def _tcss_rules(path: Path) -> dict[str, dict[str, str]]:
    """Parse a .tcss file into {selector: {property: value}}.

    Deliberately small/robust: strips block comments, then matches
    `selector { body }` and splits the body on `;` and `:`. Good enough to
    detect structural property duplication across stylesheets.
    """
    import re

    text = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
    rules: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"(?:^|\})\s*([^{}]+?)\s*\{([^{}]*)\}", text, flags=re.M):
        selector = " ".join(match.group(1).split())
        body = rules.setdefault(selector, {})
        for declaration in match.group(2).split(";"):
            if ":" in declaration:
                prop, value = declaration.split(":", 1)
                body[prop.strip()] = value.strip()
    return rules


# Baseline of structural properties duplicated between layout.tcss and a theme
# file. layout.tcss loads LAST and owns structure/geometry; theme files own
# color/visual tokens. Each entry is "<selector> :: <property>". The ratchet
# This set is only allowed to shrink. The theme-system refactor introduced
# debt down to ZERO: layout.tcss is the sole structural authority, theme.tcss is
# pure color (tokenized to $theme-*), and the divergent macos_light.tcss was
# merged in and removed. This is now a ZERO-TOLERANCE contract — any new
# layout/theme property duplication fails CI.
_CSS_DUP_BASELINE: set[str] = set()


def _current_css_duplications() -> set[str]:
    styles = PRODUCT_ROOT / "tui" / "styles"
    layout = _tcss_rules(styles / "layout.tcss")
    duplicated: set[str] = set()
    for theme_file in sorted(styles.glob("*.tcss")):
        if theme_file.name == "layout.tcss":
            continue
        theme = _tcss_rules(theme_file)
        for selector, layout_props in layout.items():
            theme_props = theme.get(selector, {})
            for prop in set(layout_props) & set(theme_props):
                duplicated.add(f"{selector} :: {prop}")
    return duplicated


def test_no_new_structural_css_duplication_between_layout_and_themes() -> None:
    """G7 — structural CSS lives in layout.tcss, not duplicated into theme files.

    layout.tcss loads last and owns geometry/structure; theme files own visual
    tokens. A property defined for the SAME selector in both places is a
    duplication smell (and, when values differ, a silent override). This ratchet
    fails CI when a NEW duplication appears beyond the frozen baseline.
    """
    current = _current_css_duplications()
    new_dups = sorted(current - _CSS_DUP_BASELINE)
    assert new_dups == [], f"new layout/theme CSS duplication introduced: {new_dups}"


def test_css_duplication_baseline_only_shrinks() -> None:
    """Companion ratchet: when a duplication is removed, drop it from the
    baseline so the debt can only burn down, never silently regrow.
    """
    current = _current_css_duplications()
    stale = sorted(_CSS_DUP_BASELINE - current)
    assert stale == [], (
        f"these CSS duplications were resolved — remove them from "
        f"_CSS_DUP_BASELINE: {stale}"
    )


def test_both_surfaces_implement_the_semantic_token_vocabulary() -> None:
    """Lote 0 — CLI and TUI both implement the full neutral token vocabulary.

    `application/presentation/semantic_tokens.ALL_COLOR_ROLES` is the single
    source of truth for WHICH semantic color roles exist. Values differ per
    surface (Rich names vs hex) and per theme, but the ROLE SET must be covered
    on both sides, so a role like `status_thinking` or `agent_agi` is never
    hard-coded on one surface and missing on the other.
    """
    from aura_cli.application.presentation.semantic_tokens import ALL_COLOR_ROLES
    from aura_cli.cli.ui.constants import UIStyles
    from aura_cli.tui.styles.themes import ThemeColors

    tui_roles = set(ThemeColors.__dataclass_fields__)
    cli_roles = set(UIStyles._DEFAULTS)

    tui_missing = sorted(ALL_COLOR_ROLES - tui_roles)
    cli_missing = sorted(ALL_COLOR_ROLES - cli_roles)

    assert tui_missing == [], f"TUI ThemeColors missing semantic roles: {tui_missing}"
    assert cli_missing == [], (
        f"CLI UIStyles._DEFAULTS missing semantic roles: {cli_missing}"
    )


def test_tcss_rule_bodies_use_only_semantic_color_tokens() -> None:
    """Lote 4 — the semantic lock: no literal colors inside .tcss rule bodies.

    Every color in a rule body must reference a semantic token (`$theme-*`).
    Literal hex / named colors are allowed ONLY in `$theme-*` variable
    *declarations* (the palette definitions a theme owns) and as the Textual
    keyword `transparent`/`none`/`auto`/`initial`. This is what makes the whole
    style system semantic: themes change by swapping the injected `$theme-*`
    values, never by editing scattered literals.
    """
    import re

    styles = PRODUCT_ROOT / "tui" / "styles"
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    violations: list[str] = []

    for tcss in sorted(styles.glob("*.tcss")):
        text = re.sub(r"/\*.*?\*/", "", tcss.read_text(encoding="utf-8"), flags=re.S)
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("$") or ":" not in line:
                # variable declarations ($theme-*: #hex) and non-declarations skip
                continue
            if hex_pattern.search(line):
                violations.append(f"{tcss.name}:{lineno}: {line}")

    assert violations == [], (
        "literal colors in rule bodies — use $theme-* tokens:\n" + "\n".join(violations)
    )


def test_tool_args_reach_presentation_only_through_safe_payloads() -> None:
    """safe_payloads is the mandatory ingress for tool arguments.

    Tool argument *values* may contain secrets (tokens, file contents, commands).
    They must never be serialized for display except through
    `application/presentation/safe_payloads` (which redacts values to shape-only).
    This ratchet scans the presentation surfaces (cli/ui, tui) and fails CI if a
    module serializes `tool_args` (json.dumps / str() / f-string) without routing
    through safe_payloads — closing the door on a new surface leaking raw args.
    """
    import re

    presentation_roots = (
        PRODUCT_ROOT / "cli" / "ui",
        PRODUCT_ROOT / "tui",
    )
    safe_module = "safe_payloads"
    # serialization of something named *tool_args* (attribute or key)
    serialize_pattern = re.compile(
        r"(json\.dumps\s*\([^)]*tool_args"  # json.dumps(... tool_args ...)
        r"|str\s*\([^)]*tool_args"  # str(... tool_args ...)
        r"|f\"[^\"]*\{[^}]*tool_args"  # f"...{...tool_args...}"
        r"|f'[^']*\{[^}]*tool_args)"  # f'...{...tool_args...}'
    )
    violations: list[str] = []

    for root in presentation_roots:
        for source in sorted(root.rglob("*.py")):
            text = source.read_text(encoding="utf-8")
            uses_safe = safe_module in text
            for lineno, line in enumerate(text.splitlines(), start=1):
                if "tool_args" not in line:
                    continue
                if serialize_pattern.search(line) and not uses_safe:
                    violations.append(
                        f"{source.relative_to(REPOSITORY_ROOT)}:{lineno}: {line.strip()}"
                    )

    assert violations == [], (
        "tool_args serialized for display without safe_payloads:\n"
        + "\n".join(violations)
    )


# Residual Rich renderables printed directly by core tools — tracked per file.
# `core/` is the engine: tools return data and the CLI presentation layer
# (`ToolResult` + `tabular_result`) renders it. Tables were removed; what remains
# is docker command-output Panels (logs/exec/compose), which need their own
# design (return text vs. a streaming channel). The ratchet only lets this SHRINK.
_CORE_PRINTED_RENDERABLE_BASELINE: dict[str, int] = {
    "core/ops_tools/docker/__init__.py": 5,
}


def _core_printed_renderables() -> dict[str, int]:
    """Count `<x>.print(table|panel|Table(...)|Panel(...))` per file."""
    counts: dict[str, int] = {}
    for root in (PRODUCT_ROOT / "core" / "ops_tools", PRODUCT_ROOT / "core" / "tools"):
        for source in sorted(root.rglob("*.py")):
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            hits = 0
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "print"
                ):
                    continue
                for arg in node.args:
                    is_named = isinstance(arg, ast.Name) and arg.id in {
                        "table",
                        "panel",
                    }
                    is_ctor = (
                        isinstance(arg, ast.Call)
                        and isinstance(arg.func, ast.Name)
                        and arg.func.id in {"Table", "Panel"}
                    )
                    if is_named or is_ctor:
                        hits += 1
            if hits:
                counts[str(source.relative_to(PRODUCT_ROOT))] = hits
    return counts


def test_core_tools_do_not_print_new_rich_renderables() -> None:
    current = _core_printed_renderables()
    grown = {
        path: count
        for path, count in current.items()
        if count > _CORE_PRINTED_RENDERABLE_BASELINE.get(path, 0)
    }
    assert grown == {}, f"core tools must return data, not print Table/Panel: {grown}"


def test_core_printed_renderable_baseline_only_shrinks() -> None:
    current = _core_printed_renderables()
    stale = {
        path: count
        for path, count in _CORE_PRINTED_RENDERABLE_BASELINE.items()
        if current.get(path, 0) < count
    }
    assert stale == {}, f"residual shrank — lower/remove these in the baseline: {stale}"


def test_provider_credential_tables_live_only_in_provider_spec() -> None:
    """P1-1 — a provider↔credential TABLE is declared once, in ProviderSpec.

    Parallel tables (four of them, drifting apart) caused the Cerebras
    validator/default bug. Product code in `core/llm` and `core/api_key*` must
    derive such collections from `core/llm/provider_spec`. A lone
    `os.environ.get("X_API_KEY")` is *usage*, not a table, and stays legal; what
    this ratchet forbids is a literal collection (dict/list/tuple/set) holding
    credential names of 3+ different providers, which is a fifth table.
    """
    import re

    credential = re.compile(
        r"(GOOGLE|GEMINI|OPENAI|ANTHROPIC|OPENROUTER|NVIDIA|CEREBRAS|GROQ)_API_KEY"
    )
    allowed = {PRODUCT_ROOT / "core" / "llm" / "provider_spec.py"}
    scanned = [
        *sorted((PRODUCT_ROOT / "core" / "llm").glob("*.py")),
        PRODUCT_ROOT / "core" / "api_key_store.py",
        PRODUCT_ROOT / "core" / "api_keys.py",
    ]
    violations: list[str] = []
    for source in scanned:
        if source in allowed:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
                continue
            providers = {
                match.group(1)
                for child in ast.walk(node)
                if isinstance(child, ast.Constant)
                and isinstance(child.value, str)
                and (match := credential.fullmatch(child.value))
            }
            # GEMINI and GOOGLE are one provider; collapse before counting.
            providers = {"GOOGLE" if name == "GEMINI" else name for name in providers}
            if len(providers) >= 3:
                violations.append(
                    f"{source.relative_to(REPOSITORY_ROOT)}:{node.lineno}: "
                    f"table of {sorted(providers)}"
                )
    assert violations == [], "credential tables outside ProviderSpec:\n" + "\n".join(
        violations
    )


def test_model_catalog_is_declared_as_package_data() -> None:
    """P1-2 — the canonical model catalog must ship with the wheel.

    `core/llm/models.json` is the single source of truth for the model list. If it
    is not declared in `[tool.setuptools.package-data]`, an installed (non-editable)
    wheel silently loses it and the CLI runs on the minimal emergency catalog.
    """
    pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    section = pyproject.split("[tool.setuptools.package-data]", 1)[1].split("\n[", 1)[0]
    assert '"aura_cli.core.llm"' in section and "models.json" in section
    assert (PRODUCT_ROOT / "core" / "llm" / "models.json").is_file()


def test_build_backend_floor_supports_the_declared_license_syntax() -> None:
    """The wheel must build: SPDX `license = "..."` (PEP 639) needs setuptools>=77.

    With the old `setuptools>=64.0` floor, an environment resolving setuptools 65.x
    rejected `project.license` and `pip wheel` failed at metadata generation. The
    floor and the license syntax must move together.
    """
    import re

    pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = pyproject.split("[project]", 1)[1].split("\n[", 1)[0]
    uses_spdx_string = re.search(r'^license\s*=\s*"', project, re.MULTILINE) is not None

    build_system = pyproject.split("[build-system]", 1)[1].split("\n[", 1)[0]
    match = re.search(r"setuptools>=(\d+)(?:\.(\d+))?", build_system)
    assert match is not None, "build-system must pin a setuptools floor"
    major = int(match.group(1))

    if uses_spdx_string:
        assert major >= 77, (
            f"license is an SPDX string (PEP 639) but setuptools floor is {major}; "
            "needs >=77.0.3"
        )


def test_cli_interactive_prompts_go_through_the_single_prompt_layer() -> None:
    """P1-3 — one interactive-prompt toolkit for the CLI.

    Onboarding (questionary) and /settings (stock prompt_toolkit dialogs) disagreed
    on `Enter`, so the same gesture behaved differently in the same product. All CLI
    prompts now come from `cli/ui/prompts.py`; `cli/` and `core/` may not import
    `questionary` or the stock `prompt_toolkit.shortcuts` dialogs. The TUI is a
    separate surface (Textual) and is out of scope.
    """
    stock_dialogs = {
        "radiolist_dialog",
        "input_dialog",
        "yes_no_dialog",
        "message_dialog",
        "button_dialog",
        "checkboxlist_dialog",
        "progress_dialog",
        "prompt",
        "PromptSession",
    }
    scanned_roots = (PRODUCT_ROOT / "cli", PRODUCT_ROOT / "core")
    violations: list[str] = []
    for source in _python_sources():
        if not any(root in source.parents for root in scanned_roots):
            continue
        relative = source.relative_to(REPOSITORY_ROOT).as_posix()
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                banned = [
                    alias.name
                    for alias in node.names
                    if alias.name.split(".")[0] == "questionary"
                    or alias.name == "prompt_toolkit.shortcuts"
                ]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                banned = []
                if module.split(".")[0] == "questionary" or (
                    module == "prompt_toolkit.shortcuts"
                    and any(alias.name in stock_dialogs for alias in node.names)
                ):
                    banned.append(module)
            else:
                continue
            violations.extend(f"{relative}:{node.lineno}: {name}" for name in banned)
    assert violations == [], "use aura_cli.cli.ui.prompts instead:\n" + "\n".join(
        violations
    )


# ---------------------------------------------------------------------------
# Consolidated config backend (AppSettings / ConfigCompat)
# ---------------------------------------------------------------------------
# All callers outside the config infrastructure layer must route through
# ConfigCompat (get_config_manager) rather than accessing SecureConfig directly.
# Exempt files are the infra layer itself (config.py, secure_config.py,
# api_key_store.py, di_bootstrap.py, api_keys.py).

_P2_1_EXEMPT_SUFFIXES = {
    "aura_cli/core/config.py",
    "aura_cli/core/secure_config.py",
    "aura_cli/core/api_key_store.py",
    "aura_cli/core/di_bootstrap.py",
    "aura_cli/core/api_keys.py",
}


def test_api_key_callers_route_through_config_compat() -> None:
    """No file outside the config infra layer may call secure_config_manager directly."""
    violations: list[str] = []
    for source in _python_sources():
        relative = source.relative_to(REPOSITORY_ROOT).as_posix()
        if any(relative.endswith(suf) or relative == suf for suf in _P2_1_EXEMPT_SUFFIXES):
            continue
        text = source.read_text(encoding="utf-8")
        if "secure_config_manager" not in text:
            continue
        # Count non-comment, non-docstring occurrences
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if "secure_config_manager" in stripped and not stripped.startswith("#"):
                violations.append(f"{relative}:{i}: {stripped[:80]}")
    assert violations == [], (
        "Direct secure_config_manager access bypasses the AppSettings backend.\n"
        "Use get_config_manager().get_api_key() / .set_api_key() instead.\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Tool-panel chain removal (dead code, G6 follow-through)
# ---------------------------------------------------------------------------
# tool_panel_helper.py and tool_execution_panel.py were dead code (PE-G6 proved
# panel.executions always empty → no-op). Both files were deleted. This ratchet
# ensures they are never re-introduced.

_DELETED_TOOL_PANEL_MODULES = {
    PRODUCT_ROOT / "cli" / "workers" / "tool_panel_helper.py",
    PRODUCT_ROOT / "cli" / "ui" / "components" / "tool_execution_panel.py",
}


def test_deleted_tool_panel_modules_do_not_exist() -> None:
    """Dead modules removed in G6 follow-through must not be re-introduced."""
    reintroduced = [str(p) for p in _DELETED_TOOL_PANEL_MODULES if p.exists()]
    assert reintroduced == [], (
        "These dead-code modules were intentionally deleted and must not return:\n"
        + "\n".join(reintroduced)
    )
