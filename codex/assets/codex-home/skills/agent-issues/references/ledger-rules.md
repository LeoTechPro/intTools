# Coordctl / кратко про coordination leases
- В начале каждого turn читай `/int/AGENTS.md` и проектный `AGENTS.md`; machine-wide источник истины по coordination state живёт в `coordctl`.
- Добавляй/продлевай/снимай coordination sessions/intents через `coordctl` MCP/project wrappers; `issue` — optional metadata, его стоит ставить в reachable `INT-*` только для задач с issue-дисциплиной. Никогда не редактируй runtime storage вручную.
- На один path допустим один active writer-lock; если lease истёк, бери свежий лок вместо ручной правки старого runtime state.
- Контекст/progress (`goal`/`now`/`next`/`questions`/`risks`/`estimate`) хранится в Multica worklog/closed comments, а не в runtime lock state. Если использовался spawn-agent, укажи `spawn_agent_id` и `spawn_agent_utc` в Multica, а также `parent_session_id`, если он доступен.
- Не снимай и не перезаписывай активные локи других агентов.

## Поверхность tools
- CLI из PATH: `coordctl session-start|intent-acquire|status|heartbeat|release|cleanup|gc|merge-dry-run`.
- Canonical implementation owner: `/int/probe/client` (`probe coord ...`).
- Если PATH сломан, починить системный `coordctl` launcher; `/int/tools` больше не содержит Python fallback.
- Retired coordination tools не используются для текущих project locks и не являются fallback.
