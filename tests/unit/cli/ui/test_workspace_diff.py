from aura_cli.application.diffs import WorkspaceDiff
from aura_cli.cli.ui.components.workspace_diff import WorkspaceDiffDisplay


def test_workspace_diff_display_renders_snapshot_summary() -> None:
    snapshot = WorkspaceDiff(
        project_root="/tmp/project",
        status="## main\n M app.py",
        changed_files=("app.py",),
        patch="@@ -1 +1 @@\n-old\n+new",
    )

    rendered = WorkspaceDiffDisplay().render(snapshot)

    assert rendered.title == "Aura Diff"
