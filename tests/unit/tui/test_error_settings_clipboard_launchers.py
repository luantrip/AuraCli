from types import SimpleNamespace
from unittest.mock import patch

from aura_cli.tui.core.error_handler import TUIErrorHandler
from aura_cli.tui.tools import launch_files, launch_paint
from aura_cli.tui.tools.file_manager.components.file_browser import FileBrowser


def test_error_handler_accepts_notify_alias_and_callback() -> None:
    notifications: list[tuple[str, str]] = []
    app = SimpleNamespace(notify=lambda *args, **kwargs: None)
    handler = TUIErrorHandler(app)

    info = handler.handle_error(
        ValueError("synthetic failure"),
        context="test",
        notify=True,
        notify_callback=lambda message, severity="error": notifications.append(
            (message, severity)
        ),
    )

    assert info.handled is True
    assert notifications == [("ValueError: synthetic failure", "error")]


def test_files_launcher_returns_failure_when_tuifi_is_missing(monkeypatch) -> None:
    import aura_cli.tui.tools as tools

    monkeypatch.setattr(tools, "TUIFI_AVAILABLE", False)
    with patch("builtins.print") as output:
        assert launch_files() == 1
    output.assert_called_once()


def test_paint_launcher_uses_active_python_interpreter() -> None:
    with patch("subprocess.run") as run:
        run.return_value.returncode = 0
        assert launch_paint("art.ansi") == 0

    command = run.call_args.args[0]
    import sys

    assert command == [sys.executable, "-m", "aura_cli.tui.tools.paint", "art.ansi"]


def test_file_browser_clipboard_failure_is_not_reported_as_success() -> None:
    notifications: list[tuple[str, str]] = []
    browser = SimpleNamespace(
        notify=lambda message, **kwargs: notifications.append(
            (message, kwargs.get("severity", "information"))
        )
    )

    with patch(
        "aura_cli.tui.tools.file_manager.components.file_browser.subprocess.run",
        side_effect=OSError("clipboard unavailable"),
    ):
        assert FileBrowser._copy_to_clipboard(browser, "SECRET_SENTINEL") is False

    assert notifications
    assert notifications[0][1] == "error"
    assert "copiado" not in notifications[0][0].lower()
