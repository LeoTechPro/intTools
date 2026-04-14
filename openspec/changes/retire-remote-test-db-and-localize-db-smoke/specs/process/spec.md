## ADDED Requirements

### Requirement: Retired remote disposable DB entrypoints MUST stay disabled
Система MUST NOT сохранять active tooling path из `/int/tools` в retired remote disposable DB contour для `/int/data`.

#### Scenario: Wrapper targets retired remote test contour
- **WHEN** a wrapper or profile example points to `punkt_b_test` or `intdata_test` on `vds.intdata.pro`
- **THEN** that path is removed or replaced with an explicit retirement error
- **AND** active docs point to the owner-gated local disposable runner instead
