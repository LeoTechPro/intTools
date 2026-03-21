# data tooling

`/int/tools/data` — внешний ops/process/tooling contour для `data backend-core`.

## Что живёт здесь

- host-level configs и proxy/systemd templates, которые больше не считаются частью product repo `/int/data`
- devops/docops/dev helpers для `data`
- cross-repo and machine-wide scripts, которые обслуживают `data` как платформенный backend

## Что не живёт здесь

- canonical schema/functions/contracts backend-core
- runtime-state и секреты
- исходники отдельных сервисов `chat`, `bot`, `itsm`, `erp`

## Структура

- `configs/` — host-level configs и templates
- `devops/` — ops helpers
- `devs/` — developer helpers
- `docops/` — docs/process helpers

`/int/data` остаётся owner только backend-core. Всё, что является внешним tooling или host-config слоем, должно жить здесь.
