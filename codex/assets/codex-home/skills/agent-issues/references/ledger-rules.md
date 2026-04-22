# Lockctl / кратко про локи
- В начале каждого turn читай `/int/AGENTS.md` и проектный `AGENTS.md`; machine-wide источник истины по локам живёт в `lockctl`.
- Добавляй/продлевай/снимай локи через `lockctl` MCP/project wrappers; `issue` — optional metadata, его стоит ставить в reachable `INT-*` только для задач с issue-дисциплиной. Никогда не редактируй runtime storage вручную.
- На один path допустим один active writer-lock; если lease истёк, бери свежий лок вместо ручной правки старого runtime state.
- Контекст/progress (`goal`/`now`/`next`/`questions`/`risks`/`estimate`) хранится в Multica worklog/closed comments, а не в runtime lock state. Если использовался spawn-agent, укажи `spawn_agent_id` и `spawn_agent_utc` в Multica, а также `parent_session_id`, если он доступен.
- Не снимай и не перезаписывай активные локи других агентов.

## Поверхность tools
- Предпочтительно MCP/plugin: `lockctl_acquire`, `lockctl_renew`, `lockctl_release_path`, `lockctl_release_issue`, `lockctl_status`, `lockctl_gc`.
- CLI fallback из PATH: `lockctl acquire|renew|release-path|release-issue|status|gc`.
- Universal fallback только когда PATH сломан и project policy это разрешает: `python /int/tools/lockctl/lockctl.py ...`.
