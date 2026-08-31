"""Provider-neutral contract for cloud resource adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class CloudProviderManager(ABC):
    """Common interface implemented by each vendor adapter."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.stats = get_stats()
        logger.info("%sManager initialized", provider_name)

    @abstractmethod
    def list_resources(
        self, resource_type: str, **filters: Any
    ) -> list[dict[str, Any]]:
        """List resources of one provider-specific type."""

    @abstractmethod
    def get_resource_status(self, resource_id: str) -> dict[str, Any]:
        """Return status of one provider resource."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the provider SDK and credentials are available."""
