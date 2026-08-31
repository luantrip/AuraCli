# ✏️ Editing Guide - Code Editing System

Aura CLI provides a sophisticated code editing system with safety features and validation.

---

## 📋 Overview

The editing system includes:
- **Edit Executor** - Safe file editing
- **Edit Planner** - Planning edits
- **Edit Validator** - Validation before execution
- **Edit History** - Undo/redo support
- **Multi-Edit** - Edit multiple files

---

## 🔧 Basic Editing

### Simple Edit

```
› Edit main.py: replace "old_function" with "new_function"
```

The system will:
1. Read the file
2. Find the content
3. Show preview
4. Ask for confirmation
5. Apply edit
6. Validate result

### Edit Operations

- **Replace** - Replace content
- **Insert** - Insert at position
- **Delete** - Delete lines
- **Append** - Append to end

---

## 🛡️ Safety Features

### Automatic Backups

All edits create backups automatically:

```
main.py.backup.20261015_103000
```

### Validation

Edits are validated:
- Syntax checking
- Type checking
- Import validation

### Rollback

If edit fails:
```
› Restore main.py from backup
```

---

## 📝 Edit History

### View History

```
› Show edit history for main.py
```

### Undo/Redo

```
› Undo last edit
› Redo edit
```

---

## 🔗 Related Documentation

- [Tools Guide](./tools.md) - Edit tools
- [Quick Start](./quick-start.md) - Getting started

---

**Version**: 0.1.0
**Last Updated**: 2026
