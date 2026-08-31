# 🔄 User Workflows Guide

Aura CLI provides a workflow system for creating and executing multi-step automation workflows defined in YAML.

> **Note:** The `/workflow` CLI commands are planned. The backend module exists
> at `core/workflows/` but the CLI handler is not yet wired. The API described
> here reflects the intended interface.

---

## 📋 Overview

User Workflows enable you to:
- Create multi-step automation workflows
- Define dependencies between steps
- Use variables and templates
- Handle errors gracefully
- Retry failed steps automatically
- Execute workflows on demand

---

## 💾 Creating Workflows

### Method 1: YAML Files (Recommended)

Workflows are stored as YAML files in `~/.aura/workflows/`. Create a new file:

```yaml
# ~/.aura/workflows/deploy.yaml
id: deploy_001
name: deploy
description: Deploy application to production
tags:
  - deployment
  - production

variables:
  ENV: production
  VERSION: latest

steps:
  - id: test
    type: shell
    command: pytest
    description: Run tests
    timeout: 300
    on_error: stop

  - id: build
    type: shell
    command: docker build -t app:${VERSION} .
    dependencies:
      - test
    description: Build Docker image
    timeout: 600
    on_error: stop

  - id: deploy
    type: shell
    command: docker push app:${VERSION}
    dependencies:
      - build
    description: Push to registry
    timeout: 300
    retries: 2
    on_error: retry
```

### Method 2: Programmatic API

> **Note:** `aura_cli.core.workflows` is internal API and subject to change
> without notice. Prefer YAML-based workflows for stability.

```python
# Internal API — subject to change
from aura_cli.core.workflows import get_workflow_manager  # noqa: internal

manager = get_workflow_manager()

workflow = manager.create_workflow(
    name="deploy",
    description="Deploy application",
    steps=[
        {
            "id": "test",
            "type": "shell",
            "command": "pytest",
            "dependencies": [],
        },
        {
            "id": "build",
            "type": "shell",
            "command": "docker build -t app .",
            "dependencies": ["test"],
        },
    ],
    variables={"VERSION": "latest"},
    tags=["deployment"],
)
```

---

## 🎯 Step Types

### Shell Steps

Execute shell commands:

```yaml
steps:
  - id: install
    type: shell
    command: pip install -r requirements.txt
    timeout: 300
```

### Tool Steps

Execute Aura CLI tools:

```yaml
steps:
  - id: analyze
    type: tool
    command: analyze_code
    parameters:
      file_path: src/main.py
```

### AGI Steps

Run AGI agent tasks:

```yaml
steps:
  - id: refactor
    type: agi
    command: refactor the authentication module
    parameters:
      model: gemini/gemini-2.5-flash
```

### Ops Steps

Execute DevOps operations:

```yaml
steps:
  - id: git_commit
    type: ops
    command: git commit -m "Deploy ${VERSION}"
```

### Command Steps

Execute Aura CLI slash commands:

```yaml
steps:
  - id: init
    type: command
    command: /init
```

---

## 🔗 Dependencies

Steps can depend on other steps:

```yaml
steps:
  - id: test
    type: shell
    command: pytest

  - id: build
    type: shell
    command: docker build .
    dependencies:
      - test  # Build only runs after test succeeds

  - id: deploy
    type: shell
    command: docker push
    dependencies:
      - build  # Deploy only runs after build succeeds
```

Dependencies ensure steps execute in the correct order.

---

## 📝 Variables

### Workflow Variables

Define variables at the workflow level:

```yaml
variables:
  VERSION: "1.0.0"
  ENV: "production"

steps:
  - id: build
    type: shell
    command: docker build -t app:${VERSION} .
```

### Step Result Variables

Reference results from previous steps:

```yaml
steps:
  - id: get_version
    type: shell
    command: git describe --tags

  - id: build
    type: shell
    command: docker build -t app:${get_version.result} .
    dependencies:
      - get_version
```

### Environment Variables

Use environment variables:

```yaml
steps:
  - id: deploy
    type: shell
    command: deploy.sh ${HOME}/app
```

---

## ⚙️ Step Configuration

### Timeout

Set maximum execution time:

```yaml
steps:
  - id: long_task
    type: shell
    command: long_running_script.sh
    timeout: 3600  # 1 hour
```

### Retries

Automatically retry failed steps:

```yaml
steps:
  - id: network_task
    type: shell
    command: curl https://api.example.com
    retries: 3
    timeout: 60
```

### Error Handling

Control behavior on errors:

```yaml
steps:
  - id: optional_step
    type: shell
    command: optional_script.sh
    on_error: continue  # Continue even if this fails

  - id: critical_step
    type: shell
    command: critical_script.sh
    on_error: stop  # Stop workflow on failure (default)

  - id: retry_step
    type: shell
    command: flaky_script.sh
    on_error: retry  # Retry on failure
    retries: 3
```

Options:
- `stop`: Stop workflow execution (default)
- `continue`: Continue to next step
- `retry`: Retry the step (requires `retries` > 0)

### Conditions

Execute steps conditionally:

```yaml
steps:
  - id: check_env
    type: shell
    command: echo ${ENV}

  - id: deploy_prod
    type: shell
    command: deploy_prod.sh
    dependencies:
      - check_env
    condition: "${check_env.result} == 'production'"
```

---

## 🚀 Executing Workflows

### Via CLI

```bash
# List workflows
› /workflow list

# Run workflow
› /workflow run deploy

# Show workflow info
› /workflow info deploy

# Delete workflow
› /workflow delete deploy
```

### Via API

> **Note:** This is internal API and subject to change. See YAML approach above
> for the stable workflow definition method.

```python
# Internal API — subject to change
from aura_cli.core.workflows import get_workflow_manager  # noqa: internal

manager = get_workflow_manager()

# Execute workflow
results = manager.execute_workflow(
    workflow_id="deploy_001",
    variables={"VERSION": "2.0.0"},
    dry_run=False,
)

# Check results
for step_id, result in results.items():
    print(f"{step_id}: {result['status']}")
    if result['status'] == 'failed':
        print(f"  Error: {result['error']}")
```

---

## 📊 Workflow Execution

### Execution Flow

```
1. Load workflow definition
2. Resolve dependencies (topological sort)
3. For each step in order:
   a. Check dependencies completed
   b. Evaluate condition (if present)
   c. Substitute variables
   d. Execute step
   e. Handle errors based on on_error policy
   f. Retry if needed
4. Return results
```

### Result Format

```python
{
    "step_1": {
        "status": "completed",
        "output": "...",
        "exit_code": 0,
        "started_at": "2024-12-06T10:00:00",
        "completed_at": "2024-12-06T10:00:05",
    },
    "step_2": {
        "status": "failed",
        "error": "Command failed",
        "exit_code": 1,
        "started_at": "2024-12-06T10:00:05",
        "completed_at": "2024-12-06T10:00:10",
    },
}
```

---

## 📝 Example Workflows

### Development Workflow

```yaml
name: dev-setup
description: Setup development environment

steps:
  - id: install_deps
    type: shell
    command: pip install -r requirements.txt

  - id: run_tests
    type: shell
    command: pytest
    dependencies:
      - install_deps

  - id: lint
    type: shell
    command: flake8 .
    dependencies:
      - install_deps
    on_error: continue
```

### Deployment Workflow

```yaml
name: deploy
description: Deploy to production

variables:
  VERSION: "latest"

steps:
  - id: test
    type: shell
    command: pytest
    timeout: 300

  - id: build
    type: shell
    command: docker build -t app:${VERSION} .
    dependencies:
      - test
    timeout: 600

  - id: push
    type: shell
    command: docker push app:${VERSION}
    dependencies:
      - build
    retries: 2

  - id: deploy
    type: ops
    command: deploy app:${VERSION}
    dependencies:
      - push
```

### Code Review Workflow

```yaml
name: review
description: Automated code review

steps:
  - id: analyze
    type: tool
    command: analyze_code
    parameters:
      file_path: src/main.py

  - id: review
    type: agi
    command: Review this code for issues
    dependencies:
      - analyze
    parameters:
      model: claude-3-opus
```

---

## 🔍 Workflow Management

### Listing Workflows

```bash
› /workflow list
```

Shows all workflows with:
- Name
- Number of steps
- Creation date
- Description

### Workflow Info

```bash
› /workflow info deploy
```

Shows detailed information:
- ID
- Name and description
- Steps with dependencies
- Variables
- Tags

### Deleting Workflows

```bash
› /workflow delete deploy
```

---

## 💡 Best Practices

1. **Use Descriptive Names**: Name workflows clearly (`deploy-prod`, `test-suite`)
2. **Add Descriptions**: Document what each workflow does
3. **Use Tags**: Organize workflows with tags (`deployment`, `testing`, `maintenance`)
4. **Set Timeouts**: Prevent workflows from hanging indefinitely
5. **Handle Errors**: Use `on_error: continue` for optional steps
6. **Use Variables**: Make workflows reusable with variables
7. **Test Workflows**: Use `dry_run=True` to test before execution
8. **Document Dependencies**: Clearly show step dependencies

---

## 🔗 Related Documentation

- [Quick Start](../user-guides/quick-start.md) - Getting started
- [Tools Guide](../user-guides/tools.md) - Available tools
- [Session Management](../user-guides/sessions.md) - Save/restore state

---

**Version**: 0.1.0
**Last Updated**: 2026
