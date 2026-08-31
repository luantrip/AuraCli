"""Configuration command handlers for Aura CLI.

Handles commands:
- /model: Select AI model
- /dev: Manage local LLMs
- /settings: Open settings menu
- /extensions: Manage extensions
"""

from typing import Optional

from rich.console import Console
from rich.table import Table

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.settings_modal import build_model_options, graphite_dialog_style
from aura_cli.core.config import config_manager
from aura_cli.core.extensions import get_plugin_manager
from aura_cli.core.llm.model_utils import get_valid_models, resolve_model_option
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def handle_model(current_model_name: str) -> str:
    """Allow user to select model interactively."""
    from prompt_toolkit.shortcuts import radiolist_dialog

    valid_models = get_valid_models()
    canonical_current = resolve_model_option(current_model_name)
    options = build_model_options(valid_models, canonical_current)
    values = [(option.model_id, option.label) for option in options]

    if not values:
        console = get_console()
        console.print(
            f"[{UIStyles.WARNING}]Nenhum modelo válido. Configure chaves em /settings.[/{UIStyles.WARNING}]"
        )
        return current_model_name

    result = radiolist_dialog(
        title="Aura  /  Modelo padrão",
        text=(
            "Escolha o modelo usado nas novas conversas.\n"
            "● modelo atual   ↑↓ navegar   Enter selecionar   Esc voltar"
        ),
        values=values,
        default=canonical_current,
        style=graphite_dialog_style(),
    ).run()

    if result:
        canonical_result = resolve_model_option(result)
        config_manager.set("default_model", canonical_result)
        return canonical_result

    return canonical_current


def handle_dev(args: str) -> Optional[str]:
    """Report the availability of local LLM support.

    Use /model para selecionar modelos remotos (gemini, cerebras, groq,
    openai, claude ou openrouter).
    """
    unavailable = (
        f"[{UIStyles.MUTED}]LLMs locais não estão disponíveis nesta versão. "
        f"Use [bold]/model[/] para modelos remotos (gemini, cerebras, groq, "
        f"openai, claude ou openrouter).[/]"
    )
    cmd = args.lower().strip() if args else ""

    if not cmd:
        dev_url = config_manager.get("dev_url", "http://localhost:11434")
        dev_model = config_manager.get("dev_model", "llama3")
        return (
            f"[{UIStyles.TITLE}]Aura Dev[/]\n"
            f"URL: {dev_url} · Modelo: {dev_model}\n"
            f"{unavailable}"
        )
    if cmd in ("on", "off"):
        return f"[{UIStyles.WARNING}]Comando indisponível.[/{UIStyles.WARNING}] {unavailable}"
    if cmd == "status":
        return f"[{UIStyles.INFO}]Status LLM local: indisponível[/{UIStyles.INFO}]\n{unavailable}"
    return (
        f"[{UIStyles.ERROR}]Comando desconhecido: {cmd}[/{UIStyles.ERROR}]\n"
        f"▪ Use: /dev ou /dev status"
    )


def handle_extensions() -> None:
    """List loaded extensions."""
    console = Console()
    manager = get_plugin_manager()
    extensions = manager.list_plugins()

    if not extensions:
        console.print(
            f"[{UIStyles.WARNING}]{UIIcons.WARNING} Nenhuma extensão carregada.[/]"
        )
        return

    table = Table(title="🧩 Extensões Ativas")
    table.add_column("Nome", style="cyan")
    table.add_column("Versão", style="green")
    table.add_column("Status", style="yellow")

    for ext in extensions:
        name = ext.name
        version = ext.version
        is_enabled = manager.is_plugin_enabled(name)
        status = "Active" if is_enabled else "Disabled"
        table.add_row(name, version, status)

    console.print(table)
