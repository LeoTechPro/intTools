#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

try:  # pragma: no cover
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover
    psycopg2 = None

try:  # pragma: no cover
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_STATE_FILE = Path("D:/int/tools/.runtime/punctb/legacy-assess-sync/state.json")
ENTITY_ORDER = ("specialists", "clients", "results")
TARGET_HOST_ALLOWLIST = {"vds.intdata.pro"}
SOURCE_SQL_ENV = {
    "specialists": "LEGACY_ASSESS_SYNC_SQL_SPECIALISTS",
    "clients": "LEGACY_ASSESS_SYNC_SQL_CLIENTS",
    "results": "LEGACY_ASSESS_SYNC_SQL_RESULTS",
}
PERSON_ID_NAMESPACE = uuid.UUID("0a6819d8-7644-4052-b1ff-27d25ab379aa")
RESULT_ID_NAMESPACE = uuid.UUID("dcb16551-5923-4d9a-a1d1-7af96f42dfdf")
TIMESTAMP_FIELDS = ("updated_at", "created_at", "result_at", "computed_at")
DEFAULT_OVERLAP_MINUTES = 5
DEFAULT_SOURCE_SQL = {
    "specialists": """
        SELECT
          id::text AS legacy_id,
          email,
          first_name,
          family_name,
          patronymic,
          phone,
          slug,
          status,
          metadata,
          COALESCE(updated_at, created_at) AS updated_at,
          created_at
        FROM public.specialists
        WHERE (%(since)s IS NULL OR COALESCE(updated_at, created_at) > %(since)s)
        ORDER BY COALESCE(updated_at, created_at), id
    """.strip(),
    "clients": """
        SELECT
          id::text AS legacy_id,
          email,
          first_name,
          family_name,
          patronymic,
          phone,
          birthdate,
          slug,
          status,
          metadata,
          COALESCE(updated_at, created_at) AS updated_at,
          created_at
        FROM public.clients
        WHERE (%(since)s IS NULL OR COALESCE(updated_at, created_at) > %(since)s)
        ORDER BY COALESCE(updated_at, created_at), id
    """.strip(),
    "results": """
        SELECT
          id::text AS legacy_id,
          client_id::text AS legacy_client_id,
          specialist_id::text AS legacy_specialist_id,
          diagnostic_id,
          payload,
          open_answer,
          status,
          source,
          note,
          schema_version,
          method_version,
          computed_at,
          created_at,
          COALESCE(updated_at, created_at, date) AS updated_at,
          COALESCE(date, result_at, created_at) AS result_at
        FROM public.diag_results
        WHERE (%(since)s IS NULL OR COALESCE(updated_at, created_at, date) > %(since)s)
        ORDER BY COALESCE(updated_at, created_at, date), id
    """.strip(),
}
PgConnection = Any


if load_dotenv is not None:  # pragma: no branch
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)


@dataclass
class StreamState:
    last_success_at: Optional[str] = None


@dataclass
class RunState:
    version: int = 1
    streams: Dict[str, StreamState] = field(
        default_factory=lambda: {entity: StreamState() for entity in ENTITY_ORDER}
    )
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamStats:
    source_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    next_watermark: Optional[str] = None
    errors: list[str] = field(default_factory=list)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manual punkt_b -> intdata assessment sync adapter (read-only source)."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Read and diff only. No target commit.")
    mode.add_argument("--apply", action="store_true", help="Apply changes to intdata.")
    parser.add_argument("--source-dsn", required=True, help="Read-only PostgreSQL DSN for legacy punkt_b.")
    parser.add_argument("--target-dsn", required=True, help="Writable PostgreSQL DSN for intdata.")
    parser.add_argument(
        "--entity",
        default="all",
        choices=("specialists", "clients", "results", "all"),
        help="Entity stream to run.",
    )
    parser.add_argument("--from", dest="from_ts", help="Override watermark start time (ISO-8601).")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE), help="Local JSON state file path.")
    parser.add_argument("--report-json", help="Optional JSON report output path.")
    parser.add_argument(
        "--overlap-minutes",
        type=int,
        default=DEFAULT_OVERLAP_MINUTES,
        help="Overlap window applied to stored watermarks.",
    )
    parser.add_argument("--source-sql-specialists-file", help="Optional SQL file overriding specialists query.")
    parser.add_argument("--source-sql-clients-file", help="Optional SQL file overriding clients query.")
    parser.add_argument("--source-sql-results-file", help="Optional SQL file overriding results query.")
    return parser.parse_args(argv)


def utcnow() -> datetime:
    return datetime.now(UTC)


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso_datetime(raw: Optional[str]) -> Optional[datetime]:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return isoformat_utc(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=json_default)


def normalize_phone(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    digits = re.sub(r"\D+", "", value)
    return digits or None


def normalize_slug(value: Optional[str], fallback_prefix: str, legacy_id: str) -> str:
    if value:
        slug = value.strip().lower()
        slug = re.sub(r"[^a-z0-9-]+", "-", slug)
        slug = re.sub(r"-{2,}", "-", slug).strip("-")
        if slug:
            return slug
    return f"{fallback_prefix}-{legacy_id}".lower()


def ensure_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return copy.deepcopy(dict(value))
    return {}


def normalize_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str):
        return parse_iso_datetime(value)
    raise TypeError(f"Unsupported timestamp value: {value!r}")


def dsn_checksum(dsn: str) -> str:
    parsed = require_psycopg2().extensions.parse_dsn(dsn)
    alias = "|".join(str(parsed.get(key, "")) for key in ("host", "port", "dbname", "user"))
    return hashlib.sha256(alias.encode("utf-8")).hexdigest()


def dsn_host(dsn: str) -> str:
    parsed = require_psycopg2().extensions.parse_dsn(dsn)
    return str(parsed.get("host", "")).strip().lower()


def require_psycopg2():
    if psycopg2 is None:
        raise SystemExit("psycopg2 is required. Install psycopg2-binary for runtime execution.")
    return psycopg2


def assert_target_host_allowed(dsn: str) -> None:
    host = dsn_host(dsn)
    if host not in TARGET_HOST_ALLOWLIST:
        raise SystemExit(
            f"Refusing target host '{host or '<empty>'}'. Allowed hosts: {', '.join(sorted(TARGET_HOST_ALLOWLIST))}"
        )


def assert_source_query_read_only(sql: str, entity: str) -> None:
    stripped = sql.lstrip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        raise ValueError(f"{entity} source SQL must start with SELECT/WITH.")
    forbidden = (" insert ", " update ", " delete ", " truncate ", " alter ", " create ", " drop ", " lock ")
    padded = f" {stripped} "
    for token in forbidden:
        if token in padded:
            raise ValueError(f"{entity} source SQL contains forbidden token: {token.strip().upper()}")


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> RunState:
        if not self.path.exists():
            return RunState()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        streams = {
            entity: StreamState(**raw.get("streams", {}).get(entity, {}))
            for entity in ENTITY_ORDER
        }
        return RunState(
            version=int(raw.get("version", 1)),
            streams=streams,
            meta=dict(raw.get("meta", {})),
        )

    def save(self, state: RunState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": state.version,
            "streams": {name: asdict(stream) for name, stream in state.streams.items()},
            "meta": state.meta,
        }
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp_path.replace(self.path)


def compute_since(*, stored: Optional[datetime], override: Optional[datetime], overlap_minutes: int) -> Optional[datetime]:
    if override is not None:
        return override
    if stored is None:
        return None
    return stored - timedelta(minutes=overlap_minutes)


def stable_uuid(namespace: uuid.UUID, *parts: Any) -> uuid.UUID:
    normalized = "|".join("" if part is None else str(part) for part in parts)
    return uuid.uuid5(namespace, normalized)


def normalize_result_payload(payload: Any) -> Dict[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        return {"value": payload}
    return copy.deepcopy(dict(payload))


def result_identity_token(source_row: Mapping[str, Any]) -> str:
    legacy_id = source_row.get("legacy_id")
    if legacy_id:
        return f"legacy-id:{legacy_id}"
    result_at = normalize_timestamp(source_row.get("result_at"))
    if result_at is None:
        raise ValueError("results row requires result_at or legacy_id")
    return ":".join(
        (
            str(source_row.get("legacy_client_id", "")),
            str(source_row.get("diagnostic_id", "")),
            isoformat_utc(result_at),
        )
    )


def build_result_fingerprint(source_row: Mapping[str, Any]) -> str:
    result_at = normalize_timestamp(source_row.get("result_at"))
    if result_at is None:
        raise ValueError("results row requires result_at for fingerprint")
    seed = {
        "legacy_client_id": source_row.get("legacy_client_id"),
        "diagnostic_id": source_row.get("diagnostic_id"),
        "result_at": isoformat_utc(result_at),
        "payload": normalize_result_payload(source_row.get("payload")),
        "open_answer": source_row.get("open_answer") or "",
    }
    return hashlib.sha256(canonical_json(seed).encode("utf-8")).hexdigest()


def merge_person_metadata(
    existing_metadata: Any,
    *,
    legacy_id: str,
    synced_at: datetime,
    source_updated_at: Optional[datetime],
) -> Dict[str, Any]:
    metadata = ensure_mapping(existing_metadata)
    legacy_ns = ensure_mapping(metadata.get("legacy_punktb"))
    legacy_ns.update({"legacy_id": str(legacy_id), "synced_at": isoformat_utc(synced_at)})
    if source_updated_at is not None:
        legacy_ns["source_updated_at"] = isoformat_utc(source_updated_at)
    metadata["legacy_punktb"] = legacy_ns
    return metadata


def embed_result_import_metadata(
    payload: Any,
    *,
    legacy_id: Optional[str],
    legacy_client_id: Any,
    legacy_specialist_id: Any,
    fingerprint: str,
    synced_at: datetime,
    identity_token: str,
) -> Dict[str, Any]:
    result_payload = normalize_result_payload(payload)
    import_ns = ensure_mapping(result_payload.get("_import"))
    legacy_ns = ensure_mapping(import_ns.get("legacy_punktb"))
    legacy_ns.update(
        {
            "identity_token": identity_token,
            "fingerprint": fingerprint,
            "legacy_client_id": None if legacy_client_id is None else str(legacy_client_id),
            "legacy_specialist_id": None if legacy_specialist_id is None else str(legacy_specialist_id),
            "synced_at": isoformat_utc(synced_at),
        }
    )
    if legacy_id is not None:
        legacy_ns["legacy_id"] = str(legacy_id)
    import_ns["legacy_punktb"] = legacy_ns
    result_payload["_import"] = import_ns
    return result_payload


def comparable_person_metadata(value: Any) -> Dict[str, Any]:
    metadata = ensure_mapping(value)
    legacy_ns = ensure_mapping(metadata.get("legacy_punktb"))
    legacy_ns.pop("synced_at", None)
    metadata["legacy_punktb"] = legacy_ns
    return metadata


def comparable_result_payload(value: Any) -> Dict[str, Any]:
    payload = normalize_result_payload(value)
    import_ns = ensure_mapping(payload.get("_import"))
    legacy_ns = ensure_mapping(import_ns.get("legacy_punktb"))
    legacy_ns.pop("synced_at", None)
    import_ns["legacy_punktb"] = legacy_ns
    payload["_import"] = import_ns
    return payload


def row_changed(existing: Optional[Mapping[str, Any]], desired: Mapping[str, Any], *, keys: Iterable[str]) -> bool:
    if existing is None:
        return True
    for key in keys:
        if existing.get(key) != desired.get(key):
            return True
    return False


def fetch_one_dict(cur: Any, sql: str, params: tuple[Any, ...]) -> Optional[Dict[str, Any]]:
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def ensure_source_session_read_only(conn: PgConnection) -> None:
    conn.set_session(readonly=True, autocommit=False)
    with conn.cursor() as cur:
        cur.execute("SHOW transaction_read_only")
        value = cur.fetchone()[0]
    if str(value).lower() not in {"on", "true"}:
        raise RuntimeError("Source session is not read-only.")


def resolve_source_sql(args: argparse.Namespace, entity: str) -> str:
    file_attr = f"source_sql_{entity}_file"
    file_path = getattr(args, file_attr, None)
    if file_path:
        sql = Path(file_path).read_text(encoding="utf-8")
    else:
        sql = os.getenv(SOURCE_SQL_ENV[entity], DEFAULT_SOURCE_SQL[entity])
    assert_source_query_read_only(sql, entity)
    return sql


def fetch_source_rows(conn: PgConnection, *, sql: str, since: Optional[datetime]) -> list[Dict[str, Any]]:
    pg = require_psycopg2()
    with conn.cursor(cursor_factory=pg.extras.RealDictCursor) as cur:
        cur.execute(sql, {"since": since})
        return [dict(row) for row in cur.fetchall()]


class SyncEngine:
    def __init__(self, *, target_conn: PgConnection, synced_at: datetime) -> None:
        self.target_conn = target_conn
        self.synced_at = synced_at
        self.mapping_cache: dict[tuple[str, str], uuid.UUID] = {}

    def _lookup_person_by_legacy(
        self,
        cur: Any,
        table: str,
        legacy_id: str,
    ) -> Optional[Dict[str, Any]]:
        return fetch_one_dict(
            cur,
            f"""
            SELECT user_id, email, phone, slug, status, metadata, birthdate
            FROM assess.{table}
            WHERE metadata -> 'legacy_punktb' ->> 'legacy_id' = %s
            """,
            (legacy_id,),
        )

    def _lookup_person_by_email(
        self,
        cur: Any,
        table: str,
        email: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not email:
            return None
        return fetch_one_dict(
            cur,
            f"""
            SELECT user_id, email, phone, slug, status, metadata, birthdate
            FROM assess.{table}
            WHERE lower(email) = lower(%s)
            """,
            (email,),
        )

    def _lookup_person_by_phone(
        self,
        cur: Any,
        table: str,
        phone: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        normalized_phone = normalize_phone(phone)
        if not normalized_phone:
            return None
        return fetch_one_dict(
            cur,
            f"""
            SELECT user_id, email, phone, slug, status, metadata, birthdate
            FROM assess.{table}
            WHERE regexp_replace(COALESCE(phone, ''), '\\D+', '', 'g') = %s
            """,
            (normalized_phone,),
        )

    def _resolve_target_user_id(
        self,
        cur: Any,
        *,
        table: str,
        legacy_id: str,
        email: Optional[str],
        phone: Optional[str],
    ) -> tuple[uuid.UUID, Optional[Dict[str, Any]]]:
        cache_key = (table, str(legacy_id))
        cached = self.mapping_cache.get(cache_key)
        if cached is not None:
            existing = fetch_one_dict(
                cur,
                f"SELECT user_id, email, phone, slug, status, metadata, birthdate FROM assess.{table} WHERE user_id = %s",
                (str(cached),),
            )
            return cached, existing
        existing = self._lookup_person_by_legacy(cur, table, legacy_id)
        if existing is None:
            existing = self._lookup_person_by_email(cur, table, email)
        if existing is None:
            existing = self._lookup_person_by_phone(cur, table, phone)
        if existing is not None:
            user_id = uuid.UUID(str(existing["user_id"]))
        else:
            user_id = stable_uuid(PERSON_ID_NAMESPACE, table, legacy_id)
        self.mapping_cache[cache_key] = user_id
        return user_id, existing

    def _ensure_iam_user(
        self,
        cur: Any,
        *,
        user_id: uuid.UUID,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        cur.execute(
            """
            INSERT INTO iam.users (user_id, created_at, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (str(user_id), created_at, updated_at),
        )

    def sync_specialist(self, cur: Any, row: Mapping[str, Any], stats: StreamStats) -> None:
        legacy_id = str(row["legacy_id"])
        source_updated_at = normalize_timestamp(row.get("updated_at"))
        created_at = normalize_timestamp(row.get("created_at")) or source_updated_at or self.synced_at
        updated_at = source_updated_at or created_at
        user_id, existing = self._resolve_target_user_id(
            cur,
            table="specialists",
            legacy_id=legacy_id,
            email=row.get("email"),
            phone=row.get("phone"),
        )
        self._ensure_iam_user(cur, user_id=user_id, created_at=created_at, updated_at=updated_at)
        desired = {
            "email": row.get("email"),
            "first_name": row.get("first_name"),
            "family_name": row.get("family_name"),
            "patronymic": row.get("patronymic"),
            "phone": row.get("phone"),
            "slug": normalize_slug(row.get("slug"), "legacy-specialist", legacy_id),
            "status": row.get("status") or "in_work",
            "metadata": merge_person_metadata(
                existing.get("metadata") if existing else row.get("metadata"),
                legacy_id=legacy_id,
                synced_at=self.synced_at,
                source_updated_at=source_updated_at,
            ),
        }
        compare_existing = dict(existing or {})
        compare_existing["metadata"] = comparable_person_metadata(compare_existing.get("metadata"))
        compare_desired = dict(desired)
        compare_desired["metadata"] = comparable_person_metadata(compare_desired.get("metadata"))
        changed = row_changed(compare_existing, compare_desired, keys=desired.keys())
        if existing is None:
            stats.created += 1
        elif changed:
            stats.updated += 1
        else:
            stats.skipped += 1
            return
        cur.execute(
            """
            INSERT INTO assess.specialists (
              user_id, email, first_name, family_name, patronymic, phone,
              slug, status, metadata, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET email = EXCLUDED.email,
                first_name = EXCLUDED.first_name,
                family_name = EXCLUDED.family_name,
                patronymic = EXCLUDED.patronymic,
                phone = EXCLUDED.phone,
                slug = EXCLUDED.slug,
                status = EXCLUDED.status,
                metadata = EXCLUDED.metadata,
                updated_at = EXCLUDED.updated_at
            """,
            (
                str(user_id),
                desired["email"],
                desired["first_name"],
                desired["family_name"],
                desired["patronymic"],
                desired["phone"],
                desired["slug"],
                desired["status"],
                canonical_json(desired["metadata"]),
                created_at,
                updated_at,
            ),
        )

    def sync_client(self, cur: Any, row: Mapping[str, Any], stats: StreamStats) -> None:
        legacy_id = str(row["legacy_id"])
        source_updated_at = normalize_timestamp(row.get("updated_at"))
        created_at = normalize_timestamp(row.get("created_at")) or source_updated_at or self.synced_at
        updated_at = source_updated_at or created_at
        user_id, existing = self._resolve_target_user_id(
            cur,
            table="clients",
            legacy_id=legacy_id,
            email=row.get("email"),
            phone=row.get("phone"),
        )
        self._ensure_iam_user(cur, user_id=user_id, created_at=created_at, updated_at=updated_at)
        desired = {
            "email": row.get("email"),
            "first_name": row.get("first_name"),
            "family_name": row.get("family_name"),
            "patronymic": row.get("patronymic"),
            "phone": row.get("phone"),
            "birthdate": row.get("birthdate"),
            "slug": normalize_slug(row.get("slug"), "legacy-client", legacy_id),
            "status": row.get("status") or "new",
            "metadata": merge_person_metadata(
                existing.get("metadata") if existing else row.get("metadata"),
                legacy_id=legacy_id,
                synced_at=self.synced_at,
                source_updated_at=source_updated_at,
            ),
        }
        compare_existing = dict(existing or {})
        compare_existing["metadata"] = comparable_person_metadata(compare_existing.get("metadata"))
        compare_desired = dict(desired)
        compare_desired["metadata"] = comparable_person_metadata(compare_desired.get("metadata"))
        changed = row_changed(compare_existing, compare_desired, keys=desired.keys())
        if existing is None:
            stats.created += 1
        elif changed:
            stats.updated += 1
        else:
            stats.skipped += 1
            return
        cur.execute(
            """
            INSERT INTO assess.clients (
              user_id, email, first_name, family_name, patronymic, phone,
              birthdate, slug, status, metadata, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET email = EXCLUDED.email,
                first_name = EXCLUDED.first_name,
                family_name = EXCLUDED.family_name,
                patronymic = EXCLUDED.patronymic,
                phone = EXCLUDED.phone,
                birthdate = EXCLUDED.birthdate,
                slug = EXCLUDED.slug,
                status = EXCLUDED.status,
                metadata = EXCLUDED.metadata,
                updated_at = EXCLUDED.updated_at
            """,
            (
                str(user_id),
                desired["email"],
                desired["first_name"],
                desired["family_name"],
                desired["patronymic"],
                desired["phone"],
                desired["birthdate"],
                desired["slug"],
                desired["status"],
                canonical_json(desired["metadata"]),
                created_at,
                updated_at,
            ),
        )

    def _resolve_person_id_by_legacy(
        self,
        cur: Any,
        *,
        table: str,
        legacy_id: Optional[Any],
    ) -> Optional[uuid.UUID]:
        if legacy_id is None:
            return None
        cached = self.mapping_cache.get((table, str(legacy_id)))
        if cached is not None:
            return cached
        existing = self._lookup_person_by_legacy(cur, table, str(legacy_id))
        if existing is None:
            return None
        user_id = uuid.UUID(str(existing["user_id"]))
        self.mapping_cache[(table, str(legacy_id))] = user_id
        return user_id

    def sync_result(self, cur: Any, row: Mapping[str, Any], stats: StreamStats) -> None:
        client_id = self._resolve_person_id_by_legacy(cur, table="clients", legacy_id=row.get("legacy_client_id"))
        if client_id is None:
            raise RuntimeError(
                f"results row legacy_client_id={row.get('legacy_client_id')} has no mapped target client"
            )
        specialist_id = self._resolve_person_id_by_legacy(
            cur, table="specialists", legacy_id=row.get("legacy_specialist_id")
        )
        identity_token = result_identity_token(row)
        result_id = stable_uuid(RESULT_ID_NAMESPACE, identity_token)
        fingerprint = build_result_fingerprint(row)
        payload = embed_result_import_metadata(
            row.get("payload"),
            legacy_id=str(row["legacy_id"]) if row.get("legacy_id") is not None else None,
            legacy_client_id=row.get("legacy_client_id"),
            legacy_specialist_id=row.get("legacy_specialist_id"),
            fingerprint=fingerprint,
            synced_at=self.synced_at,
            identity_token=identity_token,
        )
        source_updated_at = normalize_timestamp(row.get("updated_at"))
        created_at = normalize_timestamp(row.get("created_at")) or normalize_timestamp(row.get("result_at")) or self.synced_at
        updated_at = source_updated_at or created_at
        existing = fetch_one_dict(
            cur,
            """
            SELECT id, client_id, specialist_id, diagnostic_id, payload, open_answer, status,
                   source, note, schema_version, method_version, computed_at, result_at
            FROM assess.diag_results
            WHERE id = %s
            """,
            (str(result_id),),
        )
        desired = {
            "client_id": str(client_id),
            "specialist_id": None if specialist_id is None else str(specialist_id),
            "diagnostic_id": row.get("diagnostic_id"),
            "payload": payload,
            "open_answer": row.get("open_answer"),
            "status": row.get("status") or "new_result",
            "source": row.get("source") or "legacy_punktb.sync",
            "note": row.get("note"),
            "schema_version": row.get("schema_version"),
            "method_version": row.get("method_version"),
            "computed_at": normalize_timestamp(row.get("computed_at")),
            "result_at": normalize_timestamp(row.get("result_at")),
        }
        compare_existing = dict(existing or {})
        compare_existing["payload"] = comparable_result_payload(compare_existing.get("payload"))
        compare_desired = dict(desired)
        compare_desired["payload"] = comparable_result_payload(compare_desired.get("payload"))
        changed = row_changed(compare_existing, compare_desired, keys=desired.keys())
        if existing is None:
            stats.created += 1
        elif changed:
            stats.updated += 1
        else:
            stats.skipped += 1
            return
        cur.execute(
            """
            INSERT INTO assess.diag_results (
              id, client_id, specialist_id, diagnostic_id, payload, open_answer,
              status, source, note, schema_version, method_version, computed_at,
              result_at, created_at, updated_at, assigned_at
            )
            VALUES (
              %s, %s, %s, %s, %s::jsonb, %s,
              %s::assess.user_diag_status, %s, %s, %s, %s, %s,
              %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE
            SET client_id = EXCLUDED.client_id,
                specialist_id = EXCLUDED.specialist_id,
                diagnostic_id = EXCLUDED.diagnostic_id,
                payload = EXCLUDED.payload,
                open_answer = EXCLUDED.open_answer,
                status = EXCLUDED.status,
                source = EXCLUDED.source,
                note = EXCLUDED.note,
                schema_version = EXCLUDED.schema_version,
                method_version = EXCLUDED.method_version,
                computed_at = EXCLUDED.computed_at,
                result_at = EXCLUDED.result_at,
                updated_at = EXCLUDED.updated_at
            """,
            (
                str(result_id),
                desired["client_id"],
                desired["specialist_id"],
                desired["diagnostic_id"],
                canonical_json(desired["payload"]),
                desired["open_answer"],
                desired["status"],
                desired["source"],
                desired["note"],
                desired["schema_version"],
                desired["method_version"],
                desired["computed_at"],
                desired["result_at"],
                created_at,
                updated_at,
                created_at,
            ),
        )


def run_stream(
    *,
    entity: str,
    source_conn: PgConnection,
    target_conn: PgConnection,
    sql: str,
    since: Optional[datetime],
    synced_at: datetime,
) -> StreamStats:
    rows = fetch_source_rows(source_conn, sql=sql, since=since)
    stats = StreamStats(source_rows=len(rows))
    latest_source_updated: Optional[datetime] = None
    engine = SyncEngine(target_conn=target_conn, synced_at=synced_at)
    pg = require_psycopg2()
    with target_conn.cursor(cursor_factory=pg.extras.RealDictCursor) as cur:
        for row in rows:
            row_updated_at = None
            for field in TIMESTAMP_FIELDS:
                row_updated_at = normalize_timestamp(row.get(field))
                if row_updated_at is not None:
                    break
            if row_updated_at is not None and (
                latest_source_updated is None or row_updated_at > latest_source_updated
            ):
                latest_source_updated = row_updated_at
            if entity == "specialists":
                engine.sync_specialist(cur, row, stats)
            elif entity == "clients":
                engine.sync_client(cur, row, stats)
            elif entity == "results":
                engine.sync_result(cur, row, stats)
            else:  # pragma: no cover
                raise ValueError(f"Unknown entity: {entity}")
    stats.next_watermark = isoformat_utc(latest_source_updated or synced_at)
    return stats


def print_stream_summary(entity: str, stats: StreamStats) -> None:
    print(
        f"[{entity}] source_rows={stats.source_rows} created={stats.created} "
        f"updated={stats.updated} skipped={stats.skipped} next_watermark={stats.next_watermark}"
    )
    for error in stats.errors:
        print(f"[{entity}] error: {error}", file=sys.stderr)


def build_report(
    *,
    args: argparse.Namespace,
    run_state: RunState,
    results: Dict[str, StreamStats],
    synced_at: datetime,
) -> Dict[str, Any]:
    return {
        "started_at": isoformat_utc(synced_at),
        "mode": "dry-run" if args.dry_run else "apply",
        "entity": args.entity,
        "state_file": str(Path(args.state_file)),
        "streams": {name: asdict(stats) for name, stats in results.items()},
        "state": {
            "streams": {name: asdict(stream) for name, stream in run_state.streams.items()},
            "meta": run_state.meta,
        },
    }


def write_report(path: Optional[str], report: Dict[str, Any]) -> None:
    if not path:
        return
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    assert_target_host_allowed(args.target_dsn)
    entities = list(ENTITY_ORDER) if args.entity == "all" else [args.entity]
    state_store = StateStore(Path(args.state_file))
    run_state = state_store.load()
    synced_at = utcnow()
    run_state.meta.update(
        {
            "last_started_at": isoformat_utc(synced_at),
            "source_alias_checksum": dsn_checksum(args.source_dsn),
            "target_alias_checksum": dsn_checksum(args.target_dsn),
        }
    )
    from_override = parse_iso_datetime(args.from_ts)
    results: Dict[str, StreamStats] = {}
    pg = require_psycopg2()
    source_conn = pg.connect(args.source_dsn)
    target_conn = pg.connect(args.target_dsn)
    source_conn.autocommit = False
    target_conn.autocommit = False
    try:
        ensure_source_session_read_only(source_conn)
        for entity in entities:
            sql = resolve_source_sql(args, entity)
            stored = parse_iso_datetime(run_state.streams[entity].last_success_at)
            since = compute_since(stored=stored, override=from_override, overlap_minutes=args.overlap_minutes)
            try:
                stats = run_stream(
                    entity=entity,
                    source_conn=source_conn,
                    target_conn=target_conn,
                    sql=sql,
                    since=since,
                    synced_at=synced_at,
                )
                if args.dry_run:
                    target_conn.rollback()
                else:
                    target_conn.commit()
                    run_state.streams[entity].last_success_at = stats.next_watermark
                    run_state.meta["last_success_at"] = stats.next_watermark
                    state_store.save(run_state)
                results[entity] = stats
            except Exception as exc:
                target_conn.rollback()
                stats = results.setdefault(entity, StreamStats())
                stats.errors.append(str(exc))
                print_stream_summary(entity, stats)
                raise
            print_stream_summary(entity, stats)
        run_state.meta["last_finished_at"] = isoformat_utc(utcnow())
        report = build_report(args=args, run_state=run_state, results=results, synced_at=synced_at)
        write_report(args.report_json, report)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        try:
            source_conn.rollback()
        finally:
            source_conn.close()
            target_conn.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
