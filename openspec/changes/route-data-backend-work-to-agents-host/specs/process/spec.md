## ADDED Requirements

### Requirement: Windows dev backend work MUST NOT default to local `/int/data`
The system MUST NOT route intdata dev backend work from the local Windows machine through `D:\int\data` as an implicit default.

#### Scenario: Windows intdb migration flow has no explicit repo
- **WHEN** a local Windows `intdb` migration/status flow needs `/int/data` owner scripts
- **AND** no explicit `--repo` or `INTDB_DATA_REPO` is provided
- **THEN** the tool refuses to use sibling `D:\int\data`
- **AND** the operator is directed to `agents@vds.intdata.pro:/int/data` for dev backend work

#### Scenario: Remote agents host runs intdb
- **WHEN** the flow runs on the remote agents host with `/int/tools` and `/int/data` as siblings
- **THEN** sibling `/int/data` discovery remains valid

#### Scenario: Disposable local flow is explicitly requested
- **WHEN** an operator intentionally passes `--repo` or `INTDB_DATA_REPO`
- **THEN** the explicit local repo path may be used for disposable/local testing
