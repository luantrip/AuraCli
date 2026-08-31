# Environment Variables — Aura CLI

All environment variables supported by Aura CLI.

---

## API Keys

| Variable | Provider | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Google Gemini | Google AI Studio API key |
| `GEMINI_API_KEY` | Google Gemini | Alias for `GOOGLE_API_KEY` (synchronised automatically) |
| `OPENAI_API_KEY` | OpenAI | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic | Anthropic API key (Claude) |
| `OPENROUTER_API_KEY` | OpenRouter | OpenRouter API key (access to 13+ models) |
| `NVIDIA_API_KEY` | NVIDIA | NVIDIA NIM API key |
| `XAI_API_KEY` | xAI | xAI API key (Grok) |

> API keys are preferentially stored via the OS keyring (configurable at
> `/settings`). Environment variables are used as fallback.

---

## Application Behaviour

| Variable | Values | Default | Description |
|---|---|---|---|
| `AURA_USE_ADK_BRIDGE` | `1`, `true` | unset | Enable the ADK bridge (`ADKBridgeFactory`) instead of the native backend |
| `AURA_ACCESSIBLE` | `1`, `true` | unset | Explicitly enable accessibility output; disabled by default and never starts an external reader |
| `AURA_ACCESSIBILITY_DEVICE` | `auto`, `screen_reader`, `high_contrast`, `keyboard_only` | `auto` | Declares the compatible device/profile; informational unless accessibility is enabled |
| `AURA_SCREEN_READER` | executable name/path | unset | Optional reader selected for manual use; Aura never launches it automatically |
| `AURA_SKIP_SPLASH` | `1`, `true` | unset | Skip the splash/onboarding screen at startup |
| `AURA_ASCII_MODE` | `1`, `true` | unset | Force ASCII mode (no Unicode/emojis) — useful for limited terminals |
| `AURA_HEADLESS` | `1`, `true` | unset | Headless mode (no interactive UI) — for scripts and CI |
| `AURA_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | Application log level |
| `AURA_LOG_FILE` | path | `~/.aura/logs/aura.log` | Log file path |

---

## Model Configuration

| Variable | Description |
|---|---|
| `AURA_DEFAULT_MODEL` | Default model (e.g. `gemini/gemini-2.5-flash`, `gpt-4o`) |
| `AURA_CONSCIOUSNESS_THRESHOLD` | Skill relevance threshold (0.1–0.9, default: 0.35) |

---

## Infrastructure and Paths

| Variable | Description |
|---|---|
| `AURA_HOME` | Base directory for user data (default: `~/.aura/`) |
| `AURA_PROJECT_ROOT` | Project root directory (default: current directory) |
| `AURA_MEMORY_DIR` | Persistent memory directory (default: `./memory/`) |
| `AURA_EXTENSIONS_DIR` | Custom extensions directory (default: `./extensions/`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON (used by `GCPManager`) |
| `AZURE_CLIENT_ID` | Azure authentication client ID |
| `AZURE_TENANT_ID` | Azure authentication tenant ID |
| `AZURE_CLIENT_SECRET` | Azure authentication client secret |

---

## Development and Debug

| Variable | Description |
|---|---|
| `AURA_DEV_MODE` | Enable development mode (verbose logs, no confirmations) |
| `AURA_DISABLE_RATE_LIMIT` | Disable rate limiting (for tests only) |
| `AURA_BOOT_TIMEOUT` | Boot timeout in seconds (default: 10) |

---

## Usage Examples

```bash
# Set API key and default model
export GOOGLE_API_KEY="your-key-here"
export AURA_DEFAULT_MODEL="gemini/gemini-2.5-flash"

# Headless mode for CI
AURA_HEADLESS=1 AURA_SKIP_SPLASH=1 aura

# Debug with verbose logging
AURA_LOG_LEVEL=DEBUG aura

# Use ADK Bridge
AURA_USE_ADK_BRIDGE=1 aura

# Opt-in accessibility output for a compatible device
AURA_ACCESSIBLE=1 AURA_ACCESSIBILITY_DEVICE=screen_reader aura
```

Accessibility can also be persisted in `config.json`:

```json
{
  "accessibility": {
    "enabled": true,
    "device": "screen_reader",
    "screen_reader": "voiceover"
  }
}
```

The `screen_reader` value is metadata for a manually managed device. Aura does
not detect, launch, or attach to accessibility software during startup.

---

## Configuration Precedence

1. Environment variables (highest priority)
2. `PydanticConfig` (`~/.aura/config.json`)
3. `SecureConfig` (OS keyring)
4. Application defaults

---

*Aura CLI — Environment Variables — v0.1.0 — 2026*
