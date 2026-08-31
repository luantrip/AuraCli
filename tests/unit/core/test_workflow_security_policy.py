from __future__ import annotations

from scripts.check_workflow_security import validate_workflow


def test_workflow_policy_accepts_checked_in_workflows() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    workflow_paths = sorted((root / ".github/workflows").glob("*.y*ml"))

    assert workflow_paths
    assert all(validate_workflow(path) == [] for path in workflow_paths)


def test_workflow_policy_rejects_broad_permissions(tmp_path) -> None:
    workflow = tmp_path / "unsafe.yml"
    workflow.write_text(
        """name: unsafe
on: [push]
permissions: write-all
concurrency: {group: unsafe}
jobs:
  build:
    permissions: {contents: write}
    runs-on: ubuntu-latest
    steps: []
""",
        encoding="utf-8",
    )

    errors = validate_workflow(workflow)

    assert any("top-level permissions" in error for error in errors)
    assert any("contents: write" in error for error in errors)


def test_workflow_policy_rejects_malformed_job(tmp_path) -> None:
    workflow = tmp_path / "unsafe.yml"
    workflow.write_text(
        """name: unsafe
on: [push]
permissions: {contents: read}
concurrency: {group: unsafe}
jobs:
  build: []
""",
        encoding="utf-8",
    )

    errors = validate_workflow(workflow)

    assert any("job must be a mapping" in error for error in errors)


def test_workflow_policy_rejects_untrusted_trigger_and_missing_concurrency(
    tmp_path,
) -> None:
    workflow = tmp_path / "unsafe.yml"
    workflow.write_text(
        """name: unsafe
on:
  pull_request_target:
    types: [opened]
permissions: {contents: read}
jobs: {}
""",
        encoding="utf-8",
    )

    errors = validate_workflow(workflow)

    assert any("pull_request_target" in error for error in errors)
    assert any("concurrency" in error for error in errors)
