Всегда отвечай пользователю на русском языке, если иное явно не указано.
Если в рабочей директории или её родителях обнаружены `AGENTS.md` или `agents.md`, прочитай их перед выполнением задач и следуй им с максимальным приоритетом.
Лаконично фиксируй выполняющиеся действия и поясняй обоснование шагов в выводах.

## Абсолютный Gate Одобрения Владельца (приоритетный override)
- Запрещено выполнять любые действия, которые владелец явно не одобрил, **ни в каком виде**.
- Явное одобрение обязательно для любых изменений: создание/редактирование/удаление/перемещение файлов, реорганизация структуры, слияние/разделение заметок, сокращение/переформулирование контента, запуск изменяющих скриптов и команд.
- Отсутствие прямого запроса или прямого «да» = запрет на действие; в таком случае допустимы только чтение контекста и уточняющий вопрос владельцу.
- Запрещено подменять согласованный scope «улучшениями», «оптимизациями», «адаптацией» или любыми косвенными изменениями без отдельного явного одобрения.
- Любое обнаруженное расхождение между текущими действиями и явным одобрением владельца требует немедленной остановки и запроса дальнейших инструкций.
- Этот раздел имеет приоритет над всеми конфликтующими правилами ниже.

## Базовый режим работы
- Если запрос неоднозначен или противоречив, сначала уточни требования.
- Если запрос однозначен и не требует выбора/разрешений, выполняй до конца без паузы на подтверждение.
- Фраза владельца «НЕ ТРОГАЙ ДЕРЕВО» = строгий запрет менять нерелевантные файлы/зоны.
- Тон всегда нейтральный.

## Mode Lattice (обязательно)
Перед началом работы определяй режим:
1. `EXECUTE` — реализация в текущем scope.
2. `PLAN` — планирование без мутации спецификаций.
3. `SPEC-MUTATION` — изменение proposal/spec lifecycle.
4. `FINISH` — закрытие текущей задачи без расширения scope.

По умолчанию режим = `EXECUTE`.

Триггеры `FINISH`:
- `Завершайся`
- `Finish`
- `Wrap up`
- `Close the loop`

Границы:
- `EXECUTE` и `FINISH`: не читать handbook/spec "на всякий случай".
- `PLAN`: читать только summary/headers, не запускать lifecycle.
- `SPEC-MUTATION`: lifecycle разрешён полностью.
- `FINISH`: выполнять closing pipeline (`diff review -> targeted fixes -> required checks -> migration gate(if needed) -> issue/worklog -> issue-bound commit -> optional push gate`).

## Objective Ambiguity Gate
Ambiguity считается значимой только при неясности:
1. `public API/contracts`;
2. схемы БД;
3. границ capability;
4. security/performance гарантий.

Если критерии не сработали, не открывай handbook/spec по умолчанию: решай через локальный контекст и точечные уточнения.

## Skills Loading Rule
- Загружай skill только если он явно вызван владельцем или задача контекстно попадает в его домен.
- Запрещён eager-load всех skills.
- В `FINISH` используй только процессно-релевантные skills текущей задачи.

## Local Project Priority
Если локальный `AGENTS.md` проекта задаёт path/process-specific правила, они имеют приоритет над глобальными правилами этого файла в рамках данного проекта.

## Codex Runtime Layout
- Самописный versioned tooling для Codex CLI хранится только в `/int/tools/codex/**`.
- `~/.codex` / `C:\Users\intData\.codex` используются только для native runtime-state, обязательных runtime instructions и тех home-level файлов, которые сам Codex требует именно там.
- Не использовать `~/.codex/scripts` как source-of-truth для самописных publish/helper scripts, если эти файлы можно держать в versioned `/int/tools/codex`.
- Для контуров под `D:\int` policy source-of-truth распределён по repo-local `AGENTS.md`; отдельный общий файл в корне каталога не используется.
- На `vds.intdata.pro` canonical remote users разделены так: IntData automation/deploy работает под `intdata`, Codex remote work — под `agents`, OpenClaw runtime/service — под `agents`.
- Автоматизированные действия под `leon` на `vds.intdata.pro` запрещены без прямого письменного разрешения владельца.

## Machine-wide lock policy
- Для любых файловых мутаций через Codex/OpenClaw на этой машине обязателен предварительный `lockctl acquire` по конкретному файлу до начала правки.
- Источник истины по активным локам: `lockctl` (CLI/MCP). Каноническое ядро лежит в `/int/tools/lockctl/lockctl_core.py`; CLI entrypoints: `/int/tools/lockctl/lockctl.py`, `/int/tools/lockctl/lockctl`, `/int/tools/lockctl/lockctl.ps1`, `/int/tools/lockctl/lockctl.cmd`; MCP entrypoint: `/int/tools/codex/bin/mcp-intdata-cli.py --profile intdata-control`. Lease-state хранится в локальной SQLite; проектные YAML-ledger не являются runtime truth.
- Лок должен жить только на окно реальной мутации и продлеваться heartbeat'ом, если правка длится дольше одного lease.
- После завершения правки лок должен сниматься через `lockctl release-path` или `lockctl release-issue` без ожидания окончания всей сессии.
- Для проектов с issue-discipline owner/agent обязан указывать issue id при `lockctl acquire`.
- Для lock-policy это глобальное правило имеет приоритет над project-local `AGENTS.md`: локальный проект не может ослабить обязательность `lockctl`, а может только добавлять более строгие требования поверх него.

## Запуски и кэши
- Любые команды, создающие tool cache или временные артефакты, запускай из корня целевого проекта, а не из произвольного каталога внутри `/int`.
- Cross-repo запуск тестов и линтеров по абсолютным путям из чужого `cwd` запрещён, если он может выбрать `rootdir=/int` и оставить кэш на верхнем уровне дерева.
- Если такой запуск неизбежен, явно задавай target root и cache dir в project-local ignored path или `/int/.tmp/<project>`, но не в корне `/int`.

## Безопасность и рисковые операции
- Потенциально разрушительные действия (`удаление`, `reset`, `перезапись истории`, `перезапись файлов`) выполняй только после явного подтверждения владельца.
- Операции с удалёнными сервисами/репозиториями выполняй только по прямому запросу владельца или по явно описанному обязательному шагу утверждённого процесса.
- Для любой задачи с мутациями в `/int/*` обязателен двухфазный sync-gate:
  - `start`: `python /int/tools/scripts/codex/int_git_sync_gate.py --stage start` (Linux) или `python D:/int/tools/scripts/codex/int_git_sync_gate.py --stage start` (Windows); по умолчанию gate работает только с текущим checkout.
  - `finish`: `python /int/tools/scripts/codex/int_git_sync_gate.py --stage finish --push` (Linux) или `python D:/int/tools/scripts/codex/int_git_sync_gate.py --stage finish --push` (Windows); finish gate делает `fetch -> verify -> push -> post-push fetch`, без auto-merge/rebase.
- Запрещено начинать правки без успешного `start` и запрещено завершать задачу с локальными commit-ами `ahead>0`.
- `git pull --ff-only` на clean tree с валидным upstream выполняй только в `start`; для старого массового scan всех top-level repo используй явный `--all-repos`. Если дерево грязное, upstream отсутствует или fast-forward не проходит, фиксируй это как git-блокер и эскалируй владельцу.
- Перед любым локальным commit обязательно добавить в индекс новые файлы текущего scope и повторно выполнить `git add` для уже staged путей после каждой дополнительной правки; commit по устаревшему состоянию индекса запрещён.
- В `FINISH` `git push` выполняй только по явному разрешению владельца или по обязательному явному шагу процесса (например, `issue:push:done`).
- Локальный `git add`/`git commit` по умолчанию остаётся дисциплиной согласованного scope: агент коммитит свои/согласованные правки, если владелец явно не указал включить больше.
- Если владелец явно велит `push/publish/выкатывай/публикуй`, агент обязан либо публиковать уже подготовленное publication-state как есть, либо остановиться и запросить инструкцию при блокере/неоднозначности.
- При такой owner-команде запрещено самостоятельно решать, какие чужие или "не свои" правки скрыть, stash'нуть, откатить или отложить, если они уже входят в publication-state.
- Для этого приватного репозитория `.codex` хранение `env`/секретов в git разрешено явным решением владельца; ограничение относится к публикации секретов во внешние публичные контуры.

## High-Risk Repo-Owned Tooling
- Для repo-owned high-risk tooling в `/int/tools` machine-readable registry живёт в `/int/tools/codex/config/agent-tool-routing.v1.json`.
- Resolver CLI `/int/tools/codex/bin/agent_tool_routing.py` обязан возвращать только `resolved` или `blocked` для runtime binding resolution.
- Blocked repo-owned capability не может неявно переключаться на verified skill; fallback допустим только если он явно перечислен как approved metadata в registry.
- Актуальный deduplicated MCP surface в `@int-tools`:
  - `intdata-control` (вместо `lockctl`, `multica`, `openspec`, `intdata-governance`, `intdata-routing`, `intdata-delivery`, `gatesctl`);
  - `intdata-runtime` (вместо `intdata-host`, `intdata-ssh`, `intdata-browser`, `intdata-vault`).
- Публичные tool names без alias:
  - governance: `routing_validate`, `routing_resolve`, `sync_gate`, `publish`, `gate_status`, `gate_receipt`, `commit_binding`;
  - runtime: `host_preflight`, `host_verify`, `host_bootstrap`, `recovery_bundle`, `ssh_resolve`, `ssh_host`, `browser_profile_launch`.
- Удалённые plugin IDs/tool names запрещено использовать в новых AGENTS/skills/runbooks.
- Для publish family canonical engine root = `/int/tools/delivery/bin`; `codex/bin/publish_*.ps1` не являются active compatibility surface.
- Для Firefox/SSH/host launcher family canonical engine root = `/int/tools/codex/bin`; shell/cmd/PowerShell wrappers не являются source-of-truth.

## Postgres по умолчанию
- Подключение по умолчанию: локальный сокет `sudo -u postgres psql -d <POSTGRES_DB>`.
- `<POSTGRES_DB>` берётся из `.env` проекта (сначала рабочий `.env`, fallback на `.env.example`).
- Вопросы про `POSTGRES_HOST/PORT/USER` задавай только если локальный сокет недоступен.

## Ролевые границы
- `architect-role`: системная архитектура и модульные границы (без архитектуры БД).
- `dba-role`: архитектура данных/БД, ревью миграций, индексы/RLS/ACL (без выполнения миграций).
- `devops-role`: выполнение миграций/сборок/деплоя, логи/smoke/rollback (без проектирования).
- `backend-review`: сервисная логика и подготовка миграций (применение через devops-role после DBA-gate).
- Роли не заходят в чужие зоны ответственности.

## DB/миграции
- Для DB/сетевых/миграционных решений обязателен ручной review человека.
- DBA-gate считается пройденным, если `dba-role` зафиксировал `DBA-gate (OK)` в GitHub Issues.
- Если применение миграции входит в исходную задачу и контур локальный, `devops-role` выполняет миграцию без отдельной команды владельца.

## Telegram (OpenClaw)
- Использовать runtime: `openclaw-gateway.service` + `~/.openclaw/openclaw.json`.
- Legacy bridge `/home/leon/.codex/tools/telegram_bridge` удалён и больше не используется.
- Доступ `exec/write/process` разрешён только владельцу (по allowlist в OpenClaw-конфиге).
- Мониторинг и алерты идут через `/int/probe/bridge/probe_bridge.py` в `@AgentIntDataBot`.
- На `vds.intdata.pro` этот runtime должен жить под пользователем `agents`, а не под `leon`.

