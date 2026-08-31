from queue import Queue
from types import SimpleNamespace

from rich.console import Console

from aura_cli.cli.ui import input as input_module
from aura_cli.cli.ui.input import InputManager


def _manager(queue=None) -> InputManager:
    return InputManager(
        Console(record=True, width=60),
        SimpleNamespace(skip_confirmations=True),
        status_queue=queue,
    )


def test_large_input_preview_avoids_implicit_blank_lines() -> None:
    manager = _manager()
    content = "\n".join(f"linha {index}" for index in range(12))

    manager._handle_large_input(content)
    output = manager.console.export_text(clear=False)

    assert "Entrada #1" in output
    assert "12 linhas" in output
    assert not output.startswith("\n")


def test_large_input_event_metadata_is_localized() -> None:
    queue = Queue()
    manager = _manager(queue)
    content = "\n".join(f"linha {index}" for index in range(12))

    manager._notify_status_queue(content, is_large=True)
    event = queue.get_nowait()

    assert event["data"]["metadata"]["is_large_input"] is True
    assert "linhas" in event["data"]["metadata"]["stats"]
    assert "lines" not in event["data"]["metadata"]["stats"]


def test_prompt_fallback_uses_layout_symbol_and_strips_only_newlines(
    monkeypatch,
) -> None:
    manager = _manager()
    monkeypatch.setattr(input_module, "PROMPT_TOOLKIT_AVAILABLE", False)
    monkeypatch.setattr(input_module.Prompt, "ask", lambda _prompt: "  comando  ")

    assert manager.prompt() == "  comando  "
