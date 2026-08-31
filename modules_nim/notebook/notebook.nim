## Aura Notebook - Safe Context Memory
##
## Strings retornadas pela FFI vivem em buffers globais até a próxima chamada.
## O consumidor Python deve serializar todas as chamadas com seu lock FFI.

{.push raises: [].}

import std/[os, strutils, json, times]

const
  NOTEBOOK_VERSION* = "1.1.0"
  MAX_PAGE_LINES* = 1000
  INDEX_FILENAME* = "index.md"
  ERR_IO* = -1
  ERR_LIMIT* = -2
  ERR_PATH* = -3

var
  lastReadResult {.global.}: string = ""
  lastListResult {.global.}: string = ""
  lastIndexResult {.global.}: string = ""
  lastSessionResult {.global.}: string = ""


proc hasUnsafePath(path: string): bool =
  ## Python applies workspace containment; Nim defensively rejects traversal
  ## components and embedded NULs if the FFI is called by another consumer.
  if path.len == 0 or path.contains('\0'):
    return true
  for component in path.replace('\\', '/').split('/'):
    if component == "..":
      return true
  return false


proc writeFileAtomic(path: string, content: string): bool =
  ## Write and fsync a sibling temporary file, then rename it into place.
  var temporaryPath = ""
  try:
    let parent = parentDir(path)
    if parent.len > 0 and not dirExists(parent):
      createDir(parent)
    temporaryPath = path & ".tmp." & $int(epochTime() * 1000000)
    writeFile(temporaryPath, content)
    moveFile(temporaryPath, path)
    temporaryPath = ""
    return true
  except:
    if temporaryPath.len > 0 and fileExists(temporaryPath):
      try:
        removeFile(temporaryPath)
      except:
        discard
    return false


proc notebookGetVersion*(): cstring {.exportc, dynlib.} =
  return cstring(NOTEBOOK_VERSION)


proc notebookInit*(basePath: cstring): cint {.exportc, dynlib.} =
  try:
    let path = $basePath
    if hasUnsafePath(path):
      return ERR_PATH
    if not dirExists(path):
      createDir(path)
    return 0
  except:
    return ERR_IO


proc notebookWritePage*(filePath: cstring, content: cstring): cint {.exportc, dynlib.} =
  try:
    let path = $filePath
    if hasUnsafePath(path):
      return ERR_PATH
    let parent = parentDir(path)
    let finalContent = $content
    if finalContent.splitLines().len > MAX_PAGE_LINES:
      return ERR_LIMIT
    if parent.len > 0 and not dirExists(parent):
      createDir(parent)
    if not writeFileAtomic(path, finalContent):
      return ERR_IO
    return 0
  except:
    return ERR_IO


proc notebookReadPage*(filePath: cstring): cstring {.exportc, dynlib.} =
  try:
    let path = $filePath
    if hasUnsafePath(path):
      lastReadResult = "ERRO: Caminho inválido"
      return cstring(lastReadResult)
    if not fileExists(path):
      lastReadResult = "ERRO: Página não encontrada: " & path
      return cstring(lastReadResult)
    lastReadResult = readFile(path)
    return cstring(lastReadResult)
  except Exception as e:
    lastReadResult = "ERRO: " & e.msg
    return cstring(lastReadResult)


proc notebookListPages*(dirPath: cstring): cstring {.exportc, dynlib.} =
  try:
    let path = $dirPath
    if hasUnsafePath(path):
      lastListResult = "[]"
      return cstring(lastListResult)
    if not dirExists(path):
      lastListResult = "[]"
      return cstring(lastListResult)

    var pages: seq[string] = @[]
    for kind, file in walkDir(path):
      if kind == pcFile and file.endsWith(".txt"):
        pages.add(extractFilename(file))

    lastListResult = $(%pages)
    return cstring(lastListResult)
  except:
    lastListResult = "[]"
    return cstring(lastListResult)


proc notebookGetPageCount*(dirPath: cstring): cint {.exportc, dynlib.} =
  try:
    let path = $dirPath
    if hasUnsafePath(path) or not dirExists(path):
      return 0

    var count = 0
    for kind, file in walkDir(path):
      if kind == pcFile and file.endsWith(".txt"):
        inc count
    return cint(count)
  except:
    return 0


proc notebookUpdateIndex*(dirPath: cstring,
    indexContent: cstring): cint {.exportc, dynlib.} =
  try:
    let path = $dirPath
    if hasUnsafePath(path):
      return ERR_PATH
    if not dirExists(path):
      createDir(path)
    if not writeFileAtomic(path / INDEX_FILENAME, $indexContent):
      return ERR_IO
    return 0
  except:
    return ERR_IO


proc notebookReadIndex*(dirPath: cstring): cstring {.exportc, dynlib.} =
  try:
    let path = $dirPath
    if hasUnsafePath(path):
      lastIndexResult = "ERRO: Caminho inválido"
      return cstring(lastIndexResult)
    let indexPath = path / INDEX_FILENAME
    if not fileExists(indexPath):
      lastIndexResult = "# Índice do Caderno\n\nNenhuma página registrada ainda."
      return cstring(lastIndexResult)

    lastIndexResult = readFile(indexPath)
    return cstring(lastIndexResult)
  except Exception as e:
    lastIndexResult = "ERRO: " & e.msg
    return cstring(lastIndexResult)


proc notebookDeletePage*(filePath: cstring): cint {.exportc, dynlib.} =
  try:
    let path = $filePath
    if hasUnsafePath(path):
      return ERR_PATH
    if fileExists(path):
      removeFile(path)
    return 0
  except:
    return ERR_IO


proc notebookGetSessionInfo*(dirPath: cstring): cstring {.exportc, dynlib.} =
  try:
    let path = $dirPath
    if hasUnsafePath(path):
      lastSessionResult = "{\"exists\": false, \"page_count\": 0, \"error\": \"invalid path\"}"
      return cstring(lastSessionResult)
    if not dirExists(path):
      lastSessionResult = $(%*{
        "exists": false,
        "page_count": 0,
        "total_size_bytes": 0,
        "session_id": extractFilename(path),
        "session_path": path
      })
      return cstring(lastSessionResult)

    var pageCount = 0
    var totalSize: int64 = 0
    var latestMod = ""

    for kind, file in walkDir(path):
      if kind == pcFile and file.endsWith(".txt"):
        inc pageCount
        let info = getFileInfo(file)
        totalSize += info.size
        let modTime = info.lastWriteTime.format("yyyy-MM-dd HH:mm:ss")
        if modTime > latestMod:
          latestMod = modTime

    let jsonResult = %*{
      "exists": true,
      "page_count": pageCount,
      "total_size_bytes": totalSize,
      "latest_modification": latestMod,
      "session_id": extractFilename(path),
      "session_path": path
    }

    lastSessionResult = $jsonResult
    return cstring(lastSessionResult)
  except:
    lastSessionResult = "{\"exists\": false, \"page_count\": 0, \"total_size_bytes\": 0, \"error\": \"failed to read session\"}"
    return cstring(lastSessionResult)


when isMainModule:
  discard
