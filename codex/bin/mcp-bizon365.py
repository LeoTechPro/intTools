#!/usr/bin/env python3

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import requests
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


def resolve_default_env_path() -> Path:
    primary = Path(os.environ.get("CODEX_SECRETS_ROOT", "/int/.runtime/codex-secrets")) / "bizon365-punctb.env"
    legacy = Path.home() / ".codex" / "var" / "bizon365-punctb.env"
    return primary if primary.exists() else legacy


DEFAULT_ENV_PATH = resolve_default_env_path()
DEFAULT_DOWNLOAD_DIR = Path.home() / ".codex" / "tmp" / "bizon365" / "downloads"
DEFAULT_PROFILE_ROLES = {"codex": "operator", "openclaw": "admin"}
ROLE_ORDER = {"viewer": 0, "operator": 1, "admin": 2}
UNSAFE_PATH_TOKENS = (
    "delete",
    "remove",
    "purge",
    "transfer",
    "save",
    "change",
    "reset",
    "logout",
    "upload",
    "createbot",
)
REDACTED_KEYS = {
    "pwd",
    "password",
    "privatekey",
    "token",
    "secret",
    "hash",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
}
TOOLS = (
    "bizon_auth_health",
    "bizon_get_project_info",
    "bizon_get_project_settings",
    "bizon_list_rooms",
    "bizon_find_rooms",
    "bizon_get_room",
    "bizon_list_staff",
    "bizon_list_disk_files",
    "bizon_download_disk_file",
    "bizon_find_recording",
    "bizon_get_archive_room_rec",
    "bizon_search_archive_recordings",
    "bizon_refresh_session",
    "bizon_raw_get",
    "bizon_raw_post",
    "bizon_room_admin_call",
    "bizon_disk_admin_call",
)
TOOL_MIN_ROLE = {
    "bizon_auth_health": "viewer",
    "bizon_get_project_info": "viewer",
    "bizon_get_project_settings": "viewer",
    "bizon_list_rooms": "viewer",
    "bizon_find_rooms": "viewer",
    "bizon_get_room": "viewer",
    "bizon_list_staff": "viewer",
    "bizon_list_disk_files": "operator",
    "bizon_download_disk_file": "operator",
    "bizon_find_recording": "operator",
    "bizon_get_archive_room_rec": "operator",
    "bizon_search_archive_recordings": "operator",
    "bizon_refresh_session": "admin",
    "bizon_raw_get": "admin",
    "bizon_raw_post": "admin",
    "bizon_room_admin_call": "admin",
    "bizon_disk_admin_call": "admin",
}
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
MUTATING = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


class BizonError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        payload = {"ok": False, "error": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


def load_env_file(file_path: Path) -> None:
    if not file_path.exists():
        return
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _normalize_role(value: str | None, default: str = "viewer") -> str:
    normalized = str(value or "").strip().lower()
    if normalized in ROLE_ORDER:
        return normalized
    return default


def _normalize_profile(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized or "codex"


def _role_map_from_env(env: dict[str, str] | None = None) -> dict[str, str]:
    source = os.environ if env is None else env
    raw = str(source.get("BIZON365_MCP_PROFILE_ROLES", "")).strip()
    if not raw:
        return dict(DEFAULT_PROFILE_ROLES)
    try:
        payload = json.loads(raw)
    except Exception:
        return dict(DEFAULT_PROFILE_ROLES)
    if not isinstance(payload, dict):
        return dict(DEFAULT_PROFILE_ROLES)
    mapping = dict(DEFAULT_PROFILE_ROLES)
    for key, value in payload.items():
        mapping[_normalize_profile(str(key))] = _normalize_role(str(value), mapping.get(str(key), "viewer"))
    return mapping


def resolve_mcp_context(
    *,
    env: dict[str, str] | None = None,
    role: str | None = None,
    client_profile: str | None = None,
) -> dict[str, Any]:
    source = os.environ if env is None else env
    resolved_profile = _normalize_profile(client_profile or source.get("BIZON365_MCP_CLIENT_PROFILE", ""))
    resolved_role = _normalize_role(role or source.get("BIZON365_MCP_ROLE", ""))
    profile_roles = _role_map_from_env(source)
    if not str(role or source.get("BIZON365_MCP_ROLE", "")).strip():
        resolved_role = _normalize_role(profile_roles.get(resolved_profile), "viewer")
    return {
        "client_profile": resolved_profile,
        "role": resolved_role,
        "profile_roles": profile_roles,
    }


def allowed_tool_names_for_role(role: str) -> list[str]:
    resolved_role = _normalize_role(role)
    return [tool_name for tool_name in TOOLS if ROLE_ORDER[resolved_role] >= ROLE_ORDER[TOOL_MIN_ROLE[tool_name]]]


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "download.bin"


def _normalize_text(value: str) -> str:
    lowered = str(value or "").lower()
    lowered = lowered.replace(":", " ").replace("_", " ").replace("-", " ").replace("/", " ")
    lowered = re.sub(r"[^0-9a-zа-яё\s]+", " ", lowered, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", lowered).strip()


def _tokenize(value: str) -> list[str]:
    normalized = _normalize_text(value)
    return [token for token in normalized.split(" ") if token]


def _score_tokens(query_tokens: list[str], *haystacks: str) -> float:
    if not query_tokens:
        return 0.0
    joined = " ".join(_normalize_text(item) for item in haystacks if item)
    if not joined:
        return 0.0
    score = 0.0
    for token in query_tokens:
        if token in joined:
            score += 3.0 if f" {token} " in f" {joined} " else 1.5
    return score


def _parse_datetime(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except Exception:
        return raw


def _clamp_limit(value: int | None, *, default: int = 20, maximum: int = 500) -> int:
    try:
        normalized = int(value or default)
    except Exception:
        normalized = default
    return max(1, min(maximum, normalized))


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in REDACTED_KEYS or any(token in lowered for token in REDACTED_KEYS):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = _redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    return value


def _safe_json_loads(raw_text: str) -> Any:
    try:
        return json.loads(raw_text)
    except Exception:
        return raw_text


def _extract_captcha(html: str) -> tuple[str, str]:
    cap1_match = re.search(r"window\.captcha_1 = '([^']+)'", html)
    cap2_match = re.search(r"window\.captcha_2 = '([^']+)'", html)
    if not cap1_match or not cap2_match:
        raise BizonError("auth_failed", "Failed to extract Bizon365 captcha tokens")
    return cap1_match.group(1), cap2_match.group(1)


def _json_response(
    *,
    source: str,
    project_id: str,
    data: Any = None,
    warnings: list[str] | None = None,
    debug: Any = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "source": source,
        "project_id": project_id,
        "data": data,
        "warnings": warnings or [],
    }
    if debug is not None:
        payload["debug"] = debug
    return payload


def _resolve_path_within_root(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise BizonError(
            "endpoint_not_allowed",
            "Archive path escapes archive root",
            details={"path": str(resolved_candidate), "archive_root": str(resolved_root)},
        ) from exc
    return resolved_candidate


class BizonClient:
    def __init__(self, env: dict[str, str]):
        self.env = env
        self.base_url = str(env.get("BIZON365_BASE_URL", "https://start.bizon365.ru")).rstrip("/")
        self.project_id = str(env.get("BIZON365_PROJECT_ID", "")).strip()
        self.login_name = str(env.get("BIZON365_LOGIN", "")).strip()
        self.password = str(env.get("BIZON365_PASSWORD", "")).strip()
        self.archive_root = Path(str(env.get("BIZON365_ARCHIVE_YADISK_ROOT", "/int/cloud/yadisk/Вебинары")).strip())
        self.download_dir = Path(str(env.get("BIZON365_DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR)).strip())
        self.download_dir.mkdir(parents=True, exist_ok=True)
        if not self.project_id:
            raise BizonError("auth_failed", "BIZON365_PROJECT_ID is not set")
        if not self.login_name or not self.password:
            raise BizonError("auth_failed", "BIZON365_LOGIN or BIZON365_PASSWORD is not set")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "bizon365-mcp/1.0",
            }
        )
        self._auth_lock = threading.Lock()
        self.last_login_at = ""

    def _allowed_prefixes(self) -> dict[str, tuple[str, ...]]:
        project = self.project_id
        return {
            "raw": (
                f"/admin/account/api/{project}/",
                f"/admin/rooms/api/{project}/",
                f"/admin/users/api/{project}/",
                f"/admin/service/{project}/",
                "/my/id/api/",
            ),
            "room": (
                f"/admin/rooms/api/{project}/",
                "/admin/room/",
            ),
            "disk": (
                f"/admin/service/{project}/",
            ),
        }

    def _validate_path(self, path: str, kind: str, *, method: str) -> str:
        normalized = "/" + str(path or "").lstrip("/")
        prefixes = self._allowed_prefixes()[kind]
        if not any(normalized.startswith(prefix) for prefix in prefixes):
            raise BizonError("endpoint_not_allowed", f"Endpoint is outside {kind} allowlist", details={"path": normalized})
        lowered = normalized.lower()
        if method.upper() != "GET":
            for token in UNSAFE_PATH_TOKENS:
                if token in lowered:
                    raise BizonError(
                        "unsafe_operation_blocked",
                        "Blocked unsafe Bizon365 endpoint",
                        details={"path": normalized, "token": token},
                    )
        return normalized

    def login(self, *, force: bool = False) -> dict[str, Any]:
        with self._auth_lock:
            if not force and self._session.cookies.get("sid"):
                return {"logged_in": True, "sid_present": True, "last_login_at": self.last_login_at}
            login_page = self._session.get(
                f"{self.base_url}/my/login?redirect=/admin/",
                timeout=30,
            )
            if not login_page.ok:
                raise BizonError("auth_failed", f"Bizon365 login page returned HTTP {login_page.status_code}")
            captcha_1, captcha_2 = _extract_captcha(login_page.text)
            response = self._session.post(
                f"{self.base_url}/my/login/api/loginUser",
                json={
                    "userlogin": self.login_name,
                    "password": self.password,
                    "captcha_1": captcha_1,
                    "captcha_2": captcha_2,
                },
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json; charset=UTF-8",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            payload = _safe_json_loads(response.text)
            if not response.ok:
                message = payload.get("message") if isinstance(payload, dict) else str(payload)
                raise BizonError("auth_failed", message or f"Bizon365 login failed with HTTP {response.status_code}")
            if isinstance(payload, dict) and payload.get("message") and not self._session.cookies.get("sid"):
                raise BizonError("auth_failed", str(payload.get("message")))
            if not self._session.cookies.get("sid"):
                raise BizonError("auth_failed", "Bizon365 login did not return sid cookie")
            self.last_login_at = datetime.now(timezone.utc).isoformat()
            return {"logged_in": True, "sid_present": True, "last_login_at": self.last_login_at}

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        allow_reauth: bool = True,
        empty_ok: bool = False,
    ) -> Any:
        self.login()
        url = f"{self.base_url}{path}"
        response = self._session.request(
            method.upper(),
            url,
            params=query,
            json=body,
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
            timeout=30,
        )
        if response.status_code == 401 and allow_reauth:
            self.login(force=True)
            return self._request_json(method, path, query=query, body=body, allow_reauth=False, empty_ok=empty_ok)
        if not response.ok:
            parsed_error = _safe_json_loads(response.text)
            message = parsed_error.get("message") if isinstance(parsed_error, dict) else str(parsed_error)
            raise BizonError(
                "bizon_http_error",
                message or f"Bizon365 API returned HTTP {response.status_code}",
                details={"path": path, "status": response.status_code},
            )
        raw_text = response.text.strip()
        if not raw_text:
            if allow_reauth and not empty_ok:
                self.login(force=True)
                return self._request_json(method, path, query=query, body=body, allow_reauth=False, empty_ok=empty_ok)
            return {}
        parsed = _safe_json_loads(raw_text)
        if parsed == {} and allow_reauth and method.upper() == "GET" and not empty_ok:
            self.login(force=True)
            return self._request_json(method, path, query=query, body=body, allow_reauth=False, empty_ok=empty_ok)
        return parsed

    def auth_health(self) -> dict[str, Any]:
        auth = self.login()
        project_info = self.get_project_info()
        project_settings = self.get_project_settings()
        return {
            **auth,
            "project_title": str(project_settings.get("title") or project_info.get("title", "")).strip(),
            "project_slug": str(project_settings.get("slug") or project_info.get("slug", "")).strip(),
        }

    def get_project_info(self) -> dict[str, Any]:
        payload = self._request_json("GET", f"/admin/account/api/{self.project_id}/getProjectInfo")
        if not isinstance(payload, dict):
            raise BizonError("bizon_http_error", "Unexpected project info payload")
        return payload

    def get_project_settings(self) -> dict[str, Any]:
        payload = self._request_json("GET", f"/admin/account/api/{self.project_id}/getProjectSettings")
        if not isinstance(payload, dict):
            raise BizonError("bizon_http_error", "Unexpected project settings payload")
        return payload

    def get_rooms(self) -> dict[str, Any]:
        payload = self._request_json("GET", f"/admin/rooms/api/{self.project_id}/getRooms")
        if not isinstance(payload, dict):
            raise BizonError("bizon_http_error", "Unexpected rooms payload")
        return payload

    def get_users(self) -> dict[str, Any]:
        payload = self._request_json("GET", f"/admin/users/api/{self.project_id}/getUsers")
        if not isinstance(payload, dict):
            raise BizonError("bizon_http_error", "Unexpected users payload")
        return payload

    def get_users_slice(self, access: str = "webs") -> Any:
        return self._request_json("GET", f"/admin/users/api/{self.project_id}/getUsersSlice", query={"access": access})

    def get_filelist(self, *, type_filter: str = "", folder: str = "", location: str = "") -> dict[str, Any]:
        query: dict[str, Any] = {}
        if type_filter:
            query["type"] = type_filter
        if folder:
            query["folder"] = folder
        if location:
            query["location"] = location
        payload = self._request_json("GET", f"/admin/service/{self.project_id}/getfilelist", query=query)
        if not isinstance(payload, dict):
            raise BizonError("bizon_http_error", "Unexpected filelist payload")
        return payload

    def raw_call(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        kind: str = "raw",
    ) -> Any:
        safe_path = self._validate_path(path, kind, method=method)
        return self._request_json(method, safe_path, query=query, body=body, empty_ok=method.upper() != "GET")

    def download_file(self, direct_url: str, destination_name: str) -> dict[str, Any]:
        response = self._session.get(direct_url, timeout=120, stream=True)
        if not response.ok:
            response = requests.get(direct_url, timeout=120, stream=True)
        if not response.ok:
            raise BizonError("bizon_http_error", f"Download failed with HTTP {response.status_code}", details={"url": direct_url})
        destination = self.download_dir / _sanitize_filename(destination_name)
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)
        return {
            "path": str(destination),
            "bytes": destination.stat().st_size,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }


class BizonMCPServices:
    def __init__(self, *, role: str | None = None, client_profile: str | None = None, env: dict[str, str] | None = None):
        self.env = dict(os.environ if env is None else env)
        context = resolve_mcp_context(env=self.env, role=role, client_profile=client_profile)
        self.client_profile = context["client_profile"]
        self.role = context["role"]
        self.profile_roles = context["profile_roles"]
        self.client = BizonClient(self.env)
        self._archive_index: list[dict[str, Any]] | None = None

    def _ensure_allowed(self, tool_name: str) -> None:
        if tool_name not in allowed_tool_names_for_role(self.role):
            raise BizonError("endpoint_not_allowed", f"{tool_name} is not allowed for role {self.role}")

    def _normalize_room(self, item: dict[str, Any]) -> dict[str, Any]:
        room_name = str(item.get("name", "")).strip()
        title = str(item.get("title", "")).strip()
        slug = room_name.split(":", 1)[1] if ":" in room_name else room_name
        normalized = _normalize_text(f"{room_name} {title}")
        type_guess = "webinar"
        if "course" in normalized:
            type_guess = "course"
        elif "master class" in normalized or "мастер класс" in normalized:
            type_guess = "masterclass"
        return {
            "_id": str(item.get("_id", "")).strip(),
            "name": room_name,
            "slug": slug,
            "title": title,
            "type_guess": type_guess,
            "searchable_text": normalized,
        }

    def _normalize_staff_member(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "username": str(item.get("username", "")).strip(),
            "email": str(item.get("email", "")).strip(),
            "name": str(item.get("nameInChat", "")).strip(),
            "role": str(item.get("role", "")).strip(),
            "local": bool(item.get("local")),
            "owner": bool(item.get("owner")),
            "last_access": _parse_datetime(item.get("last_access")),
        }

    def _normalize_disk_file(self, item: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        cdn = str(payload.get("cdn", "")).rstrip("/")
        project_path = str(payload.get("url", "")).replace("/userfiles/", "/", 1)
        common_path = str(payload.get("commonPath", "")).replace("/userfiles/", "/", 1)
        relative_path = common_path if item.get("c") else project_path
        if relative_path and not relative_path.endswith("/"):
            relative_path += "/"
        direct_url = requests.utils.requote_uri(f"{cdn}{relative_path}{item.get('name', '')}")
        created = _parse_datetime(item.get("created"))
        name = str(item.get("name", "")).strip()
        return {
            "name": name,
            "content_type": str(item.get("content_type", "")).strip(),
            "bytes": int(item.get("bytes") or 0),
            "created": created,
            "storage": "common" if item.get("c") else "project",
            "relative_path": relative_path,
            "direct_url": direct_url,
            "searchable_text": _normalize_text(name),
        }

    def _archive_entries(self) -> list[dict[str, Any]]:
        if self._archive_index is not None:
            return self._archive_index
        entries: list[dict[str, Any]] = []
        root = self.client.archive_root
        if root.exists():
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                suffix = path.suffix.lower()
                if suffix not in {".json", ".mp4"}:
                    continue
                entries.append(
                    {
                        "path": str(path),
                        "name": path.name,
                        "kind": "room_recs" if path.name.startswith("room_recs_") and suffix == ".json" else suffix.lstrip("."),
                        "searchable_text": _normalize_text(path.name),
                    }
                )
        self._archive_index = entries
        return entries

    def _resolve_archive_room_rec_path(self, filename: str) -> Path:
        raw_filename = str(filename or "").strip()
        if not raw_filename:
            raise BizonError("archive_not_found", "Archive room record filename is empty")
        root = self.client.archive_root
        candidate = Path(raw_filename)
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = _resolve_path_within_root(root, candidate)
        if resolved.suffix.lower() != ".json" or not resolved.name.startswith("room_recs_"):
            raise BizonError(
                "endpoint_not_allowed",
                "Only room_recs JSON files from archive root are allowed",
                details={"path": str(resolved)},
            )
        return resolved

    def _find_archive_matches(self, query: str, *, limit: int = 20, kinds: set[str] | None = None) -> list[dict[str, Any]]:
        tokens = _tokenize(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in self._archive_entries():
            if kinds and entry["kind"] not in kinds:
                continue
            score = _score_tokens(tokens, entry["name"], entry["searchable_text"])
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda item: (-item[0], item[1]["name"]))
        results = []
        for score, entry in scored[:limit]:
            results.append(
                {
                    "source": "archive_yadisk",
                    "kind": entry["kind"],
                    "path": entry["path"],
                    "name": entry["name"],
                    "confidence": round(min(score / max(len(tokens), 1), 1.0), 3),
                }
            )
        return results

    def _best_room_match(self, identifier: str) -> dict[str, Any] | None:
        rooms = self.tool_list_rooms(limit=500)["data"]["rooms"]
        if not identifier:
            return None
        for room in rooms:
            if identifier in {room["_id"], room["name"], room["slug"]}:
                return room
        matches = self.tool_find_rooms(query=identifier, limit=1)["data"]["matches"]
        return matches[0] if matches else None

    def tool_bizon_auth_health(self) -> dict[str, Any]:
        health = self.client.auth_health()
        return _json_response(source="bizon", project_id=self.client.project_id, data=health)

    def tool_get_project_info(self) -> dict[str, Any]:
        payload = self.client.get_project_info()
        settings = self.client.get_project_settings()
        webinars = payload.get("webinars", {}) if isinstance(payload.get("webinars"), dict) else {}
        disk = payload.get("disk", {}) if isinstance(payload.get("disk"), dict) else {}
        data = {
            "project_id": self.client.project_id,
            "title": str(settings.get("title") or payload.get("title", "")).strip(),
            "slug": str(settings.get("slug") or payload.get("slug", "")).strip(),
            "max_visitors": webinars.get("maxVisitors"),
            "rooms_count": webinars.get("rooms_cnt"),
            "pages_count": webinars.get("pages_cnt"),
            "live_count": webinars.get("live_cnt"),
            "disk_used_bytes": disk.get("disk_used"),
            "disk_total_used_bytes": disk.get("usedspace"),
            "disk_max_bytes": disk.get("maxsize"),
            "staff_count": len((payload.get("users", {}) or {}).get("staff", [])),
        }
        return _json_response(source="bizon", project_id=self.client.project_id, data=data)

    def tool_get_project_settings(self) -> dict[str, Any]:
        payload = _redact_secrets(self.client.get_project_settings())
        return _json_response(source="bizon", project_id=self.client.project_id, data=payload)

    def tool_list_rooms(self, *, limit: int = 200) -> dict[str, Any]:
        payload = self.client.get_rooms()
        rooms = [self._normalize_room(item) for item in payload.get("list", [])]
        limited = rooms[: _clamp_limit(limit, default=200, maximum=1000)]
        return _json_response(
            source="bizon",
            project_id=self.client.project_id,
            data={"count": len(rooms), "returned_count": len(limited), "rooms": limited},
        )

    def tool_find_rooms(self, *, query: str, limit: int = 10) -> dict[str, Any]:
        tokens = _tokenize(query)
        rooms = self.tool_list_rooms(limit=1000)["data"]["rooms"]
        scored: list[tuple[float, dict[str, Any]]] = []
        for room in rooms:
            score = _score_tokens(tokens, room["name"], room["slug"], room["title"])
            if score > 0:
                match = dict(room)
                match["confidence"] = round(min(score / max(len(tokens), 1), 1.0), 3)
                scored.append((score, match))
        scored.sort(key=lambda item: (-item[0], item[1]["name"]))
        matches = [item[1] for item in scored[: _clamp_limit(limit, default=10, maximum=100)]]
        return _json_response(source="bizon", project_id=self.client.project_id, data={"query": query, "matches": matches})

    def tool_get_room(self, *, identifier: str) -> dict[str, Any]:
        room = self._best_room_match(identifier)
        if not room:
            raise BizonError("recording_not_found", "Room was not found", details={"identifier": identifier})
        return _json_response(source="bizon", project_id=self.client.project_id, data=room)

    def tool_list_staff(self, *, access: str = "webs", limit: int = 200) -> dict[str, Any]:
        payload = self.client.get_users()
        slice_payload = self.client.get_users_slice(access=access)
        raw_users = []
        if isinstance(slice_payload, dict):
            if isinstance(slice_payload.get("list"), list):
                raw_users = slice_payload.get("list", [])
            elif isinstance(slice_payload.get("users"), list):
                raw_users = slice_payload.get("users", [])
        users = [self._normalize_staff_member(item) for item in raw_users]
        limited = users[: _clamp_limit(limit, default=200, maximum=500)]
        return _json_response(
            source="bizon",
            project_id=self.client.project_id,
            data={
                "count": len(users),
                "returned_count": len(limited),
                "self": payload.get("self"),
                "my_role": payload.get("my_role"),
                "slice_access": access,
                "users": limited,
            },
        )

    def tool_list_disk_files(
        self,
        *,
        type_filter: str = "",
        folder: str = "",
        location: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        payload = self.client.get_filelist(type_filter=type_filter, folder=folder, location=location)
        files = [self._normalize_disk_file(item, payload) for item in payload.get("list", [])]
        limited = files[: _clamp_limit(limit, default=200, maximum=1000)]
        data = {
            "count": len(files),
            "returned_count": len(limited),
            "type_filter": type_filter or "",
            "folder": folder or "",
            "location": location or "",
            "files": limited,
            "disk_used_bytes": payload.get("usedspace"),
            "disk_max_bytes": payload.get("maxsize"),
        }
        return _json_response(source="bizon", project_id=self.client.project_id, data=data)

    def _find_disk_file(self, *, filename: str = "", query: str = "", type_filter: str = "") -> dict[str, Any] | None:
        payload = self.client.get_filelist(type_filter=type_filter)
        files = [self._normalize_disk_file(item, payload) for item in payload.get("list", [])]
        if filename:
            for item in files:
                if item["name"] == filename:
                    return item
        if not query:
            return None
        tokens = _tokenize(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in files:
            score = _score_tokens(tokens, item["name"])
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda value: (-value[0], value[1]["name"]))
        return scored[0][1] if scored else None

    def tool_download_disk_file(self, *, filename: str = "", query: str = "", type_filter: str = "") -> dict[str, Any]:
        item = self._find_disk_file(filename=filename, query=query, type_filter=type_filter)
        if not item:
            raise BizonError("recording_not_found", "Disk file was not found", details={"filename": filename, "query": query})
        downloaded = self.client.download_file(item["direct_url"], item["name"])
        data = {**item, **downloaded}
        return _json_response(source="bizon", project_id=self.client.project_id, data=data)

    def tool_find_recording(self, *, query: str, limit: int = 10) -> dict[str, Any]:
        tokens = _tokenize(query)
        warnings: list[str] = []
        room_matches = self.tool_find_rooms(query=query, limit=5)["data"]["matches"]
        search_terms = [query] + [match["slug"] for match in room_matches] + [match["name"] for match in room_matches]
        bizon_files = self.tool_list_disk_files(type_filter="video", limit=1000)["data"]["files"]
        bizon_scored: list[tuple[float, dict[str, Any]]] = []
        for item in bizon_files:
            score = max(_score_tokens(tokens, item["name"]), *[_score_tokens(_tokenize(term), item["name"]) for term in search_terms if term])
            if score > 0:
                bizon_scored.append(
                    (
                        score,
                        {
                            "source": "bizon",
                            "room_name": room_matches[0]["name"] if room_matches else "",
                            "candidate": item,
                            "confidence": round(min(score / max(len(tokens), 1), 1.0), 3),
                        },
                    )
                )
        bizon_scored.sort(key=lambda value: (-value[0], value[1]["candidate"]["name"]))
        archive_matches = self._find_archive_matches(query, limit=limit, kinds={"mp4", "room_recs"})
        matches = [item[1] for item in bizon_scored[:limit]]
        if archive_matches:
            warnings.append("archive_yadisk_checked")
            matches.extend(archive_matches[: max(0, limit - len(matches))])
        if not matches:
            raise BizonError("recording_not_found", "Recording was not found", details={"query": query})
        source = "bizon" if any(match.get("source") == "bizon" for match in matches) else "archive_yadisk"
        if source == "archive_yadisk":
            warnings.append("bizon_live_recording_not_found")
        return _json_response(
            source=source,
            project_id=self.client.project_id,
            warnings=warnings,
            data={"query": query, "room_matches": room_matches, "matches": matches[:limit]},
        )

    def tool_get_archive_room_rec(self, *, room: str = "", filename: str = "") -> dict[str, Any]:
        chosen: dict[str, Any] | None = None
        if filename:
            path = self._resolve_archive_room_rec_path(filename)
            chosen = {"source": "archive_yadisk", "path": str(path), "name": path.name}
        if chosen is None and room:
            matches = self._find_archive_matches(room, limit=1, kinds={"room_recs"})
            chosen = matches[0] if matches else None
        if chosen is None:
            raise BizonError("archive_not_found", "Archive room record was not found", details={"room": room, "filename": filename})
        record_path = Path(chosen["path"])
        payload = json.loads(record_path.read_text(encoding="utf-8", errors="replace"))
        data = payload.get("data", []) if isinstance(payload, dict) else []
        timeshifts = [int(item.get("timeshift") or 0) for item in data if isinstance(item, dict)]
        posts = [item for item in data if isinstance(item, dict) and item.get("action") == "post"]
        users = sorted({str(item.get("username", "")).strip() for item in posts if str(item.get("username", "")).strip()})
        summary = {
            "file": str(record_path),
            "room": payload.get("room", ""),
            "app": payload.get("app", ""),
            "event_count": len(data),
            "post_count": len(posts),
            "admin_posts": sum(1 for item in posts if item.get("role") == "admin"),
            "guest_posts": sum(1 for item in posts if item.get("role") == "guest"),
            "unique_users": len(users),
            "timeshift_range_sec": {
                "min": min(timeshifts) if timeshifts else 0,
                "max": max(timeshifts) if timeshifts else 0,
            },
            "sample_messages": [
                {
                    "timeshift": int(item.get("timeshift") or 0),
                    "username": str(item.get("username", "")).strip(),
                    "role": str(item.get("role", "")).strip(),
                    "message": str(item.get("message", "")).strip(),
                }
                for item in posts[:10]
            ],
        }
        return _json_response(source="archive_yadisk", project_id=self.client.project_id, warnings=["archive_source"], data=summary)

    def tool_search_archive_recordings(self, *, query: str, limit: int = 20) -> dict[str, Any]:
        matches = self._find_archive_matches(query, limit=_clamp_limit(limit, default=20, maximum=200), kinds={"mp4", "room_recs"})
        if not matches:
            raise BizonError("archive_not_found", "Archive recording was not found", details={"query": query})
        return _json_response(source="archive_yadisk", project_id=self.client.project_id, data={"query": query, "matches": matches})

    def tool_refresh_session(self) -> dict[str, Any]:
        data = self.client.login(force=True)
        return _json_response(source="bizon", project_id=self.client.project_id, data=data)

    def tool_raw_get(self, *, path: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        data = _redact_secrets(self.client.raw_call("GET", path, query=query or {}, kind="raw"))
        return _json_response(source="bizon", project_id=self.client.project_id, data=data)

    def tool_raw_post(self, *, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = _redact_secrets(self.client.raw_call("POST", path, body=body or {}, kind="raw"))
        return _json_response(source="bizon", project_id=self.client.project_id, data=data)

    def tool_room_admin_call(
        self,
        *,
        method: str = "GET",
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = _redact_secrets(self.client.raw_call(method, path, query=query or {}, body=body or {}, kind="room"))
        return _json_response(source="bizon", project_id=self.client.project_id, data=data)

    def tool_disk_admin_call(
        self,
        *,
        method: str = "GET",
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = _redact_secrets(self.client.raw_call(method, path, query=query or {}, body=body or {}, kind="disk"))
        return _json_response(source="bizon", project_id=self.client.project_id, data=data)

    def execute(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        self._ensure_allowed(tool_name)
        dispatch = {
            "bizon_auth_health": self.tool_bizon_auth_health,
            "bizon_get_project_info": self.tool_get_project_info,
            "bizon_get_project_settings": self.tool_get_project_settings,
            "bizon_list_rooms": self.tool_list_rooms,
            "bizon_find_rooms": self.tool_find_rooms,
            "bizon_get_room": self.tool_get_room,
            "bizon_list_staff": self.tool_list_staff,
            "bizon_list_disk_files": self.tool_list_disk_files,
            "bizon_download_disk_file": self.tool_download_disk_file,
            "bizon_find_recording": self.tool_find_recording,
            "bizon_get_archive_room_rec": self.tool_get_archive_room_rec,
            "bizon_search_archive_recordings": self.tool_search_archive_recordings,
            "bizon_refresh_session": self.tool_refresh_session,
            "bizon_raw_get": self.tool_raw_get,
            "bizon_raw_post": self.tool_raw_post,
            "bizon_room_admin_call": self.tool_room_admin_call,
            "bizon_disk_admin_call": self.tool_disk_admin_call,
        }
        try:
            return dispatch[tool_name](**kwargs)
        except BizonError:
            raise
        except Exception as exc:
            raise BizonError("bizon_http_error", str(exc)) from exc


def build_server(*, role: str | None = None, client_profile: str | None = None, env: dict[str, str] | None = None) -> FastMCP:
    source_env = os.environ if env is None else env
    context = resolve_mcp_context(env=source_env, role=role, client_profile=client_profile)
    services = BizonMCPServices(role=context["role"], client_profile=context["client_profile"], env=source_env)
    server = FastMCP(
        name="bizon365",
        instructions=(
            "Bizon365 MCP exposes structured access to project, rooms, disk files and archive fallbacks. "
            "Use typed tools first; admin raw tools are allowlisted and block unsafe endpoints."
        ),
    )
    allowed = set(allowed_tool_names_for_role(services.role))

    if "bizon_auth_health" in allowed:
        @server.tool(name="bizon_auth_health", description="Check Bizon365 auth/session health.", annotations=READ_ONLY, structured_output=True)
        def bizon_auth_health() -> dict[str, Any]:
            return services.execute("bizon_auth_health")

    if "bizon_get_project_info" in allowed:
        @server.tool(name="bizon_get_project_info", description="Get normalized Bizon365 project info.", annotations=READ_ONLY, structured_output=True)
        def bizon_get_project_info() -> dict[str, Any]:
            return services.execute("bizon_get_project_info")

    if "bizon_get_project_settings" in allowed:
        @server.tool(name="bizon_get_project_settings", description="Get redacted Bizon365 project settings.", annotations=READ_ONLY, structured_output=True)
        def bizon_get_project_settings() -> dict[str, Any]:
            return services.execute("bizon_get_project_settings")

    if "bizon_list_rooms" in allowed:
        @server.tool(name="bizon_list_rooms", description="List Bizon365 rooms.", annotations=READ_ONLY, structured_output=True)
        def bizon_list_rooms(limit: int = 200) -> dict[str, Any]:
            return services.execute("bizon_list_rooms", limit=limit)

    if "bizon_find_rooms" in allowed:
        @server.tool(name="bizon_find_rooms", description="Find Bizon365 rooms by name/title/slug.", annotations=READ_ONLY, structured_output=True)
        def bizon_find_rooms(query: str, limit: int = 10) -> dict[str, Any]:
            return services.execute("bizon_find_rooms", query=query, limit=limit)

    if "bizon_get_room" in allowed:
        @server.tool(name="bizon_get_room", description="Get one Bizon365 room by id/name/slug.", annotations=READ_ONLY, structured_output=True)
        def bizon_get_room(identifier: str) -> dict[str, Any]:
            return services.execute("bizon_get_room", identifier=identifier)

    if "bizon_list_staff" in allowed:
        @server.tool(name="bizon_list_staff", description="List Bizon365 project staff.", annotations=READ_ONLY, structured_output=True)
        def bizon_list_staff(access: str = "webs", limit: int = 200) -> dict[str, Any]:
            return services.execute("bizon_list_staff", access=access, limit=limit)

    if "bizon_list_disk_files" in allowed:
        @server.tool(name="bizon_list_disk_files", description="List Bizon365 disk files.", annotations=READ_ONLY, structured_output=True)
        def bizon_list_disk_files(type_filter: str = "", folder: str = "", location: str = "", limit: int = 200) -> dict[str, Any]:
            return services.execute(
                "bizon_list_disk_files",
                type_filter=type_filter,
                folder=folder,
                location=location,
                limit=limit,
            )

    if "bizon_download_disk_file" in allowed:
        @server.tool(name="bizon_download_disk_file", description="Download one Bizon365 disk file into local runtime tmp.", annotations=MUTATING, structured_output=True)
        def bizon_download_disk_file(filename: str = "", query: str = "", type_filter: str = "") -> dict[str, Any]:
            return services.execute("bizon_download_disk_file", filename=filename, query=query, type_filter=type_filter)

    if "bizon_find_recording" in allowed:
        @server.tool(name="bizon_find_recording", description="Find webinar recordings in Bizon365 disk and Yandex archive.", annotations=READ_ONLY, structured_output=True)
        def bizon_find_recording(query: str, limit: int = 10) -> dict[str, Any]:
            return services.execute("bizon_find_recording", query=query, limit=limit)

    if "bizon_get_archive_room_rec" in allowed:
        @server.tool(name="bizon_get_archive_room_rec", description="Read one room_recs archive JSON from Yandex Disk.", annotations=READ_ONLY, structured_output=True)
        def bizon_get_archive_room_rec(room: str = "", filename: str = "") -> dict[str, Any]:
            return services.execute("bizon_get_archive_room_rec", room=room, filename=filename)

    if "bizon_search_archive_recordings" in allowed:
        @server.tool(name="bizon_search_archive_recordings", description="Search archived recordings and room_recs files on Yandex Disk.", annotations=READ_ONLY, structured_output=True)
        def bizon_search_archive_recordings(query: str, limit: int = 20) -> dict[str, Any]:
            return services.execute("bizon_search_archive_recordings", query=query, limit=limit)

    if "bizon_refresh_session" in allowed:
        @server.tool(name="bizon_refresh_session", description="Force Bizon365 re-login.", annotations=MUTATING, structured_output=True)
        def bizon_refresh_session() -> dict[str, Any]:
            return services.execute("bizon_refresh_session")

    if "bizon_raw_get" in allowed:
        @server.tool(name="bizon_raw_get", description="Admin-only allowlisted Bizon365 GET.", annotations=READ_ONLY, structured_output=True)
        def bizon_raw_get(path: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
            return services.execute("bizon_raw_get", path=path, query=query or {})

    if "bizon_raw_post" in allowed:
        @server.tool(name="bizon_raw_post", description="Admin-only allowlisted Bizon365 POST.", annotations=MUTATING, structured_output=True)
        def bizon_raw_post(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
            return services.execute("bizon_raw_post", path=path, body=body or {})

    if "bizon_room_admin_call" in allowed:
        @server.tool(name="bizon_room_admin_call", description="Admin-only allowlisted room API call.", annotations=MUTATING, structured_output=True)
        def bizon_room_admin_call(
            method: str = "GET",
            path: str = "",
            query: dict[str, Any] | None = None,
            body: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            return services.execute(
                "bizon_room_admin_call",
                method=method,
                path=path,
                query=query or {},
                body=body or {},
            )

    if "bizon_disk_admin_call" in allowed:
        @server.tool(name="bizon_disk_admin_call", description="Admin-only allowlisted disk API call.", annotations=MUTATING, structured_output=True)
        def bizon_disk_admin_call(
            method: str = "GET",
            path: str = "",
            query: dict[str, Any] | None = None,
            body: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            return services.execute(
                "bizon_disk_admin_call",
                method=method,
                path=path,
                query=query or {},
                body=body or {},
            )

    return server


def main() -> int:
    load_env_file(Path(os.environ.get("BIZON365_ENV_FILE", str(DEFAULT_ENV_PATH))))
    build_server().run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
