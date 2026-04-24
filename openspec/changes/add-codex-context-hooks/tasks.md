## 1. Spec

- [x] 1.1 Define global Codex context hook dispatcher behavior.
- [x] 1.2 Define managed contour policy for `/int/data` and `/int/punkt-b`.

## 2. Implementation

- [x] 2.1 Add tracked dispatcher source under `/int/tools/codex/hooks`.
- [x] 2.2 Add tracked canonical `hooks.json` template.
- [x] 2.3 Install minimal `~/.codex/hooks.json` on dev and prod VDS.
- [x] 2.4 Enable `features.codex_hooks` on prod VDS.

## 3. Validation

- [x] 3.1 Validate OpenSpec change.
- [x] 3.2 Run dispatcher unit/simulated payload checks.
- [x] 3.3 Smoke `codex exec` from `/int/data`.
- [x] 3.4 Smoke `codex exec` from `/int/punkt-b`.
- [x] 3.5 Verify prod mutating git command is blocked.
