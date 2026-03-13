# AGENTS — Stage-Gate Playbook scripts

## TL;DR
- Stage-gate пайплайн остаётся основой: Intake (TL) → Архитектура → Реализация → QA → InfoSec → DevOps release → Tech Writer. Gate’ы фиксируют контроль, но не блокируют работу автоматически — итог всегда за TL.
- Рабочая ветка одна — `main`. Все изменения делаем прямо в ней; `agent_sync.yaml` служит журналом задач и блокировок файлов.
- Отдельного `dev`-контура у `/git/scripts` нет; любые process/docs changes фиксируются локально в `main`, а push требует обычного ручного контроля diff и секретов.
- Перед каждым `git push` выполняем визуальный аудит diff и истории, проверяем, что реальные секреты отсутствуют. Конфиденциальные значения держим в `.env`, в репозитории публикуем лишь шаблоны.

## Stage-Gate pipeline
0. **Funnel upkeep** — README.md, `agent_sync.yaml`, `AGENTS.md` и handoff-документы актуализируем по мере изменения задач.
1. **Intake / TL-Gate-0** — TL принимает запрос, описывает scope, назначает роли, создаёт запись в `agent_sync.yaml` (`status: Planned`) с перечислением задач и блокируемых файлов.
2. **Architecture / TL-Gate-1** — Architect/TL подтверждает инварианты, обновляет ADR/README, отмечает в `agent_sync` переход на `In Progress`.
3. **Implementation / TL-Gate-2** — Разработчики работают в ветке `main`, предварительно резервируя файлы в `agent_sync`. Коммиты atomic. По готовности меняем `status` на `Review`.
4. **Review / TL-Gate-3** — Reviewer проверяет изменения в `main`, фиксирует решения и проверки секретов в `note`. TL нужные фиксы координирует, gate не блокирует.
5. **QA / TL-Gate-4** — QA запускает тесты, оформляет отчёты в `reports/test/*`, обновляет запись (`status: QA` → `Done`) и освобождает пути.
6. **InfoSec advisory / TL-Gate-5** — InfoSec прогоняет сканеры (detect-secrets, semgrep и т.д.), добавляет Must/Should/Could в note. Рекомендации обязательны к планированию, но не стопорят релиз.
7. **DevOps release / TL-Gate-6** — DevOps собирает артефакты, готовит runbook и smoke. TL фиксирует в `agent_sync` готовность к релизу.
8. **Tech Writer / TL-Gate-7** — Tech Writer обновляет README/Changelog, handoff-отчёты и закрывает запись (`status: Done`).

## Роли и границы
- **Team Lead / Router** — intake, декомпозиция, handoff, ревью, контроль `agent_sync`, аудит секретов.
- **Architect** — технические инварианты, ADR, ограничения, поддержка TL.
- **Developer** — реализация в `main`, тесты, документация, обновление `agent_sync` (задачи/пути/статус).
- **Reviewer** — code review, контроль секретов, обновление note в `agent_sync`.
- **QA** — smoke/pytest/manual, отчёты, разблокировка путей.
- **InfoSec** — сканы, рекомендации, фиксация результатов в `agent_sync`.
- **DevOps** — сборки, деплой, runbook, smoke, подтверждение готовности релиза.
- **Tech Writer** — финализация документации и changelog.

Каждое изменение статуса/блокировки обязательно отражаем в `agent_sync.yaml`. Если файлы больше не нужны, удаляем их из `paths` сразу, чтобы освободить коллегам.

## Git-поток
- `main` — единственная рабочая ветка. Коммиты делаем поверх неё, соблюдая порядок gate’ов и резервирование файлов.
- Отдельный release/promote-контур для `/git/scripts` не используется; ручной review и секрет-аудит обязательны перед каждым push.
- Force-push в `main` допускается только TL при аварии и фиксируется в `agent_sync` (`status: Incident`).

## agent_sync.yaml
- Формат единый для всех проектов:
  ```yaml
  agent_sync:
  - since: '2025-09-28T09:00:00Z'
    owner: codex-cli::teamlead
    branch: main
    tasks:
    - Навести порядок в README
    paths:
    - README.md
    - punctb/env
    ttl: 0
    status: In Progress  # Planned | In Progress | Review | QA | InfoSec | DevOps | TechWriter | Done | Blocked | Incident
    note: 'Резерв на время правок, gate остаётся консультативным.'
  ```
- Поля `tasks` и `paths` обязательны: перечисляем конкретные задачи и фактически заблокированные файлы/каталоги.
- `since` — UTC в ISO8601, `ttl` в минутах (0 = без таймаута). Историю не обнуляем, она служит журналом.
- Если несколько агентов работают параллельно, TL распределяет файлы через отдельные записи в `agent_sync`.

## Контроль секретов
- Регулярно запускаем `detect-secrets scan` (или аналог) и проверяем diff.
- Перед пушем: `git status`, `git diff`, убедиться, что `.env` и прочие секреты не попадут в историю.
- Обнаружили утечку — немедленно ревокуем, чистим историю (filter-repo/BFG), создаём запись с `status: Incident` и планом устранения.

## Отчёты и документация
- README.md — основной источник: roadmap, conventions, workflow, changelog.
- QA/InfoSec/DevOps отчёты складываем в `reports/` с датой и ответственным в названии.
- GateRecord/handoff докуменируем в `reports/` или `sessions/` (при введении каталога).

## Самопроверка TL перед push в `main`
- [ ] Все записи в `agent_sync` закрыты или переведены в follow-up.
- [ ] Секреты и конфиги перепроверены.
- [ ] README/Changelog обновлены.
- [ ] Тесты/линтеры зелёные, smoke пройден.
- [ ] Follow-up по Must-рекомендациям InfoSec заведены.

## Инциденты
- Любое нарушение процесса, конфликт или экстренный force-push фиксируется как запись с `status: Incident`, описанием и планом стабилизации.
- После устранения TL переводит запись в `Done` и добавляет ссылку на постморем/отчёт.
