import json

from aura_cli.core.sessions.external_import import preview_external_session


def test_preview_flags_workspace_and_model_divergence(tmp_path) -> None:
    source = tmp_path / "session.jsonl"
    source.write_text(
        json.dumps(
            {
                "cwd": "/other/project",
                "model": "external-model",
                "role": "user",
                "content": "Oi",
            }
        ),
        encoding="utf-8",
    )

    preview = preview_external_session(
        str(source),
        workspace_root=tmp_path / "workspace",
        active_model="local-model",
    )

    assert preview.message_count == 1
    assert preview.requires_confirmation is True
    assert "workspace externo" in preview.divergence_reasons[0]
    assert "modelo externo" in preview.divergence_reasons[1]


def test_preview_does_not_require_confirmation_when_context_matches(tmp_path) -> None:
    source = tmp_path / "session.jsonl"
    source.write_text(
        json.dumps(
            {
                "cwd": str(tmp_path),
                "model": "local-model",
                "role": "user",
                "content": "Oi",
            }
        ),
        encoding="utf-8",
    )

    preview = preview_external_session(
        str(source), workspace_root=tmp_path, active_model="local-model"
    )

    assert preview.requires_confirmation is False


def test_preview_requires_confirmation_for_unverified_external_policy(tmp_path) -> None:
    source = tmp_path / "grok"
    source.mkdir()
    (source / "updates.jsonl").write_text(
        json.dumps({"role": "user", "content": "Oi"}), encoding="utf-8"
    )
    (source / "summary.json").write_text(
        json.dumps(
            {
                "info": {"cwd": str(tmp_path)},
                "sandbox_profile": "off",
            }
        ),
        encoding="utf-8",
    )

    preview = preview_external_session(
        str(source), workspace_root=tmp_path, active_model=""
    )

    assert preview.policy_summary == {"sandbox_profile": "off"}
    assert preview.requires_confirmation is True
