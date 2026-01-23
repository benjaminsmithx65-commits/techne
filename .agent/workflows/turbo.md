---
description: Turbo autonomous execution - runs tasks without manual approval
---

# Turbo Mode Workflow

This workflow enables fully autonomous execution with maximum auto-approval.

## When to Use
Use `/turbo` when you want me to complete a task without any manual approvals.

## Instructions for Agent

// turbo-all

**IMPORTANT**: This workflow has `// turbo-all` annotation which means ALL commands should be auto-run.

### 1. Parse the User Request
- Understand what needs to be done
- Break down into small, atomic tasks
- Create a mental checklist

### 2. Execute Without Blocking
For each task:
- Set `SafeToAutoRun: true` for ALL terminal commands
- Set `ShouldAutoProceed: true` for notify_user calls
- Do NOT wait for user approval between steps
- Continue until complete or error

### 3. Command Safety Override
In turbo mode, the following are considered safe:
// turbo
- File operations (read, write, create, delete project files)
// turbo
- npm/node commands (install, build, run, test)
// turbo
- Python commands (pip install, run scripts, uvicorn)
// turbo
- Git operations (add, commit, push, pull, branch)
// turbo
- Hardhat/blockchain commands (compile, deploy, test)
// turbo
- curl/API calls

### 4. Error Handling
If an error occurs:
- Attempt to fix automatically
- If cannot fix after 2 attempts, notify user with `BlockedOnUser: true`

### 5. Completion
When done:
- Create brief summary
- Use `notify_user` with `ShouldAutoProceed: true`
