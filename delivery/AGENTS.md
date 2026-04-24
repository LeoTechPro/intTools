# AGENTS.md - policy-only правила для `/int/tools/delivery`

## Repo Role

`/int/tools/delivery` хранит внешний host-config, devops, docops, monitoring и delivery tooling-контур для intData-family сервисов.

## Allowed scope

- host configs и proxy/systemd templates;
- devops/docops/dev helpers;
- monitoring templates;
- cross-repo and machine-wide scripts, относящиеся к delivery/runtime задачам.

## What not to mutate

- не переносить сюда product-core backend schema/functions/contracts;
- не хранить runtime-state и секреты;
- не подменять owner repos отдельных сервисов.

## Integration expectations

- product repos владеют своим runtime-code/config/docs;
- `/int/data` остаётся strict backend-core repo;
- tooling для соседних repos может жить здесь только если это внешний helper layer, а не product-core.

## Lock discipline

- Любые файловые правки в `/int/tools/delivery` запрещены без предварительного `lockctl acquire` по конкретному файлу.
- Источник истины по активным локам — только `lockctl`; project-local заметки не подменяют runtime truth.
- После завершения правки лок обязательно снимается через `lockctl release-path` или `lockctl release-issue`.

## Git и commit hygiene

- Перед каждым локальным commit обязательно добавить в индекс новые файлы текущего scope и повторно выполнить `git add` для уже staged путей после каждой дополнительной правки; commit по устаревшему состоянию индекса запрещён.
