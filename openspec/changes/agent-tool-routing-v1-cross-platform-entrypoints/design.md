# Design: Agent Tool Routing V1 and cross-platform entrypoints

## Context

Для `/int/*` уже существует набор repo-owned agent-facing инструментов, но они описаны не как capability graph, а как разрозненные wrappers, overlays и env actions. Это особенно рискованно для high-risk paths, где ad-hoc запуск shell-specific wrapper может привести к разным transport semantics, разному fallback behavior и разным blocker conditions на Windows и Linux.

## Decision

Вводится двухслойная модель:

1. `logical intent -> logical capability` через routing registry;
2. `logical capability -> runtime binding` через canonical engine и thin adapters.

Для high-risk intent-ов V1 агент обязан сначала пройти registry resolution. Если capability не поддерживается на текущей платформе, если отсутствует canonical engine, если adapter drift'ит от engine contract или если intent ambiguous, результат должен быть `blocked`.

## Canonical engine policy

- У каждой runtime-critical capability ровно один canonical engine на platform-neutral runtime (`python`, `node`, `.mjs` или иной neutral runtime).
- Shell-specific `.ps1`, `.sh`, `.cmd` допустимы только как thin adapters.
- Registry хранит logical capability и runtime bindings, а не hardcoded wrapper как единственный primary source-of-truth.
- Для delivery/publish capabilities canonical engine root закрепляется в `D:/int/tools/delivery/bin`.
- Для SSH/browser/host-runtime canonical engine root закрепляется в `D:/int/tools/codex`.
- Для self-contained tools допустим repo-owned engine outside `tools/codex`, если capability уже изолирована и кроссплатформенна, как `D:/int/tools/intdb/lib/intdb.py` или `D:/int/tools/lockctl/lockctl_core.py`.

## V1 capability inventory and canonicalization target

### Publish / deploy

Current repo-owned tools:

- `D:/int/tools/delivery/bin/publish_repo.py`
- `D:/int/tools/delivery/bin/publish_data.py`
- `D:/int/tools/codex/bin/publish_repo.ps1`
- `D:/int/tools/codex/bin/publish_data.ps1`
- `D:/int/tools/codex/bin/publish_assess.ps1`
- `D:/int/tools/codex/bin/publish_crm.ps1`
- `D:/int/tools/codex/bin/publish_id.ps1`
- `D:/int/tools/codex/bin/publish_nexus.ps1`
- `D:/int/tools/codex/bin/publish_bundle_dint.ps1`
- `agents@vds.intdata.pro:/int/brain/deploy/scripts/publish_dev_vds_intbrain.sh`

Decision:

- `publish_repo.py` становится canonical shared engine для delivery-style publish capabilities.
- Repo-specific publish capabilities получают thin Windows/Linux adapters рядом с engine, а не новые source-of-truth в `D:/int/tools/codex/bin`.
- Старые `publish_*.ps1` в `D:/int/tools/codex/bin` выводятся из роли canonical binding и должны быть удалены после cutover callers.
- `publish_brain_dev` входит в тот же V1 inventory и обязан использовать общий SSH resolver contract, даже если его engine остаётся repo-local до отдельной унификации.

### Lock / sync gate

Current repo-owned tools:

- `D:/int/tools/scripts/codex/int_git_sync_gate.py`
- `D:/int/tools/codex/bin/int_git_sync_gate.sh`
- `D:/int/tools/codex/bin/int_git_sync_gate.ps1`
- `D:/int/tools/lockctl/lockctl_core.py`
- `D:/int/tools/lockctl/lockctl.py`
- `D:/int/tools/lockctl/lockctl`
- `D:/int/tools/lockctl/lockctl.ps1`
- `D:/int/tools/lockctl/lockctl.cmd`
- `D:/int/tools/codex/bin/mcp-lockctl.py`
- `D:/int/tools/codex/bin/mcp-lockctl.sh`
- `D:/int/tools/codex/bin/mcp-lockctl.cmd`

Decision:

- `int_git_sync_gate.py` и `lockctl_core.py` фиксируются как reference-pattern для engine/adapter split.
- Эти capabilities не требуют архитектурного переписывания, но должны быть внесены в registry V1 как canonical examples.

### Remote access

Current repo-owned tools:

- `D:/int/tools/codex/bin/int_ssh_resolve.ps1`
- `D:/int/tools/codex/bin/int_ssh_host.sh`
- duplicated SSH resolve/probe/fallback logic inside `D:/int/tools/delivery/bin/publish_repo.py`

Decision:

- Вводится единый SSH resolver engine на platform-neutral runtime.
- `int_ssh_resolve.ps1` и `int_ssh_host.sh` остаются только adapters.
- Windows и Linux обязаны возвращать одинаковую metadata shape: `destination`, `transport`, `probe_succeeded`, `fallback_used`, `tailnet_host`, `public_host`.

### Browser verify / fallback attach

Current repo-owned tools:

- `D:/int/tools/codex/bin/mcp-firefox-devtools.ps1`
- `D:/int/tools/codex/bin/mcp-firefox-devtools.cmd`
- `D:/int/tools/codex/bin/mcp-firefox-default.cmd`
- `D:/int/tools/codex/bin/mcp-firefox-assess-client.cmd`
- `D:/int/tools/codex/bin/mcp-firefox-assess-specialist-v1.cmd`
- `D:/int/tools/codex/bin/mcp-firefox-assess-specialist-v2.cmd`
- `D:/int/tools/codex/bin/mcp-firefox-assess-admin.cmd`
- `D:/int/tools/codex/bin/mcp-firefox-assess-specialist-restricted.cmd`
- `D:/int/tools/codex/projects/int/.mcp.json`
- `D:/int/tools/codex/projects/assess/.mcp.json`

Decision:

- Launcher logic переносится из `.ps1` в neutral engine.
- `.ps1`, `.sh`, `.cmd` допускаются только как transport adapters.
- Project overlays должны ссылаться на generic capability + adapter для текущей платформы, а не на `cmd.exe` плюс Windows-only absolute path.

### DB apply / smoke / migration diagnostics

Current repo-owned tools:

- `D:/int/tools/intdb/lib/intdb.py`
- `D:/int/tools/intdb/bin/*.py`
- `D:/int/tools/intdb/intdb.ps1`
- `D:/int/tools/intdb/intdb.cmd`
- `D:/int/tools/codex/bin/intdb.ps1`
- `D:/int/tools/codex/bin/intdb.cmd`

Decision:

- `intdb.py` фиксируется как canonical engine.
- Agent-facing Windows/Linux adapters обязаны давать одинаковый CLI surface и exit semantics.

### Host bootstrap / runtime launchers

Current repo-owned tools:

- `D:/int/tools/codex/bin/codex-host-bootstrap`
- `D:/int/tools/codex/bin/codex-host-verify`
- `D:/int/tools/codex/bin/codex-recovery-bundle`
- their references in `D:/int/tools/codex/layout-policy.json`, templates, env actions and runbooks

Decision:

- Эти launchers входят в V1 inventory как runtime-critical.
- Для них вводится тот же engine/adapter contract и Windows/Linux parity requirement.

## Verified skills policy

- Verified skill tools остаются допустимыми для read/search/docs и других non-V1 workflows.
- Для high-risk intents skill-provided tool может использоваться только как explicit approved fallback, заранее зафиксированный в registry.
- Если repo-owned primary blocked и approved fallback отсутствует, результат остаётся `blocked`.

## Consequences

- V1 запрещает agent self-routing на основании случайного wrapper path.
- Переход к cross-platform adapters становится обязательным не только для publish, но и для SSH, Firefox, `intdb` и host runtime launchers.
- Existing `int_git_sync_gate` и `lockctl` становятся reference implementations, а не просто частными скриптами.
