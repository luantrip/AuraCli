"""Metrics Panel for Aura TUI.

Key-value metrics display panel with grid layout.
"""

from textual.containers import Grid, Vertical
from textual.widgets import Label


class MetricsPanel(Vertical):
    """Panel to display various key-value metrics.

    Features:
    - Grid table layout for metrics
    - Key-value pair display
    - Highlight styling for values
    - Real-time updates
    """

    def compose(self):
        """Compose metrics panel structure."""
        yield Grid(id="metrics_display")

    def update_metrics(self, metrics: dict) -> None:
        """Update the displayed metrics."""
        grid = self.query_one("#metrics_display", Grid)
        grid.remove_children()

        for key, value in metrics.items():
            grid.mount(Label(f"{key}:", classes="metric-key"))
            grid.mount(Label(str(value), classes="metric-value"))
