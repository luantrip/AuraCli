# 🚀 Quick Start Guide - Aura CLI

Get up and running with Aura CLI in minutes!

---

## 📦 Installation

### Option 1: From Source

```bash
# Clone the repository
git clone https://github.com/luantrip/AuraCli.git
cd AuraCli

# Install with pip
pip install -e .
```

### Option 2: From a local wheel

The project currently documents and validates source installation plus a locally built wheel. Build it with `python -m build --wheel --no-isolation` and install the resulting file in an isolated environment when needed. A public PyPI release is not assumed by this guide.

### Requirements

- Python 3.10 or higher
- pip

---

## ⚡ First Run

### 1. Start Aura CLI

```bash
aura
```

You'll see the welcome screen:

```
        ▄▀█ █░█ █▀█ ▄▀█    █▀▀ █░░ █
        █▀█ █▄█ █▀▄ █▀█    █▄▄ █▄▄ █

Welcome to Aura CLI!
Type /help to see all commands
```

### 2. Try Your First Command

```
› /help
```

This shows all available commands.

### 3. Configure API Keys (Optional)

If you want to use remote LLMs (GPT, Claude, Gemini, NVIDIA Nemotron, OpenRouter):

```
› /settings
```

Follow the prompts to add your API keys. The OS keyring is the default secure backend; if it is unavailable, Aura fails closed instead of silently writing plaintext.


---

## 🎯 Basic Usage

### Interactive Chat

Simply type your question:

```
› How do I create a REST API with FastAPI?
```

Aura CLI will:
1. Understand your request
2. Use appropriate tools
3. Generate code or provide guidance
4. Show results in a formatted way

### Slash Commands

Aura CLI supports slash commands for quick actions:

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show all commands | `/help` |
| `/agi` | Activate AGI agent | `/agi create a todo app` |
| `/ops` | Activate Ops agent | `/ops git status` |
| `/tools` | List all tools | `/tools` |
| `/tool <name>` | Show tool details | `/tool read_file` |
| `/model` | Select LLM model | `/model` |
| `/settings` | Open settings | `/settings` |
| `/todo` | Show to-do list | `/todo` |
| `/init` | Index project (generate context) | `/init` |
| `/context` | Select files for context | `/context` |
| `/notebook` | Show memory notebook info | `/notebook` |
| `/consolidate` | Consolidate learned rules | `/consolidate` |
| `/theme` | Change UI theme | `/theme minimal` |
| `/keyboard` | Show keyboard shortcuts | `/keyboard` |
| `/tools-menu` | Open interactive tools menu (TUI) | `/tools-menu` |
| `/session` | Manage sessions ⏳ | `/session save my_project` |
| `/workflow` | Manage workflows ⏳ | `/workflow run deploy` |
| `/cache` | Manage cache ⏳ | `/cache stats` |
| `/tui` | Switch to TUI mode ⏳ | `/tui` |
| `/clear` | Clear screen | `/clear` |
| `/exit` | Exit Aura CLI | `/exit` |

---

## 🤖 Using Agents

### AGI Agent (Project Manager)

The AGI agent is perfect for complex tasks:

```
› /agi create a REST API with authentication
```

The AGI agent will:
- Analyze your project structure
- Plan the implementation
- Execute tasks step by step
- Use appropriate tools
- Track progress in `.aura/to-do.md`

### Ops Agent (DevOps)

The Ops agent handles DevOps tasks:

```
› /ops git status
› /ops docker ps
› /ops check health
```

### Chat Mode (Default)

For general questions and assistance:

```
› How do I use Python decorators?
› Explain this code: [paste code]
› What's the best way to structure a FastAPI project?
```

---


---

## 🛠️ Using Tools

Aura CLI has an extensible integrated-tool catalog. Run `/tools` to inspect the active registry; the examples below show common categories.

### File Operations

```
› Read the file config.py
› List files in the current directory
› Find all Python files in the project
```

### Code Analysis

```
› Analyze the code in src/main.py
› Find all functions in this file
› Check for code issues
```

### Git Operations

```
› /ops git status
› /ops git commit "Add new feature"
› /ops git log
```

### Docker Operations

```
› /ops docker ps
› /ops docker logs container_name
› /ops docker build .
```

### List All Tools

```
› /tools
```

### Get Tool Details

```
› /tool read_file
› /tool analyze_code
```

---

## 📝 Example Workflows

### Example 1: Create a New Project

```
› /agi create a FastAPI project with user authentication
```

The AGI agent will:
1. Create project structure
2. Set up FastAPI
3. Add authentication
4. Create example endpoints
5. Add documentation

### Example 2: Analyze Existing Code

```
› Analyze the codebase and suggest improvements
```

Aura CLI will:
1. Scan your codebase
2. Identify issues
3. Suggest improvements
4. Provide refactoring recommendations

### Example 3: Refactor Code

```
› /agi refactor the user authentication module to use JWT tokens
```

The AGI agent will:
1. Analyze current implementation
2. Plan refactoring
3. Execute changes safely
4. Run tests
5. Update documentation

### Example 4: DevOps Tasks

```
› /ops check all services health
› /ops git create branch feature/new-api
› /ops docker restart services
```

---

## 🎨 TUI Mode (Terminal UI)

Aura CLI has a rich terminal UI mode:

### Start TUI Mode

From within Aura CLI:

```
› /tui
```

Or use the alternative command:

```
› /interface
```

### TUI Features

- **AuraPaint**: native ANSI art editor with layers and animation
- **File Manager**: Dual-pane file manager
- **Monitor**: Terminal browser (requires `aura-monitor` binary)
- **Command Palette**: Command palette (Ctrl+P)

### TUI Navigation

- `Ctrl+P` - Command palette
- `Ctrl+Space` - Leader key
- `Ctrl+C` - Exit
- `Ctrl+L` - Clear

---

## ⚙️ Configuration

### Config File Location

`~/.aura/config.json`

### Environment Variables

```bash
export AURA__API_KEYS__GOOGLE=your-key
export AURA__API_KEYS__OPENAI=your-key
export AURA__DEFAULT_MODEL=gpt-4
```

### Settings Menu

```
› /settings
```

Options:
- API keys management
- Default model selection
- Theme selection
- Auto mode settings
- Advanced options

---

## 📚 Next Steps

Now that you're up and running:

1. **Explore Tools**: Run `/tools` to see the active tool registry
2. **Try AGI Agent**: Use `/agi` for complex tasks
3. **Try Ops Agent**: Use `/ops` for DevOps tasks
4. **Read Documentation**:
   - [Architecture Guide](../architecture/system-architecture.md) - Understand the system
   - [API Reference](../reference/api.md) - Complete API docs
   - [Tools Guide](./tools.md) - All tools explained
   - [TUI Tools Guide](./tui-tools.md) - Terminal UI features

---

## 🆘 Getting Help

### Built-in Help

```
› /help
```

### Command Help

```
› /help agi
› /help ops
› /help tools
```

### Documentation

- [Full Documentation](../README.md)
- [Troubleshooting](./troubleshooting.md)

---

## 💡 Tips

1. **Use Slash Commands**: They're faster than typing full commands
2. **Try AGI for Complex Tasks**: It's designed for multi-step operations
3. **Use Ops for DevOps**: Specialized for Git, Docker, monitoring
4. **Explore Tools**: Run `/tools` regularly to discover new capabilities
5. **Check Settings**: Customize Aura CLI to your needs with `/settings`
6. **Configure API Keys**: Use `/settings` to add your API keys for best performance

---

## 🎯 Common Tasks

### Create a New Project

```
› /agi create a Python web application with FastAPI
```

### Analyze Code

```
› Analyze this code: [paste code]
```

### Refactor

```
› /agi refactor this module to improve performance
```

### DevOps

```
› /ops git status
› /ops docker ps
› /ops check health
```

### Get Information

```
› What tools are available for file operations?
› How do I use the code analysis tool?
› Show me examples of using the AGI agent
```

---

**Ready to go!** Start exploring Aura CLI and discover its powerful features.

For more detailed information, see the [full documentation](../README.md).

---

**Version**: 0.1.0
**Last Updated**: 2026

> **Note:** Commands marked with ⏳ in the table above are planned. The backend
> modules exist (`core/sessions/`, `core/workflows/`, `core/cache_advanced/`)
> but the CLI handlers are not yet wired.
