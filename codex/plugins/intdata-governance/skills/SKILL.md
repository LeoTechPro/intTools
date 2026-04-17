# intdata-governance plugin skill pointer

Use this plugin for governance and delivery control-plane operations in `@int-tools`.

## Tools
- `routing_validate`
- `routing_resolve`
- `sync_gate`
- `publish`
- `gate_status`
- `gate_receipt`
- `commit_binding`

## Guardrails
- Mutating operations require `confirm_mutation=true`.
- Mutating operations require `issue_context=INT-*`.
- Structured args/enums only; no arbitrary shell passthrough.

## Migration note
- Replaces removed plugins: `intdata-routing`, `intdata-delivery`, `gatesctl`.
- Do not use removed tool names/IDs in instructions.
