---
name: Aura CLI Complete Knowledge Base
description: Use this skill when the user asks about Aura CLI, its features, tools, architecture, commands, agents, or needs comprehensive information about the project. This is the definitive knowledge base for everything related to Aura CLI, including all 68+ tools, the creator Luan Dev, project structure, and usage patterns.
version: 1.0.0
author: Luan Dev
---

# Aura CLI - Complete Knowledge Base

## About the Project

**Aura CLI** is an advanced command-line tool that combines Large Language Models (LLMs) with a comprehensive set of development tools to automate and accelerate programming tasks. It's designed with a focus on quality, security, and extensibility, offering a professional AI-assisted development experience.

### Creator

**Luan Dev** (luan@udesc.br)
- Creator and primary developer of Aura CLI
- Developed with passion for creating the ultimate development assistant
- Contact: luan@udesc.br

### Project Goals

Aura CLI was designed to be the definitive development assistant, offering:
- **Interactive CLI Interface**: Modern chat with integrated terminal
- **Multi-Model Support**: Gemini, GPT, Claude, and local LLMs
- **Specialized Agents**: AGI for strategy and Ops for DevOps
- **68+ Tools**: Complete coverage of development and operations
- **Professional Architecture**: Clean, documented, and tested code

### Key Differentiators

| Feature | Description |
|---------|-------------|
| **68+ Tools** | 51 AGI tools + 17+ DevOps tools integrated |
| **TUI Textual IDE-Grade** | Terminal graphical interface with 18 specialized widgets |
| **Interactive Terminal** | Execute shell commands directly in the interface |
| **3 Specialized Agents** | Chat, AGI (Manager), Ops (DevOps) |
| **Multi-Model with Fallback** | Support for multiple LLMs with automatic fallback |
| **Smart Compression** | Up to 76% context reduction while maintaining essential |
| **Advanced Security** | API keys encrypted with OS keyring |
| **Complete Type Hints** | PEP 561 (`py.typed`) - fully typed |
| **Complete Documentation** | 200+ Python files with professional docstrings |
| **Comprehensive Tests** | 105+ UI tests + 74 files covering all modules |
| **Extensible** | Plugin system + extensions for custom functionality |
| **Nebula Void Theme** | "Nebula Assembly" aesthetic with responsive CSS Grid |

## Architecture

### Directory Structure

```
aura-cli/
├── aura_cli/
│   ├── cli/                    # Command-line interface
│   │   ├── main.py            # Entry point
│   │   ├── app_loop.py        # Interactive loop
│   │   ├── command_processor.py
│   │   ├── command_router.py
│   │   ├── function_call_handler.py
│   │   ├── ui/                # CLI UI components (30+ files)
│   │   └── workers/           # Background workers
│   │       ├── agi_worker.py  # AGI worker
│   │       └── ops_worker.py  # Ops worker
│   │
│   ├── core/                  # Business logic
│   │   ├── agents/            # Agent system
│   │   ├── consciousness/     # Skills & Agents (RAG)
│   │   ├── events/            # Event system (Pydantic)
│   │   ├── llm/               # LLM integration
│   │   ├── tools/             # AGI tools (51)
│   │   ├── ops_tools/         # DevOps tools (17+)
│   │   ├── sessions/          # Session management
│   │   ├── cache_advanced/    # Persistent caching
│   │   ├── extensions/        # Plugin system
│   │   └── utils/             # Utilities
│   │
│   ├── tui/                   # Terminal UI (Textual)
│   │   ├── app.py             # Main application
│   │   ├── bridge.py          # Core-TUI bridge
│   │   ├── core/              # TUI infrastructure
│   │   │   ├── sync_store.py  # Reactive state
│   │   │   ├── sync_manager.py
│   │   │   ├── event_bus.py
│   │   │   └── cache_manager.py
│   │   └── widgets/           # UI components (18 widgets)
│   │
│   └── consciousness/         # Agent consciousness
│       ├── skill_retriever.py # RAG-based skill retrieval
│       ├── agent_runner.py   # Agent execution
│       ├── skills/            # Knowledge files (.md)
│       └── agents/            # Persona definitions (.md)
```

### Core Components

#### 1. Event System
Uses Pydantic models for type-safe, validated event transport:
- `AgiEvent` with `AgiEventType` enum
- Events flow from Core → TUI via status_queue
- Real-time UI updates

#### 2. Service Registry
Centralized tool management with 68+ registered tools:
- Automatic tool discovery
- Schema validation
- Execution with retry and fallback
- Usage metrics

#### 3. Consciousness System
RAG-based knowledge retrieval and specialist agents:
- `SkillRetriever`: Semantic search over skills using sentence-transformers
- `AgentRunner`: Execute specialist personas defined in Markdown
- Skills stored in `consciousness/skills/` (Markdown with YAML frontmatter)
- Agents stored in `consciousness/agents/` (Markdown with YAML frontmatter)

#### 4. Structured Exceptions
Type-safe errors with rich context:
- `AuraError[T]` generic base class
- Pydantic-validated error data
- Specific exceptions: `ToolExecutionError`, `SessionNotFoundError`, `LLMError`, etc.

#### 5. SyncStore (Reactive State)
Centralized reactive state for TUI:
- Dot-notation path access (`store.set("tasks.task_1.status", "running")`)
- Change notifications
- Batch update support

## Available Commands

### Slash Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Shows all available commands | `/help` |
| `/agi [objective]` | Activates Project Manager | `/agi create REST API with FastAPI` |
| `/ops [mode] <task>` | Activates DevOps (git/docker/general) | `/ops git make commit` |
| `/todo` | Displays project task list | `/todo` |
| `/tools` | Lists all 68+ tools | `/tools` |
| `/tool <name>` | Shows details of a tool | `/tool read_file` |
| `/theme [name]` | Changes UI theme | `/theme minimal` |
| `/dev [on\|off\|status]` | Manages Aura Dev (local LLM) | `/dev on` |
| `/model` | Selects LLM model | `/model` |
| `/extensions` | Lists loaded extensions | `/extensions` |
| `/settings` | Settings menu | `/settings` |
| `/session [cmd]` | Manages sessions (save/load/list) | `/session save my_project` |
| `/workflow [cmd]` | Manages workflows (create/run/list) | `/workflow run deploy` |
| `/cache [cmd]` | Manages cache (stats/clear) | `/cache stats` |
| `/clear` | Clears screen | `/clear` |
| `/exit` | Exits Aura CLI | `/exit` |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | List all tools |
| `Ctrl+M` | Show current LLM model |
| `Ctrl+L` | Clear screen |
| `Shift+Tab` | Toggle auto-run (automatic execution) |
| `Ctrl+C` | Exit Aura CLI |
| `↑↓` | Navigate command history |
| `"""` | Multi-line input |

## All Available Tools (68+)

### File System Tools (8)

1. **read_file** - Read file content with offset/limit support
2. **write_file** - Write to files with confirmation
3. **list_directory** - Structured directory listing
4. **edit_file** - Precise file editing operations
5. **backup_file** - Automatic backup before edits
6. **restore_backup** - Restore from backups
7. **tree_view** - Tree visualization of directories
8. **find_in_files** - Search for patterns in files

### Development Tools (12)

1. **analyze_code** - Static code analysis
2. **analyze_code_nlp** - NLP-based code analysis (HuggingFace)
3. **validate_syntax** - Multi-layer validation (syntax, types, style)
4. **classify_code** - Code classification
5. **summarize_code** - Code summarization
6. **tokenize_code** - Code tokenization
7. **find_duplicate_code** - Find semantic code duplication
8. **semantic_search_advanced** - Advanced semantic search
9. **generate_tests_ml** - ML-based test generation
10. **edit_file** - File editing with operations
11. **tree_view** - Directory tree view
12. **find_in_files** - Search in files

### Shell Tools (5)

1. **execute_shell_command** - Execute shell commands
2. **run_shell_command** - Run shell commands with output
3. **is_shell_command** - Detect if input is shell command
4. **extract_shell_command** - Extract command from text
5. **should_execute_directly** - Determine if command should execute directly

### Web Tools (3)

1. **web_search** - Web search with structured results
2. **web_search_advanced** - Advanced web search
3. **web_scrape** - Web scraping (if available)

### Git Tools (7)

1. **git_status** - Repository status
2. **git_diff** - View changes
3. **git_log** - Commit history
4. **git_branch** - Branch operations
5. **git_commit** - Create commit
6. **git_commit_smart** - Smart commit with AI
7. **git_smart** - Natural language Git commands

### Docker Tools (6)

1. **docker_ps** - List containers
2. **docker_images** - List images
3. **docker_logs** - View container logs
4. **docker_exec** - Execute command in container
5. **docker_build** - Build image
6. **docker_compose** - Docker Compose operations

### Monitoring Tools (4)

1. **check_service_health** - Health check for services
2. **check_port** - Port availability check
3. **system_resources** - System resource monitoring
4. **process_info** - Process information

### Codebase Tools (5)

1. **codebase_search** - Semantic codebase search
2. **glob_search** - Glob pattern search
3. **advanced_grep_search** - Advanced grep search
4. **view_repo_map** - Repository structure visualization
5. **view_subdirectory** - Subdirectory view

### Infrastructure Tools (8)

1. **kubernetes_*** - Kubernetes operations
2. **terraform_*** - Terraform operations
3. **cloud_providers_*** - Cloud provider operations (AWS, GCP, Azure)
4. **infrastructure_as_code** - IaC operations

### Database Tools (5)

1. **database_backup** - Database backup
2. **database_migration** - Database migrations
3. **database_monitor** - Database monitoring
4. **query_executor** - Execute database queries
5. **database_health** - Database health check

### Security Tools (5)

1. **vulnerability_scanner** - Vulnerability scanning
2. **security_audit** - Security auditing
3. **secret_manager** - Secret management
4. **access_control** - Access control operations
5. **security_scan** - Security scanning

### CI/CD Tools (4)

1. **github_actions_*** - GitHub Actions operations
2. **workflow_automation** - Workflow automation
3. **pipeline_manager** - Pipeline management
4. **deployment** - Deployment operations

### Testing Tools (6)

1. **run_tests** - Run test suite
2. **find_tests** - Discover tests
3. **test_coverage** - Test coverage analysis
4. **test_analysis** - Test analysis
5. **test_generation** - Test generation
6. **test_runner** - Test runner

## Specialized Agents

### 1. Aura AGI - Project Manager

**Purpose**: Strategic planning and code analysis agent

**Features**:
- Intelligent context detection (analyzes project structure automatically)
- Automatic To-Do system (tracking via `.aura/to-do.md`)
- 51 specialized tools for analysis, editing, refactoring, and validation
- Asynchronous execution with real-time feedback
- Dependency analysis (dependency graphs and impact analysis)
- Intelligent refactoring (strategic planning and safe execution)

**Usage**:
```bash
/agi create a blog with React and FastAPI
/agi
```

### 2. Aura Ops - DevOps Engineer

**Purpose**: Operations and infrastructure specialist

**Features**:
- **Advanced Git**: 7 tools + natural language commands
- **Complete Docker**: 6 tools (ps, logs, build, compose, exec, images)
- **Monitoring**: 4 tools (health, port, resources, processes)
- **Infrastructure**: Support for Kubernetes, Terraform, Cloud Providers
- **CI/CD**: Integration with GitHub Actions and pipelines
- **Security**: Vulnerability scanner and auditing
- **Safe Execution**: Validations and confirmations before critical operations

**Usage**:
```bash
/ops git make commit saying "fix: corrected bug"
/ops docker ps
/ops check health http://localhost:3000
```

### 3. Chat Agent

**Purpose**: General-purpose conversational assistant

**Features**:
- Natural language interaction
- Tool calling when needed
- Context-aware responses
- Multi-model support

## Consciousness System

### Skills

Skills are Markdown files stored in `aura_cli/consciousness/skills/` that provide knowledge to the LLM through RAG (Retrieval-Augmented Generation).

**Current Skills**:
1. **clean-code.md** - Clean Code Principles (Robert C. Martin)
2. **git-workflow.md** - Git workflow best practices
3. **python-environment.md** - Python environment management

**Skill Format**:
```markdown
---
name: Skill Name
description: Detailed description with keywords for semantic matching
version: 1.0.0
author: Author Name
---

# Skill Content

Detailed knowledge content...
```

**How It Works**:
- `SkillRetriever` uses sentence-transformers for semantic search
- Falls back to keyword matching if embeddings unavailable
- Injects relevant skill content into LLM context

### Agents

Agents are specialist personas defined in Markdown files stored in `aura_cli/consciousness/agents/`.

**Current Agents**:
1. **code-refactor-agent.md** - Code refactoring specialist
2. **code-reviewer-agent.md** - Code review specialist
3. **test-writer-agent.md** - Test writing specialist

**Agent Format**:
```markdown
---
name: agent-name
description: When to use this agent and what it does
model: sonnet
allowed-tools: Read, Write, Edit, Grep
---

You are a [specialist role]. Your task is to [main objective].

## Process
1. Step One
2. Step Two

## Constraints
- What NOT to do

## Output Format
Expected output structure...
```

## Usage Examples

### Normal Chat

```bash
› You: List files in this directory
› Aura: [Executes list_directory and shows formatted table]

› You: Read README.md content
› Aura: [Uses read_file and shows formatted content]

› You: Search about FastAPI authentication
› Aura: [Uses web_search and returns structured results]
```

### Interactive Terminal

```bash
› pwd
$ /Users/user/project
✅

› ls -la
$ ls -la
✅ [formatted file listing]

› grep -r "TODO" .
$ grep -r "TODO" .
✅ [formatted grep results]
```

### Multi-line Input

```bash
› You: """
... Create a config.py file with:
... - DATABASE_URL
... - SECRET_KEY
... - DEBUG_MODE
... """
› Aura: [Creates file with requested structure]
```

### AGI Mode - Project Manager

**Create new project**:
```bash
› /agi create a blog with React and FastAPI
```

Aura AGI will:
1. Create `.aura/` with structured documentation
2. Generate planning files (context, architecture, to-do, etc.)
3. Start incremental implementation

**Existing project**:
```bash
› /agi
```

Aura AGI will:
1. Analyze project structure
2. Create documentation based on code
3. Ask: "What would you like to do?"

### Ops Mode - DevOps

**Git**:
```bash
› /ops git make commit saying "fix: corrected bug"
› /ops git view changes
› /ops git history
› /ops git create branch feature/new-feature
```

**Docker**:
```bash
› /ops docker ps
› /ops docker logs <container>
› /ops docker build . -t my-image
› /ops docker compose up -d
```

**Monitoring**:
```bash
› /ops check system resources
› /ops check health http://localhost:3000
› /ops check port 8080
› /ops process info 1234
```

## Advanced Features

### Persistent Cache
- Disk cache with configurable TTL
- zlib compression for space savings
- LRU policy with size limit
- Specialized cache for code analysis
- Vector embedding cache

### Session System
- Save and restore context between executions
- Persistent conversation history
- Agent state between sessions
- Session export/import

### Rate Limiter LLM
- Request control per provider
- Sliding window for precise rate limiting
- Configurable limits per minute/day
- Automatic backoff on limit

### User Workflows
- Create custom workflows
- Steps with dependencies and conditions
- Variable and template support
- Execution with automatic retry

### Plugin API
- Hook system for extensions
- Decorators `@aura_tool`, `@aura_command`
- Complete plugin lifecycle
- Shared context between plugins

### Context Compression
- Intelligent reduction of up to 76% in context size
- Preserves essential messages and critical information
- Adaptive algorithm based on semantic importance

### Semantic Indexing
- Intelligent codebase search using embeddings
- Support for multiple models (SentenceTransformers, OpenAI, CodeBERT)
- Vector storage with TTL and automatic cleanup
- Persistent embedding cache

### Fallback System
- Robust fallback between models
- Automatic failure detection and intelligent retry
- Primary and secondary model configuration

## TUI (Textual User Interface)

### Widgets (18 Specialized Widgets)

1. **AuraChatLog** - Chat log with Rich/Markdown support and streaming
2. **AuraInputBar** - Command input bar
3. **AuraStatusSidebar** - Sidebar with status and task tree
4. **AuraLoadingIndicator** - Animated loading indicator
5. **AuraProgressBar** - Styled progress bar
6. **AuraToast** - Toast notifications
7. **AuraFooter** - Footer with keybindings
8. **CodeAnalysisPanel** - Code analysis with AI
9. **EventStreamPanel** - Real-time AGI event stream
10. **MetricsPanel** - System metrics panel
11. **LLMSettingsPanel** - LLM configuration
12. **MemoryBrowser** - Conversation memory browser
13. **ToolRegistryPanel** - OPS tools visualization
14. **TestRunnerPanel** - pytest integration
15. **WorkflowMonitor** - Workflow monitoring
16. **AutocompleteInput** - Contextual autocomplete input
17. **Charts** - ASCII charts (line, bar, gauge)
18. **IDEPanel** - IDE-like features (file tree, issues, refactoring)

### Theme: Nebula Void

- "Nebula Assembly" aesthetic
- Responsive CSS Grid layout
- Dark theme optimized
- Professional visual design

## Configuration

Settings are managed via Pydantic models and stored in `~/.aura/config.json`:

```json
{
  "api_keys": {
    "nvidia": "nvapi-...",
    "google": "AIzaSy...",
    "openai": "sk-...",
    "anthropic": "sk-ant-..."
  },
  "default_model": "openai/nvidia/llama-3.3-nemotron-super-49b-v1",
  "theme_name": "default",
  "use_keyring": false
}
```

**Modelo padrão:** `openai/nvidia/llama-3.3-nemotron-super-49b-v1` (NVIDIA Nemotron Super 49B).
Outros modelos suportados: `gemini/gemini-2.5-flash`, `cerebras/gpt-oss-120b`, `gpt-4o`, `claude-sonnet-4-6`, `openrouter/nvidia/nemotron-3-super-120b-a12b:free`.

## Extension Points

### 1. Custom Tools
Implement and register via `ServiceRegistry`:
```python
from aura_cli.core.service_registry import get_service_registry

registry = get_service_registry()
registry.register_tool("my_tool", my_function, schema)
```

### 2. Custom Skills
Add `.md` files to `aura_cli/consciousness/skills/` with YAML frontmatter.

### 3. Custom Agents
Add `.md` files to `aura_cli/consciousness/agents/` with YAML frontmatter.

### 4. Plugins
Use the extension system in `core/extensions/`:
```python
from aura_cli.core.extensions import AuraExtension


class MyExtension(AuraExtension):
    def on_load(self):
        # Initialize extension
        pass
```

## Best Practices

### When Using Aura CLI

1. **Be Specific**: Clear, specific requests get better results
2. **Use Appropriate Agent**: Use `/agi` for complex projects, `/ops` for DevOps tasks
3. **Leverage Tools**: Let the agent use tools automatically
4. **Review Changes**: Always review code changes before accepting
5. **Use Sessions**: Save context for complex multi-step tasks
6. **Monitor Resources**: Use `/ops` to monitor system resources

### When Extending Aura CLI

1. **Follow Patterns**: Use existing patterns for consistency
2. **Type Hints**: Always use type hints (PEP 561)
3. **Documentation**: Write comprehensive docstrings
4. **Tests**: Write tests for new features
5. **Error Handling**: Use structured exceptions (`AuraError`)
6. **Performance**: Consider caching and optimization

## Project Statistics

- **200+ Python files** with professional docstrings
- **68+ tools** integrated
- **18 TUI widgets** for rich terminal interface
- **3 specialized agents** (Chat, AGI, Ops)
- **3 skills** in knowledge base
- **3 agent personas** defined
- **105+ UI tests** + **74 test files** covering all modules
- **Fully typed** with PEP 561 (`py.typed`)
- **Zero warnings** in native code

## Technology Stack

- **Python 3.10+**
- **Rich** - Rich text and beautiful formatting
- **Textual** - Terminal UI framework
- **LiteLLM** - Unified LLM API abstraction
- **Pydantic** - Type validation and configuration
- **SentenceTransformers** - Semantic embeddings
- **AutoGen** - Multi-agent orchestration
- **NetworkX** - Dependency graph analysis
- **asyncio** - Asynchronous operations

## Contact & Support

- **Creator**: Luan Dev
- **Email**: luan@udesc.br
- **Project**: Aura CLI
- **Version**: 0.1.0

---

*This knowledge base is maintained as part of the Aura CLI consciousness system. For the most up-to-date information, refer to the project documentation and source code.*
