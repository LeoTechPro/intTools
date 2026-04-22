# Lockctl / locks summary
- Read `/int/AGENTS.md` and the project `AGENTS.md` at the start of each turn; machine-wide lock truth lives in `lockctl`.
- Add/refresh/remove locks via `lockctl` MCP/project wrappers; `issue` is optional metadata and should be set to a reachable `INT-*` only for issue-disciplined tasks. Never edit runtime storage directly.
- One active writer-lock per path; if lease expired, acquire a fresh lock instead of patching old runtime state.
- Context/progress (goal/now/next/questions/risks/estimate) is kept in Multica worklog/closed comments, not in runtime lock state. If spawn-agent used, include `spawn_agent_id` and `spawn_agent_utc` in Multica (and `parent_session_id` if available).
- Do not release or overwrite other agents’ active locks.
