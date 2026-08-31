## Aura Monitor - Markdown Renderer
## ================================
##
## Markdown to terminal text renderer with ANSI styling.
## Extracted from Chawan's md2html.nim and adapted for Aura.
##
## Features:
## - Headings (# to ######)
## - Emphasis (*italic*, **bold**, ***both***)
## - Code (`inline` and ```blocks```)
## - Links [text](url) and ![images](url)
## - Lists (ordered and unordered)
## - Blockquotes
## - Horizontal rules

{.push raises: [].}

import std/[strutils, sequtils, tables]
import monitor_types

type
  MdBlockType* = enum
    mbParagraph
    mbHeading
    mbCodeBlock
    mbBlockquote
    mbList
    mbListItem
    mbHorizontalRule
    mbLinkDef

  MdListType* = enum
    mlUnordered
    mlOrdered

  MdParserState* = enum
    mpsNormal
    mpsCodeBlock
    mpsCodeBlockFence

  MdRenderer* = object
    width*: int
    output*: seq[ContentLine]
    currentLine*: string
    currentFormats*: seq[tuple[pos: int, format: Format]]
    currentFormat*: Format
    links*: seq[tuple[text, url: string]]
    images*: seq[tuple[alt, src: string]]
    title*: string
    indent*: int
    state*: MdParserState
    codeBlockLang*: string
    listStack*: seq[tuple[listType: MdListType, index: int]]
    linkDefs*: Table[string, tuple[url, title: string]]

proc newMdRenderer*(width: int = 80): MdRenderer =
  result.width = width
  result.currentFormat = initFormat(defaultColor(), defaultColor())
  result.linkDefs = initTable[string, tuple[url, title: string]]()

proc flushLine*(r: var MdRenderer) =
  if r.currentLine.len > 0 or r.currentFormats.len > 0:
    let indentStr = "  ".repeat(r.indent)
    r.output.add(ContentLine(
      text: indentStr & r.currentLine,
      formats: r.currentFormats
    ))
    r.currentLine = ""
    r.currentFormats = @[]

proc addBlankLine*(r: var MdRenderer) =
  r.flushLine()
  if r.output.len > 0 and r.output[^1].text.strip != "":
    r.output.add(ContentLine(text: ""))

proc addFormat*(r: var MdRenderer) =
  r.currentFormats.add((r.currentLine.len, r.currentFormat))

proc setFormat*(r: var MdRenderer; flags: set[FormatFlag]) =
  r.currentFormat.flags = flags
  r.addFormat()

proc addFlags*(r: var MdRenderer; flags: set[FormatFlag]) =
  r.currentFormat.flags = r.currentFormat.flags + flags
  r.addFormat()

proc removeFlags*(r: var MdRenderer; flags: set[FormatFlag]) =
  r.currentFormat.flags = r.currentFormat.flags - flags
  r.addFormat()

# =============================================================================
# INLINE PARSING
# =============================================================================

proc parseInline*(r: var MdRenderer; text: string) =
  ## Parse inline markdown elements
  var i = 0
  let n = text.len

  while i < n:
    let c = text[i]

    case c
    of '\\':
      # Escape next character
      if i + 1 < n:
        r.currentLine &= text[i + 1]
        i += 2
      else:
        r.currentLine &= c
        inc i

    of '*', '_':
      # Emphasis
      var count = 1
      while i + count < n and text[i + count] == c:
        inc count

      if count >= 2:
        # Bold
        r.addFlags({ffBold})
        i += 2

        # Find closing
        var j = i
        while j < n - 1:
          if text[j] == c and text[j + 1] == c:
            break
          inc j

        if j < n - 1:
          r.parseInline(text[i ..< j])
          r.removeFlags({ffBold})
          i = j + 2
        else:
          r.currentLine &= c & c
      else:
        # Italic
        r.addFlags({ffItalic})
        inc i

        var j = i
        while j < n:
          if text[j] == c:
            break
          inc j

        if j < n:
          r.parseInline(text[i ..< j])
          r.removeFlags({ffItalic})
          i = j + 1
        else:
          r.currentLine &= c

    of '`':
      # Inline code
      var count = 1
      while i + count < n and text[i + count] == '`':
        inc count

      let delim = "`".repeat(count)
      let endPos = text.find(delim, i + count)

      if endPos >= 0:
        let code = text[i + count ..< endPos]
        r.addFlags({ffDim})
        r.currentLine &= code
        r.removeFlags({ffDim})
        i = endPos + count
      else:
        r.currentLine &= delim
        i += count

    of '[':
      # Link or image
      let closeBracket = text.find(']', i)
      if closeBracket >= 0 and closeBracket + 1 < n:
        let linkText = text[i + 1 ..< closeBracket]

        if text[closeBracket + 1] == '(':
          # Inline link [text](url)
          let closeParen = text.find(')', closeBracket + 2)
          if closeParen >= 0:
            let url = text[closeBracket + 2 ..< closeParen]

            r.addFlags({ffUnderline})
            r.currentFormat.fg = cellColor(rgb(0, 175, 255))
            r.addFormat()
            r.currentLine &= linkText
            r.removeFlags({ffUnderline})
            r.currentFormat.fg = defaultColor()
            r.addFormat()

            r.links.add((text: linkText, url: url))
            i = closeParen + 1
            continue
        elif text[closeBracket + 1] == '[':
          # Reference link [text][ref]
          let closeRef = text.find(']', closeBracket + 2)
          if closeRef >= 0:
            let linkRef = text[closeBracket + 2 ..< closeRef]
            let refKey = if linkRef == "": linkText.toLowerAscii else: linkRef.toLowerAscii

            r.addFlags({ffUnderline})
            r.currentLine &= linkText
            r.removeFlags({ffUnderline})

            if refKey in r.linkDefs:
              let linkDef = r.linkDefs.getOrDefault(refKey, (url: "", title: ""))
              if linkDef.url != "":
                r.links.add((text: linkText, url: linkDef.url))

            i = closeRef + 1
            continue

      r.currentLine &= c
      inc i

    of '!':
      # Image
      if i + 1 < n and text[i + 1] == '[':
        let closeBracket = text.find(']', i + 2)
        if closeBracket >= 0 and closeBracket + 1 < n and text[closeBracket +
            1] == '(':
          let altText = text[i + 2 ..< closeBracket]
          let closeParen = text.find(')', closeBracket + 2)
          if closeParen >= 0:
            let src = text[closeBracket + 2 ..< closeParen]

            r.currentLine &= "[" & (if altText != "": altText else: "image") & "]"
            r.images.add((alt: altText, src: src))
            i = closeParen + 1
            continue

      r.currentLine &= c
      inc i

    else:
      r.currentLine &= c
      inc i

# =============================================================================
# BLOCK PARSING
# =============================================================================

proc parseLine*(r: var MdRenderer; line: string) =
  ## Parse a single line of markdown
  let trimmed = line.strip

  # Handle code block
  if r.state == mpsCodeBlock:
    if trimmed.startsWith("```"):
      r.state = mpsNormal
      r.output.add(ContentLine(text: "```"))
      r.addBlankLine()
    else:
      r.output.add(ContentLine(text: line))
    return

  # Empty line
  if trimmed == "":
    r.addBlankLine()
    return

  # Code block start
  if trimmed.startsWith("```"):
    r.addBlankLine()
    r.codeBlockLang = trimmed[3 .. ^1].strip
    r.output.add(ContentLine(text: "```" & r.codeBlockLang))
    r.state = mpsCodeBlock
    return

  # Heading
  if trimmed.startsWith("#"):
    var level = 0
    while level < trimmed.len and trimmed[level] == '#':
      inc level

    if level <= 6 and level < trimmed.len and trimmed[level] == ' ':
      r.addBlankLine()
      r.addFlags({ffBold})
      r.currentLine &= "#".repeat(level) & " "
      r.parseInline(trimmed[level + 1 .. ^1].strip)
      r.removeFlags({ffBold})
      r.flushLine()
      r.addBlankLine()

      if level == 1 and r.title == "":
        r.title = trimmed[level + 1 .. ^1].strip
      return

  # Horizontal rule
  if trimmed.len >= 3 and trimmed.all(proc(c: char): bool = c in {'-', '*', '_', ' '}):
    var count = 0
    for c in trimmed:
      if c in {'-', '*', '_'}:
        inc count
    if count >= 3:
      r.addBlankLine()
      r.output.add(ContentLine(text: "─".repeat(r.width - r.indent * 2)))
      r.addBlankLine()
      return

  # Blockquote
  if trimmed.startsWith(">"):
    r.indent += 1
    r.currentLine &= "│ "
    r.parseInline(trimmed[1 .. ^1].strip)
    r.flushLine()
    r.indent -= 1
    return

  # Unordered list
  if trimmed.len >= 2 and trimmed[0] in {'-', '*', '+'} and trimmed[1] == ' ':
    r.currentLine &= "• "
    r.parseInline(trimmed[2 .. ^1])
    r.flushLine()
    return

  # Ordered list
  if trimmed.len >= 3:
    var numEnd = 0
    while numEnd < trimmed.len and trimmed[numEnd] in '0'..'9':
      inc numEnd

    if numEnd > 0 and numEnd < trimmed.len - 1 and trimmed[numEnd] in {'.',
        ')'} and trimmed[numEnd + 1] == ' ':
      let num = trimmed[0 ..< numEnd]
      r.currentLine &= num & ". "
      r.parseInline(trimmed[numEnd + 2 .. ^1])
      r.flushLine()
      return

  # Link definition
  if trimmed.startsWith("[") and "]: " in trimmed:
    let closeBracket = trimmed.find("]:")
    if closeBracket > 1:
      let refName = trimmed[1 ..< closeBracket].toLowerAscii
      let rest = trimmed[closeBracket + 2 .. ^1].strip
      var url = rest
      var title = ""

      # Check for title
      if rest.len > 2 and rest[^1] in {'"', '\''} and rest.find(rest[^1]) <
          rest.len - 1:
        let titleStart = rest.find(rest[^1])
        url = rest[0 ..< titleStart].strip
        title = rest[titleStart + 1 ..< rest.len - 1]

      r.linkDefs[refName] = (url: url, title: title)
      return

  # Regular paragraph
  r.parseInline(trimmed)
  r.flushLine()

proc parse*(r: var MdRenderer; markdown: string) =
  ## Parse entire markdown document
  for line in markdown.splitLines:
    r.parseLine(line)
  r.flushLine()

# =============================================================================
# PUBLIC API
# =============================================================================

proc renderMarkdown*(markdown: string; width: int = 80): RenderedContent =
  ## Render markdown to terminal-friendly content
  var r = newMdRenderer(width)
  r.parse(markdown)

  result.lines = r.output
  result.title = r.title
  result.links = r.links
  result.images = r.images
