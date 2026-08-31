"""Tests for the widget-independent Paint document service."""

from unittest.mock import Mock

from aura_cli.application.paint import PaintDocumentService


def test_document_service_saves_without_importing_tui(tmp_path) -> None:
    document = Mock(width=10, height=5)
    document.encode_to_format.return_value = b"ansi"
    service = PaintDocumentService(document)

    result = service.save(tmp_path / "art.ans", "ans")

    assert result["success"] is True
    assert (tmp_path / "art.ans").read_bytes() == b"ansi"
    document.encode_to_format.assert_called_once_with("ANSI")


def test_document_service_fails_explicitly_without_document(tmp_path) -> None:
    result = PaintDocumentService().save(tmp_path / "art.ans")

    assert result == {"success": False, "error": "Paint document is unavailable"}


def test_paint_hosts_do_not_share_mutable_editor_state() -> None:
    from aura_cli.tui.tools.paint.paint import Paint

    first = Paint()
    second = Paint()

    first.undos.append(object())
    first.tool_points.append(object())

    assert second.undos == []
    assert second.tool_points == []
    assert first.background_tasks is not second.background_tasks
