"""Basic command handlers for Aura CLI.

Handles commands:
- /help: Display help message
- /clear: Clear terminal screen
- /exit: Exit application
- /tui: Switch to TUI mode
- /welcome: Show welcome message and quick tips
"""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aura_cli.cli.ui.composition.dashboard_surface import render_dashboard_subcommand
from aura_cli.cli.ui.console_view import display_console_view, get_console_history
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console


def handle_help() -> None:
    """Display help with all available commands in formatted table."""
    console = get_console()

    table = Table(
        show_header=True,
        header_style=f"{UIStyles.PRIMARY} bold",
        box=None,
        padding=(0, 2),
        expand=True,
    )
    table.add_column("Comando", style=f"{UIStyles.ACCENT} bold", width=20)
    table.add_column("Descrição", style=UIStyles.BODY)
    table.add_column("Categoria", style=f"{UIStyles.MUTED} italic", width=15)

    commands = [
        (
            "/agi <objetivo>",
            "Inicia agente estratégico para tarefas complexas",
            f"{UIIcons.AGENT} Agentes",
        ),
        (
            "/ops <tarefa>",
            "Inicia agente DevOps (git, docker, sistema)",
            f"{UIIcons.OPS} Ops",
        ),
        (
            "/tools",
            "Lista todas as ferramentas disponíveis",
            f"{UIIcons.TOOL} Ferramentas",
        ),
        (
            "/tool <nome>",
            "Mostra detalhes de uma ferramenta",
            f"{UIIcons.TOOL} Ferramentas",
        ),
        ("/todo", "Exibe quadro de tarefas do projeto", f"{UIIcons.PASTE} Projeto"),
        ("/init", "Indexa o projeto atual (cria .aura/)", f"{UIIcons.PASTE} Projeto"),
        ("/notebook", "Gerencia memória de longo prazo", f"{UIIcons.AGI} Memória"),
        (
            "/model",
            "Seleciona modelo de IA (Gemini, GPT, etc)",
            f"{UIIcons.SYSTEM} Config",
        ),
        (
            "/dev [status]",
            "Informa a disponibilidade de LLMs locais",
            f"{UIIcons.SYSTEM} Config",
        ),
        ("/settings", "Menu interativo de configurações", f"{UIIcons.SYSTEM} Config"),
        (
            "/theme",
            "Seleciona tema visual (Nebula, minimal, etc)",
            f"{UIIcons.SYSTEM} Config",
        ),
        ("/keyboard", "Mostra atalhos de teclado", f"{UIIcons.SYSTEM} Config"),
        ("/extensions", "Gerencia extensões do Aura", f"{UIIcons.SPARKLES} Extensões"),
        (
            "/history",
            "Exibe histórico de interações da sessão",
            f"{UIIcons.STATS} Gestão",
        ),
        ("/session", "Gerencia sessões (salvar/carregar)", f"{UIIcons.SAVE} Gestão"),
        (
            "/workflow",
            "Gerencia workflows automatizados",
            f"{UIIcons.WORKING} Workflow",
        ),
        ("/cache", "Gerencia cache do sistema", f"{UIIcons.ROCKET} Cache"),
        (
            "/tangent",
            "Gerencia conversas paralelas (tangentes)",
            f"{UIIcons.ARROW} Contexto",
        ),
        (
            "/checkpoint",
            "Checkpoints: init, create, list, restore (git)",
            f"{UIIcons.COMMIT} Contexto",
        ),
        ("/tui", "Abre interface gráfica no terminal (Nebula)", f"{UIIcons.SYSTEM} UI"),
        ("/welcome", "Exibe boas-vindas e comandos rápidos", f"{UIIcons.AURA} Sistema"),
        ("/clear", "Limpa a tela do terminal", f"{UIIcons.AURA} Sistema"),
        ("/exit", "Encerra o Aura CLI", f"{UIIcons.AURA} Sistema"),
    ]

    for cmd, desc, cat in commands:
        table.add_row(cmd, desc, cat)

    # Advanced commands section
    adv_table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    adv_table.add_column("Comando", style=f"dim {UIStyles.ACCENT}", width=20)
    adv_table.add_column("Descrição", style=f"dim {UIStyles.BODY}")

    advanced = [
        ("/auto-run", "Ativa/desativa execução automática de ferramentas (Shift+Tab)"),
        ("/keyboard", "Mostra todos os atalhos de teclado"),
        ("/welcome", "Reexibe boas-vindas e dicas rápidas"),
        ("/tool <nome>", "Detalhes e schema de uma ferramenta específica"),
        ("/memory", "Busca e lista memórias persistentes"),
        ("/constitution", "Exibe ou edita a constituição do projeto"),
    ]
    for cmd, desc in advanced:
        adv_table.add_row(cmd, desc)

    adv_panel = Panel(
        adv_table,
        title=f"[dim {UIStyles.MUTED}]Comandos Avançados[/]",
        border_style=UIStyles.BORDER_PRIMARY,
        padding=(0, 2),
    )

    panel = Panel(
        table,
        title=f"[{UIStyles.TITLE}]{UIIcons.AURA} Comandos Disponíveis[/]",
        border_style=UIStyles.BORDER_PRIMARY,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print(adv_panel)
    console.print()


def handle_welcome() -> None:
    """Show compact welcome message and quick tips (re-discoverability)."""
    console = get_console()
    welcome_text = (
        f"[{UIStyles.TITLE}]Bem-vindo ao Aura CLI[/]\n\n"
        f"[{UIStyles.BODY}]Comandos rápidos:[/]\n"
        f"  [cyan]/help[/]     — Lista todos os comandos\n"
        f"  [cyan]/keyboard[/] — Atalhos de teclado\n"
        f"  [cyan]/tools[/]    — Ferramentas disponíveis\n"
        f"  [cyan]/model[/]    — Trocar modelo de IA\n\n"
        f"[{UIStyles.MUTED}]Digite uma pergunta ou use um comando acima.[/{UIStyles.MUTED}]"
    )
    panel = Panel(
        welcome_text,
        title=f"[{UIStyles.TITLE}]{UIIcons.AURA} Olá![/]",
        border_style=UIStyles.BORDER_PRIMARY,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def handle_history() -> None:
    """Display session interaction history using ConsoleHistory."""
    history = get_console_history()
    if not history.interactions:
        Console().print(
            Panel(
                f"[{UIStyles.MUTED}]Nenhuma interação registrada nesta sessão.\n\n"
                f"O histórico é populado automaticamente conforme você conversa com o Aura.[/{UIStyles.MUTED}]",
                title=f"[{UIStyles.TITLE}]{UIIcons.STATS} Histórico da Sessão[/]",
                border_style=UIStyles.BORDER_MUTED,
            )
        )
        return
    display_console_view(history.selected_id)


def handle_clear() -> None:
    """Clear terminal screen (keeps scroll history)."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def handle_dashboard(args: str) -> None:
    """Handle /dashboard [tool_history|memory|graph|infra|extensions] command."""
    console = get_console()
    subcmd = args.strip() or "help"
    try:
        renderable = render_dashboard_subcommand(console, subcmd)
        if renderable is None:
            return
        console.print()
        console.print(renderable)
        console.print()
    except Exception as e:
        console.print(
            f"[{UIStyles.ERROR}]Error loading dashboard '{subcmd.strip()}': {e}[/]"
        )
