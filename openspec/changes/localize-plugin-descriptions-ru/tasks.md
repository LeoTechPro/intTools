## 1. Spec

- [x] 1.1 Create OpenSpec change for RU-localization of plugin descriptions.
- [x] 1.2 Fix scope to user-facing plugin text only, without contract/runtime mutations.

## 2. Implementation

- [x] 2.1 Update `description`, `shortDescription`, `longDescription` in 8 active plugin manifests.
- [x] 2.2 Keep plugin IDs, display names, tool names and launcher/runtime wiring unchanged.
- [x] 2.3 Replace pointer-only plugin `SKILL.md` bodies with direct self-contained tool instructions.

## 3. Validation

- [x] 3.1 Validate JSON syntax for modified plugin manifests.
- [x] 3.2 Validate OpenSpec change (`openspec validate <change> --strict`).
- [x] 3.3 Verify git diff contains only expected text-localization and plugin skill body changes.
