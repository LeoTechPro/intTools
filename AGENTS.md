<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

⚠️ Сначала прочитайте [корневой AGENTS.md](/int/AGENTS.md).

# AGENTS — intTools

## Allowed scope

- machine-wide ops/process/tooling, hooks, bootstrap scripts и shared runbooks;
- внешние tooling contours для `intdata`, `crm`, `probe`, `codex` и соседних repos;
- repo-level docs по reusable tooling и host helpers.

## Source-of-truth ownership

- `/int/tools` владеет только reusable ops/process/tooling contour;
- business product-core и domain ownership остаются в соответствующих product repos;
- runtime state и реальные секреты живут во внешних host paths, а не в repo.

## What not to mutate

- не складывать сюда canonical product domains и user-facing product shells;
- не использовать repo как permanent runtime storage;
- не подменять локальные product README/AGENTS процессными копиями в tooling repo.

## Integration expectations

- reusable tooling хранится здесь, а не в корне `/int` и не в чужих product repos;
- product repos подключают этот contour извне через scripts, hooks и documented runbooks;
- repo остаётся machine-wide tooling layer, а не отдельным business runtime.

## Escalation triggers

- попытка превратить `/int/tools` в owner business product-core;
- перенос mutable runtime-state или секретов в tracked repo;
- дублирование локальных product-docs вместо ссылок на реальные owner repos.

## Git и завершение работы

- Перед новой работой в этом git-репозитории агент обязан проверить чистоту дерева и upstream текущей ветки; обязательный `git pull` выполняется только при clean tree и валидном upstream.
- Если дерево грязное, upstream отсутствует, upstream gone или `git pull` требует ручного решения, работа останавливается до явных инструкций владельца.
- Любая завершённая правка в `/int/tools` считается незавершённой, пока в пределах текущей задачи не создан как минимум один локальный commit в этом repo.
- `git push` и прочие remote-операции остаются отдельным шагом и не выполняются автоматически без owner approval или явного требования локального процесса.
