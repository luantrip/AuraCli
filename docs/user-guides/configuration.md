# ⚙️ Configuration Guide - Aura CLI

Complete guide to configuring Aura CLI for your needs.

---

## 📁 Configuration Files

### Main Config File

**Location**: `~/.aura/config.json`

**Structure**:
```json
{
    "api_keys": {
        "google": "<managed-by-keyring-or-environment>",
        "openai": "<managed-by-keyring-or-environment>",
        "anthropic": "<managed-by-keyring-or-environment>"
    },
    "default_model": "gemini/gemini-2.5-flash",
    "theme_name": "default",
    "workers": {
        "agi": {
            "timeout": 300,
            "max_retries": 3,
            "use_adk_bridge": true
        },
        "ops": {
            "timeout": 60,
            "max_retries": 2
        }
    },
    "tools": {
        "auto_confirm": false,
        "confirm_destructive": true
    },
    "ui": {
        "show_animations": true,
        "compact_mode": false
    }
}
```

### Project Config

**Location**: `.aura/config.json` (project-specific)

Overrides user config for specific projects. The active project root is canonicalized for workspace-scoped sessions, memory and file tools; paths that resolve outside it are rejected by the corresponding contracts.

---

## 🔑 API Keys

### Setting API Keys

#### Via Settings Menu

```
› /settings
```

Follow prompts to add API keys.

#### Via Environment Variables

```bash
export AURA__API_KEYS__GOOGLE=your-key
export AURA__API_KEYS__OPENAI=your-key
export AURA__API_KEYS__ANTHROPIC=your-key
```

#### Via Config File

Use the settings flow or environment variables as the preferred paths. The JSON shape above is a schema illustration, not an invitation to paste live secrets into source-controlled files.

### Security contract

- The OS keyring is the default secure backend. The exact backend depends on the platform, such as Keychain, Secret Service or Windows Credential Manager.
- If the secure backend is unavailable, Aura fails closed instead of silently downgrading to plaintext persistence. An insecure backend is available only through an explicit opt-in intended for controlled local scenarios.
- Never commit keys to version control, include them in issue reports, or place them in project artifacts.
- Use environment variables in CI/CD and clean them from diagnostic output.
- A missing provider key is reported as unavailable; no real provider is contacted by the offline test gate.

---

## 🤖 Model Configuration

### Default Model

```json
{
    "default_model": "gemini/gemini-2.5-flash"
}
```

### Supported Models

| Provider | Models |
|----------|--------|
| **Google** | `gemini/gemini-2.5-flash` (default), `gemini/gemini-2.5-pro`, `gemini/gemini-2.0-flash` |
| **Cerebras** | `cerebras/gpt-oss-120b`, `cerebras/zai-glm-4.7`, `cerebras/llama3.1-8b` |
| **OpenRouter** | `openrouter/free`, `openrouter/nvidia/nemotron-3-super-120b-a12b:free`, `openrouter/qwen/qwen3-coder:free` |
| **NVIDIA** | `nvidia/nvidia/nemotron-3-super-120b-a12b`, `nvidia/nvidia/nemotron-3-ultra-550b-a55b` |
| **OpenAI** | `gpt-4o`, `gpt-4o-mini` |
| **Anthropic** | `claude-sonnet-4-6` |

### Model Selection

```bash
# Interactive selection
› /model

# Or set in config
{
    "default_model": "gemini/gemini-2.5-flash"
}
```

### Fallback Configuration

```json
{
    "models": {
        "primary": "gemini/gemini-2.5-flash",
        "fallback": ["cerebras/gpt-oss-120b", "openrouter/free", "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b"]
    }
}
```

---

## 🎨 UI Configuration

### CLI Themes

Themes for the command-line interface:

```json
{
    "theme_name": "default"
}
```

Available CLI themes:
- `default` - Professional default theme
- `minimal` - Minimalist with thin typography
- `light-minimal` - Light version for bright screens
- `ultra-minimal` - Extreme monochrome theme

### TUI Themes

Themes for the Terminal UI (Textual interface) are configured separately when using TUI mode:

Available TUI themes:
- `nebula-dark` - Dark nebula theme (default for TUI)
- `nebula-light` - Light nebula theme
- `dracula` - Dracula theme
- `midnight` - Midnight theme

**Note**: TUI themes are only available when using `/tui` mode. CLI themes apply to the interactive command-line interface.

### UI Settings

```json
{
    "ui": {
        "show_animations": true,
        "compact_mode": false,
        "show_footer": true,
        "footer_height": 3
    }
}
```

---

## 👷 Worker Configuration

### AGI Worker

```json
{
    "workers": {
        "agi": {
            "timeout": 300,
            "max_retries": 3,
            "use_adk_bridge": true,
            "planning_enabled": true,
            "parallel_execution": true
        }
    }
}
```

### Ops Worker

```json
{
    "workers": {
        "ops": {
            "timeout": 60,
            "max_retries": 2,
            "confirm_destructive": true
        }
    }
}
```

---

## 🛠️ Tool Configuration

### Auto Confirm

```json
{
    "tools": {
        "auto_confirm": false,
        "confirm_destructive": true,
        "confirm_file_writes": true
    }
}
```

### Tool Timeouts

```json
{
    "tools": {
        "timeouts": {
            "shell_command": 30,
            "web_search": 10,
            "docker": 60
        }
    }
}
```

---

## 📝 Logging Configuration

### Log Levels

```json
{
    "logging": {
        "level": "INFO",
        "file": "~/.aura/logs/aura.log",
        "max_size": "10MB",
        "backup_count": 5
    }
}
```

### Environment Variable

```bash
export AURA_LOG_LEVEL=DEBUG
```

---

## 💾 Cache Configuration

### Cache Settings

```json
{
    "cache": {
        "enabled": true,
        "ttl": 3600,
        "max_size": "100MB",
        "persistent": true
    }
}
```

### Cache Locations

- `~/.aura/cache/` - User cache
- `.aura/cache/` - Project cache

---

## 🔐 Security Configuration

### Keyring

API keys are stored in OS keyring by default:

- **macOS**: Keychain
- **Linux**: Secret Service (GNOME Keyring, KWallet)
- **Windows**: Windows Credential Manager

### Disable Keyring

```json
{
    "security": {
        "use_keyring": false,
        "encrypt_config": true
    }
}
```

---

## 🌍 Environment Variables

### Complete List

```bash
# API Keys
export AURA__API_KEYS__GOOGLE=your-key
export AURA__API_KEYS__OPENAI=your-key
export AURA__API_KEYS__ANTHROPIC=your-key

# Model
export AURA__DEFAULT_MODEL=gpt-4

# Workers
export AURA_USE_ADK_BRIDGE=true
export AURA_WORKER_TIMEOUT=300

# Logging
export AURA_LOG_LEVEL=INFO

# UI (CLI themes only)
export AURA_THEME=default
export AURA_COMPACT_MODE=false
```

---

## 📊 Configuration Priority

Configuration is loaded in this order (later overrides earlier):

1. **Default values** (hardcoded)
2. **User config file** (`~/.aura/config.json`)
3. **Project config file** (`.aura/config.json`)
4. **Environment variables**
5. **Command-line arguments**

---

## 🔍 Verifying Configuration

### Check Current Config

```
› /settings
```

### View Config File

```bash
cat ~/.aura/config.json
```

### Test Configuration

```python
from aura_cli.core.config import config_manager

# Get config value
model = config_manager.get("default_model")
print(f"Current model: {model}")

# Check if key exists
if config_manager.has("api_keys.google"):
    print("Google API key is set")
```

---

## 🛠️ Advanced Configuration

### Custom Tool Registration

```python
from aura_cli.core.service_registry import get_service_registry

registry = get_service_registry()

# Register custom tool
registry._register_tool(
    name="my_tool",
    category=ToolCategory.DEVELOPMENT,
    description="My custom tool",
    function=my_tool_function,
    schema={...}
)
```

### Custom Agent Configuration

```json
{
    "agents": {
        "custom_agent": {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2048,
            "tools": ["read_file", "write_file"]
        }
    }
}
```

---

## 🔗 Related Documentation

- [Quick Start](./quick-start.md) - Getting started
- [Workers Guide](./workers.md) - Worker configuration
- [API Reference](../reference/api.md) - API documentation

---

**Version**: 0.1.0
**Last Updated**: 2026
