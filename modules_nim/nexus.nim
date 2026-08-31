## Aura Nexus - Static Dependency Graph Builder
## ============================================
##
## Scans source code to build a high-speed dependency graph.
## Currently optimized for Python imports.
##
## Usage: nexus <root_path> [output_file]
## Output: JSON Adjacency List

import std/[os, json, strutils, tables, sets, strformat, sequtils]

const
  # Only analyze Python for now (Phase 1 of Nexus)
  TARGET_EXTENSIONS = [".py"]
  
  IGNORE_DIRS = [
    ".git", "__pycache__", "venv", ".venv", "env", "node_modules",
    "dist", "build", ".idea", ".vscode", ".aura", "site-packages"
  ]

type
  DependencyType = enum
    dtDirect   # import x
    dtFrom     # from x import y
    dtRelative # from . import x

  ImportEntry = object
    source: string      # Source file
    target: string      # Imported module/file (inferred)
    raw: string         # Raw import string
    kind: DependencyType
    line: int

  Graph = object
    nodes: HashSet[string]           # Set of all files/modules
    edges: Table[string, seq[string]] # Adjacency list: File -> [Dependencies]
    inverse_edges: Table[string, seq[string]] # File -> [Consumers] (Who imports me?)

proc shouldIgnore(path: string): bool =
  let parts = path.split(DirSep)
  for part in parts:
    if part in IGNORE_DIRS or part.startsWith("."):
      return true
  return false

# --- Python Import Parser ---

proc resolvePythonImport(basePath, currentFile, importStr: string, level: int = 0): string =
  ## Attempts to resolve a Python import string to a filesystem path
  ## This is a heuristic approximation, not a full PYTHONPATH resolver.
  
  var target = importStr.replace(".", "/")
  let currentDir = splitFile(currentFile).dir
  
  # 1. Relative Import (level > 0)
  if level > 0:
    # Go up 'level' directories
    var searchDir = currentDir
    # from . import -> level 1 (current dir)
    # from .. import -> level 2 (parent dir)
    for i in 1 ..< level:
      searchDir = parentDir(searchDir)
      
    if target == "": # just "from . import x" -> target is empty initially
        return searchDir
    
    # Check if target is a file or dir in searchDir
    let candidateFile = searchDir / target & ".py"
    let candidateDir = searchDir / target
    
    if fileExists(candidateFile): return candidateFile
    if dirExists(candidateDir): return candidateDir
    return searchDir / target # Best guess
    
  # 2. Absolute Import (from project root)
  # Check relative to project root
  let rootCandidateFile = basePath / target & ".py"
  let rootCandidateDir = basePath / target
  
  if fileExists(rootCandidateFile): return rootCandidateFile
  if dirExists(rootCandidateDir): return rootCandidateDir
  
  # Return as module path if not found (likely external lib)
  return importStr

proc parsePythonImports(filePath, rootPath: string): seq[ImportEntry] =
  result = @[]
  var lines: seq[string]
  try:
    lines = readFile(filePath).splitLines()
  except:
    return

  for i, line in lines:
    let lineNum = i + 1
    let trimmed = line.strip()
    
    if trimmed.startsWith("#") or trimmed.len == 0: continue
    
    # Case 1: import x, y
    if trimmed.startsWith("import "):
      let parts = trimmed[7..^1].split(",")
      for part in parts:
        let modName = part.split(" as ")[0].strip()
        result.add(ImportEntry(
          source: filePath,
          target: resolvePythonImport(rootPath, filePath, modName),
          raw: modName,
          kind: dtDirect,
          line: lineNum
        ))
        
    # Case 2: from x import y
    elif trimmed.startsWith("from "):
      let parts = trimmed.split(" import ")
      if parts.len == 2:
        var moduleBase = parts[0][5..^1].strip()
        let importedItems = parts[1].strip()
        
        # Handle relative imports (dots)
        var level = 0
        while moduleBase.startsWith("."):
          level.inc
          moduleBase = moduleBase[1..^1]
        
        # Heuristic: Check if imported item is a submodule
        # Try resolving moduleBase/item
        # We take the first item if multiple (from x import y, z)
        let firstItem = importedItems.split(",")[0].strip().split(" as ")[0]
        
        # Potential paths to check
        # 1. moduleBase/firstItem (submodule)
        # 2. moduleBase (module containing item)
        
        var targetToResolve = moduleBase
        if moduleBase.len > 0 and firstItem.len > 0:
             targetToResolve = moduleBase & "." & firstItem
        elif moduleBase.len == 0 and firstItem.len > 0: # from . import y
             targetToResolve = firstItem

        let resolvedSub = resolvePythonImport(rootPath, filePath, targetToResolve, level)
        let resolvedBase = resolvePythonImport(rootPath, filePath, moduleBase, level)
        
        # If submodule resolves to a file, use it. Otherwise use base.
        # This discriminates "from os import path" (os.py) vs "from core import logic" (core/logic.py)
        var finalTarget = resolvedBase
        if resolvedSub.endsWith(".py") and fileExists(resolvedSub):
            finalTarget = resolvedSub
        elif dirExists(resolvedSub):
            finalTarget = resolvedSub
            
        result.add(ImportEntry(
          source: filePath,
          target: finalTarget,
          raw: if moduleBase.len > 0: moduleBase else: firstItem,
          kind: if level > 0: dtRelative else: dtFrom,
          line: lineNum
        ))

# --- Graph Builder ---

proc buildGraph(rootPath: string): Graph =
  result.nodes = initHashSet[string]()
  result.edges = initTable[string, seq[string]]()
  result.inverse_edges = initTable[string, seq[string]]()
  
  let absRoot = absolutePath(rootPath)
  # stderr.writeLine("Root: " & absRoot)
  
  for kind, path in walkDir(absRoot, relative=false):
    if shouldIgnore(path): continue
    
    if kind == pcDir:
      for p in walkDirRec(path, relative=false):
        if shouldIgnore(p): continue
        if splitFile(p).ext == ".py":
          # stderr.writeLine("Found: " & p)
          let relPath = relativePath(p, absRoot)
          result.nodes.incl(relPath)
          
          let imports = parsePythonImports(p, absRoot)
          
          if not result.edges.hasKey(relPath):
            result.edges[relPath] = @[]
            
          for imp in imports:
            # Normalize target path relative to root if possible
            var targetRel = imp.target
            if targetRel.startsWith(absRoot):
              targetRel = relativePath(targetRel, absRoot)
            
            # Check if target is internal (exists in our scan) or external
            # For simplicity, we store everything, filter later
            result.edges[relPath].add(targetRel)
            
            # Inverse graph (Dependents)
            if not result.inverse_edges.hasKey(targetRel):
              result.inverse_edges[targetRel] = @[]
            result.inverse_edges[targetRel].add(relPath)

    elif kind == pcFile and splitFile(path).ext == ".py":
        # Handle root level files
        let relPath = relativePath(path, absRoot)
        result.nodes.incl(relPath)
        let imports = parsePythonImports(path, absRoot)
        if not result.edges.hasKey(relPath): result.edges[relPath] = @[]
        for imp in imports:
            var targetRel = imp.target
            if targetRel.startsWith(absRoot): targetRel = relativePath(targetRel, absRoot)
            result.edges[relPath].add(targetRel)
            if not result.inverse_edges.hasKey(targetRel): result.inverse_edges[targetRel] = @[]
            result.inverse_edges[targetRel].add(relPath)

# --- Main ---

proc main() =
  let args = commandLineParams()
  if args.len < 1:
    quit("Usage: nexus <root_path>")
    
  let rootPath = args[0]
  
  if not dirExists(rootPath):
    quit("Directory not found")
    
  let graph = buildGraph(rootPath)
  
  # Convert sets to seq for JSON serialization
  let jsonNodes = %* graph.nodes.toSeq
  let jsonEdges = %* graph.edges
  let jsonInverse = %* graph.inverse_edges
  
  let output = %* {
    "root": rootPath,
    "total_files": graph.nodes.len,
    "nodes": jsonNodes,
    "dependencies": jsonEdges,
    "dependents": jsonInverse
  }
  
  echo $output

when isMainModule:
  main()
