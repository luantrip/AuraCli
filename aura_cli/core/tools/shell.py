"""Shell command detection and execution utilities.

Identifies when the user wants to run a shell command directly, extracts
and sanitises it, then executes it with a configurable timeout. Bypasses
the LLM for common OS commands, giving a faster and more fluid experience.
All commands run with output/error capture; dangerous patterns are blocked
by shell_policy.
"""

import shlex
import subprocess
from typing import Any, Tuple

_REAL_SUBPROCESS_RUN = subprocess.run

from aura_cli.application.tools.shell_policy import BLOCKED_COMMANDS as BLOCKED_COMMANDS
from aura_cli.application.tools.shell_policy import (
    DANGEROUS_PATTERNS as DANGEROUS_PATTERNS,
)
from aura_cli.application.tools.shell_policy import (
    has_safe_quoting,
    is_command_safe,
    sanitize_command,
)
from aura_cli.core.constants import DEFAULT_SHELL_TIMEOUT, LONG_SHELL_TIMEOUT
from aura_cli.core.stats import get_stats
from aura_cli.core.utils.safe_subprocess import SafeSubprocess, SubprocessResult

SHELL_MAX_OUTPUT_SIZE = 65536


def _sanitize_command(command: str) -> str:
    """Compatibility facade for the Application command policy."""
    return sanitize_command(command)


def _scan_unquoted_chars(command: str) -> bool:
    """Compatibility facade for quote-aware policy validation."""
    return has_safe_quoting(command)


def shell_execution_status() -> tuple[bool, str]:
    """Return whether shell execution is enabled, with a safe reason on failure."""
    try:
        from aura_cli.core.config import get_config_manager

        enabled = get_config_manager().get("enable_shell", True)
    except Exception as error:
        return (
            False,
            "Execução de shell bloqueada: configuração indisponível "
            f"({type(error).__name__}).",
        )

    if enabled is not True:
        return (
            False,
            "Execução de shell desabilitada. Habilite em /settings → "
            "Configurações do sistema e do agente → Permitir exec. shell.",
        )
    return True, ""


def _shell_cwd() -> str:
    """Return the canonical cwd configured for this workspace session."""
    from aura_cli.core.tools.file_system import get_allowed_base_dir

    return str(get_allowed_base_dir())


def _run_supervised(
    command_args: list[str],
    *,
    timeout: int,
    input_data: str | None = None,
    cwd: str | None = None,
) -> SubprocessResult:
    """Run foreground shell work through the single bounded supervisor.

    A patched ``subprocess.run`` is adapted only as a compatibility seam for
    legacy unit tests. Production execution always uses ``SafeSubprocess``.
    """
    if subprocess.run is not _REAL_SUBPROCESS_RUN:
        try:
            completed = subprocess.run(
                command_args,
                cwd=cwd,
                timeout=timeout,
                input=input_data,
                capture_output=True,
                text=True,
                check=False,
            )
            stdout = str(getattr(completed, "stdout", "") or "")
            stderr = str(getattr(completed, "stderr", "") or "")
            return SubprocessResult(
                timeout=False,
                exit_code=int(getattr(completed, "returncode", 0)),
                stdout=stdout[:SHELL_MAX_OUTPUT_SIZE],
                stderr=stderr[:SHELL_MAX_OUTPUT_SIZE],
            )
        except subprocess.TimeoutExpired:
            return SubprocessResult(
                timeout=True,
                exit_code=-1,
                stdout="",
                stderr="Timeout: comando excedeu o tempo limite",
            )
        except FileNotFoundError:
            return SubprocessResult(
                timeout=False,
                exit_code=127,
                stdout="",
                stderr=f"Command not found: {command_args[0]}",
            )
        except PermissionError:
            return SubprocessResult(
                timeout=False,
                exit_code=126,
                stdout="",
                stderr=f"Permission denied: {command_args[0]}",
            )

    return SafeSubprocess(
        timeout_seconds=timeout,
        max_output_size=SHELL_MAX_OUTPUT_SIZE,
    ).run(
        command_args,
        timeout_seconds=timeout,
        cwd=cwd,
        input_data=input_data,
    )


def _is_safe_command(command: str) -> bool:
    """Return True if the command passes safety checks."""
    from aura_cli.core.stats import get_stats

    return is_command_safe(command, autonomous=get_stats().skip_confirmations)


COMMON_SHELL_COMMANDS = {
    "ls",
    "pwd",
    "cd",
    "echo",
    "cat",
    "grep",
    "find",
    "which",
    "whoami",
    "date",
    "cal",
    "df",
    "du",
    "free",
    "top",
    "ps",
    "kill",
    "mkdir",
    "rmdir",
    "rm",
    "cp",
    "mv",
    "touch",
    "chmod",
    "chown",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "diff",
    "man",
    "history",
    "clear",
    "env",
    "export",
    "git",
    "npm",
    "pip",
    "python",
    "python3",
    "node",
    "java",
    "gcc",
}


def is_shell_command(text: str) -> bool:
    """Return True if the text looks like a shell command."""
    text = text.strip()

    if text.startswith("!"):
        return True

    parts = text.split()
    if not parts:
        return False

    command = parts[0].lower()

    if command.startswith("!"):
        command = command[1:]

    return command in COMMON_SHELL_COMMANDS


def extract_shell_command(text: str) -> str:
    """Extract a clean shell command from text."""
    text = text.strip()

    if text.startswith("!"):
        return text[1:].strip()

    return text


def execute_shell_command(
    command: str, timeout: int = DEFAULT_SHELL_TIMEOUT
) -> Tuple[bool, str]:
    """Execute a shell command and return the result."""
    shell_enabled, shell_reason = shell_execution_status()
    if not shell_enabled:
        return False, shell_reason

    if not _is_safe_command(command):
        return (
            False,
            "Comando bloqueado por segurança: contém caracteres perigosos (|, &, ;, `, $)",
        )

    try:
        command_args = shlex.split(command)
        if not command_args:
            return False, "Erro: comando vazio após parsing"

        result = _run_supervised(
            command_args,
            timeout=timeout,
            cwd=_shell_cwd(),
        )

        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        output = output.rstrip()

        if result.timeout:
            return False, f"⏱️ Timeout: comando excedeu {timeout}s"
        if command.strip().lower() == "clear" and result.success:
            return True, "__CLEAR_SCREEN__"
        if not output:
            output = (
                "[Command executed successfully]"
                if result.success
                else f"Comando terminou com código {result.exit_code}"
            )
        return result.success, output

    except subprocess.TimeoutExpired:
        return False, f"\u23f1\ufe0f  Timeout: comando excedeu {timeout}s"
    except FileNotFoundError:
        return False, "\u274c Error: command not found"
    except PermissionError:
        return False, "\u274c Erro: sem permissão para executar comando"
    except OSError as e:
        return False, f"\u274c Erro de sistema: {e!s}"


def should_execute_directly(text: str) -> bool:
    """Return True if the command should bypass the LLM."""
    if text.strip().startswith("!"):
        return True

    return bool(is_shell_command(text) and "?" not in text)


def _start_background_command(
    command: str, console: Any, owner_task: str | None = None
) -> Any:
    """Start a validated command through the session background supervisor."""
    from aura_cli.application.tools.shell_policy import ShellCommandResult
    from aura_cli.core.ui_bridge import UIIcons, UIStyles
    from aura_cli.core.utils.background_process import (
        get_background_process_supervisor,
    )

    command_args = shlex.split(command)
    if not command_args:
        error_msg = "Erro: comando vazio após parsing"
        console.print(f"[red]x {error_msg}[/red]")
        return ShellCommandResult(error_msg, exit_code=-1, background=True)

    try:
        record = get_background_process_supervisor().start(
            command_args,
            owner_task=owner_task,
            cwd=_shell_cwd(),
        )
    except FileNotFoundError:
        error_msg = "Error: command not found"
        console.print(f"[red]x {error_msg}[/red]")
        return ShellCommandResult(error_msg, exit_code=127, background=True)
    except PermissionError:
        error_msg = "Erro: sem permissão para executar comando"
        console.print(f"[red]x {error_msg}[/red]")
        return ShellCommandResult(error_msg, exit_code=126, background=True)
    except OSError as error:
        error_msg = f"Erro de sistema ao iniciar background: {error!s}"
        console.print(f"[red]x {error_msg}[/red]")
        return ShellCommandResult(error_msg, exit_code=-1, background=True)

    success_msg = (
        f"Comando '{command}' iniciado em segundo plano com PID: {record.pid}."
    )
    success_style = UIStyles.safe_style("SUCCESS", "green")
    console.print(f"[{success_style}]{UIIcons.SUCCESS} {success_msg}[/{success_style}]")
    return ShellCommandResult(
        success_msg,
        exit_code=None,
        background=True,
        process_id=record.pid,
    )


def run_shell_command(
    command: str, background: bool = False, owner_task: str | None = None
) -> str:
    """Run a shell command with timeout and capture output."""
    from rich.console import Console

    from aura_cli.application.execution_feedback import (
        ShellExecutionState,
        ShellExecutionView,
        present_shell_feedback,
    )
    from aura_cli.application.tools.shell_policy import ShellCommandResult
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call(
        "run_shell_command", {"command": command, "background": background}
    )

    console = Console()
    stats = get_stats()

    box = ShellExecutionView(command, background)

    shell_enabled, shell_reason = shell_execution_status()
    if not shell_enabled:
        box.cancel()
        console.print(f"[red]x {shell_reason}[/red]")
        return ShellCommandResult(shell_reason, exit_code=-1)

    action_desc = "em segundo plano" if background else "e aguardar"
    warning_style = UIStyles.safe_style("WARNING", "yellow")
    console.print(
        f"\n[{warning_style}]{UIIcons.WARNING} Executar comando {action_desc}:[/{warning_style}] [bold]{command}[/bold]"
    )

    if not _is_safe_command(command):
        error_msg = "Comando bloqueado por segurança: contém caracteres perigosos (|, &, ;, `, $)"
        console.print(f"[red]x {error_msg}[/red]")
        return ShellCommandResult(error_msg, exit_code=-1)

    from aura_cli.core.tools.human_intervention_adapter import (
        confirm_tool_execution_locally,
    )

    success_style = UIStyles.safe_style("SUCCESS", "green")
    confirmed = confirm_tool_execution_locally(
        "run_shell_command",
        {"command": command, "background": background},
        fallback_message="Executar?",
        console=console,
        auto_confirm_message=(
            f"[{success_style}]{UIIcons.SUCCESS} "
            "Skip confirmations: Executando comando automaticamente."
            f"[/{success_style}]"
        ),
    )

    if not confirmed:
        box.cancel()
        warning_style = UIStyles.safe_style("WARNING", "yellow")
        console.print(f"[{warning_style}]{UIIcons.CANCEL} Cancelled[/{warning_style}]")
        return ShellCommandResult(
            "Execução de comando cancelada pelo usuário.", exit_code=None
        )

    command_lower = command.lower()
    needs_interactive_handling = (
        "npx" in command_lower and "create-next-app" in command_lower
    )

    stats.track_tool_usage("run_shell_command")

    if background:
        return _start_background_command(command, console, owner_task=owner_task)

    try:
        if needs_interactive_handling:
            info_style = UIStyles.safe_style("INFO", "cyan")
            console.print(
                f"[{info_style}]{UIIcons.INFO} Executando em modo não-interativo (auto-confirmando todas as perguntas)[/{info_style}]"
            )

            input_data = "y\n" * 10
            command_args = shlex.split(command)
            if not command_args:
                error_msg = "Erro: comando vazio após parsing"
                console.print(f"[red]x {error_msg}[/red]")
                return error_msg

            box.start()
            result = _run_supervised(
                command_args,
                timeout=LONG_SHELL_TIMEOUT,
                input_data=input_data,
            )
            exit_code = -1 if result.timeout else result.exit_code
            box.output_lines = result.stdout.splitlines() if result.stdout else []
            box.stderr_lines = result.stderr.splitlines() if result.stderr else []
            box.finish(exit_code)
            present_shell_feedback(console, box)

            stats.add_shell_command(command, box.execution_time or 0)

            output = (result.stdout or "") + (
                f"\n{result.stderr}" if result.stderr else ""
            )
            if result.timeout:
                output = f"Timeout: comando excedeu {LONG_SHELL_TIMEOUT}s"
            return ShellCommandResult(
                output if output else "Command executed with no output.",
                exit_code=exit_code,
            )

        box.start()
        command_args = shlex.split(command)
        if not command_args:
            box.finish(-1)
            return ShellCommandResult("Erro: comando vazio após parsing", exit_code=-1)

        result = _run_supervised(
            command_args,
            timeout=LONG_SHELL_TIMEOUT,
        )
        stdout, stderr = result.stdout, result.stderr
        exit_code = -1 if result.timeout else result.exit_code

        box.output_lines = stdout.splitlines() if stdout else []
        box.stderr_lines = stderr.splitlines() if stderr else []
        box.finish(exit_code)
        present_shell_feedback(console, box)
        output = ((stdout or "") + (f"\n{stderr}" if stderr else "")) or (
            "Command executed with no output."
        )
        if result.timeout:
            output = f"Timeout: comando excedeu {LONG_SHELL_TIMEOUT}s"

        stats.add_shell_command(command, box.execution_time or 0)
        return ShellCommandResult(output, exit_code=exit_code)

    except KeyboardInterrupt:
        box.cancel()
        warning_style = UIStyles.safe_style("WARNING", "yellow")
        console.print(f"[{warning_style}]{UIIcons.CANCEL} Cancelled[/{warning_style}]")
        return ShellCommandResult("Command cancelled by user.", exit_code=None)

    except subprocess.TimeoutExpired:
        box.state = ShellExecutionState.FAILED
        box.exit_code = -1
        present_shell_feedback(console, box)
        return ShellCommandResult(
            "Timeout: comando excedeu o tempo limite", exit_code=-1
        )

    except Exception as e:
        box.state = ShellExecutionState.FAILED
        box.exit_code = -1
        present_shell_feedback(console, box)
        return ShellCommandResult(f"Error executing command: {e!s}", exit_code=-1)
