# OpenSpec Instructions

В `/int/tools` OpenSpec является обязательным governance-слоем для любых tracked tooling/process mutations. Локальный lifecycle здесь не optional bootstrap, а canonical process gate для repo-owned tooling.

## Source of truth
- Назначение репозитория, ownership и process-specific ограничения живут в `../AGENTS.md` и `../README.md`.
- Machine-wide правила работы, lockctl и mode-lattice живут в `/int/AGENTS.md`.
- `openspec/specs/**` и `openspec/changes/**` в этом репозитории являются каноническим source-of-truth для tracked tooling/process governance внутри `/int/tools`.

## TL;DR
- Не мутируйте tracked tooling/process assets без owner-approved change package в `openspec/changes/<change-id>/`.
- `SPEC-MUTATION` обязателен не только для `public API/contracts`, `schema/DB`, capability boundaries и breaking changes, но и для любых tracked tooling mutations этого репозитория.
- В `EXECUTE` разрешена только реализация по уже согласованному active change; прямой mutate-first path без change package запрещён.
- Если релевантный spec/change уже существует, его нужно читать и обновлять в пределах согласованного scope, а не создавать параллельный lifecycle.
- Перед любой файловой мутацией соблюдайте repo-local и machine-wide `lockctl` policy.
- Перед любым локальным commit по spec/process-изменениям обязательно добавить в индекс новые файлы текущего scope и повторно выполнить `git add` для уже staged путей после каждой дополнительной правки; commit по устаревшему состоянию индекса запрещён.

## Modes
- `EXECUTE`: реализация по уже согласованному active change без расширения scope.
- `PLAN`: анализ и планирование без lifecycle-мутаций; читать только summary/headers по необходимости.
- `SPEC-MUTATION`: создание/обновление `proposal.md`, `tasks.md`, `design.md` и spec-deltas для tracked tooling/process changes.
- `FINISH`: closing pipeline без расширения scope и без запуска нового OpenSpec lifecycle.

## Mode boundaries
- В `EXECUTE` и `FINISH` не создавайте новый lifecycle "на всякий случай", но обязаны опираться на уже согласованный active change/spec.
- В `PLAN` не создавайте scaffold и не меняйте lifecycle state.
- В `SPEC-MUTATION` сначала найдите существующий spec/change через `openspec list`, `openspec list --specs`, `openspec show <item>`.
- Если подходящего spec/change нет, остановитесь и запросите явное одобрение владельца перед созданием нового `change-id` или capability.

## Objective Ambiguity Gate
Ambiguity считается значимой только при неясности:
1. `public API/contracts`;
2. схемы БД;
3. границ capability;
4. security/performance гарантий.

Если эти критерии не сработали, для read-only анализа можно использовать локальный контекст репозитория. Для tracked tooling mutations OpenSpec всё равно остаётся обязательным process gate.

## Lifecycle policy
- Любая tracked-мутация repo-owned tooling должна иметь active change package и релевантную canonical spec.
- Создание `proposal.md`, `tasks.md`, `design.md` и spec-deltas разрешено только после явного owner approval.
- По умолчанию предпочитайте обновление уже существующего approved spec/change вместо создания нового.
- Перед handoff используйте только релевантные проверки (`openspec validate ...` нужен только если вы реально меняли spec/change lifecycle).

## Catalog note
- `openspec/project.md` описывает governance model именно для `/int/tools`, а не заменяет root repo docs.
- За фактической архитектурой, ветками, ownership и host-ограничениями всегда идите в root `README.md`, root `AGENTS.md` и `/int/AGENTS.md`.

## Spec-First Policy
- Главный приоритет любой реализации — согласованная актуальная спека (OpenSpec / approved spec source-of-truth для контура).
- Если спеки нет, она неполная, противоречивая или не фиксирует API/contracts/capability boundaries, сначала нужно довести спеку до согласованного состояния и только потом приступать к реализации.
- Изменения API, RPC, schema contracts, payload shape, capability boundaries и access semantics без зафиксированной и согласованной спеки запрещены.
- Если реализация расходится со спекой, приоритет у спеки; сначала исправляется/уточняется spec-source-of-truth, затем код.
- Любой owner-facing triage обязан явно ответить: какая спека является source-of-truth, полна ли она и разрешает ли текущую реализацию.
