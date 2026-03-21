#!/usr/bin/env python3
"""
Импорт оффлайн-черновиков из `AGENTS/issues.json` (`offline_queue`) в GitHub Project V2.

Алгоритм:
1. Читает `AGENTS/issues.json` и забирает объекты из массива `offline_queue`.
2. Для каждого черновика создаёт Draft Issue в проекте, переносит тело/метаданные.
3. По возможности заполняет поля (Status, Role, Module, Type, Since/Updated UTC, Deadline).
4. После успешного создания удаляет запись из `offline_queue` и переписывает JSON.

Требования:
- авторизация `gh auth status` (должен работать `gh auth token`);
- переменные окружения (опционально) `STATUS_OPTION_<STATUS>` с ID вариантов поля Status
  (например, `STATUS_OPTION_BACKLOG=...`). Если переменная не задана, поле не заполняется;
- `AGENTS/issues.json` должен быть в актуальном формате (см. README).
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


PROJECT_OWNER = os.getenv("PROJECT_OWNER", "LeoTechRu")
PROJECT_NUMBER = int(os.getenv("PROJECT_NUMBER", "1"))
REPO = os.getenv("REPO", "LeoTechRu/intData")
ISSUES_MIRROR = Path(os.getenv("ISSUES_MIRROR", "AGENTS/issues.json"))
API_URL = os.getenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")


FIELD_IDS = {
    "status": "PVTSSF_lAHOAprIjs4BFUGCzg2r-1o",
    "role": "PVTSSF_lAHOAprIjs4BFUGCzg2sAwg",
    "module": "PVTSSF_lAHOAprIjs4BFUGCzg2sAwk",
    "since": "PVTF_lAHOAprIjs4BFUGCzg2sB9o",
    "updated": "PVTF_lAHOAprIjs4BFUGCzg2sB9s",
    "ttl": "PVTF_lAHOAprIjs4BFUGCzg2sAyw",
}

ROLE_OPTIONS = {
    "teamlead": ("Team Lead", "bda914c3"),
    "architect": ("Architect", "6b73d875"),
    "backend": ("Backend", "57d4c981"),
    "frontend": ("Frontend", "167ef5c1"),
    "qa": ("QA", "d0ab980e"),
    "infosec": ("Infosec", "aac6fa93"),
    "devops": ("DevOps", "95efb900"),
    "dba": ("DBA", "ed05c0ec"),
    "techwriter": ("Tech Writer", "e73098aa"),
}

MODULE_OPTIONS = {
    "nexus": "8a26cc98",
    "id": "ce417a79",
    "crm": "518be9a4",
    "erp": "5405fc7d",
    "chat": "f57ab845",
    "bridge": "82af873c",
    "bot": "be24dfd4",
    "shared": "37ca6646",
    "configs": "bcef9b17",
    "scripts": "589a1df5",
}


class GithubApiError(RuntimeError):
    """Ошибка GraphQL API GitHub."""


def env_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GithubApiError("GITHUB_TOKEN не задан. Получите токен командой `gh auth token`.")
    return token


def graphql(query: str, variables: dict) -> dict:
    response = requests.post(
        API_URL,
        json={"query": query, "variables": variables},
        headers={
            "Authorization": f"Bearer {env_token()}",
            "Accept": "application/vnd.github+json",
            "GraphQL-Features": "projects_next_graphql",
        },
        timeout=40,
    )
    if response.status_code != 200:
        raise GithubApiError(f"GraphQL HTTP {response.status_code}: {response.text}")
    payload = response.json()
    if "errors" in payload:
        raise GithubApiError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


def resolve_project() -> tuple[str, str]:
    user_query = """
    query($login: String!, $number: Int!) {
      user(login: $login) {
        projectV2(number: $number) { id }
      }
    }
    """
    data = graphql(user_query, {"login": PROJECT_OWNER, "number": PROJECT_NUMBER})
    user = data.get("user")
    if user and user.get("projectV2"):
        return "USER", user["projectV2"]["id"]

    org_query = """
    query($login: String!, $number: Int!) {
      organization(login: $login) {
        projectV2(number: $number) { id }
      }
    }
    """
    data = graphql(org_query, {"login": PROJECT_OWNER, "number": PROJECT_NUMBER})
    org = data.get("organization")
    if org and org.get("projectV2"):
        return "ORG", org["projectV2"]["id"]

    raise GithubApiError(f"Проект {PROJECT_OWNER} #{PROJECT_NUMBER} не найден")


CREATE_DRAFT_MUTATION = """
mutation($projectId: ID!, $title: String!, $body: String!) {
  addProjectV2DraftIssue(input: {projectId: $projectId, title: $title, body: $body}) {
    projectItem { id }
  }
}
"""

UPDATE_TEXT_MUTATION = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $text: String!) {
  updateProjectV2ItemFieldValue(
    input: { projectId: $projectId, itemId: $itemId, fieldId: $fieldId, value: { text: $text } }
  ) { projectV2Item { id } }
}
"""

UPDATE_NUMBER_MUTATION = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $number: Float!) {
  updateProjectV2ItemFieldValue(
    input: { projectId: $projectId, itemId: $itemId, fieldId: $fieldId, value: { number: $number } }
  ) { projectV2Item { id } }
}
"""

UPDATE_SINGLE_SELECT_MUTATION = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId,
      itemId: $itemId,
      fieldId: $fieldId,
      value: { singleSelectOptionId: $optionId }
    }
  ) { projectV2Item { id } }
}
"""


@dataclass
class OfflineDraft:
    draft_id: str
    title: str
    body_markdown: str
    status: Optional[str]
    role: Optional[str]
    module: Optional[str]
    since_utc: Optional[str]
    updated_utc: Optional[str]
    ttl_min: Optional[float]
    resources: Optional[Dict[str, Any]]


def load_offline_drafts() -> List[OfflineDraft]:
    if not ISSUES_MIRROR.exists():
        raise FileNotFoundError(f"{ISSUES_MIRROR} не найден")
    data = json.loads(ISSUES_MIRROR.read_text("utf-8"))
    drafts = []
    for raw in data.get("offline_queue", []):
        drafts.append(
            OfflineDraft(
                draft_id=raw.get("draft_id") or raw.get("title", "offline-draft"),
                title=raw.get("title") or raw.get("draft_id") or "offline-draft",
                body_markdown=raw.get("body_markdown") or "",
                status=raw.get("status"),
                role=(raw.get("role") or "").lower(),
                module=(raw.get("module") or "").lower(),
                since_utc=raw.get("since_utc"),
                updated_utc=raw.get("updated_utc"),
                ttl_min=raw.get("ttl_min"),
                resources=raw.get("resources"),
            )
        )
    return drafts


def save_offline_queue(updated_queue: List[dict], original: dict) -> None:
    original["offline_queue"] = updated_queue
    ISSUES_MIRROR.write_text(json.dumps(original, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_mirror_raw() -> dict:
    return json.loads(ISSUES_MIRROR.read_text("utf-8"))


def status_option_id(status: Optional[str]) -> Optional[str]:
    if not status:
        return None
    key = f"STATUS_OPTION_{status.upper()}"
    return os.getenv(key)


def set_text_field(project_id: str, item_id: str, field_id: str, value: Optional[str]) -> None:
    if not value:
        return
    graphql(UPDATE_TEXT_MUTATION, {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "text": value})
    time.sleep(0.1)


def set_number_field(project_id: str, item_id: str, field_id: str, value: Optional[float]) -> None:
    if value is None:
        return
    graphql(UPDATE_NUMBER_MUTATION, {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "number": value})
    time.sleep(0.1)


def set_single_select_field(project_id: str, item_id: str, field_id: str, option_id: Optional[str]) -> None:
    if not option_id:
        return
    graphql(
        UPDATE_SINGLE_SELECT_MUTATION,
        {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "optionId": option_id},
    )
    time.sleep(0.1)


def create_draft(project_id: str, draft: OfflineDraft) -> str:
    body = draft.body_markdown or f"Импорт из AGENTS/issues.json (draft_id: {draft.draft_id})"
    data = graphql(CREATE_DRAFT_MUTATION, {"projectId": project_id, "title": draft.title, "body": body})
    return data["addProjectV2DraftIssue"]["projectItem"]["id"]


def main() -> int:
    mirror_raw = load_mirror_raw()
    drafts = load_offline_drafts()
    if not drafts:
        print("[info] offline_queue пуст — нечего импортировать")
        return 0

    owner_type, project_id = resolve_project()
    print(f"[info] проект найден ({owner_type}), оффлайн-черновиков: {len(drafts)}")

    remaining_queue: List[dict] = mirror_raw.get("offline_queue", []).copy()
    created = 0

    for draft in drafts:
        try:
            item_id = create_draft(project_id, draft)
            print(f"[create] {draft.draft_id} → item {item_id}")

            # status
            option = status_option_id(draft.status)
            if option:
                set_single_select_field(project_id, item_id, FIELD_IDS["status"], option)

            # role
            role_option = ROLE_OPTIONS.get(draft.role or "")
            if role_option:
                set_single_select_field(project_id, item_id, FIELD_IDS["role"], role_option[1])

            # module
            module_option = MODULE_OPTIONS.get(draft.module or "")
            if module_option:
                set_single_select_field(project_id, item_id, FIELD_IDS["module"], module_option)

            # since/updated
            set_text_field(project_id, item_id, FIELD_IDS["since"], draft.since_utc)
            set_text_field(project_id, item_id, FIELD_IDS["updated"], draft.updated_utc)

            # ttl
            if draft.ttl_min is not None:
                set_number_field(project_id, item_id, FIELD_IDS["ttl"], float(draft.ttl_min))

            created += 1
            # удаляем из offline_queue
            remaining_queue = [entry for entry in remaining_queue if entry.get("draft_id") != draft.draft_id]
            time.sleep(0.2)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {draft.draft_id}: {exc}", file=sys.stderr)
            # не удаляем черновик — нужно повторить после исправления проблемы

    save_offline_queue(remaining_queue, mirror_raw)
    print(f"[done] создано: {created}, осталось в offline_queue: {len(remaining_queue)}")
    return 0 if created == len(drafts) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GithubApiError as err:
        print(f"[fatal] {err}", file=sys.stderr)
        sys.exit(2)
