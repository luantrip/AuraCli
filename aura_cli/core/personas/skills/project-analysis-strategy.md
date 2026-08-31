---
name: Project Analysis Strategy
description: Use this skill to systematically analyze, explore, and understand complex codebases and multi-layer projects. Covers structured exploration techniques, dependency mapping, and a step-by-step framework for reasoning about project architecture before making changes.
title: "Project Analysis Strategy"
category: "development"
tags: ["analysis", "codebase", "project-structure", "systematic-exploration"]
priority: "high"
version: "1.0.0"
author: "Aura Core Team"
---

# Project Analysis Strategy

## Overview

This skill provides a systematic approach for analyzing and understanding projects, especially when working with complex codebases with multiple fronts (Backend, Frontend, Mobile, etc.).

## Core Principle

**Always follow a structured, systematic approach when analyzing projects. Don't jump to conclusions or analyze random files.**

## Systematic Analysis Workflow

### Phase 1: Initial Exploration (5-10 minutes)

1. **Start with `analyze_project_structure`**
   - This tool provides a comprehensive overview
   - Identifies all project fronts automatically
   - Reads key files (README, package.json, configs)
   - Generates structured report

2. **Read Root README**
   - Use `read_file("README.md")` to understand project purpose
   - Look for architecture diagrams, setup instructions
   - Identify main technologies and stack

3. **Explore Directory Structure**
   - Use `list_directory(".")` to see root structure
   - Identify main directories and their purposes
   - Look for patterns: `*_Backend`, `*_Frontend`, `*_Mobile`, etc.

### Phase 2: Front-by-Front Analysis

For each identified front:

1. **Read Front README**
   - `read_file("FrontName/README.md")`
   - Understand specific purpose and stack

2. **Explore Front Structure**
   - `list_directory("FrontName/")`
   - Understand organization and architecture

3. **Read Key Configuration Files**
   - `package.json`, `pyproject.toml`, `requirements.txt`
   - `docker-compose.yml`, `Dockerfile`
   - `.env.example` for environment variables

4. **Analyze Source Structure**
   - `list_directory("FrontName/src/")` or equivalent
   - Understand module organization
   - Identify entry points

### Phase 3: Deep Analysis (When Needed)

1. **Use `investigate_codebase` for comprehensive analysis**
   - Provides AST analysis
   - Extracts symbols and dependencies
   - Generates detailed reports

2. **Use `codebase_search` for specific patterns**
   - Find function/class definitions
   - Search for specific concepts
   - Locate related code

3. **Read Critical Files**
   - Entry points (main.py, index.js, App.tsx)
   - Core modules and services
   - Configuration files

## Tool Selection Guide

### When to Use Each Tool

- **`analyze_project_structure`**: ALWAYS start here for new projects
  - Provides complete overview
  - Identifies fronts automatically
  - Reads key files systematically
  - Analyzes architecture, dependencies, and tests (optional)
  - **NEW**: Now includes architecture patterns, dependencies analysis, and test structure

- **`analyze_project_quality`**: For code quality analysis
  - Detects code smells and anti-patterns
  - Finds code duplication
  - Analyzes complexity
  - Identifies structural issues
  - Use after understanding basic structure

- **`analyze_project_security`**: For security analysis
  - Detects hardcoded secrets
  - Identifies insecure patterns
  - Checks for vulnerable dependencies
  - Use for security audits

- **`analyze_project_documentation`**: For documentation analysis
  - Checks README completeness
  - Analyzes code documentation
  - Identifies missing docs
  - Use to assess documentation quality

- **`compare_project_fronts`**: For comparing different fronts
  - Compares technologies between fronts
  - Finds similarities and differences
  - Identifies shared dependencies
  - Use to understand relationships between fronts

- **`list_directory`**: For exploring directory structure
  - Use when you need to see what's in a directory
  - Use before reading specific files
  - Use to understand organization

- **`read_file`**: For reading specific files
  - README files (always read these first)
  - Configuration files
  - Source code files you need to understand

- **`codebase_search`**: For finding specific patterns
  - Function/class definitions
  - Usage of specific concepts
  - Configuration patterns

- **`investigate_codebase`**: For deep, comprehensive analysis
  - When you need full AST analysis
  - When analyzing architecture
  - When generating detailed reports

- **`analyze_code`**: For analyzing individual files
  - Structure of specific files
  - Classes, functions, imports
  - Only for FILES, not directories

- **`analyze_code_nlp`**: For NLP-based code understanding
  - Classification and summarization
  - Only for FILES, not directories

## Common Mistakes to Avoid

1. **❌ Trying to analyze directories with file-only tools**
   - `analyze_code("directory/")` → Use `list_directory("directory/")` first
   - Always check if path is file or directory

2. **❌ Random file analysis**
   - Don't analyze random files
   - Follow systematic workflow
   - Start with READMEs and key files

3. **❌ Skipping structure exploration**
   - Always explore structure before deep analysis
   - Understand organization first
   - Identify fronts and modules

4. **❌ Ignoring README files**
   - READMEs contain critical information
   - Always read them first
   - They explain purpose and setup

5. **❌ Not using `analyze_project_structure`**
   - This tool does systematic analysis automatically
   - Use it as starting point
   - Saves time and ensures completeness

## Best Practices

1. **Always start with `analyze_project_structure`**
   - Gets you 80% of the way there
   - Identifies fronts automatically
   - Reads key files systematically

2. **Read READMEs systematically**
   - Root README first
   - Then each front's README
   - They contain purpose, architecture, setup

3. **Explore before analyzing**
   - Use `list_directory` to understand structure
   - Identify important directories
   - Then read specific files

4. **Use appropriate tools for the task**
   - File tools for files
   - Directory tools for directories
   - Search tools for finding patterns

5. **Generate structured understanding**
   - Document what you learn
   - Build mental model of project
   - Identify key components and relationships

## Example Workflows

### Workflow 1: Análise Inicial Completa
```
User: "Analise este projeto e me explique o que ele faz"

Agent:
1. analyze_project_structure(".")
   → Identifies: Loquei_Backend, Loquei_Mobile, Loquei_Contratos
   → Reads: README.md, package.json files
   → Extracts: Technologies, purpose, structure
   → Analyzes: Architecture patterns, dependencies, tests

2. read_file("README.md")
   → Gets project overview and purpose

3. For each front:
   - read_file("FrontName/README.md")
   - list_directory("FrontName/")
   - Read key config files

4. Generate comprehensive explanation
```

### Workflow 2: Análise de Qualidade
```
User: "Quais problemas de qualidade existem neste projeto?"

Agent:
1. analyze_project_structure(".")  # Get overview first
2. analyze_project_quality(".", focus_areas=["duplication", "smells", "complexity"])
   → Detects code smells
   → Finds duplication
   → Analyzes complexity
3. Generate quality report with recommendations
```

### Workflow 3: Análise de Segurança
```
User: "Verifique problemas de segurança"

Agent:
1. analyze_project_security(".")
   → Checks for hardcoded secrets
   → Identifies insecure patterns
   → Checks dependencies
2. Generate security report
```

### Workflow 4: Comparação de Frentes
```
User: "Compare as frentes Backend e Frontend"

Agent:
1. analyze_project_structure(".")  # Get fronts
2. compare_project_fronts(".", fronts=["Loquei_Backend", "Loquei"])
   → Compares technologies
   → Finds similarities/differences
   → Identifies shared dependencies
3. Generate comparison report
```

## Integration with Other Skills

- **Clean Code**: Apply when analyzing code quality
- **Architectural Patterns**: Use to identify patterns in structure
- **API Design**: Apply when analyzing API endpoints
- **Testing Pyramid**: Check test structure and coverage

## Summary

The key to effective project analysis is **systematic exploration**:
1. Start with `analyze_project_structure` for overview
2. Read READMEs to understand purpose
3. Explore structure with `list_directory`
4. Use appropriate tools for specific needs
5. Build comprehensive understanding before deep analysis

Always remember: **Structure first, details later.**
