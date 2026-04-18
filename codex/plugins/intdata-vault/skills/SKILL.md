---
name: intdata-vault
description: Запускай санацию vault и runtime GC через dry-run-first MCP-инструменты intData Vault.
---

# intData Vault

Используй этот skill для проверки и очистки intData vault/runtime storage через guarded MCP wrappers.

## Инструменты

- `intdata_vault_sanitize`: проверяет или выполняет санацию vault. По умолчанию используй `dry_run=true`.
- `intdata_runtime_vault_gc`: проверяет или выполняет GC runtime vault. По умолчанию используй `dry_run=true`.

## Правила выполнения

- Не вызывай vault installer scripts напрямую, если доступен MCP-инструмент этого плагина.
- Всегда начинай с dry-run и читай planned actions до non-dry-run.
- Non-dry-run требует `confirm_mutation=true`, `issue_context=INT-*` и явного owner approval.
- Не удаляй runtime state или архивы по догадке; если dry-run показывает неожиданные paths, остановись и зафиксируй blocker.
- На Windows проверяй encoding/Unicode failures отдельно: падение dry-run на stdout encoding является дефектом tooling, а не разрешением выполнять non-dry-run.
