## ADDED Requirements

### Requirement: Roistat helper contour keeps secrets and runtime out of git

The intTools Roistat helper MUST keep reusable Roistat integration code under
`/int/tools/roistat` while storing real config and mutable runtime state outside
tracked git.

#### Scenario: Roistat core is migrated
- **WHEN** useful Roistat integration files are preserved from the old checkout
- **THEN** only the core CRM/webhook PHP files are tracked under
  `/int/tools/roistat`
- **AND** dashboard, Bitrix monitoring, and old deploy/nginx experiments are not
  tracked as part of the helper contour
- **AND** real config, SQLite/cursor state, and logs remain under ignored
  `/int/tools/.runtime/roistat/**`.
