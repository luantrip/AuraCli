# 🔄 Refactoring Guide

Aura CLI provides intelligent code refactoring with impact analysis and safe execution.

---

## 📋 Overview

The refactoring system includes:
- **Refactoring Planner** - Plans refactoring strategy
- **Impact Analysis** - Analyzes change impact
- **Refactoring Executor** - Executes refactoring safely
- **Semantic Similarity** - Finds similar code patterns

---

## 🎯 Basic Refactoring

### Simple Refactoring

```
› /agi refactor the user authentication module to use JWT tokens
```

The system will:
1. Analyze current code
2. Plan refactoring
3. Analyze impact
4. Show preview
5. Execute safely
6. Run tests
7. Update documentation

### Refactoring Operations

- **Rename** - Rename functions, classes, variables
- **Extract** - Extract functions, classes
- **Inline** - Inline functions
- **Move** - Move code between files
- **Restructure** - Restructure code

---

## 🔍 Impact Analysis

### Before Refactoring

The system analyzes:
- **Dependencies** - What depends on this code
- **Usages** - Where code is used
- **Tests** - Affected tests
- **Documentation** - Docs to update

### Example

```
› Analyze impact of renaming UserService to UserManager

Impact Analysis:
- 15 files use UserService
- 3 tests reference UserService
- 2 documentation files mention UserService
- Estimated changes: 45 locations
```

---

## 🛡️ Safe Refactoring

### Validation

- Syntax validation
- Type checking
- Test execution
- Import validation

### Rollback

If refactoring fails:
```
› Rollback refactoring
```

---

## 🔗 Related Documentation

- [Tools Guide](./tools.md) - Refactoring tools
- [Quick Start](./quick-start.md) - Getting started

---

**Version**: 0.1.0
**Last Updated**: 2026
