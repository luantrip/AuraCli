"""Regression tests for side-effect-free worker readiness."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from aura_cli.cli.utils.worker_readiness import (
    ReadinessReport,
    WorkerReadinessError,
    build_worker_readiness,
    ensure_worker_ready,
)


def test_ready_report_is_serializable_without_secret_value(tmp_path: Path) -> None:
    sentinel = "secret-sentinel-must-not-leak"
    report = build_worker_readiness(
        worker_type="agi",
        model="gpt-4",
        api_keys={"OPENAI_API_KEY": sentinel},
        project_root=tmp_path,
    )

    assert report.ready is True
    assert report.provider == "gpt"
    assert report.credential_name == "OPENAI_API_KEY"
    assert sentinel not in repr(report.to_dict())
    assert report.to_dict()["status"] == "ready"


def test_missing_credential_is_configuration_error_without_secret(
    tmp_path: Path,
) -> None:
    report = build_worker_readiness(
        worker_type="ops",
        model="gpt-4",
        api_keys={},
        project_root=tmp_path,
    )

    payload = report.to_dict()
    assert report.ready is False
    assert report.code == "configuration"
    assert payload["error_code"] == "configuration"
    assert "OPENAI_API_KEY" in str(payload["error"])


def test_invalid_workspace_is_rejected_before_dependency_check(tmp_path: Path) -> None:
    dependency_check = Mock(return_value=None)
    report = build_worker_readiness(
        worker_type="agi",
        model="gpt-4",
        api_keys={"OPENAI_API_KEY": "test-key"},
        project_root=tmp_path / "missing",
        dependency_check=dependency_check,
    )

    assert report.ready is False
    assert report.code == "workspace"
    dependency_check.assert_not_called()


def test_dependency_failure_is_structured(tmp_path: Path) -> None:
    report = build_worker_readiness(
        worker_type="ops",
        model="gpt-4",
        api_keys={"OPENAI_API_KEY": "test-key"},
        project_root=tmp_path,
        dependency_check=lambda: {"ops_tools": False},
    )

    assert report.ready is False
    assert report.code == "dependency"
    assert report.dependencies == ("ops_tools",)


def test_auto_model_preserves_existing_google_fallback(tmp_path: Path) -> None:
    report = build_worker_readiness(
        worker_type="agi",
        model="auto",
        api_keys={"GOOGLE_API_KEY": "test-key"},
        project_root=tmp_path,
    )

    assert report.ready is True
    assert report.provider == "auto"
    assert report.credential_name == "GOOGLE_API_KEY"


def test_ensure_worker_ready_raises_before_creation(tmp_path: Path) -> None:
    with pytest.raises(WorkerReadinessError) as raised:
        ensure_worker_ready(
            worker_type="agi",
            model="gpt-4",
            api_keys={},
            project_root=tmp_path,
        )

    assert raised.value.report.code == "configuration"
    assert isinstance(raised.value.report, ReadinessReport)
