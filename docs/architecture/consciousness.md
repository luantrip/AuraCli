# 🧠 Consciousness Guide - Skills and Agents

Aura CLI's consciousness system provides RAG-based knowledge retrieval and specialist agents.

---

## 📋 Overview

The consciousness system includes:
- **Skill Retriever** - Semantic skill matching
- **Agent Runner** - Specialist agent execution
- **Skills** - Knowledge base (markdown files)
- **Agents** - Specialist personas (markdown files)

---

## 📚 Skills

### What are Skills?

Skills are markdown files that provide knowledge to the LLM. They're retrieved using semantic search (RAG).

### Location

```
aura_cli/consciousness/skills/your-skill.md
```

### Structure

```markdown
---
name: Your Skill Name
description: Detailed description with keywords
version: 1.0.0
author: Your Name
---

# Skill Title

Content explaining the topic...
```

### Using Skills

Skills are automatically retrieved when relevant:

```
› How do I use Python decorators?
```

The system will:
1. Search skills semantically
2. Find relevant skill
3. Include in LLM context
4. Provide accurate answer

---

## 🤖 Agents

### What are Agents?

Agents are specialist personas that can be invoked for specific tasks.

### Location

```
aura_cli/consciousness/agents/your-agent.md
```

### Structure

```markdown
---
name: your-agent-name
description: When to use this agent
model: sonnet
allowed-tools: Read, Write, Grep
---

You are a [specialist role]. Your task is to [main objective].

## Process

1. Step One
2. Step Two
3. Step Three
```

### Using Agents

Agents are automatically selected when appropriate, or can be invoked directly.

---

## 🔍 Skill Retriever

### Finding Skills

```python
from aura_cli.consciousness import get_skill_retriever

retriever = get_skill_retriever()

# Find relevant skill
content = retriever.find_relevant_skill("How do I manage Python environments?")

# Find with match details
match = retriever.find_best_match(query, threshold=0.4)

# Find multiple matches
matches = retriever.find_all_matches(query, limit=5, threshold=0.3)
```

---

## 🏃 Agent Runner

### Running Agents

```python
from aura_cli.consciousness import get_agent_runner

runner = get_agent_runner()

# Run agent
result = await runner.run(
    agent_name="code-refactor-agent",
    input_data="def foo(x): return x+1",
    llm_query=my_llm_function
)
```

---

## 🔗 Related Documentation

- [Plugin Development](../developer-guides/plugins.md) - Creating skills and agents
- [ADK Guide](../developer-guides/adk-guide.md) - Agent development

---

**Version**: 0.1.0
**Last Updated**: 2026
