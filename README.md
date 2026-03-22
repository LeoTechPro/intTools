# intTools

`intTools` — machine-wide tooling repo `LeoTechPro/intTools` с каноническим путём `/int/tools`.

## Target Role

`/int/tools` — `ops-tooling`: внешний reusable contour для process tooling, hooks, host helpers, bootstrap scripts и shared runbooks.

## Canonical Ownership

- `/int/tools` владеет только machine-wide ops/process/tooling артефактами;
- business product-core, user-facing shells и domain ownership остаются в соответствующих top-level repos;
- runtime state и реальные секреты живут во внешних host paths, а не в repo.

## What Lives Here

- `lockctl`, `gatesctl`, `codex`, `probe`, `data` и другие reusable tooling modules;
- shared hooks, bootstrap scripts и ops runbooks;
- repo-level docs для tooling contour.

## What Must Not Live Here

- canonical product domains и user-facing product shells;
- permanent runtime-state, caches и секреты как tracked source-of-truth;
- дубли локальных product README/AGENTS вместо ссылок на owner repos.

## Integration Expectations

- reusable tooling хранится здесь, а не в корне `/int` и не в product repos;
- product repos подключают этот contour извне через scripts, hooks и documented runbooks;
- если historical tooling-модуль временно отсутствует в дереве `/int`, его не включаем в актуальную верхнеуровневую карту до фактического возвращения checkout.
