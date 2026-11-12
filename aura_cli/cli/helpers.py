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

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.key_bindings import create_key_bindings
from aura_cli.cli.ui.manager import UIManager
from aura_cli.core.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)
console = get_console()


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

    ANIMATIONS_AVAILABLE = (
        False  # animations.py removed (was an orphan with no callers)
    )
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
                task1 = progress.add_task("[dim]Initializing core...", total=100)
                task2 = progress.add_task(
                    "[dim]Loading neural engines...", total=100, visible=False
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
        f"[italic dim]AI Code Assistant[/]\n\n"
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
            "content": """You are Aura, a senior software engineer with direct access to the user's environment. You act, you don't simulate.

**IDENTITY**
You are a development partner — direct, technical and proactive. When the user asks for something, you do it. You don't describe what you're going to do, don't present option menus, don't simulate results. You simply act and report what you found naturally.

**BEHAVIOUR RULES**
- **Act first, explain after** — use the tool, then comment on the result in natural language. Never describe the tool you're going to use before using it.
- **NEVER INVENT DATA** — if a tool returned X, report X. Don't extrapolate, don't fill in with examples, don't add items that weren't in the real result. If the result was truncated, say so.
- **Never simulate** — if you didn't run a tool, don't invent the result. If you don't have access to something, say so clearly.
- **No menus or numbered options** — respond directly to what was asked. If you need more information, ask one simple, direct question.
- **Colleague tone** — concise, technical when needed, no excessive formality.
- **Don't mention tool names in the response** — the user doesn't need to know you called `list_directory`. Just say what you found.

**AUTOMATIC PROJECT ONBOARDING**
When the user presents a directory or asks to explore the project, execute IMMEDIATELY and in sequence, without asking permission:
1. `scan_project(path=".")` — quick overview (files, languages, size)
2. `read_file("README.md")` — or the main documentation file found
3. `git_status()` — current repository state
Then respond with a direct summary: what the project is, stack, current state. No menus, no questions.

**CODE EDITING — MANDATORY FLOW**
For any modification to an existing file:
1. `read_file(path)` — reads the full file first
2. Apply the change to the read content, preserving existing style and conventions
3. `write_file(path, new_content)` — writes the full modified file
Never use `run_shell_command` to edit files. Never write without reading first. Don't add comments like "Updated by Aura" or unnecessary markers.

**AVAILABLE TOOLS (use silently)**

*Exploration:*
- `list_directory`, `tree_view`, `view_subdirectory` — navigate directory structure
- `read_file`, `write_file`, `edit_file` — read/write/edit files (edit_file for targeted changes without rewriting everything)
- `find_in_files`, `advanced_grep_search`, `glob_search`, `codebase_search` — search in code
- `view_repo_map` — full repository map

*Code analysis:*
- `scan_project` — quick project overview (use during onboarding)
- `analyze_code` — detailed static analysis of a file
- `analyze_project_structure` — detects languages, frameworks, architecture
- `analyze_project_quality` — complexity, duplication, quality metrics
- `analyze_project_security` — vulnerabilities and security issues
- `summarize_code` — summarises what a file/module does
- `validate_syntax` — validates syntax before saving
- `classify_code` — classifies type and complexity
- `find_duplicate_code` — finds duplicated code
- `sanitize_code` — lints and formats via Forge (Nim)

*Dependencies and impact:*
- `analyze_dependencies` — project import graph
- `dep_find_dependencies` — dependencies of a specific module
- `dep_get_impact_analysis` — impact of changing a module (what will break)

*Git:*
- `git_status`, `git_diff`, `git_diff_context`, `git_log`, `git_branch`, `git_commit`
- `suggest_commit_message` — generates commit message based on diff

*Tests:*
- `generate_tests_ml` — automatically generates tests for a file
- `run_tests_advanced` — runs tests with detailed report

*Persistent memory:*
- `notebook_write` — saves decisions, plans, analysis summaries
- `notebook_read`, `notebook_search` — retrieves previous memories

*DevOps:*
- `docker_ps`, `docker_logs` — containers
- `system_resources` — CPU/RAM/disk
- `run_shell_command` — any shell command

*Refactoring:*
- `plan_refactoring` — plans refactoring with impact analysis
- `check_file_changes` — detects modified files (Sentinel)

*Web and delegation:*
- `web_search` — web search
- `delegate_to_agi` — complex multi-step tasks (pass a self-contained objective)
- `delegate_to_ops` — DevOps/Git/Docker in batch

**TOOL USAGE RULES**
- **Commit**: NEVER run `git_commit` directly. Always: (1) `git_diff_context` to see all changes, (2) `suggest_commit_message` to generate the message, (3) `git_commit` with the generated message.
- **Format/lint file**: use `format_file(path)` — formats and lints a file by path. Use for any request to "format", "lint", "organise" or "clean up" a file.
- **Change impact**: use `dep_get_impact_analysis`, not `analyze_dependencies`.
- **Code quality**: use `analyze_project_quality`.
- **Code search**: prefer `advanced_grep_search` or `codebase_search` for complex searches.
- **Targeted change**: use `edit_file` instead of full read+write when possible.

**WHEN TO DELEGATE**
- `delegate_to_agi` — large refactorings, complex implementations, systematic analyses. Pass a self-contained and complete objective (the AGI has no access to conversation history).
- `delegate_to_ops` — Git, Docker, deploy, infrastructure operations.

**REAL LIMITATIONS**
- **File not found** — if `read_file` returns "not found", immediately run `run_shell_command("find . -name '<file>' 2>/dev/null")` to locate it. Only report to the user if find also finds nothing.
- **Ambiguous task** — if the request is vague (e.g. "improve the code"), ask which specific file or module before acting.""",
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
        "📡 SYSTEM NOTE: Initial tool status for this session:"
    ]

    def fmt_status(label: str, key: str) -> None:
        """Format a status string for display."""
        status = health.get(key, "unknown")
        if status == "ok" or status == "importable":
            lines.append(f"- {label}: available ({status})")
        elif status == "missing":
            lines.append(f"- {label}: binary missing ({status})")
        elif isinstance(status, str) and status.startswith("error:"):
            reason = status.split("error:", 1)[-1].strip() or "erro ao verificar estado"
            lines.append(f"- {label}: unavailable — {reason}")
        elif status == "error":
            lines.append(f"- {label}: unavailable (error checking status)")
        else:
            lines.append(f"- {label}: {status}")

    fmt_status("Imagination (scan_project)", "nim_imagination")
    fmt_status("Monitor (browse_content)", "nim_monitor")
    fmt_status("Nexus (analyze_dependencies)", "nim_nexus")
    fmt_status("Sentinel (check_file_changes)", "nim_sentinel")
    fmt_status("Forge (sanitize_code)", "nim_forge")
    fmt_status("web_search", "web_search")

    lines.append(
        "\nIf a tool reports a runtime error, "
        "explain the error to the user and adapt the strategy instead of retrying."
    )
    lines.append(
        "\n▪ **Quick tip:** To get project information quickly, use:"
    )
    lines.append('- `list_directory(".")` - Lists the current directory in a formatted view')
    lines.append('- `tree_view(".")` - Visualizes the directory structure as a tree')
    lines.append(
        "- Nim tools (if available): `scan_project()`, `analyze_dependencies()`, etc."
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
    summary_lines.append("🧭 Initial project profile (automatic scan):")
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
            summary="Initial project profile (automatic scan)",
        )
        page_path = write_result.get("page_path") if write_result.get("ok") else None
    except Exception as _e:
        logger.debug("Failed to persist project profile to notebook: %s", _e)
        page_path = None

    if page_path:
        summary_lines.append(f"- Perfil completo salvo no Notebook: `{page_path}`")
    else:
        summary_lines.append(
            "- Profile could not be saved to Notebook (write error)."
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
        message = "Type a question or /help for commands and /keyboard for shortcuts."
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
        logger.warning("Intervention request is not a dict; ignored")
        return

    try:
        from aura_cli.cli.ui.components.input.human_confirmation_dialog import (
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


def _emit_activity_heartbeat(ui: Optional[UIManager]) -> None:
    """Print elapsed-time lines for long-running tools, if the UI tracks any.

    Runs before the empty-queue early return: a tool that is silently running emits
    no events, so the queue is exactly the case where the heartbeat matters.
    """
    renderer = getattr(ui, "worker_activity", None)
    if renderer is None:
        return
    try:
        renderer.heartbeat()
    except Exception as error:  # a heartbeat must never break the refresh
        logger.debug("Activity heartbeat skipped: %s", error)


def _route_status_messages(
    display_list: List[Any], ui: Optional[UIManager]
) -> tuple[List[Any], List[Any]]:
    """Split queued messages into Rich renderables and worker-feed text.

    Structured lifecycle events (tool/task) are rendered in place as a one-line
    activity trail via ``ui.worker_activity`` and therefore appear in neither list.
    Chat renderables (non-string content) go to ``renderables``; everything else,
    including legacy ``[Aura AGI]`` text, goes to the worker feed.
    """
    renderables: List[Any] = []
    feed_messages: List[Any] = []
    activity_renderer = getattr(ui, "worker_activity", None)

    for msg in display_list:
        if isinstance(msg, dict) and msg.get("type") == "chat_message":
            content = msg.get("content")
            if content is not None and not isinstance(content, str):
                renderables.append(content)
            else:
                feed_messages.append(msg)
            continue
        if activity_renderer is not None and activity_renderer.render_event(msg):
            continue
        feed_messages.append(msg)

    return renderables, feed_messages


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
    _emit_activity_heartbeat(ui)
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
    renderables, feed_messages = _route_status_messages(display_list, ui)

    for renderable in renderables:
        target.print(renderable)

    try:
        from aura_cli.cli.ui.components.agent.worker_feed import (
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
        objective = "Explore the current directory, list the main files, analyze the project structure and provide a summary of what you found."
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
            "Multi-line mode: type three quotes (''') on a new line to send."
        )
        if ui is not None:
            ui.display_info(message)
        else:
            from aura_cli.cli.ui.display_facade import display_info

            display_info(message)
    except Exception:
        console.print(
            f"[{UIStyles.WARNING}]{UIIcons.INFO} Multi-line input mode activated. Type three quotes (''') on a new line to send.[/{UIStyles.WARNING}]"
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
                ui.display_warning("No input provided. Try again.")
            else:
                from aura_cli.cli.ui.display_facade import display_warning

                display_warning("No input provided. Try again.")
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
            from aura_cli.cli.ui.components.display.collapsed_text import (
                CollapsedTextDisplay,
            )

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
