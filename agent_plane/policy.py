from __future__ import annotations

from uuid import uuid4

from .models import PolicyDecision, ToolCallRequest


READ_ONLY_MULTICA_COMMANDS = {"get", "list", "search", "runs", "run-messages"}
READ_ONLY_MULTICA_COMMENT_COMMANDS = {"list"}

MUTATING_TOOLS = {
    "intbrain_context_store",
    "intbrain_graph_link",
    "intbrain_group_policy_upsert",
    "intbrain_job_policy_upsert",
    "intbrain_jobs_sync_runtime",
    "intbrain_import_vault_pm",
    "intbrain_memory_sync_sessions",
    "intbrain_memory_import_mempalace",
    "lockctl_acquire",
    "lockctl_release_path",
    "lockctl_release_issue",
    "lockctl_renew",
    "lockctl_gc",
    "openspec_new",
    "openspec_exec",
    "publish",
    "sync_gate",
    "host_bootstrap",
    "recovery_bundle",
    "browser_profile_launch",
}


class PolicyEngine:
    def decide(self, request: ToolCallRequest) -> PolicyDecision:
        if _is_cabinet_tool(request.tool):
            return self._reject("cabinet_out_of_scope")

        guarded = self.is_guarded(request)
        if guarded and not request.approval_ref:
            return PolicyDecision(str(uuid4()), False, "approval_required", guarded=True)

        return PolicyDecision(str(uuid4()), True, "allowed", guarded=guarded)

    def is_guarded(self, request: ToolCallRequest) -> bool:
        if request.tool in MUTATING_TOOLS:
            return True
        if request.tool.startswith("multica_"):
            return not self._is_read_only_multica(request)
        return False

    def _is_read_only_multica(self, request: ToolCallRequest) -> bool:
        command = str(request.args.get("command") or "").strip()
        if request.tool == "multica_issue":
            return command in READ_ONLY_MULTICA_COMMANDS
        if request.tool == "multica_attachment":
            return command in {"list"}
        if request.tool == "multica_issue_comment":
            return command in READ_ONLY_MULTICA_COMMENT_COMMANDS
        return False

    def _reject(self, reason: str) -> PolicyDecision:
        return PolicyDecision(str(uuid4()), False, reason, guarded=True)


def _is_cabinet_tool(tool: str) -> bool:
    return tool.startswith("cabinet_") or tool.startswith("cabinet.") or "_cabinet_" in tool or tool.endswith("_cabinet")
