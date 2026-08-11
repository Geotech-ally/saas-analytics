# AGENTS.md — Project Knowledge & Workflow

## Git Worktree Workflow

This project uses Git worktrees for parallel feature development and hotfixes.

### Creating a Worktree

```bash
# Create a new worktree for a feature branch
git worktree add ../feature/auth-refactor -b feature/auth-refactor

# Create a worktree for a hotfix
git worktree add ../hotfix/security-patch -b hotfix/security-patch
```

### Listing Active Worktrees

```bash
git worktree list
```

### Resolving Conflicts in a Worktree

1. Fetch latest changes from the base branch:
   ```bash
   git fetch origin main
   ```

2. Rebase your worktree branch onto the latest main:
   ```bash
   git rebase origin/main
   ```

3. If conflicts occur, resolve them manually:
   - Open conflicting files
   - Look for conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
   - Edit to produce the correct merged content
   - Stage resolved files: `git add <file>`

4. Continue the rebase:
   ```bash
   git rebase --continue
   ```

5. If you need to abort the rebase:
   ```bash
   git rebase --abort
   ```

### Removing a Worktree

```bash
# Remove the worktree directory
git worktree remove ../feature/auth-refactor

# Prune stale worktree references
git worktree prune
```

### Cleanup Commands

```bash
# Remove all stale worktree references
git worktree prune

# List all worktrees (active and stale)
git worktree list --porcelain

# Remove a worktree forcefully (even if not checked out)
git worktree remove --force ../feature/auth-refactor
```

### Best Practices

- Always `git pull --rebase` in your worktree before starting work
- Push your branch to origin before removing the worktree
- Never delete a worktree directory manually; use `git worktree remove`
- Run `git worktree prune` regularly to clean up stale entries