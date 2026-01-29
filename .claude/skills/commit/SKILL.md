---
name: commit
description: Commit changes to git with a message
argument-hint: [commit message]
disable-model-invocation: true
allowed-tools: Bash(git *)
---

# Git Commit

Commit all staged and unstaged changes with the provided message.

## Workflow

When invoked with `/commit [message]`:

1. **Show current status**
   ```bash
   git status
   ```

2. **Stage all changes**
   ```bash
   git add -A
   ```

3. **Commit with the message**
   ```bash
   git commit -m "$ARGUMENTS

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
   ```

4. **Show result**
   ```bash
   git log --oneline -1
   ```

## Examples

- `/commit fix: improve affiliate link capture timeout`
- `/commit feat: add deploy-gcp skill`
- `/commit refactor: simplify scraper patterns`

## Notes

- All changes (tracked and untracked) are staged automatically
- Co-authored tag is added automatically
- Does NOT push to remote (use `/push` for that)
