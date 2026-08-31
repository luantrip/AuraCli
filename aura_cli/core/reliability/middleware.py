"""Composable request middleware chain inspired by notebooklm-py."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Request:
    method: str
    target: str
    headers: dict[str, str] = field(default_factory=dict)
    payload: Any = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    status: int
    payload: Any = None
    headers: dict[str, str] = field(default_factory=dict)


class MiddlewareChain:
    """Run request middleware in registration order and unwind responses."""

    def __init__(self, transport: Callable[[Request], Response]) -> None:
        self.transport = transport
        self._middleware: list[Callable] = []

    def add(self, middleware: Callable) -> MiddlewareChain:
        self._middleware.append(middleware)
        return self

    def send(self, request: Request) -> Response:
        def invoke(index: int, current: Request) -> Response:
            if index == len(self._middleware):
                return self.transport(current)
            return self._middleware[index](current, lambda next_request: invoke(index + 1, next_request))

        return invoke(0, request)
