# Lockctl / locks summary
- Read `/home/leon/.codex/AGENTS.md` and the project `AGENTS.md` at the start of each turn; machine-wide lock truth lives in `lockctl`, not in project-local YAML.
- Add/refresh/remove locks only for existing GitHub Issues issues (`gh issue view <number> -R <owner/repo>` must pass) and only via `lockctl`/project wrappers; never edit SQLite directly.
- One active writer-lock per path; if lease expired, acquire a fresh lock instead of patching old runtime state.
- Context/progress (goal/now/next/questions/risks/estimate) is kept in GitHub Issues worklog/closed, not in runtime lock state. If spawn-agent used, include `spawn_agent_id` and `spawn_agent_utc` in GitHub Issues (and `parent_session_id` if available).
- Do not release or overwrite other agents’ active locks.
