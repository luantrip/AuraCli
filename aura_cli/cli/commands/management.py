"""Management command handlers for Aura CLI.

Handles commands:
- /session: Manage sessions
- /workflow: Manage workflows
- /cache: Manage system cache
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aura_cli.application.sessions import (
    LoadSessionStatus,
    count_conversation_messages,
    load_session_into_workspace,
    save_workspace_session,
)
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def _session_manager_for(app_loop: Any = None):
    """Resolve the session singleton against the active CLI workspace."""
    from aura_cli.core.sessions.session_manager import get_session_manager

    project_root = getattr(app_loop, "project_root", None)
    return get_session_manager(
        Path(project_root).expanduser().resolve() if project_root is not None else None
    )


def _create_workflow_tool_executor(console: Console) -> Callable[[str, Dict, int], Any]:
    """Adapt synchronous workflows to the canonical guarded tool executor."""
    from aura_cli.cli.tool_execution import execute_tool_call
    from aura_cli.cli.ui.manager import UIManager
    from aura_cli.core.service_registry import get_tools_dict
    from aura_cli.core.stats import get_stats

    stats = get_stats()
    ui = UIManager(stats=stats, console=console)
    available_tools = get_tools_dict()

    def execute(tool_name: str, params: Dict, timeout: int) -> Any:
        del timeout  # Timeout policy remains owned by the canonical executor.
        result, _elapsed = asyncio.run(
            execute_tool_call(
                tool_name,
                params,
                f"workflow-{uuid.uuid4().hex}",
                available_tools,
                [],
                stats,
                ui,
                console,
            )
        )
        return result

    return execute


def handle_session(args: str, app_loop: Any = None) -> Optional[str]:
    """Manage sessions (save/load/list/delete/info).

    Args:
        args: Sub-command and optional name (e.g. "save myproject", "load abc123").
        app_loop: AppLoop instance — required for save/load to access conversation_history.
    """
    console = Console()

    if not args:
        panel = Panel(
            """[bold]Uso:[/bold] /session <comando> [args]

[bold]Comandos:[/bold]
  [cyan]save <nome>[/]   - Salvar sessão atual
  [cyan]load <id>[/]     - Carregar sessão salva (restaura histórico)
  [cyan]list[/]          - Listar sessões salvas
  [cyan]delete <id>[/]   - Excluir sessão salva
  [cyan]info[/]          - Informações da sessão atual""",
            title=f"[{UIStyles.TITLE}]{UIIcons.AURA} Gestão de Sessão[/]",
            border_style=UIStyles.BORDER_PRIMARY,
        )
        console.print(panel)
        return None

    parts = args.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else None

    _DISPATCH = {
        "info": _session_info,
        "list": _session_list,
        "save": _session_save,
        "load": _session_load,
        "delete": _session_delete,
    }
    handler = _DISPATCH.get(cmd)
    if handler:
        return handler(console, arg, app_loop)
    return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Comando desconhecido: {cmd}[/]"


def handle_resume(reference: str, app_loop: Any = None) -> Optional[str]:
    """Resume a saved session using the canonical session-load use case."""
    return _session_load(Console(), reference.strip() or None, app_loop)


def _session_info(console: Console, _arg: Any, app_loop: Any) -> Optional[str]:
    """Handle /session info."""
    from aura_cli.core.sessions.session_state import get_session_state

    state = get_session_state().get_current_state()
    if not state:
        return f"[{UIStyles.WARNING}]{UIIcons.WARNING} Nenhuma sessão ativa.[/]"

    history = getattr(app_loop, "conversation_history", None) or []
    msg_count = count_conversation_messages(history)
    info = (
        f"[bold]ID:[/bold] {state.session_id}\n"
        f"[bold]Início:[/bold] {getattr(state, 'created_at', '—')}\n"
        f"[bold]Mensagens:[/bold] {msg_count}\n"
        f"[bold]Modo:[/bold] {getattr(state, 'active_mode', 'chat')}"
    )
    panel = Panel(
        info,
        title=f"[{UIStyles.TITLE}]{UIIcons.INFO} Sessão Atual[/]",
        border_style=UIStyles.BORDER_ACCENT,
    )
    console.print(panel)
    return None


def _session_list(console: Console, _arg: Any, _app_loop: Any) -> Optional[str]:
    """Handle /session list."""
    try:
        manager = _session_manager_for(_app_loop)
        sessions = manager.list_sessions(limit=20, sort_by="updated_at")
    except Exception as e:
        logger.debug("Session listing error: %s", e)
        sessions = []

    table = Table(
        title="Sessões salvas", box=None, show_header=True, header_style="bold cyan"
    )
    table.add_column("Nome", style="white")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Atualizado", style="dim", width=18)
    table.add_column("Mensagens", justify="right")

    if not sessions:
        console.print(
            f"[{UIStyles.MUTED}]Nenhuma sessão salva. Use /session save <nome> para salvar.[/]"
        )
    else:
        for s in sessions:
            updated = (
                s.updated_at[:16].replace("T", " ")
                if getattr(s, "updated_at", None)
                else "—"
            )
            table.add_row(
                s.name,
                s.id,
                updated,
                str(len(getattr(s, "conversation_history", []))),
            )
        console.print(table)
    return None


def _session_save(console: Console, arg: Optional[str], app_loop: Any) -> Optional[str]:
    """Handle /session save <name>."""
    if not arg:
        return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Uso: /session save <nome>[/]"
    if app_loop is None:
        return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Erro interno: contexto do loop não disponível.[/]"
    try:
        manager = _session_manager_for(app_loop)
        outcome = save_workspace_session(
            manager,
            name=arg,
            conversation_history=getattr(app_loop, "conversation_history", []),
            model=getattr(app_loop, "final_model", ""),
        )
        return (
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Sessão '{arg}' salva "
            f"(ID: {outcome.session_id}, {outcome.message_count} mensagens).[/]"
        )
    except Exception as e:
        logger.error("Error saving session: %s", e)
        return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Failed to save session: {e}[/]"


def _session_load(console: Console, arg: Optional[str], app_loop: Any) -> Optional[str]:
    """Handle /session load <id>."""
    if not arg:
        return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Uso: /session load <id>[/]"
    if app_loop is None:
        return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Erro interno: contexto do loop não disponível.[/]"
    try:
        manager = _session_manager_for(app_loop)
        external_source = _external_resume_source(arg)
        if external_source:
            from aura_cli.core.sessions.external_import import (
                ExternalSessionImportError,
                import_external_session,
                preview_external_session,
            )

            try:
                preview = preview_external_session(
                    external_source,
                    workspace_root=Path(
                        getattr(app_loop, "project_root", Path.cwd())
                    ),
                    active_model=getattr(app_loop, "final_model", ""),
                )
                if preview.requires_confirmation:
                    reasons = "; ".join(preview.divergence_reasons)
                    return (
                        f"[{UIStyles.WARNING}]{UIIcons.WARNING} Importação bloqueada por "
                        f"divergência ({reasons}). Use `aura --resume` para confirmar "
                        f"interativamente.[/]"
                    )
                imported = import_external_session(manager, external_source)
            except ExternalSessionImportError as exc:
                return f"[{UIStyles.ERROR}]{UIIcons.ERROR} {exc}[/]"
            outcome = load_session_into_workspace(
                manager, reference=imported.id, workspace=app_loop
            )
        else:
            outcome = load_session_into_workspace(
                manager,
                reference=arg,
                workspace=app_loop,
            )
        if outcome.status is LoadSessionStatus.AMBIGUOUS:
            names = ", ".join(f"{s.name} ({s.id})" for s in outcome.matches)
            return f"[{UIStyles.WARNING}]{UIIcons.WARNING} Ambíguo: múltiplas sessões coincidem: {names}[/]"
        if outcome.status is LoadSessionStatus.NOT_FOUND:
            return (
                f"[{UIStyles.ERROR}]{UIIcons.ERROR} Sessão '{arg}' não encontrada. "
                f"Use /session list para ver as disponíveis.[/]"
            )
        session = outcome.session
        if session is None:
            return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Sessão indisponível.[/]"
        return (
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Sessão '{session.name}' carregada "
            f"(ID: {session.id}, {outcome.message_count} mensagens). Histórico restaurado.[/]"
        )
    except Exception as e:
        logger.error("Error loading session: %s", e)
        return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Failed to load session: {e}[/]"


def _external_resume_source(reference: str) -> str | None:
    """Resolve direct external sources without provider discovery or execution."""
    prefixes = ("file:", "grok:", "codex:", "claude:", "opencode:")
    if reference.startswith(prefixes):
        source = reference.split(":", 1)[1]
        provider = reference.split(":", 1)[0].casefold()
        if provider in {"grok", "codex"} and not Path(source).expanduser().exists():
            from aura_cli.core.sessions.external_discovery import (
                resolve_external_reference,
            )

            resolved = resolve_external_reference(reference)
            return str(resolved) if resolved else source
        return source or None
    candidate = Path(reference).expanduser()
    return str(candidate) if candidate.exists() else None


def _session_delete(
    console: Console, arg: Optional[str], _app_loop: Any
) -> Optional[str]:
    """Handle /session delete <id>."""
    if not arg:
        return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Uso: /session delete <id>[/]"
    try:
        manager = _session_manager_for(_app_loop)
        deleted = manager.delete_session(arg)
        if deleted:
            return f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Sessão '{arg}' excluída.[/]"
        return (
            f"[{UIStyles.WARNING}]{UIIcons.WARNING} Sessão '{arg}' não encontrada.[/]"
        )
    except Exception as e:
        logger.error("Error deleting session: %s", e)
        return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Failed to delete session: {e}[/]"


def _workflow_list(wm: Any, console: Console) -> None:
    """List available workflows."""
    if wm is None:
        console.print(f"[{UIStyles.MUTED}]Sistema de workflows não disponível.[/]")
        return
    try:
        workflows = wm.list_workflows()
        if not workflows:
            console.print(
                f"[{UIStyles.INFO}]{UIIcons.INFO} No workflows created yet.[/]"
            )
            console.print(
                f"[{UIStyles.MUTED}]Use /workflow create <nome> para criar um.[/]"
            )
            return
        from rich.table import Table

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Nome", style=UIStyles.ACCENT)
        table.add_column("Passos", style=UIStyles.MUTED, width=8)
        table.add_column("Descrição", style=UIStyles.BODY)
        for wf in workflows:
            table.add_row(
                getattr(wf, "name", str(wf)),
                str(len(getattr(wf, "steps", []))),
                getattr(wf, "description", "")[:60],
            )
        console.print(
            Panel(
                table,
                title=f"[{UIStyles.TITLE}]{UIIcons.AGENT} Workflows[/]",
                border_style=UIStyles.BORDER_PRIMARY,
            )
        )
    except Exception as e:
        logger.warning(f"Error listing workflows: {e}")
        console.print(f"[{UIStyles.ERROR}]Error listing workflows: {e}[/]")


def handle_workflow(args: str) -> Optional[str]:
    """Manage workflows using UserWorkflowManager (create/run/list/info)."""
    console = Console()

    if not args:
        console.print(
            Panel(
                """[bold]Uso:[/bold] /workflow <comando> [args]

[bold]Comandos:[/bold]
  [cyan]list[/]           - Listar workflows disponíveis
  [cyan]run <nome>[/]     - Executar um workflow
  [cyan]info <nome>[/]    - Detalhes do workflow
  [cyan]create <nome>[/]  - Criar novo workflow interativamente""",
                title=f"[{UIStyles.TITLE}]{UIIcons.WORKFLOW} Gestão de Workflow[/]",  # type: ignore[attr-defined]
                border_style=UIStyles.BORDER_SECONDARY,
            )
        )
        return None

    parts = args.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else None

    try:
        from aura_cli.core.workflows.user_workflow import UserWorkflowManager

        wm: Any = UserWorkflowManager(
            tool_executor=_create_workflow_tool_executor(console)
        )
    except Exception as e:
        logger.warning(f"UserWorkflowManager indisponível: {e}")
        wm = None

    if cmd == "list":
        _workflow_list(wm, console)
        return None

    if cmd == "run":
        if not arg:
            return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Erro: nome do workflow obrigatório.[/]"
        if wm is None:
            return f"[{UIStyles.ERROR}]Sistema de workflows não disponível.[/]"
        try:
            result = wm.execute_workflow(arg)
            status = (
                result.get("status", "unknown")
                if isinstance(result, dict)
                else str(result)
            )
            return f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Workflow '{arg}' completed: {status}[/]"
        except Exception as e:
            logger.warning(f"Error running workflow '{arg}': {e}")
            return f"[{UIStyles.ERROR}]Error running workflow '{arg}': {e}[/]"

    if cmd == "info":
        if not arg:
            return f"[{UIStyles.ERROR}]Erro: nome do workflow obrigatório.[/]"
        if wm is None:
            return f"[{UIStyles.ERROR}]Sistema de workflows não disponível.[/]"
        try:
            wf = wm.get_workflow(arg)
            if not wf:
                return f"[{UIStyles.ERROR}]Workflow '{arg}' not found.[/]"
            lines = [
                f"[bold]Nome:[/] {getattr(wf, 'name', arg)}",
                f"[bold]Descrição:[/] {getattr(wf, 'description', '')}",
                f"[bold]Passos:[/] {len(getattr(wf, 'steps', []))}",
            ]
            console.print(
                Panel(
                    "\n".join(lines),
                    title=f"[{UIStyles.TITLE}]Workflow: {arg}[/]",
                    border_style=UIStyles.BORDER_PRIMARY,
                )
            )
        except Exception as e:
            logger.warning(f"Error fetching workflow info '{arg}': {e}")
            return f"[{UIStyles.ERROR}]Erro: {e}[/]"
        return None

    if cmd == "create":
        if not arg:
            return f"[{UIStyles.ERROR}]Erro: nome do workflow obrigatório.[/]"
        console.print(
            f"[{UIStyles.INFO}]Criação interativa de workflows via /agi em breve.[/]"
        )
        console.print(
            f"[{UIStyles.MUTED}]Por enquanto, crie arquivos YAML em .aura/workflows/[/]"
        )
        return None

    return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Comando desconhecido: {cmd}[/]"


def _get_cache_stats_aggregate() -> list:
    """Aggregate stats from persistent, analysis, embedding and tool result caches. Returns list of (name, stats_dict)."""
    result = []
    try:
        from aura_cli.core.cache_advanced import get_persistent_cache

        result.append(("Persistente (global)", get_persistent_cache().get_stats()))
    except Exception as e:
        logger.debug("Cache persistente não disponível: %s", e)
    try:
        from aura_cli.core.cache_advanced import get_analysis_cache

        result.append(("Análise (código)", get_analysis_cache().get_stats()))
    except Exception as e:
        logger.debug("Cache de análise não disponível: %s", e)
    try:
        from aura_cli.core.cache_advanced import get_embedding_cache

        result.append(("Embeddings", get_embedding_cache().get_stats()))
    except Exception as e:
        logger.debug("Cache de embeddings não disponível: %s", e)
    try:
        from aura_cli.core.service_registry import get_service_registry

        result.append(
            (
                "Resultados de ferramentas",
                get_service_registry().get_tool_result_cache_stats(),
            )
        )
    except Exception as e:
        logger.debug("Cache de resultados de ferramentas não disponível: %s", e)
    return result


def _cache_stats_display(console: Console) -> None:
    """Print cache stats tables to console."""
    rows = _get_cache_stats_aggregate()
    if not rows:
        console.print(
            Panel(
                "Nenhum cache disponível ou erro ao ler estatísticas.",
                title="Estatísticas do cache",
                border_style=UIStyles.BORDER_ACCENT,
            )
        )
        return
    for name, st in rows:
        entries = st.get("entries", st.get("total_embeddings", st.get("size", 0)))
        size_mb = st.get("size_mb", 0) or st.get("size_bytes", 0) / (1024 * 1024)
        hit_rate = st.get("hit_rate", "-")
        if isinstance(hit_rate, (int, float)):
            hit_rate = f"{hit_rate}%"
        table = Table(
            title=f"Cache: {name}", show_header=True, header_style="bold cyan", box=None
        )
        table.add_column("Métrica", style="dim")
        table.add_column("Valor", style="green")
        table.add_row("Entradas", str(entries))
        table.add_row(
            "Tamanho (MB)",
            f"{size_mb:.2f}" if isinstance(size_mb, (int, float)) else str(size_mb),
        )
        if "hit_rate" in st:
            table.add_row("Hit rate", str(hit_rate))
        console.print(table)
    try:
        from aura_cli.core.agents.agent_metrics import get_metrics_collector

        collector = get_metrics_collector()
        summary = collector.get_summary() if hasattr(collector, "get_summary") else {}
        if summary:
            t = Table(
                title="Métricas de Agentes",
                show_header=True,
                header_style="bold cyan",
                box=None,
            )
            t.add_column("Métrica", style="dim")
            t.add_column("Valor", style="green")
            for k, v in summary.items():
                t.add_row(str(k), str(v))
            console.print(t)
    except Exception as _e:
        logger.debug(f"Agent execution metrics unavailable: {_e}")


def _cache_clear() -> str:
    """Clear all cache backends. Returns result message."""
    cleared = []
    _ops = [
        (
            "Persistente",
            lambda: (lambda c: (c.clear(), f"Persistente: {c.clear()} entradas"))(
                __import__(
                    "aura_cli.core.cache_advanced", fromlist=["get_persistent_cache"]
                ).get_persistent_cache()
            ),
        ),
    ]
    try:
        from aura_cli.core.cache_advanced import get_persistent_cache

        n = get_persistent_cache().clear()
        cleared.append(f"Persistente: {n} entradas")
    except Exception as e:
        logger.debug("Clear persistente: %s", e)
    try:
        from aura_cli.core.cache_advanced import get_analysis_cache

        n = get_analysis_cache().cache.clear()
        cleared.append(f"Análise: {n} entradas")
    except Exception as e:
        logger.debug("Clear análise: %s", e)
    try:
        from aura_cli.core.cache_advanced import get_embedding_cache

        n = get_embedding_cache().clear()
        cleared.append(f"Embeddings: {n} entradas")
    except Exception as e:
        logger.debug("Clear embeddings: %s", e)
    try:
        from aura_cli.core.service_registry import get_service_registry

        reg = get_service_registry()
        n = reg.get_tool_result_cache_stats().get("size", 0)
        reg.clear_cache()  # type: ignore[attr-defined]
        cleared.append(f"Resultados de ferramentas: {n} entradas")
    except Exception as e:
        logger.debug("Clear resultados de ferramentas: %s", e)
    if not cleared:
        return f"[{UIStyles.WARNING}]{UIIcons.WARNING} Nenhum cache pôde ser limpo.[/{UIStyles.WARNING}]"
    return f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Cache limpo: {', '.join(cleared)}.[/{UIStyles.SUCCESS}]"


def handle_cache(args: str) -> Optional[str]:
    """Manage cache (stats/clear). Uses real cache backends when available."""
    console = Console()

    if not args:
        console.print(
            Panel(
                """[bold]Uso:[/bold] /cache <comando>

[bold]Comandos:[/bold]
  [cyan]stats[/]   - Estatísticas do cache
  [cyan]clear[/]   - Limpar todo o cache""",
                title=f"[{UIStyles.TITLE}]{UIIcons.AURA} Gestão de Cache[/]",
                border_style=UIStyles.BORDER_ACCENT,
            )
        )
        return None

    cmd = args.lower().strip()
    if cmd == "stats":
        _cache_stats_display(console)
        return None
    if cmd == "clear":
        return _cache_clear()
    return f"[{UIStyles.ERROR}]{UIIcons.ERROR} Comando desconhecido: {cmd}[/]"
