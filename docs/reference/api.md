# API Reference - Aura CLI

Complete reference for the public APIs of Aura CLI.

## Index

- [Thread Management](#thread-management)
- [Worker Factory](#worker-factory)
- [Exception Handling](#exception-handling)
- [UI Formatters](#ui-formatters)
- [Command Processing](#command-processing)
- [Function Call Handling](#function-call-handling)
- [App Loop](#app-loop)
- [Helpers](#helpers)

---

## Thread Management

### `get_thread_manager() -> ThreadManager`

Returns the ThreadManager singleton instance.

**Returns:**
- `ThreadManager`: Singleton thread manager instance

**Example:**
```python
from aura_cli.cli.utils.thread_manager import get_thread_manager

thread_manager = get_thread_manager()
```

### `ThreadManager.register_thread()`

Registra e inicia uma nova thread.

**Parameters:**
- `name` (str): Unique name for the thread
- `target` (Callable): Callable to execute in the thread
- `daemon` (bool): Whether the thread is a daemon (default: True)
- `shutdown_timeout` (float): Timeout para shutdown graceful (default: 5.0)
- `health_check` (Optional[Callable]): Optional health-check callable
- `**kwargs`: Argumentos adicionais para Thread constructor

**Returns:**
- `threading.Thread`: Thread criada e iniciada

**Raises:**
- `ValueError`: If the thread name already exists

**Example:**
```python
thread = thread_manager.register_thread(
    name="worker_thread",
    target=worker_function,
    daemon=True,
    shutdown_timeout=30.0
)
```

### `ThreadManager.stop_thread()`

Para uma thread gracefulmente.

**Parameters:**
- `name` (str): Nome da thread a parar
- `timeout` (Optional[float]): Timeout opcional (usa default se None)

**Returns:**
- `bool`: True se parou com sucesso, False se timeout

**Example:**
```python
success = thread_manager.stop_thread("worker_thread", timeout=10.0)
```

### `ThreadManager.stop_all()`

For all registered threads.

**Parameters:**
- `timeout` (Optional[float]): Timeout opcional

**Returns:**
- `Dict[str, bool]`: Dictionary mapping thread names to stop status

**Example:**
```python
results = thread_manager.stop_all(timeout=10.0)
```

### `ThreadManager.get_thread()`

Get a thread instance by name.

**Parameters:**
- `name` (str): Nome da thread

**Returns:**
- `Optional[threading.Thread]`: Thread or None if not found

### `ThreadManager.get_thread_info()`

Get thread information by name.

**Parameters:**
- `name` (str): Nome da thread

**Returns:**
- `Optional[ThreadInfo]`: Thread info or None

### `ThreadManager.list_threads()`

List all registered thread names.

**Returns:**
- `List[str]`: Lista de nomes de threads

### `ThreadManager.get_stats()`

Get statistics for all threads.

**Returns:**
- `Dict[str, Any]`: Statistics including total, running, stopped, etc.

---

## Worker Factory

### `create_agi_worker_thread()`

Create and register an AgiWorker thread.

**Parameters:**
- `objective` (str): Task objective for the AGI worker
- `model` (str): LLM model name to use
- `api_keys` (Dict[str, str]): Dictionary of API keys
- `headless` (bool): Whether to run in headless mode (default: False)
- `project_root` (Optional[Path]): Project root path (default: None)
- `shutdown_timeout` (float): Shutdown timeout in seconds (default: 30.0)

**Returns:**
- `Tuple[AgiWorker, threading.Thread]`: Tuple with worker and registered thread

**Example:**
```python
from aura_cli.cli.utils.worker_factory import create_agi_worker_thread

agi_worker, thread = create_agi_worker_thread(
    objective="Analyze project structure",
    model="gemini/gemini-2.5-flash",
    api_keys={"GOOGLE_API_KEY": "..."},
    project_root=Path.cwd()
)
```

### `create_ops_worker_thread()`

Create and register an OpsWorker thread.

**Parameters:**
- `task` (str): Task description for the Ops worker
- `model` (str): LLM model name to use
- `api_keys` (Dict[str, str]): Dictionary of API keys
- `mode` (str): Operation mode ('git', 'docker', or 'general') (default: "general")
- `headless` (bool): Whether to run in headless mode (default: False)
- `shutdown_timeout` (float): Shutdown timeout in seconds (default: 30.0)

**Returns:**
- `Tuple[OpsWorker, threading.Thread]`: Tuple with worker and registered thread

**Example:**
```python
from aura_cli.cli.utils.worker_factory import create_ops_worker_thread

ops_worker, thread = create_ops_worker_thread(
    task="Check git status",
    model="gemini/gemini-2.5-flash",
    api_keys={"GOOGLE_API_KEY": "..."},
    mode="git"
)
```

---

## Exception Handling

### Exception Hierarchy

```
AuraCLIError (base)
├── ConfigurationError
├── ToolExecutionError
├── WorkerError
├── LLMError
├── UIError
├── ThreadError
├── ValidationError
├── FileOperationError
└── CommandError
```

### `ToolExecutionError`

Exception for tool execution failures.

**Parameters:**
- `tool_name` (str): Nome da ferramenta que falhou
- `message` (str): Mensagem de erro
- `original_error` (Optional[Exception]): Erro original que causou a falha

**Attributes:**
- `tool_name`: Nome da ferramenta
- `original_error`: Erro original

**Example:**
```python
from aura_cli.cli.utils.exceptions import ToolExecutionError

raise ToolExecutionError(
    tool_name="read_file",
    message="File not found",
    original_error=FileNotFoundError("path/to/file")
)
```

### `WorkerError`

Exception for worker errors.

**Parameters:**
- `worker_name` (str): Nome do worker
- `message` (str): Mensagem de erro
- `original_error` (Optional[Exception]): Erro original

### `FileOperationError`

Exception for file operation failures.

**Parameters:**
- `operation` (str): Operation type (create, edit, read, delete)
- `file_path` (str): File path
- `message` (str): Mensagem de erro
- `original_error` (Optional[Exception]): Erro original

### `CommandError`

Exception for command processing failures.

**Parameters:**
- `command` (str): Comando que falhou
- `message` (str): Mensagem de erro
- `original_error` (Optional[Exception]): Erro original

---

## UI Formatters

### `format_agent_status()`

Formata mensagem de status de agente.

**Parameters:**
- `agent_type` (str): Tipo de agente (AGI, Ops, etc.)
- `status` (str): Mensagem de status

**Returns:**
- `str`: Mensagem formatada com Rich markup

**Example:**
```python
from aura_cli.cli.ui.formatters import format_agent_status

message = format_agent_status("Aura AGI", "ON")
# Returns: "[cyan]🤖 Aura AGI: ON[/cyan]"
```

### `format_success_message()`

Formata mensagem de sucesso.

**Parameters:**
- `message` (str): Texto da mensagem
- `icon` (Optional[str]): Optional icon (default: SUCCESS)

**Returns:**
- `str`: Mensagem formatada

### `format_error_message()`

Formata mensagem de erro.

**Parameters:**
- `message` (str): Texto da mensagem
- `icon` (Optional[str]): Optional icon (default: ERROR)

**Returns:**
- `str`: Mensagem formatada

### `format_info_message()`

Formata mensagem informativa.

**Parameters:**
- `message` (str): Texto da mensagem
- `icon` (Optional[str]): Optional icon (default: INFO)

**Returns:**
- `str`: Mensagem formatada

### `format_warning_message()`

Formata mensagem de aviso.

**Parameters:**
- `message` (str): Texto da mensagem
- `icon` (Optional[str]): Optional icon (default: WARNING)

**Returns:**
- `str`: Mensagem formatada

### `format_file_operation()`

Format a file operation message.

**Parameters:**
- `operation` (str): Operation type (create, edit, read, delete)
- `file_path` (str): File path
- `status` (str): Operation status (completed, failed, pending)

**Returns:**
- `str`: Mensagem formatada

---

## Command Processing

### `process_slash_command()`

Process slash commands and return whether the loop should continue.

**Parameters:**
- `command` (str): User command
- `agi_thread` (Optional[threading.Thread]): Thread AGI atual (se existe)
- `ops_thread` (Optional[threading.Thread]): Thread Ops atual (se existe)
- `final_model` (str): Nome do modelo AI atual
- `stats` (StatsTracker): Statistics tracker instance

**Returns:**
- `Tuple[bool, Optional[str], Optional[threading.Thread], Optional[threading.Thread], Optional[str]]`:
  - `continue_loop`: Se deve continuar o loop principal
  - `optional_message`: Mensagem para exibir (se houver)
  - `new_agi_thread`: Nova thread AGI (se iniciada)
  - `new_ops_thread`: Nova thread Ops (se iniciada)
  - `new_model`: Novo nome de modelo (se mudou)

**Example:**
```python
from aura_cli.cli.helpers import process_slash_command

should_continue, message, new_agi, new_ops, new_model = process_slash_command(
    command="/agi analyze project",
    agi_thread=None,
    ops_thread=None,
    final_model="auto",
    stats=stats_tracker
)
```

### Handlers de Comandos

#### `handle_help() -> None`
Display help message with all available commands.

#### `handle_tools() -> None`
List all available tools in columns.

#### `handle_tool_details(tool_name: str) -> None`
Display technical details for a specific tool.

**Parameters:**
- `tool_name` (str): Nome da ferramenta a inspecionar

#### `handle_model(current_model_name: str) -> None`
Allow interactive LLM model selection.

**Parameters:**
- `current_model_name` (str): Nome do modelo atualmente ativo

#### `handle_todo() -> None`
Exibe lista visual de tarefas do to-do.md.

#### `handle_clear() -> None`
Limpa a tela do terminal (cross-platform).

#### `handle_init() -> None`
Index the current project (generate context, conventions, and overview).

---

## Function Call Handling

### `execute_tool_call()`

Executa uma chamada de ferramenta (tool call) do LLM.

**Parameters:**
- `function_name` (str): Function/tool name
- `function_args` (Dict[str, Any]): Function arguments
- `tool_call_id` (str): Unique tool call ID
- `available_tools` (Dict[str, Any]): Dictionary of available tools
- `conversation_history` (List[Dict]): Conversation history
- `stats` (Any): Statistics tracker
- `ui` (UIManager): Gerenciador de UI
- `console` (Console): Console Rich

**Returns:**
- `Tuple[Any, float]`: Tuple with result and execution time

**Raises:**
- `ToolExecutionError`: If execution fails
- `FileOperationError`: If a file operation fails

### `process_function_calls_loop()`

Process the function-call loop until a final response is obtained.

**Parameters:**
- `model` (str): Nome do modelo LLM
- `conversation_history` (List[Dict]): Conversation history
- `tool_schemas` (List[Dict]): Schemas das ferramentas
- `available_tools` (Dict[str, Any]): Available tools
- `stats` (Any): Statistics tracker
- `ui` (UIManager): Gerenciador de UI
- `console` (Console): Console Rich
- `use_local_llm` (bool): Se deve usar LLM local (default: False)
- `max_calls` (int): Maximum calls (default: 5)
- `shutdown_event` (Optional[threading.Event]): Evento de shutdown

**Returns:**
- `Tuple[str, Any]`: Tupla com resposta final e objeto de resposta

---

## App Loop

### `AppLoop`

Main class encapsulating the application interaction loop.

#### `__init__()`

Inicializa o AppLoop.

**Parameters:**
- `ui` (UIManager): Gerenciador de UI
- `stats` (StatsTracker): Statistics tracker
- `console` (Console): Console Rich
- `conversation_history` (List[Dict[str, Any]]): Conversation history
- `context_manager` (ContextManager): Gerenciador de contexto
- `available_tools` (Dict[str, Any]): Available tools
- `initial_model` (str): Modelo inicial
- `project_root` (Path): Caminho raiz do projeto

#### `run() -> None`

Start and run the main interaction loop.

#### `process_command_single_shot() -> bool`

Process a single user command.

**Parameters:**
- `command` (str): User command

**Returns:**
- `bool`: False if the application should terminate, True otherwise

#### `shutdown() -> bool`

Encerra gracefulmente todas as threads e recursos.

**Parameters:**
- `timeout` (float): Maximum time to wait for shutdown (default: 10.0)

**Returns:**
- `bool`: True if shutdown was successful, False otherwise

#### `set_shutdown_event() -> None`

Define evento que sinaliza quando TUI deve encerrar.

**Parameters:**
- `event` (threading.Event): Evento de threading para sinalizar shutdown

---

## Helpers

### `initialize_conversation_history() -> List[Dict[str, str]]`

Initialise conversation history with the default system message.

**Returns:**
- `List[Dict[str, str]]`: Lista com mensagem de sistema inicial

### `setup_prompt_session() -> PromptSession`

Configure and return an interactive prompt session with persistent history.

**Returns:**
- `PromptSession`: Configured session ready to use

### `parse_agi_command() -> Optional[str]`

Extrai objetivo do comando /agi.

**Parameters:**
- `command` (str): String completa do comando (ex: "/agi create a blog")

**Returns:**
- `Optional[str]`: Extracted objective, or default exploration task if empty

### `parse_ops_command() -> Tuple[str, str]`

Extrai modo e tarefa do comando /ops.

**Parameters:**
- `command` (str): String completa do comando (ex: "/ops git status")

**Returns:**
- `Tuple[str, str]`: Tuple (mode, task) where mode is 'git', 'docker', or 'general'

### `get_api_keys_dict() -> Dict[str, str]`

Get a dictionary of API keys from environment variables.

**Returns:**
- `Dict[str, str]`: Dictionary with configured API keys (Google, OpenAI, Anthropic)

### `handle_multiline_input() -> Optional[str]`

Process multi-line user input.

**Returns:**
- `Optional[str]`: Texto completo ou None se cancelado (ESC/Ctrl+C)

### `handle_status_updates() -> None`

Display real-time status updates from the queue.

**Parameters:**
- `status_queue` (queue.Queue[str]): Queue contendo mensagens de status dos workers

---

## Command Router

### `route_command()`

Process and route the user command to the appropriate handler.

**Parameters:**
- `command` (str): User input command
- `agi_thread` (Optional[threading.Thread]): AgiWorker thread instance
- `ops_thread` (Optional[threading.Thread]): OpsWorker thread instance
- `current_model` (str): Modelo LLM atualmente ativo
- `stats` (StatsTracker): Statistics tracker object
- `ui` (Any): UIManager instance
- `console` (Console): Objeto Console Rich
- `project_root` (Optional[Path]): Project root path (default: None)
- `app_loop` (Optional[Any]): AppLoop instance (default: None)

**Returns:**
- `Tuple[bool, Optional[str], Optional[threading.Thread], Optional[threading.Thread], Optional[str]]`:
  - `should_continue`: Se loop principal deve continuar
  - `result_type`: Tipo de resultado ('llm_query' ou mensagem)
  - `new_agi`: Thread AGI atualizada (ou None)
  - `new_ops`: Thread Ops atualizada (ou None)
  - `new_model`: Nome de modelo atualizado (ou None)

---

## Usage Conventions

### Thread Management

- Sempre use `ThreadManager` para criar threads
- Always register threads with unique names
- Use timeouts apropriados para shutdown
- Chame `cleanup()` em workers antes de encerrar

### Exception Handling

- Use specific exceptions from the hierarchy
- Sempre inclua contexto (tool_name, worker_name, etc.)
- Use `exc_info=True` em logging de erros inesperados
- Preserve `original_error` when possible

### UI Formatting

- Use centralised formatters for consistency
- Prefer formatters over manual formatting
- Keep icons and styles consistent

### Command Processing

- Handlers devem ser independentes
- Return clear messages to the user
- Handle errors gracefully
- Use structured logging

---

## Complete Examples

### Create and Manage a Worker

```python
from pathlib import Path
from aura_cli.cli.utils.worker_factory import create_agi_worker_thread
from aura_cli.cli.utils.thread_manager import get_thread_manager

# Create worker
api_keys = {"GOOGLE_API_KEY": "..."}
agi_worker, thread = create_agi_worker_thread(
    objective="Analyze project",
    model="gemini/gemini-2.5-flash",
    api_keys=api_keys,
    project_root=Path.cwd()
)

# Wait for completion
thread.join(timeout=300.0)

# Cleanup
agi_worker.cleanup()
```

### Process a Slash Command

```python
from aura_cli.cli.helpers import process_slash_command
from aura_cli.core.stats import get_stats

stats = get_stats()
should_continue, message, new_agi, new_ops, new_model = process_slash_command(
    command="/agi create API",
    agi_thread=None,
    ops_thread=None,
    final_model="auto",
    stats=stats
)

if message:
    print(message)
```

### Handle Exceptions

```python
from aura_cli.cli.utils.exceptions import ToolExecutionError, FileOperationError

try:
    result = execute_tool("read_file", {"path": "file.txt"})
except FileOperationError as e:
    logger.error(f"File operation failed: {e.file_path}", exc_info=True)
    # Handle error
except ToolExecutionError as e:
    logger.error(f"Tool failed: {e.tool_name}", exc_info=True)
    # Handle error
```

---

## Version Notes

### v0.1.0
- Centralised ThreadManager
- Complete exception hierarchy
- Worker factory functions
- Centralised UI formatters
- Structured logging
- Graceful shutdown

---

*Aura CLI — API Reference — v0.1.0 — 2026*
