import json

import pytest

from aura_cli.core.sessions.external_discovery import (
    ExternalSessionDiscoveryError,
    discover_external_sessions,
    resolve_external_reference,
)


def test_discovers_grok_summary_and_resolves_prefix(tmp_path) -> None:
    root = tmp_path / "grok" / "encoded" / "session"
    root.mkdir(parents=True)
    (root / "summary.json").write_text(
        json.dumps(
            {
                "info": {"id": "01abc", "cwd": "/project"},
                "generated_title": "Plan",
                "current_model_id": "grok-4.7",
            }
        ),
        encoding="utf-8",
    )

    candidates = discover_external_sessions("grok", roots=[tmp_path / "grok"])

    assert candidates[0].session_id == "01abc"
    assert candidates[0].path == root


def test_codex_discovery_reports_ambiguous_prefix(tmp_path, monkeypatch) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    for suffix in ("one", "two"):
        path = root / f"rollout-{suffix}.jsonl"
        path.write_text(json.dumps({"thread_id": f"abc-{suffix}"}) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        "aura_cli.core.sessions.external_discovery._default_roots", lambda _provider: [root]
    )

    with pytest.raises(ExternalSessionDiscoveryError, match="ambígua"):
        resolve_external_reference("codex:abc")


def test_unknown_provider_has_no_discovery(tmp_path) -> None:
    assert discover_external_sessions("claude", roots=[tmp_path]) == []
