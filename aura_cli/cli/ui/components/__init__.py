"""CLI UI components — input, display, layout, and agent sub-packages.

For new code, import directly from the sub-package:
    from aura_cli.cli.ui.components.input import BaseComponent
    from aura_cli.cli.ui.components.display import MessageBubble
    from aura_cli.cli.ui.components.layout import StatusBar
    from aura_cli.cli.ui.components.agent import TaskBoard
"""

# Re-export everything from sub-packages for backwards compatibility
from aura_cli.cli.ui.components.agent import *  # noqa: F403
from aura_cli.cli.ui.components.display import *  # noqa: F403
from aura_cli.cli.ui.components.input import *  # noqa: F403
from aura_cli.cli.ui.components.layout import *  # noqa: F403
