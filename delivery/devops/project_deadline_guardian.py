#!/usr/bin/env python3
"""
Deadline Guardian for GitHub Project V2 items.

Скрипт проверяет поле дедлайна в карточках проекта, переводит просроченные
элементы в выбранный статус и уведомляет ответственное лицо.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone, time as time_cls
from typing import Dict, Iterable, List, Optional, Tuple

import requests


API_GRAPHQL_DEFAULT = "https://api.github.com/graphql"


class GithubApiError(RuntimeError):
    """Исключение для ошибок GitHub API."""


def _env(name: str, required: bool = True) -> Optional[str]:
    value = os.getenv(name)
    if required and not value:
        raise GithubApiError(f"Ожидается переменная окружения {name}")
    return value


def parse_deadline(value: str) -> datetime:
    """Возвращает момент окончания дедлайна в UTC."""
    value = value.strip()
    if not value:
        raise GithubApiError("Пустой дедлайн")
    # Формат YYYY-MM-DD
    if len(value) == 10:
        try:
            date = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise GithubApiError(f"Неверный формат дедлайна: {value}") from exc
        return datetime.combine(date, time_cls(23, 59, 59), tzinfo=timezone.utc)
    # ISO 8601
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError as exc:
        raise GithubApiError(f"Неверный формат дедлайна: {value}") from exc


def graphql(token: str, query: str, variables: dict, api_url: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.post(api_url, json={"query": query, "variables": variables}, headers=headers, timeout=30)
    if response.status_code != 200:
        raise GithubApiError(f"GraphQL HTTP {response.status_code}: {response.text}")
    data = response.json()
    if "errors" in data:
        raise GithubApiError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def get_user_or_org_project(token: str, api_url: str, owner: str, number: int) -> Tuple[str, dict]:
    """Находит проект пользователя или организации и возвращает тип владельца и тело проекта."""
    user_query = """
    query($login: String!, $number: Int!) {
      user(login: $login) {
        projectV2(number: $number) {
          id
          title
        }
      }
    }
    """
    data = graphql(token, user_query, {"login": owner, "number": number}, api_url)
    user = data.get("user")
    if user and user.get("projectV2"):
        return "USER", user["projectV2"]

    org_query = """
    query($login: String!, $number: Int!) {
      organization(login: $login) {
        projectV2(number: $number) {
          id
          title
        }
      }
    }
    """
    data = graphql(token, org_query, {"login": owner, "number": number}, api_url)
    organization = data.get("organization")
    if organization and organization.get("projectV2"):
        return "ORG", organization["projectV2"]
    raise GithubApiError(f"Проект {owner} #{number} не найден")


@dataclass
class FieldIds:
    status: str
    status_overdue_option: str
    deadline: str


@dataclass
class ProjectItem:
    item_id: str
    issue_id: Optional[str]
    issue_number: Optional[int]
    issue_repo: Optional[str]
    current_status_option: Optional[str]
    deadline: Optional[str]


ITEMS_QUERY_USER = """
query($owner: String!, $number: Int!, $after: String) {
  user(login: $owner) {
    projectV2(number: $number) {
      id
      items(first: 50, after: $after) {
        nodes {
          id
          content {
            __typename
            ... on Issue {
              id
              number
              repository {
                nameWithOwner
              }
            }
          }
          fieldValues(first: 20) {
            nodes {
              __typename
              ... on ProjectV2ItemFieldDateValue {
                date
                field { ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldTextValue {
                text
                field { ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldNumberValue {
                number
                field { ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                optionId
                field { ... on ProjectV2FieldCommon { id name } }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""

ITEMS_QUERY_ORG = """
query($owner: String!, $number: Int!, $after: String) {
  organization(login: $owner) {
    projectV2(number: $number) {
      id
      items(first: 50, after: $after) {
        nodes {
          id
          content {
            __typename
            ... on Issue {
              id
              number
              repository {
                nameWithOwner
              }
            }
          }
          fieldValues(first: 20) {
            nodes {
              __typename
              ... on ProjectV2ItemFieldDateValue {
                date
                field { ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldTextValue {
                text
                field { ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldNumberValue {
                number
                field { ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                optionId
                field { ... on ProjectV2FieldCommon { id name } }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""


def list_project_items(token: str, api_url: str, owner: str, number: int, owner_type: str) -> Iterable[ProjectItem]:
    cursor = None
    while True:
        query = ITEMS_QUERY_USER if owner_type == "USER" else ITEMS_QUERY_ORG
        data = graphql(token, query, {"owner": owner, "number": number, "after": cursor}, api_url)
        project_node = (data.get("user") or {}).get("projectV2") if owner_type == "USER" else (data.get("organization") or {}).get("projectV2")
        if not project_node:
            break
        page = project_node["items"]
        for node in page["nodes"]:
            content = node.get("content") or {}
            typename = content.get("__typename")
            issue_id = None
            issue_number = None
            issue_repo = None
            if typename == "Issue":
                issue_id = content["id"]
                issue_number = int(content["number"])
                issue_repo = content["repository"]["nameWithOwner"]
            field_map: Dict[str, dict] = {}
            for fv in node["fieldValues"]["nodes"]:
                field = fv.get("field")
                if not field:
                    continue
                field_map[field["id"]] = fv
            deadline_value = field_map.get(FIELD_IDS.deadline, {})
            deadline = (
                deadline_value.get("date")
                or deadline_value.get("text")
                or (
                    str(deadline_value.get("number"))
                    if deadline_value.get("number") is not None
                    else None
                )
            )
            yield ProjectItem(
                item_id=node["id"],
                issue_id=issue_id,
                issue_number=issue_number,
                issue_repo=issue_repo,
                current_status_option=field_map.get(FIELD_IDS.status, {}).get("optionId"),
                deadline=deadline,
            )
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
        time.sleep(0.2)


UPDATE_STATUS_MUTATION = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId,
      itemId: $itemId,
      fieldId: $fieldId,
      value: { singleSelectOptionId: $optionId }
    }
  ) {
    projectV2Item {
      id
    }
  }
}
"""

ADD_COMMENT_MUTATION = """
mutation($subjectId: ID!, $body: String!) {
  addComment(input: {subjectId: $subjectId, body: $body}) {
    commentEdge {
      node {
        id
      }
    }
  }
}
"""

ADD_ASSIGNEES_MUTATION = """
mutation($assignableId: ID!, $assigneeIds: [ID!]!) {
  addAssigneesToAssignable(input: {assignableId: $assignableId, assigneeIds: $assigneeIds}) {
    assignable {
      id
    }
  }
}
"""


def resolve_user_id(token: str, api_url: str, login: str) -> str:
    query = """
    query($login: String!) {
      user(login: $login) {
        id
      }
    }
    """
    data = graphql(token, query, {"login": login}, api_url)
    user = data["user"]
    if not user:
        raise GithubApiError(f"Пользователь {login} не найден")
    return user["id"]


def set_status_overdue(token: str, api_url: str, project_id: str, item_id: str) -> None:
    graphql(
        token,
        UPDATE_STATUS_MUTATION,
        {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": FIELD_IDS.status,
            "optionId": FIELD_IDS.status_overdue_option,
        },
        api_url,
    )


def add_overdue_comment(token: str, api_url: str, issue_id: str, deadline_at: datetime, mention: Optional[str]) -> None:
    mention_text = f"@{mention}" if mention else "Ответственный"
    body = (
        "<!-- deadline-guardian -->\n"
        f"⚠️ Дедлайн `{deadline_at.date().isoformat()}` просрочен. {mention_text}, требуется реакция. "
        "Статус карточки обновлён на `Expired`."
    )
    graphql(token, ADD_COMMENT_MUTATION, {"subjectId": issue_id, "body": body}, api_url)


def assign_issue_owner(token: str, api_url: str, issue_id: str, user_id: str) -> None:
    graphql(token, ADD_ASSIGNEES_MUTATION, {"assignableId": issue_id, "assigneeIds": [user_id]}, api_url)


def main() -> int:
    token = _env("GITHUB_TOKEN")
    project_owner = _env("PROJECT_OWNER")
    project_number = int(_env("PROJECT_NUMBER"))
    api_url = os.getenv("GITHUB_GRAPHQL_URL", API_GRAPHQL_DEFAULT)

    mention_login = (os.getenv("MENTION_LOGIN") or "").strip()
    mention_user_id = None
    if mention_login:
        try:
            mention_user_id = resolve_user_id(token, api_url, mention_login)
        except GithubApiError as exc:
            print(f"[warn] {exc}", file=sys.stderr)

    owner_type, project_meta = get_user_or_org_project(token, api_url, project_owner, project_number)
    project_id = project_meta["id"]

    now = datetime.now(timezone.utc)
    processed: List[str] = []

    for item in list_project_items(token, api_url, project_owner, project_number, owner_type):
        if not item.deadline:
            continue
        try:
            deadline_dt = parse_deadline(item.deadline)
        except GithubApiError as exc:
            print(f"[warn] {exc}", file=sys.stderr)
            continue

        if now <= deadline_dt:
            continue
        if item.current_status_option == FIELD_IDS.status_overdue_option:
            continue

        set_status_overdue(token, api_url, project_id, item.item_id)
        processed.append(item.item_id)

        if item.issue_id:
            add_overdue_comment(token, api_url, item.issue_id, deadline_dt, mention_login)
            if mention_user_id:
                assign_issue_owner(token, api_url, item.issue_id, mention_user_id)

    print(f"Overdue items processed: {len(processed)}")
    return 0


if __name__ == "__main__":
    try:
        FIELD_IDS = FieldIds(
            status=_env("STATUS_FIELD_ID"),
            status_overdue_option=_env("STATUS_OVERDUE_OPTION_ID"),
            deadline=_env("DEADLINE_FIELD_ID"),
        )
        sys.exit(main())
    except GithubApiError as exc:
        print(f"[deadline-guardian] ошибка: {exc}", file=sys.stderr)
        sys.exit(1)
