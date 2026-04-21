## 1. ROUTING
- [x] 1.1 Remove hardcoded `D:\int\data` default from guarded intdb migration entrypoints.
- [x] 1.2 Make Windows intdb repo auto-discovery fail with an `agents@vds.intdata.pro:/int/data` hint instead of using sibling `D:\int\data`.
- [x] 1.3 Preserve explicit `--repo`/`INTDB_DATA_REPO` for intentional local disposable flows.

## 2. DOCS
- [x] 2.1 Update active `intdb` AGENTS/README references.
- [x] 2.2 Update intTools README command/help text.
- [x] 2.3 Update intdb migration skill routing note.

## 3. VALIDATION
- [x] 3.1 Delete local `D:\int\data`.
- [x] 3.2 Verify remote `agents@vds.intdata.pro:/int/data` exists.
- [x] 3.3 Run focused intdb unit tests.
- [x] 3.4 Re-scan active files for `D:\int\data` operational references.
