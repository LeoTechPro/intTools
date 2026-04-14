# Change: Agent Tool Routing V1 + Cross-Platform Entrypoints for `/int/*`

## Why

Сейчас agent-facing tooling для `/int/*` частично маршрутизируется через случайные shell-specific entrypoints и project-local hardcodes вместо одного capability contract:

- high-risk intents (`publish/deploy`, `remote access`, `DB diagnostics`, `browser verify/attach`, `lock/sync gate`) не имеют общего routing source-of-truth;
- часть publish/deploy path всё ещё завязана на PowerShell wrappers в `D:/int/tools/codex/bin/*` как на фактический primary implementation;
- SSH routing split между `int_ssh_resolve.ps1`, `int_ssh_host.sh` и локальной логикой в `publish_repo.py`;
- Firefox MCP overlays в `D:/int/tools/codex/projects/*/.mcp.json` содержат Windows-only launcher assumptions;
- verified skills остаются полезными, но сейчас их легко превратить в неявный ad-hoc workaround для blocked repo-owned high-risk capability.

Нужен единый V1 contract: агент сначала резолвит intent в approved logical capability, затем использует canonical cross-platform engine и только потом platform adapter. Если такой binding не существует, результат должен быть `blocked`, а не самодельный workaround.

## What Changes

- Добавляется новый capability-spec `agent-tool-routing`.
- В change явно фиксируется cross-platform entrypoint policy для repo-owned runtime-critical capabilities.
- В registry V1 source-of-truth становится logical capability binding, а не конкретный `.ps1`/`.sh` файл.
- Для delivery-capabilities canonical engine root закрепляется в `D:/int/tools/delivery/bin`.
- Для non-delivery high-risk capabilities canonical engine root остаётся в `D:/int/tools/codex` или в repo-owned tool directory, если capability уже self-contained.
- Verified skill tools остаются разрешёнными, но только как explicit approved fallback там, где это заранее описано в registry.

## V1 Inventory To Canonize

### Publish / deploy
- `publish_data`
- `publish_assess`
- `publish_crm`
- `publish_id`
- `publish_nexus`
- `publish_bundle_dint`
- `publish_brain_dev`

### Lock / sync gate
- `int_git_sync_gate`
- `lockctl` CLI
- `lockctl` MCP

### Remote access
- `int_ssh_resolve`
- `int_ssh_host`

### Browser verify / fallback attach
- `mcp-firefox-devtools`
- profile launch adapters such as `mcp-firefox-default.cmd` and `mcp-firefox-assess-*.cmd`
- project overlays in `D:/int/tools/codex/projects/*/.mcp.json`

### DB apply / smoke / migration diagnostics
- `intdb`

### Host bootstrap / runtime launchers
- `codex-host-bootstrap`
- `codex-host-verify`
- `codex-recovery-bundle`

## Scope Boundaries

- Scope этого change — spec/governance + routing contract + inventory + executor-facing implementation plan.
- Change не выполняет сам runtime refactor; он задаёт source-of-truth для следующей исполнительской волны.
- Verified skills и их tooling не запрещаются этим change, если они не подменяют repo-owned high-risk capability вне approved fallback path.

## Acceptance (high-level)

- В `openspec/changes/<change-id>/` есть owner-facing пакет, который фиксирует весь V1 inventory и blocker/fallback contract.
- В `specs/process/spec.md` delta добавлены process-gates для high-risk agent routing.
- В `specs/agent-tool-routing/spec.md` delta описывает logical registry contract, engine/adapter contract и blocker semantics.
- В change package есть отдельный `executor-prompt.md` с конкретным списком repo-owned инструментов, путей, ожидаемых правок и acceptance criteria для исполнителя.
