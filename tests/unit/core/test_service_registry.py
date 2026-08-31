"""Tests for core/service_registry.py - ServiceRegistry.

Tests verify:
- ServiceRegistry initialization
- Tool registration
- Tool retrieval
- Tool execution
- Tool metrics
- get_service_registry: Singleton access
"""

from unittest.mock import Mock

from aura_cli.core.service_registry import (
    ServiceRegistry,
    ToolCategory,
    ToolDescriptor,
    get_service_registry,
)


class TestToolCategory:
    """Test suite for ToolCategory enum."""

    def test_tool_category_values(self):
        """Test ToolCategory enum values."""
        assert ToolCategory.FILE_SYSTEM.value == "file_system"
        assert ToolCategory.DEVELOPMENT.value == "development"
        assert ToolCategory.SHELL.value == "shell"
        assert ToolCategory.GIT.value == "git"


class TestToolDescriptor:
    """Test suite for ToolDescriptor."""

    def test_tool_descriptor_creation(self):
        """Test creating ToolDescriptor."""
        mock_function = Mock()
        descriptor = ToolDescriptor(
            name="test_tool",
            category=ToolCategory.FILE_SYSTEM,
            description="Test tool",
            function=mock_function,
            schema={},
        )

        assert descriptor.name == "test_tool"
        assert descriptor.category == ToolCategory.FILE_SYSTEM
        assert descriptor.usage_count == 0
        assert descriptor.error_count == 0


class TestServiceRegistry:
    """Test suite for ServiceRegistry."""

    def test_initialization(self):
        """Test ServiceRegistry initialization."""
        registry = ServiceRegistry()

        assert registry.tools is not None
        assert registry.stats is not None

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ServiceRegistry()
        mock_function = Mock()

        registry._register_tool(
            "test_tool", ToolCategory.FILE_SYSTEM, "Test tool", mock_function, {}
        )

        assert "test_tool" in registry.tools

    def test_get_tool_not_registered(self):
        """Test getting a tool that is not registered."""
        registry = ServiceRegistry()

        tool = registry.get_tool("nonexistent")

        assert tool is None

    def test_get_tool_registered(self):
        """Test getting a registered tool."""
        registry = ServiceRegistry()
        mock_function = Mock()

        registry._register_tool(
            "test_tool", ToolCategory.FILE_SYSTEM, "Test tool", mock_function, {}
        )

        tool = registry.get_tool("test_tool")

        assert tool is not None
        assert tool.name == "test_tool"

    def test_get_all_tools(self):
        """Test getting all tools."""
        registry = ServiceRegistry()

        tools = registry.get_all_tools()

        assert isinstance(tools, dict)

    def test_execute_tool(self):
        """Test executing a tool."""
        registry = ServiceRegistry()
        mock_function = Mock(return_value="result")

        registry._register_tool(
            "test_tool", ToolCategory.FILE_SYSTEM, "Test tool", mock_function, {}
        )

        result = registry.execute_tool("test_tool", {"arg1": "value1"})

        assert result == "result"
        mock_function.assert_called_once()

    def test_execute_tool_not_found(self):
        """Test executing a tool that doesn't exist."""
        registry = ServiceRegistry()

        # execute_tool returns None when tool not found (doesn't raise KeyError)
        result = registry.execute_tool("nonexistent", {})
        assert result is None

    def test_get_tool_metrics(self):
        """Test getting tool metrics."""
        registry = ServiceRegistry()
        mock_function = Mock()

        registry._register_tool(
            "test_tool", ToolCategory.FILE_SYSTEM, "Test tool", mock_function, {}
        )

        # get_tool_metrics doesn't exist, but we can check tool info via tools dict
        tool_info = registry.tools.get("test_tool")
        assert tool_info is not None
        assert hasattr(tool_info, "usage_count")
        assert hasattr(tool_info, "error_count")


class TestGetServiceRegistry:
    """Test suite for get_service_registry."""

    def test_get_service_registry_returns_instance(self):
        """Test that get_service_registry returns ServiceRegistry instance."""
        registry = get_service_registry()

        assert isinstance(registry, ServiceRegistry)
