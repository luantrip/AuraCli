"""
Modern Chat System for Aura CLI.

This module provides a complete, modern chat interface with:
- Enhanced message bubbles with glass-morphism
- Avatar system for visual identity
- Streaming text renderer for LLM responses
- Context menus for quick actions
- Reactions and threading support
- Code blocks with syntax highlighting
"""

from aura_cli.cli.ui.components.animated_spinner import (
    AnimatedSpinner,
    SpinnerConfig,
    SpinnerFactory,
    SpinnerStyle,
)
from aura_cli.cli.ui.components.code_block_enhanced import (
    CodeBlockConfig,
    CodeBlockEnhanced,
    render_code,
)
from aura_cli.cli.ui.components.context_menu import (
    ActionType,
    ContextAction,
    ContextMenu,
    QuickReactions,
    create_message_actions,
)
from aura_cli.cli.ui.components.message_bubble import (
    MessageBubble,
    MessageMetadata,
    MessageType,
    Reaction,
    StreamingBubble,
    ThinkingBubble,
)
from aura_cli.cli.ui.components.streaming_renderer import (
    StreamingConfig,
    StreamingTextRenderer,
    TypingIndicator,
    create_streaming_renderer,
)
from aura_cli.cli.ui.core.avatar_system import (
    Avatar,
    AvatarStyle,
    AvatarSystem,
    get_avatar_system,
)
from aura_cli.cli.ui.core.icon_set import (
    IconSet,
    IconSetType,
    detect_icon_support,
    get_icon_set,
)
from aura_cli.cli.ui.core.styled_text import StyledTextEngine, get_styled_text_engine

__all__ = [
    "ActionType",
    "AnimatedSpinner",
    "Avatar",
    "AvatarStyle",
    "AvatarSystem",
    "CodeBlockConfig",
    "CodeBlockEnhanced",
    "ContextAction",
    "ContextMenu",
    "IconSet",
    "IconSetType",
    "MessageBubble",
    "MessageMetadata",
    "MessageType",
    "QuickReactions",
    "Reaction",
    "SpinnerConfig",
    "SpinnerFactory",
    "SpinnerStyle",
    "StreamingBubble",
    "StreamingConfig",
    "StreamingTextRenderer",
    "StyledTextEngine",
    "ThinkingBubble",
    "TypingIndicator",
    "create_message_actions",
    "create_streaming_renderer",
    "detect_icon_support",
    "get_avatar_system",
    "get_icon_set",
    "get_styled_text_engine",
    "render_code",
]
