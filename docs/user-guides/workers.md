# 👷 Workers Guide - AGI and Ops Workers

Aura CLI uses specialized workers to handle complex tasks in the background. This guide explains how AGI and Ops workers work.

---

## 📋 Overview

Aura CLI has two main workers:

1. **AgiWorker** - Project management and complex development tasks
2. **OpsWorker** - DevOps operations and infrastructure management

Both workers run in background threads and communicate via queues.

---

## 🤖 AGI Worker

### Purpose

The AGI (Artificial General Intelligence) worker handles:
- Complex multi-step tasks
- Project planning and analysis
- Code generation and refactoring
- Strategic decision making
- Tool orchestration

### Activation

```bash
# From Aura CLI
› /agi create a REST API with authentication

# Or programmatically
from aura_cli.cli.workers import AgiWorker

worker = AgiWorker(prompt="create API", model="gpt-4", api_keys={...})
worker.start()
```

### How It Works

```
User Input → AgiWorker
    ↓
Planning Phase
    ↓
Task Decomposition
    ↓
Tool Execution (active registry)
    ↓
Result Aggregation
    ↓
Status Updates (via queue)
    ↓
Final Result
```

### Features

#### Planning System
- **Problem Decomposition** - Breaks complex tasks into steps
- **Task Planning** - Creates execution plan
- **Task Validation** - Validates plan before execution
- **Parallel Execution** - Runs independent tasks in parallel

#### Agent System
- **CodeAgent** - Code generation and manipulation
- **ReviewAgent** - Code review and analysis
- **RefactorAgent** - Code refactoring
- **TestAgent** - Test generation
- **OpsCodeAgent** - DevOps operations

#### Tool Integration
- Automatically selects appropriate tools
- Orchestrates multiple tools
- Handles tool errors gracefully
- Provides progress updates

### Status Updates

The worker sends status updates via `status_queue`:

```python
# Status update format
{
    "type": "task_update",
    "task_id": "task_123",
    "status": "running",
    "message": "Analyzing project structure...",
    "progress": 0.5
}
```

### Example Workflow

```
User: /agi create a FastAPI project with authentication

1. Planning Phase
   - Analyze requirements
   - Create task plan
   - Validate plan

2. Execution Phase
   - Create project structure
   - Generate FastAPI code
   - Add authentication
   - Create tests
   - Update documentation

3. Completion
   - Aggregate results
   - Show summary
   - Save to .aura/to-do.md
```

### Configuration

```python
# Feature flag for ADK Bridge
USE_ADK_BRIDGE = os.getenv("AURA_USE_ADK_BRIDGE", "true").lower() == "true"

# If enabled, uses ADK agents
# If disabled, uses legacy agents
```

---

## 🔧 Ops Worker

### Purpose

The Ops worker handles:
- Git operations
- Docker management
- System monitoring
- Infrastructure operations
- CI/CD tasks

### Activation

```bash
# From Aura CLI
› /ops git status
› /ops docker ps
› /ops check health

# Or programmatically
from aura_cli.cli.workers import OpsWorker

worker = OpsWorker(prompt="git status", model="gpt-4", api_keys={...})
worker.start()
```

### How It Works

```
User Input → OpsWorker
    ↓
Parse Command (natural language or direct)
    ↓
Select Ops Tool
    ↓
Execute Tool
    ↓
Format Result
    ↓
Return to User
```

### Features

#### Git Operations
- `git_status` - Repository status
- `git_diff` - Show tracked/staged differences
- `git_diff_context` - Show the complete bounded workspace snapshot, including readable untracked files
- `git_log` - Commit history
- `git_branch` - Branch management
- `git_commit` - Create commits
- `git_commit_smart` - Smart commits
- `git_smart` - Natural language Git

#### Docker Operations
- `docker_ps` - List containers
- `docker_images` - List images
- `docker_logs` - Container logs
- `docker_exec` - Execute in container
- `docker_build` - Build images
- `docker_compose` - Compose operations

#### Monitoring
- `check_service_health` - Health checks
- `check_port` - Port checking
- `system_resources` - System metrics
- `process_info` - Process information

#### Infrastructure
- Kubernetes management
- Terraform operations
- Cloud provider integration (AWS, GCP, Azure)
- Infrastructure as Code

#### Security
- Vulnerability scanning
- Security auditing
- Access control
- Secret management

### Natural Language Processing

The Ops worker understands natural language:

```
› /ops git create a new branch for the API feature
› /ops docker show me logs from the last hour
› /ops check if port 8000 is open
```

### Example Workflow

```
User: /ops git create branch and commit changes

1. Parse Command
   - Understand "create branch"
   - Understand "commit changes"

2. Execute
   - git_branch(action="create", name="feature/new")
   - git_status() to see changes
   - git_commit(message="Add new feature")

3. Result
   - Show branch created
   - Show commit created
   - Display summary
```

---

## 🔄 Worker Communication

### Status Queue

Workers communicate via `status_queue`:

```python
from queue import Queue

status_queue = Queue()

# Worker sends updates
status_queue.put({
    "type": "task_start",
    "task_id": "task_123",
    "message": "Starting task..."
})

# UI receives updates
while True:
    update = status_queue.get()
    # Display update to user
```

### Event System

Workers emit events:

```python
from aura_cli.core.events.agi_events import (
    create_task_start,
    create_task_update,
    create_task_complete
)

# Create event
event = create_task_start(
    task_id="task_123",
    description="Create API",
    objective="Build REST API"
)

# Emit event
status_queue.put(event)
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Enable/disable ADK Bridge
export AURA_USE_ADK_BRIDGE=true

# Worker settings
export AURA_WORKER_TIMEOUT=300
export AURA_WORKER_MAX_RETRIES=3
```

### Worker Settings

```python
# In config.json
{
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
    }
}
```

---

## 🎯 Best Practices

### For AGI Worker

1. **Be Specific**: Provide clear objectives
2. **Break Down Tasks**: Complex tasks work better when broken down
3. **Monitor Progress**: Check status updates
4. **Review Results**: Always review generated code
5. **Use To-Do Tracking**: Check `.aura/to-do.md` for task list

### For Ops Worker

1. **Use Natural Language**: Describe what you want
2. **Check Before Execute**: Review what will be executed
3. **Use Smart Commits**: Let it generate commit messages
4. **Monitor Services**: Regular health checks
5. **Secure Operations**: Be careful with destructive operations

---

## 🔍 Troubleshooting

### Worker Not Starting

```python
# Check if worker thread is running
if worker.is_alive():
    print("Worker is running")
else:
    print("Worker is not running")
```

### No Status Updates

```python
# Check status queue
if not status_queue.empty():
    update = status_queue.get()
    print(update)
```

### Tool Execution Fails

```python
# Check tool registry
from aura_cli.core.service_registry import get_service_registry

registry = get_service_registry()
tool = registry.get_tool("tool_name")
if tool:
    print(f"Tool found: {tool.description}")
else:
    print("Tool not found")
```

---

## 📚 Related Documentation

- [Tools Guide](./tools.md) - All available tools
- [ADK Guide](../developer-guides/adk-guide.md) - Agent Development Kit
- [Application Layer](../architecture/application-layer.md) - Agent orchestration
- [Quick Start](./quick-start.md) - Getting started

---

**Version**: 0.1.0
**Last Updated**: 2026
