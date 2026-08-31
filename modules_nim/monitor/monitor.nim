## Aura Monitor - Terminal Content Browser
## ========================================
##
## A high-performance terminal-based content viewer for the Aura CLI.
## Designed to render web pages, documentation, and monitor content
## directly in the terminal.
##
## Features:
## - HTML rendering with ANSI colors
## - Markdown rendering
## - HTTP/HTTPS content fetching
## - Vim-style navigation
## - Search functionality
## - Link extraction and navigation
##
## Build: nim c -d:release -d:ssl -o:bin/aura-monitor modules_nim/monitor/monitor.nim
## Usage: ./bin/aura-monitor [options] [URL or file]
##
## Part of the Aura CLI ecosystem.
## Consolidated from Chawan browser source.

{.push raises: [].}

import std/[strutils, parseopt, options, json]
import monitor_types
import monitor_ansi
import monitor_html
import monitor_md
import monitor_fetch
import monitor_term

const
  VERSION = MONITOR_VERSION
  HELP_TEXT = """
Aura Monitor v""" & VERSION & """

Terminal-based content browser for the Aura CLI ecosystem.

USAGE:
  aura-monitor [options] [URL or file]

OPTIONS:
  -d, --dump          Dump content to stdout (non-interactive)
  -w, --width=N       Set output width (default: terminal width)
  -c, --color=MODE    Color mode: auto, true, 256, 16, mono
  -T, --type=MIME     Force content type
  -j, --json          Output as JSON (with --dump)
  -h, --help          Show this help
  -v, --version       Show version

INTERACTIVE COMMANDS:
  q, Esc      Quit
  j, Down     Scroll down
  k, Up       Scroll up
  g, Home     Go to top
  G, End      Go to bottom
  Ctrl+F      Page down
  Ctrl+B      Page up
  /           Search
  n           Next search result
  N           Previous search result
  o           Open URL
  [           Previous link
  ]           Next link
  Enter       Follow link
  r           Reload
  l           Show links

EXAMPLES:
  aura-monitor https://example.com
  aura-monitor README.md
  aura-monitor --dump https://api.example.com/data.json
  aura-monitor -w 80 --color=256 page.html

OUTPUT FORMATS:
  The monitor automatically detects content type from:
  - HTTP Content-Type header
  - File extension
  - --type flag override

  Supported types:
  - text/html (HTML documents)
  - text/markdown (Markdown files)
  - application/json (JSON data)
  - text/plain (Plain text)
  - text/gemini (Gemini protocol)
"""

type
  ViewerMode* = enum
    vmInteractive
    vmDump

  InputMode* = enum
    imNormal
    imSearch
    imOpen
    imLinks
    imHelp

  ViewerState* = object
    url*: string
    content*: RenderedContent
    scrollOffset*: int
    selectedLink*: int
    searchQuery*: string
    searchResults*: seq[int]
    searchIndex*: int
    inputBuffer*: string
    statusMessage*: string
    running*: bool
    inputMode*: InputMode

  Viewer* = object
    mode*: ViewerMode
    terminal*: Terminal
    state*: ViewerState
    config*: MonitorConfig
    outputJson*: bool
    forceContentType*: Option[ContentType]

proc newViewer*(mode: ViewerMode = vmInteractive): Viewer =
  result.mode = mode
  result.terminal = initTerminal()
  result.config = defaultConfig()
  result.config.columns = result.terminal.width
  result.config.lines = result.terminal.height
  result.state.running = true

proc cleanup*(v: var Viewer) =
  if v.mode == vmInteractive:
    v.terminal.exitAltScreen()
    v.terminal.showCursor()
  v.terminal.cleanup()

proc render*(v: var Viewer; content: string;
    contentType: ContentType): RenderedContent =
  ## Render content based on type
  let width = v.config.columns

  case contentType
  of ctHtml:
    result = renderHtml(content, width)
  of ctMarkdown:
    result = renderMarkdown(content, width)
  of ctJson:
    # Pretty-print JSON
    try:
      let parsed = parseJson(content)
      let pretty = parsed.pretty()
      result.lines = @[]
      for line in pretty.splitLines:
        result.lines.add(ContentLine(text: line))
    except:
      result.lines = @[ContentLine(text: content)]
  of ctPlain, ctGemini:
    # Just split lines
    result.lines = @[]
    for line in content.splitLines:
      result.lines.add(ContentLine(text: line))

proc loadUrl*(v: var Viewer; url: string): bool =
  ## Load content from URL or file
  v.state.url = url
  v.state.statusMessage = "Loading " & url & "..."

  let fetchResult = fetchUrl(url, FetchOptions(
    timeout: v.config.timeout,
    followRedirects: true,
    maxRedirects: v.config.maxRedirects,
    userAgent: v.config.userAgent
  ))

  if not fetchResult.success:
    v.state.statusMessage = "Error: " & fetchResult.errorMessage
    v.state.content.lines = @[ContentLine(text: "Error loading " & url)]
    v.state.content.lines.add(ContentLine(text: fetchResult.errorMessage))
    return false

  let contentType = if v.forceContentType.isSome:
    v.forceContentType.get
  else:
    fetchResult.contentType

  v.state.content = v.render(fetchResult.content, contentType)
  v.state.url = fetchResult.finalUrl
  v.state.scrollOffset = 0
  v.state.selectedLink = 0
  v.state.statusMessage = fetchResult.finalUrl

  if v.state.content.title != "":
    v.terminal.setTitle("Aura Monitor: " & v.state.content.title)

  return true

proc fitToWidth(s: string; width: int): string =
  ## Keep terminal chrome stable when a URL or message is wider than its region.
  if width <= 0:
    return ""
  if s.len <= width:
    return s
  if width <= 3:
    return s[0 ..< width]
  return s[0 ..< width - 3] & "..."

proc drawStatusBar*(v: var Viewer) =
  ## Draw status bar at bottom
  let y = v.terminal.height
  v.terminal.moveCursor(1, y)
  v.terminal.clearLine()

  let modeLabel = case v.state.inputMode
    of imSearch: " SEARCH "
    of imOpen: " OPEN "
    of imLinks: " LINKS "
    else: " AURA "
  let statusFormat = initFormat(
    cellColor(rgb(0, 0, 0)),
    cellColor(rgb(0, 175, 255)),
    {ffBold}
  )

  let totalLines = v.state.content.lines.len
  let currentLine = v.state.scrollOffset + 1
  let posInfo = " " & $currentLine & "/" & $totalLines & " "
  let statusText = " " & v.state.statusMessage
  let messageWidth = max(0, v.terminal.width - modeLabel.len - posInfo.len)

  v.terminal.writeFormatted(modeLabel, statusFormat)
  v.terminal.writeFormatted(fitToWidth(statusText, messageWidth), statusFormat)
  let posX = max(1, v.terminal.width - posInfo.len + 1)
  v.terminal.writeAt(posX, y, posInfo)

proc drawContent*(v: var Viewer) =
  ## Draw content area
  let viewHeight = v.terminal.height - 1 # Reserve 1 line for status

  for i in 0 ..< viewHeight:
    let lineIndex = v.state.scrollOffset + i
    v.terminal.moveCursor(1, i + 1)
    v.terminal.clearLine()

    if lineIndex < v.state.content.lines.len:
      let line = v.state.content.lines[lineIndex]
      let visibleText = fitToWidth(line.text, max(1, v.terminal.width))

      if line.formats.len == 0:
        v.terminal.write(visibleText)
      else:
        var formatIdx = 0

        for j, c in visibleText:
          while formatIdx < line.formats.len and line.formats[formatIdx].pos <= j:
            try:
              stdout.write(line.formats[formatIdx].format.toAnsiString())
            except:
              discard
            inc formatIdx
          try:
            stdout.write(c)
          except:
            discard

        try:
          stdout.write(ANSI_RESET)
        except:
          discard

proc drawLinksScreen(v: var Viewer) =
  v.terminal.clearScreen()
  let links = v.state.content.links
  v.terminal.writeAt(2, 2, "Links on this page")
  v.terminal.writeAt(2, 3, "j/k or arrows to select, Enter to open, Esc to return")

  if links.len == 0:
    v.terminal.writeAt(2, 5, "No links were found in this document.")
    return

  let viewHeight = max(1, v.terminal.height - 6)
  let first = max(0, v.state.selectedLink - viewHeight div 2)
  let last = min(links.len, first + viewHeight)
  for i in first ..< last:
    let marker = if i == v.state.selectedLink: "> " else: "  "
    let label = if links[i].text.len > 0: links[i].text else: links[i].url
    let entry = marker & $(i + 1) & ". " & label & "  " & links[i].url
    v.terminal.writeAt(2, 5 + i - first, fitToWidth(entry, max(1, v.terminal.width - 3)))

proc drawHelpScreen(v: var Viewer) =
  ## Clears the screen and draws a centered help menu.
  v.terminal.clearScreen()
  let helpLines = @[
    "Aura Monitor Help",
    "-----------------",
    "",
    "q, Esc      Quit",
    "j, Down     Scroll down",
    "k, Up       Scroll up",
    "g, Home     Go to top",
    "G, End      Go to bottom",
    "Ctrl+F      Page down",
    "Ctrl+B      Page up",
    "d / u       Half-page down / up",
    "",
    "/           Search for text",
    "n           Next search result",
    "N           Previous search result",
    "",
    "r           Reload content",
    "o           Open new URL/file",
    "l           List links on page",
    "[ , ]       Navigate links",
    "Enter       Follow selected link",
    "",
    "Press any key to close this help"
  ]

  let startY = max(1, (v.terminal.height - helpLines.len) div 2)
  for i, line in helpLines:
    if startY + i < v.terminal.height:
      let x = max(1, (v.terminal.width - line.len) div 2)
      v.terminal.writeAt(x, startY + i, fitToWidth(line, max(1, v.terminal.width)))

proc draw*(v: var Viewer) =
  ## Full screen redraw
  v.terminal.hideCursor()
  if v.state.inputMode == imHelp:
    v.drawHelpScreen()
  elif v.state.inputMode == imLinks:
    v.drawLinksScreen()
    v.drawStatusBar()
  else:
    v.drawContent()
    v.drawStatusBar()
  v.terminal.flush()

proc scrollTo*(v: var Viewer; offset: int) =
  ## Scroll to specific offset
  let maxOffset = max(0, v.state.content.lines.len - (v.terminal.height - 1))
  v.state.scrollOffset = clamp(offset, 0, maxOffset)

proc scrollBy*(v: var Viewer; delta: int) =
  v.scrollTo(v.state.scrollOffset + delta)

proc performSearch(v: var Viewer) =
  ## Perform a case-insensitive search and store results
  v.state.searchResults = @[]
  v.state.searchIndex = 0

  if v.state.searchQuery.len == 0:
    return

  let query = v.state.searchQuery.toLower()
  for i, line in v.state.content.lines:
    if line.text.toLower().contains(query):
      v.state.searchResults.add(i)

  if v.state.searchResults.len > 0:
    v.state.statusMessage = "Found " & $v.state.searchResults.len & " matches for '" & v.state.searchQuery & "'"
    # Scroll to the first result
    v.scrollTo(v.state.searchResults[0])
  else:
    v.state.statusMessage = "No matches found for '" & v.state.searchQuery & "'"

proc handleInput*(v: var Viewer): bool =
  ## Handle input, return false to quit
  let input = v.terminal.readInput()
  if input.isNone:
    return true

  let event = input.get
  if not event.isKey:
    return true

  let key = event.key

  if v.state.inputMode == imHelp:
    v.state.inputMode = imNormal
    return true

  if v.state.inputMode == imLinks:
    case key
    of 'q':
      return false
    of '\e':
      v.state.inputMode = imNormal
      v.state.statusMessage = v.state.url
    of 'j':
      if v.state.selectedLink < v.state.content.links.len - 1:
        inc v.state.selectedLink
    of 'k':
      if v.state.selectedLink > 0:
        dec v.state.selectedLink
    of '\r', '\n':
      if v.state.selectedLink < v.state.content.links.len:
        let url = v.state.content.links[v.state.selectedLink].url
        v.state.inputMode = imNormal
        discard v.loadUrl(url)
    else:
      discard
    return true

  if v.state.inputMode == imSearch:
    case key
    of '\r', '\n': # Enter
      v.state.inputMode = imNormal
      if v.state.searchQuery.len > 0:
        performSearch(v)
      else:
        v.state.statusMessage = v.state.url # Restore status
    of '\e': # Escape
      v.state.inputMode = imNormal
      v.state.searchResults = @[]
      v.state.statusMessage = v.state.url # Restore status
    of '\b', '\x7f': # Backspace
      if v.state.searchQuery.len > 0:
        v.state.searchQuery.setLen(v.state.searchQuery.len - 1)
      v.state.statusMessage = "Search: " & v.state.searchQuery
    else:
      if key >= ' ': # is printable
        v.state.searchQuery.add(key)
        v.state.statusMessage = "Search: " & v.state.searchQuery
    return true

  if v.state.inputMode == imOpen:
    case key
    of '\r', '\n':
      v.state.inputMode = imNormal
      if v.state.inputBuffer.len > 0:
        discard v.loadUrl(v.state.inputBuffer)
      else:
        v.state.statusMessage = v.state.url
    of '\e':
      v.state.inputMode = imNormal
      v.state.statusMessage = v.state.url
    of '\b', '\x7f':
      if v.state.inputBuffer.len > 0:
        v.state.inputBuffer.setLen(v.state.inputBuffer.len - 1)
      v.state.statusMessage = "Open: " & v.state.inputBuffer
    else:
      if key >= ' ':
        v.state.inputBuffer.add(key)
        v.state.statusMessage = "Open: " & v.state.inputBuffer
    return true

  # Check for Ctrl modifiers
  if modCtrl in event.modifiers:
    case key
    of 'c', 'q':
      return false
    of 'f':
      v.scrollBy(v.terminal.height - 1)
    of 'b':
      v.scrollBy(-(v.terminal.height - 1))
    of 'l':
      v.draw()
    else:
      discard
    return true

  case key
  of '?':
    v.state.inputMode = imHelp
  of 'n':
    if v.state.searchResults.len > 0:
      v.state.searchIndex = (v.state.searchIndex + 1) mod v.state.searchResults.len
      let lineNum = v.state.searchResults[v.state.searchIndex]
      v.scrollTo(lineNum)
      v.state.statusMessage = "Match " & $(v.state.searchIndex + 1) & "/" & $v.state.searchResults.len
  of 'N':
    if v.state.searchResults.len > 0:
      v.state.searchIndex = (v.state.searchIndex - 1 + v.state.searchResults.len) mod v.state.searchResults.len
      let lineNum = v.state.searchResults[v.state.searchIndex]
      v.scrollTo(lineNum)
      v.state.statusMessage = "Match " & $(v.state.searchIndex + 1) & "/" & $v.state.searchResults.len
  of '/':
    v.state.inputMode = imSearch
    v.state.searchQuery = ""
    v.state.searchResults = @[]
    v.state.searchIndex = 0
    v.state.statusMessage = "Search: "
  of 'o':
    v.state.inputMode = imOpen
    v.state.inputBuffer = ""
    v.state.statusMessage = "Open: "
  of 'q', '\e':
    return false
  of 'j':
    v.scrollBy(1)
  of 'k':
    v.scrollBy(-1)
  of 'g':
    v.scrollTo(0)
  of 'G':
    v.scrollTo(v.state.content.lines.len)
  of 'd':
    v.scrollBy(v.terminal.height div 2)
  of 'u':
    v.scrollBy(-(v.terminal.height div 2))
  of 'r':
    discard v.loadUrl(v.state.url)
  of 'l':
    v.state.inputMode = imLinks
    v.state.statusMessage = $v.state.content.links.len & " links found"
  of '[':
    # Previous link
    if v.state.selectedLink > 0:
      dec v.state.selectedLink
      v.state.statusMessage = "Link " & $(v.state.selectedLink + 1) & "/" & $v.state.content.links.len & ": " &
          v.state.content.links[v.state.selectedLink].url
  of ']':
    # Next link
    if v.state.selectedLink < v.state.content.links.len - 1:
      inc v.state.selectedLink
      v.state.statusMessage = "Link " & $(v.state.selectedLink + 1) & "/" & $v.state.content.links.len & ": " &
          v.state.content.links[v.state.selectedLink].url
  of '\r', '\n':
    # Follow selected link
    if v.state.selectedLink < v.state.content.links.len:
      let url = v.state.content.links[v.state.selectedLink].url
      discard v.loadUrl(url)
  else:
    discard

  return true

proc runInteractive*(v: var Viewer; url: string) =
  ## Run interactive viewer
  v.terminal.enterAltScreen()
  v.terminal.setRawMode()
  v.terminal.hideCursor()

  if url != "":
    discard v.loadUrl(url)
  else:
    v.state.content.lines = @[
      ContentLine(text: ""),
      ContentLine(text: "  AURA MONITOR  v" & VERSION),
      ContentLine(text: "  Terminal content browser"),
      ContentLine(text: ""),
      ContentLine(text: "  o  Open a URL or file"),
      ContentLine(text: "  ?  View keyboard commands"),
      ContentLine(text: "  q  Quit"),
      ContentLine(text: ""),
    ]
    v.state.statusMessage = "Ready"

  while v.state.running:
    v.draw()
    if not v.handleInput():
      break

  v.cleanup()

proc runDump*(v: var Viewer; url: string) =
  ## Run dump mode (output to stdout)
  if not v.loadUrl(url):
    quit(1)

  if v.outputJson:
    # JSON output
    var output = %*{
      "url": v.state.url,
      "title": v.state.content.title,
      "lines": v.state.content.lines.len,
      "links": v.state.content.links.len,
      "content": ""
    }

    var text = ""
    for line in v.state.content.lines:
      text &= line.text & "\n"
    output["content"] = %text

    var linksArr = newJArray()
    for link in v.state.content.links:
      linksArr.add(%*{"text": link.text, "url": link.url})
    output["links"] = linksArr

    echo output.pretty()
  else:
    # Plain text output
    for line in v.state.content.lines:
      echo line.toAnsi()

proc main() =
  var viewer = newViewer()
  var url = ""
  var showHelp = false
  var showVersion = false

  # Parse command line
  var p = initOptParser()
  while true:
    p.next()
    case p.kind
    of cmdEnd:
      break
    of cmdShortOption, cmdLongOption:
      case p.key.toLowerAscii
      of "d", "dump":
        viewer.mode = vmDump
      of "w", "width":
        try:
          viewer.config.columns = parseInt(p.val)
        except:
          discard
      of "c", "color":
        case p.val.toLowerAscii
        of "auto": viewer.terminal.colorMode = cmAuto
        of "true", "24bit": viewer.terminal.colorMode = cmTrue
        of "256": viewer.terminal.colorMode = cm256
        of "16": viewer.terminal.colorMode = cm16
        of "mono": viewer.terminal.colorMode = cmMono
        else: discard
      of "t", "type":
        case p.val.toLowerAscii
        of "html", "text/html":
          viewer.forceContentType = some(ctHtml)
        of "markdown", "md", "text/markdown":
          viewer.forceContentType = some(ctMarkdown)
        of "json", "application/json":
          viewer.forceContentType = some(ctJson)
        of "plain", "text/plain":
          viewer.forceContentType = some(ctPlain)
        of "gemini", "text/gemini":
          viewer.forceContentType = some(ctGemini)
        else: discard
      of "j", "json":
        viewer.outputJson = true
      of "h", "help":
        showHelp = true
      of "v", "version":
        showVersion = true
      else:
        discard
    of cmdArgument:
      url = p.key

  if showHelp:
    echo HELP_TEXT
    quit(0)

  if showVersion:
    echo "Aura Monitor v" & VERSION
    quit(0)

  # Run appropriate mode
  case viewer.mode
  of vmInteractive:
    viewer.runInteractive(url)
  of vmDump:
    if url == "":
      try:
        stderr.writeLine("Error: URL required for dump mode")
      except:
        discard
      quit(1)
    viewer.runDump(url)

when isMainModule:
  main()
