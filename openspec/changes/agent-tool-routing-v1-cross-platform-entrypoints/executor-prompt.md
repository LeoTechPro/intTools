# ТЗ-промпт для исполнителя

Нужно реализовать owner-approved change `agent-tool-routing-v1-cross-platform-entrypoints` в `D:/int/tools/openspec` и привести repo-owned high-risk agent tooling для дерева `/int/*` к единому contract `logical intent -> canonical engine -> thin adapter`.

## Что нужно сделать

1. Создай и/или обнови canonical spec artifacts для capability `agent-tool-routing` и для process-gates, как описано в этом change package.
2. Добавь runtime registry V1 и schema рядом с ним так, чтобы registry был machine-readable и валидировал binding resolution, а не оставался prose-only.
3. Для high-risk repo-owned capabilities переведи source-of-truth с shell-specific wrappers на canonical engines.
4. Сохрани verified skills разрешёнными, но не допускай их как implicit substitute для blocked repo-owned high-risk capability.

## Обязательный V1 inventory

Publish/deploy inventory removed by `remove-local-delivery-publish-surface`: do not add local delivery publish wrappers back to this routing inventory.

### Lock / sync gate
- `D:/int/tools/lockctl/lockctl_core.py`
- `D:/int/tools/lockctl/lockctl.py`
- `D:/int/tools/codex/bin/mcp-intdata-cli.py`

Требование:
- используй их как reference-pattern для engine/adapter split;
- не ломай текущий cross-platform contract.

### Remote access
- `D:/int/tools/codex/bin/int_ssh_resolve.ps1`
- `D:/int/tools/codex/bin/int_ssh_host.sh`

Требование:
- выдели один общий SSH resolver engine;
- оставь `.ps1` и `.sh` только adapters;
- Windows и Linux должны одинаково возвращать `destination`, `transport`, `probe_succeeded`, `fallback_used`, `tailnet_host`, `public_host`.

### Browser verify / fallback attach
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

Требование:
- вынеси launcher logic из `.ps1` в neutral engine;
- overlays должны ссылаться на platform-appropriate adapter, а не на Windows-only `cmd.exe + D:\...`.

### DB diagnostics
- `D:/int/tools/intdb/lib/intdb.py`
- `D:/int/tools/intdb/bin/*.py`
- `D:/int/tools/intdb/intdb.ps1`
- `D:/int/tools/intdb/intdb.cmd`
- `D:/int/tools/codex/bin/intdb.ps1`
- `D:/int/tools/codex/bin/intdb.cmd`

Требование:
- canonical engine = `D:/int/tools/intdb/lib/intdb.py`;
- добейся одинакового CLI surface и exit semantics на Windows и Linux.

### Host bootstrap / runtime launchers
- `D:/int/tools/codex/bin/codex-host-bootstrap`
- `D:/int/tools/codex/bin/codex-host-verify`
- `D:/int/tools/codex/bin/codex-recovery-bundle`
- все ссылки на них в `layout-policy.json`, templates, env actions и runbooks

Требование:
- включи их в V1 inventory;
- добавь единый contract по аргументам, stdout/stderr и non-zero behavior.

## Registry contract

Добавь machine-readable registry V1 со следующими обязательными полями:

- `logical_intents[]`
- `runtime_bindings.<runtime>.primary`
- `runtime_bindings.<runtime>.fallbacks[]`
- `resolution_status = primary | fallback | blocked | ambiguous`
- `binding_kind = engine | adapter`
- `binding_origin = repo_owned | verified_skill`
- `platforms_supported`
- `adapter_targets_engine`
- `parity_required`

Для high-risk bindings `parity_required = true`.

## Blocker rules

- unsupported platform => `blocked`
- missing engine => `blocked`
- missing approved adapter => `blocked`
- adapter drift from engine contract => `blocked`
- ambiguous or unknown intent => `blocked`
- repo-owned primary blocked without explicit approved fallback => `blocked`

## Verified skills policy

- Не запрещай verified skills в целом.
- Разреши их для read/search/docs и прочих non-high-risk сценариев.
- Для high-risk intent skill tool допустим только как явно описанный approved fallback в registry.
- Если repo-owned high-risk path blocked и approved fallback не описан, результат обязан остаться `blocked`; автоматический переход на skill path запрещён.

## Non-goals первой волны

- Не стандартизируй всю экосистему skill tools.
- Не вводи ad-hoc fallback paths вне registry.
- Не растягивай V1 на low-risk read/search/docs workflows, если они не блокируют high-risk path.

## Acceptance

1. Все V1 high-risk repo-owned capabilities описаны в registry и capability spec.
2. Ни один primary binding не остаётся shell-specific source-of-truth без canonical engine.
3. Local delivery publish wrapper layer remains removed and is not reintroduced as a routing binding.
4. SSH routing и Firefox launcher имеют cross-platform engine/adapter contract.
5. `lockctl` остаётся рабочим cross-platform reference-pattern без регрессии; `int_git_sync_gate` удалён/запрещён.
6. Verified skills остаются допустимыми, но не могут неявно подменять blocked repo-owned high-risk capability.
