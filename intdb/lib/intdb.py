#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from typing import Sequence
from urllib.parse import urlsplit, urlunsplit


TOOL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_REPO_ENV = "INTDB_DATA_REPO"
REMOTE_DATA_REPO_HINT = "agents@vds.intdata.pro:/int/data"
PROFILE_PATTERN = re.compile(r"^INTDB_PROFILE__([A-Z0-9_]+)__([A-Z0-9_]+)$")
SAFE_TABLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")
WINDOWS_PG_ROOT = Path(r"C:\Program Files\PostgreSQL")
WINDOWS_GIT_BASH_PATHS = (
    Path(r"C:\Program Files\Git\bin\bash.exe"),
    Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
)
OWNER_CONTROL_ACK = "I_ACKNOWLEDGE_LOCAL_ONLY"
LOCAL_TEST_DIRNAME = "local-supabase"
SUPABASE_DB_URL_PATTERN = re.compile(r"DB URL:\s*(?P<value>\S+)")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class IntDbError(RuntimeError):
    pass


@dataclass(frozen=True)
class Profile:
    name: str
    key: str
    values: dict[str, str]

    @property
    def host(self) -> str:
        return self.values["PGHOST"]

    @property
    def port(self) -> str:
        return self.values.get("PGPORT", "5432")

    @property
    def database(self) -> str:
        return self.values["PGDATABASE"]

    @property
    def user(self) -> str:
        return self.values["PGUSER"]

    @property
    def password(self) -> str:
        return self.values["PGPASSWORD"]

    @property
    def sslmode(self) -> str:
        return self.values.get("PGSSLMODE", "require")

    @property
    def write_class(self) -> str:
        return self.values.get("WRITE_CLASS", "nonprod").strip().lower() or "nonprod"


def _utc_stamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _canonical_profile_key(value: str) -> str:
    canonical = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().upper()).strip("_")
    if not canonical:
        raise IntDbError("Имя профиля не задано.")
    return canonical


def _parse_env_text(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue
        if value and value[0] in {"'", '"'} and value[-1:] == value[0]:
            value = value[1:-1]
        else:
            value = re.sub(r"\s+#.*$", "", value).rstrip()
        result[key] = value
    return result


def _load_env_file(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    return _parse_env_text(env_path.read_text(encoding="utf-8"))


def _load_tool_env(env_path: Path) -> dict[str, str]:
    merged = _load_env_file(env_path)
    merged.update(os.environ)
    return merged


def _load_profiles(env_path: Path) -> dict[str, Profile]:
    merged = _load_tool_env(env_path)
    grouped: dict[str, dict[str, str]] = {}
    for key, value in merged.items():
        match = PROFILE_PATTERN.match(key)
        if not match:
            continue
        profile_key, field_name = match.groups()
        grouped.setdefault(profile_key, {})[field_name] = value

    profiles: dict[str, Profile] = {}
    required = {"PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"}
    for profile_key, values in grouped.items():
        missing = sorted(required - values.keys())
        if missing:
            raise IntDbError(
                f"Профиль {profile_key} неполный: отсутствуют {', '.join(missing)}."
            )
        display_name = profile_key.lower().replace("_", "-")
        profiles[profile_key] = Profile(name=display_name, key=profile_key, values=values)
    return profiles


def _get_profile(env_path: Path, requested_name: str) -> Profile:
    profiles = _load_profiles(env_path)
    profile_key = _canonical_profile_key(requested_name)
    try:
        return profiles[profile_key]
    except KeyError as exc:
        known = ", ".join(sorted(profile.name for profile in profiles.values())) or "нет профилей"
        raise IntDbError(f"Профиль {requested_name!r} не найден. Доступно: {known}.") from exc


def _ensure_write_allowed(profile: Profile, approve_target: str | None, force_prod_write: bool) -> None:
    approved_key = _canonical_profile_key(approve_target or "")
    if approved_key != profile.key:
        raise IntDbError(
            f"Mutating-операция для {profile.name} требует --approve-target {profile.name}."
        )
    if profile.write_class == "prod" and not force_prod_write:
        raise IntDbError(
            f"Профиль {profile.name} помечен как prod; добавьте --force-prod-write."
        )


def _ensure_repo(path: Path) -> Path:
    repo = path.resolve()
    if not repo.exists():
        raise IntDbError(f"Путь не найден: {repo}")
    return repo


def _resolve_data_repo(requested_repo: str | None) -> Path:
    if requested_repo:
        return _ensure_repo(Path(requested_repo))

    env_path = TOOL_ROOT / ".env"
    env_repo = _load_tool_env(env_path).get(DEFAULT_DATA_REPO_ENV, "").strip()
    if env_repo:
        return _ensure_repo(Path(env_repo))

    sibling_repo = TOOL_ROOT.parent.parent / "data"
    if os.name == "nt":
        raise IntDbError(
            "Не удалось автоматически найти repo `/int/data`: локальный Windows checkout `D:\\int\\data` "
            f"не является dev backend default. Для работы с dev backend intdata используйте remote checkout "
            f"`{REMOTE_DATA_REPO_HINT}`, например через `ssh agents@vds.intdata.pro` и `cd /int/data`, "
            "либо передайте явный локальный --repo/INTDB_DATA_REPO для осознанного disposable flow."
        )
    if sibling_repo.exists():
        return sibling_repo.resolve()

    raise IntDbError(
        "Не удалось автоматически найти repo `/int/data`; укажите --repo, задайте INTDB_DATA_REPO "
        f"или выполните dev backend workflow на `{REMOTE_DATA_REPO_HINT}`."
    )


def _tool_tmp_dir(purpose: str) -> Path:
    path = TOOL_ROOT / ".tmp" / purpose / _utc_stamp()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _process_env(profile: Profile, *, read_only: bool = False, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {
        "PGPASSWORD": profile.password,
        "PGSSLMODE": profile.sslmode,
    }
    if read_only:
        env["PGOPTIONS"] = "-c default_transaction_read_only=on"
    if extra:
        env.update(extra)
    return env


def _prepend_path_entry(path_value: str, entry: Path) -> str:
    resolved_entry = str(entry.resolve())
    if not path_value:
        return resolved_entry
    parts = [part for part in path_value.split(os.pathsep) if part]
    normalized_entry = os.path.normcase(os.path.normpath(resolved_entry))
    filtered = [
        part
        for part in parts
        if os.path.normcase(os.path.normpath(part)) != normalized_entry
    ]
    return os.pathsep.join([resolved_entry, *filtered])


def _candidate_pg_paths(command_name: str) -> list[Path]:
    if os.name != "nt" or not WINDOWS_PG_ROOT.exists():
        return []
    candidates = list(WINDOWS_PG_ROOT.glob(f"*/bin/{command_name}.exe"))
    return sorted(candidates, reverse=True)


def _resolve_command(command_name: str, *, candidates: Sequence[Path] | None = None) -> str | None:
    resolved = shutil.which(command_name)
    if resolved:
        return resolved
    for candidate in candidates or ():
        if candidate.exists():
            return str(candidate)
    return None


def _require_pg_command(command_name: str) -> str:
    resolved = _resolve_command(command_name, candidates=_candidate_pg_paths(command_name))
    if not resolved:
        raise IntDbError(
            f"{command_name} не найден. Установите PostgreSQL client и убедитесь, что его bin-каталог доступен из PATH."
        )
    return resolved


def _require_pg_tools() -> dict[str, str]:
    return {name: _require_pg_command(name) for name in ("psql", "pg_dump", "pg_restore")}


def _require_bash() -> str:
    if os.name == "nt":
        for candidate in WINDOWS_GIT_BASH_PATHS:
            if candidate.exists():
                return str(candidate)
    resolved = shutil.which("bash")
    if not resolved:
        raise IntDbError(
            "bash не найден. Для incremental migration установите Git for Windows и откройте новый shell."
        )
    return resolved


def _require_docker() -> str:
    resolved = shutil.which("docker")
    if not resolved:
        raise IntDbError("docker не найден. Для local-test runner нужен установленный Docker Desktop/Engine.")
    return resolved


def _resolve_supabase_command() -> list[str]:
    resolved = shutil.which("supabase")
    if resolved:
        return [resolved]
    npx = shutil.which("npx")
    if npx:
        return [npx, "supabase"]
    raise IntDbError("Supabase CLI не найден. Установите `supabase` или используйте `npx supabase`.")


def _run_process(
    argv: Sequence[str],
    *,
    env_map: dict[str, str] | None = None,
    cwd: Path | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    child_env = os.environ.copy()
    for key, value in (env_map or {}).items():
        child_env[key] = value
    try:
        return subprocess.run(
            list(argv),
            env=child_env,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=capture_output,
            check=False,
        )
    except OSError as exc:
        raise IntDbError(f"Внешняя команда не запустилась: {exc}") from exc


def _run_checked(
    argv: Sequence[str],
    *,
    profile: Profile | None = None,
    read_only: bool = False,
    extra_env: dict[str, str] | None = None,
    capture_output: bool = False,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env_map: dict[str, str] = {}
    if profile is not None:
        env_map.update(_process_env(profile, read_only=read_only))
    if extra_env:
        env_map.update(extra_env)
    result = _run_process(
        argv,
        env_map=env_map,
        cwd=cwd,
        capture_output=capture_output,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() if result.stderr else ""
        if not detail and result.stdout:
            detail = result.stdout.strip()
        raise IntDbError(f"Внешняя команда завершилась с кодом {result.returncode}: {detail}")
    return result


def _run_checked_capture(
    argv: Sequence[str],
    *,
    env_map: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return _run_checked(argv, extra_env=env_map, cwd=cwd, capture_output=True)


def _psql_base_args(profile: Profile) -> list[str]:
    return [
        _require_pg_command("psql"),
        "--host",
        profile.host,
        "--port",
        profile.port,
        "--username",
        profile.user,
        "--dbname",
        profile.database,
        "--no-password",
        "-v",
        "ON_ERROR_STOP=1",
    ]


def _pg_dump_base_args(profile: Profile) -> list[str]:
    return [
        _require_pg_command("pg_dump"),
        "--host",
        profile.host,
        "--port",
        profile.port,
        "--username",
        profile.user,
        "--dbname",
        profile.database,
        "--no-password",
        "--verbose",
    ]


def _pg_restore_base_args(profile: Profile) -> list[str]:
    return [
        _require_pg_command("pg_restore"),
        "--host",
        profile.host,
        "--port",
        profile.port,
        "--username",
        profile.user,
        "--dbname",
        profile.database,
        "--no-password",
        "--verbose",
    ]


def _test_tcp(profile: Profile, timeout_sec: float = 3.0) -> None:
    try:
        with socket.create_connection((profile.host, int(profile.port)), timeout=timeout_sec):
            return
    except OSError as exc:
        raise IntDbError(f"TCP-подключение к {profile.host}:{profile.port} не удалось: {exc}") from exc


def _query_remote_versions(profile: Profile) -> list[str]:
    exists_query = "SELECT COALESCE(to_regclass('public.schema_migrations')::text, '')"
    exists_result = _run_checked(
        _psql_base_args(profile) + ["-Atqc", exists_query],
        profile=profile,
        read_only=True,
        capture_output=True,
    )
    if not exists_result.stdout.strip():
        return []

    query = (
        "SELECT version::text "
        "FROM public.schema_migrations "
        "WHERE version::text ~ '^[0-9]{14}$' "
        "ORDER BY version::text"
    )
    result = _run_checked(
        _psql_base_args(profile) + ["-Atqc", query],
        profile=profile,
        read_only=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _read_manifest_versions(repo_root: Path) -> list[tuple[str, str]]:
    manifest_path = repo_root / "init" / "migration_manifest.lock"
    if not manifest_path.exists():
        raise IntDbError(f"Не найден manifest: {manifest_path}")
    versions: list[tuple[str, str]] = []
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 2:
            continue
        versions.append((parts[0], parts[1]))
    return versions


def _default_dump_output(profile: Profile, format_name: str) -> Path:
    suffix = ".sql" if format_name == "plain" else ".dump"
    out_dir = _tool_tmp_dir("dumps")
    return out_dir / f"{profile.name}{suffix}"


def _detect_restore_format(path: Path, selected: str) -> str:
    if selected != "auto":
        return selected
    return "plain" if path.suffix.lower() in {".sql", ".psql"} else "custom"


def _write_text(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _sql_literal_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _psql_meta_command_line(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip())


def _truncate_lines(path: Path, limit: int | None) -> None:
    if limit is None:
        return
    if limit < 1:
        raise IntDbError("--limit must be >= 1.")
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > limit:
        path.write_text("\n".join(lines[:limit]) + "\n", encoding="utf-8")


def _cmd_doctor(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    profile = _get_profile(env_path, args.profile)
    tools = _require_pg_tools()
    _test_tcp(profile)
    result = _run_checked(
        _psql_base_args(profile)
        + [
            "-Atqc",
            "SELECT current_database() || '|' || current_user || '|' || current_setting('server_version')",
        ],
        profile=profile,
        read_only=True,
        capture_output=True,
    )
    db_name, db_user, server_version = (result.stdout.strip().split("|", 2) + ["", "", ""])[:3]
    print(f"profile: {profile.name}")
    print(
        "cli: ok "
        f"(psql={Path(tools['psql']).name}, pg_dump={Path(tools['pg_dump']).name}, pg_restore={Path(tools['pg_restore']).name})"
    )
    print(f"tcp: ok ({profile.host}:{profile.port})")
    print(f"sql: ok (db={db_name}, user={db_user}, server={server_version})")
    return 0


def _cmd_sql(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    profile = _get_profile(env_path, args.profile)
    if args.write:
        _ensure_write_allowed(profile, args.approve_target, args.force_prod_write)
    _run_checked(
        _psql_base_args(profile) + ["-c", args.sql],
        profile=profile,
        read_only=not args.write,
    )
    return 0


def _cmd_file(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    profile = _get_profile(env_path, args.profile)
    if args.write:
        _ensure_write_allowed(profile, args.approve_target, args.force_prod_write)
    sql_path = Path(args.path).resolve()
    if not sql_path.exists():
        raise IntDbError(f"SQL-файл не найден: {sql_path}")
    _run_checked(
        _psql_base_args(profile) + ["-f", str(sql_path)],
        profile=profile,
        read_only=not args.write,
    )
    return 0


def _run_dump(
    profile: Profile,
    output_path: Path,
    *,
    format_name: str,
    schema_only: bool,
    data_only: bool,
    tables: Sequence[str],
) -> Path:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    argv = _pg_dump_base_args(profile) + [
        f"--format={'p' if format_name == 'plain' else 'c'}",
        "--file",
        str(output_path),
    ]
    if schema_only:
        argv.append("--schema-only")
    if data_only:
        argv.append("--data-only")
    for table in tables:
        argv.extend(["--table", table])
    _run_checked(argv, profile=profile, read_only=True)
    return output_path


def _cmd_dump(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    profile = _get_profile(env_path, args.source)
    output_path = Path(args.output).resolve() if args.output else _default_dump_output(profile, args.format)
    final_path = _run_dump(
        profile,
        output_path,
        format_name=args.format,
        schema_only=args.schema_only,
        data_only=args.data_only,
        tables=args.table or [],
    )
    print(final_path)
    return 0


def _run_restore(
    profile: Profile,
    input_path: Path,
    *,
    restore_format: str,
    clean: bool,
    schema_only: bool,
    data_only: bool,
) -> None:
    input_path = input_path.resolve()
    if not input_path.exists():
        raise IntDbError(f"Файл восстановления не найден: {input_path}")
    if restore_format == "plain":
        if clean or schema_only or data_only:
            raise IntDbError(
                "Для plain SQL restore поддерживается только полное выполнение файла без флагов clean/schema/data."
            )
        _run_checked(
            _psql_base_args(profile) + ["-f", str(input_path)],
            profile=profile,
        )
        return

    argv = _pg_restore_base_args(profile)
    if clean:
        argv.append("--clean")
    if schema_only:
        argv.append("--schema-only")
    if data_only:
        argv.append("--data-only")
    argv.append(str(input_path))
    _run_checked(argv, profile=profile)


def _cmd_restore(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    profile = _get_profile(env_path, args.target)
    _ensure_write_allowed(profile, args.approve_target, args.force_prod_write)
    input_path = Path(args.input).resolve()
    restore_format = _detect_restore_format(input_path, args.format)
    _run_restore(
        profile,
        input_path,
        restore_format=restore_format,
        clean=args.clean,
        schema_only=args.schema_only,
        data_only=args.data_only,
    )
    return 0


def _cmd_clone(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    source_profile = _get_profile(env_path, args.source)
    target_profile = _get_profile(env_path, args.target)
    _ensure_write_allowed(target_profile, args.approve_target, args.force_prod_write)
    clone_dir = _tool_tmp_dir("clone")
    dump_path = clone_dir / f"{source_profile.name}-to-{target_profile.name}.dump"
    _run_dump(
        source_profile,
        dump_path,
        format_name="custom",
        schema_only=args.schema_only,
        data_only=args.data_only,
        tables=args.table or [],
    )
    _run_restore(
        target_profile,
        dump_path,
        restore_format="custom",
        clean=args.clean,
        schema_only=args.schema_only,
        data_only=args.data_only,
    )
    print(dump_path)
    return 0


def _cmd_copy(args: argparse.Namespace) -> int:
    if not SAFE_TABLE_PATTERN.match(args.target_table):
        raise IntDbError("target-table должен быть в формате schema.table или table без произвольного SQL.")

    env_path = TOOL_ROOT / ".env"
    source_profile = _get_profile(env_path, args.source)
    target_profile = _get_profile(env_path, args.target)
    _ensure_write_allowed(target_profile, args.approve_target, args.force_prod_write)

    temp_dir = _tool_tmp_dir("copy")
    csv_path = temp_dir / "copy.csv"
    export_sql = temp_dir / "export.sql"
    import_sql = temp_dir / "import.sql"

    _write_text(
        export_sql,
        f"\\copy ({args.query}) TO '{_sql_literal_path(csv_path)}' WITH (FORMAT csv, HEADER true)\n",
    )

    import_lines = []
    if args.truncate:
        import_lines.append(f"TRUNCATE TABLE {args.target_table};")
    import_lines.append(
        f"\\copy {args.target_table} FROM '{_sql_literal_path(csv_path)}' WITH (FORMAT csv, HEADER true)"
    )
    _write_text(import_sql, "\n".join(import_lines) + "\n")

    _run_checked(
        _psql_base_args(source_profile) + ["-f", str(export_sql)],
        profile=source_profile,
        read_only=True,
    )
    _run_checked(
        _psql_base_args(target_profile) + ["-f", str(import_sql)],
        profile=target_profile,
    )
    print(csv_path)
    return 0


PUNKTB_LEGACY_CLIENTS_EXPORT_SQL = """
\\copy (
  SELECT jsonb_build_object(
    'legacy_id', id,
    'manager_id', manager_id,
    'name', name,
    'phone', phone,
    'email', lower(btrim(email)),
    'raw_email', email,
    'new', new,
    'in_archive', in_archive,
    'date', date,
    'is_phone_adult', is_phone_adult,
    'contact_permission', contact_permission,
    'results', COALESCE(results, '[]'::jsonb)
  )::text
  FROM public.clients
  WHERE NULLIF(btrim(email), '') IS NOT NULL
  {limit_clause}
  ORDER BY lower(btrim(email)), id
) TO '{clients_path}' WITH (FORMAT text)
""".strip()


PUNKTB_LEGACY_MANAGERS_EXPORT_SQL = """
\\copy (
  SELECT jsonb_build_object(
    'legacy_id', id,
    'login', lower(btrim(login)),
    'raw_login', login,
    'name', name,
    'surname', surname,
    'phone', phone,
    'active', active,
    'is_admin', is_admin,
    'available_diagnostics', to_jsonb(available_diagnostics),
    'full_access', full_access,
    'new_conclusion_access', new_conclusion_access
  )::text
  FROM public.managers
  WHERE NULLIF(btrim(login), '') IS NOT NULL
  ORDER BY lower(btrim(login)), id
) TO '{managers_path}' WITH (FORMAT text)
""".strip()


def _build_punktb_legacy_target_sql(
    *,
    clients_path: Path,
    managers_path: Path,
    dry_run: bool,
) -> str:
    finish = "ROLLBACK;" if dry_run else "COMMIT;"
    return f"""
BEGIN;

CREATE OR REPLACE FUNCTION pg_temp._intdb_uuid(seed text)
RETURNS uuid
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT (
    substr(md5(seed), 1, 8) || '-' ||
    substr(md5(seed), 9, 4) || '-' ||
    substr(md5(seed), 13, 4) || '-' ||
    substr(md5(seed), 17, 4) || '-' ||
    substr(md5(seed), 21, 12)
  )::uuid;
$$;

CREATE TEMP TABLE _intdb_punktb_clients_raw(raw jsonb) ON COMMIT DROP;
CREATE TEMP TABLE _intdb_punktb_managers_raw(raw jsonb) ON COMMIT DROP;
\\copy _intdb_punktb_clients_raw(raw) FROM '{_sql_literal_path(clients_path)}' WITH (FORMAT text)
\\copy _intdb_punktb_managers_raw(raw) FROM '{_sql_literal_path(managers_path)}' WITH (FORMAT text)

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM assess.clients
    WHERE NULLIF(btrim(email), '') IS NOT NULL
    GROUP BY lower(btrim(email))
    HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION 'target assess.clients has duplicate normalized emails';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM assess.specialists
    WHERE NULLIF(btrim(email), '') IS NOT NULL
    GROUP BY lower(btrim(email))
    HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION 'target assess.specialists has duplicate normalized emails';
  END IF;
END
$$;

CREATE TEMP TABLE _intdb_punktb_managers ON COMMIT DROP AS
WITH ranked AS (
  SELECT
    lower(btrim(raw->>'login')) AS email_norm,
    (array_agg(raw ORDER BY (raw->>'legacy_id')::int DESC))[1] AS raw,
    jsonb_agg(raw->>'legacy_id' ORDER BY (raw->>'legacy_id')::int) AS legacy_ids
  FROM _intdb_punktb_managers_raw
  WHERE NULLIF(btrim(raw->>'login'), '') IS NOT NULL
  GROUP BY lower(btrim(raw->>'login'))
)
SELECT
  COALESCE(s.user_id, au.id, pg_temp._intdb_uuid('punktb-user-email:' || email_norm)) AS user_id,
  email_norm,
  raw,
  legacy_ids
FROM ranked r
LEFT JOIN assess.specialists s ON lower(btrim(s.email)) = r.email_norm
LEFT JOIN auth.users au ON lower(btrim(au.email)) = r.email_norm;

CREATE TEMP TABLE _intdb_punktb_clients ON COMMIT DROP AS
WITH ranked AS (
  SELECT
    lower(btrim(raw->>'email')) AS email_norm,
    (array_agg(raw ORDER BY NULLIF(raw->>'date', '')::bigint DESC NULLS LAST, (raw->>'legacy_id')::int DESC))[1] AS raw,
    jsonb_agg(raw->>'legacy_id' ORDER BY (raw->>'legacy_id')::int) AS legacy_ids
  FROM _intdb_punktb_clients_raw
  WHERE NULLIF(btrim(raw->>'email'), '') IS NOT NULL
  GROUP BY lower(btrim(raw->>'email'))
)
SELECT
  COALESCE(c.user_id, au.id, pg_temp._intdb_uuid('punktb-user-email:' || email_norm)) AS user_id,
  email_norm,
  raw,
  legacy_ids
FROM ranked r
LEFT JOIN assess.clients c ON lower(btrim(c.email)) = r.email_norm
LEFT JOIN auth.users au ON lower(btrim(au.email)) = r.email_norm;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM _intdb_punktb_managers m
    JOIN assess.specialists s
      ON s.slug = m.raw->>'legacy_id'
     AND lower(btrim(s.email)) IS DISTINCT FROM m.email_norm
  ) THEN
    RAISE EXCEPTION 'target assess.specialists has conflicting legacy numeric slugs';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM _intdb_punktb_clients c
    JOIN assess.clients existing
      ON existing.slug = c.raw->>'legacy_id'
     AND lower(btrim(existing.email)) IS DISTINCT FROM c.email_norm
  ) THEN
    RAISE EXCEPTION 'target assess.clients has conflicting legacy numeric slugs';
  END IF;
END
$$;

INSERT INTO auth.users (
  id, aud, role, email, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
  is_sso_user, is_anonymous
)
SELECT
  user_id,
  'authenticated',
  'authenticated',
  email_norm,
  now(),
  '{{"provider":"email","providers":["email"]}}'::jsonb,
  jsonb_build_object('_import', jsonb_build_object('legacy_punktb', jsonb_build_object('kind', 'specialist', 'legacy_ids', legacy_ids))),
  now(),
  now(),
  false,
  false
FROM _intdb_punktb_managers
ON CONFLICT (id) DO UPDATE
SET email = EXCLUDED.email,
    raw_user_meta_data = auth.users.raw_user_meta_data || EXCLUDED.raw_user_meta_data,
    updated_at = EXCLUDED.updated_at;

INSERT INTO auth.users (
  id, aud, role, email, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
  is_sso_user, is_anonymous
)
SELECT
  user_id,
  'authenticated',
  'authenticated',
  email_norm,
  now(),
  '{{"provider":"email","providers":["email"]}}'::jsonb,
  jsonb_build_object('_import', jsonb_build_object('legacy_punktb', jsonb_build_object('kind', 'client', 'legacy_ids', legacy_ids))),
  to_timestamp(COALESCE(NULLIF(raw->>'date', '')::numeric / 1000.0, extract(epoch from now()))),
  now(),
  false,
  false
FROM _intdb_punktb_clients
ON CONFLICT (id) DO UPDATE
SET email = EXCLUDED.email,
    raw_user_meta_data = auth.users.raw_user_meta_data || EXCLUDED.raw_user_meta_data,
    updated_at = EXCLUDED.updated_at;

INSERT INTO assess.specialists (
  user_id, email, first_name, family_name, phone, slug, status,
  configured_package_codes, created_at, updated_at
)
SELECT
  user_id,
  email_norm,
  NULLIF(raw->>'name', ''),
  NULLIF(raw->>'surname', ''),
  NULLIF(raw->>'phone', ''),
  raw->>'legacy_id',
  CASE WHEN COALESCE((raw->>'active')::boolean, false) THEN 'in_work'::assess.specialist_status ELSE 'blocked'::assess.specialist_status END,
  ARRAY[]::text[],
  now(),
  now()
FROM _intdb_punktb_managers
ON CONFLICT (user_id) DO UPDATE
SET email = EXCLUDED.email,
    first_name = EXCLUDED.first_name,
    family_name = EXCLUDED.family_name,
    phone = EXCLUDED.phone,
    slug = EXCLUDED.slug,
    status = EXCLUDED.status,
    configured_package_codes = EXCLUDED.configured_package_codes,
    updated_at = EXCLUDED.updated_at;

INSERT INTO assess.clients (
  user_id, email, first_name, phone, slug, status, specialist_id,
  is_phone_adult, contact_permission, created_at, updated_at
)
SELECT
  c.user_id,
  c.email_norm,
  NULLIF(c.raw->>'name', ''),
  NULLIF(c.raw->>'phone', ''),
  c.raw->>'legacy_id',
  CASE WHEN COALESCE((c.raw->>'in_archive')::boolean, false) THEN 'archive'::assess.client_status ELSE 'lead'::assess.client_status END,
  m.user_id,
  COALESCE((c.raw->>'is_phone_adult')::boolean, false),
  COALESCE((c.raw->>'contact_permission')::boolean, false),
  to_timestamp(COALESCE(NULLIF(c.raw->>'date', '')::numeric / 1000.0, extract(epoch from now()))),
  now()
FROM _intdb_punktb_clients c
LEFT JOIN _intdb_punktb_managers m ON (c.raw->>'manager_id') = (m.raw->>'legacy_id')
ON CONFLICT (user_id) DO UPDATE
SET email = EXCLUDED.email,
    first_name = EXCLUDED.first_name,
    phone = EXCLUDED.phone,
    slug = EXCLUDED.slug,
    status = EXCLUDED.status,
    specialist_id = EXCLUDED.specialist_id,
    is_phone_adult = EXCLUDED.is_phone_adult,
    contact_permission = EXCLUDED.contact_permission,
    updated_at = EXCLUDED.updated_at;

CREATE TEMP TABLE _intdb_punktb_results ON COMMIT DROP AS
SELECT
  pg_temp._intdb_uuid(
    'punktb-result:' || c.email_norm || ':' || (cr.raw->>'legacy_id') || ':' ||
    result_item.ordinality::text || ':' || COALESCE(result_item.item->>'diagnostic-id', '') || ':' ||
    COALESCE(result_item.item->>'date', '')
  ) AS result_id,
  c.user_id AS client_id,
  m.user_id AS specialist_id,
  (result_item.item->>'diagnostic-id')::int AS diagnostic_id,
  result_item.item AS item,
  cr.raw AS client_raw,
  result_item.ordinality AS result_index,
  to_timestamp(COALESCE(NULLIF(result_item.item->>'date', '')::numeric / 1000.0, extract(epoch from now()))) AS result_at
FROM _intdb_punktb_clients c
JOIN _intdb_punktb_clients_raw cr ON lower(btrim(cr.raw->>'email')) = c.email_norm
CROSS JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(cr.raw->'results') = 'array' THEN cr.raw->'results' ELSE '[]'::jsonb END
) WITH ORDINALITY AS result_item(item, ordinality)
LEFT JOIN _intdb_punktb_managers m ON (cr.raw->>'manager_id') = (m.raw->>'legacy_id')
WHERE (result_item.item->>'diagnostic-id') ~ '^[0-9]+$';

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM _intdb_punktb_results r
    LEFT JOIN assess.diagnostics d ON d.id = r.diagnostic_id
    WHERE d.id IS NULL
  ) THEN
    RAISE EXCEPTION 'legacy result references diagnostic id absent in target assess.diagnostics';
  END IF;
END
$$;

INSERT INTO assess.diag_results (
  id, client_id, specialist_id, diagnostic_id, payload, open_answer,
  status, source, result_at, created_at, updated_at, assigned_at
)
SELECT
  result_id,
  client_id,
  specialist_id,
  diagnostic_id,
  COALESCE(item->'data', '{{}}'::jsonb) ||
    jsonb_build_object(
      '_import',
      jsonb_build_object(
        'legacy_punktb',
        jsonb_build_object(
          'legacy_client_id', client_raw->>'legacy_id',
          'legacy_result_index', result_index,
          'diagnostic_id', diagnostic_id,
          'source_fingerprint', md5(item::text)
        )
      )
    ),
  NULLIF(item->>'openAnswer', ''),
  'new_result'::assess.user_diag_status,
  'legacy_punktb.clients.results',
  result_at,
  result_at,
  now(),
  result_at
FROM _intdb_punktb_results
ON CONFLICT (id) DO UPDATE
SET client_id = EXCLUDED.client_id,
    specialist_id = EXCLUDED.specialist_id,
    diagnostic_id = EXCLUDED.diagnostic_id,
    payload = EXCLUDED.payload,
    open_answer = EXCLUDED.open_answer,
    source = EXCLUDED.source,
    result_at = EXCLUDED.result_at,
    updated_at = EXCLUDED.updated_at;

SELECT 'source_clients|' || count(*) FROM _intdb_punktb_clients_raw;
SELECT 'merged_clients|' || count(*) FROM _intdb_punktb_clients;
SELECT 'source_managers|' || count(*) FROM _intdb_punktb_managers_raw;
SELECT 'merged_specialists|' || count(*) FROM _intdb_punktb_managers;
SELECT 'source_results|' || count(*) FROM _intdb_punktb_results;
SELECT 'mode|' || {_sql_literal('dry-run' if dry_run else 'apply')};

{finish}
""".strip() + "\n"


def _punktb_legacy_source_limit_clause(limit: int | None) -> str:
    if limit is None:
        return ""
    if limit < 1:
        raise IntDbError("--limit must be >= 1.")
    return f"AND id IN (SELECT id FROM public.clients WHERE NULLIF(btrim(email), '') IS NOT NULL ORDER BY id LIMIT {limit})"


def _cmd_project_migrate_punktb_legacy_assess(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    source_profile = _get_profile(env_path, args.source)
    target_profile = _get_profile(env_path, args.target)
    if args.apply:
        _ensure_write_allowed(target_profile, args.approve_target, args.force_prod_write)
    workdir = Path(args.workdir).resolve() if args.workdir else _tool_tmp_dir("punktb-legacy-assess")
    workdir.mkdir(parents=True, exist_ok=True)
    clients_path = workdir / "legacy_clients.jsonl"
    managers_path = workdir / "legacy_managers.jsonl"
    export_sql = workdir / "source_export.sql"
    target_sql = workdir / "target_stage.sql"
    _write_text(
        export_sql,
        "\n".join(
            [
                _psql_meta_command_line(
                    PUNKTB_LEGACY_CLIENTS_EXPORT_SQL.format(
                        clients_path=_sql_literal_path(clients_path),
                        limit_clause=_punktb_legacy_source_limit_clause(args.limit),
                    )
                ),
                _psql_meta_command_line(
                    PUNKTB_LEGACY_MANAGERS_EXPORT_SQL.format(managers_path=_sql_literal_path(managers_path))
                ),
                "",
            ]
        ),
    )
    _run_checked(
        _psql_base_args(source_profile) + ["-f", str(export_sql)],
        profile=source_profile,
        read_only=True,
    )
    _truncate_lines(clients_path, args.limit)
    _write_text(
        target_sql,
        _build_punktb_legacy_target_sql(
            clients_path=clients_path,
            managers_path=managers_path,
            dry_run=args.dry_run,
        ),
    )
    result = _run_checked(
        _psql_base_args(target_profile) + ["-f", str(target_sql)],
        profile=target_profile,
        read_only=False,
        capture_output=True,
    )
    print(result.stdout.rstrip())
    if args.report_json:
        report_path = Path(args.report_json).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "mode": "dry-run" if args.dry_run else "apply",
                    "source": source_profile.name,
                    "target": target_profile.name,
                    "workdir": str(workdir),
                    "stdout": result.stdout,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    print(f"workdir: {workdir}")
    return 0


def _cmd_migrate_status(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    profile = _get_profile(env_path, args.target)
    repo_root = _resolve_data_repo(args.repo)
    manifest_versions = _read_manifest_versions(repo_root)
    applied_versions = set(_query_remote_versions(profile))

    pending = [(version, filename) for version, filename in manifest_versions if version not in applied_versions]
    print(f"profile: {profile.name}")
    print(f"manifest_total: {len(manifest_versions)}")
    print(f"applied_total: {len(applied_versions)}")
    print(f"pending_total: {len(pending)}")
    for version, filename in pending:
        print(f"pending: {version} {filename}")
    return 0


def _cmd_migrate_data(args: argparse.Namespace) -> int:
    env_path = TOOL_ROOT / ".env"
    profile = _get_profile(env_path, args.target)
    _ensure_write_allowed(profile, args.approve_target, args.force_prod_write)
    repo_root = _resolve_data_repo(args.repo)
    env = {
        "POSTGRES_HOST": profile.host,
        "POSTGRES_PORT": profile.port,
        "POSTGRES_DB": profile.database,
        "POSTGRES_USER": profile.user,
        "POSTGRES_PASSWORD": profile.password,
        "PGSSLMODE": profile.sslmode,
    }

    if args.mode == "incremental":
        bash_path = _require_bash()
        psql_dir = Path(_require_pg_command("psql")).resolve().parent
        incremental_env = dict(env)
        incremental_env["PATH"] = _prepend_path_entry(os.environ.get("PATH", ""), psql_dir)
        _run_checked(
            [bash_path, str(repo_root / "init" / "010_supabase_migrate.sh")],
            extra_env=incremental_env,
            cwd=repo_root,
        )
        return 0

    psql_base = [
        _require_pg_command("psql"),
        "--host",
        profile.host,
        "--port",
        profile.port,
        "--username",
        profile.user,
        "--dbname",
        profile.database,
        "--no-password",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    _run_checked(
        psql_base + ["-f", str(repo_root / "init" / "schema.sql")],
        profile=profile,
        extra_env=env,
        cwd=repo_root,
    )
    if args.seed_business:
        _run_checked(
            psql_base + ["-f", str(repo_root / "init" / "seed_business.sql")],
            profile=profile,
            extra_env=env,
            cwd=repo_root,
        )
    return 0


def _assert_owner_control_token(token: str | None) -> None:
    if token != OWNER_CONTROL_ACK:
        raise IntDbError(
            f"Local disposable runner requires --confirm-owner-control {OWNER_CONTROL_ACK}."
        )


def _local_test_workspace_path(workdir: str | None) -> Path:
    if workdir:
        return Path(workdir).resolve()
    return _tool_tmp_dir(LOCAL_TEST_DIRNAME)


def _supabase_status_db_url(supabase_cmd: Sequence[str], workspace: Path) -> str:
    result = _run_checked_capture([*supabase_cmd, "status"], cwd=workspace)
    match = SUPABASE_DB_URL_PATTERN.search(result.stdout)
    if not match:
        raise IntDbError("Не удалось извлечь DB URL из `supabase status`.")
    return match.group("value")


def _db_env_from_url(db_url: str) -> dict[str, str]:
    parts = urlsplit(db_url)
    username = parts.username
    password = parts.password
    host = parts.hostname
    database = parts.path.lstrip("/")
    if not username or password is None or not host or not database:
        raise IntDbError("DB URL из local Supabase runtime неполный; не удалось подготовить env.")
    port = str(parts.port or 5432)
    driverless = urlunsplit(("postgresql", parts.netloc, parts.path, "", ""))
    return {
        "POSTGRES_HOST": host,
        "POSTGRES_PORT": port,
        "POSTGRES_DB": database,
        "POSTGRES_USER": username,
        "POSTGRES_PASSWORD": password,
        "PGPASSWORD": password,
        "LOCAL_TEST_DATABASE_URL": driverless,
        "TEST_DATABASE_URL": driverless,
    }


def _run_repo_seed(repo_root: Path, db_url: str) -> None:
    parsed = urlsplit(db_url)
    username = parsed.username
    password = parsed.password
    host = parsed.hostname
    database = parsed.path.lstrip("/")
    if not username or password is None or not host or not database:
        raise IntDbError("DB URL из local Supabase runtime неполный; не удалось подготовить env для seed.")
    port = str(parsed.port or 5432)
    env = {
        "PGPASSWORD": password,
        "POSTGRES_HOST": host,
        "POSTGRES_PORT": port,
        "POSTGRES_DB": database,
        "POSTGRES_USER": username,
        "POSTGRES_PASSWORD": password,
    }
    psql_base = [
        _require_pg_command("psql"),
        "--host",
        host,
        "--port",
        port,
        "--username",
        username,
        "--dbname",
        database,
        "--no-password",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    _run_checked(
        psql_base + ["-f", str(repo_root / "init" / "seed.sql")],
        extra_env=env,
        cwd=repo_root,
    )


def _run_local_smoke(repo_root: Path, db_url: str, smoke_files: Sequence[str]) -> None:
    if not smoke_files:
        return

    parsed = urlsplit(db_url)
    username = parsed.username
    password = parsed.password
    host = parsed.hostname
    database = parsed.path.lstrip("/")
    if not username or password is None or not host or not database:
        raise IntDbError("DB URL из local Supabase runtime неполный; smoke не могут быть запущены.")
    port = str(parsed.port or 5432)
    psql_base = [
        _require_pg_command("psql"),
        "--host",
        host,
        "--port",
        port,
        "--username",
        username,
        "--dbname",
        database,
        "--no-password",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    env = {"PGPASSWORD": password}
    for smoke_file in smoke_files:
        smoke_path = Path(smoke_file)
        if not smoke_path.is_absolute():
            smoke_path = (repo_root / smoke_path).resolve()
        if not smoke_path.exists():
            raise IntDbError(f"Smoke SQL file not found: {smoke_path}")
        _run_checked(psql_base + ["-f", str(smoke_path)], extra_env=env, cwd=repo_root)


def _cmd_local_test_run(args: argparse.Namespace) -> int:
    _assert_owner_control_token(args.confirm_owner_control)
    _require_docker()
    repo_root = _resolve_data_repo(args.repo)
    workspace = _local_test_workspace_path(args.workdir)
    workspace.mkdir(parents=True, exist_ok=True)
    supabase_cmd = _resolve_supabase_command()
    try:
        _run_checked([*supabase_cmd, "init"], cwd=workspace)
        _run_checked([*supabase_cmd, "start"], cwd=workspace)
        db_url = _supabase_status_db_url(supabase_cmd, workspace)
        temp_env = dict(os.environ)
        temp_env.update(_db_env_from_url(db_url))
        _run_checked(
            [
                _require_bash(),
                str(repo_root / "init" / "010_supabase_migrate.sh"),
                "apply",
            ],
            extra_env=temp_env,
            cwd=repo_root,
        )
        if not args.no_seed:
            _run_repo_seed(repo_root, db_url)
        _run_local_smoke(repo_root, db_url, args.smoke_file or [])
        print(
            json.dumps(
                {
                    "workspace": str(workspace),
                    "db_url": db_url,
                    "kept_running": bool(args.keep_running),
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        if not args.keep_running:
            try:
                _run_checked([*supabase_cmd, "stop", "--no-backup"], cwd=workspace)
            except Exception:
                pass


def _cmd_local_test_stop(args: argparse.Namespace) -> int:
    _assert_owner_control_token(args.confirm_owner_control)
    workspace = _local_test_workspace_path(args.workdir)
    if not workspace.exists():
        raise IntDbError(f"Workspace not found: {workspace}")
    supabase_cmd = _resolve_supabase_command()
    _run_checked([*supabase_cmd, "stop", "--no-backup"], cwd=workspace)
    print(str(workspace))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="intdb",
        description="Self-contained operator CLI для remote Postgres/Supabase профилей через native PostgreSQL CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Проверить native PostgreSQL CLI, TCP и SQL-доступ к профилю.")
    doctor.add_argument("--profile", required=True)
    doctor.set_defaults(handler=_cmd_doctor)

    sql = subparsers.add_parser("sql", help="Выполнить ad-hoc SQL на выбранном профиле.")
    sql.add_argument("--profile", required=True)
    sql.add_argument("--sql", required=True)
    sql.add_argument("--write", action="store_true")
    sql.add_argument("--approve-target")
    sql.add_argument("--force-prod-write", action="store_true")
    sql.set_defaults(handler=_cmd_sql)

    file_cmd = subparsers.add_parser("file", help="Выполнить SQL-файл на выбранном профиле.")
    file_cmd.add_argument("--profile", required=True)
    file_cmd.add_argument("--path", required=True)
    file_cmd.add_argument("--write", action="store_true")
    file_cmd.add_argument("--approve-target")
    file_cmd.add_argument("--force-prod-write", action="store_true")
    file_cmd.set_defaults(handler=_cmd_file)

    dump = subparsers.add_parser("dump", help="Снять dump с source-профиля.")
    dump.add_argument("--source", required=True)
    dump.add_argument("--output")
    dump.add_argument("--format", choices=("plain", "custom"), default="custom")
    dump.add_argument("--schema-only", action="store_true")
    dump.add_argument("--data-only", action="store_true")
    dump.add_argument("--table", action="append")
    dump.set_defaults(handler=_cmd_dump)

    restore = subparsers.add_parser("restore", help="Залить dump в target-профиль.")
    restore.add_argument("--target", required=True)
    restore.add_argument("--input", required=True)
    restore.add_argument("--format", choices=("auto", "plain", "custom"), default="auto")
    restore.add_argument("--clean", action="store_true")
    restore.add_argument("--schema-only", action="store_true")
    restore.add_argument("--data-only", action="store_true")
    restore.add_argument("--approve-target", required=True)
    restore.add_argument("--force-prod-write", action="store_true")
    restore.set_defaults(handler=_cmd_restore)

    clone = subparsers.add_parser("clone", help="Скопировать dump source -> target через локальную машину.")
    clone.add_argument("--source", required=True)
    clone.add_argument("--target", required=True)
    clone.add_argument("--schema-only", action="store_true")
    clone.add_argument("--data-only", action="store_true")
    clone.add_argument("--table", action="append")
    clone.add_argument("--clean", action="store_true")
    clone.add_argument("--approve-target", required=True)
    clone.add_argument("--force-prod-write", action="store_true")
    clone.set_defaults(handler=_cmd_clone)

    copy_cmd = subparsers.add_parser("copy", help="Сделать query-export из source и залить в target table.")
    copy_cmd.add_argument("--source", required=True)
    copy_cmd.add_argument("--target", required=True)
    copy_cmd.add_argument("--query", required=True)
    copy_cmd.add_argument("--target-table", required=True)
    copy_cmd.add_argument("--truncate", action="store_true")
    copy_cmd.add_argument("--approve-target", required=True)
    copy_cmd.add_argument("--force-prod-write", action="store_true")
    copy_cmd.set_defaults(handler=_cmd_copy)

    migrate = subparsers.add_parser("migrate", help="Операции с migration flow `/int/data`.")
    migrate_subparsers = migrate.add_subparsers(dest="migrate_command", required=True)

    migrate_status = migrate_subparsers.add_parser("status", help="Сравнить manifest и remote schema_migrations.")
    migrate_status.add_argument("--target", required=True)
    migrate_status.add_argument("--repo")
    migrate_status.set_defaults(handler=_cmd_migrate_status)

    migrate_data = migrate_subparsers.add_parser("data", help="Применить migration flow `/int/data` на target-профиль.")
    migrate_data.add_argument("--target", required=True)
    migrate_data.add_argument("--repo")
    migrate_data.add_argument("--mode", choices=("incremental", "bootstrap"), default="incremental")
    migrate_data.add_argument("--seed-business", action="store_true")
    migrate_data.add_argument("--approve-target", required=True)
    migrate_data.add_argument("--force-prod-write", action="store_true")
    migrate_data.set_defaults(handler=_cmd_migrate_data)

    local_test = subparsers.add_parser(
        "local-test",
        help="Owner-gated local disposable Supabase workflow for `/int/data` bootstrap and smoke.",
    )
    local_test_subparsers = local_test.add_subparsers(dest="local_test_command", required=True)

    local_test_run = local_test_subparsers.add_parser(
        "run",
        help="Поднять local Supabase runtime, применить migrations/seed и опционально smoke.",
    )
    local_test_run.add_argument("--repo")
    local_test_run.add_argument("--workdir")
    local_test_run.add_argument("--smoke-file", action="append")
    local_test_run.add_argument("--no-seed", action="store_true")
    local_test_run.add_argument("--keep-running", action="store_true")
    local_test_run.add_argument("--confirm-owner-control", required=True)
    local_test_run.set_defaults(handler=_cmd_local_test_run)

    local_test_stop = local_test_subparsers.add_parser(
        "stop",
        help="Остановить local Supabase runtime из указанного workspace без backup.",
    )
    local_test_stop.add_argument("--workdir", required=True)
    local_test_stop.add_argument("--confirm-owner-control", required=True)
    local_test_stop.set_defaults(handler=_cmd_local_test_stop)

    project_migrate = subparsers.add_parser(
        "project-migrate",
        help="Project-specific data migrators backed by intdb profiles and PostgreSQL CLI.",
    )
    project_migrate_subparsers = project_migrate.add_subparsers(
        dest="project_migrate_command",
        required=True,
    )

    punktb_legacy = project_migrate_subparsers.add_parser(
        "punktb-legacy-assess",
        help="Migrate legacy PunktB clients/managers/results into the current assessment schema.",
    )
    punktb_mode = punktb_legacy.add_mutually_exclusive_group(required=True)
    punktb_mode.add_argument("--dry-run", action="store_true")
    punktb_mode.add_argument("--apply", action="store_true")
    punktb_legacy.add_argument("--source", required=True)
    punktb_legacy.add_argument("--target", required=True)
    punktb_legacy.add_argument("--approve-target")
    punktb_legacy.add_argument("--force-prod-write", action="store_true")
    punktb_legacy.add_argument("--workdir")
    punktb_legacy.add_argument("--report-json")
    punktb_legacy.add_argument("--limit", type=int, help="Limit exported legacy client rows for rehearsal debugging.")
    punktb_legacy.set_defaults(handler=_cmd_project_migrate_punktb_legacy_assess)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except IntDbError as exc:
        print(f"intdb: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"intdb: внешняя команда завершилась с кодом {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1
    except OSError as exc:
        print(f"intdb: системная ошибка: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("intdb: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
