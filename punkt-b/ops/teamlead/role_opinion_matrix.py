#!/usr/bin/env python3
"""Classify issue scope into checks/opinions/major-change policy."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


RISK_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
PRIMARY_DOMAINS = {"frontend", "backend", "db", "process", "docs-user"}
SUPPORTED_FIELDS = {
    "required_checks",
    "required_opinions",
    "touched_domains",
    "touched_primary_domains",
    "highest_risk",
    "major_change",
    "auto_commit_eligible",
}


def _csv_to_list(raw: str | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if not isinstance(raw, str):
        raw = str(raw)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _to_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_matrix(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = payload.get("defaults") or {}
    rules = payload.get("rules") or []

    if not isinstance(defaults, dict):
        raise SystemExit("matrix defaults must be a mapping")
    if not isinstance(rules, list):
        raise SystemExit("matrix rules must be a list")
    if "risk" not in defaults or "checks" not in defaults:
        raise SystemExit("matrix defaults must contain risk and checks")

    normalized_rules: list[dict[str, object]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise SystemExit("matrix rules must contain mappings")
        if "pattern" not in rule:
            raise SystemExit("each matrix rule must contain pattern")
        normalized_rules.append(rule)

    return defaults, normalized_rules


def classify(files: list[str], defaults: dict[str, object], rules: list[dict[str, object]]) -> dict[str, object]:
    highest_risk = str(defaults["risk"])
    checks: set[str] = set(_csv_to_list(defaults.get("checks", "")))
    opinions: set[str] = set(_csv_to_list(defaults.get("opinions", "")))
    domains: set[str] = set(_csv_to_list(defaults.get("domains", "")))
    major_change = _to_bool(str(defaults.get("major_change", "false")))
    auto_commit = _to_bool(str(defaults.get("auto_commit", "false")))
    matched_rules: list[dict[str, object]] = []

    for rel_path in files:
      rel_path = rel_path.strip()
      if not rel_path:
          continue

      selected = defaults
      selected_rule: dict[str, object] | None = None
      for rule in rules:
          if re.search(str(rule["pattern"]), rel_path):
              selected = rule
              selected_rule = rule
              break

      if selected_rule is not None:
          matched_rules.append({"file": rel_path, "pattern": selected_rule["pattern"]})

      file_risk = str(selected.get("risk", defaults["risk"]))
      if RISK_RANK.get(file_risk, 0) > RISK_RANK.get(highest_risk, 0):
          highest_risk = file_risk

      checks.update(_csv_to_list(selected.get("checks", defaults.get("checks", ""))))
      opinions.update(_csv_to_list(selected.get("opinions", defaults.get("opinions", ""))))
      domains.update(_csv_to_list(selected.get("domains", defaults.get("domains", ""))))
      major_change = major_change or _to_bool(str(selected.get("major_change", "false")))
      auto_commit = auto_commit or _to_bool(str(selected.get("auto_commit", "false")))

    touched_primary = sorted(domain for domain in domains if domain in PRIMARY_DOMAINS)
    if len(touched_primary) > 1 or "architecture" in domains or "routing" in domains or highest_risk == "critical":
        opinions.add("architect-role")

    if major_change and opinions:
        auto_commit = True

    return {
        "files": files,
        "highest_risk": highest_risk,
        "required_checks": sorted(checks),
        "required_opinions": sorted(item for item in opinions if item),
        "touched_domains": sorted(item for item in domains if item),
        "touched_primary_domains": touched_primary,
        "major_change": major_change,
        "auto_commit_eligible": auto_commit,
        "matched_rules": matched_rules,
    }


def render_field(payload: dict[str, object], field: str) -> str:
    if field not in SUPPORTED_FIELDS:
        raise SystemExit(2)

    value = payload.get(field)
    if isinstance(value, list):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify files via swarm risk/opinion matrix")
    parser.add_argument("--matrix", required=True, help="Path to matrix yaml")
    parser.add_argument("--files", required=True, help="Comma-separated files")
    parser.add_argument("--field", choices=sorted(SUPPORTED_FIELDS), help="Print a single computed field")
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    files = [item.strip() for item in args.files.split(",") if item.strip()]
    defaults, rules = load_matrix(matrix_path)
    payload = classify(files, defaults, rules)
    if args.field:
        print(render_field(payload, args.field))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
