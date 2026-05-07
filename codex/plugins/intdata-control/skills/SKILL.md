---
name: intdata-control
description: Internal int-tools skill entrypoint for the intdata-control plugin. Use as the router for coordctl, OpenSpec, routing, and review workflows.
---

# intData Control

## When to use
- Use for coordination, OpenSpec discovery or mutation, routing validation, and hostile review workflows in intData tooling.

## Do first
- Prefer the plugin MCP surface for `intdata-control`; do not substitute shell fallback by default.
- Pick the narrowest leaf skill before calling tools.
- Restate the expected result, mutation mode, and the exact repo or artifact you are operating on.
- Summarize material tool results in worklog or final response because the UI may hide raw payloads.

## Expected result
- The correct control-plane tool family is chosen and called with a clear scope.

## Checks
- The requested action matches exactly one leaf skill or an explicit combination.
- Required identifiers are known: repo root, item name, issue id, or target path.
- Read-only requests stay read-only; mutating requests carry explicit approval.

## Stop when
- Required args are unknown.
- MCP returns policy or config errors.
- The request needs mutation without approval.
- Source of truth or target artifact is ambiguous.

## Ask user when
- The work needs `SPEC-MUTATION` approval.
- More than one artifact or repo could be the intended target.
- A mutating fallback is proposed after MCP drift or outage.

## Skill map
- `coordctl`: session and intent coordination for parallel edits.
- `openspec-read`: read-only OpenSpec discovery and validation.
- `openspec-mutation`: owner-approved OpenSpec lifecycle mutations.
- `routing`: routing registry validation and resolution.
- `review-find`: hostile review of an earlier result.
- `review-fix`: verify findings against real code and fix only confirmed issues.
