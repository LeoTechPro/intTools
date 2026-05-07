---
name: openspec-mutation
description: OpenSpec lifecycle mutations. Используйте только когда есть owner-approved SPEC-MUTATION scope для создания, изменения, архивации или mutating exec операций OpenSpec.
---

# OpenSpec lifecycle mutations

## When to use
- Use only for owner-approved `SPEC-MUTATION` work on OpenSpec lifecycle state.

## Do first
- Confirm that the task is explicitly in `SPEC-MUTATION` mode.
- Prefer the MCP lifecycle tools; do not improvise shell mutations.
- Restate the target change or spec, desired lifecycle action, and linked `INT-*` context.
- Summarize created or changed artifacts, archive results, and execution status in worklog or final output.

## Expected result
- Exactly one approved lifecycle mutation is applied to the intended OpenSpec artifact.

## Checks
- Mutating calls include `confirm_mutation=true` and `issue_context=INT-*`.
- Read-only discovery has already answered what can be answered without mutation.
- The target repo and artifact are unambiguous.

## Stop when
- `SPEC-MUTATION` approval is missing.
- Required args are unknown.
- MCP returns policy or config errors.
- A read-only tool would satisfy the request.

## Ask user when
- The intended change or spec is not uniquely identified.
- There is ambiguity between create, patch, archive, or generic exec mutation.
- A broad or emergency fallback mutation is proposed.

## Tool map
- `openspec_archive`: mutating; inputs `confirm_mutation`, `issue_context`, `change_name`; optional `cwd`, `timeout_sec`, `args`.
- `openspec_change_mutate`: mutating; inputs `confirm_mutation`, `issue_context`, `subcommand`; optional `cwd`, `timeout_sec`, `args`.
- `openspec_spec_mutate`: mutating; inputs `confirm_mutation`, `issue_context`, `subcommand`; optional `cwd`, `timeout_sec`, `args`.
- `openspec_new`: mutating; inputs `confirm_mutation`, `issue_context`; optional `cwd`, `timeout_sec`, `args`.
- `openspec_exec_mutate`: mutating fallback; inputs `confirm_mutation`, `issue_context`, `args`; optional `cwd`, `timeout_sec`.
