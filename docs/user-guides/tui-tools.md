# TUI Tools — User Guide

Aura CLI includes visual tools built into the terminal using Textual. This guide
covers AuraPaint, the File Manager, and the Monitor.

---

## Overview

The TUI environment provides three primary tools:

1. **AuraPaint** — native ANSI art editor with layers, animation, and an AI agent
2. **File Manager** — Dual-pane file manager in the style of Midnight Commander
3. **Monitor** — Terminal browser via the optional `aura-monitor` binary

Access all tools from the TUI:

```
› /tui
```

---

## AuraPaint

AuraPaint is AuraCli's native ANSI art editor. It is bundled with the project,
requires no separate `textual-paint` installation, and preserves compatibility
with legacy Textual Paint documents. The original MIT attribution remains in
the project acknowledgments.

### Features

#### Drawing Tools (16 tools)

- Pencil — freehand drawing
- Brush — variable-size brush
- Line — straight lines
- Rectangle — rectangles and squares
- Ellipse — circles and ellipses
- Polygon — multi-point polygons
- Fill — flood fill (bucket)
- Text — insert text with a character picker
- Eraser — erase content
- Spray — spray-paint effect
- Color Picker — sample colour from canvas
- Selection — select and move regions
- Crop — crop the canvas
- Resize — resize the canvas
- Rotate — rotate a selection
- Flip — flip horizontally or vertically

#### Layer System

- Unlimited layers
- Blend modes: Normal, Multiply, Screen, Overlay, Difference, and more
- Per-layer opacity control
- Drag-to-reorder layers
- Individual layer visibility and lock

#### Animation

- Frame-by-frame timeline control
- Onion skinning (preview previous/next frames)
- Playback controls: play, pause, step
- Frame management: add, duplicate, remove
- Export as GIF, video, or image sequence

#### AI Agent

- Generate ANSI art from a text prompt
- Palette and composition suggestions
- Auto-fill selected regions

#### Colour Management

- Full colour picker
- Customisable palettes
- Recent-colour history
- Gradient creation

#### Export Formats

| Format | Description |
|--------|-------------|
| ANSI | Native terminal art format |
| PNG | Raster image |
| SVG | Vector |
| HTML | Web export |
| TXT | Plain text |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+S` | Save |
| `Ctrl+O` | Open |
| `Ctrl+N` | New canvas |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+E` | Export |
| `Ctrl+L` | Layer panel |
| `Ctrl+T` | Timeline |
| `Space` | Play/pause animation |
| `←/→` | Previous/next frame |
| `+/-` | Zoom in/out |

### Workflow

1. Create a new canvas: `Ctrl+N` — set dimensions
2. Select a tool and draw
3. Add layers: `Ctrl+L` — organise the composition
4. Animate: `Ctrl+T` — add frames to the timeline
5. Export: `Ctrl+E` — choose the output format

---

## File Manager

Dual-pane file manager in the style of Midnight Commander, with support for
67 file-type icons.

### Features

- Dual-pane layout (two panels side by side)
- 67 file icons by type and extension
- Context menu with quick actions
- Operations: copy, cut, paste, rename, delete
- Create new files and directories
- Toggle hidden files
- File preview without opening
- Status bar with selected item information
- Properties panel (size, permissions, dates)

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Open file/directory |
| `Ctrl+N` | New file |
| `Ctrl+Shift+N` | New directory |
| `Ctrl+C` | Copy |
| `Ctrl+X` | Cut |
| `Ctrl+V` | Paste |
| `F2` | Rename |
| `Delete` | Delete |
| `Ctrl+H` | Toggle hidden files |
| `Ctrl+F` | Search |
| `Tab` | Switch between panels |
| `Esc` | Close |

### Workflow

1. Navigate the project structure in both panels
2. Use `Tab` to switch between panels
3. Copy/move files between panels with `Ctrl+C`/`Ctrl+X` and `Ctrl+V`
4. Preview file content before opening
5. Check properties for size and permissions

---

## Monitor

Integrated terminal browser via the `aura-monitor` binary.

> **Note:** `aura-monitor` is an optional Nim binary. It must be built locally
> on platforms other than macOS x86_64, or compiled from source using
> `./scripts/build_nim.sh`. If the binary is absent, the Monitor tool is
> unavailable.

### Operation Modes

| Mode | Description |
|------|-------------|
| `browser` | Interactive terminal browser |
| `dump` | Plain-text content dump |
| `headless` | No-UI mode for automation |
| `watch` | Continuous page-change monitoring |

### Usage

```bash
# Interactive browser
aura-monitor browser https://example.com

# Content dump
aura-monitor dump https://example.com

# Headless (automation/scripts)
aura-monitor headless https://example.com --output result.txt

# Watch (polling for changes)
aura-monitor watch https://example.com --interval 30
```

From the TUI, invoke the Monitor via the command palette or directly from chat:

```
› /tui
# In the command palette: Monitor
```

---

## Cross-Tool Integration

### AuraPaint ↔ File Manager

- Open ANSI files from the File Manager directly in AuraPaint
- Save Paint exports and navigate to them in the File Manager
- Create visual assets and organise them through the directory structure

### Tools ↔ Aura CLI

- All tools are accessible from the main Aura CLI interface
- Shared context between tools and chat
- Unified command palette in the TUI

---

## Use Cases

### Creating ANSI Art

1. Open AuraPaint via `/tui`
2. Create a new canvas with the desired dimensions
3. Use drawing tools and layers
4. Add animation in the timeline if needed
5. Export as ANSI, PNG, or GIF

### Managing a Project

1. Open File Manager via `/tui`
2. Navigate the structure in the dual panels
3. Create, move, and organise files
4. Use preview to inspect content
5. Open assets in AuraPaint when needed

### Inspecting a Web Page

1. Invoke Monitor from the TUI or terminal
2. Choose the appropriate mode (browser, dump, headless, watch)
3. Navigate or extract content as needed

---

## Tips

1. Learn the keyboard shortcuts — they increase speed considerably
2. Use layers in Paint to organise complex compositions
3. Onion skinning makes smooth animations easier
4. In the File Manager, toggle hidden files (`Ctrl+H`) to reveal dotfiles
5. Monitor in watch mode is useful for tracking deployments and status pages
6. Combine File Manager + Paint for asset creation and organisation workflows

---

## Related Documentation

- [TUI Components](../developer-guides/tui-components.md) — Component library
- [Quick Start](./quick-start.md) — First steps
- [System Architecture](../architecture/system-architecture.md) — System architecture

---

**Version**: 0.1.0
**Last Updated**: 2026
