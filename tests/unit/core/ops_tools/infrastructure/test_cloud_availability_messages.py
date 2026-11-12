"""Cloud providers give an actionable reason when unavailable, not a silent empty list.

When the SDK is missing or credentials are absent, ``availability_error`` returns
a specific, actionable message (what to install / how to authenticate), and the
``cloud_list_resources`` tool surfaces it instead of returning ``[]``.
"""

from __future__ import annotations

import json

import pytest

from aura_cli.core.ops_tools.infrastructure.cloud.aws import AWSManager
from aura_cli.core.ops_tools.infrastructure.cloud.azure import AzureManager
from aura_cli.core.ops_tools.infrastructure.cloud.gcp import GCPManager

_PROVIDERS = [
    (AWSManager, "boto3"),
    (GCPManager, "google-cloud"),
    (AzureManager, "azure-"),
]


@pytest.mark.parametrize("manager_cls, install_hint", _PROVIDERS)
def test_missing_sdk_yields_an_install_command(manager_cls, install_hint) -> None:
    manager = manager_cls()
    manager._sdk_installed = lambda: False  # type: ignore[assignment]
    manager._available = None
    message = manager.availability_error()
    assert message is not None
    assert "not installed" in message
    assert "pip install" in message
    assert install_hint in message


@pytest.mark.parametrize("manager_cls, _", _PROVIDERS)
def test_missing_credentials_yields_auth_guidance(manager_cls, _) -> None:
    manager = manager_cls()
    manager._sdk_installed = lambda: True  # type: ignore[assignment]
    manager.is_available = lambda: False  # type: ignore[assignment]
    message = manager.availability_error()
    assert message is not None
    assert "credentials not configured" in message
    assert "not installed" not in message  # distinct from the SDK case


@pytest.mark.parametrize("manager_cls, _", _PROVIDERS)
def test_available_provider_has_no_error(manager_cls, _) -> None:
    manager = manager_cls()
    manager.is_available = lambda: True  # type: ignore[assignment]
    assert manager.availability_error() is None


def test_tool_surfaces_the_actionable_message(monkeypatch) -> None:
    from aura_cli.core.tools import cloud_tools

    class _Unavailable:
        def is_available(self) -> bool:
            return False

        def availability_error(self) -> str:
            return "AWS SDK not installed. Install it with: pip install boto3"

    monkeypatch.setattr(
        cloud_tools, "_provider_manager", lambda provider: _Unavailable()
    )
    result = json.loads(cloud_tools.cloud_list_resources("aws", "ec2"))
    assert "pip install boto3" in result["error"]
    # The old empty-list behavior is gone: no silent success envelope.
    assert "resources" not in result


def test_github_workflow_status_reports_missing_cli_instead_of_empty(
    monkeypatch,
) -> None:
    """Missing GitHub CLI yields an actionable diagnostic message, not []."""
    import shutil

    from aura_cli.core.ops_tools.ci_cd import github_actions

    monkeypatch.setattr(shutil, "which", lambda name: None)
    result = github_actions.get_workflow_status()
    assert result != []
    assert len(result) == 1
    assert "gh" in result[0]["error"].lower()
    assert "install" in result[0]["error"].lower()

