"""TUI widgets package for Aura CLI.

Re-exports all reusable Textual components: chat log, input bar, status
sidebar, loading indicators, charts, dialogs, IDE panels, spinners,
command palette, and monitoring/analysis panels.
"""

from aura_cli.tui.widgets.aura_text_area import AuraTextArea
from aura_cli.tui.widgets.autocomplete_input import (
    AutocompleteInput,
    CommandCompletionProvider,
    CompletionItem,
    CompletionProvider,
    HistoryCompletionProvider,
)
from aura_cli.tui.widgets.charts import (
    ASCIILineChart,
    BarChart,
    MetricGauge,
    MiniSparkline,
    StatsDisplay,
    VerticalBarChart,
)
from aura_cli.tui.widgets.chat import AuraChatLog
from aura_cli.tui.widgets.code_analysis_panel import CodeAnalysisPanel
from aura_cli.tui.widgets.command_palette import (
    Command,
    CommandPalette,
    CommandRegistry,
    get_command_registry,
    register_command,
)
from aura_cli.tui.widgets.delegation_panel import DelegationPanel, DelegationSnapshot
from aura_cli.tui.widgets.dialogs import (
    BaseDialog,
    ConfirmDialog,
    DialogProvider,
    DialogResult,
    FatalErrorDialog,
    InputDialog,
    SelectDialog,
)
from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel
from aura_cli.tui.widgets.footer import AuraFooter, AuraKeyHint
from aura_cli.tui.widgets.ide_panel import (
    CodeIssue,
    FileTreePanel,
    IDEPanel,
    IssueSeverity,
    IssuesPanel,
    RefactoringAction,
    RefactoringPanel,
)
from aura_cli.tui.widgets.imagination_panel import (
    CategoryBreakdown,
    ExtensionCloud,
    HolographicHeader,
    ImaginationCompact,
    ImaginationPanel,
    RecentActivity,
    ScanStats,
    ScanStatus,
)
from aura_cli.tui.widgets.input import AuraInputBar
from aura_cli.tui.widgets.knight_rider_spinner import (
    CompactSpinner,
    KnightRiderSpinner,
    ProgressSpinner,
)
from aura_cli.tui.widgets.loading import AuraLoadingIndicator, AuraProgressBar
from aura_cli.tui.widgets.memory_browser import MemoryBrowser
from aura_cli.tui.widgets.message_bubble import (
    MessageBubble,
    MessageMetadata,
    MessageType,
    Reaction,
    StreamingBubble,
    ThinkingBubble,
)
from aura_cli.tui.widgets.metrics_panel import MetricsPanel
from aura_cli.tui.widgets.rich_input import PromptPart, PromptState, RichPromptInput
from aura_cli.tui.widgets.settings_panel import LLMSettings, LLMSettingsPanel
from aura_cli.tui.widgets.snippets import (
    SnippetInfo,
    SnippetManager,
    get_snippet_manager,
)
from aura_cli.tui.widgets.status import AuraStatusSidebar
from aura_cli.tui.widgets.test_runner_panel import (
    TestResult,
    TestRunnerPanel,
    TestStatus,
)
from aura_cli.tui.widgets.toast import AuraToast, AuraToastContainer
from aura_cli.tui.widgets.todo_panel import AuraTodoPanel, TaskItem, TaskStatus
from aura_cli.tui.widgets.tool_registry_panel import (
    ToolInfo,
    ToolRegistryPanel,
    ToolStatus,
)
from aura_cli.tui.widgets.workflow_monitor import (
    Workflow,
    WorkflowMonitor,
    WorkflowStep,
)

__all__ = [
    "ASCIILineChart",
    "AuraChatLog",
    "AuraFooter",
    "AuraInputBar",
    "AuraKeyHint",
    "AuraLoadingIndicator",
    "AuraProgressBar",
    "AuraStatusSidebar",
    "AuraTextArea",
    "AuraToast",
    "AuraToastContainer",
    "AutocompleteInput",
    "BarChart",
    "BaseDialog",
    "CategoryBreakdown",
    "CodeAnalysisPanel",
    "CodeIssue",
    "Command",
    "CommandCompletionProvider",
    "CommandPalette",
    "CommandRegistry",
    "CompactSpinner",
    "CompletionItem",
    "CompletionProvider",
    "ConfirmDialog",
    "DelegationPanel",
    "DelegationSnapshot",
    "DialogProvider",
    "DialogResult",
    "EventStreamPanel",
    "ExtensionCloud",
    "FatalErrorDialog",
    "FileTreePanel",
    "HistoryCompletionProvider",
    "HolographicHeader",
    "IDEPanel",
    "ImaginationCompact",
    # Imagination Engine
    "ImaginationPanel",
    "InputDialog",
    "IssueSeverity",
    "IssuesPanel",
    "KnightRiderSpinner",
    "LLMSettings",
    "LLMSettingsPanel",
    "MemoryBrowser",
    "MessageBubble",
    "MessageMetadata",
    "MessageType",
    "MetricGauge",
    "MetricsPanel",
    "MiniSparkline",
    "ProgressSpinner",
    "PromptPart",
    "PromptState",
    "Reaction",
    "RecentActivity",
    "RefactoringAction",
    "RefactoringPanel",
    "RichPromptInput",
    "ScanStats",
    "ScanStatus",
    "SelectDialog",
    "SnippetInfo",
    "SnippetManager",
    "StatsDisplay",
    "StreamingBubble",
    "TestResult",
    "TestRunnerPanel",
    "TestStatus",
    "ThinkingBubble",
    "ToolInfo",
    "ToolRegistryPanel",
    "ToolStatus",
    "VerticalBarChart",
    "Workflow",
    "WorkflowMonitor",
    "WorkflowStep",
    "get_command_registry",
    "get_snippet_manager",
    "register_command",
]
