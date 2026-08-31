"""Coverage tests for dev_tools.py missing lines."""

from pathlib import Path
from unittest.mock import MagicMock, patch

UI_PATCHES = [
    patch("aura_cli.core.tools.dev_tools.rprint"),
    patch("aura_cli.core.tools.dev_tools.console"),
    patch("aura_cli.core.ui.display_tool_call", create=True),
]

CONFIRM_PATH = "aura_cli.core.tools.dev_tools.confirm_tool_execution_locally"
DISPLAY_PATH = "aura_cli.core.ui.display_tool_call"


def ui_patches():
    return [
        patch("aura_cli.core.tools.dev_tools.rprint"),
        patch("aura_cli.core.tools.dev_tools.console"),
        patch(DISPLAY_PATH, create=True),
    ]


# ── edit_file ────────────────────────────────────────────────────────────────

LOADING_PATH = "aura_cli.cli.ui.loading_states.show_tool_loading"


class TestEditFileExtra:
    def _run(self, path, old, new, confirm=True):
        from aura_cli.core.tools.dev_tools import edit_file

        with (
            patch(CONFIRM_PATH, return_value=confirm),
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch("aura_cli.core.tools.dev_tools.console"),
            patch(DISPLAY_PATH, create=True),
            patch(
                "aura_cli.core.tools.dev_tools.get_stats",
                return_value=MagicMock(skip_confirmations=False),
            ),
            patch(LOADING_PATH, return_value=MagicMock(), create=True),
            patch("aura_cli.cli.ui.display.display_file_edit", create=True),
        ):
            return edit_file(str(path), old, new)

    def test_edit_cancelled(self, tmp_path):
        f = tmp_path / "f.py"
        f.write_text("old")
        result = self._run(f, "old", "new", confirm=False)
        assert "cancelada" in result

    def test_edit_file_not_found(self, tmp_path):
        from aura_cli.core.tools.dev_tools import edit_file

        with (
            patch(CONFIRM_PATH, return_value=True),
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch("aura_cli.core.tools.dev_tools.console"),
            patch(DISPLAY_PATH, create=True),
        ):
            result = edit_file(str(tmp_path / "nope.py"), "x", "y")
        assert "não encontrado" in result or "Erro" in result


# ── find_in_files ─────────────────────────────────────────────────────────────


class TestFindInFiles:
    def _run(self, pattern, path, **kwargs):
        from aura_cli.core.tools.dev_tools import find_in_files

        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
        ):
            return find_in_files(pattern, path, **kwargs)

    def test_finds_match(self, tmp_path):
        (tmp_path / "a.py").write_text("def hello(): pass\n")
        result = self._run("def ", str(tmp_path))
        assert "hello" in result


    def test_max_results_limit(self, tmp_path):
        content = "\n".join(f"match_{i} = 1" for i in range(100))
        (tmp_path / "a.py").write_text(content)
        result = self._run("match_", str(tmp_path), max_results=5)
        assert "limitado" in result or "match_" in result

    def test_extension_filter(self, tmp_path):
        (tmp_path / "a.py").write_text("needle\n")
        (tmp_path / "b.txt").write_text("needle\n")
        result = self._run("needle", str(tmp_path), file_extensions=[".py"])
        assert "a.py" in result
        assert "b.txt" not in result


# ── tree_view ─────────────────────────────────────────────────────────────────


class TestTreeView:
    def _run(self, path, **kwargs):
        from aura_cli.core.tools.dev_tools import tree_view

        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch("aura_cli.core.tools.dev_tools.console"),
            patch(DISPLAY_PATH, create=True),
        ):
            return tree_view(path, **kwargs)


    def test_not_found(self):
        result = self._run("/no/such/path/xyz")
        assert "Erro" in result or "não encontrado" in result


# ── backup_file / restore_backup ─────────────────────────────────────────────


class TestBackupFile:
    def _run(self, path):
        from aura_cli.core.tools.dev_tools import backup_file

        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
        ):
            return backup_file(str(path))

    def test_success(self, tmp_path):
        f = tmp_path / "myfile.py"
        f.write_text("content")
        with patch("aura_cli.core.tools.dev_tools.Path"):
            # Use real Path but redirect backup_dir to tmp
            real_path = Path

            def fake_path(*args):
                p = real_path(*args)
                return p

            # Just run directly, backup goes to .aura/backups relative to cwd
            import os

            old = os.getcwd()
            os.chdir(tmp_path)
            try:
                from aura_cli.core.tools.dev_tools import backup_file

                with (
                    patch("aura_cli.core.tools.dev_tools.rprint"),
                    patch(DISPLAY_PATH, create=True),
                ):
                    result = backup_file(str(f))
                assert ".bak" in result or "backup" in result.lower()
            finally:
                os.chdir(old)

    def test_file_not_found(self, tmp_path):
        result = self._run(tmp_path / "nope.py")
        assert "não encontrado" in result or "Erro" in result

    def test_exception(self, tmp_path):
        f = tmp_path / "f.py"
        f.write_text("x")
        with (
            patch("shutil.copy2", side_effect=OSError("no space")),
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
        ):
            from aura_cli.core.tools.dev_tools import backup_file

            result = backup_file(str(f))
        assert "Erro" in result


class TestRestoreBackup:
    def test_no_backup_dir(self, tmp_path):
        import os

        from aura_cli.core.tools.dev_tools import restore_backup

        old = os.getcwd()
        os.chdir(tmp_path)  # no .aura/backups here
        try:
            with (
                patch("aura_cli.core.tools.dev_tools.rprint"),
                patch("aura_cli.core.tools.dev_tools.console"),
                patch(DISPLAY_PATH, create=True),
            ):
                result = restore_backup("file.py")
        finally:
            os.chdir(old)
        assert "Erro" in result or "não encontrado" in result

    def test_no_backup_found_for_file(self, tmp_path):
        from aura_cli.core.tools.dev_tools import restore_backup

        backup_dir = tmp_path / ".aura" / "backups"
        backup_dir.mkdir(parents=True)
        import os

        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            with (
                patch("aura_cli.core.tools.dev_tools.rprint"),
                patch("aura_cli.core.tools.dev_tools.console"),
                patch(DISPLAY_PATH, create=True),
            ):
                result = restore_backup("ghost.py")
        finally:
            os.chdir(old)
        assert "Nenhum backup" in result or "Erro" in result


# ── validate_syntax ───────────────────────────────────────────────────────────


class TestValidateSyntax:
    def _run(self, content, language):
        from aura_cli.core.tools.dev_tools import validate_syntax

        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
        ):
            return validate_syntax(content, language)

    def test_valid_python(self):
        assert self._run("x = 1", "python") == "OK"

    def test_invalid_python(self):
        result = self._run("def (:", "python")
        assert "sintaxe" in result.lower() or "Erro" in result

    def test_valid_json(self):
        assert self._run('{"key": 1}', "json") == "OK"

    def test_invalid_json(self):
        result = self._run("{bad json}", "json")
        assert "Erro" in result or "JSON" in result

    def test_valid_yaml(self):
        result = self._run("key: value\n", "yaml")
        assert result == "OK"


# ── analyze_code (extra branches) ─────────────────────────────────────────────


class TestAnalyzeCodeExtra:
    def _run(self, path):
        from aura_cli.core.tools.dev_tools import analyze_code

        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
        ):
            return analyze_code(str(path))

    def test_directory_input(self, tmp_path):
        result = self._run(tmp_path)
        assert "diretório" in result or "Erro" in result

    def test_not_found(self, tmp_path):
        result = self._run(tmp_path / "nope.py")
        assert "não encontrado" in result or "Erro" in result


# ── heavy-dep functions — exception path only ────────────────────────────────


class TestHeavyDepFunctions:
    """Cover exception branches for functions with heavy ML/NLP dependencies."""


    def test_analyze_code_nlp_not_found(self, tmp_path):
        from aura_cli.core.tools.dev_tools import analyze_code_nlp

        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
        ):
            result = analyze_code_nlp(str(tmp_path / "nope.py"))
        assert "não encontrado" in result or "Erro" in result

    def test_analyze_code_nlp_is_dir(self, tmp_path):
        from aura_cli.core.tools.dev_tools import analyze_code_nlp

        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
        ):
            result = analyze_code_nlp(str(tmp_path))
        assert "diretório" in result or "Erro" in result

    def test_analyze_code_nlp_exception(self, tmp_path):
        from aura_cli.core.tools.dev_tools import analyze_code_nlp

        f = tmp_path / "x.py"
        f.write_text("x=1")
        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
            patch(
                "aura_cli.core.tools.file_system.read_file",
                side_effect=RuntimeError("fail"),
                create=True,
            ),
            patch(
                "aura_cli.core.code_analysis.nlp_analyzer.NLPAnalyzer",
                side_effect=RuntimeError("fail"),
                create=True,
            ),
        ):
            result = analyze_code_nlp(str(f))
        assert "Erro" in result

    def test_classify_code_exception(self, tmp_path):
        from aura_cli.core.tools.dev_tools import classify_code

        f = tmp_path / "x.py"
        f.write_text("x=1")
        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
            patch(
                "aura_cli.core.code_analysis.nlp_analyzer.NLPAnalyzer",
                side_effect=RuntimeError("fail"),
                create=True,
            ),
        ):
            result = classify_code(str(f))
        assert "Erro" in result

    def test_summarize_code_exception(self, tmp_path):
        from aura_cli.core.tools.dev_tools import summarize_code

        f = tmp_path / "x.py"
        f.write_text("x=1")
        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
            patch(
                "aura_cli.core.code_analysis.nlp_analyzer.NLPAnalyzer",
                side_effect=RuntimeError("fail"),
                create=True,
            ),
        ):
            result = summarize_code(str(f))
        assert "Erro" in result


    def test_find_duplicate_code_exception(self, tmp_path):
        from aura_cli.core.tools.dev_tools import find_duplicate_code

        with (
            patch("aura_cli.core.tools.dev_tools.rprint"),
            patch(DISPLAY_PATH, create=True),
            patch("os.walk", side_effect=RuntimeError("fail")),
        ):
            result = find_duplicate_code(str(tmp_path))
        assert "Erro" in result


