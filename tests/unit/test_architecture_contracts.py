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
