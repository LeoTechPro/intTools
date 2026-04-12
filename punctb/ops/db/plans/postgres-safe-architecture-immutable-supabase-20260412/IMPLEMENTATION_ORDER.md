# Implementation Order (Draft)

1. Выполнить `00_inventory_checks.sql` в read-only режиме и сохранить отчет.
2. Подтвердить список custom roles и финальный DR topology.
3. Подготовить wrapper/runbook rollout (без SQL-мутаций).
4. В отдельное окно внедрения применить:
   - `10_role_flag_hardening_prod.sql`
   - `20_role_flag_hardening_legacy.sql`
   - `30_role_flag_hardening_dev.sql`
   - `40_readonly_enforcement_legacy.sql`
   - `50_migrator_model.sql`
   - `60_agent_guardrails.sql`
5. Сразу после каждого блока выполнять `70_validation_queries.sql`.
6. Для DR запускать `80_dr_prerequisites.sql` только после утверждения topology/network.

## Stop conditions

Останавливаем внедрение, если:

- обнаружены unexpected dependencies на system Supabase roles вне runtime;
- нет подтверждения по `punktb_pro` replication boundary;
- не утвержден owner DNS failover/failback.
