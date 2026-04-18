## 1. Spec

- [x] 1.1 Create OpenSpec change package for repo-local ignored runtime root.
- [x] 1.2 Define transition compatibility expectations.

## 2. Implementation

- [x] 2.1 Add `.runtime/` gitignore coverage.
- [x] 2.2 Update docs and process policy references.
- [x] 2.3 Update wrapper defaults and hardcoded runtime paths.
- [x] 2.4 Update tests for the new default runtime root.
- [x] 2.5 Move local runtime data under `/int/tools/.runtime` with compatibility path.

## 3. Validation

- [x] 3.1 Verify no non-OpenSpec tracked dependency still defaults to `/int/.runtime`.
- [x] 3.2 Run targeted Python tests/compilation for changed runtime entrypoints.
- [x] 3.3 Verify git status and local runtime placement.
