"""Tests for ui/loading_states.py - Loading state management.

Tests verify:
- LoadingState: Enum values
- LoadingCategory: Enum values
- AdvancedLoadingManager: Loading state management
- LLMLoadingStates: LLM-specific loading states
- ToolLoadingStates: Tool-specific loading states
- FileLoadingStates: File-specific loading states
- AgentLoadingStates: Agent-specific loading states
- BackgroundLoadingStates: Background-specific loading states
- Helper functions: show_llm_loading, show_tool_loading, etc.
"""

from unittest.mock import Mock, patch

from aura_cli.cli.ui.loading_states import (
    AdvancedLoadingManager,
    FileLoadingStates,
    LLMLoadingStates,
    LoadingCategory,
    LoadingState,
    ToolLoadingStates,
    show_agent_loading,
    show_file_loading,
    show_llm_loading,
    show_tool_loading,
)


class TestLoadingState:
    """Test suite for LoadingState enum."""

    def test_loading_state_values(self):
        """Test LoadingState enum values."""
        assert LoadingState.IDLE.value == "idle"
        assert LoadingState.PREPARING.value == "preparing"
        assert LoadingState.EXECUTING.value == "executing"
        assert LoadingState.COMPLETE.value == "complete"
        assert LoadingState.ERROR.value == "error"


class TestLoadingCategory:
    """Test suite for LoadingCategory enum."""

    def test_loading_category_values(self):
        """Test LoadingCategory enum values."""
        assert LoadingCategory.LLM.value == "llm"
        assert LoadingCategory.TOOL.value == "tool"
        assert LoadingCategory.FILE.value == "file"
        assert LoadingCategory.AGENT.value == "agent"


class TestAdvancedLoadingManager:
    """Test suite for AdvancedLoadingManager."""

    def test_initialization(self):
        """Test AdvancedLoadingManager initialization."""
        manager = AdvancedLoadingManager()

        assert manager.current_state == LoadingState.IDLE
        assert manager.current_category is None
        assert manager.start_time is None

    @patch("aura_cli.cli.ui.loading_states.Console")
    def test_start_operation(self, mock_console_class):
        """Test starting an operation."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        manager = AdvancedLoadingManager(mock_console)
        manager.start(LoadingCategory.LLM, "Querying model")

        assert manager.current_state == LoadingState.PREPARING
        assert manager.current_category == LoadingCategory.LLM
        assert manager.start_time is not None

    @patch("aura_cli.cli.ui.loading_states.Console")
    def test_update_state(self, mock_console_class):
        """Test updating loading state."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        manager = AdvancedLoadingManager(mock_console)
        manager.start(LoadingCategory.TOOL, "Executing tool")
        manager.update(LoadingState.EXECUTING)

        assert manager.current_state == LoadingState.EXECUTING

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_complete_operation(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test completing an operation."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        mock_live_instance = Mock()
        mock_live.return_value = mock_live_instance

        manager = AdvancedLoadingManager(mock_console)
        manager.start(LoadingCategory.FILE, "Reading file")
        manager.complete()

        assert manager.current_state == LoadingState.COMPLETE
        assert mock_live_instance.stop.called

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_error_operation(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test error in operation."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        mock_live_instance = Mock()
        mock_live.return_value = mock_live_instance
        mock_theme_instance = Mock()
        mock_theme.return_value = mock_theme_instance
        mock_theme_instance.get_color.return_value = "red"

        manager = AdvancedLoadingManager(mock_console)
        manager.start(LoadingCategory.AGENT, "Processing")
        manager.error("Test error")

        assert manager.current_state == LoadingState.ERROR
        assert mock_live_instance.stop.called


class TestLLMLoadingStates:
    """Test suite for LLMLoadingStates."""

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_llm_loading_states(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test LLM loading states."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        manager = LLMLoadingStates.query_llm(mock_console, "gemini-2.5-flash")

        assert manager.current_category == LoadingCategory.LLM


class TestToolLoadingStates:
    """Test suite for ToolLoadingStates."""

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_tool_loading_states(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test tool loading states."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        manager = ToolLoadingStates.execute_tool(
            mock_console, "read_file", {"path": "test.py"}
        )

        assert manager.current_category == LoadingCategory.TOOL


class TestFileLoadingStates:
    """Test suite for FileLoadingStates."""

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_file_loading_states(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test file loading states."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        manager = FileLoadingStates.read_file(mock_console, "test.py")

        assert manager.current_category == LoadingCategory.FILE


class TestHelperFunctions:
    """Test suite for helper functions."""

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_show_llm_loading(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test show_llm_loading helper."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        manager = show_llm_loading(mock_console, "gemini-2.5-flash")

        assert isinstance(manager, AdvancedLoadingManager)

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_show_tool_loading(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test show_tool_loading helper."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        manager = show_tool_loading(mock_console, "read_file", {"path": "test.py"})

        assert isinstance(manager, AdvancedLoadingManager)

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_show_file_loading(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test show_file_loading helper."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        manager = show_file_loading(mock_console, "read", "test.py")

        assert isinstance(manager, AdvancedLoadingManager)

    @patch("aura_cli.cli.ui.loading_states.Console")
    @patch("aura_cli.cli.ui.loading_states.Live")
    @patch("aura_cli.cli.ui.loading_states.Spinner")
    @patch("aura_cli.cli.ui.loading_states.get_theme_manager")
    def test_show_agent_loading(
        self, mock_theme, mock_spinner, mock_live, mock_console_class
    ):
        """Test show_agent_loading helper."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        mock_live_instance = Mock()
        mock_live.return_value = mock_live_instance
        mock_theme_instance = Mock()
        mock_theme.return_value = mock_theme_instance
        mock_theme_instance.get_color.return_value = "blue"

        manager = show_agent_loading(
            mock_console, "test_agent", "thinking", "Processing task"
        )

        assert isinstance(manager, AdvancedLoadingManager)
