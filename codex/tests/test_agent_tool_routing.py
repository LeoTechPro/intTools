#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTER_ROOT = REPO_ROOT / "codex" / "bin"
if str(ROUTER_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROUTER_ROOT))

import agent_tool_routing as routing  # noqa: E402


EXPECTED_V1_CAPABILITIES = {
    "publish_data",
    "publish_assess",
    "publish_crm",
    "publish_id",
    "publish_nexus",
    "publish_bundle_dint",
    "publish_brain_dev",
    "int_git_sync_gate",
    "lockctl-cli",
    "lockctl-mcp",
    "int_ssh_resolve",
    "int_ssh_host",
    "firefox-default",
    "assess-firefox-client",
    "assess-firefox-specialist-v1",
    "assess-firefox-specialist-v2",
    "assess-firefox-admin",
    "assess-firefox-specialist-restricted",
    "intdb",
    "codex-host-bootstrap",
    "codex-host-verify",
    "codex-recovery-bundle",
}


class AgentToolRoutingTest(unittest.TestCase):
    maxDiff = None

    def _load_registry(self) -> dict:
        return routing.load_registry(str(REPO_ROOT / "codex" / "config" / "agent-tool-routing.v1.json"))

    def _write_temp_registry(self, payload: dict) -> str:
        temp_dir = Path(tempfile.mkdtemp(prefix="agent_tool_routing_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(temp_dir, ignore_errors=True))
        registry_path = temp_dir / "agent-tool-routing.v1.json"
        registry_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(registry_path)

    def test_validate_registry_succeeds(self) -> None:
        result = routing.validate_registry(str(REPO_ROOT / "codex" / "config" / "agent-tool-routing.v1.json"))
        self.assertTrue(result["ok"], result["errors"])

    def test_all_v1_capabilities_are_present(self) -> None:
        payload = self._load_registry()
        declared = {item["capability_id"] for item in payload["capabilities"]}
        self.assertEqual(declared, EXPECTED_V1_CAPABILITIES)

    def test_resolve_publish_data_windows_selects_delivery_adapter(self) -> None:
        payload = routing.resolve_capability("publish_data", platform="windows")
        self.assertEqual(payload["selected_binding"]["binding_origin"], "delivery/bin/publish_data.ps1")

    def test_resolve_sync_gate_uses_python_engine(self) -> None:
        payload = routing.resolve_capability("sync-gate:start", platform="linux")
        self.assertEqual(payload["selected_binding"]["binding_origin"], "scripts/codex/int_git_sync_gate.py")

    def test_unknown_intent_blocks(self) -> None:
        with self.assertRaises(routing.RoutingError) as ctx:
            routing.resolve_capability("does-not-exist", platform="windows")
        self.assertEqual(ctx.exception.code, "UNKNOWN_INTENT")

    def test_unsupported_platform_blocks(self) -> None:
        with self.assertRaises(routing.RoutingError) as ctx:
            routing.resolve_capability("codex-host-bootstrap", platform="windows")
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_PLATFORM")

    def test_missing_engine_blocks(self) -> None:
        payload = self._load_registry()
        for capability in payload["capabilities"]:
            if capability["capability_id"] == "publish_data":
                capability["canonical_engine"] = "delivery/bin/missing_publish_data.py"
                for binding in capability["runtime_bindings"]:
                    if binding["binding_kind"] == "engine":
                        binding["binding_origin"] = "delivery/bin/missing_publish_data.py"
                    elif binding["adapter_targets_engine"] == "delivery/bin/publish_data.py":
                        binding["adapter_targets_engine"] = "delivery/bin/missing_publish_data.py"
        registry_path = self._write_temp_registry(payload)
        with self.assertRaises(routing.RoutingError) as ctx:
            routing.resolve_capability("publish_data", platform="windows", registry_path=registry_path)
        self.assertEqual(ctx.exception.code, "MISSING_ENGINE")

    def test_missing_adapter_blocks(self) -> None:
        payload = self._load_registry()
        for capability in payload["capabilities"]:
            if capability["capability_id"] == "publish_assess":
                for binding in capability["runtime_bindings"]:
                    if binding["binding_origin"] == "delivery/bin/publish_assess.ps1":
                        binding["binding_origin"] = "delivery/bin/publish_assess_missing.ps1"
        registry_path = self._write_temp_registry(payload)
        with self.assertRaises(routing.RoutingError) as ctx:
            routing.resolve_capability("publish_assess", platform="windows", registry_path=registry_path)
        self.assertEqual(ctx.exception.code, "MISSING_ADAPTER")

    def test_adapter_drift_blocks(self) -> None:
        payload = self._load_registry()
        for capability in payload["capabilities"]:
            if capability["capability_id"] == "publish_nexus":
                for binding in capability["runtime_bindings"]:
                    if binding["binding_origin"] == "delivery/bin/publish_nexus.ps1":
                        binding["adapter_targets_engine"] = "delivery/bin/publish_data.py"
        registry_path = self._write_temp_registry(payload)
        with self.assertRaises(routing.RoutingError) as ctx:
            routing.resolve_capability("publish_nexus", platform="windows", registry_path=registry_path)
        self.assertEqual(ctx.exception.code, "ADAPTER_DRIFT")

    def test_ambiguous_intent_blocks(self) -> None:
        payload = self._load_registry()
        for capability in payload["capabilities"]:
            if capability["capability_id"] == "publish_id":
                capability["logical_intents"].append("publish:data")
        registry_path = self._write_temp_registry(payload)
        with self.assertRaises(routing.RoutingError) as ctx:
            routing.resolve_capability("publish:data", platform="windows", registry_path=registry_path)
        self.assertEqual(ctx.exception.code, "AMBIGUOUS_INTENT")

    def test_fallbacks_are_reported_but_not_executed(self) -> None:
        payload = self._load_registry()
        for capability in payload["capabilities"]:
            if capability["capability_id"] == "codex-host-bootstrap":
                capability["approved_fallback_skills"] = ["playwright"]
        registry_path = self._write_temp_registry(payload)
        with self.assertRaises(routing.RoutingError) as ctx:
            routing.resolve_capability("codex-host-bootstrap", platform="windows", registry_path=registry_path)
        self.assertEqual(ctx.exception.payload["approved_fallback_skills"], ["playwright"])
        self.assertNotIn("executed_fallback_skill", ctx.exception.payload)

    def test_firefox_overlays_use_python_engine_directly(self) -> None:
        int_overlay = json.loads((REPO_ROOT / "codex" / "projects" / "int" / ".mcp.json").read_text(encoding="utf-8"))
        assess_overlay = json.loads((REPO_ROOT / "codex" / "projects" / "assess" / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(int_overlay["mcpServers"]["firefox-default"]["command"], "python")
        self.assertEqual(assess_overlay["mcpServers"]["assess-firefox-client"]["command"], "python")
        firefox_servers = [
            int_overlay["mcpServers"]["firefox-default"],
            *assess_overlay["mcpServers"].values(),
        ]
        for server in firefox_servers:
            self.assertIn("firefox_mcp_launcher.py", " ".join(server["args"]))
            self.assertNotIn("cmd.exe", server["command"])


if __name__ == "__main__":
    unittest.main()
