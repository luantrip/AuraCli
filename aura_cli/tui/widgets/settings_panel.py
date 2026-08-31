"""LLM Settings Configuration Panel for Aura TUI.

Interactive configuration panel for LLM provider settings and parameters.

Features:
- LLM Provider selection (OpenAI, Anthropic, Google, NVIDIA, etc.)
- Model selection with dropdown
- Temperature and max tokens sliders
- API keys with secure input
- Context settings configuration
- Save/load configuration profiles

Components:
- LLMSettings: Configuration dataclass
- Provider-specific options
- Real-time validation
- Secure credential handling
"""

import asyncio
import logging
from typing import ClassVar, Dict, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.validation import Number
from textual.widgets import Button, Input, Label, Select, Static, Switch

from aura_cli.application.presentation.llm_settings import (
    LLMSettings,
    parse_llm_settings_form,
    provider_api_key_name,
    provider_selector_name,
)
from aura_cli.core.api_key_store import (
    clear_api_key_for_provider,
    set_api_key_for_provider,
)
from aura_cli.core.api_keys import get_api_keys_dict
from aura_cli.core.config import get_config_manager
from aura_cli.core.llm.model_utils import (
    DEFAULT_MODEL,
    MODEL_PRESETS,
    get_provider_from_model,
)

logger = logging.getLogger(__name__)


class SettingsField(Static):
    """A single settings field with label and input."""

    def __init__(self, label: str, field_id: str, help_text: str = "", **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.label_text = label
        self.field_id = field_id
        self.help_text = help_text


class LLMSettingsPanel(Static):
    """
    Interactive settings panel for LLM configuration.

    Features:
    - Provider selection (OpenAI, Anthropic, Google, OpenRouter, NVIDIA, Local)
    - Model selection based on provider
    - Temperature, max tokens, etc. controls
    - API key input (secure)
    - Save/Reset functionality
    """

    PROVIDERS: ClassVar[dict] = {}
    CANONICAL_SCOPE: ClassVar[tuple[str, ...]] = ("provider", "model", "api_key")

    current_provider = reactive("google")
    settings_modified = reactive(False)

    class SettingsSaved(Message):
        """Emitted when settings are saved."""

        def __init__(self, settings: LLMSettings):
            """Initialize the instance."""
            super().__init__()
            self.settings = settings

    class SettingsReset(Message):
        """Emitted when settings are reset."""

    def __init__(self, initial_settings: Optional[LLMSettings] = None, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._ensure_provider_catalog()
        self.settings = initial_settings or self._load_settings_from_config()
        self._original_settings = LLMSettings(**self.settings.to_dict())

    @classmethod
    def _build_provider_catalog(cls) -> Dict[str, list[str]]:
        """Build provider catalog from the centralized model presets."""
        return {
            "google": list(MODEL_PRESETS.get("gemini", [])),
            "cerebras": list(MODEL_PRESETS.get("cerebras", [])),
            "openrouter": list(MODEL_PRESETS.get("openrouter", [])),
            "openai": list(MODEL_PRESETS.get("gpt", [])),
            "anthropic": list(MODEL_PRESETS.get("claude", [])),
            "nvidia": list(MODEL_PRESETS.get("nvidia", [])),
            "groq": list(MODEL_PRESETS.get("groq", [])),
        }

    @classmethod
    def _ensure_provider_catalog(cls) -> None:
        """Initialize provider catalog lazily from central presets."""
        if not cls.PROVIDERS:
            cls.PROVIDERS = cls._build_provider_catalog()

    @staticmethod
    def _provider_for_model(model: str) -> str:
        """Map a model ID to the TUI provider selector namespace."""
        provider = get_provider_from_model(model) or ""
        return provider_selector_name(provider)

    @staticmethod
    def _api_key_name_for_provider(provider: str) -> str:
        """Return the environment-style API key name for a provider."""
        return provider_api_key_name(provider)

    @classmethod
    def _load_settings_from_config(cls) -> LLMSettings:
        """Build panel settings from the canonical config and key sources."""
        cls._ensure_provider_catalog()
        config = get_config_manager()
        model = config.get("default_model") or DEFAULT_MODEL
        provider = cls._provider_for_model(model)
        provider_models = cls.PROVIDERS.get(provider, [])
        selected_model = (
            model
            if model in provider_models
            else (provider_models[0] if provider_models else model)
        )

        api_keys = get_api_keys_dict()
        api_key = api_keys.get(cls._api_key_name_for_provider(provider), "")

        return LLMSettings(
            provider=provider,
            model=selected_model,
            api_key=api_key,
        )

    @classmethod
    def persist_settings(cls, settings: LLMSettings) -> None:
        """Persist TUI settings through the canonical config and key paths."""
        config = get_config_manager()
        config.set("default_model", settings.model or DEFAULT_MODEL)

        if settings.provider == "local":
            return
        if settings.api_key and settings.api_key.strip():
            set_api_key_for_provider(settings.provider, settings.api_key)
        else:
            clear_api_key_for_provider(settings.provider)

    def on_mount(self) -> None:
        """Initialize dynamic data."""
        self._populate_themes()

    def _populate_themes(self) -> None:
        """Populate theme selector."""
        try:
            from aura_cli.tui.styles.themes import get_theme_manager

            manager = get_theme_manager()
            themes = manager.available_themes
            current = next(
                (
                    name
                    for name in themes
                    if manager.current_theme.name.lower().replace(" ", "-") == name
                ),
                themes[0] if themes else "nebula-dark",
            )

            theme_select = self.query_one("#theme_select", Select)
            theme_select.set_options([(t.capitalize(), t) for t in themes])
            theme_select.value = current
        except ImportError as error:
            logger.debug("Theme manager unavailable while mounting settings: %s", error)

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Static("⚙ Configuração LLM", classes="settings-header")
        yield Static(
            "Configuração canônica: provedor, modelo e chave API. Parâmetros avançados são apenas pré-visualização local.",
            classes="field-help",
        )

        with ScrollableContainer():
            with Vertical(classes="settings-section"):
                yield Static("Provedor & Modelo", classes="section-title")

                with Horizontal(classes="field-row"):
                    yield Label("Provedor:", classes="field-label")
                    yield Select(
                        [(p.title(), p) for p in self.PROVIDERS],
                        value=self.settings.provider,
                        id="provider_select",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Modelo:", classes="field-label")
                    yield Select(
                        [(m, m) for m in self.PROVIDERS[self.settings.provider]],
                        value=self.settings.model,
                        id="model_select",
                    )

            with Vertical(classes="settings-section"):
                yield Static(
                    "Parâmetros de Geração (Pré-visualização)", classes="section-title"
                )

                with Horizontal(classes="field-row"):
                    yield Label("Temperatura:", classes="field-label")
                    yield Input(
                        str(self.settings.temperature),
                        id="temperature_input",
                        validators=[Number(minimum=0.0, maximum=2.0)],
                        placeholder="0.0 - 2.0",
                    )
                    yield Static("(criatividade)", classes="field-help")

                with Horizontal(classes="field-row"):
                    yield Label("Máx. Tokens:", classes="field-label")
                    yield Input(
                        str(self.settings.max_tokens),
                        id="max_tokens_input",
                        validators=[Number(minimum=1, maximum=128000)],
                        placeholder="1 - 128000",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Top P:", classes="field-label")
                    yield Input(
                        str(self.settings.top_p),
                        id="top_p_input",
                        validators=[Number(minimum=0.0, maximum=1.0)],
                        placeholder="0.0 - 1.0",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Penalidade Freq.:", classes="field-label")
                    yield Input(
                        str(self.settings.frequency_penalty),
                        id="freq_penalty_input",
                        validators=[Number(minimum=-2.0, maximum=2.0)],
                        placeholder="-2.0 - 2.0",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Penalidade Pres.:", classes="field-label")
                    yield Input(
                        str(self.settings.presence_penalty),
                        id="pres_penalty_input",
                        validators=[Number(minimum=-2.0, maximum=2.0)],
                        placeholder="-2.0 - 2.0",
                    )

            with Vertical(classes="settings-section"):
                yield Static("Configuração da API", classes="section-title")

                with Horizontal(classes="field-row"):
                    yield Label("Chave API:", classes="field-label")
                    yield Input(
                        self.settings.api_key,
                        id="api_key_input",
                        password=True,
                        placeholder="sk-...",
                    )
                    yield Button(
                        "▶ Testar",
                        id="test_connection_btn",
                        variant="warning",
                        classes="action-button",
                    )
                    yield Button(
                        "✗ Remover chave",
                        id="remove_api_key_btn",
                        variant="error",
                        classes="action-button",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("URL Base:", classes="field-label")
                    yield Input(
                        self.settings.base_url,
                        id="base_url_input",
                        placeholder="https://api.openai.com/v1 (optional)",
                    )

            with Vertical(classes="settings-section"):
                yield Static("Recursos", classes="section-title")

                with Horizontal(classes="field-row"):
                    yield Label("Streaming:", classes="field-label")
                    yield Switch(value=self.settings.streaming, id="streaming_switch")
                    yield Static("Habilitar respostas em stream", classes="field-help")

                with Horizontal(classes="field-row"):
                    yield Label("Janela de Contexto:", classes="field-label")
                    yield Input(
                        str(self.settings.context_window),
                        id="context_window_input",
                        validators=[Number(minimum=1000, maximum=128000)],
                        placeholder="tokens",
                    )

            with Vertical(classes="settings-section"):
                yield Static("Prompt do Sistema", classes="section-title")
                yield Input(
                    self.settings.system_prompt,
                    id="system_prompt_input",
                )

            with Vertical(classes="settings-section"):
                yield Static("Aparência", classes="section-title")
                with Horizontal(classes="field-row"):
                    yield Label("Tema:", classes="field-label")
                    yield Select(
                        [],  # Will be populated in on_mount
                        id="theme_select",
                    )

            with Horizontal(classes="button-row"):
                yield Button(
                    "▾ Salvar",
                    variant="primary",
                    id="save_button",
                    classes="save-button",
                )
                yield Button("⟳ Resetar", variant="default", id="reset_button")
                yield Button("✖ Cancelar", variant="error", id="cancel_button")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        self.settings_modified = True

        if event.select.id == "provider_select":
            self.current_provider = str(event.value)
            model_select = self.query_one("#model_select", Select)
            new_models = self.PROVIDERS.get(str(event.value), [])
            model_select.set_options([(m, m) for m in new_models])
            if new_models:
                model_select.value = new_models[0]
            api_keys = get_api_keys_dict()
            key_name = self._api_key_name_for_provider(str(event.value))
            self.query_one("#api_key_input", Input).value = api_keys.get(key_name, "")

        elif event.select.id == "theme_select":
            try:
                from aura_cli.tui.styles.themes import get_theme_manager

                get_theme_manager().set_theme(str(event.value))
                self.notify(f"Tema alterado para {event.value}", title="Tema")
            except Exception as error:
                logger.warning("Unable to apply TUI theme %r: %s", event.value, error)
                self.notify(
                    "Não foi possível aplicar o tema.", title="Tema", severity="error"
                )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self.settings_modified = True

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes."""
        self.settings_modified = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save_button":
            self._save_settings()
        elif event.button.id == "reset_button":
            self._reset_settings()
        elif event.button.id == "cancel_button":
            self.post_message(self.SettingsReset())
        elif event.button.id == "test_connection_btn":
            self._test_connection()
        elif event.button.id == "remove_api_key_btn":
            self._remove_api_key()

    def _remove_api_key(self) -> None:
        """Clear API key for the selected provider."""
        provider_select = self.query_one("#provider_select", Select)
        provider = str(provider_select.value) if provider_select.value else "google"
        clear_api_key_for_provider(provider)
        self.query_one("#api_key_input", Input).value = ""
        self.settings.api_key = ""
        self.notify(
            f"Chave removida: {provider}", title="API Key", severity="information"
        )

    def _test_connection(self) -> None:
        """Test the current API configuration."""
        provider_select = self.query_one("#provider_select", Select)
        provider = str(provider_select.value) if provider_select.value else "google"
        api_key = self.query_one("#api_key_input", Input).value

        if not api_key:
            self.notify("Insira uma chave API primeiro", title="Erro", severity="error")
            return

        self.notify(f"Testando conexão com {provider}...", title="Testando")
        self.run_worker(self._test_connection_async(provider, api_key))

    async def _test_connection_async(self, provider: str, api_key: str) -> None:
        """Validate an API key off the Textual event loop."""
        try:
            from aura_cli.core.llm.api_validator import (
                ValidationStatus,
                validate_api_key,
            )

            result = await asyncio.to_thread(validate_api_key, provider, api_key)
            if result.status == ValidationStatus.SUCCESS:
                self.notify(
                    f"Sucesso: {result.message}",
                    title="Conexão verificada",
                    severity="information",
                )
            else:
                self.notify(
                    f"Falha: {result.message}",
                    title="Conexão falhou",
                    severity="error",
                )
        except Exception as error:
            self.notify(f"Erro: {error!s}", title="Erro no teste", severity="error")

    def _save_settings(self) -> None:
        """Collect and save all settings."""
        try:
            provider_select = self.query_one("#provider_select", Select)
            model_select = self.query_one("#model_select", Select)

            self.settings = parse_llm_settings_form(
                {
                    "provider": provider_select.value,
                    "model": model_select.value or DEFAULT_MODEL,
                    "temperature": self.query_one("#temperature_input", Input).value,
                    "max_tokens": self.query_one("#max_tokens_input", Input).value,
                    "top_p": self.query_one("#top_p_input", Input).value,
                    "frequency_penalty": self.query_one(
                        "#freq_penalty_input", Input
                    ).value,
                    "presence_penalty": self.query_one(
                        "#pres_penalty_input", Input
                    ).value,
                    "api_key": self.query_one("#api_key_input", Input).value,
                    "base_url": self.query_one("#base_url_input", Input).value,
                    "streaming": self.query_one("#streaming_switch", Switch).value,
                    "context_window": self.query_one(
                        "#context_window_input", Input
                    ).value,
                    "system_prompt": self.query_one(
                        "#system_prompt_input", Input
                    ).value,
                }
            )

            self.persist_settings(self.settings)

            self.settings_modified = False
            self._original_settings = LLMSettings(**self.settings.to_dict())

            self.post_message(self.SettingsSaved(self.settings))
            self.notify(
                "Configurações canônicas salvas. Parâmetros avançados permanecem locais.",
                title="Configurações",
                severity="information",
            )

        except ValueError as e:
            self.notify(f"Invalid value: {e}", title="Error", severity="error")

    def _reset_settings(self) -> None:
        """Reset settings to original values."""
        self.settings = LLMSettings(**self._original_settings.to_dict())
        self._populate_fields()
        self.settings_modified = False
        self.notify(
            "Configurações resetadas para valores originais", title="Configurações"
        )

    def _populate_fields(self) -> None:
        """Populate all fields with current settings."""
        provider_select = self.query_one("#provider_select", Select)
        provider_select.value = self.settings.provider

        model_select = self.query_one("#model_select", Select)
        models = self.PROVIDERS.get(self.settings.provider, [])
        model_select.set_options([(m, m) for m in models])
        model_select.value = self.settings.model

        self.query_one("#temperature_input", Input).value = str(
            self.settings.temperature
        )
        self.query_one("#max_tokens_input", Input).value = str(self.settings.max_tokens)
        self.query_one("#top_p_input", Input).value = str(self.settings.top_p)
        self.query_one("#freq_penalty_input", Input).value = str(
            self.settings.frequency_penalty
        )
        self.query_one("#pres_penalty_input", Input).value = str(
            self.settings.presence_penalty
        )
        self.query_one("#api_key_input", Input).value = self.settings.api_key
        self.query_one("#base_url_input", Input).value = self.settings.base_url
        self.query_one("#streaming_switch", Switch).value = self.settings.streaming
        self.query_one("#context_window_input", Input).value = str(
            self.settings.context_window
        )
        self.query_one(
            "#system_prompt_input", Input
        ).value = self.settings.system_prompt

    def load_settings(self, settings: LLMSettings) -> None:
        """Load settings into the panel."""
        self.settings = settings
        self._original_settings = LLMSettings(**settings.to_dict())
        self._populate_fields()
        self.settings_modified = False

    def get_settings(self) -> LLMSettings:
        """Get current settings."""
        return self.settings


LLMSettingsPanel._ensure_provider_catalog()
