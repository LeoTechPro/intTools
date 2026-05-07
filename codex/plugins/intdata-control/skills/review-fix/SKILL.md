---
name: review-fix
description: Перепроверка предыдущего ревью по реальному коду и исправление только подтверждённых замечаний. Используйте, когда нужно верифицировать findings и внести узкие правки без расширения scope.
---

# Review Fix

## When to use
- Use when there is an existing review or finding set and the task is to confirm it against current code, then fix only confirmed issues.

## Do first
- Re-verify each finding against the current tree before editing.
- Keep scope narrow: confirmed issues only, no opportunistic cleanup.
- Follow active governance, OpenSpec, and coordination rules for the owning repo.
- Summarize any MCP or coordination tool results that materially affected the fix.

## Expected result
- Confirmed findings are fixed and unconfirmed findings are left untouched with an explicit note.

## Checks
- Each fix maps to a confirmed finding.
- Files changed are only those needed for the confirmed issues.
- Verification covers the behavior or invariant claimed by the review.

## Stop when
- Findings cannot be reproduced or verified.
- Scope expands beyond the reviewed issues.
- Required approval, issue context, or coordination state is missing.

## Ask user when
- A finding is ambiguous or depends on product intent.
- Fixing one confirmed issue requires broader refactor or contract changes.

## Output contract
- List confirmed findings fixed.
- List findings rejected or left unresolved and why.
- Report checks run and remaining risk.
