- [ ] 1. Define rename contract in OpenSpec
- [ ] 1.1 Add canonical `dba` capability spec delta.
- [ ] 1.2 Add process/routing delta for `dba` contour/profile naming and branding.
- [ ] 1.3 Link `INT-344` to this OpenSpec package in Multica worklog/comment.

- [ ] 2. Rename tracked DBA contour
- [ ] 2.1 Rename `/int/tools/intdb` to `/int/tools/dba`.
- [ ] 2.2 Rename canonical engine, wrappers, tests and local docs from `intdb` to `dba`.
- [ ] 2.3 Update repo-owned references in routing config, templates, verification scripts and plugin metadata.

- [ ] 3. Normalize branding
- [ ] 3.1 Replace short human-facing `intdb` naming with `intDBA`.
- [ ] 3.2 Replace full display naming with `intData Tools DBA`.
- [ ] 3.3 Update active runbooks and README references to the renamed contour.

- [ ] 4. Verify
- [ ] 4.1 Run focused DBA tests from the renamed contour.
- [ ] 4.2 Verify CLI help/entrypoint works through renamed wrapper.
- [ ] 4.3 Search the tracked tree for stale `intdb` references and classify any intentional leftovers.
