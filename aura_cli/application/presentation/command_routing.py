"""Presentation command classification without framework dependencies."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar


class PresentationCommandAction(Enum):
    CLEAR = "clear"
    HELP = "help"
    SHORTCUTS = "shortcuts"
    BACK = "back"
    CONSOLIDATE = "consolidate"
    WELCOME = "welcome"
    HISTORY = "history"
    EXIT = "exit"
    TOOLS = "tools"
    CONSTITUTION = "constitution"
    SETTINGS = "settings"
    SESSIONS = "sessions"
    CONTEXT = "context"
    FILES = "files"
    TODO = "todo"
    MODEL = "model"
    PASSTHROUGH = "passthrough"
    UNHANDLED = "unhandled"


class PresentationCommandRouter:
    """Classify local presentation commands and complex-work intent."""

    _PASSTHROUGH_PREFIXES = (
        "/todo ",
        "/model",
        "/auto-run",
        "/autorun",
        "/checkpoint",
        "/tangent",
        "/cache",
        "/config",
    )
    _COMMANDS: ClassVar[dict[str, PresentationCommandAction]] = {
        "/clear": PresentationCommandAction.CLEAR,
        "/cls": PresentationCommandAction.CLEAR,
        "/help": PresentationCommandAction.HELP,
        "/?": PresentationCommandAction.HELP,
        "/keyboard": PresentationCommandAction.SHORTCUTS,
        "/keys": PresentationCommandAction.SHORTCUTS,
        "/shortcuts": PresentationCommandAction.SHORTCUTS,
        "/back": PresentationCommandAction.BACK,
        "/legacy": PresentationCommandAction.BACK,
        "/cli": PresentationCommandAction.BACK,
        "/consolidate": PresentationCommandAction.CONSOLIDATE,
        "/welcome": PresentationCommandAction.WELCOME,
        "/history": PresentationCommandAction.HISTORY,
        "/exit": PresentationCommandAction.EXIT,
        "/quit": PresentationCommandAction.EXIT,
        "/tools-menu": PresentationCommandAction.TOOLS,
        "/tools": PresentationCommandAction.TOOLS,
        "/constitution": PresentationCommandAction.CONSTITUTION,
        "/constituicao": PresentationCommandAction.CONSTITUTION,
        "/settings": PresentationCommandAction.SETTINGS,
        "/sessions": PresentationCommandAction.SESSIONS,
        "/session-history": PresentationCommandAction.SESSIONS,
        "/context": PresentationCommandAction.CONTEXT,
        "/files": PresentationCommandAction.FILES,
        "/todo": PresentationCommandAction.TODO,
    }

    def classify_command(self, command: str) -> PresentationCommandAction:
        normalized = command.casefold().strip()
        exact = self._COMMANDS.get(normalized)
        if exact is not None:
            return exact
        if normalized == "/model" or normalized.startswith("/model "):
            return PresentationCommandAction.MODEL
        if any(
            normalized == prefix.strip() or normalized.startswith(prefix)
            for prefix in self._PASSTHROUGH_PREFIXES
        ):
            return PresentationCommandAction.PASSTHROUGH
        return PresentationCommandAction.UNHANDLED

    def should_use_agi_worker(self, command: str) -> bool:
        normalized = command.casefold().strip()
        if normalized.startswith(("/agi", "/ops")):
            return False
        action_prefixes = (
            "crie",
            "implemente",
            "construa",
            "refatore",
            "desenvolva",
            "gere",
            "projete",
            "build",
            "create",
            "implement",
            "refactor",
            "develop",
        )
        if normalized.startswith(action_prefixes):
            return True
        domain_terms = (
            "api",
            "endpoint",
            "database",
            "migration",
            "docker",
            "deploy",
            "arquitetura",
            "microservice",
            "pipeline",
            "refatoração",
            "implementação",
            "serviço",
            "módulo",
            "authentication",
            "crud",
            "schema",
            "middleware",
        )
        return (
            len(command) > 150 and sum(term in normalized for term in domain_terms) >= 3
        )


__all__ = ["PresentationCommandAction", "PresentationCommandRouter"]
