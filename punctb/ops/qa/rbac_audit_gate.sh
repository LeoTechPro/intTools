#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

SCHEMA_FILE="${SCHEMA_FILE:-backend/init/schema.sql}"
SEED_FILE="${SEED_FILE:-backend/init/seed.sql}"

if [[ ! -f "${SCHEMA_FILE}" ]]; then
  echo "RBAC_AUDIT_FAIL: schema file not found: ${SCHEMA_FILE}" >&2
  exit 1
fi

if [[ ! -f "${SEED_FILE}" ]]; then
  echo "RBAC_AUDIT_FAIL: seed file not found: ${SEED_FILE}" >&2
  exit 1
fi

schema_forbidden_tokens=(
  "admin:users:manage"
  "users:manage"
  "admin:system:manage"
  "admin:users:status"
  "admin:profile:update"
  "profile:update"
  "admin:profile:view"
  "profile:view"
  "specialist:assign"
)

schema_fail=0
for token in "${schema_forbidden_tokens[@]}"; do
  if awk '
    BEGIN {skip = 0}
    /^CREATE FUNCTION app\._rbac_canonicalize_perm_code\(p_perm_code text\)/ {skip = 1}
    skip == 0 {print}
    skip == 1 && /^\$\$;/ {skip = 0; next}
  ' "${SCHEMA_FILE}" | rg -n --fixed-strings "${token}" >/dev/null; then
    echo "RBAC_AUDIT_FAIL: forbidden token in runtime schema: ${token}" >&2
    schema_fail=1
  fi
done

if [[ "${schema_fail}" -ne 0 ]]; then
  exit 1
fi

if ! rg -n --fixed-strings "system:edit" "${SCHEMA_FILE}" >/dev/null; then
  echo "RBAC_AUDIT_FAIL: expected canonical token missing in schema: system:edit" >&2
  exit 1
fi

if ! rg -n --fixed-strings "supervisor:assign" "${SCHEMA_FILE}" >/dev/null; then
  echo "RBAC_AUDIT_FAIL: expected canonical token missing in schema: supervisor:assign" >&2
  exit 1
fi

if ! rg -n --fixed-strings "CREATE FUNCTION app.roles_deactivate_with_strategy(" "${SCHEMA_FILE}" >/dev/null; then
  echo "RBAC_AUDIT_FAIL: roles_deactivate_with_strategy() missing in schema baseline" >&2
  exit 1
fi

if ! rg -n --fixed-strings "valid_to = v_now" "${SCHEMA_FILE}" >/dev/null; then
  echo "RBAC_AUDIT_FAIL: roles_deactivate_with_strategy() must close grants with valid_to = v_now" >&2
  exit 1
fi

if rg -n "CREATE FUNCTION public\\.admin_" "${SCHEMA_FILE}" >/dev/null; then
  echo "RBAC_AUDIT_FAIL: legacy public.admin_* functions must not exist in schema baseline" >&2
  rg -n "CREATE FUNCTION public\\.admin_" "${SCHEMA_FILE}" >&2
  exit 1
fi

if rg -n "app\\.admin_[a-z0-9_]+\\(" "${SCHEMA_FILE}" >/dev/null; then
  echo "RBAC_AUDIT_FAIL: runtime function definitions still reference app.admin_*" >&2
  rg -n "app\\.admin_[a-z0-9_]+\\(" "${SCHEMA_FILE}" >&2
  exit 1
fi

perm_dups="$(awk '
  BEGIN {inside = 0}
  /^INSERT INTO app\.perms \(/ {inside = 1; next}
  inside == 1 && /^ON CONFLICT \(code\)/ {inside = 0}
  inside == 1 {
    if (match($0, /^[[:space:]]*\047([^'\'']+)\047[[:space:]]*,/, m)) {
      code = m[1]
      cnt[code]++
    }
  }
  END {
    for (k in cnt) if (cnt[k] > 1) print k "|" cnt[k]
  }
' "${SEED_FILE}")"

if [[ -n "${perm_dups}" ]]; then
  echo "RBAC_AUDIT_FAIL: duplicate app.perms(code) entries in seed.sql" >&2
  echo "${perm_dups}" >&2
  exit 1
fi

role_grant_dups="$(awk '
  BEGIN {inside = 0}
  /^INSERT INTO app\.role_perm_grants \(/ {inside = 1; next}
  inside == 1 && /^ON CONFLICT \(role_code, perm_code\)/ {inside = 0}
  inside == 1 {
    if (match($0, /^[[:space:]]*\047([^'\'']+)\047[[:space:]]*,[[:space:]]*\047([^'\'']+)\047[[:space:]]*,/, m)) {
      key = m[1] "|" m[2]
      cnt[key]++
    }
  }
  END {
    for (k in cnt) if (cnt[k] > 1) print k "|" cnt[k]
  }
' "${SEED_FILE}")"

if [[ -n "${role_grant_dups}" ]]; then
  echo "RBAC_AUDIT_FAIL: duplicate app.role_perm_grants(role_code, perm_code) entries in seed.sql" >&2
  echo "${role_grant_dups}" >&2
  exit 1
fi

seed_forbidden_patterns=(
  "notes::read"
  "settings:timeline:post"
  "supervisor:change"
)

for token in "${seed_forbidden_patterns[@]}"; do
  if rg -n --fixed-strings "${token}" "${SEED_FILE}" >/dev/null; then
    echo "RBAC_AUDIT_FAIL: forbidden legacy token in seed.sql: ${token}" >&2
    exit 1
  fi
done

if rg -n -o "diagnostics:[a-z0-9._:-]+" "${SEED_FILE}" | rg -v "diagnostics:edit$" >/dev/null; then
  echo "RBAC_AUDIT_FAIL: legacy diagnostics:<slug> token found in seed.sql" >&2
  rg -n -o "diagnostics:[a-z0-9._:-]+" "${SEED_FILE}" | rg -v "diagnostics:edit$" >&2
  exit 1
fi

echo "RBAC_AUDIT_OK: schema runtime tokens and seed consistency checks passed"
