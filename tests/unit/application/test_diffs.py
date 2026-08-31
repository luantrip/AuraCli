"""Tests for surface-independent diff generation."""

from aura_cli.application.diffs import (
    WorkspaceDiff,
    generate_new_file_diff,
    generate_unified_diff,
)


def test_generate_unified_diff_marks_old_and_new_paths() -> None:
    diff = generate_unified_diff("src/a.py", "old\n", "new\n")

    assert diff[:2] == ["--- a/src/a.py", "+++ b/src/a.py"]
    assert "-old\n" in diff
    assert "+new\n" in diff


def test_generate_new_file_diff_marks_every_content_line_as_added() -> None:
    assert generate_new_file_diff("notes.txt", "one\ntwo") == [
        "--- /dev/null",
        "+++ b/notes.txt",
        "@@ -0,0 +1,2 @@",
        "+one",
        "+two",
    ]


def test_workspace_diff_render_includes_status_and_truncation() -> None:
    snapshot = WorkspaceDiff(
        project_root="/tmp/project",
        status="## main\n M src/a.py",
        changed_files=("src/a.py",),
        patch="@@\n-old\n+new",
        truncated=True,
    )

    rendered = snapshot.render()

    assert "WORKSPACE DIFF" in rendered
    assert "src/a.py" in rendered
    assert "diff truncada" in rendered
    assert snapshot.to_dict()["has_changes"] is True
