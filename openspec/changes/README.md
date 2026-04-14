# OpenSpec Changes

`openspec/changes/*` хранит owner-approved change packages для tracked tooling/process mutations в `/int/tools`.

Минимальный пакет change:

- `proposal.md`
- `tasks.md`
- релевантный `spec.md` delta в `specs/**`
- `design.md`, если change меняет architecture/enforcement/runtime model

Execution без active change package запрещён для repo-owned tooling mutations.
