# 🧠 Memory Guide - Memory and Embeddings

Aura CLI provides advanced memory systems for maintaining context and semantic search.

---

## 📋 Overview

Aura CLI has multiple memory systems:

1. **ConversationMemory** - Conversation history
2. **VectorMemory** - Semantic search with embeddings
3. **PersistentMemory** - File-based persistence

---

## 💬 Conversation Memory

### Basic Usage

```python
from aura_cli.adk import ConversationMemory

memory = ConversationMemory(max_turns=50, max_tokens=8000)

# Add messages
memory.add_user_message("Hello!")
memory.add_assistant_message("Hi! How can I help?")

# Get context
context = memory.get_context()
```

### Features

- **Sliding Window** - Keeps recent messages
- **Token Limit** - Respects token limits
- **Auto-pruning** - Removes old messages automatically

---

## 🔍 Vector Memory (Semantic Search)

### Basic Usage

```python
from aura_cli.adk import VectorMemory

memory = VectorMemory()

# Add entries
await memory.add("Python is a programming language", {"topic": "programming"})
await memory.add("TypeScript adds types to JavaScript", {"topic": "programming"})

# Semantic search
results = await memory.search("What language has static types?", limit=5)
```

### Features

- **Semantic Search** - Find similar content
- **Embeddings** - Uses **fastembed** when installed (auto on Windows, Linux, macOS 11+); otherwise Chroma default embeddings on older macOS
- **Metadata** - Attach metadata to entries
- **Fast Retrieval** - Optimized vector search

---

## 💾 Persistent Memory

### Basic Usage

```python
from aura_cli.adk import PersistentMemory
from pathlib import Path

memory = PersistentMemory(Path("~/.aura/memory.json"))

# Use like any other memory
await memory.add("Important information")

# Auto-saves on add/delete
# Or manually save
memory.save()
```

### Features

- **File-based** - Persists to disk
- **Auto-save** - Saves automatically
- **JSON Format** - Human-readable

---

## 🎯 Use Cases

### Use Case 1: Maintain Context

```python
memory = ConversationMemory(max_turns=20)

# Throughout conversation
memory.add_user_message("Create a user model")
memory.add_assistant_message("I'll create a User model...")

# Later
memory.add_user_message("Add email validation")
# Context includes previous conversation
```

### Use Case 2: Code Knowledge Base

```python
memory = VectorMemory()

# Add code snippets
await memory.add("def authenticate_user(username, password): ...", {
    "file": "auth.py",
    "function": "authenticate_user"
})

# Search semantically
results = await memory.search("How do I authenticate users?")
```

### Use Case 3: Project Documentation

```python
memory = PersistentMemory(Path(".aura/memory.json"))

# Add project docs
await memory.add("This project uses FastAPI for the API layer")
await memory.add("Database is PostgreSQL with SQLAlchemy")

# Search later
results = await memory.search("What database does this project use?")
```

---

## 🔗 Related Documentation

- [ADK Guide](../developer-guides/adk-guide.md) - ADK memory systems
- [API Reference](../reference/api.md) - Memory APIs

---

**Version**: 0.1.0
**Last Updated**: 2026
