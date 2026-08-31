"""
First-Run Setup Wizard for Aura CLI.

Provides a guided onboarding experience when no config exists,
using questionary for interactive prompts.

The wizard recommends configuring 4 free providers (Google, Cerebras, OpenRouter, Groq)
to guarantee uninterrupted AGI pipeline execution via cross-provider fallback.
"""

from rich.console import Console
from rich.panel import Panel

from aura_cli.core.llm.model_utils import get_default_model_for_provider
from aura_cli.core.logger import get_logger
from aura_cli.core.paths import get_aura_home

logger = get_logger(__name__)

CONFIG_DIR = get_aura_home()
CONFIG_FILE = CONFIG_DIR / "config.json"

# Provider display order: free-tier first, paid after
PROVIDERS = {
    "Google Gemini (free)": "google",
    "Cerebras (free)": "cerebras",
    "OpenRouter (free)": "openrouter",
    "Groq (free)": "groq",
    "OpenAI": "openai",
    "Anthropic": "anthropic",
}

DEFAULT_MODELS = {
    provider: get_default_model_for_provider(provider)
    for provider in ("google", "cerebras", "openrouter", "groq", "openai", "anthropic")
}

KEY_URLS = {
    "google": "https://aistudio.google.com/apikey",
    "cerebras": "https://cloud.cerebras.ai/",
    "openrouter": "https://openrouter.ai/keys",
    "groq": "https://console.groq.com/keys",
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
}

# Public alias used by external scripts and tests
PROVIDER_URLS = KEY_URLS


def is_first_run() -> bool:
    """Check if this is the first run (no config.json exists)."""
    return not CONFIG_FILE.exists()


def run_setup_wizard() -> bool:
    """
    Run the interactive first-run setup wizard.

    Recommends 4 free-tier providers for optimal AGI pipeline performance.

    Returns:
        True if setup completed successfully, False if skipped/cancelled.
    """
    import questionary

    console = Console()

    # Welcome banner
    console.print()
    console.print(
        Panel(
            "[bold cyan]Bem-vindo ao Aura CLI![/bold cyan]\n\n"
            "Vamos configurar em menos de 1 minuto.\n"
            "Para máxima performance do AGI, recomendamos 4 providers gratuitos:\n\n"
            "  [green]1.[/green] Google Gemini — modelo principal (gemini-2.5-flash)\n"
            "  [green]2.[/green] Cerebras     — respostas ultra-rápidas (0.3s)\n"
            "  [green]3.[/green] OpenRouter   — fallback confiável (nemotron-3-super)\n\n"
            "  [green]4.[/green] Groq         — inferência rápida (GPT OSS)\n\n"
            "[dim]Com os providers configurados, o pipeline AGI reduz falhas por rate limit.[/dim]",
            title="[bold]◈ Setup Inicial[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()

    try:
        # Ask setup mode
        mode = questionary.select(
            "Como deseja configurar?",
            choices=[
                "Configurar os 4 gratuitos (recomendado)",
                "Escolher apenas 1 provider",
                "Pular (configurar depois com /settings)",
            ],
        ).ask()

        if mode is None or "Pular" in mode:
            console.print(
                "\n[dim]Setup pulado. Use /settings quando quiser configurar.[/dim]"
            )
            return False

        if "4 gratuitos" in mode:
            return _setup_multiple_providers(console)
        else:
            return _setup_single_provider(console)

    except KeyboardInterrupt:
        console.print(
            "\n[dim]Setup pulado. Use /settings quando quiser configurar.[/dim]"
        )
        return False
    except Exception as e:
        logger.warning(f"Setup wizard error: {e}")
        console.print(f"\n[yellow]Erro no setup: {e}[/yellow]")
        console.print("[dim]Use /settings para configurar manualmente.[/dim]")
        return False


def _setup_multiple_providers(console: Console) -> bool:
    """Guide user through setting up all 4 free providers."""
    import questionary

    providers_to_setup = [
        ("google", "Google Gemini", "AIza..."),
        ("cerebras", "Cerebras", "csk-..."),
        ("openrouter", "OpenRouter", "sk-or-v1-..."),
        ("groq", "Groq", "gsk_..."),
    ]

    configured = []

    for provider_key, provider_name, key_prefix in providers_to_setup:
        url = KEY_URLS[provider_key]
        console.print(
            f"\n[cyan]▸ {provider_name}[/cyan] — Obtenha sua key em: [underline]{url}[/underline]"
        )

        api_key = questionary.password(
            f"  API key {provider_name} ({key_prefix}):",
            instruction="(Enter para pular)",
        ).ask()

        if api_key and api_key.strip():
            _save_provider_key(provider_key, api_key.strip())
            configured.append(provider_name)
            console.print(f"  [green]✓[/green] {provider_name} configurado")
        else:
            console.print(f"  [dim]─ {provider_name} pulado[/dim]")

    if not configured:
        console.print(
            "\n[yellow]Nenhum provider configurado. Use /settings depois.[/yellow]"
        )
        return False

    # Set default model based on first configured provider
    primary = configured[0]
    provider_key = next(
        k
        for k, v in [
            ("google", "Google Gemini"),
            ("cerebras", "Cerebras"),
            ("openrouter", "OpenRouter"),
            ("groq", "Groq"),
        ]
        if v == primary
    )
    default_model = DEFAULT_MODELS[provider_key]

    from aura_cli.core.config import get_config_manager

    config = get_config_manager()
    config.set("default_model", default_model)
    config.save()

    # Success message
    console.print()
    fallback_msg = ""
    if len(configured) >= 3:
        fallback_msg = "\n  [green]◈[/green] Cross-provider fallback: [green]ativo[/green] (pipeline ininterrupto)"
    elif len(configured) >= 2:
        fallback_msg = (
            "\n  [yellow]◈[/yellow] Fallback parcial: 2 providers (recomendamos 3)"
        )

    console.print(
        Panel(
            f"[bold green]✓ Setup completo![/bold green]\n\n"
            f"  Providers: [cyan]{', '.join(configured)}[/cyan]\n"
            f"  Modelo:    [cyan]{default_model}[/cyan]"
            f"{fallback_msg}\n\n"
            "[dim]Altere a qualquer momento com /settings ou /model[/dim]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()
    return True


def _setup_single_provider(console: Console) -> bool:
    """Guide user through setting up a single provider."""
    import questionary

    provider_choice = questionary.select(
        "Qual provider deseja usar?",
        choices=list(PROVIDERS.keys()),
        instruction="(Setas para selecionar, Enter para confirmar)",
    ).ask()

    if provider_choice is None:
        return False

    provider_key = PROVIDERS[provider_choice]
    url = KEY_URLS[provider_key]
    console.print(f"\n[dim]Obtenha sua key em: {url}[/dim]")

    api_key = questionary.password(
        f"API key {provider_choice}:",
        instruction="(input oculto)",
    ).ask()

    if not api_key or not api_key.strip():
        console.print("\n[dim]Nenhuma key fornecida. Use /settings depois.[/dim]")
        return False

    _save_first_run_config(provider_key, api_key.strip())

    model = DEFAULT_MODELS.get(provider_key, "auto")
    console.print()
    console.print(
        Panel(
            f"[bold green]✓ Setup completo![/bold green]\n\n"
            f"  Provider: [cyan]{provider_choice}[/cyan]\n"
            f"  Modelo:   [cyan]{model}[/cyan]\n\n"
            "[dim]Dica: configure mais providers com /settings para fallback automático[/dim]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()
    return True


def _save_provider_key(provider: str, api_key: str) -> None:
    """Save a single provider's API key."""
    from aura_cli.core.secure_config import secure_config_manager

    secure_config_manager.set_api_key(provider, api_key)
    logger.info(f"API key configured for: {provider}")


def _save_first_run_config(provider: str, api_key: str) -> None:
    """Save the API key and default model from the setup wizard."""
    _save_provider_key(provider, api_key)

    default_model = DEFAULT_MODELS.get(provider, "gemini/gemini-2.5-flash")

    from aura_cli.core.config import get_config_manager

    config = get_config_manager()
    config.set("default_model", default_model)
    config.save()

    logger.info(f"First-run setup complete: provider={provider}, model={default_model}")
