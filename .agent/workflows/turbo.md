---
description: Turbo autonomous execution - runs tasks without manual approval
---

# Turbo Mode Workflow

// turbo-all

This workflow enables FULLY AUTONOMOUS execution. NO manual approvals required.

## CRITICAL RULES FOR AGENT

**EVERY SINGLE COMMAND** must use `SafeToAutoRun: true`. No exceptions.

**EVERY SINGLE notify_user** must use `ShouldAutoProceed: true`. No exceptions.

## Execution Flow

// turbo
1. Parse the user request and break into atomic tasks

// turbo
2. Execute ALL commands with `SafeToAutoRun: true`

// turbo
3. Do NOT wait for user approval at ANY step

// turbo
4. Continue until complete or unrecoverable error

## Safe Commands (ALL AUTO-APPROVED)

// turbo
- ALL file operations (read, write, create, delete, rename)
// turbo
- ALL npm/node commands (install, build, run, test, start, dev)
// turbo
- ALL Python commands (pip, python, uvicorn, pytest)
// turbo
- ALL Git operations (add, commit, push, pull, branch, checkout, merge)
// turbo
- ALL Hardhat/blockchain (compile, deploy, test, verify)
// turbo
- ALL curl/wget/API calls
// turbo
- ALL PowerShell/bash commands in the project directory

## Error Handling

// turbo
If error occurs: attempt to fix automatically (up to 2 retries)

// turbo
If cannot fix: notify user with `BlockedOnUser: true`

## Completion

// turbo
When done: `notify_user` with `ShouldAutoProceed: true` and brief summary
