# OpenSpec Instructions (policy-only bootstrap)

Этот репозиторий использует минимальный OpenSpec bootstrap. Локальный lifecycle spec/proposal здесь не является default execution path и не расширяет владелец-одобренный scope сам по себе.

## Source of truth
- Назначение репозитория, ownership и process-specific ограничения живут в `../AGENTS.md` и `../README.md`.
- Machine-wide правила работы, lockctl и mode-lattice живут в `/int/AGENTS.md`.
- `openspec/specs/**` и `openspec/changes/**` в этом репозитории считаются вспомогательным bootstrap-контуром, а не заменой root-документации.

## TL;DR
- Не создавайте новые `openspec/changes/<change-id>` и новые capability specs без явного одобрения владельца.
- `SPEC-MUTATION` допустим только для явно одобренной работы по `public API/contracts`, `schema/DB`, границам capability или breaking changes.
- В обычном `EXECUTE` используйте локальный repo context (`README.md`, `AGENTS.md`, код), а не OpenSpec lifecycle.
- Если релевантный spec/change уже существует, его можно читать и обновлять только в пределах согласованного scope.
- Перед любой файловой мутацией соблюдайте repo-local и machine-wide `lockctl` policy.

## Modes
- `EXECUTE`: реализация в согласованном scope без запуска proposal/spec lifecycle.
- `PLAN`: анализ и планирование без lifecycle-мутаций; читать только summary/headers по необходимости.
- `SPEC-MUTATION`: разрешён только по явному одобрению владельца и только для реально затронутых contracts/schema/capability changes.
- `FINISH`: closing pipeline без расширения scope и без запуска нового OpenSpec lifecycle.

## Mode boundaries
- В `EXECUTE` и `FINISH` не открывайте `openspec/project.md`, `openspec/specs/**` и `openspec/changes/**` "на всякий случай".
- В `PLAN` не создавайте scaffold и не меняйте lifecycle state.
- В `SPEC-MUTATION` сначала найдите существующий spec/change через `openspec list`, `openspec list --specs`, `openspec show <item>`.
- Если подходящего spec/change нет, остановитесь и запросите явное одобрение владельца перед созданием нового `change-id` или capability.

## Objective Ambiguity Gate
Ambiguity считается значимой только при неясности:
1. `public API/contracts`;
2. схемы БД;
3. границ capability;
4. security/performance гарантий.

Если эти критерии не сработали, задачу решаем через локальный контекст репозитория без OpenSpec-by-default.

## Lifecycle policy
- OpenSpec здесь используется как optional process layer, а не как обязательный handshake на каждую задачу.
- Создание `proposal.md`, `tasks.md`, `design.md` и spec-deltas разрешено только после явного owner approval.
- По умолчанию предпочитайте обновление уже существующего approved spec/change вместо создания нового.
- Перед handoff используйте только релевантные проверки (`openspec validate ...` нужен только если вы реально меняли spec/change lifecycle).

## Bootstrap note
- `openspec/project.md` в bootstrap-репозиториях не является полным handbook.
- За фактической архитектурой, ветками, ownership и ограничениями всегда идите в root `README.md`, root `AGENTS.md` и `/int/AGENTS.md`.
