---
name: Python Environment Management
description: Use this skill when the user asks about Python environment management, including venv, virtualenv, poetry, pip, dependencies, pyproject.toml, requirements.txt, conda, or package installation.
version: 1.0.0
author: Aura Core Team
---

# Python Environment Management Guide

This guide covers managing Python environments to isolate project dependencies and avoid conflicts.

## 1. Using venv (Python 3 Native)

### Creating an Environment

```bash
python3 -m venv .venv
```

### Activation

- **Linux/macOS**: `source .venv/bin/activate`
- **Windows**: `.venv\Scripts\activate`

### Deactivation

```bash
deactivate
```

### Managing Dependencies

```bash
# Install package
pip install <package>

# Save dependencies
pip freeze > requirements.txt

# Install from file
pip install -r requirements.txt
```

## 2. Using Poetry (Modern)

Poetry manages everything through `pyproject.toml`.

### Installation

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Commands

```bash
# Create new project
poetry new my-project

# Initialize in existing project
poetry init

# Add dependency
poetry add <package>

# Add dev dependency
poetry add --group dev <package>

# Install all dependencies
poetry install

# Activate environment
poetry shell

# Run command in environment
poetry run python script.py

# Update dependencies
poetry update

# Show dependencies
poetry show --tree
```

### pyproject.toml Structure

```toml
[tool.poetry]
name = "my-project"
version = "0.1.0"
description = ""
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.28.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
black = "^23.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## 3. Using pip-tools

Compiles `requirements.in` to pinned `requirements.txt`.

```bash
# Install pip-tools
pip install pip-tools

# Compile requirements
pip-compile requirements.in

# Sync environment
pip-sync requirements.txt
```

## 4. Using Conda

For data science and scientific computing.

```bash
# Create environment
conda create -n myenv python=3.10

# Activate
conda activate myenv

# Install package
conda install numpy

# Export environment
conda env export > environment.yml

# Create from file
conda env create -f environment.yml
```

## 5. Best Practices

1. **Always use virtual environments** for project isolation
2. **Pin versions** in production dependencies
3. **Separate dev and production** dependencies
4. **Use lock files** (poetry.lock, requirements.txt) for reproducibility
5. **Document Python version** requirements
6. **Use `.python-version`** file for pyenv users
