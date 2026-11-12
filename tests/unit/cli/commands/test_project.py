"""Tests for project command handlers (/init, /todo, /notebook).

Regression coverage: /init previously imported a non-existent
module (aura_cli.core.indexing.project_indexer.ProjectIndexer), called
status.update outside the console.status context, and referenced the
non-existent UIStyles.WORKING attribute. These tests lock in the fix.
"""

from unittest.mock import patch


class TestHandleInit:
    """Tests for the /init command handler."""

    def test_init_calls_real_indexer_entrypoint(self):
        """handle_init must drive the real async handle_init_command."""
        from aura_cli.cli.commands import project

        fake_results = {
            "status": "success",
            "files_analyzed": 3,
            "files_skipped": 1,
        }

        with patch.object(project, "get_console") as mock_console:
            with patch(
                "aura_cli.core.context.project_indexer.handle_init_command"
            ) as mock_cmd:
                # handle_init runs the coroutine via asyncio.run; return a
                # plain dict from an async stub.
                async def _fake(*_args, **_kwargs):
                    return fake_results

                mock_cmd.side_effect = _fake

                project.handle_init()

                mock_cmd.assert_called_once()
                # success path prints a confirmation
                mock_console.return_value.print.assert_called()

    def test_init_no_nonexistent_indexing_module(self):
        """The dead aura_cli.core.indexing package must not be imported."""
        from pathlib import Path

        import aura_cli.cli.commands.project as project_mod

        source = Path(project_mod.__file__).read_text(encoding="utf-8")
        assert "core.indexing.project_indexer" not in source
        assert "ProjectIndexer(" not in source

    def test_init_uses_valid_style_token(self):
        """UIStyles.WORKING does not exist; must use STATUS_WORKING."""
        from pathlib import Path

        import aura_cli.cli.commands.project as project_mod

        source = Path(project_mod.__file__).read_text(encoding="utf-8")
        assert "UIStyles.WORKING" not in source
        assert "UIStyles.STATUS_WORKING" in source

    def test_init_reports_error_status(self):
        """When the indexer returns an error status, handle_init reports it."""
        from aura_cli.cli.commands import project

        with patch.object(project, "get_console") as mock_console:
            with patch(
                "aura_cli.core.context.project_indexer.handle_init_command"
            ) as mock_cmd:

                async def _fake(*_args, **_kwargs):
                    return {"status": "error", "error": "boom"}

                mock_cmd.side_effect = _fake

                project.handle_init()

                printed = " ".join(
                    str(c.args[0])
                    for c in mock_console.return_value.print.call_args_list
                    if c.args
                )
                assert "boom" in printed
