---
description: Express command to enable full turbo autonomous mode
---

# Express Turbo Activation

When user types `/express` or just "dzialaj", enable maximum autonomy:

// turbo-all

## Immediate Actions:
// turbo
1. Do NOT ask clarifying questions unless absolutely critical
// turbo
2. Make reasonable assumptions based on context
// turbo
3. Execute all commands with `SafeToAutoRun: true`
// turbo
4. Use `ShouldAutoProceed: true` for all notify_user calls
// turbo
5. Complete the entire task in one go

## Summary at End:
- Provide short completion summary
- List any assumptions made
- Note any issues encountered

## Example Triggers:
- `/express`
- `dzialaj`
- `turbo`
- `bez approva`
- `sam zrob`
- `nie pytaj`
