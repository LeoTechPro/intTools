# Change: Normalize Tools Root Catalog

## Why

The `/int/tools` repository has grown into a visible operator surface. Its non-hidden root directories should be understandable as standalone tools, product adapters, runtime layers, or explicit references. Generic roots such as `data/` and `scripts/` make ownership unclear, and stale one-off artifacts such as `gate-brief-int-2/` should not remain visible as tools.

The public Tools website also needs to reflect the actual root inventory without exposing private paths, secrets, hostnames, or personal data.

## What Changes

- Treat every non-hidden root directory as a catalog item: tool, adapter, runtime layer, governance layer, delivery layer, website, or external reference.
- Move `data/*` host/config/process assets into `delivery/*`.
- Move reusable Codex scripts from `scripts/codex/*` into `codex/scripts/*`.
- Remove stale `gate-brief-int-2/` tracked artifacts.
- Keep `ngt-memory` allowed as an external reference, not as an owned intData tool.
- Add a public-safe `web/tools.catalog.json` and render the catalog on the static website.
- Update README/runbook references to the normalized layout.

## Scope Boundaries

- No runtime secrets, private hostnames, private local machine paths, or personal data are added to tracked docs or the public website.
- No product-core ownership is moved into `/int/tools`.
- `ngt-memory` may remain as a visible reference, but its upstream contents are not imported into tracked intTools source.
- This change does not refactor code/package namespaces unless required by moved file paths.

## Issue

Owning Multica issue: `INT-347`.

## Acceptance

- `data/`, `scripts/`, and `gate-brief-int-2/` are absent as non-hidden root directories.
- Host/config/process assets previously under `data/` live under `delivery/`.
- Reusable Codex scripts previously under `scripts/codex/` live under `codex/scripts/`.
- README and relevant runbooks reference the new layout.
- The website displays a root tool/reference catalog from public-safe data.
- OpenSpec validation passes for this change.
