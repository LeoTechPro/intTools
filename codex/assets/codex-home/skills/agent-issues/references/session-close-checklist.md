# Session close checklist (universal)

1. Create GitHub Issues issues for remaining work (if any).
2. Run required quality gates (per project AGENTS).
3. Update GitHub Issues issue statuses (close completed, keep in_progress).
4. Ensure changes are packaged (commit/patch): commit the agreed scope. If the owner explicitly ordered `push/publish/deploy`, either publish the already prepared publication-state as-is or stop and ask, but do not hide/revert/defer "foreign" changes from that publication-state on your own. Use a meaningful commit message (project language rules apply).
5. Provide handoff details (artifact + next steps + risks).
6. Clean temporary local artifacts (no branches, no remote ops).
