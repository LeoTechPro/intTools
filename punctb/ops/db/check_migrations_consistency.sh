#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

MIGRATIONS_DIR="${MIGRATIONS_DIR:-backend/init/migrations}"
ARCHIVE_DIR="${ARCHIVE_DIR:-${MIGRATIONS_DIR}/archive}"
MANIFEST_FILE="${MANIFEST_FILE:-backend/init/migration_manifest.lock}"
VERSION_FLOOR="${VERSION_FLOOR:-20260126000000}"

resolve_db_name() {
  if [[ -n "${DB_NAME:-}" ]]; then
    printf '%s\n' "$DB_NAME"
    return
  fi

  local env_file=".env"
  if [[ ! -f "$env_file" ]]; then
    env_file=".env.example"
  fi

  if [[ -f "$env_file" ]]; then
    local from_env
    from_env="$(grep -E '^POSTGRES_DB=' "$env_file" | tail -n1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')"
    if [[ -n "$from_env" ]]; then
      printf '%s\n' "$from_env"
      return
    fi
  fi

  printf '%s\n' "punctbpro"
}

DB_NAME="$(resolve_db_name)"

psql_ro() {
  local sql="$1"
  sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -Atc "$sql"
}

if [[ ! -d "$MIGRATIONS_DIR" ]]; then
  echo "SMOKE_FAIL: migrations dir not found: $MIGRATIONS_DIR"
  exit 1
fi

if [[ ! -f "$MANIFEST_FILE" ]]; then
  echo "SMOKE_FAIL: migration manifest not found: $MANIFEST_FILE"
  exit 1
fi

if [[ "$(psql_ro "select to_regclass('public.schema_migrations') is not null;")" != "t" ]]; then
  echo "SMOKE_FAIL: required table not found: public.schema_migrations"
  exit 1
fi

mapfile -t active_files < <(find "$MIGRATIONS_DIR" -maxdepth 1 -type f -name '*.sql' -printf '%f\n' | sort)

file_versions_raw=()
malformed_files=()
declare -A active_version_by_file
for file_name in "${active_files[@]}"; do
  if [[ "$file_name" =~ ^([0-9]{14})_.*\.sql$ ]]; then
    file_versions_raw+=("${BASH_REMATCH[1]}")
    active_version_by_file["$file_name"]="${BASH_REMATCH[1]}"
  else
    malformed_files+=("$file_name")
  fi
done

mapfile -t file_duplicates < <(printf '%s\n' "${file_versions_raw[@]}" | sort | uniq -d)
mapfile -t active_versions < <(printf '%s\n' "${file_versions_raw[@]}" | awk -v floor="$VERSION_FLOOR" '$1 >= floor' | sort -u)

declare -A manifest_version_by_file
declare -A manifest_checksum_by_file
manifest_bad_entries=()

while IFS='|' read -r manifest_version manifest_file_name manifest_checksum; do
  if [[ -z "$manifest_version" || "$manifest_version" =~ ^[[:space:]]*# ]]; then
    continue
  fi
  manifest_version="$(echo "$manifest_version" | tr -d '[:space:]')"
  manifest_file_name="$(echo "$manifest_file_name" | tr -d '[:space:]')"
  manifest_checksum="$(echo "$manifest_checksum" | tr -d '[:space:]')"

  if [[ ! "$manifest_version" =~ ^[0-9]{14}$ || -z "$manifest_file_name" || ! "$manifest_checksum" =~ ^[0-9a-f]{64}$ ]]; then
    manifest_bad_entries+=("$manifest_version|$manifest_file_name|$manifest_checksum")
    continue
  fi

  if [[ -n "${manifest_version_by_file[$manifest_file_name]:-}" ]]; then
    manifest_bad_entries+=("duplicate:$manifest_file_name")
    continue
  fi

  manifest_version_by_file["$manifest_file_name"]="$manifest_version"
  manifest_checksum_by_file["$manifest_file_name"]="$manifest_checksum"
done < "$MANIFEST_FILE"

manifest_missing=()
manifest_version_mismatch=()
manifest_checksum_mismatch=()
single_insert_failures=()
schema_version_mismatch=()
active_untracked=()
manifest_untracked=()

is_git_tracked() {
  local path="$1"
  git ls-files --error-unmatch "$path" >/dev/null 2>&1
}

extract_insert_block() {
  local sql_file="$1"
  awk '
    BEGIN { IGNORECASE = 1; capture = 0 }
    /insert[[:space:]]+into[[:space:]]+public\.schema_migrations/ { capture = 1 }
    capture { print }
    capture && /;/ { exit }
  ' "$sql_file"
}

for file_name in "${active_files[@]}"; do
  sql_path="$MIGRATIONS_DIR/$file_name"
  file_version="${active_version_by_file[$file_name]:-}"
  manifest_version="${manifest_version_by_file[$file_name]:-}"
  manifest_checksum="${manifest_checksum_by_file[$file_name]:-}"

  if ! is_git_tracked "$sql_path"; then
    active_untracked+=("$file_name")
  fi

  if [[ -z "$manifest_version" || -z "$manifest_checksum" ]]; then
    manifest_missing+=("$file_name")
    continue
  fi

  if [[ "$manifest_version" != "$file_version" ]]; then
    manifest_version_mismatch+=("$file_name:file=$file_version manifest=$manifest_version")
  fi

  file_checksum="$(sha256sum "$sql_path" | awk '{print $1}')"
  if [[ "$file_checksum" != "$manifest_checksum" ]]; then
    manifest_checksum_mismatch+=("$file_name")
  fi

  insert_count="$(grep -Eic 'insert[[:space:]]+into[[:space:]]+public\.schema_migrations' "$sql_path" || true)"
  if [[ "$insert_count" -ne 1 ]]; then
    single_insert_failures+=("$file_name:insert_count=$insert_count")
    continue
  fi

  insert_block="$(extract_insert_block "$sql_path")"
  insert_version="$(printf '%s\n' "$insert_block" | grep -Eo '[0-9]{14}' | head -n1 || true)"
  if [[ -z "$insert_version" || "$insert_version" != "$file_version" ]]; then
    schema_version_mismatch+=("$file_name:expected=$file_version actual=${insert_version:-none}")
  fi
done

manifest_stale_entries=()
for file_name in "${!manifest_version_by_file[@]}"; do
  manifest_path="$MIGRATIONS_DIR/$file_name"
  if [[ ! -f "$manifest_path" ]]; then
    manifest_stale_entries+=("$file_name")
    continue
  fi
  if ! is_git_tracked "$manifest_path"; then
    manifest_untracked+=("$file_name")
  fi
done

mapfile -t public_versions < <(
  psql_ro "select version::text from public.schema_migrations where version::text ~ '^[0-9]{14}$' and version::text >= '$VERSION_FLOOR' order by version::text;"
)

has_auth_table="$(psql_ro "select to_regclass('auth.schema_migrations') is not null;")"
auth_versions=()
if [[ "$has_auth_table" == "t" ]]; then
  mapfile -t auth_versions < <(
    psql_ro "select version::text from auth.schema_migrations where version::text ~ '^[0-9]{14}$' and version::text >= '$VERSION_FLOOR' order by version::text;"
  )
fi

mapfile -t public_duplicates < <(
  psql_ro "select version::text from public.schema_migrations where version::text ~ '^[0-9]{14}$' and version::text >= '$VERSION_FLOOR' group by version having count(*) > 1 order by version::text;"
)

auth_duplicates=()
if [[ "$has_auth_table" == "t" ]]; then
  mapfile -t auth_duplicates < <(
    psql_ro "select version::text from auth.schema_migrations where version::text ~ '^[0-9]{14}$' and version::text >= '$VERSION_FLOOR' group by version having count(*) > 1 order by version::text;"
  )
fi

mapfile -t db_versions < <(printf '%s\n' "${public_versions[@]}" "${auth_versions[@]}" | grep -E '^[0-9]{14}$' | sort -u)

mapfile -t archive_versions < <(
  find "$ARCHIVE_DIR" -maxdepth 1 -type f -name '*.sql' -printf '%f\n' 2>/dev/null \
    | sed -nE 's/^([0-9]{14})_.*/\1/p' \
    | awk -v floor="$VERSION_FLOOR" '$1 >= floor' \
    | sort -u
)

missing_in_db=()
for version in "${active_versions[@]}"; do
  if ! printf '%s\n' "${db_versions[@]}" | grep -qx "$version"; then
    missing_in_db+=("$version")
  fi
done

extra_in_db=()
for version in "${db_versions[@]}"; do
  if ! printf '%s\n' "${active_versions[@]}" | grep -qx "$version"; then
    extra_in_db+=("$version")
  fi
done

archived_applied=()
unmanaged_extras=()
for version in "${extra_in_db[@]}"; do
  if printf '%s\n' "${archive_versions[@]}" | grep -qx "$version"; then
    archived_applied+=("$version")
  else
    unmanaged_extras+=("$version")
  fi
done

failed=0

print_fail_list() {
  local title="$1"
  shift
  local values=("$@")
  if [[ "${#values[@]}" -gt 0 ]]; then
    failed=1
    echo "$title"
    printf '  - %s\n' "${values[@]}"
  fi
}

print_fail_list "SMOKE_FAIL: malformed migration filenames (expected YYYYMMDDHHMMSS_*.sql):" "${malformed_files[@]}"
print_fail_list "SMOKE_FAIL: duplicate file version prefixes in active migrations dir:" "${file_duplicates[@]}"
print_fail_list "SMOKE_FAIL: duplicate versions in public.schema_migrations:" "${public_duplicates[@]}"
print_fail_list "SMOKE_FAIL: duplicate versions in auth.schema_migrations:" "${auth_duplicates[@]}"
print_fail_list "SMOKE_FAIL: invalid entries in migration manifest:" "${manifest_bad_entries[@]}"
print_fail_list "SMOKE_FAIL: active migrations missing in manifest:" "${manifest_missing[@]}"
print_fail_list "SMOKE_FAIL: manifest version mismatch:" "${manifest_version_mismatch[@]}"
print_fail_list "SMOKE_FAIL: manifest checksum mismatch:" "${manifest_checksum_mismatch[@]}"
print_fail_list "SMOKE_FAIL: stale entries in manifest (file missing in active dir):" "${manifest_stale_entries[@]}"
print_fail_list "SMOKE_FAIL: active migrations are not git-tracked:" "${active_untracked[@]}"
print_fail_list "SMOKE_FAIL: manifest points to non-tracked migration files:" "${manifest_untracked[@]}"
print_fail_list "SMOKE_FAIL: single-version rule violated (must contain exactly one public.schema_migrations insert):" "${single_insert_failures[@]}"
print_fail_list "SMOKE_FAIL: schema_migrations version mismatch inside SQL file:" "${schema_version_mismatch[@]}"
print_fail_list "SMOKE_FAIL: missing active migration versions in DB:" "${missing_in_db[@]}"
print_fail_list "SMOKE_FAIL: unmanaged DB migration versions (not active, not archive):" "${unmanaged_extras[@]}"

if [[ "${#archived_applied[@]}" -gt 0 ]]; then
  echo "SMOKE_INFO: applied archive versions detected (allowed):"
  printf '  - %s\n' "${archived_applied[@]}"
fi

if [[ "$failed" -ne 0 ]]; then
  exit 1
fi

echo "SMOKE_OK: migration consistency passed (manifest/checksum/single-version/active-sync)"
