# AGENTS — Stage-Gate Playbook scripts

## TL;DR
- Работаем только по stage-gate: Intake (TL) → Архитектура → Реализация → PR в `dev` → QA → InfoSec → DevOps release → Tech Writer.
- Единственный источник статуса — `agent_sync.yaml` (формат как в IntData/IntBridge). Все записи ведём на русском языке.
- Ветки: `dev` (рабочая) и `main` (релизная). Прямые коммиты в `main` запрещены; merge `dev → main` делает TL fast-forward’ом.
- Перед каждым `git push` вручную убеждаемся, что секретов нет в diff и истории. Конфиденциальные значения — только в `.env` (шаблоны публикуем отдельно).

## Stage-Gate pipeline
0. **Funnel upkeep** — README.md, `agent_sync.yaml` и `AGENTS.md` поддерживаем в актуальном состоянии; фиксируем идею → vision → conventions → tasklist → workflow.
1. **Intake / TL-Gate-0** — Team Lead принимает запрос, описывает scope, назначает роли, создаёт запись в `agent_sync.yaml` с `status: Planned`.
2. **Architecture / TL-Gate-1** — Architect (или сам TL) валидирует инварианты, оформляет ADR/черновик в README, обновляет запись (`status: In Progress`).
3. **Implementation / TL-Gate-2** — Developers работают в ветках `feature/<epic>/<task>-<role>` от `dev`, пишут тесты, обновляют docs. По завершении переводят запись в `Review`.
4. **PR → dev / TL-Gate-3** — Reviewer проверяет PR, следит за отсутствием секретов, добавляет вывод ревью в note. Merge в `dev` выполняет TL.
5. **QA / TL-Gate-4** — QA проверяет функциональность из ветки `dev`, формирует отчёт (`reports/test/*`), статус `QA` → `Done`, note содержит сводку.
6. **InfoSec advisory / TL-Gate-5** — InfoSec прогоняет сканеры (detect-secrets, semgrep, npm audit и прочее). Результаты фиксируем в отчёте и note.
7. **DevOps release / TL-Gate-6** — DevOps готовит runbook, smoke, миграции. TL fast-forward’ит `dev → main`, обновляет `agent_sync` и README (Changelog).
8. **Tech Writer / TL-Gate-7** — Tech Writer оформляет финальную документацию, закрывает запись в `agent_sync.yaml` (`status: Done`), прикладывает ссылки на отчёты.

## Роли и границы
- **Team Lead / Router** — intake, декомпозиция, handoff, ревью, merge, контроль `agent_sync`, финальный аудит секретов. Не пишет продуктивный код (кроме аварий).
- **Architect** — подтверждает технические инварианты, обновляет ADR, фиксирует ограничения. Не мержит код.
- **Developer (backend/frontend/scripts)** — реализует задачи, покрывает тестами, обновляет README/Changelog, готовит PR.
- **Reviewer** — проводит code review, следит за отсутствием секретов, фиксирует решение в note.
- **QA** — запускает тесты/смоук, оформляет отчёты в `reports/test/`.
- **InfoSec** — выполняет SAST/SCA/secret scan, заносит Must/Should/Could рекомендации.
- **DevOps** — отвечает за сборки, деплой, runbook, smoke.
- **Tech Writer** — финализирует документацию, README, Changelog.

Каждый агент обновляет `agent_sync.yaml` при смене статуса и после handoff. TL подписывает GateRecord только после проверки AC и границ ролей.

## Git-поток
- Рабочие ветки: `feature/<epic>/<task>-<role>` от `dev`.
- Merge в `dev` выполняет TL после ревью. Ребейз перед merge обязателен.
- Релиз: TL fast-forward’ит `dev → main`, отмечает релиз в README (Changelog) и `agent_sync.yaml`.
- Force-push разрешён только TL в аварии и фиксируется в note (`status: Incident`).

## agent_sync.yaml
- Формат общий:
  ```yaml
  agent_sync:
  - since: '2025-09-28T09:00:00Z'
    owner: codex-cli::teamlead
    branch: main
    paths: []
    ttl: 0
    status: Planned  # Planned | In Progress | Review | QA | InfoSec | DevOps | TechWriter | Done | Blocked | Incident
    note: 'Создан intake, задачки декомпозированы.'
  ```
- Время (`since`) — UTC, ISO8601. `paths` перечисляет рабочие файлы. `ttl` — минуты блокировки (0 = без тайм-аута).
- Историю не чистим: завершённые записи остаются для аудита.
- Скрипты синхронизации (например, `scripts/sync-agents.sh`) читают файл как единый источник правды.

## Контроль секретов
- Ежедневно прогоняем `detect-secrets scan` и проверяем diff.
- Перед пушем: `git diff --stat`, `git diff` визуально, проверяем `.env` и другие игноры.
- Секрет утёк — незамедлительно ревокуем, чистим историю (BFG/filter-repo), фиксируем инцидент в `agent_sync.yaml` (`status: Incident`).

## Отчёты и документация
- README.md содержит roadmap, conventions, workflow и changelog. Обновляем при каждом функциональном изменении.
- Отчёты (QA, InfoSec, DevOps) складываем в `reports/` с датой в имени.
- GateRecord/hand-off храним в `reports/` или `sessions/` (если добавим).

## Самопроверка перед merge
- [ ] Ссылки на эпик/задачу и AC отражены в README.md.
- [ ] Тесты и линтеры зелёные.
- [ ] Конфигурации и `.env` не содержат реальных секретов.
- [ ] Обновлены README/Changelog, agent_sync, handoff.
- [ ] GateRecords подписаны нужными ролями.

## Инциденты
- Любое нарушение процесса, утечка или авария — новая запись в `agent_sync.yaml` с `status: Incident`, описанием и планом стабилизации.
- TL координирует устранение, закрывает инцидент переводом в `Done` и ссылкой на постморем.
