"""Stable Core names for the application telemetry coordinator."""

from aura_cli.application.observability.coordinator import (
    TelemetryCoordinator,
    get_telemetry_coordinator,
)

MetricsBridge = TelemetryCoordinator
get_metrics_bridge = get_telemetry_coordinator

__all__ = ["MetricsBridge", "get_metrics_bridge"]
