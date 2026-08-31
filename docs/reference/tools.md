# 🔧 Aura CLI — Tools Reference

The tool registry is extensible. Run `/tools` for the authoritative list of tools
available in your current session.

## Index

1. [File System Tools](#-file-system-tools-4)
2. [Codebase Search Tools](#-codebase-search-tools-4)
3. [Codebase Investigation Tools](#-codebase-investigation-tools-3)
4. [Memory Tools](#-memory-tools-5)
5. [Git Tools](#-git-tools-8)
6. [Natural Git Tools](#-natural-git-tools-2)
7. [Shell Tools](#-shell-tools-2)
8. [Web Tools](#-web-tools-1)
9. [Imagination Tools](#-imagination-tools-2)
10. [Docker Tools](#-docker-tools-6)
11. [System Tools](#-system-tools-4)
12. [Dev Tools](#-dev-tools-4)
13. [Task Management Tools](#-task-management-tools-5)
14. [Deep Analysis Tools](#-deep-analysis-tools-3)

---

## 📁 File System Tools (4)

### `read_file`
Read file contents with optional partial-read support.

```python
read_file(path: str, offset: int = 0, limit: int = -1) -> str
```

**Parameters:**
- `path`: File path
- `offset`: Linha inicial (0-indexed)
- `limit`: Number of lines (-1 = all)

**Exemplo:**
```python
content = read_file("main.py")
lines_10_20 = read_file("main.py", offset=10, limit=10)
```

---

### `write_file`
Write content to a file (with user confirmation).

```python
write_file(path: str, content: str, append: bool = False) -> str
```

**Parameters:**
- `path`: File path
- `content`: Content to write
- `append`: Se True, adiciona ao final

---

### `list_directory`
List directory contents with detailed information.

```python
list_directory(path: str = ".") -> str
```

---

### `find_directory`
Recursive directory search (up to 3 levels).

```python
find_directory(directory_name: str, start_path: str = ".") -> str
```

---

## 🔍 Codebase Search Tools (4)

### `codebase_search`
Intelligent codebase search (text, regex, functions/classes).

```python
codebase_search(
    query: str,
    path: str = ".",
    filters: Optional[Dict] = None,
    max_results: int = 50
) -> str
```

**Available filters:**
- `file_extensions`: List of extensions
- `exclude_dirs`: Directories to exclude
- `case_sensitive`: Case-sensitive
- `search_in_comments`: Search in comments

---

### `glob_search`
Search by glob patterns.

```python
glob_search(
    pattern: str,
    path: str = ".",
    exclude: Optional[List[str]] = None
) -> str
```

**Exemplo:**
```python
glob_search("**/*.py")  # Todos os arquivos Python
glob_search("src/**/*.ts", exclude=["*.test.ts"])
```

---

### `view_repo_map`
Display a hierarchical repository map.

```python
view_repo_map(depth: int = 3, path: str = ".") -> str
```

---

### `advanced_grep_search`
Advanced grep search with context.

```python
advanced_grep_search(
    pattern: str,
    path: str = ".",
    options: Optional[Dict] = None
) -> str
```

**Options:**
- `context_lines`: Linhas de contexto
- `whole_word`: Match palavra inteira
- `invert_match`: Inverter resultado

---

## 🔬 Codebase Investigation Tools (3)

### `investigate_codebase`
Full codebase analysis with CodeGraph.

```python
investigate_codebase(
    root_path: str,
    objective: Optional[str] = None,
    include_extensions: Optional[List[str]] = None,
    max_files: int = 100,
    verbose: bool = False,
    respect_gitignore: bool = True,
    use_imagination: bool = True
) -> Dict[str, Any]
```

**Retorna:**
- `summary`: Project statistics
- `context_manager`: Gerenciador de contexto
- `index`: Search index
- `imagination_scan`: Quick-scanner data

---

### `investigate_codebase_deep`
Deep analysis with dependency graph.

```python
investigate_codebase_deep(
    root_path: str,
    include_extensions: Optional[List[str]] = None,
    max_files: int = 200
) -> Dict[str, Any]
```

**Retorna:**
- `code_graph`: Code graph
- `aggregate_metrics`: Aggregate metrics
- `high_complexity_functions`: High-complexity functions

---

### `get_code_insights`
Responde perguntas sobre o codebase.

```python
get_code_insights(
    root_path: str,
    question: str,
    max_files: int = 100
) -> Dict[str, Any]
```

**Perguntas suportadas:**
- "What functions call X?"
- "What inherits from BaseClass?"
- "Most complex function?"
- "Where is Y defined?"
- "Impact of changing Z?"

---

## 💾 Memory Tools (5)

### `ler_pagina_caderno`
Read a notebook memory page.

```python
ler_pagina_caderno(caminho_pagina: str) -> str
```

---

### `listar_paginas_caderno`
List all available pages.

```python
listar_paginas_caderno() -> str
```

---

### `ver_indice_caderno`
Display index with summaries.

```python
ver_indice_caderno() -> str
```

---

### `info_sessao_caderno`
Current session information.

```python
info_sessao_caderno() -> str
```

---

### `save_constitution`
Save the project constitution.

```python
save_constitution(content: str, project_root: str = ".") -> str
```

---

## 📝 Git Tools (8)

### `git_status`
Git repository status.

```python
git_status() -> str
```

---

### `git_diff_context`
Complete bounded workspace state, including readable untracked files.

```python
git_diff_context(path: Optional[str] = None, max_chars: int = 12000) -> str
```

---

### `git_diff`
Uncommitted differences.

```python
git_diff(file: Optional[str] = None, staged: bool = False) -> str
```

---

### `git_log`
Commit history.

```python
git_log(limit: int = 10) -> str
```

---

### `git_branch`
Lista branches.

```python
git_branch() -> str
```

---

### `git_commit`
Cria commit com mensagem.

```python
git_commit(message: str, files: Optional[List[str]] = None) -> str
```

---

### `git_commit_smart`
Commit inteligente (linguagem natural).

```python
git_commit_smart(command: str) -> str
```

**Exemplos:**
```python
git_commit_smart("commit current changes")
git_commit_smart("commitar com mensagem 'feat: nova feature'")
```

---

### `git_smart`
Executa comando git em linguagem natural.

```python
git_smart(command: str) -> str
```

---

## 🗣️ Natural Git Tools (2)

### `parse_natural_git_command`
Interpreta comando git em linguagem natural.

```python
parse_natural_git_command(command: str) -> Dict[str, Any]
```

---

### `suggest_commit_message`
Sugere mensagem de commit.

```python
suggest_commit_message(changes: List[str]) -> str
```

---

## 💻 Shell Tools (2)

### `run_shell_command`
Execute a shell command (with confirmation).

```python
run_shell_command(command: str, background: bool = False) -> str
```

---

### `execute_shell_command`
Direct command execution.

```python
execute_shell_command(command: str, timeout: int = 30) -> Tuple[bool, str]
```

---

## 🌐 Web Tools (1)

### `web_search`
Pesquisa na web via Google.

```python
web_search(query: str, num_results: int = 5) -> str
```

---

## 🚀 Imagination Tools (2)

### `scan_filesystem_sync`
Quick filesystem scanner.

```python
scan_filesystem_sync(path: str = ".") -> Dict[str, Any]
```

**Retorna:**
- `total_files`: Total de arquivos
- `total_lines`: Total de linhas
- `by_category`: Por categoria
- `by_extension`: By extension
- `recently_modified`: Modificados recentemente

---

### `get_imagination_scanner`
Get the scanner instance.

```python
get_imagination_scanner() -> ImaginationScanner
```

---

## 🐳 Docker Tools (6)

### `docker_ps`
Lista containers.

```python
docker_ps(show_all: bool = False) -> str
```

---

### `docker_images`
List Docker images.

```python
docker_images() -> str
```

---

### `docker_logs`
Logs de container.

```python
docker_logs(container: str, tail: int = 50, follow: bool = False) -> str
```

---

### `docker_exec`
Execute a command in a container.

```python
docker_exec(container: str, command: str) -> str
```

---

### `docker_build`
Build a Docker image.

```python
docker_build(path: str, tag: str, dockerfile: str = "Dockerfile") -> str
```

---

### `docker_compose`
Executa docker-compose.

```python
docker_compose(action: str, file: str = "docker-compose.yml") -> str
```

**Actions:** `up`, `down`, `ps`, `logs`, `restart`, `stop`, `start`

---

## ⚙️ System Tools (4)

### `check_service_health`
Check health of an HTTP service.

```python
check_service_health(url: str, timeout: int = 5) -> str
```

---

### `check_port`
Check if a port is open.

```python
check_port(host: str, port: int, timeout: int = 3) -> str
```

---

### `system_resources`
Mostra CPU, RAM, Disco.

```python
system_resources() -> str
```

---

### `process_info`
Lista processos.

```python
process_info(name: Optional[str] = None) -> str
```

---

## 📊 Dev Tools (4)

### `edit_file`
Edita arquivo com diff visual.

```python
edit_file(path: str, old_content: str, new_content: str) -> str
```

---

### `analyze_code`
Analyse code (complexity, imports).

```python
analyze_code(path: str) -> str
```

---

### `find_in_files`
Search across multiple files.

```python
find_in_files(pattern: str, path: str = ".") -> str
```

---

### `tree_view`
Tree view.

```python
tree_view(path: str = ".", max_depth: int = 3) -> str
```

---

## 📋 Task Management Tools (5)

### `create_task_list`
Cria lista de tarefas.

```python
create_task_list(tasks: List[str], objective: str = "") -> str
```

**Exemplo:**
```python
create_task_list(
    tasks=["Analisar estrutura", "Ler main.py", "Documentar"],
    objective="Analyse project"
)
```

---

### `complete_task`
Mark a task as completed.

```python
complete_task(task_id: Optional[int] = None, task_text: Optional[str] = None) -> str
```

---

### `view_tasks`
Mostra todas as tarefas.

```python
view_tasks() -> str
```

---

### `add_task`
Adiciona nova tarefa.

```python
add_task(task_text: str) -> str
```

---

### `get_next_task`
Return the next pending task.

```python
get_next_task() -> str
```

---

## 🔍 Deep Analysis Tools (3)

### `deep_project_analysis`
Full project analysis.

```python
deep_project_analysis(
    path: str = ".",
    focus_areas: Optional[List[str]] = None,
    max_files: int = 50
) -> str
```

**Focus areas:**
- `quality`: Code quality
- `architecture`: Estrutura
- `security`: Security
- `performance`: Performance
- `documentation`: Documentation

---

### `discover_patterns`
Discover code patterns.

```python
discover_patterns(
    path: str = ".",
    pattern_type: str = "all"
) -> str
```

**Pattern types:** `all`, `naming`, `structure`, `testing`, `error`

---

### `analyze_dependencies`
Analyse project dependencies.

```python
analyze_dependencies(path: str = ".") -> str
```

---

## 📌 Notas Importantes

### Security
- All write operations request confirmation
- Shell commands go through security validation
- API keys are stored securely

### Performance
- Imagination tools use Nim for maximum performance
- Results are cached when appropriate
- Asynchronous operations available for TUI

### Integration
- All tools are accessible via function calling
- Feedback visual consistente com Rich
- Usage statistics are tracked

---

*Aura CLI — Tools Reference — v0.1.0 — 2026*
