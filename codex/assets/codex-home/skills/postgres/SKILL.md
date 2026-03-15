---
name: postgres
description: 'PostgreSQL: проектирование схем, миграции, оптимизация запросов и индексов,
  производительность и эксплуатация.'
---

# PostgreSQL Core

## Overview

Unified PostgreSQL skill covering schema design, migrations, query optimization, and production engineering.

## Workflow

1. Clarify scope: schema design, migration, query tuning, or production ops.
2. Collect context: existing schema, workloads, constraints, and target behavior.
3. Apply relevant guidance from references (below).
4. Provide a concrete plan or SQL changes with rationale and risk notes.

## References

- `references/table-design.md` - data types, constraints, indexing, and table design rules.
- `references/database-development.md` - schema design, migrations, ORM patterns, query optimization, JSONB, full-text search.
- `references/database-engineering.md` - performance tuning, replication, HA, VACUUM, monitoring, and ops.

## Output Expectations

- Use explicit SQL examples when proposing changes.
- Call out required extensions and compatibility concerns.
- Provide performance impact notes for indexing and query changes.
