# AGENTS.md - policy-only правила для `/int/tools/data`

## Repo Role

`/int/tools/data` хранит внешний tooling-контур для `data backend-core`.

## Allowed scope

- host configs
- devops/docops/dev helpers
- cross-repo and machine-wide scripts, относящиеся к `data`

## What not to mutate

- не переносить сюда product-core backend schema/functions/contracts
- не хранить runtime-state и секреты
- не подменять owner repos отдельных сервисов

## Integration expectations

- `/int/data` остаётся strict backend-core repo
- `/int/chat`, `/int/bot`, `/int/itsm`, `/int/erp` владеют своими runtime-code/config/docs
- tooling для этих repos может жить здесь только если это внешний helper layer, а не product-core
