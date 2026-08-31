# 🔧 Troubleshooting Guide

Common issues and solutions for Aura CLI.

---

## ❌ Common Issues

### Issue: API Key Not Working

**Symptoms**:
- "Invalid API key" error
- Model not responding

**Solutions**:
1. Check API key in settings: `/settings`
2. Verify key is valid on provider website
3. Check key has correct permissions
4. Try regenerating key

---

### Issue: Model Not Responding

**Symptoms**:
- Timeout errors
- No response from model

**Solutions**:
1. Check internet connection
2. Try different model: `/model`
3. Check rate limits
4. Enable fallback models

---

### Issue: Tool Execution Fails

**Symptoms**:
- "Tool not found" error
- Tool execution timeout

**Solutions**:
1. Check tool exists: `/tools`
2. Verify tool parameters
3. Check file permissions
4. Review tool logs
5. Try tool directly: `/tool <name>`

---

### Issue: Worker Not Starting

**Symptoms**:
- AGI/Ops worker doesn't start
- No status updates

**Solutions**:
1. Check worker configuration
2. Verify API keys are set
3. Check logs: `~/.aura/logs/`
4. Restart Aura CLI
5. Check environment variables

---

### Issue: TUI Not Loading

**Symptoms**:
- TUI doesn't start
- Blank screen

**Solutions**:
1. Check terminal compatibility
2. Verify Textual is installed
3. Try CLI mode: `aura` (use `/tui` command from within CLI to access TUI)
4. Check terminal size
5. Update Textual: `pip install --upgrade textual`

---

### Issue: `pip install -e .` fails on fastembed / onnxruntime

**Symptoms**:
- `ResolutionImpossible` mentioning `fastembed` and `onnxruntime>=1.17`
- Only on **macOS 10.15 (Catalina)** or very old systems

**Cause**:
- `fastembed` requires `onnxruntime>=1.17`; PyPI has no compatible wheel for Catalina.

**Solutions**:
1. Use Aura **0.1.0+** `pyproject.toml`: default install **skips** fastembed on Darwin `< 20` (macOS 10.x).
2. Run only `pip install -e .` — **do not** use `pip install -e ".[embeddings]"` on Catalina.
3. Upgrade to macOS 11+ (or use Linux/Windows) for automatic fastembed install.
4. See [optional-deps](../reference/optional-deps.md).

---

### Issue: Import Errors

**Symptoms**:
- "Module not found" errors
- Import failures

**Solutions**:
1. Reinstall dependencies: `pip install -e .`
2. Check Python version: `python --version` (needs 3.10+)
3. Verify virtual environment
4. Check PYTHONPATH
5. Clear cache: `rm -rf __pycache__`

---

## 🔍 Debugging

### Enable Debug Logging

```bash
export AURA_LOG_LEVEL=DEBUG
aura
```

### Check Logs

```bash
# View latest log
tail -f ~/.aura/logs/aura_$(date +%Y%m%d).log

# Search logs
grep "ERROR" ~/.aura/logs/*.log
```

### Verbose Mode

```bash
aura --verbose
```

---

## 🆘 Getting Help

### Built-in Help

```
› /help
```

### Check Status

```
› /status
```

### Report Issue

1. Check logs
2. Gather error messages
3. Create GitHub issue
4. Include:
   - Error message
   - Steps to reproduce
   - System information
   - Log excerpts

---

## 🔗 Related Documentation

- [Configuration](./configuration.md) - Configuration issues
- [Quick Start](./quick-start.md) - Setup help

---

**Version**: 0.1.0
**Last Updated**: 2026
