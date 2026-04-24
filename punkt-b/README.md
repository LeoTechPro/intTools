# PunktB Adapter

`punkt-b/` is a product adapter for PunktB-specific operations.

It may contain wrappers, product profiles, product runbooks, migration adapters and smoke scenarios that depend on PunktB naming, schema, roles, URLs or release rules. Reusable implementation code should move to neutral top-level tools.

## What Stays Here

- Product-specific DBA and migration wrappers.
- PunktB runbooks and historical operation notes.
- Product-specific browser smoke scenarios and role matrices.
- Compatibility entrypoints for old commands while consumers migrate.

## What Moves Out

- Generic repo workflow helpers move to `repo-ops/`.
- Generic lock lifecycle belongs to `lockctl/`.
- Generic gate receipts and commit binding belong to `gatesctl/`.
- Generic DBA commands belong to `dba/`.
- Delivery and host configuration belongs to `delivery/`.

## Current Split Status

- `ops/qa/agent_tmp_cleanup.py` delegates to `repo-ops/bin/agent_tmp_cleanup.py`.
- `ops/qa/agent_lock_cleanup.py` delegates to `repo-ops/bin/agent_lock_cleanup.py`.
- Gate, release, issue-hook and browser-smoke scripts still contain PunktB assumptions and require parameterization before they can be safely extracted.
