# Coordination ledger rules

- `coordctl` хранит normalized task id, issue id, paths/regions, owner, base и lease state.
- Не сохраняй в coordination storage prompts, reasoning, transcripts, raw outputs, messages или secrets.
- Один active writer на region; реальный overlap останавливает агента, warning только сообщает факт.
- Истёкший lease заменяется новой штатной записью; runtime storage вручную не редактируется.
- Goal/progress/evidence хранится в GitHub issue только как material concise comment, а не в coordination ledger.
- Project membership и coordctl никогда не являются approval authority.
- После completion/block/handoff освободи свои sessions и leases; чужие записи не изменяй.

## Tool surface

- `coordctl begin|intent|status|commit-scope-check|release|cleanup`.
- Canonical implementation owner: `/int/probe/client`.
- Если launcher недоступен, сообщи blocker; не подменяй его ручной правкой runtime state.
