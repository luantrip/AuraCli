"""Tests for console_view module.

Tests for interaction history management and visualization.
"""

import time
from unittest.mock import patch

import pytest


class TestInteractionStatus:
    """Tests for InteractionStatus enum."""

    def test_interaction_status_values(self):
        """Test InteractionStatus enum has all expected values."""
        from aura_cli.cli.ui.console_view import InteractionStatus

        assert InteractionStatus.RUNNING.value == "running"
        assert InteractionStatus.SUCCESS.value == "success"
        assert InteractionStatus.ERROR.value == "error"
        assert InteractionStatus.CANCELLED.value == "cancelled"


class TestInteraction:
    """Tests for Interaction dataclass."""

    def test_interaction_creation(self):
        """Test Interaction dataclass can be created."""
        from aura_cli.cli.ui.console_view import Interaction, InteractionStatus

        interaction = Interaction(
            id="test_id", timestamp=time.time(), prompt="Test prompt"
        )

        assert interaction.id == "test_id"
        assert interaction.prompt == "Test prompt"
        assert interaction.response is None
        assert interaction.status == InteractionStatus.RUNNING
        assert interaction.tool_calls == []

    def test_interaction_with_all_fields(self):
        """Test Interaction with all fields."""
        from aura_cli.cli.ui.console_view import Interaction, InteractionStatus

        interaction = Interaction(
            id="test_id",
            timestamp=time.time(),
            prompt="Test prompt",
            response="Test response",
            status=InteractionStatus.SUCCESS,
            prompt_tokens=100,
            generated_tokens=50,
            execution_time=1.5,
            tool_calls=[{"name": "test_tool"}],
            error=None,
        )

        assert interaction.response == "Test response"
        assert interaction.status == InteractionStatus.SUCCESS
        assert interaction.prompt_tokens == 100
        assert len(interaction.tool_calls) == 1

    def test_interaction_post_init(self):
        """Test Interaction __post_init__ initializes tool_calls."""
        from aura_cli.cli.ui.console_view import Interaction

        interaction = Interaction(
            id="test", timestamp=time.time(), prompt="test", tool_calls=None
        )

        assert interaction.tool_calls == []


class TestConsoleHistory:
    """Tests for ConsoleHistory class."""

    @pytest.fixture
    def history(self):
        """Create fresh ConsoleHistory instance."""
        from aura_cli.cli.ui.console_view import ConsoleHistory

        return ConsoleHistory()

    def test_console_history_init(self, history):
        """Test ConsoleHistory initialization."""
        assert history.interactions == []
        assert history.selected_id is None

    def test_add_interaction(self, history):
        """Test adding an interaction."""
        interaction_id = history.add_interaction("Test prompt")

        assert len(history.interactions) == 1
        assert history.interactions[0].prompt == "Test prompt"
        assert history.selected_id == interaction_id

    def test_add_interaction_with_custom_id(self, history):
        """Test adding interaction with custom ID."""
        custom_id = history.add_interaction("Test", interaction_id="custom_123")

        assert custom_id == "custom_123"
        assert history.interactions[0].id == "custom_123"

    def test_add_multiple_interactions(self, history):
        """Test adding multiple interactions."""
        history.add_interaction("First")
        id2 = history.add_interaction("Second")

        assert len(history.interactions) == 2
        assert history.selected_id == id2  # Should be last added

    def test_update_interaction(self, history):
        """Test updating an interaction."""
        from aura_cli.cli.ui.console_view import InteractionStatus

        interaction_id = history.add_interaction("Test")

        result = history.update_interaction(
            interaction_id,
            response="Response text",
            status=InteractionStatus.SUCCESS,
            prompt_tokens=100,
            generated_tokens=50,
            execution_time=1.5,
        )

        assert result is True
        interaction = history.get_interaction(interaction_id)
        assert interaction.response == "Response text"
        assert interaction.status == InteractionStatus.SUCCESS
        assert interaction.prompt_tokens == 100

    def test_update_interaction_not_found(self, history):
        """Test updating non-existent interaction."""
        result = history.update_interaction("nonexistent", response="test")
        assert result is False

    def test_update_interaction_with_tool_calls(self, history):
        """Test updating interaction with tool calls."""
        interaction_id = history.add_interaction("Test")

        tool_calls = [{"name": "tool1"}, {"name": "tool2"}]
        history.update_interaction(interaction_id, tool_calls=tool_calls)

        interaction = history.get_interaction(interaction_id)
        assert len(interaction.tool_calls) == 2

    def test_update_interaction_with_error(self, history):
        """Test updating interaction with error."""
        from aura_cli.cli.ui.console_view import InteractionStatus

        interaction_id = history.add_interaction("Test")

        history.update_interaction(
            interaction_id, status=InteractionStatus.ERROR, error="Something went wrong"
        )

        interaction = history.get_interaction(interaction_id)
        assert interaction.status == InteractionStatus.ERROR
        assert interaction.error == "Something went wrong"

    def test_get_interaction(self, history):
        """Test getting an interaction by ID."""
        interaction_id = history.add_interaction("Test")

        interaction = history.get_interaction(interaction_id)

        assert interaction is not None
        assert interaction.prompt == "Test"

    def test_get_interaction_not_found(self, history):
        """Test getting non-existent interaction."""
        interaction = history.get_interaction("nonexistent")
        assert interaction is None


class TestGlobalConsoleHistory:
    """Tests for global console history functions."""

    def test_get_console_history(self):
        """Test getting global history instance."""
        from aura_cli.cli.ui.console_view import ConsoleHistory, get_console_history

        history = get_console_history()

        assert isinstance(history, ConsoleHistory)

    def test_get_console_history_singleton(self):
        """Test global history is singleton."""
        from aura_cli.cli.ui.console_view import get_console_history

        history1 = get_console_history()
        history2 = get_console_history()

        assert history1 is history2


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_status_icon(self):
        """Test get_status_icon function."""
        from aura_cli.cli.ui.console_view import InteractionStatus, get_status_icon

        icon = get_status_icon(InteractionStatus.SUCCESS)
        assert isinstance(icon, str)
        assert len(icon) > 0

    def test_get_status_icon_all_statuses(self):
        """Test get_status_icon for all statuses."""
        from aura_cli.cli.ui.console_view import InteractionStatus, get_status_icon

        for status in InteractionStatus:
            icon = get_status_icon(status)
            assert isinstance(icon, str)

    def test_get_status_color(self):
        """Test get_status_color function."""
        from aura_cli.cli.ui.console_view import InteractionStatus, get_status_color

        color = get_status_color(InteractionStatus.SUCCESS)
        assert isinstance(color, str)

    def test_get_status_color_all_statuses(self):
        """Test get_status_color for all statuses."""
        from aura_cli.cli.ui.console_view import InteractionStatus, get_status_color

        for status in InteractionStatus:
            color = get_status_color(status)
            assert isinstance(color, str)


class TestDisplayFunctions:
    """Tests for display functions."""

    def test_display_interaction_list_empty(self):
        """Test display_interaction_list with empty history."""
        from aura_cli.cli.ui.console_view import (
            ConsoleHistory,
            display_interaction_list,
        )

        with patch("aura_cli.cli.ui.console_view.get_console_history") as mock_history:
            mock_history.return_value = ConsoleHistory()

            with patch("aura_cli.cli.ui.console_view.console") as mock_console:
                display_interaction_list()
                mock_console.print.assert_called()

    def test_display_interaction_details_not_found(self):
        """Test display_interaction_details with non-existent ID."""
        from aura_cli.cli.ui.console_view import (
            ConsoleHistory,
            display_interaction_details,
        )

        with patch("aura_cli.cli.ui.console_view.get_console_history") as mock_history:
            mock_history.return_value = ConsoleHistory()

            with patch("aura_cli.cli.ui.console_view.console") as mock_console:
                display_interaction_details("nonexistent")
                mock_console.print.assert_called()


class TestInteractiveConsoleDashboard:
    """Tests for InteractiveConsoleDashboard class."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard with mock history."""
        from aura_cli.cli.ui.console_view import (
            ConsoleHistory,
            InteractiveConsoleDashboard,
        )

        history = ConsoleHistory()
        return InteractiveConsoleDashboard(history)

    def test_dashboard_creation(self, dashboard):
        """Test dashboard can be created."""
        assert dashboard is not None
        assert dashboard.search_query == ""
        assert dashboard.status_filter is None
        assert dashboard.type_filter is None

    def test_set_search(self, dashboard):
        """Test setting search query."""
        dashboard.set_search("Test Query")
        assert dashboard.search_query == "test query"  # Lowercased

    def test_set_status_filter(self, dashboard):
        """Test setting status filter."""
        from aura_cli.cli.ui.console_view import InteractionStatus

        dashboard.set_status_filter(InteractionStatus.SUCCESS)
        assert dashboard.status_filter == InteractionStatus.SUCCESS

    def test_set_type_filter(self, dashboard):
        """Test setting type filter."""
        dashboard.set_type_filter("Chat")
        assert dashboard.type_filter == "Chat"

    def test_set_date_filter(self, dashboard):
        """Test setting date filter."""
        from datetime import timedelta

        dashboard.set_date_filter(24)  # 24 hours
        assert dashboard.date_filter == timedelta(hours=24)

    def test_set_date_filter_none(self, dashboard):
        """Test clearing date filter."""
        dashboard.set_date_filter(24)
        dashboard.set_date_filter(None)
        assert dashboard.date_filter is None

    def test_filter_interactions_empty(self, dashboard):
        """Test filtering empty interactions."""
        result = dashboard._filter_interactions()
        assert result == []

    def test_get_statistics_empty(self, dashboard):
        """Test statistics with no interactions."""
        stats = dashboard._get_statistics([])

        assert stats["total"] == 0
        assert stats["by_status"] == {}
        assert stats["total_tokens"] == 0

    def test_get_statistics_with_interactions(self, dashboard):
        """Test statistics with interactions."""
        from aura_cli.cli.ui.console_view import Interaction, InteractionStatus

        interactions = [
            Interaction(
                id="1",
                timestamp=time.time(),
                prompt="Test",
                status=InteractionStatus.SUCCESS,
                prompt_tokens=100,
                generated_tokens=50,
                execution_time=1.0,
            )
        ]

        stats = dashboard._get_statistics(interactions)

        assert stats["total"] == 1
        assert stats["total_tokens"] == 150
        assert stats["avg_execution_time"] == 1.0

    def test_export_history_json(self, dashboard):
        """Test exporting history as JSON."""
        result = dashboard.export_history("json")

        assert isinstance(result, str)
        assert result.startswith("[")  # JSON array

    def test_export_history_csv(self, dashboard):
        """Test exporting history as CSV."""
        result = dashboard.export_history("csv")

        assert isinstance(result, str)
        assert "ID" in result  # Header

    def test_export_history_unknown_format(self, dashboard):
        """Test exporting with unknown format."""
        result = dashboard.export_history("unknown")
        assert result == ""


def test_interaction_list_uses_injected_console_without_leading_blank(monkeypatch):
    from rich.console import Console

    from aura_cli.application.presentation.interaction_history import (
        ConsoleHistory,
        Interaction,
        InteractionStatus,
    )
    from aura_cli.cli.ui import console_view

    history = ConsoleHistory()
    history.interactions.append(
        Interaction(
            id="ok-1",
            timestamp=1_700_000_000.0,
            prompt="listar arquivos",
            response="aura_cli",
            status=InteractionStatus.SUCCESS,
            tool_calls=[{"name": "list_directory"}],
        )
    )
    monkeypatch.setattr(console_view, "_console_history", history)
    output_console = Console(record=True, width=72)

    console_view.display_interaction_list(output_console=output_console)
    output = output_console.export_text(clear=False)

    assert not output.startswith("\n")
    assert "Ferramentas (1)" in output
    assert "Entrada" in output


def test_interaction_details_localizes_existing_and_missing_states(monkeypatch):
    from rich.console import Console

    from aura_cli.application.presentation.interaction_history import (
        ConsoleHistory,
        Interaction,
        InteractionStatus,
    )
    from aura_cli.cli.ui import console_view

    history = ConsoleHistory()
    history.interactions.append(
        Interaction(
            id="ok-1",
            timestamp=1_700_000_000.0,
            prompt="listar arquivos",
            response="aura_cli",
            status=InteractionStatus.SUCCESS,
        )
    )
    monkeypatch.setattr(console_view, "_console_history", history)
    output_console = Console(record=True, width=72)

    console_view.display_interaction_details("ok-1", output_console=output_console)
    console_view.display_interaction_details("missing", output_console=output_console)
    output = output_console.export_text(clear=False)

    assert "Interação ok-1" in output
    assert "Estado:" in output
    assert "Resposta:" in output
    assert "Interação não encontrada" in output
    assert "Response:" not in output


def test_dashboard_accepts_compact_width_and_localized_header():
    from rich.console import Console

    from aura_cli.application.presentation.interaction_history import ConsoleHistory
    from aura_cli.cli.ui.console_view import InteractiveConsoleDashboard

    dashboard = InteractiveConsoleDashboard(ConsoleHistory())
    compact_layout = dashboard.render_dashboard(console_width=60)
    output_console = Console(record=True, width=60)
    output_console.print(compact_layout)
    output = output_console.export_text(clear=False)

    assert "Dashboard do histórico" in output
    assert "Selecione uma interação" in output
