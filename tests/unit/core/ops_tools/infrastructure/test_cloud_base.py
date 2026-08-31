"""Provider-neutral cloud contract tests."""

import pytest

from aura_cli.core.ops_tools.infrastructure.cloud.base import CloudProviderManager


def test_cloud_provider_contract_is_abstract() -> None:
    with pytest.raises(TypeError):
        CloudProviderManager("test")


def test_aggregate_surface_reexports_the_canonical_contract() -> None:
    from aura_cli.core.ops_tools.infrastructure.cloud_providers import (
        CloudProviderManager as AggregateContract,
    )

    assert AggregateContract is CloudProviderManager
