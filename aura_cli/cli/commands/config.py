"""Configuration command handlers for Aura CLI.

Handles commands:
- /model: Select AI model
- /dev: Manage local LLMs
- /settings: Open settings menu
- /extensions: Manage extensions
"""

from typing import Optional

from rich.table import Table

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.settings_modal import build_model_options, graphite_dialog_style
from aura_cli.core.config import config_manager
from aura_cli.core.extensions import get_plugin_manager
from aura_cli.core.llm.model_utils import (
    get_valid_models,
    provider_for_model,
    provider_has_key,
    resolve_model_option,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def handle_model(current_model_name: str) -> str:
    """Allow user to select model interactively."""
    from aura_cli.cli.helpers import get_api_keys_dict
    from aura_cli.cli.ui.prompts import select_dialog

    api_keys = get_api_keys_dict()
    # Only offer models whose provider has a configured key; if none are
    # configured yet, fall back to the full catalog so the picker is not empty.
    valid_models = get_valid_models(api_keys=api_keys, only_configured=True)
    if not valid_models:
        valid_models = get_valid_models()
    canonical_current = resolve_model_option(current_model_name)
    options = build_model_options(valid_models, canonical_current)
    values = [(option.model_id, option.label) for option in options]

    if not values:
        console = get_console()
        console.print(
            f"[{UIStyles.WARNING}]No valid model. Configure keys in /settings.[/{UIStyles.WARNING}]"
        )
        return current_model_name

    result = select_dialog(
        title="Aura  /  Default model",
        text=(
            "Choose the model used in new conversations.\n"
            "● current model   ↑↓ navigate   Enter select   Esc back"
        ),
        values=values,
        default=canonical_current,
        style=graphite_dialog_style(),
    ).run()

    if result:
        canonical_result = resolve_model_option(result)
        config_manager.set("default_model", canonical_result)
        # Warn if the selected model's provider has no configured key.
        # This is a hint, not a blocker — the key can be added later via /settings.
        provider = provider_for_model(canonical_result)
        if provider and provider != "auto" and not provider_has_key(provider, api_keys):
            console = get_console()
            console.print(
                f"[yellow]⚠ Model saved, but no API key found for provider "
                f"'{provider}'. Add it with /settings → API Keys.[/yellow]"
            )
        return canonical_result

    return canonical_current


def handle_dev(args: str) -> Optional[str]:
    """Report the availability of local LLM support.

    Use /model para selecionar modelos remotos (gemini, cerebras, groq,
    openai, claude ou openrouter).
    """
    unavailable = (
        f"[{UIStyles.MUTED}]Local LLMs are not available in this version. "
        f"Use [bold]/model[/] para modelos remotos (gemini, cerebras, groq, "
        f"openai, claude ou openrouter).[/]"
    )
    cmd = args.lower().strip() if args else ""

    if not cmd:
        dev_url = config_manager.get("dev_url", "http://localhost:11434")
        dev_model = config_manager.get("dev_model", "llama3")
        return (
            f"[{UIStyles.TITLE}]Aura Dev[/]\n"
            f"URL: {dev_url} · Model: {dev_model}\n"
            f"{unavailable}"
        )
    if cmd in ("on", "off"):
        return f"[{UIStyles.WARNING}]Command unavailable.[/{UIStyles.WARNING}] {unavailable}"
    if cmd == "status":
        return f"[{UIStyles.INFO}]Local LLM status: unavailable[/{UIStyles.INFO}]\n{unavailable}"
    return (
        f"[{UIStyles.ERROR}]Comando desconhecido: {cmd}[/{UIStyles.ERROR}]\n"
        f"▪ Use: /dev ou /dev status"
    )


def handle_extensions() -> None:
    """List loaded extensions."""
    console = get_console()
    manager = get_plugin_manager()
    extensions = manager.list_plugins()

    if not extensions:
        console.print(
            f"[{UIStyles.WARNING}]{UIIcons.WARNING} No extensions loaded.[/]"
        )
        return

    table = Table(title="🧩 Active Extensions")
    table.add_column("Nome", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Status", style="yellow")

    for ext in extensions:
        name = ext.name
        version = ext.version
        is_enabled = manager.is_plugin_enabled(name)
        status = "Active" if is_enabled else "Disabled"
        table.add_row(name, version, status)

    console.print(table)
