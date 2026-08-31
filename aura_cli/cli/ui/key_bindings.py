"""Custom keyboard shortcuts for Aura CLI via prompt_toolkit.

Ctrl+T → /tools, Ctrl+L → /clear (both submitted without Enter),
Shift+Tab → toggle auto-run mode, ESC → cancel input.
Handlers use get_console() from display_facade (no new Console() per keypress).
"""

from prompt_toolkit.key_binding import KeyBindings
from rich.table import Table

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console


def create_key_bindings() -> KeyBindings:
    """Create custom key bindings for the prompt session.

    Returns:
        KeyBindings instance with Aura CLI shortcuts.
    """
    bindings = KeyBindings()

    @bindings.add("c-t")
    def show_tools(event):
        """Ctrl+T: Execute /tools immediately (no Enter required)."""
        event.app.exit(result="/tools")

    @bindings.add("c-l")
    def clear_screen_custom(event):
        """Ctrl+L: Execute /clear immediately (no Enter required)."""
        event.app.exit(result="/clear")

    @bindings.add("s-tab")
    def toggle_skip_confirmations(event):
        """Shift+Tab: Toggle auto-run mode (skip tool confirmations)."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        stats.skip_confirmations = not stats.skip_confirmations
        status = "ativado" if stats.skip_confirmations else "desativado"

        # Use shared console — no new Console() per keypress
        console = get_console()
        console.print(
            f"[{UIStyles.INFO}]{UIIcons.INFO} Execução sem confirmação {status}[/{UIStyles.INFO}]"
        )
        # Clear buffer and exit prompt so main loop re-renders toolbar state
        event.app.current_buffer.text = ""
        event.app.exit(result="")

    @bindings.add("escape")
    def cancel_operation(event):
        """ESC: Cancel current input and return to prompt.

        Does NOT kill running agents (/agi, /ops) — those continue in background.
        """
        # Only cancel if buffer is non-empty to avoid noisy blank-line messages
        if event.app.current_buffer.text:
            console = get_console()
            console.print(
                f"[{UIStyles.WARNING}]{UIIcons.CANCEL} Entrada cancelada (ESC)[/{UIStyles.WARNING}]"
            )
        event.app.current_buffer.text = ""
        event.app.exit(result="")

    # Ctrl+H removed — conflicts with backspace in many terminals.
    # Use /keyboard or /help instead.

    return bindings


def show_keyboard_help() -> None:
    """Display professional keyboard shortcuts table."""
    console = get_console()

    table = Table(
        title="Atalhos de teclado",
        show_header=True,
        header_style=UIStyles.SUBTITLE,
        border_style=None,
        box=None,
    )

    table.add_column("Shortcut", width=15, style=UIStyles.ACCENT)
    table.add_column("Action", width=40, style=UIStyles.BODY)
    table.add_column("Description", width=35, style=UIStyles.MUTED)

    shortcuts = [
        ("Ctrl+T", "Executar /tools", "Listar ferramentas disponíveis"),
        ("Ctrl+L", "Executar /clear", "Limpar a tela sem pressionar Enter"),
        ("Shift+Tab", "Alternar automático", "Ignorar confirmações de tools"),
        ("ESC", "Cancelar entrada", "Limpar o buffer atual"),
        ("Ctrl+C", "Sair", "Encerrar a AuraCli"),
        ("/keyboard", "Mostrar ajuda", "Também: /keys, /shortcuts"),
    ]

    for shortcut, action, description in shortcuts:
        table.add_row(
            f"[bold {UIStyles.PRIMARY}]{shortcut}[/bold {UIStyles.PRIMARY}]",
            f"[{UIStyles.PRIMARY}]{action}[/]",
            description,
        )

    console.print(table)
