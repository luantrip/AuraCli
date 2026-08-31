"""Validate least-privilege and trigger policy for GitHub Actions workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github/workflows"
EXPECTED_WORKFLOW_PERMISSIONS = {"contents": "read"}
APPROVED_CONTENTS_WRITERS = {"release", "github-release"}


def _permissions(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        return {"__invalid_permissions__": str(value)}
    return {str(key): str(permission) for key, permission in value.items()}


def _validate_workflow_header(path: Path, document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    top_permissions = _permissions(document.get("permissions"))
    if top_permissions != EXPECTED_WORKFLOW_PERMISSIONS:
        errors.append(
            f"{path.name}: top-level permissions must be exactly "
            f"{EXPECTED_WORKFLOW_PERMISSIONS!r}, got {top_permissions!r}"
        )

    yaml_document = cast(dict[Any, Any], document)
    trigger = yaml_document.get("on", yaml_document.get(True, {}))
    if isinstance(trigger, dict) and "pull_request_target" in trigger:
        errors.append(f"{path.name}: pull_request_target is not permitted")
    if "concurrency" not in document:
        errors.append(f"{path.name}: concurrency policy is required")
    return errors


def _validate_jobs(path: Path, jobs: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            errors.append(f"{path.name}:{job_name}: job must be a mapping")
            continue
        permissions = _permissions(job.get("permissions"))
        if "__invalid_permissions__" in permissions:
            errors.append(f"{path.name}:{job_name}: permissions must be a mapping")
        if (
            permissions.get("contents") == "write"
            and job_name not in APPROVED_CONTENTS_WRITERS
        ):
            errors.append(
                f"{path.name}:{job_name}: contents: write is not an approved job"
            )
        errors.extend(
            f"{path.name}:{job_name}: broad permission {key}: {value}"
            for key, value in permissions.items()
            if value in {"write-all", "read-all"}
        )
    return errors


def _job_permissions(jobs: dict[str, Any], job_name: str) -> dict[str, str]:
    job = jobs.get(job_name, {})
    if not isinstance(job, dict):
        return {}
    return _permissions(job.get("permissions"))


def _validate_release_exceptions(path: Path, jobs: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if path.name == "nim-build.yml":
        release_permissions = _job_permissions(jobs, "release")
        if release_permissions.get("contents") != "write":
            errors.append(
                "nim-build.yml: release job must explicitly request contents: write"
            )
    if path.name == "release.yml":
        pypi_permissions = _job_permissions(jobs, "publish-pypi")
        github_permissions = _job_permissions(jobs, "github-release")
        if pypi_permissions.get("id-token") != "write":
            errors.append(
                "release.yml: PyPI job must explicitly request id-token: write"
            )
        if github_permissions.get("contents") != "write":
            errors.append(
                "release.yml: GitHub release job must explicitly request contents: write"
            )
    return errors


def validate_workflow(path: Path) -> list[str]:
    """Return policy violations for one workflow file."""
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        return [f"{path.name}: workflow root must be a mapping"]

    errors = _validate_workflow_header(path, document)
    jobs = document.get("jobs", {})
    if not isinstance(jobs, dict):
        return [*errors, f"{path.name}: jobs must be a mapping"]
    errors.extend(_validate_jobs(path, jobs))
    errors.extend(_validate_release_exceptions(path, jobs))
    return errors


def main() -> int:
    workflow_paths = sorted(WORKFLOW_DIR.glob("*.y*ml"))
    errors = [error for path in workflow_paths for error in validate_workflow(path)]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Workflow security policy verified: {len(workflow_paths)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
