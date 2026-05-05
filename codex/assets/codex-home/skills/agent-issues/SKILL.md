---
name: agent-issues
description: 'Multica-first процесс работы с задачами агентов: Multica Issues, runtime lockctl, worklog/closed, commit-гейты и движение статусов. Используй для любых tracked-мутаций файлов, работ с issue, взятия/снятия локов, Multica status/worklog и closure.'
metadata:
  knowledge_mode: hybrid-core-reference
  last_verified_at: "2026-05-01"
  refresh_interval_days: 30
  official_sources:
    - https://multica.intdata.pro
---

# Agent Issues

## Ядро процесса (стабильное)
- Работай через Multica Issues как единственный task-control-plane для агентских задач.
- Используй официальный документированный `multica` CLI для чтения/записи issues; если в runtime установлен официальный Multica MCP plugin (`mcp__multica__`), можно использовать его. Не используй `intdata-control` как Multica-прослойку.
- Если Multica недоступна, задача считается заблокированной: остановись, сообщи владельцу конкретный блокер и продолжай без Multica только после явного разрешения владельца.
- Привязывай реализацию к Multica issue + lock-flow проекта, если lock-flow существует.
- Поддерживай lock state через runtime `lockctl`; если доступен MCP/plugin tool surface, используй его вместо direct CLI, иначе используй CLI `lockctl` из PATH.
- В `FINISH` выполняй closure-процедуры по текущему Multica issue; push/PR/remote-операции — только при явном разрешении.

## Цель
Работать с Multica Issues и проектным lock-flow в любом репозитории без hardcoded paths.
- OpenSpec = источник требований/контекста; Multica Issues = трекинг исполнения, worklog, статусы и история runs.
- В MCP-enabled runtime используй project-approved OpenSpec MCP tools для OpenSpec list/show/status/validate/lifecycle операций; direct `openspec` или repo-local `codex/bin/openspec*` wrappers не являются PATH fallback.
- Используй issue-linked locks только когда проект/задача требует issue-дисциплину; `lockctl.issue` — optional metadata, и для non-project/pre-intake work локи могут браться без `INT-*` issue.
- Создавай новые задачи только после утверждённой OpenSpec-спеки/дельты или прямого запроса владельца. Консультации без правок остаются комментариями в текущем Multica issue.
- Codex `/goal` = runtime continuation state для текущего Codex thread; он помогает не терять objective между resume/turns, но не является durable source-of-truth.
- Не заменяй `/goal`-ом OpenSpec, Multica, worklog, acceptance criteria, commit history или release notes.
- Не читай и не изменяй Codex-owned goal storage под `CODEX_HOME` из repo hooks/scripts/custom automation; допускается только read-only inspection, когда это прямо нужно для диагностики.
- Не дёргай владельца без блокеров: если задача однозначна и решаема в рамках правил, выполняй и фиксируй результат в Multica issue; вопросы задавай только при конфликте требований, нехватке данных, необходимости санкции на high-risk действия или недоступности Multica.

## Codex `/goal` discipline
- Для длинной issue-bound работы можешь создать/обновить `/goal` с форматом: `<INT-*> <repo> <scope>: <inventory> -> <mutation> -> <verification> -> <worklog/closeout>`.
- Перед мутациями всё равно сначала прочитай live Multica issue, relevant OpenSpec, repo state и project rules; `/goal` не доказывает актуальное состояние.
- При pause/handoff укажи в Multica worklog/comment: `Goal`, `Current state`, `Verified`, `Next action`.
- Перед successful closeout перенеси durable факты в OpenSpec/Multica/git, затем пометь `/goal` complete/cleared или явно укажи, что goal остался active/paused/blocked.
## Обязательный gate доступности Multica
1. Перед началом нетривиальной работы определить текущий Multica issue.
   - Если задача пришла из Multica, используй эту issue.
   - Если issue нет, create/import её в Multica до реализации только когда это разрешает владелец или процесс проекта.
   - Для imported/backlog work, который не должен стартовать автоматически, создавай issue без agent assignee или в `backlog`.
2. Проверь доступ к Multica самым дешёвым доступным official check:
   - `multica issue list`, `multica issue get <INT-*>`, or `multica issue search <query>`.
   - Если установлен официальный Multica MCP plugin, допустима его эквивалентная read-only проверка.
3. Если Multica недоступна:
   - Не продолжай выполнение как untracked task без явного owner approval на это исключение.
   - Сообщи: attempted plugin tool/API, ошибку, затронутую задачу и самый безопасный следующий шаг.

## Обязательный gate коммитов Multica
- Каждый local commit для agent work должен содержать текущий Multica task id в формате `INT-*` в subject или body.
- Отсутствие reachable Multica issue id блокирует `git commit`, push, deploy, publication, создание PR и любой close-out flow, который публикует код.
- Если commit в текущем publication scope не содержит `INT-*`, остановись и сообщи блокер; исправляй commit metadata только самым безопасным project-approved способом и с owner approval, где оно требуется.

## Обязательный lockctl gate
- Перед любой tracked-мутацией файла в governed repo возьми `lockctl` lease на каждый конкретный file path.
- Предпочитай MCP/plugin tools, если они доступны: `lockctl_acquire`, `lockctl_renew`, `lockctl_release_path`, `lockctl_release_issue`, `lockctl_status`, `lockctl_gc`.
- Примеры CLI fallback:
  - Windows/Linux/macOS PATH: `lockctl acquire --repo-root <repo> --path <file> --owner <owner> --issue INT-* --lease-sec 3600`
  - Статус: `lockctl status --repo-root <repo> --issue INT-* --format json`
  - Снять лок с одного пути: `lockctl release-path --repo-root <repo> --path <file> --owner <owner>`
  - Снять локи по issue scope: `lockctl release-issue --repo-root <repo> --issue INT-*`
- Используй только file paths, никогда директории.
- Продлевай долгие правки до истечения lease.
- Снимай локи сразу после завершения, блокировки или handoff файлового scope.
- Никогда не редактируй lock SQLite/events/runtime storage вручную.
- `gatectl`/gate receipts — отдельный governance tooling и намеренно вне scope этого skill, если project-local правило явно не требует обратного.

## Рабочий процесс
1. Найди контекст проекта из текущего `cwd`.
   - Найди canonical lock path текущего проекта, `AGENTS.md` и `openspec/AGENTS.md`, если он есть.
   - Если есть несколько кандидатов lock path, выбери ближайший project-canonical path или спроси владельца.
   - Пример команды: `rg --files -g AGENTS.md -g SKILL.md`.

2. Прочитай правила проекта.
   - Открой `AGENTS.md` и `GEMINI.md`, если проект этого требует.
   - Если запрос включает планирование или правки, сначала открой `openspec/AGENTS.md` и релевантный change proposal/spec delta.
   - OpenSpec reference для любого репозитория: `openspec/AGENTS.md`, если он есть.
   - В MCP-enabled runtime используй project-approved OpenSpec MCP tools для discovery/validation/lifecycle OpenSpec.
   - Если scope включает создание или правку `SKILL.md`, загрузи официальный `$skill-creator` до файловых изменений; после правки запусти `quick_validate.py <skill-folder>` и проверь, что `SKILL.md` начинается с raw `---` без UTF-8 BOM.
   - Следуй проектной schema, consult IDs, templates и issue prefix.
   - Если `AGENTS.md` задаёт обязательные поля Worklog/Closed, убедись, что references/templates их включают.
   - Если ты spawned agent, следуй тем же правилам Multica issue и фиксируй `spawn_agent_id`/`spawn_agent_utc` в comments/worklog Multica.

3. Используй Multica CLI/API/UI как источник истины по задаче.
   - Предпочитай official `multica issue ...` commands для `list`, `get`, `search`, `runs`, `run-messages`, `create`, `update`, `assign`, `status` и `comment`.
   - Если syntax или behavior CLI неясны, перед мутациями проверь `multica --help`, `multica issue --help` или Multica API.
   - Считай неоднозначный assignee/name matching блокером или используй точные IDs.

4. Выбирай issue type/status осознанно.
   - Используй `references/issue-type-selection.md`.
   - Никогда не ставь `task` по умолчанию без обоснования, если в проекте есть typed issue metadata.

5. Если задача включает миграции БД, зафиксируй в acceptance обязательный backend-gate: `backend-role` должен пройти внутренний цикл review/apply/smoke до green и зафиксировать это в Multica issue без дополнительных согласований (если владелец не указал иное). Дополнительно фиксируй требования: версия миграции должна записываться в таблицу миграций проекта (`schema_migrations` или эквивалент), архивные миграции не применяются.

6. Держи локи синхронизированными.
   - Добавляй/продлевай/снимай локи через runtime `lockctl`; добавляй `issue=INT-*` только когда у задачи есть или требуется Multica issue.
   - Store locks only on file paths; directories are forbidden.
   - Если в рабочем дереве есть неожиданные изменения, не откатывай/не stash'и/не трогай их без прямого запроса владельца. Зафиксируй наблюдение в Multica issue handoff/worklog.
   - Если использовался spawn-agent, фиксируй `spawn_agent_id`, `spawn_agent_utc`, `parent_session_id` в Multica worklog/comment; progress остаётся в Multica.
   - Если лок исчез или TTL истёк, ставь новый лок по текущему Multica issue и не вмешивайся в чужие.
   - Никогда не редактируй lock runtime storage вручную.

7. Используй Multica для обновлений задачи.
   - Создавай, обновляй, комментируй, назначай, двигай status и закрывай через Multica CLI/API/UI.
   - Для multiline или non-ASCII comment/worklog content предпочитай `multica issue comment add <INT-*> --content-stdin` вместо длинного `--content`.
   - На этом Windows-host PowerShell pipe/here-string в external `multica ... --content-stdin` может испортить кириллицу и превратить её в `?`; не считай такой путь безопасным по умолчанию.
   - Если нужна надёжная кириллица из Windows shell, предпочитай `python`/`python -c` с `subprocess.run(..., input=content, text=True, encoding='utf-8')` и вызовом `multica issue comment add ... --content-stdin` или `--content`.
   - В bash/zsh safest pattern: `cat file.md | multica issue comment add <INT-*> --content-stdin` или heredoc в stdin.
   - Не используй shell output с уже сломанной кодировкой как источник текста для нового comment/worklog. Если terminal показывает кракозябры, считай подозрительными stdout/stderr или текущее codepage-decoding, а не обязательно сам исходный текст.
   - Если comment берётся из файла, файл должен быть UTF-8; prefer UTF-8 without BOM для промежуточных markdown/text artifacts.
   - Избегай PowerShell-паттернов, которые часто портят текст или quoting: ручной copy-paste длинных JSON-escaped строк, `Out-File` без явной encoding-стратегии, legacy shell pipelines с неясной перекодировкой, here-string/pipe в external CLI без round-trip проверки, и попытки скормить multiline русский текст через один `--content "..."`.
   - Перед отправкой важного русского комментария, если есть малейшее сомнение в shell encoding, сначала собери текст в UTF-8 источнике и только потом передай его в `--content-stdin`.
   - Для критичных owner-facing комментариев делай round-trip verification: сразу перечитай comment через `multica issue comment list ... --output json` и, если нужно, проверь содержимое через `python`/`json.loads`, а не глазами через potentially broken terminal rendering.

Примеры safe-write:

```powershell
python -c "import subprocess; content='Короткий комментарий без поломанной кодировки.\n- строка 1\n- строка 2\n'; subprocess.run(['multica','issue','comment','add','INT-123','--content-stdin'], input=content, text=True, encoding='utf-8', check=True)"

python -c "import pathlib, subprocess; content=pathlib.Path(r'.\comment.md').read_text(encoding='utf-8'); subprocess.run(['multica','issue','comment','add','INT-123','--content',content], text=True, encoding='utf-8', check=True)"
```

```bash
cat ./comment.md | multica issue comment add INT-123 --content-stdin

multica issue comment add INT-123 --content-stdin <<'EOF'
Короткий комментарий без поломанной кодировки.
- строка 1
- строка 2
EOF
```

Проверенный canary на этом host:
- PowerShell here-string -> `multica issue comment add ... --content-stdin` дал поломанный comment с `?`.
- `python subprocess` с явным `encoding='utf-8'` сохранил кириллицу корректно.

8. Пиши worklog после каждого значимого шага.
   - Используй `references/worklog-template.md`.
   - Указывай использованные tools и список изменённых файлов.
   - Если использовался spawn-agent, укажи `spawn_agent_id` и `spawn_agent_utc`, а также `parent_session_id`, если он доступен.
   - Если использовался wrapper fallback, укажи attempted official command/API, error/blocker, owner approval и точную fallback command.
   - Для worklog/comment с кириллицей применяй те же safe-write правила: UTF-8 source + `--content-stdin` по умолчанию.

9. Закрывай только когда acceptance criteria выполнены.
   - Используй `references/closed-template.md`.
   - Переводи Multica issue в `done`/`in_review`/`blocked` по политике проекта.

10. Handoff или pause.
   - Оставь Multica worklog/comment со следующими шагами и рисками.
   - Если использовался Codex `/goal`, включи `Goal`, `Current state`, `Verified`, `Next action` и goal status (`active`, `paused`, `blocked` или `complete`).
   - Используй `references/handoff-template.md` для handoff block, когда применимо.

11. Закрытие сессии.
   - Используй `references/session-close-checklist.md`.
   - Если владелец сказал «Завершайся», трактуй это как явную команду на полный цикл завершения: прогнать релевантные ревью/quality gates, обновить документацию, закрыть/перевести Multica issue где acceptance выполнен, отметить выполненные пункты чеклистов в OpenSpec, выполнить `git add`/`git commit` только своих релевантных правок при явном запросе/проектном правиле, затем снять локи и очистить `.agents/tmp` по правилам проекта.
   - Если использовался Codex `/goal`, не считай задачу закрытой, пока durable closeout не записан в OpenSpec/Multica/git; после этого clear/complete goal через доступный runtime UI/CLI или явно зафиксируй, что goal ещё активен.

12. Синхронизируй инструкции, если требуется.
   - Если меняешь `AGENTS.md`, синхронизируй `GEMINI.md` по правилам проекта. Делай это только когда владелец явно разрешил редактировать эти файлы.
   - Если проект использует zonal IDs, держи явные cross-links в comments/fields Multica issue; избегай local JSONL sync layers для состояния задачи.

## Справки
- references/ledger-rules.md
- references/issue-type-selection.md
- references/worklog-template.md
- references/closed-template.md
- references/handoff-template.md
- references/session-close-checklist.md

## Нестабильные справки (по требованию)
- Поведение Multica CLI/API — live system behavior. Предпочитай MCP plugin tools; если plugin coverage заблокирован и владелец разрешил fallback, перед действием проверь CLI syntax через `multica --help` / `multica issue --help` или deployed API.

## Gate актуальности
- Если с последней верификации прошло более `refresh_interval_days`, считай CLI/API syntax и plugin behavior потенциально устаревшими и проверяй их перед мутациями.
