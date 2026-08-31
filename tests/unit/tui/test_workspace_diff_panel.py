from aura_cli.application.diffs import WorkspaceDiff
from aura_cli.tui.widgets.diff.workspace_diff_panel import WorkspaceDiffPanel


def test_workspace_diff_panel_classifies_patch_lines() -> None:
    assert "line-added" in WorkspaceDiffPanel._line_class("+new")
    assert "line-removed" in WorkspaceDiffPanel._line_class("-old")
    assert "line-header" in WorkspaceDiffPanel._line_class("@@ -1 +1 @@")
    assert "line-context" in WorkspaceDiffPanel._line_class(" context")


def test_workspace_diff_panel_summarizes_state() -> None:
    snapshot = WorkspaceDiff(
        project_root="/tmp/project",
        status="## main",
        changed_files=(),
        patch="",
    )

    panel = WorkspaceDiffPanel(snapshot)

    assert "limpo" in panel._summary()
