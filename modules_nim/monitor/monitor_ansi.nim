## Aura Monitor - ANSI Rendering Engine
## =====================================
##
## Handles ANSI escape sequence parsing and generation for terminal rendering.
## Extracted from Chawan's ansi2html.nim and adapted for Aura.
##
## Features:
## - Parse ANSI escape sequences
## - Convert ANSI to structured format
## - Generate ANSI output
## - Support 16/256/24-bit colors

{.push raises: [].}

import std/[strutils, options]
import monitor_types

type
  AnsiParseState* = enum
    apsNormal # Normal text
    apsEscape # After ESC
    apsCSI    # After ESC[
    apsOSC    # After ESC]
    apsDCS    # After ESC P

  AnsiParser* = object
    state*: AnsiParseState
    params*: string
    intermediate*: string
    currentFormat*: Format
    output*: seq[ContentLine]
    currentLine*: string
    currentFormats*: seq[tuple[pos: int, format: Format]]

proc newAnsiParser*(): AnsiParser =
  result.state = apsNormal
  result.currentFormat = initFormat(defaultColor(), defaultColor())

proc parseColor(params: string; i: var int; isFg: bool): Option[CellColor] =
  ## Parse extended color (38;2;r;g;b or 38;5;n)
  if i >= params.len:
    return none(CellColor)

  var numStr = ""
  while i < params.len and params[i] in '0'..'9':
    numStr &= params[i]
    inc i

  if numStr == "":
    return none(CellColor)

  var colorType: int
  try:
    colorType = parseInt(numStr)
  except ValueError:
    colorType = 0

  # Skip semicolon
  if i < params.len and params[i] == ';':
    inc i

  case colorType
  of 2:
    # 24-bit RGB: 38;2;r;g;b
    var r, g, b: int
    # Parse R
    numStr = ""
    while i < params.len and params[i] in '0'..'9':
      numStr &= params[i]
      inc i
    if numStr == "": return none(CellColor)
    try:
      r = parseInt(numStr)
    except ValueError:
      r = 0
    if i < params.len and params[i] == ';': inc i

    # Parse G
    numStr = ""
    while i < params.len and params[i] in '0'..'9':
      numStr &= params[i]
      inc i
    if numStr == "": return none(CellColor)
    try:
      g = parseInt(numStr)
    except ValueError:
      g = 0
    if i < params.len and params[i] == ';': inc i

    # Parse B
    numStr = ""
    while i < params.len and params[i] in '0'..'9':
      numStr &= params[i]
      inc i
    if numStr == "": return none(CellColor)
    try:
      b = parseInt(numStr)
    except ValueError:
      b = 0

    return some(cellColor(rgb(uint8(r), uint8(g), uint8(b))))

  of 5:
    # 256 color: 38;5;n
    numStr = ""
    while i < params.len and params[i] in '0'..'9':
      numStr &= params[i]
      inc i
    if numStr == "": return none(CellColor)
    var colorValue: int
    try:
      colorValue = parseInt(numStr)
    except ValueError:
      colorValue = 0
    return some(cellColor(uint8(colorValue)))

  else:
    return none(CellColor)

proc parseSGR*(parser: var AnsiParser; params: string) =
  ## Parse SGR (Select Graphic Rendition) parameters
  if params == "" or params == "0":
    parser.currentFormat = initFormat(defaultColor(), defaultColor())
    return

  var i = 0
  while i < params.len:
    var numStr = ""
    while i < params.len and params[i] in '0'..'9':
      numStr &= params[i]
      inc i

    if numStr == "":
      if i < params.len:
        inc i # Skip separator
      continue

    var code: int
    try:
      code = parseInt(numStr)
    except ValueError:
      code = 0

    case code
    of 0:
      parser.currentFormat = initFormat(defaultColor(), defaultColor())
    of 1:
      parser.currentFormat.flags.incl(ffBold)
    of 2:
      parser.currentFormat.flags.incl(ffDim)
    of 3:
      parser.currentFormat.flags.incl(ffItalic)
    of 4:
      parser.currentFormat.flags.incl(ffUnderline)
    of 5:
      parser.currentFormat.flags.incl(ffBlink)
    of 7:
      parser.currentFormat.flags.incl(ffReverse)
    of 9:
      parser.currentFormat.flags.incl(ffStrike)
    of 21:
      parser.currentFormat.flags.excl(ffBold)
    of 22:
      parser.currentFormat.flags.excl(ffBold)
      parser.currentFormat.flags.excl(ffDim)
    of 23:
      parser.currentFormat.flags.excl(ffItalic)
    of 24:
      parser.currentFormat.flags.excl(ffUnderline)
    of 25:
      parser.currentFormat.flags.excl(ffBlink)
    of 27:
      parser.currentFormat.flags.excl(ffReverse)
    of 29:
      parser.currentFormat.flags.excl(ffStrike)
    of 30..37:
      parser.currentFormat.fg = cellColor(uint8(code - 30))
    of 38:
      # Extended foreground
      if i < params.len and params[i] == ';':
        inc i
        let color = parseColor(params, i, true)
        if color.isSome:
          parser.currentFormat.fg = color.get
    of 39:
      parser.currentFormat.fg = defaultColor()
    of 40..47:
      parser.currentFormat.bg = cellColor(uint8(code - 40))
    of 48:
      # Extended background
      if i < params.len and params[i] == ';':
        inc i
        let color = parseColor(params, i, false)
        if color.isSome:
          parser.currentFormat.bg = color.get
    of 49:
      parser.currentFormat.bg = defaultColor()
    of 90..97:
      parser.currentFormat.fg = cellColor(uint8(code - 90 + 8))
    of 100..107:
      parser.currentFormat.bg = cellColor(uint8(code - 100 + 8))
    else:
      discard

    # Skip separator
    if i < params.len and params[i] in {';', ':'}:
      inc i

proc handleCSI*(parser: var AnsiParser; final: char) =
  ## Handle CSI (Control Sequence Introducer) sequence
  case final
  of 'm':
    parser.parseSGR(parser.params)
  else:
    discard # Ignore other CSI sequences for now

proc flushLine*(parser: var AnsiParser) =
  ## Flush current line to output
  if parser.currentLine.len > 0 or parser.currentFormats.len > 0:
    parser.output.add(ContentLine(
      text: parser.currentLine,
      formats: parser.currentFormats
    ))
    parser.currentLine = ""
    parser.currentFormats = @[]

proc feed*(parser: var AnsiParser; c: char) =
  ## Feed a character to the parser
  case parser.state
  of apsNormal:
    case c
    of '\e':
      parser.state = apsEscape
    of '\n':
      parser.flushLine()
    of '\r':
      discard # Ignore CR
    of '\t':
      # Convert tab to spaces
      let spaces = 8 - (parser.currentLine.len mod 8)
      for _ in 0 ..< spaces:
        parser.currentLine &= ' '
    else:
      if c >= ' ': # Printable
        parser.currentLine &= c

  of apsEscape:
    case c
    of '[':
      parser.state = apsCSI
      parser.params = ""
      parser.intermediate = ""
    of ']':
      parser.state = apsOSC
      parser.params = ""
    of 'P':
      parser.state = apsDCS
      parser.params = ""
    else:
      parser.state = apsNormal

  of apsCSI:
    case c
    of '0'..'9', ';', ':', '?', '!', '"', '\'', ' ':
      if c in '0'..'9' or c == ';' or c == ':':
        parser.params &= c
      else:
        parser.intermediate &= c
    of '@'..'~':
      # Record format change position
      if parser.params != "" or c == 'm':
        parser.currentFormats.add((parser.currentLine.len,
            parser.currentFormat))
      parser.handleCSI(c)
      parser.state = apsNormal
    else:
      parser.state = apsNormal

  of apsOSC:
    if c == '\a' or c == '\e':
      parser.state = apsNormal
    else:
      parser.params &= c

  of apsDCS:
    if c == '\e':
      parser.state = apsNormal

proc parse*(parser: var AnsiParser; input: string) =
  ## Parse an entire string
  for c in input:
    parser.feed(c)
  parser.flushLine()

proc parseAnsi*(input: string): seq[ContentLine] =
  ## Convenience function to parse ANSI text
  var parser = newAnsiParser()
  parser.parse(input)
  result = parser.output

# =============================================================================
# ANSI GENERATION
# =============================================================================

proc toAnsi*(line: ContentLine): string =
  ## Convert a ContentLine back to ANSI-formatted text
  result = ""
  var lastFormat = initFormat(defaultColor(), defaultColor())
  var formatIdx = 0

  for i, c in line.text:
    # Check if we need to apply a new format
    while formatIdx < line.formats.len and line.formats[formatIdx].pos <= i:
      let newFormat = line.formats[formatIdx].format
      if newFormat != lastFormat:
        result &= newFormat.toAnsiString()
        lastFormat = newFormat
      inc formatIdx
    result &= c

  result &= ANSI_RESET

proc toAnsi*(content: RenderedContent): string =
  ## Convert rendered content to ANSI string
  result = ""
  for line in content.lines:
    result &= line.toAnsi() & "\n"

# =============================================================================
# PLAIN TEXT CONVERSION
# =============================================================================

proc stripAnsi*(input: string): string =
  ## Remove all ANSI escape sequences from text
  result = ""
  var parser = newAnsiParser()

  for c in input:
    case parser.state
    of apsNormal:
      if c == '\e':
        parser.state = apsEscape
      elif c >= ' ' or c == '\n' or c == '\t':
        result &= c
    of apsEscape:
      parser.state = if c == '[': apsCSI elif c == ']': apsOSC else: apsNormal
    of apsCSI:
      if c in '@'..'~':
        parser.state = apsNormal
    of apsOSC:
      if c == '\a' or c == '\e':
        parser.state = apsNormal
    of apsDCS:
      if c == '\e':
        parser.state = apsNormal
