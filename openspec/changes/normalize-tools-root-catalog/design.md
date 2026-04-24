# Design: Normalize Tools Root Catalog

## Directory Model

Each non-hidden root directory is a visible catalog unit. A unit may be:

- an owned tool, such as `lockctl`, `gatesctl`, `dba`, or `agent_plane`;
- a runtime/tooling layer, such as `codex` or `openclaw`;
- a delivery/configuration layer, such as `delivery`;
- a product adapter, such as `punkt-b`;
- a public interface, such as `web`;
- an external reference, such as `ngt-memory`.

Generic catch-all roots are avoided. When content is cross-cutting but operational, it should be placed under the most specific owned layer, for example `delivery/` for host/config/deploy assets and `codex/` for Codex-facing scripts/config.

## Public Catalog

The website uses `web/tools.catalog.json` as the public-safe catalog source. Catalog entries are intentionally high-level:

- no secrets;
- no credentials;
- no private local filesystem paths;
- no private VDS hostnames;
- no personal data;
- no internal DB connection details.

The catalog may include non-owned references when they are explicitly marked as references.

## Compatibility

Path references in README and runbooks are updated for moved files. Historical snapshots may keep historical paths only when they clearly state that the path is historical; active mitigation/current-location fields should use the normalized layout.

No compatibility aliases are added for removed root directories in this change. If a runtime still depends on an old path, that dependency must be fixed to the new canonical path instead of reintroducing a generic root.
