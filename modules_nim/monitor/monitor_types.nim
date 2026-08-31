## Aura Monitor - Common Types
## ============================
##
## Shared type definitions for the Aura Monitor system.
## These types are used across all monitor modules.
##
## Build: Part of the monitor module system
## See: modules_nim/monitor/monitor.nim for main entry

{.push raises: [].}

import std/[options]
import std/strutils

const
  MONITOR_VERSION* = "1.0.0"

  # ANSI color codes
  ANSI_RESET* = "\e[0m"
  ANSI_BOLD* = "\e[1m"
  ANSI_DIM* = "\e[2m"
  ANSI_ITALIC* = "\e[3m"
  ANSI_UNDERLINE* = "\e[4m"
  ANSI_BLINK* = "\e[5m"
  ANSI_REVERSE* = "\e[7m"
  ANSI_STRIKE* = "\e[9m"

# =============================================================================
# COLOR TYPES
# =============================================================================

type
  ColorMode* = enum
    cmAuto = "auto"
    cmTrue = "true" # 24-bit color
    cm256 = "256"   # 256 colors
    cm16 = "16"     # 16 colors
    cmMono = "mono" # Monochrome

  RGBColor* = object
    r*, g*, b*: uint8

  CellColor* = object
    case isRgb*: bool
    of true:
      rgb*: RGBColor
    of false:
      ansi*: uint8 # 0-255 for ANSI colors

proc `==`*(a, b: RGBColor): bool =
  a.r == b.r and a.g == b.g and a.b == b.b

proc `==`*(a, b: CellColor): bool =
  if a.isRgb != b.isRgb:
    return false
  if a.isRgb:
    return a.rgb == b.rgb
  else:
    return a.ansi == b.ansi

proc rgb*(r, g, b: uint8): RGBColor =
  RGBColor(r: r, g: g, b: b)

proc cellColor*(c: RGBColor): CellColor =
  CellColor(isRgb: true, rgb: c)

proc cellColor*(ansi: uint8): CellColor =
  CellColor(isRgb: false, ansi: ansi)

proc defaultColor*(): CellColor =
  cellColor(0'u8)

proc toAnsiString*(c: CellColor; fg: bool): string =
  ## Convert color to ANSI escape sequence
  if c.isRgb:
    if fg:
      result = "\e[38;2;" & $c.rgb.r & ";" & $c.rgb.g & ";" & $c.rgb.b & "m"
    else:
      result = "\e[48;2;" & $c.rgb.r & ";" & $c.rgb.g & ";" & $c.rgb.b & "m"
  else:
    if c.ansi < 8:
      if fg:
        result = "\e[" & $(30 + c.ansi) & "m"
      else:
        result = "\e[" & $(40 + c.ansi) & "m"
    elif c.ansi < 16:
      if fg:
        result = "\e[" & $(90 + c.ansi - 8) & "m"
      else:
        result = "\e[" & $(100 + c.ansi - 8) & "m"
    else:
      if fg:
        result = "\e[38;5;" & $c.ansi & "m"
      else:
        result = "\e[48;5;" & $c.ansi & "m"

# =============================================================================
# FORMAT TYPES
# =============================================================================

type
  FormatFlag* = enum
    ffBold
    ffItalic
    ffUnderline
    ffReverse
    ffStrike
    ffOverline
    ffBlink
    ffDim

  Format* = object
    fg*: CellColor
    bg*: CellColor
    flags*: set[FormatFlag]

proc `==`*(a, b: Format): bool =
  a.fg == b.fg and a.bg == b.bg and a.flags == b.flags

proc initFormat*(fg, bg: CellColor; flags: set[FormatFlag] = {}): Format =
  Format(fg: fg, bg: bg, flags: flags)

proc toAnsiString*(f: Format): string =
  ## Convert format to ANSI escape sequence
  result = ANSI_RESET

  if ffBold in f.flags: result &= ANSI_BOLD
  if ffDim in f.flags: result &= ANSI_DIM
  if ffItalic in f.flags: result &= ANSI_ITALIC
  if ffUnderline in f.flags: result &= ANSI_UNDERLINE
  if ffBlink in f.flags: result &= ANSI_BLINK
  if ffReverse in f.flags: result &= ANSI_REVERSE
  if ffStrike in f.flags: result &= ANSI_STRIKE

  result &= f.fg.toAnsiString(true)
  result &= f.bg.toAnsiString(false)

# =============================================================================
# CELL TYPES (Terminal Grid)
# =============================================================================

type
  Cell* = object
    ch*: Rune
    format*: Format
    width*: int # Display width (1 or 2 for CJK)

  Rune* = distinct uint32

  FixedCell* = object
    ch*: uint32
    format*: Format

  FixedGrid* = object
    cells*: seq[FixedCell]
    width*, height*: int

proc newFixedGrid*(width, height: int): FixedGrid =
  result.width = width
  result.height = height
  result.cells = newSeq[FixedCell](width * height)

proc `[]`*(grid: FixedGrid; x, y: int): FixedCell =
  if x >= 0 and x < grid.width and y >= 0 and y < grid.height:
    result = grid.cells[y * grid.width + x]

proc `[]=`*(grid: var FixedGrid; x, y: int; cell: FixedCell) =
  if x >= 0 and x < grid.width and y >= 0 and y < grid.height:
    grid.cells[y * grid.width + x] = cell

# =============================================================================
# CONTENT TYPES
# =============================================================================

type
  ContentType* = enum
    ctPlain = "text/plain"
    ctHtml = "text/html"
    ctMarkdown = "text/markdown"
    ctJson = "application/json"
    ctGemini = "text/gemini"

  ContentLine* = object
    text*: string
    formats*: seq[tuple[pos: int; format: Format]]

  RenderedContent* = object
    lines*: seq[ContentLine]
    title*: string
    links*: seq[tuple[text, url: string]]
    images*: seq[tuple[alt, src: string]]

# =============================================================================
# MONITOR CONFIG
# =============================================================================

type
  MonitorConfig* = object
    colorMode*: ColorMode
    columns*: int
    lines*: int
    userAgent*: string
    timeout*: int
    followRedirects*: bool
    maxRedirects*: int
    cookies*: bool
    images*: bool

proc defaultConfig*(): MonitorConfig =
  MonitorConfig(
    colorMode: cmAuto,
    columns: 80,
    lines: 24,
    userAgent: "AuraMonitor/" & MONITOR_VERSION,
    timeout: 30,
    followRedirects: true,
    maxRedirects: 10,
    cookies: false,
    images: false
  )

# =============================================================================
# URL TYPES
# =============================================================================

type
  URL* = object
    scheme*: string
    host*: string
    port*: int
    path*: string
    query*: string
    fragment*: string
    username*: string
    password*: string

proc parseURL*(s: string): Option[URL] =
  ## Simple URL parser
  var url: URL
  var i = 0

  # Parse scheme
  let colonSlash = s.find("://")
  if colonSlash > 0:
    url.scheme = s[0 ..< colonSlash].toLowerAscii()
    i = colonSlash + 3
  else:
    return none(URL)

  # Parse authority (user:pass@host:port)
  let pathStart = s.find('/', i)
  let authorityEnd = if pathStart >= 0: pathStart else: s.len
  let authority = s[i ..< authorityEnd]

  # Check for userinfo
  let atSign = authority.find('@')
  var hostStart = 0
  if atSign >= 0:
    let userinfo = authority[0 ..< atSign]
    let colonPos = userinfo.find(':')
    if colonPos >= 0:
      url.username = userinfo[0 ..< colonPos]
      url.password = userinfo[colonPos + 1 .. ^1]
    else:
      url.username = userinfo
    hostStart = atSign + 1

  # Parse host:port
  let hostPart = authority[hostStart .. ^1]
  let colonPos = hostPart.rfind(':')
  if colonPos >= 0:
    url.host = hostPart[0 ..< colonPos]
    try:
      url.port = parseInt(hostPart[colonPos + 1 .. ^1])
    except ValueError:
      url.port = 0
  else:
    url.host = hostPart
    # Default ports
    case url.scheme
    of "http": url.port = 80
    of "https": url.port = 443
    of "gemini": url.port = 1965
    of "gopher": url.port = 70
    else: url.port = 0

  i = authorityEnd

  # Parse path, query, fragment
  if i < s.len:
    let queryStart = s.find('?', i)
    let fragStart = s.find('#', i)

    if queryStart >= 0 and (fragStart < 0 or queryStart < fragStart):
      url.path = s[i ..< queryStart]
      if fragStart >= 0:
        url.query = s[queryStart + 1 ..< fragStart]
        url.fragment = s[fragStart + 1 .. ^1]
      else:
        url.query = s[queryStart + 1 .. ^1]
    elif fragStart >= 0:
      url.path = s[i ..< fragStart]
      url.fragment = s[fragStart + 1 .. ^1]
    else:
      url.path = s[i .. ^1]

  if url.path == "":
    url.path = "/"

  return some(url)

proc `$`*(url: URL): string =
  result = url.scheme & "://"
  if url.username != "":
    result &= url.username
    if url.password != "":
      result &= ":" & url.password
    result &= "@"
  result &= url.host
  if url.port != 0:
    let defaultPort = case url.scheme
      of "http": 80
      of "https": 443
      else: 0
    if url.port != defaultPort:
      result &= ":" & $url.port
  result &= url.path
  if url.query != "":
    result &= "?" & url.query
  if url.fragment != "":
    result &= "#" & url.fragment
