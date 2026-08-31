## Aura Prism - Semantic Code Chunker
## ====================================
##
## Breaks source code into semantic blocks (functions, classes)
## for optimized vector embedding.
##
## Features:
## - Indentation-based chunking (Python)
## - Brace-based chunking (C-like languages)
## - Fast lexical analysis without heavy AST dependencies
##
## Usage: prism <file_path> [max_chunk_size]
## Output: JSON stream of chunks

import std/[os, json, strutils, streams]

const
  DEFAULT_MAX_CHUNK_SIZE = 2000 # Characters

type
  ChunkType = enum
    ctFunction = "function"
    ctClass = "class"
    ctBlock = "block"
    ctUnknown = "unknown"

  Chunk = object
    content: string
    start_line: int
    end_line: int
    kind: ChunkType
    name: string

  LanguageStyle = enum
    lsIndent # Python, Nim, YAML
    lsBrace  # C, Java, JS, Rust, Go

proc detectStyle(ext: string): LanguageStyle =
  case ext.toLowerAscii()
  of ".py", ".nim", ".yaml", ".yml", ".coffee":
    return lsIndent
  else:
    return lsBrace

# --- Indentation Based Parser (Python) ---

proc parseIndent(content: string, maxChunk: int): seq[Chunk] =
  result = @[]
  let lines = content.splitLines()
  
  var buffer = ""
  var chunkStart = 1
  var currentKind = ctUnknown
  var currentName = ""
  
  for i, line in lines:
    let lineNum = i + 1
    let trimmed = line.strip()
    
    if trimmed.len == 0:
      buffer.add("\n")
      continue
      
    # Top-level definition detection (starts at col 0)
    if not line.startsWith(" ") and not line.startsWith("\t") and not line.startsWith("#"):
      # If we have accumulated content, save previous chunk
      if buffer.strip().len > 0:
        result.add(Chunk(
            content: buffer, 
            start_line: chunkStart, 
            end_line: lineNum - 1, 
            kind: if currentKind != ctUnknown: currentKind else: ctBlock, 
            name: currentName
        ))
        buffer = ""
        chunkStart = lineNum
        currentKind = ctUnknown
        currentName = ""
        
      # Detect new chunk type
      if trimmed.startsWith("def "):
        currentKind = ctFunction
        currentName = trimmed.split(" ")[1].split("(")[0]
      elif trimmed.startsWith("class "):
        currentKind = ctClass
        currentName = trimmed.split(" ")[1].split("(")[0].split(":")[0]
      else:
        currentKind = ctBlock # Generic top level code
        
    buffer.add(line & "\n")
    
    # Force split if too big
    if buffer.len > maxChunk:
        result.add(Chunk(
            content: buffer,
            start_line: chunkStart,
            end_line: lineNum,
            kind: currentKind,
            name: currentName & " (part)"
        ))
        buffer = ""
        chunkStart = lineNum + 1

  # Add remaining buffer
  if buffer.strip().len > 0:
    result.add(Chunk(
        content: buffer,
        start_line: chunkStart,
        end_line: lines.len,
        kind: if currentKind != ctUnknown: currentKind else: ctBlock,
        name: currentName
    ))

# --- Brace Based Parser (C-like) ---

proc parseBrace(content: string, maxChunk: int): seq[Chunk] =
  result = @[]
  let lines = content.splitLines()
  var buffer = ""
  var braceLevel = 0
  var chunkStart = 1
  
  for i, line in lines:
    let lineNum = i + 1
    buffer.add(line & "\n")
    
    # Very basic brace counting (ignores strings/comments for speed/simplicity)
    # A robust parser would need a state machine, but this is 95% effective
    for c in line:
      if c == '{': inc braceLevel
      elif c == '}': dec braceLevel
    
    # If returned to level 0 (or less), we might have closed a block
    if braceLevel <= 0 and buffer.len > 100: # Only split substantial blocks
       result.add(Chunk(
           content: buffer,
           start_line: chunkStart,
           end_line: lineNum,
           kind: ctBlock,
           name: ""
       ))
       buffer = ""
       chunkStart = lineNum + 1
       braceLevel = 0 # Reset safety

    # Force split
    if buffer.len > maxChunk:
        result.add(Chunk(
            content: buffer,
            start_line: chunkStart,
            end_line: lineNum,
            kind: ctBlock,
            name: "split"
        ))
        buffer = ""
        chunkStart = lineNum + 1
        braceLevel = 0

  if buffer.len > 0:
    result.add(Chunk(content: buffer, start_line: chunkStart, end_line: lines.len, kind: ctBlock, name: ""))

proc toJson(c: Chunk): JsonNode =
  %* {
    "content": c.content,
    "start_line": c.start_line,
    "end_line": c.end_line,
    "kind": $c.kind,
    "name": c.name
  }

# --- Main ---

proc main() =
  let args = commandLineParams()
  if args.len < 1:
    quit("Usage: prism <file_path> [max_chunk_size]")
    
  let filePath = args[0]
  let maxSize = if args.len > 1: parseInt(args[1]) else: DEFAULT_MAX_CHUNK_SIZE
  
  if not fileExists(filePath):
    quit("File not found")
    
  let content = readFile(filePath)
  let ext = splitFile(filePath).ext
  let style = detectStyle(ext)
  
  var chunks: seq[Chunk]
  
  case style
  of lsIndent: chunks = parseIndent(content, maxSize)
  of lsBrace: chunks = parseBrace(content, maxSize)
  
  # Output JSON stream
  var jsonChunks = newJArray()
  for c in chunks:
    jsonChunks.add(c.toJson())
    
  echo $jsonChunks

when isMainModule:
  main()
