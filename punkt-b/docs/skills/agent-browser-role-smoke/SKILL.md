---
name: agent-browser-role-smoke
description: "Role-based smoke testing for punkt-b.pro via agent-browser (client/specialist/admin)."
---

# Agent Browser Role Smoke

## Goal
Fast role-level smoke for `punkt-b.pro` via `agent-browser` with fixed checks:
- `admin` permissions and deny markers;
- `specialist` permissions and deny markers;
- `client` permissions and deny markers.

Use this skill for quick agent triage and pre-handoff regression after UI/RBAC changes.
For business-priority checks (client full diag + specialist/admin key flows), use the key-scenarios runner from this same skill.

## When To Use
- Route/access updates in workspace/client zones.
- Permission-related changes (RBAC, guards, redirects, deny screens).
- Agent exploratory checks before converting scenario to deterministic Playwright E2E.

## Inputs
Environment variables:
- `BASE_URL` (default: `https://punkt-b.pro`)
- `WORKSPACE_PASSWORD` (default for e2e smoke context)
- `ADMIN_EMAIL` (default: `admin.demo@punkt-b.test`)
- `SPECIALIST_EMAIL` (default: `specialist.demo@punkt-b.test`)
- `CLIENT_EMAIL` (default: `client.demo@punkt-b.test`)
- `REPORT_PATH` (optional; default in `~/.codex/tmp/punkt-b`)

## Run
```bash
bash ops/agent-browser/agent_browser_role_smoke.sh
```

Custom accounts/base URL:
```bash
BASE_URL=https://punkt-b.pro \
WORKSPACE_PASSWORD='******' \
ADMIN_EMAIL='admin.demo@punkt-b.test' \
SPECIALIST_EMAIL='specialist.demo@punkt-b.test' \
CLIENT_EMAIL='client.demo@punkt-b.test' \
bash ops/agent-browser/agent_browser_role_smoke.sh
```

## Key Scenarios Mode
Run the extended business-priority suite:
```bash
bash ops/agent-browser/agent_browser_key_scenarios.sh
```

What this suite validates:
- authorized client: full `43 профессии` completion to `/diag/testing-end`;
- new client (public link): registration step and backend error detection;
- specialist: diagnostics assignment, results, clients, conclusion issuance;
- admin: users page, create-user modal, grant/revoke control availability.

Extra env for public new-client scenario:
- `PUBLIC_CLIENT_FIRST_NAME` (default `Тестовый`)
- `PUBLIC_CLIENT_FAMILY_NAME` (default `Клиент`)
- `PUBLIC_CLIENT_PHONE` (default `+7 900 000 00 00`)
- `PUBLIC_CLIENT_EMAIL` (default `public.demo@punkt-b.test`)

## Process Gate Mode
Use the process runner to integrate this into role pipelines:
```bash
MODE=handoff bash ops/agent-browser/agent_browser_gate.sh
```

Modes:
- `handoff` — quick mandatory gate (role smoke only).
- `full` / `release` — role smoke + key scenarios.
- `nightly` — scheduled role smoke + key scenarios.

Nightly soft-fail option:
```bash
MODE=nightly ALLOW_NIGHTLY_SOFT_FAIL=1 bash ops/agent-browser/agent_browser_gate.sh
```

## Output Contract
- `SMOKE_OK` + `REPORT_PATH=...` if checks passed.
- `SMOKE_FAIL` + failed check ids + `REPORT_PATH=...` if at least one check failed.
- JSON report contains:
  - role/account map;
  - per-check pass/fail;
  - failed check ids.

For key-scenarios mode:
- `SCENARIOS_OK` + `REPORT_PATH=...` if all checks passed.
- `SCENARIOS_FAIL` + failed check ids + `REPORT_PATH=...` if at least one check failed.

## Role Guidance
- `qa-role`: run full role-smoke before handoff, attach `REPORT_PATH` to worklog.
- `frontend-role`: run after route/guard/deny-screen edits.
- `backend-role`: run after RBAC/ACL changes that affect UI access shape.
- `teamlead-role`: use as lightweight gate before requesting deeper E2E pass.
- `devops-role`: run key-scenarios after env/config changes on staging/local contour.

Recommended cadence:
- pre-handoff: `MODE=handoff`
- release-candidate: `MODE=full`
- nightly monitoring: `MODE=nightly`

## Practical Notes
- Do not rely on URL only. Access can surface as:
  - deny section text;
  - workspace deny text;
  - 404 guard page.
- For ad-hoc steps, prefer specific selectors or `find first ...` in `agent-browser`.
  Ambiguous text locators can fail in strict mode.
- Keep per-role isolated sessions. Do not reuse one session for multiple roles.
