---
name: paint-agent-tool
description: Complete knowledge guide for the paint_generate_art tool - art generation capabilities, usage patterns, best practices, and integration with Aura CLI
version: 1.0.0
author: Aura Core Team
---

# 🎨 Paint Agent Tool - Complete Knowledge Guide

## Overview

The `paint_generate_art` tool allows the Aura CLI agent to generate ASCII art, diagrams, and visual content using the Paint Agent without requiring the Paint TUI application. This tool provides headless art generation capabilities that integrate seamlessly with the main CLI chat.

## Tool Information

**Name:** `paint_generate_art`  
**Category:** Development  
**Type:** Art Generation Tool  
**Mode:** Headless (no TUI required)

## Capabilities

### What It Can Do

1. **Generate ASCII Art**
   - Create text-based art from natural language descriptions
   - Support for complex ASCII art patterns
   - Multiple generation modes (auto, ascii, primitives, hybrid)

2. **Create Diagrams**
   - Architecture diagrams
   - Flow charts
   - Technical illustrations
   - UI mockups

3. **Generate Visual Content**
   - Logos and icons
   - Decorative elements
   - Documentation illustrations
   - Code visualization

4. **Multiple Output Formats**
   - ANSI (`.ans`) - Text-based, preserves colors
   - PNG (`.png`) - Raster image
   - SVG (`.svg`) - Vector graphics
   - HTML (`.html`) - Web-compatible

## Tool Parameters

### Required Parameters

- **`prompt`** (string): Description of art to generate
  - Examples:
    - "a cat"
    - "ASCII art of a house"
    - "diagram of a microservices architecture"
    - "logo for a tech startup"

### Optional Parameters

- **`width`** (integer, default: 80): Canvas width in characters
  - Range: 1-500 (recommended: 40-120)
  - Larger = more detail but slower generation

- **`height`** (integer, default: 24): Canvas height in characters
  - Range: 1-200 (recommended: 10-50)
  - Taller = more vertical space

- **`output_file`** (string, optional): File path to save result
  - If not provided: saves to `artes/arte_<timestamp>.<format>`
  - Directory is created automatically if it doesn't exist
  - Examples:
    - `"artes/logo.ans"`
    - `"docs/images/diagram.svg"`
    - `"assets/icon.png"`

- **`format`** (string, default: "ans"): Output format
  - Options: `"ans"`, `"png"`, `"svg"`, `"html"`
  - `"ans"`: Best for terminal viewing, preserves colors
  - `"png"`: Best for images, documentation
  - `"svg"`: Best for scalable graphics, web
  - `"html"`: Best for web pages, interactive content

- **`mode`** (string, default: "auto"): Generation mode
  - `"auto"`: LLM decides best approach (recommended)
  - `"ascii"`: Direct ASCII art generation (fast, text-focused)
  - `"primitives"`: Geometric shapes and structured drawings (precise)
  - `"hybrid"`: Combines ASCII and primitives (best quality, complex scenes)

## Usage Patterns

### Pattern 1: Simple ASCII Art

**When to use:** Simple text art, logos, icons

```python
paint_generate_art(prompt="a cat", width=40, height=20, format="ans")
```

**Best for:**
- Simple illustrations
- Text-based logos
- Quick visualizations

### Pattern 2: Detailed Diagrams

**When to use:** Architecture, flowcharts, technical diagrams

```python
paint_generate_art(
    prompt="microservices architecture diagram with API gateway, services, and database",
    width=120,
    height=40,
    format="svg",
    mode="primitives",
)
```

**Best for:**
- Technical documentation
- Architecture visualization
- Process flows

### Pattern 3: Complex Scenes

**When to use:** Detailed illustrations, complex compositions

```python
paint_generate_art(
    prompt="a detailed scene of a futuristic city with flying cars and neon lights",
    width=100,
    height=50,
    format="png",
    mode="hybrid",
)
```

**Best for:**
- Complex illustrations
- Detailed artwork
- Rich visualizations

## Output Behavior

### Important: Art is NOT Displayed in Chat

**Why:**
- Rich terminal doesn't support visual ANSI art rendering
- Would be too large to display inline
- Better UX: save and view separately

### Art is Saved to File

**Default Location:**
- Directory: `artes/` (created automatically)
- Filename: `arte_<timestamp>.<format>`
- Example: `artes/arte_1738000000.ans`

**Custom Location:**
- Specify `output_file` parameter
- Directory created automatically if needed
- Full path supported

### Chat Shows File Information

**Response Format:**
```
✅ Arte criada com sucesso!
📁 Arquivo: artes/gato.ans
📐 Dimensões: 80x24
🎨 Formato: ANSI
💡 Para visualizar: aura paint artes/gato.ans
```

## Best Practices

### 1. Prompt Engineering

**Good Prompts:**
- Be specific: "a cat sitting on a mat" vs "a cat"
- Include style: "ASCII art of a house" vs "house"
- Specify details: "diagram with 3 services and database" vs "diagram"

**Bad Prompts:**
- Too vague: "something cool"
- Too complex: "entire operating system architecture with 50 components"
- Ambiguous: "the thing"

### 2. Canvas Sizing

**Small (40x20):**
- Icons, simple logos
- Quick visualizations
- Fast generation

**Medium (80x24):**
- Standard ASCII art
- Simple diagrams
- Balanced quality/speed

**Large (120x40+):**
- Complex diagrams
- Detailed illustrations
- Slower but higher quality

### 3. Format Selection

**ANSI (`.ans`):**
- Terminal viewing
- Preserves colors
- Text-based

**PNG (`.png`):**
- Documentation
- Presentations
- Image sharing

**SVG (`.svg`):**
- Scalable graphics
- Web use
- Professional diagrams

**HTML (`.html`):**
- Web pages
- Interactive content
- Embedded displays

### 4. Mode Selection

**Auto (Recommended):**
- Let LLM decide
- Best for most cases
- Intelligent mode selection

**ASCII:**
- Text-focused art
- Simple patterns
- Fast generation

**Primitives:**
- Geometric shapes
- Technical diagrams
- Precise drawings

**Hybrid:**
- Complex scenes
- Best quality
- Detailed artwork

## Integration with Other Tools

### File Operations

After generating art, you can:
- Read the file: `read_file("artes/arte_123.ans")`
- Copy to docs: Use file operations
- Include in documentation: Reference the file path

### Documentation

Art files can be:
- Referenced in markdown: `![Diagram](artes/diagram.svg)`
- Included in HTML: `<img src="artes/logo.png">`
- Embedded in documentation

## Error Handling

### Common Errors

1. **LLM Unavailable:**
   - Tool falls back to simple command-based generation
   - Still functional but less intelligent

2. **Invalid Format:**
   - Defaults to ANSI if format not supported
   - Error returned in response

3. **File Write Error:**
   - Check permissions
   - Verify disk space
   - Error details in response

### Error Response Format

```python
{"success": False, "error": "Error message", "file_path": "path/if/partial/save"}
```

## Examples for Agent

### Example 1: User Requests Logo

**User:** "Create a logo for my project called 'Aura'"

**Agent Action:**
```python
result = paint_generate_art(
    prompt="modern tech logo with text 'Aura' in ASCII art style",
    width=60,
    height=15,
    format="ans",
    output_file="artes/aura_logo.ans",
)
```

**Agent Response:**
```
✅ Logo criado com sucesso!
📁 Arquivo: artes/aura_logo.ans
📐 Dimensões: 60x15
🎨 Formato: ANSI
💡 Para visualizar: aura paint artes/aura_logo.ans
```

### Example 2: User Requests Diagram

**User:** "Show me a diagram of my application architecture"

**Agent Action:**
```python
result = paint_generate_art(
    prompt="application architecture diagram showing frontend, backend API, database, and cache layers with connections",
    width=100,
    height=35,
    format="svg",
    mode="primitives",
    output_file="docs/architecture.svg",
)
```

**Agent Response:**
```
✅ Diagrama de arquitetura criado!
📁 Arquivo: docs/architecture.svg
📐 Dimensões: 100x35
🎨 Formato: SVG
💡 Abra no navegador ou visualize com: aura paint docs/architecture.svg
```

### Example 3: User Requests Illustration

**User:** "Create a cute ASCII cat"

**Agent Action:**
```python
result = paint_generate_art(
    prompt="cute ASCII art of a cat with whiskers and tail",
    width=40,
    height=20,
    format="ans",
)
```

**Agent Response:**
```
✅ Arte criada com sucesso!
📁 Arquivo: artes/arte_1738000000.ans
📐 Dimensões: 40x20
🎨 Formato: ANSI
💡 Para visualizar: aura paint artes/arte_1738000000.ans
```

## Technical Details

### Architecture

- **HeadlessPaintAgent:** Core engine without TUI dependency
- **PaintAgent:** Original agent adapted for headless mode
- **AnsiArtDocument:** Document model supporting multiple formats
- **LLMPaintAgent:** LLM-powered generation with 3 modes

### Generation Process

1. **Prompt Analysis:** LLM analyzes prompt (if available)
2. **Mode Selection:** Auto-selects or uses specified mode
3. **Art Generation:** Creates art using selected method
4. **Format Encoding:** Converts to requested format
5. **File Saving:** Saves to specified or default location

### Performance

- **Small (40x20):** ~1-3 seconds
- **Medium (80x24):** ~2-5 seconds
- **Large (120x40+):** ~5-15 seconds
- **With LLM:** Adds ~2-5 seconds for generation

## Limitations

1. **No Visual Preview in Chat:**
   - Art must be viewed separately
   - Use `aura paint <file>` to view

2. **Size Constraints:**
   - Very large canvases (>200x100) may be slow
   - Recommended max: 150x60

3. **LLM Dependency:**
   - Best results require LLM client
   - Falls back to simple generation if unavailable

4. **Format Limitations:**
   - Some formats may lose information
   - ANSI preserves most detail

## When to Use This Tool

### ✅ Good Use Cases

- Creating ASCII art for documentation
- Generating architecture diagrams
- Creating logos and icons
- Visualizing concepts
- Adding visual elements to projects
- Creating decorative content

### ❌ Not Ideal For

- Real-time visual editing (use Paint TUI)
- Complex image manipulation
- Photo editing
- Professional graphic design
- Large-scale image processing

## Tips for Maximum Performance

1. **Use appropriate canvas size:** Don't go larger than needed
2. **Choose right format:** ANSI for terminal, SVG for web, PNG for images
3. **Be specific in prompts:** Better prompts = better results
4. **Use auto mode:** Let LLM decide best approach
5. **Specify output location:** Avoid default directory clutter

---

**Last Updated:** 2026-01-26  
**Tool Version:** 1.0.0  
**Status:** ✅ Production Ready
