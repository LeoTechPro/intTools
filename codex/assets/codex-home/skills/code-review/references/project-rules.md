# Review Rules (summary)

- Follow project process rules in AGENTS.md (or GEMINI.md) from repo root.
- Do not run git push/pull/fetch or touch remote branches.
- Do not create new branches, cherry-pick, rebase, or amend commits.
- Do not delete or revert other people's changes without explicit user approval.
- Avoid destructive commands (git reset --hard, git checkout --) unless user explicitly requests.
- Prefer existing libraries and patterns; avoid custom code unless necessary.
- Frontend reviews: preserve existing UI patterns and brandbook constraints; avoid new global CSS unless required.
- Backend/DB reviews: do not apply migrations unless user explicitly requests it.
- If review requires running tests/builds but you cannot, record the gap in the report.
- For consult reviews, add a worklog comment to the consult issue defined in AGENTS.md after substantive work.
