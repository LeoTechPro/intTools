# Release notes and versioning (general)

## Source of truth
- Release notes are published on a single page: `/docs/release`.
- Keep `docs/content/release.md` as the consumer-facing changelog only.
- Do not maintain a local `changelog.md` unless project rules explicitly allow it.

## Versioning policy
- Follow the project `AGENTS.md` for versioning and milestones.

## Release log entry format
Include (in this order):
1) Date
2) Version
3) Short summary (1-2 sentences)
4) Highlights (bulleted)
5) Fixes (bulleted)
6) Known issues / limitations
7) Migrations or required actions (if any)
8) Related issues (IDs per project rules)

## Release note template (markdown)
```markdown
### X.Y.Z — YYYY-MM-DD
**Summary:** ...

**Highlights**
- ...

**Fixes**
- ...

**Known issues**
- ...

**Migrations / actions**
- ...

**Related**
- `project-...`
```
