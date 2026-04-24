## 1. Spec and Inventory

- [x] Link the change to Multica issue `INT-347`.
- [x] Define the normalized root-directory contract.
- [x] Inventory visible root directories and classify them as tools, runtime layers, adapters, delivery layers, website, or references.

## 2. Layout Normalization

- [x] Move `data/configs`, `data/devops`, `data/devs`, `data/docops`, `data/monitoring`, and `data/docker-compose.yaml` under `delivery/`.
- [x] Move `data/markdown-context-policy.json` under `codex/config/`.
- [x] Move reusable `scripts/codex/*` under `codex/scripts/`.
- [x] Remove tracked `gate-brief-int-2/` artifacts.
- [x] Remove obsolete empty `data/` and `scripts/` roots.

## 3. Documentation and Web

- [x] Update README and runbook references to the normalized paths.
- [x] Add public-safe `web/tools.catalog.json`.
- [x] Render the catalog on the public static website.
- [x] Keep website copy Russian and avoid secrets/private paths/private hostnames.

## 4. Verification

- [x] Validate OpenSpec change strictly.
- [x] Run relevant unit/smoke checks.
- [x] Serve `web/` locally and verify HTML/CSS/JS/catalog load.
- [x] Verify root inventory has no visible `data/`, `scripts/`, or `gate-brief-int-2/`.
- [x] Commit and publish to `origin/main`.
