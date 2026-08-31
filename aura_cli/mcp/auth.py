"""Optional bearer-token gate for non-stdio MCP transports."""

from __future__ import annotations

import hmac
import os


def authorize(token: str | None) -> bool:
    expected = os.environ.get("AURA_MCP_TOKEN")
    return not expected or bool(token and hmac.compare_digest(token, expected))
