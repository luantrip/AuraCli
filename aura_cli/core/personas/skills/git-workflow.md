---
name: Git Workflow
description: Use this skill when the user asks about git commands, branching strategies, commits, merging, rebasing, pull requests, git best practices, or version control workflows.
version: 1.0.0
author: Aura Core Team
---

# Git Workflow Guide

Comprehensive guide for Git version control best practices.

## 1. Basic Commands

### Repository Setup

```bash
# Initialize new repository
git init

# Clone existing repository
git clone <url>

# Add remote
git remote add origin <url>
```

### Daily Workflow

```bash
# Check status
git status

# Stage changes
git add <file>
git add .  # All changes

# Commit
git commit -m "message"

# Push
git push origin <branch>

# Pull
git pull origin <branch>
```

## 2. Branching

### Branch Commands

```bash
# List branches
git branch
git branch -a  # All including remote

# Create branch
git branch <name>

# Switch branch
git checkout <name>
git switch <name>  # Modern

# Create and switch
git checkout -b <name>
git switch -c <name>

# Delete branch
git branch -d <name>  # Safe delete
git branch -D <name>  # Force delete
```

### Branch Naming Conventions

- `feature/` - New features: `feature/user-authentication`
- `bugfix/` - Bug fixes: `bugfix/login-error`
- `hotfix/` - Urgent fixes: `hotfix/security-patch`
- `release/` - Release prep: `release/v1.2.0`
- `chore/` - Maintenance: `chore/update-dependencies`

## 3. Commit Messages

### Conventional Commits Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### Examples

```bash
git commit -m "feat(auth): add OAuth2 login support"
git commit -m "fix(api): handle null response from server"
git commit -m "docs: update API documentation"
```

## 4. Merging vs Rebasing

### Merge

```bash
# Merge branch into current
git merge <branch>

# Merge with no fast-forward
git merge --no-ff <branch>
```

### Rebase

```bash
# Rebase current onto branch
git rebase <branch>

# Interactive rebase
git rebase -i HEAD~3

# Continue after conflict
git rebase --continue

# Abort rebase
git rebase --abort
```

### When to Use

- **Merge**: Public branches, preserves history
- **Rebase**: Local branches, clean linear history

## 5. Undoing Changes

```bash
# Unstage file
git reset HEAD <file>

# Discard local changes
git checkout -- <file>
git restore <file>

# Amend last commit
git commit --amend

# Reset to commit (keep changes)
git reset --soft HEAD~1

# Reset to commit (discard changes)
git reset --hard HEAD~1

# Revert commit (creates new commit)
git revert <commit>
```

## 6. Stashing

```bash
# Stash changes
git stash

# Stash with message
git stash save "message"

# List stashes
git stash list

# Apply latest stash
git stash pop

# Apply specific stash
git stash apply stash@{0}

# Drop stash
git stash drop stash@{0}
```

## 7. Viewing History

```bash
# Log
git log
git log --oneline
git log --graph --oneline --all

# Show commit
git show <commit>

# Diff
git diff
git diff --staged
git diff <branch1>..<branch2>
```

## 8. Best Practices

1. **Commit early, commit often** with meaningful messages
2. **Pull before push** to avoid conflicts
3. **Never force push** to shared branches
4. **Use branches** for all features and fixes
5. **Review changes** before committing
6. **Keep commits atomic** - one logical change per commit
7. **Write descriptive commit messages** explaining why
