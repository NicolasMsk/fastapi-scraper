---
name: push
description: Push commits to remote repository
disable-model-invocation: true
allowed-tools: Bash(git *)
---

# Git Push

Push local commits to the remote repository.

## Workflow

When invoked with `/push`:

1. **Show commits to push**
   ```bash
   git log --oneline origin/main..HEAD
   ```

2. **Push to remote**
   ```bash
   git push origin HEAD
   ```

3. **Confirm success**
   ```bash
   git status
   ```

## Notes

- Pushes current branch to origin
- Shows unpushed commits before pushing
