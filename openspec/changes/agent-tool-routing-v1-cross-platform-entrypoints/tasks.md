## 1. CHANGE PACKAGE
- [x] 1.1 Зафиксировать owner-approved change `agent-tool-routing-v1-cross-platform-entrypoints`.
- [x] 1.2 Добавить proposal, design, tasks и executor prompt с полным repo-owned V1 inventory.

## 2. PROCESS / GOVERNANCE SPEC
- [x] 2.1 Расширить `process` spec policy для mandatory routing на high-risk intents.
- [x] 2.2 Зафиксировать blocker semantics: missing engine, unsupported platform, adapter drift, ambiguous intent => `blocked`.
- [x] 2.3 Зафиксировать policy, что verified skills не запрещаются, но не являются implicit replacement для repo-owned high-risk capability.

## 3. NEW CAPABILITY SPEC: `agent-tool-routing`
- [x] 3.1 Добавить logical registry contract для `logical_intents[]`, `runtime_bindings`, `resolution_status`.
- [x] 3.2 Добавить engine/adapter contract и обязательные binding fields: `binding_kind`, `binding_origin`, `platforms_supported`, `adapter_targets_engine`, `parity_required`.
- [x] 3.3 Зафиксировать V1 high-risk inventory: publish/deploy, lock/sync, remote access, browser verify/fallback attach, DB diagnostics, host bootstrap/runtime launchers.

## 4. EXECUTOR HANDOFF
- [x] 4.1 Дать исполнителю точный implementation prompt с canonical engine roots и cutover expectations.
- [x] 4.2 Явно перечислить текущие repo-owned entrypoints, которые должны быть приведены к capability contract.
- [x] 4.3 Явно зафиксировать non-goals первой волны и verified-skill fallback policy.

## 5. VALIDATION
- [x] 5.1 Прогнать `openspec validate agent-tool-routing-v1-cross-platform-entrypoints --strict`.
- [x] 5.2 Проверить diff на отсутствие несвязанных runtime/tooling mutations вне spec package.
- [x] 5.3 Выполнить локальный commit в `/int/tools` с этим change package.

### Blockers (current)
- Нет.
