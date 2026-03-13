# Teamlead-first Role Opinion Orchestration

## Назначение
Этот регламент фиксирует process-first слой независимых role-мнений для крупных правок. Основная сессия остаётся исполнителем и owner-facing reporter; specialist opinions всегда приходят из независимых child-runs.

## Инварианты
- Любая major change определяется через `path + risk matrix` из `templates/swarm-risk-matrix.yaml`.
- Основная сессия не имитирует `frontend-role`, `frontend-design`, `backend-role`, `architect-role`, `dba-role`, `qa-role`, `devops-role`, `techwriter-role` внутри собственного reasoning.
- Независимость мнений обеспечивается отдельными `codex exec --ephemeral` запусками без shared transcript.
- Teamlead orchestrator обязателен перед green-milestone commit и в финальном finish.
- Milestone commit делается автоматически после зелёного workstream без отдельного owner prompt.
- Если acceptance checklist в issue зелёный, финальный путь — `issue:push:done` + cleanup issue-scoped `~/.codex/tmp/punctb`.

## Артефакты процесса
- Matrix classification: `templates/swarm-risk-matrix.yaml`
- Role opinion schema: `templates/role-opinion-result.schema.json`
- Orchestrator: `ops/teamlead/teamlead_orchestrator.sh`
- Helper classifier: `ops/teamlead/role_opinion_matrix.py`
- Runtime artifacts: `~/.codex/tmp/punctb/teamlead-orchestrator/<issue>/...`

## Роли по умолчанию
- Visual/UI change: `frontend-role` + `frontend-design`, при маршрутах/guard/entry additionally `qa-role`
- Backend runtime/API change: `backend-role`
- Schema/migration/RLS/ACL change: `dba-role` + `backend-role`
- Cross-zone или architecture/routing drift: `architect-role`
- Process/docs change: `techwriter-role`
- Deploy/runtime contour change: `devops-role`

## Цикл milestone
1. Основная сессия собирает рабочий scope.
2. `teamlead_orchestrator --mode milestone` классифицирует scope и запускает независимые role-opinions.
3. Если есть `request_changes`, orchestrator делает один bounded main-session-style fix loop внутри scope и перезапускает только проблемные роли.
4. После `ok` по opinions и обязательным gates основная сессия делает `issue:commit`.

## Цикл finish
1. `teamlead_orchestrator --mode finish` запускается по финальному scope/range в read-only режиме.
2. `issue:push:done` дополнительно проверяет acceptance checklist.
3. После успешного push и `issue:done` чистятся issue-scoped временные артефакты в `~/.codex/tmp/punctb`.
4. Владелец подключается только при `blocked`/`owner_choice_required`.
