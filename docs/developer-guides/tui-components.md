# Aura CLI TUI Components

## Overview

This document describes the Textual TUI widget library used by Aura CLI.
Components are organised in `aura_cli/tui/widgets/`.

**Version:** 0.1.0
**Last Updated:** 2026

---

## 📁 Directory Structure

```
aura_cli/tui/
├── core/                          # Core Systems
│   ├── __init__.py
│   ├── event_bus.py              # Typed Event Bus with Pydantic
│   ├── sync_store.py             # Reactive State Store
│   ├── sync_manager.py           # Async Sync with Batching
│   ├── router.py                 # Navigation System
│   └── error_handler.py          # Global Error Handling
├── keybinds/                      # Keybinding System
│   ├── __init__.py
│   ├── keybind_manager.py        # Leader Key + Manager
│   └── keybind_config.py         # Configuration
├── utils/                         # Utilities
│   ├── __init__.py
│   ├── terminal_detector.py      # Terminal Detection
│   └── clipboard_utils.py        # Clipboard Operations
├── widgets/
│   ├── knight_rider_spinner.py   # Animation Widget
│   ├── rich_input.py             # Rich Prompt Input
│   ├── command_palette.py        # Command Palette
│   └── dialogs/                   # Dialog System
│       ├── base_dialog.py
│       ├── confirm_dialog.py
│       ├── input_dialog.py
│       ├── select_dialog.py
│       └── error_dialog.py
└── styles/
    └── nebula.tcss               # Updated Styles
```

---

## 🔧 Core Systems

### Event Bus (`core/event_bus.py`)

A typed event system with Pydantic validation, enabling type-safe communication between TUI components.

```python
from aura_cli.tui.core.event_bus import TUIEventBus, TUIEvents
from pydantic import BaseModel

# Define event schema
class MessagePayload(BaseModel):
    text: str
    sender: str

# Create event definition
bus = TUIEventBus()
MessageEvent = bus.define("chat.message", MessagePayload)

# Subscribe
def on_message(payload):
    print(f"{payload['sender']}: {payload['text']}")

unsub = bus.subscribe("chat.message", on_message)

# Publish (validates automatically)
bus.publish("chat.message", {"text": "Hello!", "sender": "User"})

# Unsubscribe
unsub()

# Pre-defined events
TUIEvents.bus.publish("tui.toast.show", {
    "message": "Hello!",
    "severity": "success"
})
```

### Sync Store (`core/sync_store.py`)

A reactive state store with path-based access and change notifications.

```python
from aura_cli.tui.core.sync_store import SyncStore, get_store

store = get_store()  # Global instance

# Set nested values using dot notation
store.set("tasks.task_1.status", "running")
store.set("ui.focused_task", "task_1")

# Get values
status = store.get("tasks.task_1.status")  # "running"
default = store.get("missing.path", "default")  # "default"

# Subscribe to changes
def on_task_change(path, value):
    print(f"Changed: {path} = {value}")

unsub = store.subscribe("tasks", on_task_change)

# Batch updates (single notification)
with store.batch_update():
    store.set("tasks.task_1.status", "complete")
    store.set("tasks.task_1.result", "success")

# Snapshot and restore
snapshot = store.snapshot("Before operation")
# ... make changes ...
store.restore(snapshot)  # Rollback
```

### Screen registry (`shell/screen_registry.py`)

The central navigation registry resolves stable screen identifiers and route
aliases while keeping screen imports lazy.

```python
from aura_cli.tui.shell.screen_registry import ScreenId, open_screen, navigate_route

# Open a registered screen
open_screen(app, ScreenId.SETTINGS)

# Navigate through a public route alias
navigate_route(app, "settings")

# Return to the previous screen
app.pop_screen()
```

Screen-specific state and callbacks stay in the screen or its presentation
adapter; the registry is responsible only for resolution and composition.

### Error Handler (`core/error_handler.py`)

Global error handling with recovery options.

```python
from aura_cli.tui.core.error_handler import TUIErrorHandler, handle_error

handler = TUIErrorHandler(app)

# Handle errors
try:
    risky_operation()
except Exception as e:
    error_info = handler.handle_error(e, context="risky_operation")

# Context manager
with handler.catch_errors("widget_render"):
    render_widget()

# Error callbacks
handler.on_error(lambda e: log_error(e))

# GitHub issue integration
handler.open_github_issue(error_info)
```

---

## ⌨️ Keybinding System

### Leader Key Manager (`keybinds/keybind_manager.py`)

Multi-key sequences inspired by Vim/tmux.

```python
from aura_cli.tui.keybinds import KeybindManager, KeybindInfo, LeaderKeyManager

manager = KeybindManager(app)

# Register direct keybind
manager.register(KeybindInfo(
    key="ctrl+s",
    action="save",
    description="Save session"
))

# Register leader sequence (<leader> + key)
manager.register(KeybindInfo(
    key="<leader> g",
    action="show_delegates",
    description="Show delegated task follow-up"
))

# Default leader key is Ctrl+Space
# Press Ctrl+Space, then 'g' to trigger show_delegates
```

### Default Keybindings

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+C` | quit | Quit application |
| `Ctrl+L` | clear_chat | Clear chat |
| `Ctrl+P` | command_palette | Open command palette |
| `Ctrl+E` | toggle_panel | Toggle analysis/events |
| `Ctrl+Space` | leader_key | Activate leader mode |
| `<leader> g` | show_delegates | Show delegated tasks |
| `<leader> e` | show_events | Show event stream |
| `<leader> b` | show_memory | Show memory browser |
| `<leader> w` | show_workflows | Show workflow demo |
| `<leader> h` | show_help | Show help |

---

## 🛠️ Utilities

### Terminal Detector (`utils/terminal_detector.py`)

Detects terminal characteristics for optimal theming.

```python
from aura_cli.tui.utils.terminal_detector import (
    TerminalDetector,
    detect_background_color,
    get_optimal_theme
)

# Detect terminal info
detector = TerminalDetector()
info = detector.detect()

print(info.background)        # "dark" or "light"
print(info.supports_truecolor) # True/False
print(info.terminal_program)   # e.g., "iterm.app"

# Convenience functions
bg = detect_background_color()  # "dark", "light", "unknown"
theme = get_optimal_theme()     # "nebula-dark" or "nebula-light"
```

### Clipboard Manager (`utils/clipboard_utils.py`)

Cross-platform clipboard operations with smart detection.

```python
from aura_cli.tui.utils.clipboard_utils import ClipboardManager, get_clipboard

manager = ClipboardManager()

# Basic operations
manager.copy("Hello, World!")
text = manager.paste()

# Smart paste (detects content type)
content = manager.paste_smart()
if content.is_file_path:
    print(f"File: {content.content}")
elif content.is_large_text:
    print(f"Large text: {content.metadata['lines']} lines")
```

---

## 🎨 Widgets

### Knight Rider Spinner (`widgets/knight_rider_spinner.py`)

Sophisticated loading animation.

```python
from aura_cli.tui.widgets import KnightRiderSpinner, CompactSpinner

# Full spinner
spinner = KnightRiderSpinner(
    width=30,
    style="block",  # block, diamond, dot, wave, pulse
    color="#00d9ff",
    message="Processing..."
)

# Compact spinner
compact = CompactSpinner(message="Loading")

# Progress spinner
from aura_cli.tui.widgets import ProgressSpinner
progress = ProgressSpinner(message="Uploading")
progress.set_progress(0.5, "50% complete")
```

### Rich Prompt Input (`widgets/rich_input.py`)

Advanced input with file/image paste detection.

```python
from aura_cli.tui.widgets import RichPromptInput, PromptPart

prompt = RichPromptInput(
    placeholder="Type a command...",
    on_submit=handle_submit
)

# Supports:
# - File paste detection -> shows [📄 filename]
# - Image paste detection -> shows [🖼️ image]
# - Large text summarization -> shows [📝 Pasted (~N lines)]
# - External editor (Ctrl+E)
# - History navigation (Up/Down)
# - Multiline mode (triple quotes)
```

### Command Palette (`widgets/command_palette.py`)

VS Code-style command palette.

```python
from aura_cli.tui.widgets import CommandPalette, CommandRegistry, Command

registry = CommandRegistry()
registry.register(Command(
    id="my_command",
    name="My Command",
    description="Does something",
    keybind="ctrl+m",
    category="tools"
))

# Toggle palette with Ctrl+P
palette = CommandPalette(registry=registry)

# Features:
# - Fuzzy search
# - Keyboard navigation
# - Recently used tracking
# - Category grouping
```

### Dialog System (`widgets/dialogs/`)

Modal dialog components.

```python
from aura_cli.tui.widgets.dialogs import (
    ConfirmDialog,
    InputDialog,
    SelectDialog,
    FatalErrorDialog
)

# Confirm dialog
confirm = ConfirmDialog(
    message="Delete this file?",
    title="Confirm Delete",
    on_confirm=lambda: delete_file()
)

# Input dialog
input_dlg = InputDialog(
    prompt="Enter filename:",
    title="New File",
    validator=lambda x: len(x) > 0
)

# Select dialog
from aura_cli.tui.widgets.dialogs.select_dialog import SelectOption
select = SelectDialog(
    title="Choose Model",
    options=[
        SelectOption("gpt4", "GPT-4", "Most capable", "🧠"),
        SelectOption("claude", "Claude 3", "Best for code", "🤖"),
    ]
)

# Error dialog
error = FatalErrorDialog(
    error_info={"error_type": "RuntimeError", "message": "..."},
    on_reset=reset_app,
    on_report=open_github_issue
)
```

---

## 📊 Testing

All components have comprehensive tests in `tests/unit/ui/test_tui_evolution.py`:

```bash
# Run all TUI evolution tests
python -m pytest tests/unit/ui/test_tui_evolution.py -v

# Run specific test class
python -m pytest tests/unit/ui/test_tui_evolution.py::TestTUIEventBus -v
```

**Test Coverage:**
- 52 tests covering all new components
- Event Bus: 8 tests
- Sync Store: 8 tests
- Router: 6 tests
- Error Handler: 6 tests
- Keybinds: 6 tests
- Terminal Detector: 3 tests
- Clipboard Utils: 2 tests
- Widgets: 11 tests
- Integration: 2 tests

---

## 🔗 Integration with AuraTUI

The app.py has been updated to integrate all new systems:

```python
class AuraTUI(App):
    def __init__(self, ...):
        # Initialize new systems
        self.store = get_store()
        self.error_handler = TUIErrorHandler(self)
        self.keybind_manager = KeybindManager(self)
        
        # Subscribe to TUI events
        TUIEvents.bus.subscribe("tui.toast.show", self._on_toast)
        TUIEvents.bus.subscribe("tui.command.execute", self._on_command)
    
    def compose(self):
        # ... existing widgets ...
        yield CommandPalette(id="command_palette")
    
    def action_toggle_command_palette(self):
        self.query_one("#command_palette").toggle()
    
    def action_leader_key(self):
        self.keybind_manager.leader.enter_leader_mode()
```

---

## 📈 Metrics

| Component | Lines of Code | Test Count |
|-----------|--------------|------------|
| Event Bus | ~450 | 8 |
| Sync Store | ~350 | 8 |
| Sync Manager | ~280 | - |
| Router | ~300 | 6 |
| Error Handler | ~320 | 6 |
| Keybind Manager | ~400 | 6 |
| Terminal Detector | ~250 | 3 |
| Clipboard Utils | ~200 | 2 |
| Knight Rider Spinner | ~250 | 4 |
| Rich Input | ~350 | 2 |
| Command Palette | ~400 | 3 |
| Dialogs | ~500 | 2 |
| **Total** | **~4,050** | **52** |

---

## 🆕 Phase 2 Implementations (Latest)

### Theme System (`styles/themes.py`)

Dynamic theme management with light/dark mode support and terminal detection.

```python
from aura_cli.tui.styles.themes import (
    ThemeManager, get_theme_manager, Theme, ThemeMode,
    NEBULA_DARK, NEBULA_LIGHT, DRACULA, MIDNIGHT
)

# Get global theme manager
manager = get_theme_manager()

# Set theme
manager.set_theme("dracula")  # or "nebula-dark", "nebula-light", etc.
manager.set_theme("auto")  # Auto-detect from terminal

# Toggle light/dark
manager.toggle_mode()

# Subscribe to theme changes
unsub = manager.subscribe(lambda theme: print(f"Theme: {theme.name}"))

# Create custom theme
custom = Theme(
    name="My Theme",
    mode=ThemeMode.DARK,
    colors=ThemeColors(
        background="#1e1e2e",
        primary="#89b4fa",
        # ... other colors
    )
)
manager.register_theme(custom)

# Available themes
themes = manager.available_themes  # ["nebula-dark", "nebula-light", ...]
```

### Plugin SDK (`plugins/sdk.py`)

Complete SDK for building custom TUI plugins with event integration.

```python
from aura_cli.tui.plugins.sdk import (
    PluginWidget, PluginInfo, plugin_command, on_event,
    register_plugin, get_plugin_registry
)

@register_plugin("my-analytics", version="1.0.0", description="Analytics dashboard")
class AnalyticsPlugin(PluginWidget):
    """Custom analytics plugin."""
    
    def compose(self):
        from textual.widgets import Static
        yield Static("📊 Analytics Dashboard")
    
    def on_plugin_mount(self):
        self.log.info("Analytics plugin loaded!")
    
    @plugin_command("refresh", "Refresh analytics data", keybind="ctrl+r")
    def refresh_data(self):
        self.show_toast("Refreshing analytics...")
        self.emit_event("data.refreshed", {"timestamp": "now"})
    
    @on_event("tui.theme.changed")
    def handle_theme_change(self, payload):
        self.log.info(f"Theme changed: {payload.get('theme_name')}")

# Using the plugin
registry = get_plugin_registry()
instance = registry.instantiate("my-analytics")
```

### Keybind Persistence (`keybinds/keybind_config.py`)

Advanced keybind management with profiles, undo/redo, and import/export.

```python
from aura_cli.tui.keybinds import (
    KeybindPersistence, get_keybind_persistence
)

# Get global persistence manager
persistence = get_keybind_persistence()

# Set keybind (auto-saved)
persistence.set_keybind(
    key="ctrl+shift+n",
    action="new_file",
    description="Create new file",
    category="file"
)

# Remove keybind
persistence.remove_keybind("ctrl+shift+n")

# Undo/Redo
persistence.undo()
persistence.redo()

# Profiles
persistence.save_profile("vim-style")
persistence.load_profile("vim-style")
profiles = persistence.list_profiles()  # ["default", "vim-style"]
persistence.delete_profile("vim-style")

# Import/Export
persistence.export_keybinds(Path("~/keybinds-backup.json"))
persistence.import_keybinds(Path("~/keybinds-backup.json"), merge=True)

# Reset to defaults
persistence.reset_to_defaults()

# Get keybinds by category
file_keybinds = persistence.get_keybinds_by_category("file")
```

### SyncManager Integration (`bridge.py`)

Bridge now uses SyncManager for efficient event synchronization.

```python
from aura_cli.tui.bridge import TextualUIManager

# Create bridge with SyncManager
bridge = TextualUIManager(app, status_queue=queue, stats=stats)

# SyncManager is automatically initialized
assert bridge.sync_manager is not None
assert bridge.sync_manager.is_running

# Get sync metrics
metrics = bridge.get_sync_metrics()
# {
#     "events_processed": 150,
#     "batches_processed": 30,
#     "last_batch_time": "2024-11-27T10:30:00",
#     "pending_events": 0,
#     "running": True
# }

# Stop when done
bridge.stop()
```

---

## 📊 Updated Metrics

| Component | Lines of Code | Test Count |
|-----------|--------------|------------|
| Event Bus | ~615 | 8 |
| Sync Store | ~425 | 8 |
| Sync Manager | ~435 | - |
| Router | ~437 | 6 |
| Error Handler | ~456 | 6 |
| Keybind Manager | ~555 | 6 |
| Keybind Persistence | ~370 | 3 |
| Terminal Detector | ~377 | 3 |
| Clipboard Utils | ~354 | 2 |
| Knight Rider Spinner | ~384 | 4 |
| Rich Input | ~477 | 2 |
| Command Palette | ~454 | 3 |
| Dialogs | ~950 | 5 |
| Theme System | ~450 | 2 |
| Plugin SDK | ~450 | 2 |
| **Total** | **~7,189** | **60** |

**Note:** Line counts are approximate as of 2026 and will drift as the codebase evolves.

---

## Implemented Components

The following features are implemented and available:

- Leader Key System
- Rich Prompt Input
- Sync Manager + Store
- Terminal Theme Detection (Light/Dark)
- Error Handler
- Typed Event Bus
- Command Palette
- Knight Rider Spinner
- Dialog System
- Router System
- SyncManager Bridge Integration
- Dynamic Theme System
- Plugin SDK
- Keybind Persistence with Profiles

---

*Aura CLI — TUI Components Reference*
