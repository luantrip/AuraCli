"""Shared adapters used by CLI composition, commands and worker feedback.

The module owns prompt-toolkit input, runtime notes, API-key access and status
translation specific to the Rich CLI. Toolkit-neutral decisions belong in
Application; imports that would create composition cycles are resolved lazily.
"""

from __future__ import annotations

from pathlib import Path
import queue
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.key_bindings import create_key_bindings
from aura_cli.cli.ui.manager import UIManager
from aura_cli.core.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)
console = Console()


def display_aura_splash_screen(ui: Optional[UIManager] = None) -> None:
    """Display welcome splash screen with 'Wow' factor animations.

    Shows the Aura CLI ASCII logo with fade-in effects, simulated system checks,
    and a clean professional footer.
    """
    from rich.align import Align
    from rich.padding import Padding
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    try:
        from aura_cli.cli.main import __version__
    except ImportError:
        __version__ = "0.1.0"

    ANIMATIONS_AVAILABLE = False  # animations.py removed (was an orphan with no callers)
    if not hasattr(UIStyles, "_styles_initialized") or not UIStyles._styles_initialized:
        UIStyles._init_styles()

    logo_text = (
        "░█████╗░██╗░░░██╗██████╗░░█████╗░\n"
        "██╔══██╗██║░░░██║██╔══██╗██╔══██╗\n"
        "███████║██║░░░██║██████╔╝███████║\n"
        "██╔══██║██║░░░██║██╔══██╗██╔══██║\n"
        "██║░░██║╚██████╔╝██║░░██║██║░░██║\n"
        "╚═╝░░╚═╝░╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝"
    )
    title_style = getattr(UIStyles, "PRIMARY", "cyan")
    target = ui if ui is not None else console
    target.print(f"[{title_style}]{logo_text}[/]", justify="center")
    target.print()
    from aura_cli.core.config import config_manager

    skip_animation = config_manager.get("skip_splash", False)

    if ANIMATIONS_AVAILABLE and not skip_animation:
        try:
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=20),
                console=console,
                transient=True,
            ) as progress:
                task1 = progress.add_task("[dim]Inicializando núcleo...", total=100)
                task2 = progress.add_task(
                    "[dim]Carregando motores neurais...", total=100, visible=False
                )

                while not progress.finished:
                    progress.update(task1, advance=5)
                    if progress.tasks[0].completed > 50:
                        progress.update(task2, visible=True, advance=8)
                    time.sleep(0.01)  # Fast boot
        except Exception as _e:
            logger.debug(f"Ignorado: {_e}")
    welcome_content = Align.center(
        f"[bold white]Aura CLI[/] [dim]v{__version__}[/]\n"
        f"[italic dim]Assistente de Código AI[/]\n\n"
        f"[dim]▪ Digite [bold]/help[/] para comandos ou [bold]/agi[/] para delegar tarefas.[/]"
    )
    welcome_panel = Padding(welcome_content, (1, 2))
    target.print(welcome_panel)
    target.print()


def initialize_conversation_history() -> List[Dict[str, str]]:
    """Initialize conversation history with default system message.

    Creates the initial conversation history structure used by the LLM
    throughout the session. The system message defines the assistant's
    behavior, capabilities, and rules.

    Returns:
        List containing a single system message in chat format:
        [{"role": "system", "content": "..."}]

    Note:
        The system message includes:
            - Assistant description (Aura Dev)
            - Available tools list (79 total)
            - Mandatory behavior rules
            - Usage examples
            - Special modes information (/agi, /ops)

        This message is always preserved at the beginning of history,
        even when conversation is truncated for token limits.
    """
    return [
        {
            "role": "system",
            "content": """Você é a Aura, uma engenheira de software sênior com acesso direto ao ambiente do usuário. Você age, não simula.

**IDENTIDADE**
Você é uma parceira de desenvolvimento — direta, técnica e proativa. Quando o usuário pede algo, você faz. Não descreve o que vai fazer, não apresenta menus de opções, não simula resultados. Simplesmente age e reporta o que encontrou de forma natural.

**REGRAS DE COMPORTAMENTO**
- **Aja primeiro, explique depois** — use a ferramenta, depois comente o resultado em linguagem natural. Nunca descreva a ferramenta que vai usar antes de usá-la.
- **NUNCA INVENTE DADOS** — se uma ferramenta retornou X, reporte X. Não extrapole, não complete com exemplos, não adicione itens que não estavam no resultado real. Se o resultado foi truncado, diga isso.
- **Nunca simule** — se não executou uma ferramenta, não invente o resultado. Se não tem acesso a algo, diga claramente.
- **Sem menus nem opções numeradas** — responda diretamente ao que foi pedido. Se precisar de mais informação, faça uma pergunta simples e direta.
- **Tom de colega de trabalho** — conciso, técnico quando necessário, sem formalidades excessivas.
- **Não mencione nomes de ferramentas na resposta** — o usuário não precisa saber que você chamou `list_directory`. Apenas diga o que encontrou.

**ONBOARDING AUTOMÁTICO DE PROJETO**
Quando o usuário apresentar um diretório ou pedir para conhecer/explorar o projeto, execute IMEDIATAMENTE e em sequência, sem pedir permissão:
1. `scan_project(path=".")` — visão geral rápida (arquivos, linguagens, tamanho)
2. `read_file("README.md")` — ou o arquivo de documentação principal encontrado
3. `git_status()` — estado atual do repositório
Depois responda com um resumo direto: o que é o projeto, stack, estado atual. Sem menus, sem perguntas.

**EDIÇÃO DE CÓDIGO — FLUXO OBRIGATÓRIO**
Para qualquer modificação em arquivo existente:
1. `read_file(path)` — lê o arquivo completo primeiro
2. Aplica a mudança no conteúdo lido, mantendo o estilo e convenções existentes
3. `write_file(path, novo_conteúdo)` — escreve o arquivo completo modificado
Nunca use `run_shell_command` para editar arquivos. Nunca escreva sem ler antes. Não adicione comentários como "Updated by Aura" ou marcações desnecessárias.

**FERRAMENTAS DISPONÍVEIS (use silenciosamente)**

*Exploração:*
- `list_directory`, `tree_view`, `view_subdirectory` — navega estrutura de diretórios
- `read_file`, `write_file`, `edit_file` — lê/escreve/edita arquivos (edit_file para mudanças pontuais sem reescrever tudo)
- `find_in_files`, `advanced_grep_search`, `glob_search`, `codebase_search` — busca em código
- `view_repo_map` — mapa completo do repositório

*Análise de código:*
- `scan_project` — visão geral rápida do projeto (use no onboarding)
- `analyze_code` — análise estática detalhada de um arquivo
- `analyze_project_structure` — detecta linguagens, frameworks, arquitetura
- `analyze_project_quality` — complexidade, duplicação, métricas de qualidade
- `analyze_project_security` — vulnerabilidades e problemas de segurança
- `summarize_code` — resume o que um arquivo/módulo faz
- `validate_syntax` — valida sintaxe antes de salvar
- `classify_code` — classifica tipo e complexidade
- `find_duplicate_code` — encontra código duplicado
- `sanitize_code` — linta e formata via Forge (Nim)

*Dependências e impacto:*
- `analyze_dependencies` — grafo de imports do projeto
- `dep_find_dependencies` — dependências de um módulo específico
- `dep_get_impact_analysis` — impacto de mudar um módulo (o que vai quebrar)

*Git:*
- `git_status`, `git_diff`, `git_diff_context`, `git_log`, `git_branch`, `git_commit`
- `suggest_commit_message` — gera mensagem de commit baseada no diff

*Testes:*
- `generate_tests_ml` — gera testes automaticamente para um arquivo
- `run_tests_advanced` — roda testes com relatório detalhado

*Memória persistente:*
- `notebook_write` — salva decisões, planos, resumos de análises
- `notebook_read`, `notebook_search` — recupera memórias anteriores

*DevOps:*
- `docker_ps`, `docker_logs` — containers
- `system_resources` — CPU/RAM/disco
- `run_shell_command` — qualquer comando shell

*Refatoração:*
- `plan_refactoring` — planeja refatoração com análise de impacto
- `check_file_changes` — detecta arquivos modificados (Sentinel)

*Web e delegação:*
- `web_search` — busca na web
- `delegate_to_agi` — tarefas complexas multi-etapa (passe objetivo autocontido)
- `delegate_to_ops` — DevOps/Git/Docker em lote

**REGRAS DE USO DE FERRAMENTAS**
- **Commit**: NUNCA execute `git_commit` diretamente. Sempre: (1) `git_diff_context` para ver todas as mudanças, (2) `suggest_commit_message` para gerar a mensagem, (3) `git_commit` com a mensagem gerada.
- **Formatar/lintar arquivo**: use `format_file(path)` — formata e linta um arquivo pelo caminho. Use para qualquer pedido de "formatar", "lintar", "organizar" ou "limpar" um arquivo.
- **Impacto de mudança**: use `dep_get_impact_analysis`, não `analyze_dependencies`.
- **Qualidade do código**: use `analyze_project_quality`.
- **Busca em código**: prefira `advanced_grep_search` ou `codebase_search` para buscas complexas.
- **Mudança pontual**: use `edit_file` em vez de read+write completo quando possível.

**QUANDO DELEGAR**
- `delegate_to_agi` — refatorações grandes, implementações complexas, análises sistemáticas. Passe um objetivo autocontido e completo (o AGI não tem acesso ao histórico da conversa).
- `delegate_to_ops` — operações Git, Docker, deploy, infraestrutura.

**LIMITAÇÕES REAIS**
- **Arquivo não encontrado** — se `read_file` retornar erro "not found", execute imediatamente `run_shell_command("find . -name '<arquivo>' 2>/dev/null")` para localizar. Só reporte ao usuário se o find também não encontrar nada.
- **Tarefa ambígua** — se o pedido for vago (ex: "melhora o código"), pergunte qual arquivo ou módulo específico antes de agir.""",
        }
    ]


def build_runtime_system_note() -> Dict[str, str]:
    """
    Build a lightweight runtime system note with tool health information.

    This is injected as a second system message at session start so that
    the LLM knows which high-level engines are available in this process.
    It avoids heavy network or filesystem work (no full scans here).

    Also includes quick tips on how to get project information.
    """
    health: Dict[str, str] = {}

    try:
        from aura_cli.core.nim_runtime import resolve_nim_binary

        project_root = Path(__file__).resolve().parent.parent.parent
        bin_dir = project_root / "bin"
        nim_checks = [
            ("nim_imagination", "imagination", bin_dir / "imagination"),
            ("nim_monitor", "aura-monitor", bin_dir / "aura-monitor"),
            ("nim_nexus", "nexus", bin_dir / "nexus"),
            ("nim_sentinel", "sentinel", bin_dir / "sentinel"),
            ("nim_forge", "forge", bin_dir / "forge"),
        ]
        for key, binary_name, project_bin in nim_checks:
            try:
                path = resolve_nim_binary(binary_name, extra_candidates=[project_bin])
                health[key] = "ok" if path else "missing"
            except Exception as e:
                health[key] = f"error: {e!s}"
    except Exception as _e:
        health["nim_engines"] = "unknown"
        logger.debug("Nim engine health check failed: %s", _e)
    try:
        health["web_search"] = "importable"
    except Exception as _e:
        logger.debug("Web search health check failed: %s", _e)
        health["web_search"] = "missing"
    lines: List[str] = [
        "📡 NOTA DE SISTEMA: Estado inicial das ferramentas nesta sessão:"
    ]

    def fmt_status(label: str, key: str) -> None:
        """Format a status string for display."""
        status = health.get(key, "unknown")
        if status == "ok" or status == "importable":
            lines.append(f"- {label}: disponível ({status})")
        elif status == "missing":
            lines.append(f"- {label}: binário ausente ({status})")
        elif isinstance(status, str) and status.startswith("error:"):
            reason = status.split("error:", 1)[-1].strip() or "erro ao verificar estado"
            lines.append(f"- {label}: indisponível — {reason}")
        elif status == "error":
            lines.append(f"- {label}: indisponível (erro ao verificar estado)")
        else:
            lines.append(f"- {label}: {status}")

    fmt_status("Imagination (scan_project)", "nim_imagination")
    fmt_status("Monitor (browse_content)", "nim_monitor")
    fmt_status("Nexus (analyze_dependencies)", "nim_nexus")
    fmt_status("Sentinel (check_file_changes)", "nim_sentinel")
    fmt_status("Forge (sanitize_code)", "nim_forge")
    fmt_status("web_search", "web_search")

    lines.append(
        "\nSe uma ferramenta reportar erro em tempo de execução, "
        "explique o erro ao usuário e adapte a estratégia em vez de insistir."
    )
    lines.append(
        "\n▪ **Dica rápida:** Para obter informações do projeto rapidamente, use:"
    )
    lines.append('- `list_directory(".")` - Lista o diretório atual de forma formatada')
    lines.append('- `tree_view(".")` - Visualiza estrutura de diretórios em árvore')
    lines.append(
        "- Ferramentas Nim (se disponíveis): `scan_project()`, `analyze_dependencies()`, etc."
    )

    return {
        "role": "system",
        "content": "\n".join(lines),
    }


def build_initial_project_profile(project_root: Path) -> Optional[Dict[str, str]]:
    """
    Run a light-weight initial project scan and save a profile to the Notebook.

    This is intended to be called once per interactive session to give
    the agent quick awareness of the current repository without flooding the user with logs. If anything fails, the function fails silently.
    """
    try:
        from aura_cli.core.tools import nim_integration, project_analyzer
    except Exception as _e:
        logger.debug("Project tools unavailable for initial scan: %s", _e)
        return None

    root_str = str(project_root)

    scan_result: Dict[str, Any] = {}
    structure_result: Dict[str, Any] = {}

    try:
        structure_result = project_analyzer.analyze_project_structure(root_str)
    except Exception as _e:
        logger.debug("Project structure analysis failed: %s", _e)
        structure_result = {"error": "analyze_project_structure_failed"}
    summary_lines: List[str] = []
    summary_lines.append("🧭 Perfil inicial do projeto (scan automático):")
    summary_lines.append(f"- Raiz do projeto: `{root_str}`")

    if isinstance(structure_result, dict) and "error" not in structure_result:
        main_lang = structure_result.get("main_language") or structure_result.get(
            "language"
        )
        if main_lang:
            summary_lines.append(f"- Linguagem principal detectada: {main_lang}")
        fronts = structure_result.get("fronts") or structure_result.get("frontends")
        if fronts and isinstance(fronts, dict):
            active_fronts = [k for k, v in fronts.items() if v]
            if active_fronts:
                summary_lines.append(
                    f"- Frentes detectadas: {', '.join(active_fronts)}"
                )
    else:
        if structure_result.get("error"):
            summary_lines.append(
                f"- analyze_project_structure: falhou ({structure_result.get('error')})"
            )
    page_path: Optional[str] = None
    try:
        profile_payload = {
            "project_root": root_str,
            "scan_result": scan_result,
            "structure_result": structure_result,
        }
        profile_text = (
            "Perfil inicial do projeto gerado automaticamente pela Aura.\n\n"
            f"Raiz: {root_str}\n\n"
            "=== Resultado Imagination (scan_project) ===\n"
            f"{profile_payload['scan_result']}\n\n"
            "=== Resultado analyze_project_structure ===\n"
            f"{profile_payload['structure_result']}\n"
        )
        write_result = nim_integration.notebook_write(
            content=profile_text,
            summary="Perfil inicial do projeto (scan automático)",
        )
        page_path = write_result.get("page_path") if write_result.get("ok") else None
    except Exception as _e:
        logger.debug("Failed to persist project profile to notebook: %s", _e)
        page_path = None

    if page_path:
        summary_lines.append(f"- Perfil completo salvo no Notebook: `{page_path}`")
    else:
        summary_lines.append(
            "- Perfil não pôde ser salvo no Notebook (erro ao escrever)."
        )

    return {
        "role": "system",
        "content": "\n".join(summary_lines),
    }


def setup_prompt_session() -> PromptSession:
    """Configure and return interactive prompt session with persistent history.

    Initializes a PromptSession from prompt_toolkit with:
        - Persistent history file (~/.aura/history)
        - Custom key bindings for special features
        - Style and behavior configurations

    Returns:
        Configured PromptSession ready for use. The session maintains history
        across Aura CLI executions, allowing navigation with arrows and
        command history search.

    Note:
        History is stored in ~/.aura/history and shared between all Aura CLI
        sessions. Custom key bindings are created by create_key_bindings()
        from ui.key_bindings module.
    """
    return PromptSession(
        history=FileHistory(".aura_history"), key_bindings=create_key_bindings()
    )


def show_onboarding_hint_if_first_run(ui: Optional[UIManager] = None) -> None:
    """Display a one-time onboarding hint on first CLI run."""
    from aura_cli.core.paths import get_aura_home

    aura_dir = get_aura_home()
    seen_file = aura_dir / ".onboarding_seen"
    if seen_file.exists():
        return
    try:
        aura_dir.mkdir(parents=True, exist_ok=True)
        seen_file.touch()
    except OSError:
        return
    try:
        message = "Digite uma pergunta ou /help para comandos e /keyboard para atalhos."
        if ui is not None:
            ui.display_info(message)
        else:
            from aura_cli.cli.ui.display_facade import display_info

            display_info(message)
    except Exception as _e:
        logger.debug(f"Ignorado: {_e}")


def _handle_intervention_request(request_dict: Dict[str, Any]) -> None:
    """Process one human_intervention_request from the queue: show dialog and deliver response.

    Called when status_queue yields an item with type \"human_intervention_request\".
    Looks up the adapter by task_id and calls receive_response so the worker can unblock.
    """
    if not isinstance(request_dict, dict):
        logger.warning("Intervention request não é um dicionário; ignorado")
        return

    try:
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanConfirmationDialog,
        )
        from aura_cli.core.events.human_intervention_events import (
            InterventionRequest,
            InterventionRequestType,
        )
        from aura_cli.core.tools.human_intervention_adapter import (
            get_intervention_adapter,
        )
    except ImportError as e:
        logger.debug("Intervention handler skipped (import): %s", e)
        return

    if request_dict.get("type") != "human_intervention_request":
        return

    task_id = request_dict.get("task_id")
    request_id = request_dict.get("request_id")
    if not task_id or not request_id:
        logger.warning("Intervention request missing task_id or request_id")
        return

    adapter = get_intervention_adapter(task_id)
    if not adapter:
        logger.warning(
            "No intervention adapter for task_id=%s; user prompt not shown", task_id
        )
        return

    try:
        request = InterventionRequest.from_dict(request_dict)
    except (KeyError, TypeError, ValueError) as e:
        logger.warning("Invalid intervention request dict: %s", e)
        return

    if request.request_type != InterventionRequestType.CONFIRM:
        logger.debug(
            "Non-confirm intervention type %s not handled in UI", request.request_type
        )
        adapter.receive_response(
            {
                "task_id": task_id,
                "request_id": request_id,
                "approved": False,
                "cancelled": True,
                "reason": "unsupported_request_type",
            }
        )
        return

    try:
        dialog = HumanConfirmationDialog()
        result = dialog.prompt_user(request)
    except Exception as e:
        logger.exception("Error showing confirmation dialog: %s", e)
        result = {"approved": False, "cancelled": True, "reason": str(e)}

    response_dict = {
        "task_id": task_id,
        "request_id": request_id,
        "approved": result.get("approved", False),
        "value": result.get("value"),
        "cancelled": result.get("cancelled", False),
        "reason": result.get("reason"),
        "scope": result.get("scope", "once"),
    }
    adapter.receive_response(response_dict)


def handle_status_updates(
    status_queue: queue.Queue[str], ui: Optional[UIManager] = None
) -> None:
    """Display real-time status updates from queue.

    Processes status messages from workers and displays them using
    appropriate formatting. Intervention requests (human_intervention_request)
    are handled separately: show confirmation dialog and deliver response to
    the worker adapter. Other messages go to the status panel or fallback.

    Args:
        status_queue: Queue containing status messages from workers
    """
    if status_queue.empty():
        return

    display_list: List[Any] = []
    while not status_queue.empty():
        try:
            item = status_queue.get_nowait()
        except queue.Empty:
            break
        if isinstance(item, dict) and item.get("type") == "human_intervention_request":
            _handle_intervention_request(item)
        else:
            display_list.append(item)

    if not display_list:
        return

    target = ui if ui is not None else console
    renderables: List[Any] = []
    feed_messages: List[Any] = []

    for msg in display_list:
        if isinstance(msg, dict) and msg.get("type") == "chat_message":
            content = msg.get("content")
            if content is not None and not isinstance(content, str):
                renderables.append(content)
                continue
        feed_messages.append(msg)

    for renderable in renderables:
        target.print(renderable)

    try:
        from aura_cli.cli.ui.components.worker_feed import (
            parse_status_messages,
            render_worker_feeds,
        )

        feeds = parse_status_messages(feed_messages)
        if feeds:
            target.print(render_worker_feeds(feeds))
            return
    except (ImportError, Exception) as _e:
        logger.debug("Worker feed renderer unavailable: %s", _e)

    temp_queue: queue.Queue[Any] = queue.Queue()
    for msg in feed_messages:
        temp_queue.put(msg)

    try:
        from aura_cli.cli.ui.status_panel import create_status_panel

        status_panel = create_status_panel(temp_queue)
    except (ImportError, AttributeError):
        status_panel = None

    if status_panel:
        target.print(status_panel)


def parse_agi_command(command: str) -> Optional[str]:
    """Extract objective from /agi command.

    Parses the /agi command and extracts the objective. If no objective
    is provided, returns a default exploration task. Also detects --validate flag.

    Args:
        command: Full command string (e.g., "/agi create a blog" or "/agi --validate create a blog")

    Returns:
        Extracted objective string, or default exploration task if empty.
        Default task explores current directory and analyzes project structure.

    Example:
        >>> parse_agi_command("/agi create API")
        'create API'
        >>> parse_agi_command("/agi --validate create API")
        'create API'
        >>> parse_agi_command("/agi")
        'Explore the current directory...'
    """
    objective = command[4:].strip()
    # Strip --validate flag (handled separately by parse_agi_flags)
    objective = objective.replace("--validate", "").strip()
    if not objective:
        objective = "Explore o diretório atual, liste os arquivos principais, analise a estrutura do projeto e forneça um resumo do que encontrou."
    return objective


def parse_agi_flags(command: str) -> Dict[str, bool]:
    """Extract flags from /agi command.

    Args:
        command: Full command string (e.g., "/agi --validate create a blog")

    Returns:
        Dictionary of parsed flags.

    Example:
        >>> parse_agi_flags("/agi --validate create API")
        {'validate': True}
        >>> parse_agi_flags("/agi create API")
        {'validate': False}
    """
    args = command[4:].strip()
    return {
        "validate": "--validate" in args,
    }


def parse_ops_command(command: str) -> Tuple[str, str]:
    """Extract mode and task from /ops command.

    Parses the /ops command to extract the operation mode (git, docker, general)
    and the task description. Handles various command formats.

    Args:
        command: Full command string (e.g., "/ops git status", "/ops docker ps")

    Returns:
        Tuple (mode, task) where:
            - mode: 'git', 'docker', or 'general'
            - task: Task description or default infrastructure analysis

    Example:
        >>> parse_ops_command("/ops git status")
        ('git', 'status')
        >>> parse_ops_command("/ops docker ps")
        ('docker', 'ps')
        >>> parse_ops_command("/ops check system")
        ('general', 'check system')
    """
    parts = command[4:].strip().split(maxsplit=1)

    if len(parts) == 0:
        mode = "general"
        task = "Analise o ambiente e me diga o estado atual da infraestrutura."
    elif len(parts) == 1:
        known_modes = ["git", "docker", "general"]
        if parts[0].lower() in known_modes:
            mode = parts[0].lower()
            task = "Analise o ambiente e me diga o estado atual da infraestrutura."
        else:
            mode = "general"
            task = parts[0]
    else:
        known_modes = ["git", "docker", "general"]
        if parts[0].lower() in known_modes:
            mode = parts[0].lower()
            task = parts[1]
        else:
            mode = "general"
            task = command[4:].strip()

    return mode, task


def get_api_keys_dict() -> Dict[str, str]:
    """Expose configured API keys to CLI composition and worker factories."""
    from aura_cli.core.api_keys import get_api_keys_dict as _core_get_api_keys_dict

    return _core_get_api_keys_dict()


def handle_multiline_input(ui: Optional[UIManager] = None) -> Optional[str]:
    """Handle multiline user input.

    Allows users to enter multiple lines of text, terminated by triple
    quotes (\"\"\") on a new line. Useful for long prompts or code blocks.
    Provides visual feedback and handles cancellation gracefully.

    Returns:
        Complete text as string if successful, None if cancelled (ESC/Ctrl+C)

    Note:
        User must type triple quotes (''') on a new line to submit.
        The triple quotes are not included in the returned text.

    Example:
        >>> text = handle_multiline_input()
        ... # User types multiple lines
        ... # User types triple quotes to finish
        >>> print(text)  # Returns all lines except the triple quotes
    """
    try:
        message = (
            "Modo multi-linha: digite três aspas (''') em uma nova linha para enviar."
        )
        if ui is not None:
            ui.display_info(message)
        else:
            from aura_cli.cli.ui.display_facade import display_info

            display_info(message)
    except Exception:
        console.print(
            f"[{UIStyles.WARNING}]{UIIcons.INFO} Modo de entrada multi-linha ativado. Digite três aspas (''') em uma nova linha para enviar.[/{UIStyles.WARNING}]"
        )
    user_lines = []

    while True:
        try:
            line = input("... ")
            if line.strip() == '"""':
                break
            user_lines.append(line)
        except (EOFError, KeyboardInterrupt):
            try:
                if ui is not None:
                    ui.display_warning("Entrada cancelada (ESC/Ctrl+C).")
                else:
                    from aura_cli.cli.ui.display_facade import display_warning

                    display_warning("Entrada cancelada (ESC/Ctrl+C).")
            except Exception:
                console.print(
                    f"[{UIStyles.WARNING}]{UIIcons.CANCEL} Entrada cancelada (ESC/Ctrl+C).[/{UIStyles.WARNING}]"
                )
            return None

    user_input = "\n".join(user_lines)

    if not user_input:
        try:
            if ui is not None:
                ui.display_warning("Nenhuma entrada fornecida. Tente novamente.")
            else:
                from aura_cli.cli.ui.display_facade import display_warning

                display_warning("Nenhuma entrada fornecida. Tente novamente.")
        except Exception:
            console.print(
                f"[{UIStyles.WARNING}]{UIIcons.WARNING} Nenhuma entrada fornecida. Tente novamente.[/{UIStyles.WARNING}]"
            )
        return None

    user_input = user_input.strip()

    # Display collapsed view for large multiline input
    CHAR_THRESHOLD = 500
    LINE_THRESHOLD = 10

    if len(user_input) > CHAR_THRESHOLD or user_input.count("\n") > LINE_THRESHOLD:
        try:
            from aura_cli.cli.ui.components.collapsed_text import CollapsedTextDisplay

            collapsed_display = CollapsedTextDisplay()
            collapsed_view = collapsed_display.render_minimal(
                user_input,
                label="Entrada multilinha",
                for_chat=True,
            )
            target = ui if ui is not None else console
            target.print()
            target.print(collapsed_view)
        except ImportError:
            lines = user_input.splitlines()
            size_kb = len(user_input.encode("utf-8")) / 1024
            target = ui if ui is not None else console
            target.print(
                f"[dim][◇ Entrada multilinha │ {len(lines)} linhas │ {size_kb:.1f} KB][/dim]"
            )

    return user_input
