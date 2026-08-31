# 🛠️ Complete Tools Guide - Aura CLI

Aura CLI provides an extensible catalog of integrated tools organized into categories. This guide documents representative public interfaces and usage patterns; the runtime `/tools` command is authoritative for the active catalog.

Tool output is consistently spaced before and after the model response. On failure, the message is brief and suggests `/retry`. Long outputs can be expanded (default: `⋯ N lines [e] expand`). File-operation summaries appear **after** the model response and, when there are many operations, in compact format.

---

## 📊 Tools Overview

| Category | Scope | Description |
|----------|-------|-------------|
| **File System** | Core | File operations (read, write, list, etc.) |
| **Development** | Core | Code analysis, editing, validation |
| **Shell** | Core | Bounded shell command execution |
| **Web** | Optional/provider-dependent | Web search and HTTP operations |
| **Git** | Core/optional | Git operations, subject to local repository state |
| **Docker** | Optional | Docker container management when available |
| **Monitoring** | Optional | System and service monitoring when available |
| **Infrastructure** | Optional | Infrastructure management when configured |
| **Database** | Optional | Database operations when drivers/services exist |
| **Security** | Core/optional | Security auditing and scanning |
| **CI/CD** | Core/optional | Continuous integration/deployment |
| **Testing** | Core | Test discovery and execution |
| **Codebase** | Core | Codebase analysis and search |
| **Runtime catalog** | Dynamic | Use `/tools` to inspect the active registry |

---

## 📁 File System Tools

### `read_file`

Read file contents with optional pagination.

**Parameters:**
- `path` (str, required): File path to read
- `offset` (int, optional): Line offset to start reading
- `limit` (int, optional): Maximum lines to read

**Example:**
```
› Read the file src/main.py
› Read lines 10-20 from config.json
```

**Returns:** File contents as string

---

### `write_file`

Write content to a file with confirmation.

**Parameters:**
- `path` (str, required): File path to write
- `content` (str, required): Content to write

**Example:**
```
› Write "Hello, World!" to output.txt
› Create a new file test.py with Python code
```

**Returns:** Success status (bool)

---

### `list_directory`

List directory contents with optional recursion.

**Parameters:**
- `path` (str, required): Directory path
- `recursive` (bool, optional): List recursively

**Example:**
```
› List files in the current directory
› Show all Python files in src/ recursively
```

**Returns:** List of file/directory information

---

### `find_files`

Find files by pattern.

**Parameters:**
- `pattern` (str, required): File pattern (glob)
- `path` (str, optional): Base path to search

**Example:**
```
› Find all .py files
› Find test_*.py files in tests/
```

**Returns:** List of matching file paths

---

### `backup_file`

Create a backup of a file.

**Parameters:**
- `path` (str, required): File to backup

**Example:**
```
› Backup config.json
› Create backup of main.py before editing
```

**Returns:** Backup file path

---

### `restore_backup`

Restore a file from backup.

**Parameters:**
- `path` (str, required): Original file path
- `backup_path` (str, optional): Specific backup to restore

**Example:**
```
› Restore config.json from backup
› Restore the latest backup of main.py
```

**Returns:** Success status

---

### `edit_file`

Edit file with various operations.

**Parameters:**
- `path` (str, required): File to edit
- `operation` (str, required): Operation type
- Additional operation-specific parameters

**Operations:**
- `insert`: Insert content at position
- `replace`: Replace content
- `delete`: Delete lines
- `append`: Append content

**Example:**
```
› Edit main.py: insert "import os" at line 5
› Replace "old_function" with "new_function" in utils.py
```

**Returns:** Success status

---

### `tree_view`

Generate a tree view of directory structure.

**Parameters:**
- `path` (str, required): Root directory
- `max_depth` (int, optional): Maximum depth

**Example:**
```
› Show tree view of the project
› Display directory structure up to 3 levels deep
```

**Returns:** Tree structure as string

---

## 💻 Development Tools

### `analyze_code`

Perform static code analysis.

**Parameters:**
- `path` (str, required): File or directory to analyze

**Example:**
```
› Analyze the code in src/main.py
› Analyze the entire project structure
```

**Returns:** Analysis results (dict)

---

### `analyze_code_nlp`

NLP-based code analysis.

**Parameters:**
- `path` (str, required): Code to analyze

**Example:**
```
› Analyze code quality using NLP
› Get semantic insights about this code
```

**Returns:** NLP analysis results

---

### `validate_syntax`

Validate code syntax.

**Parameters:**
- `path` (str, required): File to validate

**Example:**
```
› Check if main.py has syntax errors
› Validate all Python files in src/
```

**Returns:** Validation results

---

### `find_in_files`

Search for text in files.

**Parameters:**
- `query` (str, required): Text to search
- `path` (str, optional): Directory to search
- `file_pattern` (str, optional): File pattern filter

**Example:**
```
› Find all occurrences of "TODO" in the codebase
› Search for "def main" in Python files
```

**Returns:** List of matches with locations

---

### `find_duplicate_code`

Find duplicate code patterns.

**Parameters:**
- `path` (str, required): Directory to analyze

**Example:**
```
› Find duplicate code in the project
› Detect code duplication in src/
```

**Returns:** List of duplicate code blocks

---

### `classify_code`

Classify code by type/pattern.

**Parameters:**
- `path` (str, required): Code to classify

**Example:**
```
› Classify the code in utils.py
› Identify code patterns in this file
```

**Returns:** Classification results

---

### `summarize_code`

Generate code summary.

**Parameters:**
- `path` (str, required): Code to summarize

**Example:**
```
› Summarize the functionality of main.py
› Create a summary of this module
```

**Returns:** Code summary

---

### `tokenize_code`

Tokenize code for analysis.

**Parameters:**
- `path` (str, required): Code to tokenize

**Example:**
```
› Tokenize the code in parser.py
› Analyze code tokens
```

**Returns:** Tokenization results

---

### `generate_tests_ml`

Generate tests using ML.

**Parameters:**
- `path` (str, required): Code to test
- `test_type` (str, optional): Type of tests

**Example:**
```
› Generate tests for main.py
› Create unit tests for this module
```

**Returns:** Generated test code

---

### `semantic_search_advanced`

Advanced semantic code search.

**Parameters:**
- `query` (str, required): Semantic query
- `path` (str, optional): Search scope

**Example:**
```
› Find code related to user authentication
› Search for error handling patterns
```

**Returns:** Semantic search results

---

## 🔧 Shell Tools

### `run_shell_command`

Execute shell commands with visual preview and confirmation.

**Parameters:**
- `command` (str, required): Shell command
- `background` (bool, optional): Run in background

**Behavior:**
- Shows a **warning banner** with the command to be executed.
- Requires explicit confirmation by default (`Executar?`). Auto-run can skip the prompt only where the current policy permits it; unavailable policy/confirmation fails closed.
- Applies the same safety policy in direct and agent paths. Dangerous commands and unsupported shell composition such as unquoted `&&`/`||` are rejected while the runner remains `shell=False`.
- Runs foreground work through the bounded supervisor with an absolute timeout, isolated process group, captured stdout/stderr and exact per-stream output limit.
- Runs background work through the registry supervisor with PID, owner when available, timestamps, status, cancellation and reaping. Session shutdown cancels remaining live processes.
- Uses the canonical allowed workspace as cwd; paths outside the workspace are rejected by workspace-scoped file tools.

**Example:**
```
› Run: ls -la
› Execute: python test.py
› Run git status in the project root
```

**Returns:** Rich shell box with status, output, exit code and execution time. A non-zero exit code is not converted into success.

---

### `execute_shell_command`

Execute shell command with options.

**Parameters:**
- `command` (str, required): Command to execute
- `timeout` (int, optional): Timeout in seconds
- `cwd` (str, optional): Working directory, constrained to the canonical workspace

**Returns:** Execution result with stdout, stderr, exit code and timeout status. The command is executed without `shell=True`.

---

### `should_execute_directly`

Determine if a command should be executed directly (i.e., without going through the LLM).

**Parameters:**
- `command` (str, required): Command to check

**Returns:** Boolean

---

## 🌐 Web Tools (3 tools)

### `web_search`

Search the web for information.

**Parameters:**
- `query` (str, required): Search query
- `limit` (int, optional): Maximum results

**Example:**
```
› Search the web for "Python async best practices"
› Find information about FastAPI authentication
```

**Returns:** Search results

---

## 🔀 Git Tools (7 tools)

### `git_status`

Get Git repository status.

**Parameters:**
- `path` (str, optional): Repository path

**Example:**
```
› /ops git status
› Check git status of the project
```

**Returns:** Git status information

---

### `git_diff`

Show Git differences.

**Parameters:**
- `ref1` (str, optional): First reference
- `ref2` (str, optional): Second reference

**Example:**
```
› /ops git diff
› Show differences between main and feature branch
```

**Returns:** Diff output

---

### `git_diff_context`

Return the authoritative workspace snapshot used by Aura Ops. It combines
branch/status information, tracked and staged changes, and readable untracked
files as new-file patches. The result is bounded and marks truncation when the
workspace is larger than the prompt budget.

**Parameters:**
- `path` (str, optional): Project root to inspect
- `max_chars` (int, optional): Maximum rendered diff size

**Example:**
```
› /ops git diff context
› Inspect the complete current workspace diff before editing
```

**Returns:** Status, changed paths, and a unified patch snapshot

The same snapshot can be rendered by the Rich `WorkspaceDiffDisplay` or the
Textual `WorkspaceDiffPanel`; both preserve the native Aura diff colors and
truncation state.

---

### `git_log`

Show Git commit history.

**Parameters:**
- `limit` (int, optional): Number of commits

**Example:**
```
› /ops git log
› Show last 10 commits
```

**Returns:** Commit history

---

### `git_branch`

Manage Git branches.

**Parameters:**
- `action` (str, required): Action (create, list, delete, etc.)
- `name` (str, optional): Branch name

**Example:**
```
› /ops git branch create feature/new-api
› List all branches
```

**Returns:** Branch information

---

### `git_commit`

Create a Git commit.

**Parameters:**
- `message` (str, required): Commit message
- `files` (list, optional): Files to commit

**Example:**
```
› /ops git commit "Add new feature"
› Commit all changes with message
```

**Returns:** Commit result

---

### `git_commit_smart`

Smart commit with automatic message generation.

**Parameters:**
- `files` (list, optional): Files to commit

**Example:**
```
› /ops git commit smart
› Create smart commit for staged files
```

**Returns:** Commit result with generated message

---

### `git_smart`

Natural language Git operations.

**Parameters:**
- `command` (str, required): Natural language command

**Example:**
```
› /ops git smart "create a new branch for the API feature"
› /ops git smart "show me what changed in the last commit"
```

**Returns:** Operation result

---

## 🐳 Docker Tools (6 tools)

### `docker_ps`

List Docker containers.

**Parameters:**
- `all` (bool, optional): Include stopped containers

**Example:**
```
› /ops docker ps
› List all Docker containers including stopped ones
```

**Returns:** Container list

---

### `docker_images`

List Docker images.

**Example:**
```
› /ops docker images
› Show all Docker images
```

**Returns:** Image list

---

### `docker_logs`

Get container logs.

**Parameters:**
- `container` (str, required): Container name/ID
- `tail` (int, optional): Number of lines

**Example:**
```
› /ops docker logs my-container
› Show last 100 lines of container logs
```

**Returns:** Log output

---

### `docker_exec`

Execute command in container.

**Parameters:**
- `container` (str, required): Container name/ID
- `command` (str, required): Command to execute

**Example:**
```
› /ops docker exec my-container "ls -la"
› Run bash in the container
```

**Returns:** Command output

---

### `docker_build`

Build Docker image.

**Parameters:**
- `path` (str, required): Build context path
- `tag` (str, required): Image tag

**Example:**
```
› /ops docker build . my-app:latest
› Build Docker image from current directory
```

**Returns:** Build result

---

### `docker_compose`

Docker Compose operations.

**Parameters:**
- `action` (str, required): Action (up, down, restart, etc.)
- `file` (str, optional): Compose file path

**Example:**
```
› /ops docker compose up
› Restart all services in docker-compose.yml
```

**Returns:** Operation result

---

## 📊 Monitoring Tools (4 tools)

### `check_service_health`

Check service health status.

**Parameters:**
- `service` (str, optional): Service name
- `url` (str, optional): Service URL

**Example:**
```
› /ops check health
› Check health of API service at http://localhost:8000
```

**Returns:** Health status

---

### `check_port`

Check if port is open.

**Parameters:**
- `port` (int, required): Port number
- `host` (str, optional): Host address

**Example:**
```
› /ops check port 8000
› Check if port 5432 is open on localhost
```

**Returns:** Port status

---

### `system_resources`

Get system resource usage.

**Example:**
```
› /ops system resources
› Show CPU and memory usage
```

**Returns:** Resource information

---

### `process_info`

Get process information.

**Parameters:**
- `process_name` (str, optional): Process name

**Example:**
```
› /ops process info python
› Show information about Python processes
```

**Returns:** Process information

---

## 🏗️ Infrastructure Tools (8 tools)

See [API Reference](../reference/api.md) for implementation details.

---

## 🗄️ Database Tools (5 tools)

See [API Reference](../reference/api.md) for implementation details.

---

## 🔒 Security Tools (5 tools)

See [API Reference](../reference/api.md) for implementation details.

---

## 🔄 CI/CD Tools (4 tools)

See [API Reference](../reference/api.md) for implementation details.

---

## 🧪 Testing Tools (6 tools)

### Test Discovery and Execution

See [Testing Guide](../developer-guides/testing.md) for complete testing documentation.

---

## 🔍 Codebase Tools (10+ tools)

### `codebase_search`

Search codebase semantically.

**Parameters:**
- `query` (str, required): Search query
- `path` (str, optional): Search scope

**Example:**
```
› Search codebase for authentication logic
› Find all error handling patterns
```

**Returns:** Search results

---

### `view_repo_map`

View repository structure map.

**Parameters:**
- `path` (str, optional): Repository path

**Example:**
```
› Show repository map
› Display project structure
```

**Returns:** Repository map

---

### `view_subdirectory`

View subdirectory details.

**Parameters:**
- `path` (str, required): Directory path

**Example:**
```
› Show details of src/ directory
› View contents of tests/ directory
```

**Returns:** Directory details

---

### `glob_search`

Search files using glob patterns.

**Parameters:**
- `pattern` (str, required): Glob pattern
- `path` (str, optional): Base path

**Example:**
```
› Find all test_*.py files
› Search for *.json files in config/
```

**Returns:** Matching files

---

### `advanced_grep_search`

Advanced grep search with options.

**Parameters:**
- `pattern` (str, required): Search pattern
- `path` (str, optional): Search scope
- `options` (dict, optional): Grep options

**Example:**
```
› Search for "class.*Agent" in Python files
› Find all TODO comments
```

**Returns:** Search results

---

### `investigate_codebase`

Deep codebase investigation.

**Parameters:**
- `path` (str, optional): Codebase path
- `depth` (int, optional): Investigation depth

**Example:**
```
› Investigate the codebase structure
› Deep dive into src/ directory
```

**Returns:** Investigation results

---

### `investigate_codebase_deep`

Very deep codebase analysis.

**Parameters:**
- `path` (str, optional): Codebase path

**Example:**
```
› Perform deep codebase investigation
› Analyze entire project structure
```

**Returns:** Deep analysis results

---

### `get_code_insights`

Get code insights and metrics.

**Parameters:**
- `path` (str, required): Code path

**Example:**
```
› Get insights about main.py
› Analyze code quality metrics
```

**Returns:** Code insights

---

### `analyze_python_ast`

Analyze Python AST.

**Parameters:**
- `path` (str, required): Python file path

**Example:**
```
› Analyze AST of parser.py
› Get AST structure of this file
```

**Returns:** AST analysis

---

### `quick_scan_with_imagination`

Quick scan using imagination system.

**Parameters:**
- `path` (str, optional): Scan path

**Example:**
```
› Quick scan the project
› Scan current directory
```

**Returns:** Scan results

---

## 🎯 Using Tools

### Via Chat

Simply describe what you want:

```
› Read the file config.json
› Analyze the code in src/main.py
› Find all Python files in the project
```

### Via AGI Agent

```
› /agi analyze my project and suggest improvements
```

The AGI agent will automatically select and use appropriate tools.

### Via Ops Agent

```
› /ops git status
› /ops docker ps
› /ops check health
```

### Direct Tool Reference

```
› /tool read_file
› /tool analyze_code
```

---

## 📚 Tool Categories Reference

### File System (8 tools)
- `read_file`, `write_file`, `list_directory`, `find_files`
- `backup_file`, `restore_backup`, `edit_file`, `tree_view`

### Development (12 tools)
- `analyze_code`, `analyze_code_nlp`, `validate_syntax`, `find_in_files`
- `find_duplicate_code`, `classify_code`, `summarize_code`, `tokenize_code`
- `generate_tests_ml`, `semantic_search_advanced`

### Shell (5 tools)
- `run_shell_command`, `is_shell_command`, `extract_shell_command`
- `execute_shell_command`, `should_execute_directly`

### Web (3 tools)
- `web_search`

### Git (7 tools)
- `git_status`, `git_diff`, `git_diff_context`, `git_log`, `git_branch`
- `git_commit`, `git_commit_smart`, `git_smart`

### Docker (6 tools)
- `docker_ps`, `docker_images`, `docker_logs`
- `docker_exec`, `docker_build`, `docker_compose`

### Monitoring (4 tools)
- `check_service_health`, `check_port`
- `system_resources`, `process_info`

### Codebase (10+ tools)
- `codebase_search`, `view_repo_map`, `view_subdirectory`
- `glob_search`, `advanced_grep_search`, `investigate_codebase`
- `investigate_codebase_deep`, `get_code_insights`, `analyze_python_ast`
- `quick_scan_with_imagination`

---

## 💡 Best Practices

1. **Use Natural Language**: Describe what you want, Aura CLI will choose the right tool
2. **Be Specific**: Provide clear file paths and parameters
3. **Use AGI for Complex Tasks**: Let the agent orchestrate multiple tools
4. **Use Ops for DevOps**: Specialized tools for Git, Docker, monitoring
5. **Explore Tools**: Run `/tools` to discover capabilities

---

## 🔗 Related Documentation

- [API Reference](../reference/api.md) - Complete API documentation
- [Quick Start](./quick-start.md) - Getting started guide
- [Workers Guide](./workers.md) - How agents use tools

---

**Version**: 0.1.0
**Last Updated**: 2026

> Use `/tools` at runtime to inspect the active tool registry — the catalogue is extensible and the count may differ from this document.
