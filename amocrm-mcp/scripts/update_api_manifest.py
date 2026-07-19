"""Build the public amoCRM HTTP endpoint manifest from official documentation.

The generated file is committed so production startup never depends on the
documentation site.  Re-running this script is the audit/update workflow.
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "amocrm_mcp" / "api_manifest.json"
DOC_ROOT = "https://www.amocrm.ru/developers/content/"

CRM_PAGES = (
    "crm_platform/account-info",
    "crm_platform/calls-api",
    "crm_platform/catalogs-api",
    "crm_platform/chat-templates-api",
    "crm_platform/companies-api",
    "crm_platform/contacts-api",
    "crm_platform/custom-fields",
    "crm_platform/customers-api",
    "crm_platform/customers-statuses-api",
    "crm_platform/duplication-control",
    "crm_platform/entity-links-api",
    "crm_platform/events-and-notes",
    "crm_platform/leads_pipelines",
    "crm_platform/leads-api",
    "crm_platform/products-api",
    "crm_platform/salesbot-api",
    "crm_platform/short_links",
    "crm_platform/sources-api",
    "crm_platform/subscriptions-api",
    "crm_platform/tags-api",
    "crm_platform/talks-api",
    "crm_platform/tasks-api",
    "crm_platform/unsorted-api",
    "crm_platform/users-api",
    "crm_platform/webhooks-api",
    "crm_platform/widgets-api",
)

OTHER_PAGES = (
    ("chats", "chats/chat-api-reference"),
    ("files", "files/files-api"),
    ("telephony", "telephony/call_event"),
)

HTTP_RE = re.compile(
    r"\b(GET|POST|PATCH|PUT|DELETE)\s+"
    r"((?:https?://[^\s<\"']+)?/(?:api/|v1\.0/|v2/)[^\s<\"']*)",
    re.IGNORECASE,
)


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "amocrm-mcp-parity-audit/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_path(raw: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
    value = re.sub(r"^https?://[^/]+", "", value)
    value = value.split("?", 1)[0]
    value = value.rstrip(".,;:)]")
    value = value.replace("&lbrace;", "{").replace("&rbrace;", "}")
    value = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*):[^{}]+\}", r"{\1}", value)
    return value


def endpoint_id(surface: str, method: str, path: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")
    return f"{surface}_{method.lower()}_{slug}"


def extract(surface: str, source: str, body: str) -> list[dict[str, str]]:
    endpoints: list[dict[str, str]] = []
    for match in HTTP_RE.finditer(html.unescape(body)):
        method = match.group(1).upper()
        path = clean_path(match.group(2))
        if not path.startswith(("/api/", "/v1.0/", "/v2/")):
            continue
        endpoints.append(
            {
                "id": endpoint_id(surface, method, path),
                "surface": surface,
                "method": method,
                "path": path,
                "host": "drive" if surface == "files" and path.startswith("/v1.0/") else "account",
                "auth": "hmac-sha1" if surface == "chats" else "oauth-bearer",
                "source": source,
            }
        )
    return endpoints


def main() -> None:
    records: dict[tuple[str, str, str], dict[str, str]] = {}
    sources: list[str] = []

    for page in CRM_PAGES:
        url = DOC_ROOT + page
        sources.append(url)
        surface = "webhooks" if page == "crm_platform/webhooks-api" else "rest"
        for item in extract(surface, url, fetch(url)):
            records[(item["surface"], item["method"], item["path"])] = item

    for surface, page in OTHER_PAGES:
        url = DOC_ROOT + page
        try:
            body = fetch(url)
        except Exception:
            # Telephony documentation has changed location historically; the
            # authoritative endpoint below is retained as a manual assertion.
            if surface != "telephony":
                raise
            continue
        sources.append(url)
        for item in extract(surface, url, body):
            records[(item["surface"], item["method"], item["path"])] = item

    # Official backend endpoint documented on the telephony integration page.
    telephony_source = DOC_ROOT + "telephony/call_event"
    item = {
        "id": endpoint_id("telephony", "POST", "/api/v2/events/"),
        "surface": "telephony",
        "method": "POST",
        "path": "/api/v2/events/",
        "host": "account",
        "auth": "oauth-bearer",
        "source": telephony_source,
    }
    records[(item["surface"], item["method"], item["path"])] = item

    endpoints = sorted(records.values(), key=lambda row: (row["surface"], row["path"], row["method"]))
    manifest = {
        "schema_version": 1,
        "generated_from": sorted(set(sources + [telephony_source])),
        "excluded_surfaces": [
            {
                "name": "notifications-ui",
                "reason": "Browser-only APP.notifications JavaScript API; not a server HTTP API.",
                "source": DOC_ROOT + "crm_platform/adding_notifications",
            }
        ],
        "endpoints": endpoints,
    }
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(endpoints)} endpoints to {OUTPUT}")


if __name__ == "__main__":
    main()
