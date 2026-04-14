## 1. CHANGE PACKAGE
- [ ] 1.1 Зафиксировать owner-approved change `agent-tool-routing-v1-cross-platform-entrypoints`.
- [ ] 1.2 Добавить proposal, design, tasks и executor prompt с полным repo-owned V1 inventory.

## 2. PROCESS / GOVERNANCE SPEC
- [ ] 2.1 Расширить `process` spec policy для mandatory routing на high-risk intents.
- [ ] 2.2 Зафиксировать blocker semantics: missing engine, unsupported platform, adapter drift, ambiguous intent => `blocked`.
- [ ] 2.3 Зафиксировать policy, что verified skills не запрещаются, но не являются implicit replacement для repo-owned high-risk capability.

## 3. NEW CAPABILITY SPEC: `agent-tool-routing`
- [ ] 3.1 Добавить logical registry contract для `logical_intents[]`, `runtime_bindings`, `resolution_status`.
- [ ] 3.2 Добавить engine/adapter contract и обязательные binding fields: `binding_kind`, `binding_origin`, `platforms_supported`, `adapter_targets_engine`, `parity_required`.
- [ ] 3.3 Зафиксировать V1 high-risk inventory: publish/deploy, lock/sync, remote access, browser verify/fallback attach, DB diagnostics, host bootstrap/runtime launchers.

## 4. EXECUTOR HANDOFF
- [ ] 4.1 Дать исполнителю точный implementation prompt с canonical engine roots и cutover expectations.
- [ ] 4.2 Явно перечислить текущие repo-owned entrypoints, которые должны быть приведены к capability contract.
- [ ] 4.3 Явно зафиксировать non-goals первой волны и verified-skill fallback policy.

## 5. VALIDATION
- [ ] 5.1 Прогнать `openspec validate agent-tool-routing-v1-cross-platform-entrypoints --strict`.
- [ ] 5.2 Проверить diff на отсутствие несвязанных runtime/tooling mutations вне spec package.
- [ ] 5.3 Выполнить локальный commit в `/int/tools` с этим change package.

### Blockers (current)
- Нет.
