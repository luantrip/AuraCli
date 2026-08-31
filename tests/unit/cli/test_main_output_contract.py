import json

from aura_cli.cli.main import _format_output, _should_emit_progress


def test_machine_readable_output_never_shares_human_progress() -> None:
    assert _should_emit_progress("json", quiet=False) is False
    assert _should_emit_progress("yaml", quiet=False) is False
    assert _should_emit_progress("text", quiet=False) is True
    assert _should_emit_progress("text", quiet=True) is False


def test_json_output_is_plain_stdout(capsys) -> None:
    _format_output({"status": "completed", "message": "ok"}, "json")

    output = capsys.readouterr().out
    assert json.loads(output) == {"status": "completed", "message": "ok"}
    assert "✔" not in output
    assert "Status:" not in output
