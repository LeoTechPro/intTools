#!/usr/bin/env python3
"""
Синхронизирует зеркала GitHub Discussions категорий в JSON.

Полученные данные используются как оффлайн-источник, если GitHub API недоступен.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests

GRAPHQL_URL = "https://api.github.com/graphql"
FEATURE_HEADER = "discussions_api_preview"


class SyncError(RuntimeError):
    """Ошибка синхронизации дискуссий."""


import subprocess


def resolve_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SyncError(
            "Переменная GITHUB_TOKEN не задана и `gh auth token` недоступен"
        ) from exc
    token = result.stdout.strip()
    if not token:
        raise SyncError("`gh auth token` вернул пустой токен")
    return token


CATEGORY_QUERY = """
query($owner:String!, $repo:String!, $slug:String!) {
  repository(owner:$owner, name:$repo) {
    discussionCategory(slug:$slug) { id name slug }
  }
}
"""

DISCUSSIONS_QUERY = """
query($owner:String!, $repo:String!, $categoryId:ID!, $cursor:String, $states:[DiscussionState!]) {
  repository(owner:$owner, name:$repo) {
    discussions(
      first:100,
      after:$cursor,
      orderBy:{field:UPDATED_AT, direction:DESC},
      categoryId:$categoryId,
      states:$states
    ) {
      nodes {
        number
        title
        url
        createdAt
        updatedAt
        author { login }
        body
        answer {
          author { login }
          createdAt
          url
        }
        comments { totalCount }
        labels(first:10) { nodes { name } }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


@dataclass
class CategoryConfig:
    slug: str
    output: Path


def gql_request(query: str, variables: dict, token: str) -> dict:
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


def fetch_category(
    owner: str,
    repo: str,
    slug: str,
    token: str,
    include_all_states: bool = False,
) -> Dict[str, List[dict]]:
    category_data = gql_request(
        CATEGORY_QUERY, {"owner": owner, "repo": repo, "slug": slug}, token
    )
    category_node = category_data["repository"]["discussionCategory"]
    if category_node is None:
        raise SyncError(f"Категория '{slug}' не найдена в {owner}/{repo}")
    category_id = category_node["id"]
    category_name = category_node.get("name") or slug

    discussions: List[dict] = []
    cursor: Optional[str] = None

    while True:
        data = gql_request(
            DISCUSSIONS_QUERY,
            {
                "owner": owner,
                "repo": repo,
                "categoryId": category_id,
                "cursor": cursor,
                "states": None if include_all_states else ["OPEN"],
            },
            token,
        )
        page = data["repository"]["discussions"]
        for node in page["nodes"]:
            entry = {
                "number": node["number"],
                "title": node["title"],
                "url": node["url"],
                "created_utc": node["createdAt"],
                "updated_utc": node["updatedAt"],
                "author": node.get("author", {}).get("login"),
                "body": node.get("body"),
                "comments_total": node.get("comments", {}).get("totalCount"),
            }
            labels = [label["name"] for label in node.get("labels", {}).get("nodes", [])]
            if labels:
                entry["labels"] = labels
            answer = node.get("answer")
            if answer:
                entry["answer"] = {
                    "author": answer.get("author", {}).get("login"),
                    "created_utc": answer.get("createdAt"),
                    "url": answer.get("url"),
                }
            discussions.append(entry)

        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
        time.sleep(0.1)

    generated_at = (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    return {
        "version": 1,
        "generated_utc": generated_at,
        "source": f"GitHub Discussions ({category_name})",
        "items": discussions,
    }


def sync_category(
    config: CategoryConfig,
    owner: str,
    repo: str,
    token: str,
    include_all_states: bool,
) -> None:
    data = fetch_category(owner, repo, config.slug, token, include_all_states)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"[sync-discussions] {config.slug} -> {config.output}")


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Синхронизация зеркал GitHub Discussions категорий в JSON."
    )
    parser.add_argument("--owner", default="LeoTechRu", help="Владелец репозитория (по умолчанию LeoTechRu)")
    parser.add_argument("--repo", default="intData", help="Имя репозитория (по умолчанию intData)")
    parser.add_argument(
        "--slug",
        help="Slug категории (announcements, research и т.д.). При указании — синхронизация только её.",
    )
    parser.add_argument("--output", type=Path, help="Путь для одной категории (используется с --slug).")
    parser.add_argument(
        "--include-closed",
        action="store_true",
        help="Синхронизировать также закрытые/архивные обсуждения (по умолчанию берутся только активные).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Синхронизировать стандартный набор категорий (announcements, research).",
    )
    return parser.parse_args(argv)


DEFAULT_CATEGORIES = {
    "announcements": Path("AGENTS/announcements.json"),
    "research": Path("AGENTS/research.json"),
}


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    try:
        token = resolve_token()
        configs: List[CategoryConfig] = []

        if args.slug:
            if args.all:
                raise SyncError("Нельзя одновременно задавать --slug и --all")
            output = args.output or DEFAULT_CATEGORIES.get(args.slug)
            if output is None:
                raise SyncError("Для произвольного slug необходимо указать --output")
            configs.append(CategoryConfig(slug=args.slug, output=output))
        else:
            selected = DEFAULT_CATEGORIES if args.all else DEFAULT_CATEGORIES
            for slug, path in selected.items():
                configs.append(CategoryConfig(slug=slug, output=path))

        include_all = bool(args.include_closed)
        for config in configs:
            sync_category(config, args.owner, args.repo, token, include_all)
    except SyncError as exc:
        print(f"[sync-discussions] ошибка: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("[sync-discussions] прервано пользователем", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
