## 1. Spec

- [x] 1.1 Record owner-approved dirty/ahead and `sync_gate start` bypass exceptions for `INT-226`.
- [x] 1.2 Update proposal, design, tasks, and process spec delta for neutral Agent Tool Plane V1.
- [x] 1.3 Explicitly exclude Cabinet absorption, Cabinet aliases, and `/int/brain` changes from this scope.

## 2. Implementation

- [x] 2.1 Add `agent_plane` HTTP service with health, tools, tool-call, and audit endpoints.
- [x] 2.2 Add facade-neutral request validation for `agno`, `openclaw`, and `codex_app`.
- [x] 2.3 Add policy checks for unknown principals, Cabinet tools, and guarded calls without approval.
- [x] 2.4 Add dispatcher to existing `mcp-intdata-cli.py` profiles and filter Cabinet tools.
- [x] 2.5 Add audit stores: memory, JSONL fallback, and optional PostgreSQL writer.
- [x] 2.6 Add PostgreSQL migration for schema `agent_plane`.
- [x] 2.7 Add Codex App MCP plugin/client surface.
- [x] 2.8 Add OpenClaw shell wrapper and Agno/local harness.
- [x] 2.9 Fix `ssh_resolve` canonical capability mismatch to `int_ssh_resolve`.

## 3. Validation

- [x] 3.1 Parse JSON plugin and marketplace manifests.
- [x] 3.2 Compile and run `agent_plane` unit tests.
- [x] 3.3 Run HTTP smoke for health, tools, read-only tool call, policy rejection, and audit.
- [x] 3.4 Run Codex MCP client smoke.
- [x] 3.5 Run Agno/local harness smoke.
- [x] 3.6 Run OpenSpec strict validation and routing validation.
- [x] 3.7 Verify fresh `ssh_resolve` process path.

## 4. Plugin Skill Guidance Hardening

- [x] 4.1 Russian-localize active plugin metadata and default prompts.
- [x] 4.2 Remove Cabinet from active IntBrain metadata, skills, and MCP `tools/list`.
- [x] 4.3 Split overloaded capability skills: Multica, IntBrain jobs/PM, and IntBrain session/import guidance.
- [x] 4.4 Add one tool-card per active MCP tool with trigger, required inputs, mode, approval rules, example, and blocker language.
- [x] 4.5 Extend verifier with `--report-json`, required-arg checks, guard wording checks, read-only markers, matrix output, and Cabinet leak detection.
- [x] 4.6 Verify active counts before control split: `intbrain=27`, `intdata-control=35`, `intdata-runtime=9`, `intdb=1`.
- [x] 4.7 Split `intdata-control` OpenSpec/sync-gate command routers into explicit tools. Superseded for Multica by `remove-intdata-control-multica-surface`; active count is now `24`.

## 5. Codex Home Hardening

- [x] 5.1 Retire `sync_runtime_from_repo.*` mutating mode and keep only non-mutating dry-run diagnostics.
- [x] 5.2 Stop `codex-host-bootstrap` from calling sync or writing `config.toml` under Codex home.
- [x] 5.3 Retire `detach_home_git.sh` mutating mode and keep only non-mutating dry-run diagnostics.
- [x] 5.4 Move orphan-cleaner and debate logs/locks plus Bizon downloads under `/int/tools/.runtime/**`.
- [x] 5.5 Remove automatic Bizon secret fallback from `~/.codex/var`.
- [x] 5.6 Update docs and focused tests for native-only Codex home mutation policy.

## Exceptions

- Owner approved continuing over the existing dirty/ahead checkout without reverting unrelated work.
- Owner approved bypassing `sync_gate start` for `INT-226` because the checkout already had unrelated dirty/ahead work.
- `sync_gate finish` may remain blocked until unrelated dirty work is resolved or explicitly included by the owner.
