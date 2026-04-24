#!/usr/bin/env python3
"""Выгрузка GitHub Project V2 → AGENTS/issues.json с подробными полями."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

GRAPHQL_URL = "https://api.github.com/graphql"
FEATURE_HEADER = "projects_next_graphql"


class SyncError(RuntimeError):
    pass


def resolve_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SyncError("GITHUB_TOKEN не задан и `gh auth token` недоступен") from exc
    token = result.stdout.strip()
    if not token:
        raise SyncError("`gh auth token` вернул пустой токен")
    return token


def gql(query: str, variables: dict, token: str) -> dict:
    response = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "GraphQL-Features": FEATURE_HEADER,
        },
        timeout=40,
    )
    if response.status_code != 200:
        raise SyncError(f"GraphQL HTTP {response.status_code}: {response.text.strip()}")
    payload = response.json()
    if "errors" in payload:
        raise SyncError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


ITEMS_QUERY = """
query($project:ID!, $cursor:String){
  node(id:$project){
    ... on ProjectV2 {
      items(first:100, after:$cursor){
        nodes{
          id
          content{
            __typename
            ... on Issue{
              number
              title
              url
              state
              body
              createdAt
              updatedAt
              repository{ nameWithOwner }
              labels(first:20){ nodes{ name } }
            }
          }
          fieldValues(first:100){
            nodes{
              __typename
              ... on ProjectV2ItemFieldTextValue{
                text
                field{ ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldNumberValue{
                number
                field{ ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldDateValue{
                date
                field{ ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldSingleSelectValue{
                name
                optionId
                field{ ... on ProjectV2FieldCommon { id name } }
              }
            }
          }
        }
        pageInfo{ hasNextPage endCursor }
      }
    }
  }
}
"""


@dataclass
class Options:
    owner: str
    project_number: int
    output: Path


def fetch_project_id(owner: str, number: int, token: str) -> str:
    # сначала пробуем как пользователь
    user_query = """
    query($login:String!, $number:Int!){
      user(login:$login){ projectV2(number:$number){ id } }
    }
    """
    data = gql(user_query, {"login": owner, "number": number}, token)
    project = data.get("user", {}).get("projectV2")
    if project:
        return project["id"]

    org_query = """
    query($login:String!, $number:Int!){
      organization(login:$login){ projectV2(number:$number){ id } }
    }
    """
    data = gql(org_query, {"login": owner, "number": number}, token)
    project = data.get("organization", {}).get("projectV2")
    if project:
        return project["id"]
    raise SyncError(f"Проект {owner} #{number} не найден")


def collect_items(project_id: str, token: str) -> List[dict]:
    items: List[dict] = []
    cursor: Optional[str] = None
    while True:
        data = gql(ITEMS_QUERY, {"project": project_id, "cursor": cursor}, token)
        node = data["node"]
        if not node:
            break
        block = node["items"]
        items.extend(block["nodes"])
        if not block["pageInfo"]["hasNextPage"]:
            break
        cursor = block["pageInfo"]["endCursor"]
        time.sleep(0.15)
    return items


def map_field_values(field_nodes: List[dict]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for node in field_nodes:
        field = node.get("field") or {}
        name = field.get("name")
        if not name:
            continue
        kind = node["__typename"]
        if kind == "ProjectV2ItemFieldNumberValue":
            values[name] = node.get("number")
        elif kind == "ProjectV2ItemFieldDateValue":
            values[name] = node.get("date")
        elif kind == "ProjectV2ItemFieldSingleSelectValue":
            values[name] = node.get("name")
        elif kind == "ProjectV2ItemFieldTextValue":
            values[name] = node.get("text")
    return values


def build_entry(node: dict) -> Optional[dict]:
    content = node.get("content") or {}
    if content.get("__typename") != "Issue":
        return None

    field_map = map_field_values(node.get("fieldValues", {}).get("nodes", []))

    def take(name: str) -> Any:
        return field_map.get(name)

    resources = {
        "ports": take("Resources.Ports"),
        "services": take("Resources.Services"),
        "notes": take("Resources.Notes"),
        "cpu": take("Resources.CPU"),
        "ram_gb": take("Resources.RAM (GB)"),
        "disk_gb": take("Resources.Disk (GB)"),
    }

    project_fields = {
        "status": take("Status"),
        "role": take("Role"),
        "module": take("Module"),
        "handoff_to": take("Handoff To"),
        "type": take("Type"),
        "ttl_min": take("TTL (min)"),
        "since_utc": take("Since UTC"),
        "updated_utc": take("Updated UTC"),
        "creation_date": take("Creation Date"),
        "updation_date": take("Updation Date"),
    }

    # normalise numeric TTL
    ttl = project_fields["ttl_min"]
    if isinstance(ttl, float) and abs(ttl - round(ttl)) < 1e-9:
        project_fields["ttl_min"] = round(ttl)

    # drop empty entries in resources/project_fields
    resources = {k: v for k, v in resources.items() if v not in (None, "", [])}
    project_fields = {k: v for k, v in project_fields.items() if v not in (None, "")}

    entry = {
        "mirror_version": 1,
        "synced_utc": None,  # заполнится позже
        "source": {
            "project_item_id": node.get("id"),
            "issue_number": content.get("number"),
            "title": content.get("title"),
            "state": (content.get("state") or "").upper(),
            "url": content.get("url"),
            "repository": content.get("repository", {}).get("nameWithOwner"),
            "created_utc": content.get("createdAt"),
            "updated_utc": content.get("updatedAt"),
            "labels": [lbl["name"] for lbl in content.get("labels", {}).get("nodes", [])],
        },
        "project_fields": project_fields,
        "resources": resources,
        "body_markdown": content.get("body"),
    }
    return entry


def parse_args(argv: Optional[Iterable[str]] = None) -> Options:
    parser = argparse.ArgumentParser(description="Синхронизация зеркала issues.json")
    parser.add_argument("--owner", default="LeoTechRu", help="Логин владельца проекта")
    parser.add_argument("--project-number", type=int, default=1, help="Номер Project V2")
    parser.add_argument("--output", type=Path, default=Path("AGENTS/issues.json"))
    args = parser.parse_args(argv)
    return Options(owner=args.owner, project_number=args.project_number, output=args.output)


def main(argv: Optional[Iterable[str]] = None) -> int:
    opts = parse_args(argv)
    token = resolve_token()
    project_id = fetch_project_id(opts.owner, opts.project_number, token)
    nodes = collect_items(project_id, token)

    entries: List[dict] = []
    now_utc = (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    for node in nodes:
        entry = build_entry(node)
        if not entry:
            continue
        entry["synced_utc"] = now_utc
        entries.append(entry)

    payload = {
        "mirror_version": 1,
        "generated_utc": now_utc,
        "items": entries,
    }

    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"[sync-issues] {len(entries)} items → {opts.output}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SyncError as exc:
        print(f"[sync-issues] error: {exc}", file=sys.stderr)
        sys.exit(1)
