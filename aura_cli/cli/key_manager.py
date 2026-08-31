"""
API Key Management for Aura CLI

This module provides functions to check and configure API keys for LLM providers.
"""

import os
from typing import Any

from prompt_toolkit.shortcuts import (
    input_dialog as _input_dialog,
)
from prompt_toolkit.shortcuts import (
    message_dialog as _message_dialog,
)
from prompt_toolkit.shortcuts import (
    radiolist_dialog as _radiolist_dialog,
)
from prompt_toolkit.shortcuts import (
    yes_no_dialog as _yes_no_dialog,
)

from aura_cli.cli.helpers import get_api_keys_dict
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.settings_modal import graphite_dialog_style, settings_summary
from aura_cli.cli.utils import clear_screen
from aura_cli.core.config import get_config_manager
from aura_cli.core.llm.model_utils import (
    DEFAULT_MODEL,
    format_model_display_name,
    get_models_for_provider,
    resolve_model_option,
)
from aura_cli.core.logger import get_logger
from aura_cli.core.secure_config import secure_config_manager

console = get_console()
logger = get_logger(__name__)


def _model_preview(provider: str, limit: int = 2) -> str:
    """Render a short provider model preview from the canonical catalog."""
    models = get_models_for_provider(provider)
    if not models:
        return "nenhum modelo catalogado"
    return " · ".join(format_model_display_name(model) for model in models[:limit])


def _graphite_dialog(factory, **kwargs):
    """Apply the shared terminal-modal style to every settings dialog."""
    kwargs.setdefault("style", graphite_dialog_style())
    return factory(**kwargs)


def radiolist_dialog(**kwargs):
    return _graphite_dialog(_radiolist_dialog, **kwargs)


def input_dialog(**kwargs):
    return _graphite_dialog(_input_dialog, **kwargs)


def message_dialog(**kwargs):
    return _graphite_dialog(_message_dialog, **kwargs)


def yes_no_dialog(**kwargs):
    return _graphite_dialog(_yes_no_dialog, **kwargs)


def check_api_keys() -> bool:
    """
    Check if at least one API key is configured.

    Returns:
        True if at least one API key is configured, False otherwise.
    """
    try:
        from aura_cli.core.config import ConfigCompat

        pydantic_config = ConfigCompat()
        if any(
            [
                pydantic_config.get_api_key("google"),
                pydantic_config.get_api_key("cerebras"),
                pydantic_config.get_api_key("openrouter"),
                pydantic_config.get_api_key("openai"),
                pydantic_config.get_api_key("anthropic"),
                pydantic_config.get_api_key("nvidia"),
                pydantic_config.get_api_key("groq"),
            ]
        ):
            return True
    except Exception as _e:
        logger.debug(f"Ignorado: {_e}")
    return any(
        [
            secure_config_manager.get_api_key("google"),
            secure_config_manager.get_api_key("cerebras"),
            secure_config_manager.get_api_key("openrouter"),
            secure_config_manager.get_api_key("openai"),
            secure_config_manager.get_api_key("anthropic"),
            secure_config_manager.get_api_key("nvidia"),
            secure_config_manager.get_api_key("groq"),
        ]
    )


def clear_api_key(provider: str) -> None:
    """Remove an API key from the keyring, config file and environment."""
    from aura_cli.core.api_key_store import clear_api_key_for_provider

    try:
        clear_api_key_for_provider(provider)
        console.print(f"[{UIStyles.SUCCESS}]✓ Chave de API {provider} removida![/]")
    except Exception as e:
        console.print(f"[{UIStyles.ERROR}]Error removing key: {e}[/]")


def show_settings_menu() -> None:
    """
    Display the complete TUI settings menu with nested dialogs.
    Uses the same style as /theme command with radiolist_dialog.
    """
    try:
        _show_settings_tui()
    except (ImportError, AttributeError, RuntimeError) as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Error using TUI for settings, using fallback: {e}")
        _show_settings_fallback()


def _show_settings_tui() -> None:
    """Main settings TUI interface using radiolist_dialog."""
    from aura_cli.cli.ui.theme_manager import get_theme_manager

    config = get_config_manager()
    theme_manager = get_theme_manager()

    while True:
        api_keys = get_api_keys_dict()
        current_theme = config.get("theme_name") or theme_manager.current_theme
        raw_model = config.get("default_model") or ""
        current_model = (
            format_model_display_name(resolve_model_option(raw_model))
            if raw_model
            else "Não configurado"
        )
        log_level = config.get("log_level") or "INFO"

        # Build status indicators
        providers = {
            "Google": bool(api_keys.get("GOOGLE_API_KEY")),
            "Cerebras": bool(api_keys.get("CEREBRAS_API_KEY")),
            "OpenRouter": bool(api_keys.get("OPENROUTER_API_KEY")),
            "OpenAI": bool(api_keys.get("OPENAI_API_KEY")),
            "Claude": bool(api_keys.get("ANTHROPIC_API_KEY")),
            "NVIDIA": bool(api_keys.get("NVIDIA_API_KEY")),
            "Groq": bool(api_keys.get("GROQ_API_KEY")),
        }
        active_count = sum(providers.values())
        clear_screen()
        main_menu = radiolist_dialog(
            title="Aura  /  Configurações",
            text=settings_summary(active_count, current_model, str(current_theme)),
            values=[
                    ("apis", f"Chaves e provedores · {active_count}/7 ativos"),
                ("model", f"Modelo padrão · {current_model}"),
                ("themes", f"Aparência · {current_theme}"),
                ("system", f"Sistema · log {log_level}"),
                ("exit", "Fechar configurações"),
            ],
        ).run()

        if main_menu is None or main_menu == "exit":
            return

        if main_menu == "themes":
            _handle_themes_menu()
        elif main_menu == "apis":
            _handle_apis_menu()
        elif main_menu == "model":
            _handle_model_menu()
        elif main_menu == "system":
            _handle_system_menu()


def show_theme_menu() -> None:
    """Public entry point for theme selection (e.g. /theme command)."""
    _handle_themes_menu()


def _handle_themes_menu() -> None:
    """Handle theme selection with real-time preview."""
    from aura_cli.cli.ui.theme_manager import get_theme_manager, list_available_themes
    from aura_cli.core.config import get_config_manager

    config = get_config_manager()
    theme_manager = get_theme_manager()
    available_themes = list_available_themes()
    current_theme = config.get("theme_name") or theme_manager.current_theme

    theme_descriptions = {
        "nebula": "Deep void + neon accents (Tokyo Night)",
        "aura_minimal": "Apple HIG-inspired minimal (default)",
        "cyberpunk": "Classic neon cyberpunk terminal",
        "macos": "Alias for aura_minimal",
        "holographic": "Holográfico futurista",
        "dark": "Escuro clássico",
        "light": "Claro para telas brilhantes",
        "mono": "Monocromático para foco",
        "default": "Alias for aura_minimal",
    }

    theme_values = [
        (
            theme,
            f"{theme.capitalize()} - {theme_descriptions.get(theme, 'Tema personalizado')} {'(atual)' if theme == current_theme else ''}",
        )
        for theme in available_themes
    ]

    selected_theme = radiolist_dialog(
        title="🎨 Selecionar Tema",
        text="Escolha um tema de UI (aplicado em tempo real):",
        values=theme_values,
        default=current_theme if current_theme in available_themes else None,
    ).run()

    if selected_theme and selected_theme != current_theme:
        try:
            theme_manager.load_theme(selected_theme)
            config.set("theme_name", selected_theme)
            from aura_cli.cli.ui.constants import UIStyles, _clear_theme_cache

            _clear_theme_cache()
            UIStyles._reload_styles()
            UIStyles._ensure_initialized()

            from aura_cli.core.stats import get_stats

            stats = get_stats()
            success_style = UIStyles.safe_style("SUCCESS", "green")
            stats.set_notification(
                f"[{success_style}]{UIIcons.SUCCESS} Tema alterado para: {selected_theme}[/{success_style}]",
                duration_seconds=2.0,
            )

            message_dialog(
                title="✓ Tema Alterado",
                text=f"Tema '{selected_theme}' aplicado com sucesso!\n\nAs mudanças são aplicadas em tempo real.\n\nReinicie o Aura para ver todas as mudanças.",
            ).run()
        except Exception as e:
            error_msg = f"Error loading theme: {e}"
            message_dialog(
                title="✗ Erro",
                text=error_msg,
            ).run()


def _confirm_clear_key(provider: str, question: str) -> None:
    if yes_no_dialog(title="Confirmar", text=question).run():
        clear_api_key(provider)


def _confirm_clear_all() -> None:
    if yes_no_dialog(
        title="▲  Confirmar",
        text="Tem certeza que deseja remover TODAS as chaves de API?\n\nEsta ação não pode ser desfeita.",
    ).run():
        from aura_cli.core.api_key_store import clear_all_api_keys

        clear_all_api_keys()
        message_dialog(
            title="✓ Concluído", text="Todas as chaves de API foram removidas."
        ).run()


def _handle_apis_menu() -> None:
    """Handle API keys configuration menu."""
    while True:
        api_keys = get_api_keys_dict()

        def _st(key, keys=api_keys):
            return "✓" if keys.get(key) else "·"

        api_menu = radiolist_dialog(
            title="🔑 Provedores LLM",
            text="─── Adicione ou remova chaves de API\n",
            values=[
                (
                    "add_google",
                    f"{_st('GOOGLE_API_KEY')} Google Gemini        {_model_preview('google')} (free)",
                ),
                (
                    "add_cerebras",
                    f"{_st('CEREBRAS_API_KEY')} Cerebras             {_model_preview('cerebras')} (free)",
                ),
                (
                    "add_openrouter",
                    f"{_st('OPENROUTER_API_KEY')} OpenRouter           {_model_preview('openrouter')} (free)",
                ),
                (
                    "add_groq",
                    f"{_st('GROQ_API_KEY')} Groq                 {_model_preview('groq')} (free)",
                ),
                (
                    "add_openai",
                    f"{_st('OPENAI_API_KEY')} OpenAI              {_model_preview('openai')}",
                ),
                (
                    "add_anthropic",
                    f"{_st('ANTHROPIC_API_KEY')} Anthropic           {_model_preview('anthropic')}",
                ),
                (
                    "add_nvidia",
                    f"{_st('NVIDIA_API_KEY')} NVIDIA              {_model_preview('nvidia')}",
                ),
                ("sep", "────────────────────────────────────────"),
                ("remove_google", "  ✗ Remover Google"),
                ("remove_cerebras", "  ✗ Remover Cerebras"),
                ("remove_openrouter", "  ✗ Remover OpenRouter"),
                ("remove_groq", "  ✗ Remover Groq"),
                ("remove_openai", "  ✗ Remover OpenAI"),
                ("remove_anthropic", "  ✗ Remover Anthropic"),
                ("remove_nvidia", "  ✗ Remover NVIDIA"),
                ("clear_all", "  🗑️  Limpar tudo"),
                ("back", "  ← Voltar"),
            ],
        ).run()

        if api_menu is None or api_menu == "back":
            return
        if api_menu == "sep":
            continue

        _ADD = {
            "add_google": ("google", "Google (Gemini)"),
            "add_cerebras": ("cerebras", "Cerebras"),
            "add_openrouter": ("openrouter", "OpenRouter"),
            "add_groq": ("groq", "Groq"),
            "add_openai": ("openai", "OpenAI (GPT)"),
            "add_anthropic": ("anthropic", "Anthropic (Claude)"),
            "add_nvidia": ("nvidia", "NVIDIA"),
        }
        _REMOVE = {
            "remove_google": ("google", "Remover Google API Key?"),
            "remove_cerebras": ("cerebras", "Remover Cerebras API Key?"),
            "remove_openrouter": ("openrouter", "Remover OpenRouter API Key?"),
            "remove_groq": ("groq", "Remover Groq API Key?"),
            "remove_openai": ("openai", "Remover OpenAI API Key?"),
            "remove_anthropic": ("anthropic", "Remover Anthropic API Key?"),
            "remove_nvidia": ("nvidia", "Remover NVIDIA API Key?"),
        }

        if api_menu in _ADD:
            _configure_api_key(*_ADD[api_menu])
        elif api_menu in _REMOVE:
            provider, question = _REMOVE[api_menu]
            _confirm_clear_key(provider, question)
        elif api_menu == "clear_all":
            _confirm_clear_all()


def _system_menu_nim(config: Any) -> None:
    from aura_cli.core.nim_integrity import check_nim_integrity

    report = check_nim_integrity()
    lines = []
    for b in report.binaries:
        icon = "✓" if b.ok else ("⚠" if b.present else "✗")
        lines.append(f"  {icon} {b.name}")
    lib_icon = "✓" if report.library_ok else "✗"
    lines.append(f"  {lib_icon} notebook.dylib")

    status_text = "\n".join(lines)
    path = input_dialog(
        title="✦ F1 Engine (Nim)",
        text=f"Status dos binários:\n{status_text}\n\nCaminho (vazio = auto-detectar):",
        default=config.get("nim_binary_path") or "",
    ).run()
    if path is not None:
        config.set("nim_binary_path", path if path.strip() else None)


def _system_menu_log(config: Any) -> None:
    level = radiolist_dialog(
        title="📝 Nível de log",
        text="Selecione nível de detalhe dos logs:",
        values=[
            ("DEBUG", "DEBUG - Detalhe máximo (para desenvolvimento)"),
            ("INFO", "INFO  - Operação normal (recomendado)"),
            ("WARNING", "WARN  - Apenas avisos e erros"),
            ("ERROR", "ERROR - Apenas erros críticos"),
        ],
        default=config.get("log_level") or "INFO",
    ).run()
    if level:
        config.set("log_level", level)


def _system_menu_loops(config: Any) -> None:
    loops = input_dialog(
        title="🔄 Máximo de loops do agente",
        text="Máximo de iterações do agente (1-1000):",
        default=str(config.get("max_loops") or 50),
    ).run()
    if loops and loops.isdigit():
        loops_int = int(loops)
        if 1 <= loops_int <= 1000:
            config.set("max_loops", loops_int)
            message_dialog(
                title="✓ Configurado",
                text=f"Máximo de loops configurado para: {loops_int}",
            ).run()
        else:
            message_dialog(
                title="▲ Valor Inválido", text="O valor deve estar entre 1 e 1000."
            ).run()


def _system_menu_shell(config: Any) -> None:
    allow = yes_no_dialog(
        title="🐚 Execução de shell",
        text="Permitir que agentes executem comandos no terminal?\n(Recomendado: Sim, com supervisão)",
    ).run()
    config.set("enable_shell", allow)


def _system_menu_rag(config: Any) -> None:
    backend = radiolist_dialog(
        title="◈ Backend de armazenamento vetorial",
        text="Selecione backend de memória vetorial:",
        values=[
            ("keyword", "Keyword (Padrão, zero deps)"),
            ("chromadb", "ChromaDB (Semântico, requer extra [vector])"),
            ("faiss", "FAISS (Rápido, requer extra [vector-faiss])"),
        ],
        default=config.get("vector_backend") or "keyword",
    ).run()
    if backend:
        config.set("vector_backend", backend)


def _system_menu_ascii(config: Any) -> None:
    enable = yes_no_dialog(
        title="🔤 Modo ASCII",
        text="Ativar modo ASCII?\n\nUse em terminais sem suporte a Unicode/emoji.\nÍcones serão substituídos por caracteres ASCII.",
    ).run()
    config.set("ascii_mode", enable)
    from aura_cli.cli.ui.constants import UIIcons

    UIIcons.set_ascii_mode(enable)


def _system_menu_consciousness(config: Any) -> None:
    val = input_dialog(
        title="🎯 Threshold de Skills",
        text="Relevância mínima para injetar skills no contexto (0.1 a 0.9):\n\nValor menor = mais skills injetadas\nValor maior = apenas skills muito relevantes",
        default=str(config.get("consciousness_threshold") or 0.35),
    ).run()
    if val:
        try:
            t = float(val)
            if 0.1 <= t <= 0.9:
                config.set("consciousness_threshold", t)
            else:
                message_dialog(
                    title="▲ Valor Inválido", text="Use um valor entre 0.1 e 0.9."
                ).run()
        except ValueError:
            message_dialog(
                title="▲ Valor Inválido", text="Digite um número decimal (ex: 0.35)."
            ).run()


def _system_menu_temperature(config: Any) -> None:
    val = input_dialog(
        title="🌡️ Temperatura LLM",
        text="Temperatura para respostas (0.0 = determinístico, 1.0 = criativo):\n\nDeixe vazio para auto (recomendado).",
        default=str(config.get("temperature") or ""),
    ).run()
    if val is None:
        return
    if not val.strip():
        config.set("temperature", None)
    else:
        try:
            t = float(val)
            if 0.0 <= t <= 2.0:
                config.set("temperature", t)
            else:
                message_dialog(title="▲", text="Use 0.0 a 2.0.").run()
        except ValueError:
            message_dialog(title="▲", text="Invalid number.").run()


def _system_menu_system_prompt(config: Any) -> None:
    current = config.get("system_prompt") or ""
    val = input_dialog(
        title="◇ System Prompt",
        text="Prompt de sistema global (deixe vazio para padrão):",
        default=current,
    ).run()
    if val is not None:
        config.set("system_prompt", val if val.strip() else None)


_SYSTEM_MENU_HANDLERS: dict = {
    "nim": _system_menu_nim,
    "log": _system_menu_log,
    "loops": _system_menu_loops,
    "shell": _system_menu_shell,
    "rag": _system_menu_rag,
    "ascii": _system_menu_ascii,
    "consciousness": _system_menu_consciousness,
}


def _handle_system_menu() -> None:
    """Handle System and Agent settings configuration."""
    from aura_cli.core.config import get_config_manager
    from aura_cli.core.nim_integrity import check_nim_integrity

    config = get_config_manager()

    while True:
        # Nim status
        nim_report = check_nim_integrity()
        nim_ok = sum(1 for b in nim_report.binaries if b.ok)
        nim_total = len(nim_report.binaries)
        nim_label = (
            f"✓ {nim_ok}/{nim_total}"
            if nim_report.all_ok
            else f"⚠ {nim_ok}/{nim_total}"
        )

        log_level = config.get("log_level") or "INFO"
        max_loops = config.get("max_loops") or 50
        shell_exec = "✓" if config.get("enable_shell") else "✗"
        vector_backend = config.get("vector_backend") or "keyword"
        ascii_mode = "✓" if config.get("ascii_mode") else "✗"
        consciousness_threshold = config.get("consciousness_threshold") or 0.35
        temperature = config.get("temperature") or "auto"
        system_prompt = "Custom" if config.get("system_prompt") else "Padrão"
        skip_splash = "✓" if config.get("skip_splash") else "✗"

        menu_choice = radiolist_dialog(
            title="🛠️  Sistema",
            text=f"─── F1 Engine: {nim_label} · Shell: {shell_exec} · Log: {log_level}\n",
            values=[
                ("nim", f"✦ F1 Engine (Nim)        {nim_label} binários"),
                ("log", f"📝 Nível de log           {log_level}"),
                ("loops", f"🔄 Máx. loops agente      {max_loops}"),
                ("shell", f"🐚 Execução shell         {shell_exec}"),
                ("rag", f"◈ Backend vetorial       {vector_backend}"),
                ("temperature", f"🌡️  Temperatura LLM        {temperature}"),
                ("system_prompt", f"◇ System prompt          {system_prompt}"),
                ("ascii", f"🔤 Modo ASCII             {ascii_mode}"),
                ("skip_splash", f"◈ Pular splash           {skip_splash}"),
                (
                    "consciousness",
                    f"🎯 Threshold skills       {consciousness_threshold}",
                ),
                ("back", "  ← Voltar"),
            ],
        ).run()

        if menu_choice is None or menu_choice == "back":
            return

        if menu_choice == "temperature":
            _system_menu_temperature(config)
        elif menu_choice == "system_prompt":
            _system_menu_system_prompt(config)
        elif menu_choice == "skip_splash":
            config.set("skip_splash", not config.get("skip_splash"))
        else:
            handler = _SYSTEM_MENU_HANDLERS.get(menu_choice)
            if handler:
                handler(config)


def _persist_api_key(provider: str, api_key: str) -> None:
    """Save API key to all backends and clear env vars."""
    from aura_cli.core.api_key_store import set_api_key_for_provider

    set_api_key_for_provider(provider, api_key)


def _verify_and_notify_key(provider: str, api_key: str, provider_name: str) -> None:
    """Verify saved key and show result dialog."""
    import json

    saved_key = None
    try:
        from aura_cli.core.config import ConfigCompat

        saved_key = ConfigCompat().get_api_key(provider)
    except Exception as e:
        logger.debug(f"Error checking PydanticConfig: {e}")
    if not saved_key:
        try:
            saved_key = secure_config_manager.get_api_key(provider)
        except Exception as e:
            logger.debug(f"Error checking SecureConfig: {e}")
    if saved_key and saved_key == api_key:
        message_dialog(
            title="✓ Sucesso",
            text=f"{provider_name} API Key configurada e salva!\n\nA chave está disponível imediatamente.",
        ).run()
        return
    if saved_key:
        message_dialog(
            title="▲  Aviso",
            text=f"Chave salva, mas valor diferente do esperado.\n\nSalva: {saved_key[:20]}...\nEsperada: {api_key[:20]}...\n\nReinicie o Aura e verifique novamente.",
        ).run()
        return
    from aura_cli.core.paths import aura_path

    config_file = str(aura_path("config.json"))
    file_has_key = False
    if os.path.exists(config_file):
        try:
            with open(config_file, encoding="utf-8") as f:
                data = json.load(f)
                file_has_key = data.get("api_keys", {}).get(provider) == api_key
        except Exception as _e:
            logger.debug(f"Ignorado: {_e}")
    if file_has_key:
        message_dialog(
            title="✓ Sucesso",
            text=f"{provider_name} API Key configurada e salva!\n\nA chave foi salva no arquivo. Reinicie o Aura para garantir que esteja disponível.",
        ).run()
    else:
        message_dialog(
            title="▲  Aviso",
            text="Chave salva, mas não foi possível verificar.\n\nIsso pode ser normal se o keyring estiver sendo usado.\n\nReinicie o Aura e verifique em /settings.",
        ).run()


def _configure_api_key(provider: str, provider_name: str) -> None:
    """Configure an API key using input_dialog with connection test."""
    get_config_manager()
    clear_screen()

    api_key = input_dialog(
        title=f"Configurar {provider_name} API Key",
        text=f"Digite sua {provider_name} API Key:",
        password=True,
    ).run()

    if not api_key:
        return

    test_connection = yes_no_dialog(
        title="🔍 Testar Conexão",
        text="Deseja testar a API Key antes de salvar?\n\nIsso fará uma requisição mínima para validar a chave.",
    ).run()

    if test_connection:
        validation_result = _show_validation_popup(provider, api_key, provider_name)
        if validation_result is None or validation_result is False:
            return

    _persist_api_key(provider, api_key)
    _verify_and_notify_key(provider, api_key, provider_name)


def _show_validation_popup(
    provider: str, api_key: str, provider_name: str
) -> bool | None:
    """Display a centred popup during API key validation."""
    message_dialog(
        title="🔍 Validando Conexão",
        text=f"⏳ Testando API Key com {provider_name}...\n\nAguarde enquanto validamos a conexão.\n\nIsso pode levar alguns segundos.",
    ).run()
    try:
        from aura_cli.core.llm.api_validator import (
            ValidationStatus,
            validate_api_key,
        )

        result = validate_api_key(provider, api_key)
    except Exception as e:
        error_msg = str(e)[:250] if len(str(e)) > 250 else str(e)
        save_anyway = yes_no_dialog(
            title="❌ Erro na Validação",
            text=f"Ocorreu um erro ao validar a chave:\n\n{error_msg}\n\nDeseja salvar a chave mesmo assim?",
        ).run()
        return save_anyway
    if result.status == ValidationStatus.SUCCESS:
        preview_text = (
            f"\n\n📝 Preview da resposta:\n{result.response_preview}"
            if result.response_preview
            else ""
        )
        message_dialog(
            title="✅ Validação Bem-Sucedida",
            text=f"{result.message}{preview_text}",
        ).run()
        return True
    elif result.status == ValidationStatus.RATE_LIMITED:
        message_dialog(
            title="▲ Chave Válida (Limite/Créditos)",
            text=f"{result.message}",
        ).run()
        return True
    elif result.status == ValidationStatus.TIMEOUT:
        save_anyway = yes_no_dialog(
            title="▲ Timeout na Conexão",
            text=f"{result.message}\n\nA chave pode ser válida, mas a conexão está lenta.\nDeseja salvar a chave mesmo assim?",
        ).run()
        return save_anyway
    else:
        error_msg = (
            result.message[:400] if len(result.message) > 400 else result.message
        )
        save_anyway = yes_no_dialog(
            title="▲ Validação Falhou",
            text=f"{error_msg}\n\nDeseja salvar a chave mesmo assim?",
        ).run()
        return save_anyway


def _model_menu_params(config: Any) -> None:
    """Handle LLM parameter configuration sub-menu."""
    while True:
        temp = config.get("temperature") or 0.7
        tokens = config.get("max_tokens") or 4096
        prompt = config.get("system_prompt") or "Padrão"
        param = radiolist_dialog(
            title="⚙️  Parâmetros do LLM",
            text="Configure parâmetros de geração:",
            values=[
                ("temp", f"🌡️ Temperatura      [{temp}]"),
                ("tokens", f"📏 Máx. tokens      [{tokens}]"),
                ("prompt", f"📝 Prompt de sistema [{prompt[:20]}...]"),
                ("back", "←  Voltar"),
            ],
        ).run()
        if param is None or param == "back":
            break
        if param == "temp":
            val = input_dialog(
                title="🌡️ Temperatura",
                text="Criatividade (0.0 = Preciso, 2.0 = Criativo):",
                default=str(temp),
            ).run()
            if val:
                try:
                    config.set("temperature", float(val))
                except ValueError as _e:
                    logger.debug(f"Ignorado: {_e}")
        elif param == "tokens":
            val = input_dialog(
                title="📏 Máximo de tokens",
                text="Limite de tokens na resposta:",
                default=str(tokens),
            ).run()
            if val:
                try:
                    config.set("max_tokens", int(val))
                except ValueError as _e:
                    logger.debug(f"Ignorado: {_e}")
        elif param == "prompt":
            val = input_dialog(
                title="📝 Prompt de sistema",
                text="Prompt de sistema global (deixe vazio para padrão):",
                default=config.get("system_prompt") or "",
            ).run()
            if val is not None:
                config.set("system_prompt", val if val.strip() else None)


def _handle_model_menu() -> None:
    """Handle model selection menu."""
    from aura_cli.cli.command_processor import handle_model
    from aura_cli.core.config import get_config_manager

    config = get_config_manager()
    raw_model = config.get("default_model") or ""
    current_model = (
        format_model_display_name(resolve_model_option(raw_model))
        if raw_model
        else "Não configurado"
    )

    model_menu = radiolist_dialog(
        title="Aura  /  Modelo",
        text=(f"Atual · {current_model}\n↑↓ navegar   Enter abrir   Esc voltar"),
        values=[
            ("select", "Escolher no catálogo"),
            ("manual", "Usar identificador manual"),
            ("params", "Parâmetros de geração"),
            ("back", "Voltar às configurações"),
        ],
    ).run()

    if model_menu is None or model_menu == "back":
        return

    if model_menu == "select":
        handle_model(current_model)
    elif model_menu == "manual":
        model = input_dialog(
            title="Aura  /  Modelo manual",
            text=f"Identificador do modelo\nExemplo: {DEFAULT_MODEL}",
        ).run()
        if model:
            canonical_model = resolve_model_option(model)
            config.set("default_model", canonical_model)
            message_dialog(
                title="✓ Sucesso",
                text=f"Modelo padrão configurado: {canonical_model}",
            ).run()
    elif model_menu == "params":
        _model_menu_params(config)


def _fallback_set_key(provider: str, env_keys: list, label: str) -> None:
    """Prompt for API key and save it (fallback console mode)."""
    clear_api_key(provider)
    api_key = console.input(f"[bold]Digite sua {label} API Key:[/bold] ").strip()
    if not api_key:
        return
    secure_config_manager.set_api_key(provider, api_key)
    for env_key in env_keys:
        os.environ.pop(env_key, None)
    saved_key = secure_config_manager.get_api_key(provider)
    if saved_key == api_key:
        console.print(
            f"[{UIStyles.SUCCESS}]✓ {label} API Key configurada e verificada![/]"
        )
    else:
        console.print(f"[{UIStyles.WARNING}]⚠ Chave salva, mas verificação falhou.[/]")


def _show_settings_fallback() -> None:
    """Fallback to table-based settings menu if TUI is not available."""
    from rich.table import Table

    from aura_cli.core.config import get_config_manager

    config = get_config_manager()

    title_style = UIStyles.safe_style("TITLE", "bold white")
    border_style = UIStyles.safe_style("BORDER_PRIMARY", "cyan")
    primary_style = UIStyles.safe_style("PRIMARY", "cyan")
    body_style = UIStyles.safe_style("BODY", "white")

    api_keys = get_api_keys_dict()

    def _st(k: str) -> str:
        return "✓ Configurada" if api_keys.get(k) else "✗ Não configurada"

    raw_model = config.get("default_model") or ""
    current_model = (
        format_model_display_name(resolve_model_option(raw_model))
        if raw_model
        else "Não configurado"
    )

    table = Table(
        title=f"[{title_style}]{UIIcons.INFO} Menu de Configurações[/{title_style}]",
        show_header=True,
        header_style=title_style,
        border_style=border_style,
        title_style=title_style,
    )
    table.add_column("Opção", style=primary_style + " bold", width=8, justify="center")
    table.add_column("Ação", style=body_style, width=35)
    table.add_column("Status", style=body_style, ratio=1)
    table.add_row("1", "Configurar Google API Key (Gemini)", _st("GOOGLE_API_KEY"))
    table.add_row("2", "Configurar Cerebras API Key", _st("CEREBRAS_API_KEY"))
    table.add_row("3", "Configurar OpenRouter API Key", _st("OPENROUTER_API_KEY"))
    table.add_row("4", "Configurar OpenAI API Key (GPT)", _st("OPENAI_API_KEY"))
    table.add_row(
        "5", "Configurar Anthropic API Key (Claude)", _st("ANTHROPIC_API_KEY")
    )
    table.add_row("6", "Configurar NVIDIA API Key", _st("NVIDIA_API_KEY"))
    table.add_row("7", "Configurar Groq API Key", _st("GROQ_API_KEY"))
    table.add_row("8", "Configurar modelo padrão", current_model[:30])
    table.add_row("9", "Limpar todas as chaves (reset)", "")
    table.add_row("10", "Voltar", "")

    console.print()
    console.print(table)
    console.print()
    choice = console.input(
        f"[{primary_style} bold]Escolha uma opção (1-9):[/{primary_style} bold] "
    ).strip()

    if choice == "1":
        _fallback_set_key("google", ["GOOGLE_API_KEY", "GEMINI_API_KEY"], "Google")
    elif choice == "2":
        _fallback_set_key("cerebras", ["CEREBRAS_API_KEY"], "Cerebras")
    elif choice == "3":
        _fallback_set_key("openrouter", ["OPENROUTER_API_KEY"], "OpenRouter")
    elif choice == "4":
        _fallback_set_key("openai", ["OPENAI_API_KEY"], "OpenAI")
    elif choice == "5":
        _fallback_set_key("anthropic", ["ANTHROPIC_API_KEY"], "Anthropic")
    elif choice == "6":
        _fallback_set_key("nvidia", ["NVIDIA_API_KEY"], "NVIDIA")
    elif choice == "7":
        _fallback_set_key("groq", ["GROQ_API_KEY"], "Groq")
    elif choice == "8":
        model = console.input(
            f"[bold]Digite o modelo padrão (ex: {DEFAULT_MODEL}):[/bold] "
        ).strip()
        if model:
            canonical_model = resolve_model_option(model)
            config.set("default_model", canonical_model)
            console.print(
                f"[{UIStyles.SUCCESS}]✓ Modelo padrão configurado: {canonical_model}[/]"
            )
    elif choice == "9":
        if (
            console.input(
                "[bold yellow]Tem certeza que deseja remover TODAS as chaves? (s/N):[/bold yellow] "
            )
            .strip()
            .lower()
            == "s"
        ):
            for p in [
                "google",
                "cerebras",
                "openrouter",
                "openai",
                "anthropic",
                "nvidia",
                "groq",
            ]:
                clear_api_key(p)
            console.print(f"[{UIStyles.SUCCESS}]✓ Todas as chaves removidas![/]")
    elif choice == "10":
        return
    else:
        console.print(f"[{UIStyles.ERROR}]Opção inválida![/]")
