---
description: Ralph-style autonomous agent loop - PRD to completion
---

# Ralph Autonomous Workflow

Based on [Ralph pattern](https://github.com/snarktank/ralph) - autonomous execution until PRD complete.

// turbo-all

## How to Use

1. User provides a PRD or feature description
2. Agent creates `tasks/prd.json` with stories
3. Agent executes each story autonomously
4. Updates progress after each iteration
5. Continues until all stories pass

## PRD Format

Create `tasks/prd.json` with this structure:
```json
{
  "name": "Feature Name",
  "branchName": "feature/xxx",
  "stories": [
    {
      "id": 1,
      "title": "Story title",
      "description": "What to do",
      "acceptanceCriteria": ["Criterion 1", "Criterion 2"],
      "priority": 1,
      "passes": false
    }
  ]
}
```

## Agent Instructions

### For Each Iteration:
// turbo
1. Read `tasks/prd.json` 
// turbo
2. Find first story where `passes: false`
// turbo
3. Implement the story
// turbo
4. Run tests/checks
// turbo
5. If passes, update `passes: true` in prd.json
// turbo
6. Commit changes
// turbo
7. Append learnings to `tasks/progress.txt`
// turbo
8. Repeat until all pass

### Auto-Approval Rules
- ALL file operations are safe
- ALL terminal commands are safe
- Git operations are safe
- Deploy commands require user approval ONLY if not in turbo mode

### Stop Conditions
- All stories pass
- Max iterations reached (default: 20)
- Unrecoverable error
