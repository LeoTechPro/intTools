from __future__ import annotations

from uuid import uuid4

from .models import PolicyDecision, ToolCallRequest


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
    "openspec_exec_mutate",
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
        return False

    def _reject(self, reason: str) -> PolicyDecision:
        return PolicyDecision(str(uuid4()), False, reason, guarded=True)


def _is_cabinet_tool(tool: str) -> bool:
    return tool.startswith("cabinet_") or tool.startswith("cabinet.") or "_cabinet_" in tool or tool.endswith("_cabinet")
