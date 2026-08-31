## Aura Monitor - HTML Renderer
## ============================
##
## Simplified HTML to terminal text renderer.
## Handles common HTML elements for TUI display.
##
## Features:
## - Block elements (p, div, h1-h6, pre, blockquote)
## - Inline elements (a, b, i, u, code, span)
## - Lists (ul, ol, li)
## - Basic table support
## - Link extraction

{.push raises: [].}

import std/[strutils, htmlparser, xmltree]
import monitor_types

type
  HtmlRendererState* = enum
    hrsNormal
    hrsPre
    hrsScript
    hrsStyle

  HtmlRenderer* = object
    width*: int
    currentLine*: string
    currentFormat*: Format
    output*: seq[ContentLine]
    links*: seq[tuple[text, url: string]]
    images*: seq[tuple[alt, src: string]]
    title*: string
    state*: HtmlRendererState
    listStack*: seq[tuple[ordered: bool, index: int]]
    indent*: int
    linkCount*: int

proc newHtmlRenderer*(width: int = 80): HtmlRenderer =
  result.width = width
  result.currentFormat = initFormat(defaultColor(), defaultColor())
  result.state = hrsNormal

proc flushLine*(r: var HtmlRenderer) =
  ## Flush current line to output
  if r.currentLine.len > 0:
    # Add indentation
    let indentStr = "  ".repeat(r.indent)
    r.output.add(ContentLine(text: indentStr & r.currentLine))
    r.currentLine = ""

proc addBlankLine*(r: var HtmlRenderer) =
  ## Add a blank line if not already at start
  r.flushLine()
  if r.output.len > 0 and r.output[^1].text != "":
    r.output.add(ContentLine(text: ""))

proc wrapText*(r: var HtmlRenderer; text: string) =
  ## Word-wrap text to fit width
  let effectiveWidth = r.width - (r.indent * 2)
  let words = text.split(' ')

  for word in words:
    if word == "":
      continue

    if r.currentLine.len > 0 and r.currentLine.len + word.len + 1 > effectiveWidth:
      r.flushLine()

    if r.currentLine.len > 0:
      r.currentLine &= " "
    r.currentLine &= word

proc addText*(r: var HtmlRenderer; text: string;
    preserveWhitespace: bool = false) =
  ## Add text to current line
  if r.state in {hrsScript, hrsStyle}:
    return

  if preserveWhitespace:
    # Pre-formatted: preserve whitespace and newlines
    for line in text.splitLines:
      r.currentLine &= line
      r.flushLine()
  else:
    # Collapse whitespace
    var collapsed = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    while "  " in collapsed:
      collapsed = collapsed.replace("  ", " ")
    collapsed = collapsed.strip()

    if collapsed.len > 0:
      r.wrapText(collapsed)

# =============================================================================
# ELEMENT RENDERERS
# =============================================================================

proc renderElement*(r: var HtmlRenderer; node: XmlNode) # Forward declaration

proc renderChildren*(r: var HtmlRenderer; node: XmlNode) =
  for child in node:
    r.renderElement(child)

proc renderHeading*(r: var HtmlRenderer; node: XmlNode; level: int) =
  r.addBlankLine()

  # Add heading marker
  let marker = "#".repeat(level) & " "
  r.currentLine &= marker

  # Set bold format
  let oldFormat = r.currentFormat
  r.currentFormat.flags.incl(ffBold)

  r.renderChildren(node)
  r.flushLine()

  r.currentFormat = oldFormat
  r.addBlankLine()

proc renderParagraph*(r: var HtmlRenderer; node: XmlNode) =
  r.addBlankLine()
  r.renderChildren(node)
  r.flushLine()
  r.addBlankLine()

proc renderDiv*(r: var HtmlRenderer; node: XmlNode) =
  r.flushLine()
  r.renderChildren(node)
  r.flushLine()

proc renderPre*(r: var HtmlRenderer; node: XmlNode) =
  r.addBlankLine()
  r.output.add(ContentLine(text: "```"))

  let oldState = r.state
  r.state = hrsPre

  for child in node:
    if child.kind == xnText:
      for line in child.text.splitLines:
        r.output.add(ContentLine(text: line))
    else:
      r.renderElement(child)

  r.state = oldState
  r.output.add(ContentLine(text: "```"))
  r.addBlankLine()

proc renderBlockquote*(r: var HtmlRenderer; node: XmlNode) =
  r.addBlankLine()

  let oldIndent = r.indent
  r.indent += 1

  r.renderChildren(node)
  r.flushLine()

  r.indent = oldIndent
  r.addBlankLine()

proc renderList*(r: var HtmlRenderer; node: XmlNode; ordered: bool) =
  r.addBlankLine()

  r.listStack.add((ordered: ordered, index: 1))
  r.indent += 1

  for child in node:
    if child.kind == xnElement and child.tag.toLowerAscii == "li":
      r.flushLine()

      # Add list marker
      if ordered:
        r.currentLine &= $r.listStack[^1].index & ". "
        r.listStack[^1].index += 1
      else:
        r.currentLine &= "• "

      r.renderChildren(child)
      r.flushLine()

  r.indent -= 1
  discard r.listStack.pop()
  r.addBlankLine()

proc renderLink*(r: var HtmlRenderer; node: XmlNode) =
  let href = if node.attrs != nil: node.attr("href") else: ""

  # Render link text
  let oldFormat = r.currentFormat
  r.currentFormat.flags.incl(ffUnderline)
  r.currentFormat.fg = cellColor(rgb(0, 175, 255)) # Cyan

  r.renderChildren(node)

  # Add link reference
  if href != "":
    r.linkCount += 1
    r.currentLine &= "[" & $r.linkCount & "]"
    r.links.add((text: r.currentLine, url: href))

  r.currentFormat = oldFormat

proc renderImage*(r: var HtmlRenderer; node: XmlNode) =
  let src = if node.attrs != nil: node.attr("src") else: ""
  let alt = if node.attrs != nil: node.attr("alt") else: "image"

  if alt != "":
    r.currentLine &= "[" & alt & "]"
  else:
    r.currentLine &= "[image]"

  if src != "":
    r.images.add((alt: alt, src: src))

proc renderBold*(r: var HtmlRenderer; node: XmlNode) =
  let oldFormat = r.currentFormat
  r.currentFormat.flags.incl(ffBold)
  r.renderChildren(node)
  r.currentFormat = oldFormat

proc renderItalic*(r: var HtmlRenderer; node: XmlNode) =
  let oldFormat = r.currentFormat
  r.currentFormat.flags.incl(ffItalic)
  r.renderChildren(node)
  r.currentFormat = oldFormat

proc renderUnderline*(r: var HtmlRenderer; node: XmlNode) =
  let oldFormat = r.currentFormat
  r.currentFormat.flags.incl(ffUnderline)
  r.renderChildren(node)
  r.currentFormat = oldFormat

proc renderCode*(r: var HtmlRenderer; node: XmlNode) =
  r.currentLine &= "`"
  r.renderChildren(node)
  r.currentLine &= "`"

proc renderBr*(r: var HtmlRenderer) =
  r.flushLine()

proc renderHr*(r: var HtmlRenderer) =
  r.flushLine()
  r.output.add(ContentLine(text: "─".repeat(r.width - r.indent * 2)))
  r.flushLine()

proc renderTable*(r: var HtmlRenderer; node: XmlNode) =
  r.addBlankLine()

  # Simple table rendering
  var rows: seq[seq[string]]

  for child in node:
    if child.kind == xnElement:
      let tag = child.tag.toLowerAscii
      if tag in ["thead", "tbody", "tfoot"]:
        for row in child:
          if row.kind == xnElement and row.tag.toLowerAscii == "tr":
            var cells: seq[string]
            for cell in row:
              if cell.kind == xnElement and cell.tag.toLowerAscii in ["td", "th"]:
                cells.add(cell.innerText.strip)
            if cells.len > 0:
              rows.add(cells)
      elif tag == "tr":
        var cells: seq[string]
        for cell in child:
          if cell.kind == xnElement and cell.tag.toLowerAscii in ["td", "th"]:
            cells.add(cell.innerText.strip)
        if cells.len > 0:
          rows.add(cells)

  # Calculate column widths
  var colWidths: seq[int]
  for row in rows:
    for i, cell in row:
      while colWidths.len <= i:
        colWidths.add(0)
      colWidths[i] = max(colWidths[i], cell.len)

  # Render rows
  for rowIdx, row in rows:
    var line = "│ "
    for i, cell in row:
      let width = if i < colWidths.len: colWidths[i] else: 10
      line &= cell.alignLeft(width) & " │ "
    r.output.add(ContentLine(text: line))

    # Add separator after header
    if rowIdx == 0:
      var sep = "├─"
      for w in colWidths:
        sep &= "─".repeat(w) & "─┼─"
      if sep.len > 2:
        sep = sep[0 ..< sep.len - 2] & "┤"
      r.output.add(ContentLine(text: sep))

  r.addBlankLine()

proc renderElement*(r: var HtmlRenderer; node: XmlNode) =
  case node.kind
  of xnText:
    r.addText(node.text, r.state == hrsPre)
  of xnElement:
    let tag = node.tag.toLowerAscii

    case tag
    of "html", "body", "main", "article", "section", "nav", "header", "footer", "aside":
      r.renderChildren(node)
    of "head":
      discard # Skip head
    of "title":
      r.title = node.innerText
    of "script":
      let oldState = r.state
      r.state = hrsScript
      r.renderChildren(node)
      r.state = oldState
    of "style":
      let oldState = r.state
      r.state = hrsStyle
      r.renderChildren(node)
      r.state = oldState
    of "h1": r.renderHeading(node, 1)
    of "h2": r.renderHeading(node, 2)
    of "h3": r.renderHeading(node, 3)
    of "h4": r.renderHeading(node, 4)
    of "h5": r.renderHeading(node, 5)
    of "h6": r.renderHeading(node, 6)
    of "p": r.renderParagraph(node)
    of "div": r.renderDiv(node)
    of "span": r.renderChildren(node)
    of "pre": r.renderPre(node)
    of "code": r.renderCode(node)
    of "blockquote": r.renderBlockquote(node)
    of "ul": r.renderList(node, false)
    of "ol": r.renderList(node, true)
    of "li": r.renderChildren(node) # Handled by list
    of "a": r.renderLink(node)
    of "img": r.renderImage(node)
    of "b", "strong": r.renderBold(node)
    of "i", "em": r.renderItalic(node)
    of "u": r.renderUnderline(node)
    of "br": r.renderBr()
    of "hr": r.renderHr()
    of "table": r.renderTable(node)
    else:
      r.renderChildren(node)
  else:
    discard

# =============================================================================
# PUBLIC API
# =============================================================================

proc renderHtml*(html: string; width: int = 80): RenderedContent =
  ## Render HTML to terminal-friendly content
  var r = newHtmlRenderer(width)

  try:
    let doc = parseHtml(html)
    r.renderElement(doc)
  except:
    # Fallback: strip HTML tags
    var inTag = false
    var text = ""
    for c in html:
      if c == '<':
        inTag = true
      elif c == '>':
        inTag = false
      elif not inTag:
        text &= c
    r.addText(text)

  r.flushLine()

  result.lines = r.output
  result.title = r.title
  result.links = r.links
  result.images = r.images
