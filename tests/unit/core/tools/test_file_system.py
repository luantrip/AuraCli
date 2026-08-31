"""Tests for core/tools/file_system.py — covering uncovered branches."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _silence_ui():
    """Suppress Rich/UI output in all tests."""
    with (
        patch("aura_cli.core.ui.display_tool_call", return_value=None, create=True),
        patch("rich.console.Console.print", return_value=None),
    ):
        yield


# ---------------------------------------------------------------------------
# _sanitize_path
# ---------------------------------------------------------------------------


class TestSanitizePath:
    def setup_method(self):
        from aura_cli.core.tools.file_system import enable_path_validation

        enable_path_validation(True)

    def test_null_byte_raises(self, tmp_path):
        from aura_cli.core.tools.file_system import _sanitize_path, set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        with pytest.raises(ValueError, match="null bytes"):
            _sanitize_path("fi\x00le.txt")

    def test_absolute_path_outside_base_blocked(self, tmp_path):
        from aura_cli.core.tools.file_system import _sanitize_path, set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        with pytest.raises(ValueError):
            _sanitize_path("/etc/passwd", base_dir=tmp_path)

    def test_valid_absolute_path_within_base(self, tmp_path):
        from aura_cli.core.tools.file_system import _sanitize_path, set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        target = tmp_path / "file.txt"
        result = _sanitize_path(str(target), base_dir=tmp_path)
        assert str(result).startswith(str(tmp_path))

    def test_validation_disabled_allows_outside(self, tmp_path):
        from aura_cli.core.tools.file_system import (
            _sanitize_path,
            enable_path_validation,
            set_allowed_base_dir,
        )

        set_allowed_base_dir(str(tmp_path))
        enable_path_validation(False)
        try:
            result = _sanitize_path("/tmp/anywhere.txt")
            # macOS resolves /tmp → /private/tmp; just verify no ValueError raised
            assert "anywhere.txt" in str(result)
        finally:
            enable_path_validation(True)


class TestIsPathSafe:
    def test_safe_path(self, tmp_path):
        from aura_cli.core.tools.file_system import (
            enable_path_validation,
            is_path_safe,
            set_allowed_base_dir,
        )

        enable_path_validation(True)
        set_allowed_base_dir(str(tmp_path))
        assert is_path_safe(str(tmp_path / "file.txt"), base_dir=tmp_path) is True

    def test_outside_base_not_safe(self, tmp_path):
        from aura_cli.core.tools.file_system import (
            enable_path_validation,
            is_path_safe,
            set_allowed_base_dir,
        )

        enable_path_validation(True)
        set_allowed_base_dir(str(tmp_path))
        assert is_path_safe("/etc/passwd", base_dir=tmp_path) is False


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


class TestReadFile:
    def test_reads_full_file(self, tmp_path):
        from aura_cli.core.tools.file_system import read_file

        f = tmp_path / "a.txt"
        f.write_text("hello world")
        with patch("aura_cli.core.tools.file_system._sanitize_path", return_value=f):
            result = read_file(str(f))
        assert "hello world" in result

    def test_reads_with_offset_and_limit(self, tmp_path):
        from aura_cli.core.tools.file_system import read_file

        f = tmp_path / "lines.txt"
        f.write_text("line1\nline2\nline3\nline4\n")
        with patch("aura_cli.core.tools.file_system._sanitize_path", return_value=f):
            result = read_file(str(f), offset=1, limit=2)
        assert "line2" in result
        assert "line4" not in result

    def test_file_not_found_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import read_file

        missing = tmp_path / "missing.txt"
        with patch(
            "aura_cli.core.tools.file_system._sanitize_path", return_value=missing
        ):
            result = read_file(str(missing))
        assert "erro" in result.lower()

    def test_permission_error_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import read_file

        with (
            patch(
                "aura_cli.core.tools.file_system._sanitize_path",
                return_value=tmp_path / "f.txt",
            ),
            patch("builtins.open", side_effect=PermissionError("denied")),
        ):
            result = read_file("secret.txt")
        assert "erro" in result.lower()

    def test_is_directory_error_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import read_file

        with (
            patch(
                "aura_cli.core.tools.file_system._sanitize_path", return_value=tmp_path
            ),
            patch("builtins.open", side_effect=IsADirectoryError()),
        ):
            result = read_file(str(tmp_path))
        assert "erro" in result.lower()

    def test_unicode_error_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import read_file

        with (
            patch(
                "aura_cli.core.tools.file_system._sanitize_path",
                return_value=tmp_path / "binary.bin",
            ),
            patch(
                "builtins.open",
                side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "reason"),
            ),
        ):
            result = read_file("binary.bin")
        assert "erro" in result.lower()

    def test_path_traversal_returns_error(self):
        from aura_cli.core.tools.file_system import read_file

        with patch(
            "aura_cli.core.tools.file_system._sanitize_path",
            side_effect=ValueError("outside allowed directory"),
        ):
            result = read_file("../../etc/passwd")
        assert "erro" in result.lower()

    def test_os_error_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import read_file

        with (
            patch(
                "aura_cli.core.tools.file_system._sanitize_path",
                return_value=tmp_path / "f.txt",
            ),
            patch("builtins.open", side_effect=OSError("disk error")),
        ):
            result = read_file("f.txt")
        assert "erro" in result.lower()


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------


class TestListDirectory:
    def test_lists_files_and_dirs(self, tmp_path):
        from aura_cli.core.tools.file_system import list_directory

        (tmp_path / "file.txt").write_text("x")
        (tmp_path / "subdir").mkdir()
        result = list_directory(str(tmp_path))
        assert "file.txt" in result
        assert "subdir" in result

    def test_missing_directory_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import list_directory

        result = list_directory(str(tmp_path / "nonexistent"))
        assert "erro" in result.lower() or "não encontrado" in result.lower()

    def test_file_path_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import list_directory

        f = tmp_path / "f.txt"
        f.write_text("x")
        result = list_directory(str(f))
        assert "erro" in result.lower() or "não é um diretório" in result.lower()

    def test_empty_directory(self, tmp_path):
        from aura_cli.core.tools.file_system import list_directory

        empty = tmp_path / "empty"
        empty.mkdir()
        result = list_directory(str(empty))
        # Either "empty"/"vazio" message or just no files listed — not an error
        assert "erro" not in result.lower()

    def test_hidden_files_excluded_by_default(self, tmp_path):
        from aura_cli.core.tools.file_system import list_directory

        (tmp_path / ".hidden").write_text("x")
        (tmp_path / "visible.txt").write_text("x")
        result = list_directory(str(tmp_path))
        assert ".hidden" not in result
        assert "visible.txt" in result

    def test_hidden_files_included_when_requested(self, tmp_path):
        from aura_cli.core.tools.file_system import list_directory

        (tmp_path / ".hidden").write_text("x")
        result = list_directory(str(tmp_path), show_hidden=True)
        assert ".hidden" in result

    def test_permission_error_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import list_directory

        d = tmp_path / "locked"
        d.mkdir()
        with patch("pathlib.Path.iterdir", side_effect=PermissionError("no access")):
            result = list_directory(str(d))
        assert "erro" in result.lower() or "permiss" in result.lower()


# ---------------------------------------------------------------------------
# find_directory
# ---------------------------------------------------------------------------


class TestFindDirectory:
    def test_finds_in_start_path(self, tmp_path):
        from aura_cli.core.tools.file_system import (
            find_directory,
            set_allowed_base_dir,
        )

        set_allowed_base_dir(str(tmp_path))
        target = tmp_path / "mydir"
        target.mkdir()
        result = find_directory("mydir", str(tmp_path))
        assert "mydir" in result

    def test_default_search_uses_allowed_workspace(self, tmp_path):
        from aura_cli.core.tools.file_system import (
            find_directory,
            set_allowed_base_dir,
        )

        set_allowed_base_dir(str(tmp_path))
        (tmp_path / "nested" / "mydir").mkdir(parents=True)

        assert find_directory("mydir") == "nested/mydir"

    def test_outside_start_path_is_rejected(self, tmp_path):
        from aura_cli.core.tools.file_system import (
            enable_path_validation,
            find_directory,
            set_allowed_base_dir,
        )

        enable_path_validation(True)
        workspace = tmp_path / "workspace"
        outside = tmp_path / "outside"
        workspace.mkdir()
        outside.mkdir()
        (outside / "secret-dir").mkdir()
        set_allowed_base_dir(str(workspace))

        result = find_directory("secret-dir", str(outside))

        assert "segurança" in result.lower()

    def test_returns_message_when_not_found(self, tmp_path):
        from aura_cli.core.tools.file_system import (
            find_directory,
            set_allowed_base_dir,
        )

        set_allowed_base_dir(str(tmp_path))
        result = find_directory("nonexistent_xyz_123", str(tmp_path))
        assert "não encontrado" in result.lower() or "not found" in result.lower()


# ---------------------------------------------------------------------------
# write_file (lazy-import patches)
# ---------------------------------------------------------------------------


class TestWriteFile:
    """write_file imports confirm_tool_execution_locally lazily inside the function."""

    _CONFIRM_PATH = (
        "aura_cli.core.tools.human_intervention_adapter.confirm_tool_execution_locally"
    )

    def test_creates_file_with_confirmation(self, tmp_path):
        from aura_cli.core.tools.file_system import set_allowed_base_dir, write_file

        set_allowed_base_dir(str(tmp_path))
        target = tmp_path / "new.txt"
        with (
            patch(
                "aura_cli.core.tools.human_intervention_adapter.confirm_tool_execution_locally",
                return_value=True,
            ),
            patch(
                "aura_cli.core.tools.file_system._sanitize_path", return_value=target
            ),
            patch(
                "aura_cli.cli.ui.loading_states.show_tool_loading",
                return_value=MagicMock(),
            ),
        ):
            result = write_file(str(target), "hello")
        assert target.exists()
        assert "sucesso" in result.lower() or "criado" in result.lower()

    def test_append_to_existing_file(self, tmp_path):
        from aura_cli.core.tools.file_system import set_allowed_base_dir, write_file

        set_allowed_base_dir(str(tmp_path))
        target = tmp_path / "log.txt"
        target.write_text("first\n")
        with (
            patch(
                "aura_cli.core.tools.human_intervention_adapter.confirm_tool_execution_locally",
                return_value=True,
            ),
            patch(
                "aura_cli.core.tools.file_system._sanitize_path", return_value=target
            ),
            patch(
                "aura_cli.cli.ui.loading_states.show_tool_loading",
                return_value=MagicMock(),
            ),
        ):
            write_file(str(target), "second\n", append=True)
        content = target.read_text()
        assert "first" in content
        assert "second" in content

    def test_cancelled_returns_message(self, tmp_path):
        from aura_cli.core.tools.file_system import set_allowed_base_dir, write_file

        set_allowed_base_dir(str(tmp_path))
        with patch(
            "aura_cli.core.tools.human_intervention_adapter.confirm_tool_execution_locally",
            return_value=False,
        ):
            result = write_file(str(tmp_path / "f.txt"), "data")
        assert "cancelad" in result.lower()

    def test_permission_error_returns_error(self, tmp_path):
        from aura_cli.core.tools.file_system import set_allowed_base_dir, write_file

        set_allowed_base_dir(str(tmp_path))
        target = tmp_path / "f.txt"
        with (
            patch(
                "aura_cli.core.tools.human_intervention_adapter.confirm_tool_execution_locally",
                return_value=True,
            ),
            patch(
                "aura_cli.core.tools.file_system._sanitize_path", return_value=target
            ),
            patch(
                "aura_cli.cli.ui.loading_states.show_tool_loading",
                return_value=MagicMock(),
            ),
            patch("builtins.open", side_effect=PermissionError("denied")),
        ):
            result = write_file(str(target), "x")
        assert "erro" in result.lower() or "permiss" in result.lower()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestFormatSize:
    def test_bytes(self):
        from aura_cli.core.tools.file_system import _format_size

        assert _format_size(512) == "512 B"

    def test_kilobytes(self):
        from aura_cli.core.tools.file_system import _format_size

        assert "KB" in _format_size(2048)

    def test_megabytes(self):
        from aura_cli.core.tools.file_system import _format_size

        assert "MB" in _format_size(2 * 1024 * 1024)


class TestGetFileTypeLabel:
    def test_python_is_code(self):
        from aura_cli.core.tools.file_system import _get_file_type_label

        assert "Código" in _get_file_type_label(".py")

    def test_json_is_config(self):
        from aura_cli.core.tools.file_system import _get_file_type_label

        assert "Config" in _get_file_type_label(".json")

    def test_unknown_ext_fallback(self):
        from aura_cli.core.tools.file_system import _get_file_type_label

        assert "Arquivo" in _get_file_type_label(".xyz")

    def test_image_ext(self):
        from aura_cli.core.tools.file_system import _get_file_type_label

        assert "Imagem" in _get_file_type_label(".png")

    def test_markdown_is_text(self):
        from aura_cli.core.tools.file_system import _get_file_type_label

        assert "Texto" in _get_file_type_label(".md")
