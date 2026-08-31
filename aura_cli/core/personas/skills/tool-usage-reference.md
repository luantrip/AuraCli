---
name: Tool Usage Reference
description: Use this skill when the agent needs to call tools correctly. Contains exact function signatures, parameter types, return values, and usage patterns for all core Aura CLI tools.
version: 1.0.0
author: Aura Core Team
---

# Referência de Ferramentas — Assinaturas Exatas

## Filesystem

### read_file
```python
read_file(path: str) -> str
```
Lê o conteúdo completo de um arquivo. Retorna o texto ou mensagem de erro.

### write_file
```python
write_file(path: str, content: str, append: bool = False) -> str
```
Cria ou sobrescreve um arquivo. Cria diretórios pai automaticamente.
- `append=True`: adiciona ao final em vez de sobrescrever
- Retorna: "Conteúdo escrito em 'path' com sucesso"

### edit_file
```python
edit_file(path: str, old_content: str, new_content: str) -> str
```
Substitui a PRIMEIRA ocorrência exata de `old_content` por `new_content`.
- `old_content` deve ser uma cópia EXATA do trecho a substituir (incluindo indentação)
- Retorna erro se old_content não for encontrado no arquivo
- Use `read_file` primeiro para copiar o trecho exato

### list_directory
```python
list_directory(path: str = ".") -> str
```
Lista arquivos e pastas no diretório. Retorna lista formatada.

### tree_view
```python
tree_view(path: str = ".", max_depth: int = 3) -> str
```
Visualização hierárquica em árvore. Útil para entender estrutura de projeto.

## Busca

### find_in_files
```python
find_in_files(pattern: str, path: str = ".", filters: dict = None) -> str
```
Busca regex em todos os arquivos. Retorna `file:line: content`.

### codebase_search
```python
codebase_search(query: str, path: str = ".", max_results: int = 50) -> str
```
Busca ampla por padrão. Exclui .git, __pycache__, node_modules, .venv.

### glob_search
```python
glob_search(pattern: str, path: str = ".") -> str
```
Busca por padrão de nome de arquivo (ex: "**/*.py", "src/**/*.ts").

### advanced_grep_search
```python
advanced_grep_search(pattern: str, path: str = ".", context_lines: int = 2) -> str
```
Grep avançado com linhas de contexto ao redor de cada match.

## Shell

### run_shell_command
```python
run_shell_command(command: str, background: bool = False) -> str
```
Executa comando no terminal. Pipes (`|`) e `&&` são permitidos.
- Timeout: 300 segundos
- `background=True`: retorna PID do processo
- Retorna: stdout + stderr combinados

## Git

### git_status
```python
git_status() -> str
```
Retorna: branch atual, arquivos staged, modified, untracked.

### git_diff
```python
git_diff(file: str = None, staged: bool = False) -> str
```
Diff unificado. `staged=True` mostra diff do staging area.

### git_log
```python
git_log(n: int = 10) -> str
```
Últimos N commits formatados.

### git_commit
```python
git_commit(message: str, files: list = None) -> str
```
Cria commit. Se `files` fornecido, faz `git add` nos arquivos primeiro.

### suggest_commit_message
```python
suggest_commit_message() -> str
```
Gera mensagem de commit baseada no diff atual (Conventional Commits).

## Web

### web_search
```python
web_search(query: str, num_results: int = 5) -> str
```
Busca na web. Retorna título + URL + descrição de cada resultado.

## Padrões de Uso

### Criar arquivo novo:
1. `write_file(path="src/module.py", content="...")`
2. `read_file(path="src/module.py")` ← verificar

### Editar trecho específico:
1. `read_file(path="src/main.py")` ← copiar trecho exato
2. `edit_file(path="src/main.py", old_content="trecho exato", new_content="novo trecho")`

### Buscar padrão no projeto:
1. `find_in_files(pattern="TODO|FIXME", path="src/")`

### Executar e validar:
1. `run_shell_command(command="python -m pytest tests/ -v")`
2. Analise output para sucesso/falha
