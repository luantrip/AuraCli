"""Abstract base class for CLI UI components (Rich layer only).

ComponentBase defines the render() → RenderableType contract for all
reusable Rich-based components. TUI (Textual) widgets use their own base
in aura_cli/tui/widgets/ and are incompatible with this ABC.
"""

from abc import ABC, abstractmethod
from typing import Any

from rich.console import RenderableType


class ComponentBase(ABC):
    """
    Abstract base class for all UI components.

    Forces implementation of `render` method, ensuring consistent
    interface for component rendering across all UI components.

    Example:
        >>> class CustomComponent(ComponentBase):
        ...     def render(self):
        ...         return Text("Custom content")
    """

    @abstractmethod
    def render(self, *args: Any, **kwargs: Any) -> RenderableType:
        """
        Render component and return Rich-renderable object.

        This method must be implemented by all subclasses to provide
        component-specific rendering logic.

        Args:
            *args: Positional arguments for rendering
            **kwargs: Keyword arguments for rendering

        Returns:
            Rich-renderable object (Panel, Text, Table, etc.)

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError
