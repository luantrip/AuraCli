## Aura Monitor - Terminal Handler
## ================================
##
## Terminal manipulation and rendering for TUI display.
## Handles screen management, cursor control, and output.
##
## Features:
## - Raw mode handling
## - Screen buffer management
## - Cursor positioning
## - Color output
## - Input handling
## - Terminal size detection

{.push raises: [].}

import std/[os, posix, termios, strutils, options]
import monitor_types

type
  TerminalMode* = enum
    tmNormal
    tmRaw
    tmCbreak

  Modifier* = enum
    modCtrl
    modAlt
    modShift

  InputEvent* = object
    case isKey*: bool
    of true:
      key*: char
      modifiers*: set[Modifier]
    of false:
      mouse*: MouseEvent

  MouseEvent* = object
    x*, y*: int
    button*: int
    pressed*: bool

  Terminal* = object
    fd*: cint
    origTermios*: Termios
    mode*: TerminalMode
    width*, height*: int
    colorMode*: ColorMode
    buffer*: seq[string]
    cursorX*, cursorY*: int
    cursorVisible*: bool

# =============================================================================
# TERMINAL INITIALIZATION
# =============================================================================

type
  Winsize = object
    ws_row: cushort
    ws_col: cushort
    ws_xpixel: cushort
    ws_ypixel: cushort

const
  TIOCGWINSZ = 0x40087468'i32 # macOS/BSD
  STDOUT_FILENO = 1

proc safeWrite(s: string) =
  ## Safe write that doesn't raise exceptions
  try:
    stdout.write(s)
  except:
    discard

proc getTerminalSize*(): tuple[width, height: int] =
  ## Get current terminal size
  var ws: Winsize
  if posix.ioctl(STDOUT_FILENO.cint, TIOCGWINSZ.cuint, addr ws) == 0:
    result = (int(ws.ws_col), int(ws.ws_row))
  else:
    # Fallback to environment variables
    let cols = getEnv("COLUMNS", "80")
    let rows = getEnv("LINES", "24")
    try:
      result = (parseInt(cols), parseInt(rows))
    except:
      result = (80, 24)

proc detectColorMode*(): ColorMode =
  ## Detect terminal color capabilities
  let colorterm = getEnv("COLORTERM", "").toLowerAscii
  let term = getEnv("TERM", "").toLowerAscii

  if colorterm in ["truecolor", "24bit"]:
    return cmTrue

  if "256color" in term or "256" in colorterm:
    return cm256

  if term in ["dumb", "unknown"]:
    return cmMono

  if term.startsWith("xterm") or term.startsWith("screen") or term.startsWith("tmux"):
    return cm256

  if term.startsWith("linux"):
    return cm16

  return cmAuto

proc initTerminal*(): Terminal =
  ## Initialize terminal handling
  result.fd = STDIN_FILENO
  result.mode = tmNormal
  let size = getTerminalSize()
  result.width = size.width
  result.height = size.height
  result.colorMode = detectColorMode()
  result.cursorVisible = true

  # Save original termios
  discard tcgetattr(result.fd, addr result.origTermios)

proc cleanup*(t: var Terminal) =
  ## Restore terminal to original state
  if t.mode != tmNormal:
    discard tcsetattr(t.fd, TCSAFLUSH, addr t.origTermios)
    t.mode = tmNormal

  # Show cursor
  if not t.cursorVisible:
    safeWrite("\e[?25h")
    t.cursorVisible = true

  # Reset colors
  safeWrite(ANSI_RESET)
  try:
    stdout.flushFile()
  except:
    discard

proc setRawMode*(t: var Terminal) =
  ## Enable raw mode for input handling
  if t.mode == tmRaw:
    return

  var raw = t.origTermios
  raw.c_lflag = raw.c_lflag and not (ECHO or ICANON or ISIG or IEXTEN)
  raw.c_iflag = raw.c_iflag and not (BRKINT or ICRNL or INPCK or ISTRIP or IXON)
  raw.c_cflag = raw.c_cflag or CS8
  raw.c_oflag = raw.c_oflag and not OPOST
  raw.c_cc[VMIN] = 0.char
  raw.c_cc[VTIME] = 1.char # 100ms timeout

  discard tcsetattr(t.fd, TCSAFLUSH, addr raw)
  t.mode = tmRaw

proc setNormalMode*(t: var Terminal) =
  ## Restore normal terminal mode
  if t.mode == tmNormal:
    return

  discard tcsetattr(t.fd, TCSAFLUSH, addr t.origTermios)
  t.mode = tmNormal

# =============================================================================
# CURSOR CONTROL
# =============================================================================

proc moveCursor*(t: var Terminal; x, y: int) =
  ## Move cursor to position (1-based)
  safeWrite("\e[" & $y & ";" & $x & "H")
  t.cursorX = x
  t.cursorY = y

proc moveCursorUp*(t: var Terminal; n: int = 1) =
  safeWrite("\e[" & $n & "A")
  t.cursorY = max(1, t.cursorY - n)

proc moveCursorDown*(t: var Terminal; n: int = 1) =
  safeWrite("\e[" & $n & "B")
  t.cursorY = min(t.height, t.cursorY + n)

proc moveCursorRight*(t: var Terminal; n: int = 1) =
  safeWrite("\e[" & $n & "C")
  t.cursorX = min(t.width, t.cursorX + n)

proc moveCursorLeft*(t: var Terminal; n: int = 1) =
  safeWrite("\e[" & $n & "D")
  t.cursorX = max(1, t.cursorX - n)

proc saveCursor*(t: Terminal) =
  safeWrite("\e[s")

proc restoreCursor*(t: Terminal) =
  safeWrite("\e[u")

proc hideCursor*(t: var Terminal) =
  if t.cursorVisible:
    safeWrite("\e[?25l")
    t.cursorVisible = false

proc showCursor*(t: var Terminal) =
  if not t.cursorVisible:
    safeWrite("\e[?25h")
    t.cursorVisible = true

# =============================================================================
# SCREEN CONTROL
# =============================================================================

proc clearScreen*(t: Terminal) =
  safeWrite("\e[2J")

proc clearLine*(t: Terminal) =
  safeWrite("\e[2K")

proc clearToEndOfLine*(t: Terminal) =
  safeWrite("\e[K")

proc clearToEndOfScreen*(t: Terminal) =
  safeWrite("\e[J")

proc enterAltScreen*(t: var Terminal) =
  safeWrite("\e[?1049h")

proc exitAltScreen*(t: var Terminal) =
  safeWrite("\e[?1049l")

proc scrollUp*(t: Terminal; n: int = 1) =
  safeWrite("\e[" & $n & "S")

proc scrollDown*(t: Terminal; n: int = 1) =
  safeWrite("\e[" & $n & "T")

proc setScrollRegion*(t: Terminal; top, bottom: int) =
  safeWrite("\e[" & $top & ";" & $bottom & "r")

proc resetScrollRegion*(t: Terminal) =
  safeWrite("\e[r")

# =============================================================================
# OUTPUT
# =============================================================================

proc write*(t: Terminal; s: string) =
  safeWrite(s)

proc writeLine*(t: Terminal; s: string) =
  safeWrite(s)

proc flush*(t: Terminal) =
  stdout.flushFile()

proc writeAt*(t: var Terminal; x, y: int; s: string) =
  t.moveCursor(x, y)
  safeWrite(s)

proc writeFormatted*(t: Terminal; s: string; format: Format) =
  safeWrite(format.toAnsiString())
  safeWrite(s)
  safeWrite(ANSI_RESET)

proc writeContent*(t: var Terminal; content: RenderedContent; startY: int = 1) =
  ## Write rendered content to terminal
  var y = startY
  for line in content.lines:
    if y > t.height:
      break

    t.moveCursor(1, y)
    t.clearLine()

    if line.formats.len == 0:
      safeWrite(line.text)
    else:
      var formatIdx = 0
      var currentFormat = initFormat(defaultColor(), defaultColor())

      for i, c in line.text:
        while formatIdx < line.formats.len and line.formats[formatIdx].pos <= i:
          currentFormat = line.formats[formatIdx].format
          safeWrite(currentFormat.toAnsiString())
          inc formatIdx
        safeWrite($c)

      safeWrite(ANSI_RESET)

    inc y

  t.flush()

# =============================================================================
# INPUT
# =============================================================================

proc readKey*(t: Terminal; timeout: int = -1): Option[char] =
  ## Read a single key (non-blocking if timeout >= 0)
  var buf: array[1, char]

  if t.mode != tmRaw:
    return none(char)

  let n = posix.read(t.fd, addr buf[0], 1)
  if n > 0:
    return some(buf[0])

  return none(char)

proc readInput*(t: Terminal): Option[InputEvent] =
  ## Read input event (key or escape sequence)
  let key = t.readKey()
  if key.isNone:
    return none(InputEvent)

  let c = key.get

  # Check for escape sequence
  if c == '\e':
    let next = t.readKey(100) # Short timeout for escape sequence
    if next.isNone:
      # Just ESC
      return some(InputEvent(isKey: true, key: '\e'))

    if next.get == '[':
      # CSI sequence
      var seq = ""
      while true:
        let ch = t.readKey(50)
        if ch.isNone:
          break
        seq &= ch.get
        if ch.get in '@'..'~':
          break

      # Parse common sequences
      case seq
      of "A": return some(InputEvent(isKey: true, key: 'k')) # Up
      of "B": return some(InputEvent(isKey: true, key: 'j')) # Down
      of "C": return some(InputEvent(isKey: true, key: 'l')) # Right
      of "D": return some(InputEvent(isKey: true, key: 'h')) # Left
      of "H": return some(InputEvent(isKey: true, key: 'g')) # Home
      of "F": return some(InputEvent(isKey: true, key: 'G')) # End
      of "5~": return some(InputEvent(isKey: true, key: '\x02')) # Page Up (Ctrl+B)
      of "6~": return some(InputEvent(isKey: true, key: '\x06')) # Page Down (Ctrl+F)
      else:
        discard

    # Alt + key
    return some(InputEvent(isKey: true, key: next.get, modifiers: {modAlt}))

  # Check for Ctrl
  if c < ' ':
    case c
    of '\x01': return some(InputEvent(isKey: true, key: 'a', modifiers: {modCtrl})) # Ctrl+A
    of '\x02': return some(InputEvent(isKey: true, key: 'b', modifiers: {modCtrl})) # Ctrl+B
    of '\x03': return some(InputEvent(isKey: true, key: 'c', modifiers: {modCtrl})) # Ctrl+C
    of '\x04': return some(InputEvent(isKey: true, key: 'd', modifiers: {modCtrl})) # Ctrl+D
    of '\x06': return some(InputEvent(isKey: true, key: 'f', modifiers: {modCtrl})) # Ctrl+F
    of '\x0c': return some(InputEvent(isKey: true, key: 'l', modifiers: {modCtrl})) # Ctrl+L
    of '\x11': return some(InputEvent(isKey: true, key: 'q', modifiers: {modCtrl})) # Ctrl+Q
    of '\x17': return some(InputEvent(isKey: true, key: 'w', modifiers: {modCtrl})) # Ctrl+W
    else:
      discard

  return some(InputEvent(isKey: true, key: c))

# =============================================================================
# UTILITY
# =============================================================================

proc updateSize*(t: var Terminal) =
  ## Update terminal size
  let size = getTerminalSize()
  t.width = size.width
  t.height = size.height

proc beep*(t: Terminal) =
  safeWrite($'\a')
  t.flush()

proc setTitle*(t: Terminal; title: string) =
  safeWrite("\e]0;" & title & "\a")
  t.flush()
