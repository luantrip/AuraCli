## Imagination Engine - Ultra-Fast Filesystem Scanner

import std/[os, json, times, strutils, sequtils, algorithm, parseopt, tables]

const
  VERSION = "1.0.0"
  MAX_PREVIEW_LINES = 8
  MAX_PREVIEW_CHARS = 500

  CODE_EXTENSIONS = [
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".nim",
    ".c", ".cpp", ".h", ".hpp", ".java", ".kt", ".swift", ".rb",
    ".php", ".cs", ".scala", ".clj", ".ex", ".exs", ".hs", ".ml"
  ]

  CONFIG_EXTENSIONS = [
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".env", ".properties", ".xml"
  ]

  DOC_EXTENSIONS = [
    ".md", ".markdown", ".rst", ".txt", ".adoc", ".org"
  ]

  STYLE_EXTENSIONS = [
    ".css", ".scss", ".sass", ".less", ".tcss", ".styl"
  ]

  DATA_EXTENSIONS = [
    ".csv", ".tsv", ".sql", ".db", ".sqlite"
  ]

  IGNORE_DIRS = [
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".nox", "venv", ".venv", "env",
    ".env", "dist", "build", ".build", "target", ".idea", ".vscode",
    "coverage", ".coverage", "htmlcov", ".eggs", "*.egg-info"
  ]

  BINARY_EXTENSIONS = [
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".pdf", ".zip",
    ".tar", ".gz", ".7z", ".rar", ".woff", ".woff2", ".ttf", ".eot"
  ]

type
  FileCategory* = enum
    fcCode = "code"
    fcConfig = "config"
    fcDoc = "doc"
    fcStyle = "style"
    fcData = "data"
    fcOther = "other"
    fcBinary = "binary"

  FileInfo* = object
    path*: string
    name*: string
    extension*: string
    size*: int64
    lines*: int
    lastModified*: float # Unix timestamp
    category*: FileCategory
    preview*: seq[string]
    isDirectory*: bool
    relevanceScore*: int # 0-100, calculated based on context keywords
    contentSnippet*: string # Relevant snippet extracted from file

  ScanResult* = object
    rootPath*: string
    totalFiles*: int
    totalDirectories*: int
    totalLines*: int
    totalSize*: int64
    scanDuration*: float
    files*: seq[FileInfo]
    byCategory*: Table[FileCategory, int]
    byExtension*: Table[string, int]
    recentlyModified*: seq[FileInfo]

  ScanOptions* = object
    includePreview*: bool
    maxDepth*: int
    includeHidden*: bool
    respectGitignore*: bool
    maxFileSize*: int64 # Skip files larger than this (bytes)
    contextKeywords*: seq[string] # Keywords for relevance scoring
    maxResults*: int # Maximum number of relevant files to return (0 = all)

# Gitignore pattern matching
var gitignorePatterns: seq[string] = @[]

proc loadGitignore(rootPath: string) =
  let gitignorePath = rootPath / ".gitignore"
  if fileExists(gitignorePath):
    try:
      for line in lines(gitignorePath):
        let trimmed = line.strip()
        if trimmed.len > 0 and not trimmed.startsWith("#"):
          gitignorePatterns.add(trimmed)
    except IOError:
      discard

proc matchesGitignore(path: string, isDir: bool): bool =
  let name = extractFilename(path)
  for pattern in gitignorePatterns:
    var p = pattern
    if p.endsWith("/"):
      if isDir and name == p[0..^2]:
        return true
    elif p.contains("*"):
      let parts = p.split("*")
      if parts.len == 2:
        if name.startsWith(parts[0]) and name.endsWith(parts[1]):
          return true
    elif name == p or path.endsWith("/" & p):
      return true
  return false

proc containsSecrets(content: string): bool =
  let contentLower = content.toLowerAscii()
  let secretPatterns = @[
    "sk-proj-", "sk_live_", "sk_test_",
    "api_key", "apikey", "api-key",
    "secret_key", "secretkey", "secret-key",
    "access_key", "accesskey", "access-key",
    "aws_access_key", "aws_secret",
    "password", "passwd", "pwd",
    "token", "bearer",
    "private_key", "privatekey",
    "client_secret", "clientsecret"
  ]
  
  for pattern in secretPatterns:
    if contentLower.contains(pattern):
      let idx = contentLower.find(pattern)
      if idx >= 0:
        let after = contentLower[min(idx + pattern.len, contentLower.len-1)..^1]
        if after.startsWith("=") or after.startsWith(":") or after.startsWith(" "):
          return true
  return false

proc maskSecrets(content: string): string =
  result = content
  let lines = content.splitLines()
  var maskedLines: seq[string] = @[]

  for line in lines:
    var maskedLine = line
    if containsSecrets(line):
      var parts = line.split({'=', ':'}, maxsplit=1)
      if parts.len == 2:
        maskedLine = parts[0] & parts[1][0] & "***MASKED***"
      else:
        maskedLine = "***LINE CONTAINS POTENTIAL SECRET - MASKED***"
    maskedLines.add(maskedLine)

  result = maskedLines.join("\n")

proc categorizeFile(ext: string): FileCategory =
  let e = ext.toLowerAscii()
  if e in CODE_EXTENSIONS: return fcCode
  if e in CONFIG_EXTENSIONS: return fcConfig
  if e in DOC_EXTENSIONS: return fcDoc
  if e in STYLE_EXTENSIONS: return fcStyle
  if e in DATA_EXTENSIONS: return fcData
  if e in BINARY_EXTENSIONS: return fcBinary
  return fcOther

proc shouldIgnoreDir(name: string): bool =
  for ignored in IGNORE_DIRS:
    if name == ignored:
      return true
    if ignored.contains("*"):
      let parts = ignored.split("*")
      if parts.len == 2:
        if name.startsWith(parts[0]) and name.endsWith(parts[1]):
          return true
  return false

proc countLines(filePath: string): int =
  result = 0
  try:
    for _ in lines(filePath):
      inc result
  except IOError:
    result = 0

proc extractPreview(filePath: string, maxLines: int = MAX_PREVIEW_LINES, maskSecrets: bool = true): seq[string] =
  result = @[]
  try:
    var count = 0
    var totalChars = 0
    var fileContent = ""

    for line in lines(filePath):
      fileContent &= line & "\n"

    if maskSecrets and containsSecrets(fileContent):
      fileContent = maskSecrets(fileContent)

    for line in fileContent.splitLines():
      if count >= maxLines or totalChars >= MAX_PREVIEW_CHARS:
        break
      let trimmed = line.strip()
      if trimmed.len > 0:
        result.add(trimmed[0..min(100, trimmed.len-1)])
        totalChars += trimmed.len
      inc count
  except IOError:
    result = @[]

proc extractRelevantSnippet(filePath: string, keywords: seq[string], maxChars: int = 300): string =
  result = ""
  try:
    var bestLine = ""
    var bestScore = 0
    var fileContent = ""

    for line in lines(filePath):
      fileContent &= line & "\n"

    if containsSecrets(fileContent):
      fileContent = maskSecrets(fileContent)

    for line in fileContent.splitLines():
      let lineLower = line.toLowerAscii()
      var lineScore = 0
      for keyword in keywords:
        let kwLower = keyword.toLowerAscii()
        if lineLower.contains(kwLower):
          lineScore += 2
          if lineLower.contains(" " & kwLower & " ") or
             lineLower.startsWith(kwLower) or
             lineLower.endsWith(kwLower):
            lineScore += 3

      if lineScore > bestScore:
        bestScore = lineScore
        bestLine = line.strip()
        if bestLine.len > maxChars:
          bestLine = bestLine[0..maxChars-1] & "..."

    result = bestLine
  except IOError:
    result = ""

proc calculateRelevanceScore(fileInfo: FileInfo, keywords: seq[string]): int =
  result = 0
  if keywords.len == 0:
    return 50

  let nameLower = fileInfo.name.toLowerAscii()
  let pathLower = fileInfo.path.toLowerAscii()
  var totalMatches = 0
  var exactMatches = 0

  for keyword in keywords:
    let kwLower = keyword.toLowerAscii()

    if nameLower.contains(kwLower):
      totalMatches += 1
      if nameLower == kwLower or nameLower.startsWith(kwLower) or
         nameLower.endsWith(kwLower):
        exactMatches += 1
        result += 40
      else:
        result += 20

    if pathLower.contains(kwLower):
      result += 30

    for previewLine in fileInfo.preview:
      let lineLower = previewLine.toLowerAscii()
      if lineLower.contains(kwLower):
        result += 10
        break

  if totalMatches > 1:
    result += min(20, totalMatches * 5)

  if exactMatches > 0:
    result += min(10, exactMatches * 5)

  result = min(100, result)

proc scanDirectory(rootPath: string, options: ScanOptions): ScanResult =
  let startTime = epochTime()

  var scanResult: ScanResult
  scanResult.rootPath = absolutePath(rootPath)
  scanResult.files = @[]
  scanResult.byCategory = initTable[FileCategory, int]()
  scanResult.byExtension = initTable[string, int]()
  scanResult.recentlyModified = @[]

  for cat in FileCategory:
    scanResult.byCategory[cat] = 0

  if options.respectGitignore:
    loadGitignore(rootPath)

  let recentThreshold = epochTime() - (24 * 60 * 60)

  proc walkDir(currentPath: string, depth: int) =
    if options.maxDepth > 0 and depth > options.maxDepth:
      return

    try:
      for kind, path in walkDir(currentPath):
        let name = extractFilename(path)

        if not options.includeHidden and name.startsWith("."):
          if name != ".gitignore":
            continue

        case kind
        of pcDir:
          if shouldIgnoreDir(name):
            continue
          if options.respectGitignore and matchesGitignore(path, true):
            continue

          inc scanResult.totalDirectories
          walkDir(path, depth + 1)

        of pcFile, pcLinkToFile:
          if options.respectGitignore and matchesGitignore(path, false):
            continue

          let info = getFileInfo(path)
          let ext = splitFile(path).ext
          let category = categorizeFile(ext)

          if options.maxFileSize > 0 and info.size > options.maxFileSize:
            continue

          var fileInfo = FileInfo(
            path: path.replace(scanResult.rootPath & "/", ""),
            name: name,
            extension: ext,
            size: info.size,
            lastModified: info.lastWriteTime.toUnix().float,
            category: category,
            isDirectory: false,
            relevanceScore: 0,
            contentSnippet: ""
          )

          if category != fcBinary:
            fileInfo.lines = countLines(path)
            scanResult.totalLines += fileInfo.lines

            if options.includePreview and fileInfo.size < 50_000:
              fileInfo.preview = extractPreview(path, maskSecrets=true)

            if options.contextKeywords.len > 0:
              fileInfo.relevanceScore = calculateRelevanceScore(
                fileInfo, options.contextKeywords
              )
              if fileInfo.relevanceScore > 0:
                fileInfo.contentSnippet = extractRelevantSnippet(
                  path, options.contextKeywords
                )

          scanResult.files.add(fileInfo)
          scanResult.totalSize += info.size
          inc scanResult.totalFiles

          scanResult.byCategory[category] = scanResult.byCategory.getOrDefault(
              category, 0) + 1

          if ext.len > 0:
            scanResult.byExtension[ext] = scanResult.byExtension.getOrDefault(
                ext, 0) + 1

          if fileInfo.lastModified >= recentThreshold:
            scanResult.recentlyModified.add(fileInfo)

        else:
          discard
    except OSError:
      discard

  walkDir(rootPath, 0)

  if options.contextKeywords.len > 0:
    scanResult.files.sort(proc(a, b: FileInfo): int =
      let scoreCmp = cmp(b.relevanceScore, a.relevanceScore)
      if scoreCmp != 0:
        return scoreCmp
      return cmp(b.lastModified, a.lastModified)
    )

    if options.maxResults > 0:
      var relevantFiles: seq[FileInfo] = @[]
      for file in scanResult.files:
        if file.relevanceScore > 0:
          relevantFiles.add(file)
          if relevantFiles.len >= options.maxResults:
            break
      scanResult.files = relevantFiles
  else:
    scanResult.files.sort(proc(a, b: FileInfo): int =
      cmp(b.lastModified, a.lastModified)
    )

  scanResult.recentlyModified.sort(proc(a, b: FileInfo): int =
    cmp(b.lastModified, a.lastModified)
  )

  if scanResult.recentlyModified.len > 20:
    scanResult.recentlyModified = scanResult.recentlyModified[0..19]

  scanResult.scanDuration = epochTime() - startTime
  scanResult.totalFiles = scanResult.files.len

  result = scanResult

proc toJson*(fi: FileInfo): JsonNode =
  result = %*{
    "path": fi.path,
    "name": fi.name,
    "extension": fi.extension,
    "size": fi.size,
    "lines": fi.lines,
    "last_modified": fi.lastModified,
    "category": $fi.category,
    "preview": fi.preview,
    "is_directory": fi.isDirectory,
    "relevance_score": fi.relevanceScore,
    "content_snippet": fi.contentSnippet
  }

proc toJson*(sr: ScanResult, contextMode: bool = false): JsonNode =
  var categoryJson = newJObject()
  for cat, count in sr.byCategory:
    categoryJson[$cat] = %count

  var extJson = newJObject()
  for ext, count in sr.byExtension:
    extJson[ext] = %count

  if contextMode:
    var relevantPages: seq[JsonNode] = @[]
    var ignoredCount = 0

    for file in sr.files:
      if file.relevanceScore > 0:
        relevantPages.add(file.toJson())
      else:
        inc ignoredCount

    result = %*{
      "root_path": sr.rootPath,
      "relevant_pages": relevantPages,
      "ignored_files_count": ignoredCount,
      "total_files_scanned": sr.totalFiles + ignoredCount,
      "scan_duration_ms": int(sr.scanDuration * 1000)
    }
  else:
    result = %*{
      "root_path": sr.rootPath,
      "total_files": sr.totalFiles,
      "total_directories": sr.totalDirectories,
      "total_lines": sr.totalLines,
      "total_size": sr.totalSize,
      "scan_duration_ms": int(sr.scanDuration * 1000),
      "files": sr.files.mapIt(it.toJson()),
      "by_category": categoryJson,
      "by_extension": extJson,
      "recently_modified": sr.recentlyModified.mapIt(it.toJson())
    }

proc printHelp() =
  echo """
Imagination Engine v""" & VERSION & """

Ultra-fast filesystem scanner for AI-powered code assistants.

USAGE:
  imagination <path> [options]

OPTIONS:
  --json            Output as JSON (default)
  --pretty          Pretty-print JSON output
  --no-preview      Skip file content previews
  --max-depth=N     Maximum directory depth (0 = unlimited)
  --include-hidden  Include hidden files and directories
  --no-gitignore    Don't respect .gitignore patterns
  --max-size=N      Skip files larger than N bytes
  --context=KW      Context keywords for relevance filtering (space-separated)
  --limit=N         Maximum number of relevant files to return (default: 5)
  --help, -h        Show this help
  --version, -v     Show version

EXAMPLES:
  imagination .                                    # Scan current directory
  imagination /path/to/project                     # Scan specific path
  imagination . --pretty                           # Pretty JSON output
  imagination . --no-preview                       # Faster scan without previews
  imagination . --context="login auth user" --limit=5  # Smart context filtering

OUTPUT:
  Returns JSON with file metadata, categories, and statistics.
  With --context: Returns paginated format with relevant_pages and scores.
  Categories: code, config, doc, style, data, binary, other
"""

proc main() =
  var
    targetPath = getCurrentDir()
    outputJson = true
    prettyPrint = false
    contextMode = false
    options = ScanOptions(
      includePreview: true,
      maxDepth: 0,
      includeHidden: false,
      respectGitignore: true,
      maxFileSize: 10_000_000,
      contextKeywords: @[],
      maxResults: 0
    )

  var p = initOptParser()
  while true:
    p.next()
    case p.kind
    of cmdEnd: break
    of cmdShortOption, cmdLongOption:
      case p.key
      of "json": outputJson = true
      of "pretty": prettyPrint = true
      of "no-preview": options.includePreview = false
      of "max-depth":
        options.maxDepth = parseInt(p.val)
      of "include-hidden": options.includeHidden = true
      of "no-gitignore": options.respectGitignore = false
      of "max-size":
        options.maxFileSize = parseInt(p.val)
      of "context":
        contextMode = true
        let keywords = p.val.splitWhitespace()
        options.contextKeywords = keywords
      of "limit":
        options.maxResults = parseInt(p.val)
        if options.maxResults <= 0:
          options.maxResults = 5
      of "help", "h":
        printHelp()
        quit(0)
      of "version", "v":
        echo "Imagination Engine v" & VERSION
        quit(0)
    of cmdArgument:
      targetPath = p.key

  if not dirExists(targetPath):
    stderr.writeLine("Error: Directory not found: " & targetPath)
    quit(1)

  if contextMode and options.maxResults == 0:
    options.maxResults = 5

  let result = scanDirectory(targetPath, options)

  if outputJson:
    let jsonOutput = result.toJson(contextMode)
    if prettyPrint:
      echo jsonOutput.pretty()
    else:
      echo $jsonOutput

when isMainModule:
  main()