# TUI window composition (modals, tools, registry)

```text
tui/
├── commands/                 # slash_commands.py — single source for slash commands
├── routing/                  # settings.py — /settings TUI vs CLI
├── services/                 # session sync, token snapshot
├── shell/                    # Composition and navigation
│   ├── base_modal.py         # BaseAuraModalScreen[T], BaseAuraResultModalScreen
│   ├── base_tool_screen.py   # BaseToolScreen (launchers)
│   ├── modal_frame.py        # ModalFrame, ModalTitle
│   ├── window_stack.py       # Screen vs overlay
│   ├── prompts.py            # push_confirm / push_input
│   └── screen_registry.py    # ScreenId → open_screen() / open_screen_wait()
├── screens/                  # Surfaces (thin — compose widgets)
├── widgets/
│   ├── layout/               # ToolScreenChrome, ExternalToolLauncher
│   ├── settings/             # ApiKeysSection
│   ├── constitution/         # ConstitutionWizardPanel
│   ├── diff/                 # DiffReviewPanel
│   ├── monitor/              # TabBar, AddressBar, ContentViewer, …
│   └── history/              # HistoryBrowserPanel, session_store
└── components/shared/        # Dialogs ModalScreen (Confirm, Input, …)
```

## Surface types

| Camada | Classe base | Exemplos |
|--------|-------------|----------|
| Modal com resultado | `BaseAuraResultModalScreen[T]` | Constitution, Diff (`ScreenId.DIFF_CONFIRM`) |
| Modal informativo | `BaseAuraModalScreen[None]` | Settings, Token usage |
| Ferramenta / launcher | `BaseToolScreen` | Paint, Files, Monitor, History |
| Overlay no chat | `DialogProvider` + `widgets/dialogs` | Erros inline |
| App standalone | `App` | `HistoryApp` (`run_history_browser`) |

**Sessions:** `SessionManager` saves `~/.aura/sessions/*.json`; the TUI mirrors `*.jsonl` and the browser (`/sessions`) reads both. Periodic auto-save + on Aura response + on exit (`Ctrl+C`). In the legacy CLI, `/history` is the console command history — in the TUI use `/sessions` for saved conversations.

**Settings:** With the TUI active (`TextualUIManager`), `/settings` in the processor calls `show_settings_menu_routed()` → `SettingsScreen`. Without TUI, the legacy `prompt_toolkit` menu.

**Monitor:**

| Command / action | Effect |
|----------------|--------|
| `monitor`, Ctrl+M, paleta “Monitor (browser)” | `MonitorScreen` embutido |
| `launch_monitor`, paleta “Monitor externo” | Suspende TUI, executa Chawan/`cha` |

## Abrir telas

```python
from aura_cli.tui.shell import ScreenId, open_screen, open_screen_wait

open_screen(app, ScreenId.SETTINGS)
open_screen(app, ScreenId.HISTORY)

action, content = await open_screen_wait(
    app,
    ScreenId.DIFF_CONFIRM,
    file_path="a.py",
    diff_lines=lines,
    new_content=text,
)
```

## Decompor um screen novo

1. Widgets em `widgets/<feature>/`.
2. Screen em `screens/` com `compose_body()` ou `compose_tool_body()`.
3. Registrar em `ScreenId` + `_build_screen`.
4. Estilos: classes `aura-modal-root`, `aura-tool-screen` em `styles/theme.tcss`.
