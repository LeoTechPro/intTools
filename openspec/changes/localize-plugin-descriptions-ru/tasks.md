## 1. Spec

- [x] 1.1 Create OpenSpec change for RU-localization of plugin descriptions.
- [x] 1.2 Fix scope to description fields only, without contract/runtime mutations.

## 2. Implementation

- [x] 2.1 Update `description`, `shortDescription`, `longDescription` in 8 active plugin manifests.
- [x] 2.2 Keep plugin IDs, display names, tool names and launcher/runtime wiring unchanged.

## 3. Validation

- [ ] 3.1 Validate JSON syntax for modified plugin manifests.
- [ ] 3.2 Validate OpenSpec change (`openspec validate <change> --strict`).
- [ ] 3.3 Verify git diff contains only expected text-localization changes.
