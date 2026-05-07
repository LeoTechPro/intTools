---
name: intbrain
description: Internal int-tools skill entrypoint for the intbrain plugin. Use as the router for IntBrain context, memory, people graph, policies, jobs, PM dashboard, session sync, and external import workflows.
---

# IntBrain

## When to use
- Use for IntBrain context, memory, graph, policy, job, PM, and import workflows.

## Do first
- Prefer the plugin MCP surface for `intbrain`.
- Pick the narrowest leaf skill before calling tools.
- Restate the owner id, mutation mode, and the artifact or entity you need.
- Summarize material tool results in worklog or final response because raw payloads may be hidden in the UI.

## Expected result
- The correct IntBrain tool family is used with clear owner and scope.

## Checks
- Owner id and target entity, task, or source path are known.
- Read-only requests stay read-only.
- Mutating requests carry explicit approval and issue context.

## Stop when
- Required args are unknown.
- MCP returns policy or config errors.
- The request needs mutation without approval.
- The intended IntBrain surface is ambiguous.

## Ask user when
- More than one owner, entity, or import source could be intended.
- A write to memory, graph, policies, or tasks is requested without clear intent.

## Skill map
- `context-memory`: context packs, memory search or store, graph links.
- `session-memory`: recent work, session brief, session sync.
- `people-graph-policies`: people lookup, graph neighbors, policy reads and upserts.
- `jobs-runtime`: jobs, job sync, and job policy updates.
- `pm-dashboard-tasks`: PM dashboard, PARA, health, constraints, task create or patch.
- `external-imports`: controlled imports from vault PM and MemPalace.
