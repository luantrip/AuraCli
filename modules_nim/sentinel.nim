## Aura Sentinel - High-Performance Change Detector
## ================================================
##
## Tracks filesystem state using content hashing to detect
## modifications, additions, and deletions instantly.
##
## Usage: sentinel <root_path> [state_file]
## Output: JSON Diff

import std/[os, json, tables, strutils, sha1, streams, re]

const
  IGNORE_DIRS = [
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".nox", "venv", ".venv", "env",
    ".env", "dist", "build", ".build", "target", ".idea", ".vscode",
    "coverage", ".coverage", "htmlcov", ".eggs", "*.egg-info", ".aura"
  ]

  # Skip heavy binary files to speed up scanning
  IGNORE_EXT = [
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".pdf", ".zip",
    ".tar", ".gz", ".7z", ".rar", ".woff", ".woff2", ".ttf", ".eot"
  ]

type
  FileState = object
    hash: string
    size: int64

  StateMap = Table[string, FileState]

  DiffReport = object
    added: seq[string]
    modified: seq[string]
    deleted: seq[string]
    scanned_count: int
    duration_ms: int

proc shouldIgnore(path: string, isDir: bool): bool =
  let name = extractFilename(path)
  
  # Ignore hidden files/dirs (starting with .) except gitignore (handled separately if needed)
  # But we specifically ignore .git, .vscode, etc defined in IGNORE_DIRS
  if name.startsWith(".") and name.len > 1 and not (name in [".gitignore", ".env"]):
      # Check if it is explicitly allowed or just generic hidden
      # For now, simplistic approach: ignore all hidden dirs
      if isDir: return true

  for ignored in IGNORE_DIRS:
    if name == ignored: return true
    if ignored.contains("*"):
      if name.match(re(ignored.replace("*", ".*"))): return true
  
  if not isDir:
    let ext = splitFile(name).ext.toLowerAscii()
    if ext in IGNORE_EXT: return true

  return false

proc calculateHash(path: string): string =
  try:
    # Read file content directly. Sentinel ignores huge binaries, so this is safe enough.
    let content = readFile(path)
    result = $secureHash(content)
  except IOError:
    return ""
  except Exception:
    return ""

proc scanDirectory(rootPath: string): StateMap =
  result = initTable[string, FileState]()
  
  try:
    for kind, path in walkDir(rootPath):
      let relativePath = path.replace(rootPath & "/", "")
      
      if shouldIgnore(path, kind == pcDir):
        continue

      if kind == pcDir:
        # Recurse
        let subMap = scanDirectory(path)
        for k, v in subMap:
          result[k] = v
      elif kind == pcFile:
        let hash = calculateHash(path)
        if hash != "":
          try:
            let size = getFileSize(path)
            # Store relative path
            # Remove rootPath prefix if present to normalize
            var key = path
            if key.startsWith(rootPath):
              key = key[rootPath.len..^1]
            if key.startsWith("/"): key = key[1..^1]
            
            result[key] = FileState(hash: hash, size: size)
          except OSError:
            discard
  except OSError:
    discard

proc compareStates(oldState, newState: StateMap): DiffReport =
  result.scanned_count = newState.len
  result.added = @[]
  result.modified = @[]
  result.deleted = @[]

  # Check for Added and Modified
  for path, info in newState:
    if not oldState.hasKey(path):
      result.added.add(path)
    elif oldState[path].hash != info.hash:
      result.modified.add(path)

  # Check for Deleted
  for path, info in oldState:
    if not newState.hasKey(path):
      result.deleted.add(path)

proc loadState(path: string): StateMap =
  result = initTable[string, FileState]()
  if not fileExists(path): return
  
  try:
    let jsonNode = parseFile(path)
    for path, data in jsonNode:
      result[path] = FileState(
        hash: data["hash"].getStr(),
        size: data["size"].getBiggestInt()
      )
  except:
    discard # Corrupted state or empty, start fresh

proc saveState(path: string, state: StateMap) =
  var jsonNode = newJObject()
  for path, info in state:
    jsonNode[path] = %* {
      "hash": info.hash,
      "size": info.size
    }
  writeFile(path, $jsonNode)

import std/times

proc main() =
  let args = commandLineParams()
  if args.len < 1:
    quit("Usage: sentinel <root_path> [state_file]")
  if args[0] == "--version" or args[0] == "-v":
    echo "sentinel 1.0.0"
    quit(0)

  let rootPath = absolutePath(args[0])
  let stateFile = if args.len > 1: args[1] 
                  else: rootPath / ".aura" / "sentinel_state.json"

  let t0 = epochTime()

  # 1. Load Previous State
  let oldState = loadState(stateFile)

  # 2. Scan Current State
  let newState = scanDirectory(rootPath)

  # 3. Compare
  var diff = compareStates(oldState, newState)
  diff.duration_ms = int((epochTime() - t0) * 1000)

  # 4. Save New State
  try:
    createDir(splitFile(stateFile).dir)
    saveState(stateFile, newState)
  except Exception as e:
    # If we can't save state, we still output diff but it won't persist
    discard

  # 5. Output JSON
  let jsonOutput = %* {
    "added": diff.added,
    "modified": diff.modified,
    "deleted": diff.deleted,
    "stats": {
      "scanned": diff.scanned_count,
      "duration_ms": diff.duration_ms
    }
  }
  echo $jsonOutput

when isMainModule:
  main()
