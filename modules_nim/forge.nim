## Aura Forge - Code Quality Agent
## ================================
##
## Native code analysis + sanitation sandbox.
## Modes:
##   - "analyze": Static analysis (complexity, deadcode, style, duplicates, security)
##   - "sanitize": Legacy sandbox (py_compile + black + ruff)
##
## Usage: echo '{"mode":"analyze",...}' | forge
## Input: JSON via stdin
## Output: JSON to stdout

import std/[os, json, osproc, strutils, streams, tempfiles, tables, hashes, times, re, sequtils]

# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

type
  Severity = enum
    svLow = "low"
    svMedium = "medium"
    svHigh = "high"
    svCritical = "critical"

  Finding = object
    `type`: string
    file: string
    line: int
    rule: string
    name: string
    message: string
    severity: string
    complexity: int  # only for complexity findings

  AnalysisConfig = object
    checks: seq[string]
    complexityHigh: int
    lineLength: int
    maxArgs: int
    minDupLines: int

  FileInput = object
    path: string
    content: string

proc defaultConfig(): AnalysisConfig =
  result.checks = @["complexity", "deadcode", "style", "duplicates", "security"]
  result.complexityHigh = 10
  result.lineLength = 120
  result.maxArgs = 7
  result.minDupLines = 6

# ═══════════════════════════════════════════════════════════════
# Complexity Analyzer
# ═══════════════════════════════════════════════════════════════

proc analyzeComplexity(content: string, path: string, config: AnalysisConfig): seq[Finding] =
  let lines = content.splitLines()
  var currentFunc = ""
  var funcLine = 0
  var funcIndent = -1
  var complexity = 0
  var findings: seq[Finding] = @[]

  for i, rawLine in lines:
    let line = rawLine
    let stripped = line.strip()
    if stripped.len == 0 or stripped.startsWith("#"):
      continue

    let indent = line.len - line.strip(leading = true, trailing = false).len

    if stripped.startsWith("def ") or stripped.startsWith("async def "):
      # Flush previous function
      if currentFunc.len > 0 and complexity > 0:
        let sev = if complexity > config.complexityHigh: "high"
                  elif complexity > 5: "medium"
                  else: "low"
        findings.add(Finding(
          `type`: "complexity", file: path, line: funcLine,
          rule: "cyclomatic_complexity", name: currentFunc,
          message: currentFunc & " has complexity " & $complexity,
          severity: sev, complexity: complexity
        ))
      let nameStart = if stripped.startsWith("async "): 10 else: 4
      let parenPos = stripped.find('(', nameStart)
      currentFunc = if parenPos > nameStart: stripped[nameStart ..< parenPos] else: stripped[nameStart .. ^1]
      funcLine = i + 1
      funcIndent = indent
      complexity = 1
      continue

    if funcIndent >= 0 and indent <= funcIndent and not stripped.startsWith("@"):
      if currentFunc.len > 0 and not stripped.startsWith("def ") and not stripped.startsWith("class "):
        let sev = if complexity > config.complexityHigh: "high"
                  elif complexity > 5: "medium"
                  else: "low"
        findings.add(Finding(
          `type`: "complexity", file: path, line: funcLine,
          rule: "cyclomatic_complexity", name: currentFunc,
          message: currentFunc & " has complexity " & $complexity,
          severity: sev, complexity: complexity
        ))
        currentFunc = ""
        funcIndent = -1

    if currentFunc.len > 0:
      if stripped.startsWith("if ") or stripped.startsWith("elif "): inc complexity
      elif stripped.startsWith("for ") or stripped.startsWith("while "): inc complexity
      elif stripped.startsWith("except") or stripped.startsWith("except "): inc complexity
      elif stripped.startsWith("assert "): inc complexity
      complexity += stripped.count(" and ") + stripped.count(" or ")

  # Flush last function
  if currentFunc.len > 0 and complexity > 0:
    let sev = if complexity > config.complexityHigh: "high"
              elif complexity > 5: "medium"
              else: "low"
    findings.add(Finding(
      `type`: "complexity", file: path, line: funcLine,
      rule: "cyclomatic_complexity", name: currentFunc,
      message: currentFunc & " has complexity " & $complexity,
      severity: sev, complexity: complexity
    ))

  return findings

# ═══════════════════════════════════════════════════════════════
# Dead Code Detector
# ═══════════════════════════════════════════════════════════════

proc detectDeadCode(content: string, path: string, config: AnalysisConfig): seq[Finding] =
  let lines = content.splitLines()
  var imports: seq[tuple[name: string, line: int]] = @[]
  var allNames: string = ""

  # Phase 1: collect imports
  for i, rawLine in lines:
    let line = rawLine.strip()
    if line.startsWith("import "):
      let parts = line[7..^1].split(",")
      for p in parts:
        let name = p.strip().split(" as ")
        let importName = if name.len > 1: name[1].strip() else: name[0].strip().split(".")[^1]
        if importName.len > 0:
          imports.add((importName, i + 1))
    elif line.startsWith("from ") and " import " in line:
      let importPart = line.split(" import ")[1]
      let parts = importPart.split(",")
      for p in parts:
        let name = p.strip().split(" as ")
        let importName = if name.len > 1: name[1].strip() else: name[0].strip()
        if importName.len > 0 and importName != "*":
          imports.add((importName, i + 1))

  # Phase 2: build text of all non-import lines for name searching
  for i, line in lines:
    let stripped = line.strip()
    if not stripped.startsWith("import ") and not (stripped.startsWith("from ") and " import " in stripped):
      allNames.add(stripped & "\n")

  # Phase 3: check which imports are unused
  for imp in imports:
    if imp.name.startsWith("_"):
      continue
    # Word boundary check
    let pattern = re(r"\b" & imp.name.escapeRe() & r"\b")
    if not allNames.contains(pattern):
      result.add(Finding(
        `type`: "dead_code", file: path, line: imp.line,
        rule: "unused_import", name: imp.name,
        message: "Unused import: " & imp.name,
        severity: "medium"
      ))

  # Phase 4: unreachable code
  var prevTerminator = false
  var prevIndent = -1
  for i, rawLine in lines:
    let stripped = rawLine.strip()
    if stripped.len == 0 or stripped.startsWith("#"):
      continue
    let indent = rawLine.len - rawLine.strip(chars = {' '}).len

    if prevTerminator and indent >= prevIndent and stripped.len > 0:
      if not stripped.startsWith("elif ") and not stripped.startsWith("else:") and
         not stripped.startsWith("except") and not stripped.startsWith("finally:"):
        result.add(Finding(
          `type`: "dead_code", file: path, line: i + 1,
          rule: "unreachable", name: "",
          message: "Unreachable code after terminator",
          severity: "low"
        ))
        prevTerminator = false

    if stripped.startsWith("return") or stripped.startsWith("raise ") or
       stripped == "break" or stripped == "continue":
      prevTerminator = true
      prevIndent = indent
    else:
      prevTerminator = false

# ═══════════════════════════════════════════════════════════════
# Style Checker
# ═══════════════════════════════════════════════════════════════

proc isSnakeCase(s: string): bool =
  for c in s:
    if c.isUpperAscii() and c != '_': return false
  return true

proc isPascalCase(s: string): bool =
  if s.len == 0: return false
  return s[0].isUpperAscii()

proc checkStyle(content: string, path: string, config: AnalysisConfig): seq[Finding] =
  let lines = content.splitLines()

  for i, rawLine in lines:
    let stripped = rawLine.strip()

    # Line length
    if rawLine.len > config.lineLength:
      result.add(Finding(
        `type`: "style", file: path, line: i + 1,
        rule: "line_length", name: "",
        message: "Line too long (" & $rawLine.len & " > " & $config.lineLength & ")",
        severity: "low"
      ))

    # Function naming
    if stripped.startsWith("def ") or stripped.startsWith("async def "):
      let nameStart = if stripped.startsWith("async "): 10 else: 4
      let parenPos = stripped.find('(', nameStart)
      if parenPos > nameStart:
        let funcName = stripped[nameStart ..< parenPos]
        if not funcName.startsWith("__") and not isSnakeCase(funcName):
          result.add(Finding(
            `type`: "style", file: path, line: i + 1,
            rule: "function_naming", name: funcName,
            message: "Function '" & funcName & "' is not snake_case",
            severity: "low"
          ))

        # Too many arguments
        let argsStr = stripped[parenPos + 1 .. ^1]
        let closeParen = argsStr.find(')')
        if closeParen > 0:
          let args = argsStr[0 ..< closeParen]
          let argCount = args.count(',') + (if args.strip().len > 0: 1 else: 0)
          # Subtract 'self' and 'cls'
          let adjusted = argCount - (if "self" in args: 1 else: 0) - (if "cls" in args: 1 else: 0)
          if adjusted > config.maxArgs:
            result.add(Finding(
              `type`: "style", file: path, line: i + 1,
              rule: "too_many_args", name: funcName,
              message: "Function '" & funcName & "' has " & $adjusted & " args (max " & $config.maxArgs & ")",
              severity: "low"
            ))

    # Class naming
    if stripped.startsWith("class "):
      let nameEnd = stripped.find({'(', ':'}, 6)
      let className = if nameEnd > 6: stripped[6 ..< nameEnd] else: stripped[6 .. ^1].strip(chars = {':'})
      if className.len > 0 and not isPascalCase(className):
        result.add(Finding(
          `type`: "style", file: path, line: i + 1,
          rule: "class_naming", name: className,
          message: "Class '" & className & "' is not PascalCase",
          severity: "low"
        ))

# ═══════════════════════════════════════════════════════════════
# Duplicate Detector
# ═══════════════════════════════════════════════════════════════

proc fnvHash(s: string): uint64 =
  ## FNV-1a hash for fast string hashing
  result = 14695981039346656037'u64
  for c in s:
    result = result xor uint64(c.ord)
    result = result * 1099511628211'u64

proc detectDuplicates(content: string, path: string, config: AnalysisConfig): seq[Finding] =
  let lines = content.splitLines()
  let minLines = config.minDupLines
  if lines.len < minLines * 2:
    return @[]

  # Normalize lines (strip whitespace, skip blanks/comments)
  var normalized: seq[tuple[text: string, origLine: int]] = @[]
  for i, line in lines:
    let s = line.strip()
    if s.len > 0 and not s.startsWith("#"):
      normalized.add((s, i + 1))

  if normalized.len < minLines * 2:
    return @[]

  # Sliding window hashing
  var hashMap = initTable[uint64, seq[int]]()  # hash -> list of start indices

  for i in 0 .. normalized.len - minLines:
    var blockText = ""
    for j in 0 ..< minLines:
      blockText.add(normalized[i + j].text & "\n")
    let h = fnvHash(blockText)
    if h notin hashMap:
      hashMap[h] = @[]
    hashMap[h].add(i)

  # Report duplicates
  var reported = initTable[uint64, bool]()
  for h, positions in hashMap:
    if positions.len > 1 and h notin reported:
      reported[h] = true
      let lineA = normalized[positions[0]].origLine
      let lineB = normalized[positions[1]].origLine
      result.add(Finding(
        `type`: "duplicate", file: path, line: lineA,
        rule: "duplicate_block", name: "",
        message: "Duplicate block (" & $minLines & " lines) also at line " & $lineB,
        severity: "medium"
      ))

# ═══════════════════════════════════════════════════════════════
# Security Scanner
# ═══════════════════════════════════════════════════════════════

proc scanSecurity(content: string, path: string, config: AnalysisConfig): seq[Finding] =
  let lines = content.splitLines()
  
  let secretPats = @[
    ("(?i)(password|passwd|pwd)\\s*=\\s*['\"][^'\"]+['\"]", "hardcoded_secret", "critical"),
    ("(?i)(api_key|apikey|api_secret)\\s*=\\s*['\"][^'\"]+['\"]", "hardcoded_secret", "critical"),
    ("(?i)(secret|token|auth)\\s*=\\s*['\"][^'\"]+['\"]", "hardcoded_secret", "high"),
    ("(?i)(access_key|private_key)\\s*=\\s*['\"][^'\"]+['\"]", "hardcoded_secret", "critical"),
  ]
  
  let unsafePats = @[
    ("\\beval\\s*\\(", "unsafe_eval", "high"),
    ("\\bexec\\s*\\(", "unsafe_exec", "high"),
    ("shell\\s*=\\s*True", "shell_injection", "high"),
    ("http://(?!localhost|127\\.0\\.0\\.1)", "insecure_http", "medium"),
  ]

  for i, rawLine in lines:
    let line = rawLine.strip()
    if line.startsWith("#"):
      continue

    for (pat, rule, sev) in secretPats:
      if line.contains(re(pat)):
        result.add(Finding(
          `type`: "security", file: path, line: i + 1,
          rule: rule, name: "",
          message: "Potential " & rule & " detected",
          severity: sev
        ))
        break

    for (pat, rule, sev) in unsafePats:
      if line.contains(re(pat)):
        result.add(Finding(
          `type`: "security", file: path, line: i + 1,
          rule: rule, name: "",
          message: "Security risk: " & rule,
          severity: sev
        ))

# ═══════════════════════════════════════════════════════════════
# Legacy Sanitize Mode (preserved)
# ═══════════════════════════════════════════════════════════════

proc runTool(cmd: string, args: seq[string], workingDir: string): tuple[exitCode: int, output: string] =
  let p = startProcess(cmd, workingDir = workingDir, args = args, options = {poUsePath, poStdErrToStdOut})
  let output = p.outputStream.readAll()
  let exitCode = p.waitForExit()
  p.close()
  result = (exitCode, output.strip())

proc handleSanitize(code: string, language: string, fix: bool): JsonNode =
  var success = true
  var errors: seq[string] = @[]
  var logs: seq[string] = @[]
  var outputCode = code

  if language.toLowerAscii() notin ["python", "py"]:
    return %*{"success": false, "code": code, "errors": ["Unsupported language: " & language]}

  let tmpDir = createTempDir("aura_forge_", "")
  let tmpFile = tmpDir / "sandbox.py"

  try:
    writeFile(tmpFile, code)

    let (syntaxCode, syntaxOut) = runTool("python3", @["-m", "py_compile", "sandbox.py"], tmpDir)
    if syntaxCode != 0:
      return %*{"success": false, "code": code, "errors": ["Syntax Error:\n" & syntaxOut]}

    if fix:
      # Formatters are optional runtime helpers. Their absence must not turn a
      # valid sanitize request into a failed forge operation.
      let black = findExe("black")
      if black.len > 0:
        discard runTool(black, @["-q", "sandbox.py"], tmpDir)
        logs.add("Formatted with Black")
      else:
        logs.add("Black not available; skipped formatting")

      let ruff = findExe("ruff")
      if ruff.len > 0:
        let (_, lintOut) = runTool(ruff, @["check", "--fix", "--select", "E,F,W,I", "sandbox.py"], tmpDir)
        if lintOut.len > 0:
          logs.add("Ruff: " & lintOut)
      else:
        logs.add("Ruff not available; skipped linting")

    outputCode = readFile(tmpFile)
  except Exception as e:
    success = false
    errors.add("Forge Error: " & e.msg)
  finally:
    removeDir(tmpDir)

  return %*{"success": success, "code": outputCode, "errors": errors, "logs": logs}

# ═══════════════════════════════════════════════════════════════
# Main — Mode Dispatcher
# ═══════════════════════════════════════════════════════════════

proc main() =
  var inputStr = ""
  if paramCount() > 0:
    let arg = paramStr(1)
    if arg == "--version":
      echo "forge 2.0.0"
      quit(0)
    if fileExists(arg):
      inputStr = readFile(arg)
    else:
      inputStr = arg
  else:
    inputStr = readAll(stdin)

  if inputStr.len == 0:
    echo $(%*{"success": false, "errors": ["No input"]})
    quit(1)

  try:
    let json = parseJson(inputStr)
    let mode = json{"mode"}.getStr("sanitize")

    case mode
    of "analyze":
      # New analysis mode
      var config = defaultConfig()
      if json.hasKey("config"):
        let c = json["config"]
        if c.hasKey("checks"):
          config.checks = @[]
          for item in c["checks"]:
            config.checks.add(item.getStr())
        if c.hasKey("thresholds"):
          let t = c["thresholds"]
          config.complexityHigh = t{"complexity_high"}.getInt(10)
          config.lineLength = t{"line_length"}.getInt(120)
          config.maxArgs = t{"max_args"}.getInt(7)
          config.minDupLines = t{"min_dup_lines"}.getInt(6)

      var allFindings: seq[Finding] = @[]
      var filesAnalyzed = 0
      let startTime = cpuTime()

      for fileNode in json["files"]:
        let path = fileNode["path"].getStr()
        let content = fileNode["content"].getStr()
        inc filesAnalyzed

        if "complexity" in config.checks:
          allFindings.add(analyzeComplexity(content, path, config))
        if "deadcode" in config.checks:
          allFindings.add(detectDeadCode(content, path, config))
        if "style" in config.checks:
          allFindings.add(checkStyle(content, path, config))
        if "duplicates" in config.checks:
          allFindings.add(detectDuplicates(content, path, config))
        if "security" in config.checks:
          allFindings.add(scanSecurity(content, path, config))

      let durationMs = int((cpuTime() - startTime) * 1000)

      # Build output JSON
      var findingsJson = newJArray()
      for f in allFindings:
        var fj = %*{
          "type": f.`type`,
          "file": f.file,
          "line": f.line,
          "rule": f.rule,
          "name": f.name,
          "message": f.message,
          "severity": f.severity
        }
        if f.complexity > 0:
          fj["complexity"] = %f.complexity
        findingsJson.add(fj)

      echo $(%*{
        "success": true,
        "findings": findingsJson,
        "stats": {
          "files_analyzed": filesAnalyzed,
          "total_findings": allFindings.len,
          "duration_ms": durationMs
        }
      })

    of "sanitize":
      # Legacy mode (backward compatible)
      let code = json["code"].getStr()
      let language = json{"language"}.getStr("python")
      let fix = json{"fix"}.getBool(true)
      echo $handleSanitize(code, language, fix)

    else:
      echo $(%*{"success": false, "errors": ["Unknown mode: " & mode]})

  except JsonParsingError:
    echo $(%*{"success": false, "errors": ["Invalid JSON"]})
  except Exception as e:
    echo $(%*{"success": false, "errors": ["Error: " & e.msg]})

when isMainModule:
  main()
