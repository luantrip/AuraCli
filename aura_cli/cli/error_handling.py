"""Rich CLI reactions to provider, credential and rate-limit failures."""

import re
from typing import Any, Optional, Tuple

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def handle_rate_limit_error(
    error: Exception, retry_after: Optional[int] = None, model: str = ""
) -> str:
    """Handle rate limit errors and return user-friendly message.

    Args:
        error: The exception that occurred
        retry_after: Optional retry delay in seconds
        model: Current model name

    Returns:
        User-friendly error message
    """
    retry_msg = ""
    effective_retry = retry_after or getattr(error, "retry_after", None)
    if effective_retry:
        minutes = effective_retry // 60
        seconds = effective_retry % 60
        if minutes > 0:
            retry_msg = (
                f"\n{UIIcons.CLOCK}  Tente novamente em ~{minutes}min {seconds}s"
            )
        else:
            retry_msg = f"\n{UIIcons.CLOCK}  Tente novamente em ~{seconds}s"

    error_model = getattr(error, "model", None) or model or "current model"
    error_str = str(error).lower()
    is_free_tier = "free_tier" in error_str or "free tier" in error_str

    if is_free_tier:
        return (
            f"{UIIcons.WARNING} [{UIStyles.WARNING}]Quota do Plano Gratuito Excedida[/]\n\n"
            f"Limite diário do plano gratuito do Gemini (20 req/dia).{retry_msg}\n\n"
            f"{UIIcons.INFO} [{UIStyles.MUTED}]Tente: aguardar 24h, /settings (outro provedor) ou upgrade em ai.google.dev/pricing[/]"
        )
    return (
        f"{UIIcons.WARNING} [{UIStyles.WARNING}]Limite de uso atingido[/]\n\n"
        f"Limite de requisições da API ({error_model}).{retry_msg}\n\n"
        f"{UIIcons.INFO} [{UIStyles.MUTED}]Tente: aguardar alguns minutos, /model ou /settings[/]"
    )


def detect_provider_from_error(error_str: str) -> str:
    """Detect provider from error message.

    Args:
        error_str: Lowercase error message string

    Returns:
        Provider name (google, openai, anthropic, or unknown)
    """
    if "gemini" in error_str or "google" in error_str:
        return "google"
    elif "openai" in error_str or "gpt" in error_str:
        return "openai"
    elif "anthropic" in error_str or "claude" in error_str:
        return "anthropic"
    return "unknown"


def handle_api_key_error(
    error: Exception, error_str: str, is_leaked: bool = False, ui: Any = None
) -> Tuple[str, None]:
    """Handle API key errors and return user-friendly message.

    Args:
        error: The exception that occurred
        error_str: Lowercase error message string
        is_leaked: Whether the key was reported as leaked
        ui: Optional UI manager for notifications

    Returns:
        Tuple of (response_content, None)
    """
    from aura_cli.core.error_handler import get_error_handler
    from aura_cli.core.exceptions import APIKeyError

    error_handler = get_error_handler()
    provider = detect_provider_from_error(error_str)

    if is_leaked:
        try:
            import os

            import keyring

            from aura_cli.core.secure_config import secure_config_manager

            try:
                keyring.delete_password("aura_cli", "google_api_key")
            except Exception as e:
                logger.warning(f"Failed to remove key from keyring: {e}")

            try:
                secure_config_manager.delete_api_key("google")
            except Exception as e:
                logger.warning(f"Failed to remove key from SecureConfig: {e}")

            for env_key in ["GOOGLE_API_KEY", "GEMINI_API_KEY"]:
                if env_key in os.environ:
                    del os.environ[env_key]

            logger.info("Chave vazada removida automaticamente")
        except Exception as e:
            logger.warning(f"Failed to remove leaked key: {e}")

    api_key_error = APIKeyError(
        message="Chave de API vazada" if is_leaked else "Erro de chave de API",
        provider=provider,
        details=str(error),
    )

    notify_cb = None
    if ui:

        def notify_cb(msg, severity="error"):
            return ui.display_error(msg)

    error_handler.handle_error(
        api_key_error,
        context="app_loop:error_handling",
        log=True,
        notify=True,
        notify_callback=notify_cb,
    )

    if is_leaked:
        response_content = (
            f"{UIIcons.WARNING} [{UIStyles.ERROR}]Problema com sua chave de API[/]\n\n"
            "Sua chave de API do Gemini foi reportada como vazada e foi desativada por segurança.\n\n"
            f"{UIIcons.EDIT} [{UIStyles.TITLE}]O que fazer:[/]\n"
            "  1. Acesse /settings para configurar uma nova chave\n"
            "  2. Obtenha uma nova chave em: https://makersuite.google.com/app/apikey\n"
            "  3. Ou use outro provedor (GPT, Claude) configurando suas chaves\n"
            "  4. Consulte os provedores disponíveis com /model\n\n"
            f"{UIIcons.INFO} [{UIStyles.MUTED}]Dica: Mantenha suas chaves de API seguras e nunca as compartilhe publicamente.[/]"
        )
    else:
        response_content = (
            f"{UIIcons.WARNING} [{UIStyles.ERROR}]Erro de autenticação[/]\n\n"
            "Sua chave de API foi rejeitada ou não está configurada corretamente.\n\n"
            f"{UIIcons.EDIT} [{UIStyles.TITLE}]O que fazer:[/]\n"
            "  1. Acesse /settings para verificar suas chaves\n"
            "  2. Verifique se a chave está correta e ativa\n"
            "  3. Tente usar outro modelo: /model\n"
            "  4. Consulte os provedores disponíveis com /model\n\n"
            f"{UIIcons.INFO} [{UIStyles.MUTED}]Need help? Type /help to see all commands.[/]"
        )

    return response_content, None


def handle_llm_errors(error: Exception, current_model: str, ui: Any = None) -> None:
    """Handle LLM-related errors during query processing.

    Args:
        error: The exception that occurred
        current_model: Model name that was being used
        ui: Optional UI manager
    """
    from aura_cli.core.error_handler import get_error_handler
    from aura_cli.core.exceptions import LLMError

    error_handler = get_error_handler()
    error_str = str(error).lower()

    if hasattr(error, "response") and error.response is not None:
        try:
            error_body = error.response.text or str(error.response.content)
            logger.error(f"LLM API Error Body: {error_body}")
        except Exception as e:
            logger.debug(f"Não foi possível ler error body: {e}")

    if (
        "api key" in error_str
        or "403" in error_str
        or "permission_denied" in error_str
        or "leaked" in error_str
    ):
        is_leaked = "leaked" in error_str
        handle_api_key_error(error, error_str, is_leaked, ui=ui)
    else:
        llm_error = LLMError(
            message=f"LLM error: {error!s}",
            details=f"model={current_model}",
            context={"model": current_model, "error_type": type(error).__name__},
        )
        error_handler.handle_error(
            llm_error,
            context="app_loop:llm_query",
            log=True,
            notify=False,
        )
        raise


def handle_rate_limit_in_exception(
    error: Exception, model: str, ui: Any = None
) -> bool:
    """Handle rate limit errors detected in generic exception handler.

    Args:
        error: The exception that occurred
        model: Current model
        ui: Optional UI manager

    Returns:
        True if rate limit was handled, False otherwise
    """
    from aura_cli.cli.utils.exceptions import RateLimitError
    from aura_cli.core.error_handler import get_error_handler

    error_handler = get_error_handler()
    error_str = str(error).lower()

    if not any(
        x in error_str
        for x in ["429", "rate limit", "quota", "exceeded", "resource_exhausted"]
    ):
        return False

    retry_match = re.search(r"retry.*?(\d+)", error_str)
    retry_after = int(retry_match.group(1)) if retry_match else None

    rate_limit_error = RateLimitError(
        message="Limite de taxa excedido",
        model=model,
        retry_after=retry_after,
    )

    notify_cb = None
    if ui:

        def notify_cb(msg, severity="error"):
            return ui.display_error(msg)

    error_handler.handle_error(
        rate_limit_error,
        context="app_loop:main_loop",
        log=True,
        notify=True,
        notify_callback=notify_cb,
    )
    return True


def handle_generic_exception(error: Exception, model: str, ui: Any = None) -> None:
    """Handle generic exceptions in main loop.

    Args:
        error: The exception that occurred
        model: Current model
        ui: Optional UI manager
    """
    from aura_cli.core.error_handler import get_error_handler

    error_handler = get_error_handler()
    error_str = str(error).lower()

    if handle_rate_limit_in_exception(error, model, ui):
        return

    if (
        "api key" in error_str
        or "403" in error_str
        or "permission_denied" in error_str
        or "leaked" in error_str
    ):
        is_leaked = "leaked" in error_str
        error_msg, _ = handle_api_key_error(error, error_str, is_leaked, ui=ui)
        if ui:
            ui.display_error(error_msg)
        return

    if "'Console' object has no attribute" in str(error):
        if ui:
            ui.display_error(
                f"{UIIcons.WARNING} [{UIStyles.WARNING}]Erro interno de renderização[/]\n\n"
                "Problema ao exibir informações na tela.\n\n"
                f"{UIIcons.INFO} [{UIStyles.MUTED}]Tente: redimensionar o terminal ou reiniciar o Aura CLI[/]"
            )
        return

    if "name 'logger' is not defined" in str(error):
        if ui:
            ui.display_error(
                f"{UIIcons.WARNING} [{UIStyles.WARNING}]Erro interno[/]\n\nErro inesperado no sistema.\n\n"
                f"{UIIcons.INFO} [{UIStyles.MUTED}]Tente: reiniciar o Aura CLI[/]"
            )
        return

    notify_cb = None
    if ui:

        def notify_cb(msg, severity="error"):
            return ui.display_error(
                f"{UIIcons.WARNING} [{UIStyles.WARNING}]Erro inesperado[/]\n\n{msg}\n\n"
                f"{UIIcons.INFO} [{UIStyles.MUTED}]Tente: reiniciar o Aura CLI ou ver logs em ~/.aura/logs/[/]"
            )

    error_handler.handle_error(
        error,
        context="app_loop:main_loop",
        log=True,
        notify=True,
        notify_callback=notify_cb,
    )
