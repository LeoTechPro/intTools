from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "bin" / "mcp-intdata-cli.py"
SPEC = importlib.util.spec_from_file_location("mcp_intdata_cli", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("issue_context", ["#1", "#800", "#123456"])
def test_mutation_guard_accepts_real_github_issue(issue_context: str) -> None:
    MODULE._require_mutation(
        {"confirm_mutation": True, "issue_context": issue_context}
    )


@pytest.mark.parametrize(
    "issue_context",
    ["", "800", "#0", "#01", "INT-800", "LeoTechPro/int#800"],
)
def test_mutation_guard_rejects_noncanonical_issue_context(
    issue_context: str,
) -> None:
    with pytest.raises(PermissionError):
        MODULE._require_mutation(
            {"confirm_mutation": True, "issue_context": issue_context}
        )


def test_mutation_guard_still_requires_confirmation() -> None:
    with pytest.raises(PermissionError):
        MODULE._require_mutation(
            {"confirm_mutation": False, "issue_context": "#800"}
        )


def test_mutation_schema_advertises_only_github_issue_numbers() -> None:
    props = MODULE._mutation_props()
    assert props["issue_context"]["pattern"] == r"^#[1-9][0-9]*$"
    assert "#800" in props["issue_context"]["description"]
    assert "INT-" not in props["issue_context"]["description"]
