---
name: review-find
description: Глубокое hostile-ревью предыдущего результата агента. Используйте, когда Codex должен считать предыдущую реализацию, план или объяснение недоверенными и подтвердить выводы по реальным артефактам.
---

# Review Find

## When to use
- Use when the user wants a hostile audit of an earlier result, implementation, plan, runtime setup, or plugin surface.

## Do first
- Treat the prior result as untrusted until verified.
- Read the governing repo instructions, current code or config, and any referenced logs before forming conclusions.
- Prefer current runtime truth over prior summaries or diffs.
- If MCP tools are used during the audit, summarize the material results explicitly.

## Expected result
- A finding set grounded in current evidence, with bugs, regressions, risks, drift, and unverified claims clearly separated.

## Checks
- Critical files are read fully when behavior depends on full context.
- Repo rules, OpenSpec state, routing, and coordination rules are checked where relevant.
- Every finding cites concrete evidence from code, config, logs, or reproducible behavior.

## Stop when
- The audit target is unclear.
- Required evidence is unavailable.
- The task has shifted from review into mutation without an explicit request.

## Ask user when
- The review target could mean more than one artifact or commit.
- Resolving uncertainty would require new mutations, privileged access, or destructive verification.

## Output contract
- `Findings`: ordered by severity with path or location, impact, and evidence.
- `С чем согласен`: what remains correct after verification.
- `С чем не согласен`: what is unverified, wrong, or only a tradeoff.
- `Проверки`: what files, commands, logs, or tests were actually inspected.
