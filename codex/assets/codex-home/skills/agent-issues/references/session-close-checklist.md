# Session close checklist (universal)

1. Create or update Multica issues for remaining work (if any) through the Multica MCP plugin or approved project path.
2. Run required quality gates (per project AGENTS).
3. Update Multica issue statuses (close completed, keep in_progress/blocked as appropriate).
4. Ensure changes are packaged (commit/patch): commit the agreed scope. If the owner explicitly ordered `push/publish/deploy`, either publish the already prepared publication-state as-is or stop and ask, but do not hide/revert/defer "foreign" changes from that publication-state on your own. Use a meaningful commit message (project language rules apply).
5. Provide handoff details (artifact + next steps + risks).
6. Clean temporary local artifacts (no branches, no remote ops).
