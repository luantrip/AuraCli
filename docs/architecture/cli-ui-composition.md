# CLI UI composition (operational rendering)

```text
cli/ui/
├── manager.py              # UIManager facade
├── rendering.py            # RenderCoordinator (+ render_component)
├── events.py               # UIEventManager (AGI/Ops events → windows)
├── display_facade.py       # display_* for workers
├── command_completer.py    # prompt_toolkit (uses cli/commands/slash_registry)
└── composition/
    ├── operational_surface.py   # status queue, sub-agent, tool panel, feeds
    ├── dashboard_surface.py     # /dashboard registry + render
    └── task_composite.py        # AgiTaskWindow + ToolExecutionPanel

cli/commands/
└── slash_registry.py       # TUI slash_commands + extras CLI

components/ (renderables)
├── subagent_panel.py       # paralelo / workflow steps
├── tool_execution_panel.py # agrupa tool calls (tool_panel_helper)
├── worker_feed.py          # AGI/Ops activity feed
├── agi_task_window.py      # janela por task_id (events.py)
└── tool_result.py / tool_header.py  # inline tool output
```

## Operation flow

1. **Slash input** — `CommandCompleter` ← `slash_registry` (alinhado ao TUI).
2. **Tool loop** — `tool_execution.py` → `ToolResult` / `ToolExecutionPanel` via `publish_tool_execution_panel`.
3. **AGI/Ops worker** — eventos `AgiEvent` → `UIEventManager`:
   - `render_task_composite_surface` (janela + painel de tools quando panel mode)
   - `describe_operational_event` → `render_operational_feedback`
4. **Workflow paralelo** — `SubAgentPanel` via `publish_subagent_panel(status_queue)`.
5. **Workers background** — `publish_agent_status` → `parse_status_messages` → `render_worker_feeds` em `handle_status_updates`.

## Settings no CLI

`/settings` with `TextualUIManager` active → `show_settings_menu_routed()` (native TUI). Otherwise → `key_manager` menu.

## Dashboard

`/dashboard <subcmd>` → `dashboard_surface.render_dashboard_subcommand` (single registry compartilhado com `handle_dashboard`).

## Planned extensions

- Accumulate queue updates only as `WorkerActivityFeed` (no fallback `create_status_panel`).
- Live dashboard during AGI execution (currently: separate thread + slash command).
