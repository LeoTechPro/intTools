# AGENTS — Stage-Gate Playbook scripts

## TL;DR
- Stage-gate пайплайн остаётся основой: Intake (TL) → Архитектура → Реализация → QA → InfoSec → DevOps release → Tech Writer. Gate’ы фиксируют контроль, но не блокируют работу автоматически — итог всегда за TL.
- Рабочая ветка одна — `main`. Все изменения делаем прямо в ней; runtime-локи на файлы ведём через machine-wide `lockctl`.
- Отдельного `dev`-контура у `/git/tools` нет; любые process/docs changes фиксируются локально в `main`, а push требует обычного ручного контроля diff и секретов.
- Перед каждым `git push` выполняем визуальный аудит diff и истории, проверяем, что реальные секреты отсутствуют. Конфиденциальные значения держим в `.env`, в репозитории публикуем лишь шаблоны.

## Stage-Gate pipeline
0. **Funnel upkeep** — README.md, `AGENTS.md` и handoff-документы актуализируем по мере изменения задач.
1. **Intake / TL-Gate-0** — TL принимает запрос, описывает scope, назначает роли и резервирует целевые файлы через `lockctl acquire`.
2. **Architecture / TL-Gate-1** — Architect/TL подтверждает инварианты, обновляет ADR/README и держит lease активным, пока затронуты зарезервированные файлы.
3. **Implementation / TL-Gate-2** — Разработчики работают в ветке `main`, предварительно резервируя конкретные файлы через `lockctl`. Коммиты atomic.
4. **Review / TL-Gate-3** — Reviewer проверяет изменения в `main`, фиксирует решения и проверки секретов в handoff/worklog. TL нужные фиксы координирует, gate не блокирует.
5. **QA / TL-Gate-4** — QA запускает тесты, оформляет отчёты в `reports/test/*` и освобождает свои пути через `lockctl release-path`.
6. **InfoSec advisory / TL-Gate-5** — InfoSec прогоняет сканеры (detect-secrets, semgrep и т.д.), добавляет Must/Should/Could в отчёт. Рекомендации обязательны к планированию, но не стопорят релиз.
7. **DevOps release / TL-Gate-6** — DevOps собирает артефакты, готовит runbook и smoke. Готовность к релизу фиксируем в handoff/report, а не в отдельном YAML-журнале.
8. **Tech Writer / TL-Gate-7** — Tech Writer обновляет README/Changelog, handoff-отчёты и закрывает рабочий цикл.

## Роли и границы
- **Team Lead / Router** — intake, декомпозиция, handoff, ревью, контроль `lockctl`, аудит секретов.
- **Architect** — технические инварианты, ADR, ограничения, поддержка TL.
- **Developer** — реализация в `main`, тесты, документация, резервирование своих файлов через `lockctl`.
- **Reviewer** — code review, контроль секретов, фиксация замечаний в handoff/worklog.
- **QA** — smoke/pytest/manual, отчёты, разблокировка путей.
- **InfoSec** — сканы, рекомендации, фиксация результатов в отчётах/handoff.
- **DevOps** — сборки, деплой, runbook, smoke, подтверждение готовности релиза.
- **Tech Writer** — финализация документации и changelog.

Каждое изменение блокировок выполняем через `lockctl`, а статус/handoff фиксируем в README, отчётах или issue соответствующего проекта. Если файлы больше не нужны, снимаем лок сразу, чтобы освободить коллегам путь.

## Git-поток
- `main` — единственная рабочая ветка. Коммиты делаем поверх неё, соблюдая порядок gate’ов и резервирование файлов.
- Отдельный release/promote-контур для `/git/tools` не используется; ручной review и секрет-аудит обязательны перед каждым push.
- Force-push в `main` допускается только TL при аварии и фиксируется в incident/handoff-отчёте.

## lockctl
- Machine-wide runtime source-of-truth по локам — `lockctl`; legacy YAML-журнал больше не используем.
- Минимальный цикл для одного файла:
  ```bash
  lockctl acquire --repo-root /git/tools --path AGENTS.md --owner codex:<session> --lease-sec 900
  lockctl status --repo-root /git/tools --path AGENTS.md --format json
  lockctl release-path --repo-root /git/tools --path AGENTS.md --owner codex:<session>
  ```
- Локи ставим только на конкретные файлы; каталоги не резервируем.
- Lease держим коротким и продлеваем при долгой правке; истёкшую запись не считаем активной.
- Если задача привязана к GitHub Issue продукта, добавляем `--issue <id>` по правилам этого проекта.

## Контроль секретов
- Регулярно запускаем `detect-secrets scan` (или аналог) и проверяем diff.
- Перед пушем: `git status`, `git diff`, убедиться, что `.env` и прочие секреты не попадут в историю.
- Обнаружили утечку — немедленно ревокуем, чистим историю (filter-repo/BFG), создаём incident/handoff-отчёт с планом устранения.

## Отчёты и документация
- README.md — основной источник: roadmap, conventions, workflow, changelog.
- QA/InfoSec/DevOps отчёты складываем в `reports/` с датой и ответственным в названии.
- GateRecord/handoff докуменируем в `reports/` или `sessions/` (при введении каталога).

## Самопроверка TL перед push в `main`
- [ ] Все активные локи `lockctl` закрыты или переданы по handoff.
- [ ] Секреты и конфиги перепроверены.
- [ ] README/Changelog обновлены.
- [ ] Тесты/линтеры зелёные, smoke пройден.
- [ ] Follow-up по Must-рекомендациям InfoSec заведены.

## Инциденты
- Любое нарушение процесса, конфликт или экстренный force-push фиксируется в incident-отчёте с описанием и планом стабилизации.
- После устранения TL закрывает incident, добавляет ссылку на постморем/отчёт и снимает оставшиеся локи.
