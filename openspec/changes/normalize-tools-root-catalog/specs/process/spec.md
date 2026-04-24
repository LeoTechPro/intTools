## ADDED Requirements

### Requirement: Visible root directories MUST represent catalog units
The system MUST keep every non-hidden top-level directory in `/int/tools` as a distinct catalog unit: owned tool, runtime layer, product adapter, delivery layer, public interface, governance layer, or explicit external reference.

#### Scenario: Root inventory is reviewed
- **WHEN** a non-hidden top-level directory exists in `/int/tools`
- **THEN** README and the public Tools catalog describe its purpose
- **AND** the directory is not a generic dumping ground such as `data/` or `scripts/`
- **AND** external references are marked as references rather than owned intData tools

### Requirement: Public catalog MUST stay safe for publication
The system MUST keep website catalog content public-safe.

#### Scenario: Website catalog is updated
- **WHEN** `web/tools.catalog.json`, `web/index.html`, `web/app.js`, or `web/styles.css` is changed
- **THEN** the published content does not include secrets, credentials, private local machine paths, private VDS hostnames, or personal data
- **AND** catalog descriptions stay high-level enough for public documentation

### Requirement: Generic root directories MUST be split into owned layers
The system MUST split generic root directories into the most specific owned catalog layer.

#### Scenario: Generic operational files are found
- **WHEN** host configs, deploy helpers, docs helpers, or monitoring templates are tracked in a generic root
- **THEN** they move under `delivery/` unless a more specific owned tool layer applies
- **AND** Codex-facing reusable scripts move under `codex/`
- **AND** stale one-off artifacts are removed instead of being preserved as root tools
