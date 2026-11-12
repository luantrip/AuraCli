"""
First-Run Setup Wizard for Aura CLI.

Provides a guided onboarding experience when no config exists,
using the shared prompt layer (``aura_cli.cli.ui.prompts``).

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

_MODE_MULTI = "multi"
_MODE_SINGLE = "single"
_MODE_SKIP = "skip"


def is_first_run() -> bool:
    """Check if onboarding still needs to run.

    True only when no config exists AND onboarding was never completed/skipped.
    An explicit ``onboarding_completed`` marker (written on every terminal path,
    including skip) prevents the wizard from re-triggering on every launch.
    """
    if not CONFIG_FILE.exists():
        return True
    try:
        from aura_cli.core.config import get_config_manager

        return not bool(get_config_manager().get("onboarding_completed"))
    except Exception:
        # If config can't be read, fall back to file-existence semantics.
        return False


def _mark_onboarding_complete() -> None:
    """Persist an explicit marker so onboarding is not shown again."""
    try:
        from aura_cli.core.config import get_config_manager

        config = get_config_manager()
        config.set("onboarding_completed", True)
        config.save()
    except Exception as exc:
        logger.warning(f"Could not persist onboarding marker: {exc}")


def run_setup_wizard(*, key_required: bool = False) -> bool:
    """
    Run the interactive first-run setup wizard.

    ``key_required`` is set when the app cannot start without a key (re-entry after a
    skipped/incomplete setup): the third option then leaves instead of "configure
    later", because there is no usable "later" while no key exists.

    Recommends 4 free-tier providers for optimal AGI pipeline performance.

    Returns:
        True if setup completed successfully, False if skipped/cancelled.
    """
    from aura_cli.cli.ui.display_facade import get_console
    from aura_cli.cli.ui.prompts import select_dialog

    # Onboarding runs before register_ui(); get_console() returns the shared
    # console singleton so the wizard and the app use one console instance.
    console = get_console()

    # Welcome banner
    console.print()
    console.print(
        Panel(
            "[bold cyan]Welcome to Aura CLI![/bold cyan]\n\n"
            "Let's set up in under a minute.\n"
            "For best AGI performance, we recommend 4 free providers:\n\n"
            "  [green]1.[/green] Google Gemini — primary model (gemini-2.5-flash)\n"
            "  [green]2.[/green] Cerebras     — ultra-fast responses (0.3s)\n"
            "  [green]3.[/green] OpenRouter   — reliable fallback (nemotron-3-super)\n\n"
            "  [green]4.[/green] Groq         — fast inference (GPT OSS)\n\n"
            "[dim]With multiple providers, the AGI pipeline handles rate-limit failures automatically.[/dim]",
            title="[bold]◈ Initial Setup[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()

    try:
        mode = select_dialog(
            title="How would you like to set up?",
            values=[
                (_MODE_MULTI, "Set up the 4 free providers (recommended)"),
                (_MODE_SINGLE, "Choose a single provider"),
                (
                    _MODE_SKIP,
                    "Exit (configure later with: aura settings)"
                    if key_required
                    else "Skip (configure later with /settings)",
                ),
            ],
            full_screen=False,
        ).run()

        if mode is None or mode == _MODE_SKIP:
            console.print(
                "\n[dim]Setup skipped. Use /settings whenever you want to configure.[/dim]"
            )
            _mark_onboarding_complete()
            return False

        if mode == _MODE_MULTI:
            return _setup_multiple_providers(console)
        else:
            return _setup_single_provider(console)

    except KeyboardInterrupt:
        console.print(
            "\n[dim]Setup skipped. Use /settings whenever you want to configure.[/dim]"
        )
        _mark_onboarding_complete()
        return False
    except Exception as e:
        logger.warning(f"Setup wizard error: {e}")
        console.print(f"\n[yellow]Setup error: {e}[/yellow]")
        console.print("[dim]Use /settings to configure manually.[/dim]")
        _mark_onboarding_complete()
        return False


def _setup_multiple_providers(console: Console) -> bool:
    """Guide user through setting up all 4 free providers."""
    from aura_cli.cli.ui.prompts import input_dialog

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
            f"\n[cyan]▸ {provider_name}[/cyan] — Get your key at: [underline]{url}[/underline]"
        )

        api_key = input_dialog(
            title=f"API key {provider_name} ({key_prefix})",
            text="Enter to confirm · leave empty or Esc to skip",
            password=True,
            full_screen=False,
        ).run()

        if api_key and api_key.strip():
            key = api_key.strip()
            ok, detail = _validate_key_nonblocking(provider_key, key)
            _save_provider_key(provider_key, key)
            configured.append(provider_name)
            preview = _masked_key_preview(key)
            if ok:
                console.print(f"  [green]✓[/green] {provider_name} saved — {preview}")
            else:
                console.print(
                    f"  [yellow]⚠[/yellow] {provider_name} saved ({preview}), "
                    f"but validation failed: {detail}"
                )
        else:
            console.print(f"  [dim]─ {provider_name} skipped[/dim]")

    if not configured:
        console.print(
            "\n[yellow]No provider configured. Use /settings to add keys.[/yellow]"
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
    config.set("onboarding_completed", True)
    config.save()

    # Success message
    console.print()
    fallback_msg = ""
    if len(configured) >= 3:
        fallback_msg = "\n  [green]◈[/green] Cross-provider fallback: [green]active[/green] (uninterrupted pipeline)"
    elif len(configured) >= 2:
        fallback_msg = (
            "\n  [yellow]◈[/yellow] Partial fallback: 2 providers (3 recommended)"
        )

    console.print(
        Panel(
            f"[bold green]✓ Setup complete![/bold green]\n\n"
            f"  Providers: [cyan]{', '.join(configured)}[/cyan]\n"
            f"  Model:     [cyan]{default_model}[/cyan]"
            f"{fallback_msg}\n\n"
            "[dim]Change at any time with /settings or /model[/dim]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()
    return True


def _setup_single_provider(console: Console) -> bool:
    """Guide user through setting up a single provider."""
    from aura_cli.cli.ui.prompts import input_dialog, select_dialog

    provider_choice = select_dialog(
        title="Which provider do you want to use?",
        text="↑↓ navigate   Enter confirm   Esc cancel",
        values=[(label, label) for label in PROVIDERS],
        full_screen=False,
    ).run()

    if provider_choice is None:
        return False

    provider_key = PROVIDERS[provider_choice]
    url = KEY_URLS[provider_key]
    console.print(f"\n[dim]Get your key at: {url}[/dim]")

    api_key = input_dialog(
        title=f"API key {provider_choice}",
        text="Hidden input · Enter to confirm · Esc to cancel",
        password=True,
        full_screen=False,
    ).run()

    if not api_key or not api_key.strip():
        console.print("\n[dim]No key provided. Use /settings to configure later.[/dim]")
        return False

    key = api_key.strip()
    ok, detail = _validate_key_nonblocking(provider_key, key)
    if not ok:
        console.print(
            f"\n[yellow]⚠ Key validation failed: {detail}[/yellow]\n"
            "[dim]The key will be saved anyway; adjust in /settings if needed.[/dim]"
        )
    _save_first_run_config(provider_key, key)

    model = DEFAULT_MODELS.get(provider_key, "auto")
    console.print()
    console.print(
        Panel(
            f"[bold green]✓ Setup complete![/bold green]\n\n"
            f"  Provider: [cyan]{provider_choice}[/cyan]\n"
            f"  Model:    [cyan]{model}[/cyan]\n"
            f"  Key:      [dim]{_masked_key_preview(key)}[/dim]\n\n"
            "[dim]Tip: add more providers with /settings for automatic fallback[/dim]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()
    return True


def _masked_key_preview(key: str) -> str:
    """Return a display-safe summary of an API key: visible prefix + masked tail.

    Avoids printing the full key in the terminal while giving the user enough
    context to verify they entered the right key (e.g. ``AIzaSy··· (32 chars)``).
    """
    if not key:
        return "(empty)"
    visible = min(8, max(4, len(key) // 4))
    return f"{key[:visible]}{'·' * min(6, len(key) - visible)} ({len(key)} chars)"


def _validate_key_nonblocking(provider: str, api_key: str) -> tuple[bool, str]:
    """Validate an API key without blocking onboarding on failure.

    Returns (ok, detail). Network/timeout/rate-limit are treated as "probably
    valid" by quick_test_api_key, so only a genuinely invalid key reports False.
    Any unexpected error is swallowed and reported as a soft warning.
    """
    try:
        from aura_cli.core.llm.api_validator import quick_test_api_key

        return quick_test_api_key(provider, api_key)
    except Exception as exc:
        return False, f"could not validate ({exc})"


def _save_provider_key(provider: str, api_key: str) -> None:
    """Save a single provider's API key via the canonical key store.

    Delegates to ``set_api_key_for_provider`` (the same path used by /settings)
    so onboarding and later edits share one persistence contract, instead of
    writing straight to secure_config and diverging.
    """
    from aura_cli.core.api_key_store import set_api_key_for_provider

    set_api_key_for_provider(provider, api_key)
    logger.info(f"API key configured for: {provider}")


def _save_first_run_config(provider: str, api_key: str) -> None:
    """Save the API key and default model from the setup wizard."""
    _save_provider_key(provider, api_key)

    default_model = DEFAULT_MODELS.get(provider, "gemini/gemini-2.5-flash")

    from aura_cli.core.config import get_config_manager

    config = get_config_manager()
    config.set("default_model", default_model)
    config.set("onboarding_completed", True)
    config.save()

    logger.info(f"First-run setup complete: provider={provider}, model={default_model}")
