## 1. Spec and scope

- [x] 1.1 Create Multica issue `INT-321` for the owner-requested v2rayA/Codex recovery source.
- [x] 1.2 Create OpenSpec package for the repo-owned tooling change.
- [x] 1.3 Record acceptance criteria for source location, runtime integration, and smoke checks.

## 2. Implementation

- [x] 2.1 Add repo-owned v2rayA core hook source.
- [x] 2.2 Add repo-owned Codex/v2rayA health script source.
- [x] 2.3 Add canonical recovery runbook under `/int/tools/codex/docs/runbooks/`.
- [x] 2.4 Update `README.md` with the canonical script/runbook paths.
- [x] 2.5 Switch `agents@vds.intdata.pro` systemd health unit to the repo-owned health script.

## 3. Verification

- [x] 3.1 Run shell syntax checks for the new scripts.
- [x] 3.2 Validate the OpenSpec change.
- [x] 3.3 Run the health service once on `agents@vds.intdata.pro`.
- [x] 3.4 Verify v2ray local proxy listeners, proxied ChatGPT endpoint behavior, and Codex app-server proxy environment.
