#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

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

  printf '%s\n' "intdata"
}

DB_NAME="$(resolve_db_name)"

if [[ "$(sudo -u postgres psql "${DB_NAME}" -v ON_ERROR_STOP=1 -Atc "select 1;")" != "1" ]]; then
  echo "SMOKE_FAIL: database connectivity check failed for ${DB_NAME}"
  exit 1
fi

matrix_sql="
with expected_tables(check_id, schema_name, table_name) as (
  values
    ('rls.user_profiles', 'app', 'user_profiles'),
    ('rls.event_notifications', 'app', 'event_notifications'),
    ('rls.user_conclusions', 'app', 'user_conclusions'),
    ('rls.notes', 'app', 'notes')
),

table_state as (
  select
    e.check_id,
    e.schema_name,
    e.table_name,
    to_regclass(format('%I.%I', e.schema_name, e.table_name)) as relid
  from expected_tables e
),

rls_checks as (
  select
    check_id || '.exists' as check_id,
    case when relid is not null then 'PASS' else 'FAIL' end as status,
    format('%I.%I', schema_name, table_name) as detail
  from table_state
  union all
  select
    check_id || '.enabled' as check_id,
    case
      when relid is null then 'FAIL'
      when c.relrowsecurity then 'PASS'
      else 'FAIL'
    end as status,
    format('%I.%I', schema_name, table_name) as detail
  from table_state ts
  left join pg_class c on c.oid = ts.relid
  union all
  select
    check_id || '.has_policies' as check_id,
    case
      when relid is null then 'FAIL'
      when (
        select count(*)
        from pg_policies p
        where p.schemaname = ts.schema_name and p.tablename = ts.table_name
      ) > 0 then 'PASS'
      else 'FAIL'
    end as status,
    format('%I.%I', schema_name, table_name) as detail
  from table_state ts
),

grant_expectations(check_id, role_name, signature, should_have) as (
  values
    ('grant.required.current_user_is_system.authenticator', 'authenticator', 'app.current_user_is_system()', true),
    ('grant.required.current_user_has_perm.authenticator', 'authenticator', 'app.current_user_has_perm(text)', true),
    ('grant.required.user_has_perm.authenticator', 'authenticator', 'app.user_has_perm(uuid,text,timestamp with time zone)', true),

    ('grant.required.notes_list.authenticated', 'authenticated', 'app.notes_list(text,uuid,uuid,integer,integer,text,text,text[],text[],uuid,timestamp with time zone,timestamp with time zone,text)', true),
    ('grant.required.notes_create.authenticated', 'authenticated', 'app.notes_create(text,uuid,uuid,text,boolean,boolean,text,text,text,timestamp with time zone,uuid,timestamp with time zone,jsonb,text[])', true),
    ('grant.required.notes_update.authenticated', 'authenticated', 'app.notes_update(uuid,text,boolean,boolean,text,boolean,text,text,boolean,timestamp with time zone,boolean,uuid,boolean,timestamp with time zone,boolean,jsonb,boolean,text[])', true),
    ('grant.required.notes_soft_delete.authenticated', 'authenticated', 'app.notes_soft_delete(uuid)', true),

    ('grant.forbidden.notes_list.authenticator', 'authenticator', 'app.notes_list(text,uuid,uuid,integer,integer,text,text,text[],text[],uuid,timestamp with time zone,timestamp with time zone,text)', false),
    ('grant.forbidden.notes_create.authenticator', 'authenticator', 'app.notes_create(text,uuid,uuid,text,boolean,boolean,text,text,text,timestamp with time zone,uuid,timestamp with time zone,jsonb,text[])', false),
    ('grant.forbidden.notes_update.authenticator', 'authenticator', 'app.notes_update(uuid,text,boolean,boolean,text,boolean,text,text,boolean,timestamp with time zone,boolean,uuid,boolean,timestamp with time zone,boolean,jsonb,boolean,text[])', false),
    ('grant.forbidden.notes_soft_delete.authenticator', 'authenticator', 'app.notes_soft_delete(uuid)', false),

    ('grant.forbidden.notes_scope_for_viewer.authenticated', 'authenticated', 'app.notes_scope_for_viewer(boolean)', false),
    ('grant.forbidden.notes_scope_for_viewer.authenticator', 'authenticator', 'app.notes_scope_for_viewer(boolean)', false),
    ('grant.forbidden.notes_can_access_profile.authenticated', 'authenticated', 'app.notes_can_access_profile(uuid,boolean)', false),
    ('grant.forbidden.notes_can_access_profile.authenticator', 'authenticator', 'app.notes_can_access_profile(uuid,boolean)', false),
    ('grant.forbidden.notes_can_access_crm_case.authenticated', 'authenticated', 'app.notes_can_access_crm_case(uuid,boolean)', false),
    ('grant.forbidden.notes_can_access_crm_case.authenticator', 'authenticator', 'app.notes_can_access_crm_case(uuid,boolean)', false),
    ('grant.forbidden.can_create_note_in_context.authenticated', 'authenticated', 'app.can_create_note_in_context(uuid,uuid,uuid)', false),
    ('grant.forbidden.can_create_note_in_context.authenticator', 'authenticator', 'app.can_create_note_in_context(uuid,uuid,uuid)', false),
    ('grant.forbidden.can_edit_note_privacy_row.authenticated', 'authenticated', 'app.can_edit_note_privacy_row(uuid)', false),
    ('grant.forbidden.can_edit_note_privacy_row.authenticator', 'authenticator', 'app.can_edit_note_privacy_row(uuid)', false),
    ('grant.forbidden.can_read_note_row.authenticated', 'authenticated', 'app.can_read_note_row(uuid,uuid,uuid,uuid,boolean,boolean,timestamp with time zone)', false),
    ('grant.forbidden.can_read_note_row.authenticator', 'authenticator', 'app.can_read_note_row(uuid,uuid,uuid,uuid,boolean,boolean,timestamp with time zone)', false),
    ('grant.forbidden.can_edit_note_row.authenticated', 'authenticated', 'app.can_edit_note_row(uuid,uuid,uuid,uuid,timestamp with time zone)', false),
    ('grant.forbidden.can_edit_note_row.authenticator', 'authenticator', 'app.can_edit_note_row(uuid,uuid,uuid,uuid,timestamp with time zone)', false),
    ('grant.forbidden.notes_actor_json.authenticated', 'authenticated', 'app.notes_actor_json(uuid)', false),
    ('grant.forbidden.notes_actor_json.authenticator', 'authenticator', 'app.notes_actor_json(uuid)', false),
    ('grant.forbidden.notes_row_to_json.authenticated', 'authenticated', 'app.notes_row_to_json(uuid)', false),
    ('grant.forbidden.notes_row_to_json.authenticator', 'authenticator', 'app.notes_row_to_json(uuid)', false),
    ('grant.forbidden.notes_list_profile_safe.authenticated', 'authenticated', 'app.notes_list_profile_safe(uuid)', false),
    ('grant.forbidden.notes_list_profile_safe.authenticator', 'authenticator', 'app.notes_list_profile_safe(uuid)', false)
),

grant_checks as (
  select
    g.check_id,
    case
      when to_regprocedure(g.signature) is null then 'FAIL'
      when has_function_privilege(g.role_name, to_regprocedure(g.signature), 'EXECUTE') = g.should_have then 'PASS'
      else 'FAIL'
    end as status,
    g.signature || ' as ' || g.role_name || ' expected=' || g.should_have::text as detail
  from grant_expectations g
)

select check_id || '|' || status || '|' || detail from rls_checks
union all
select check_id || '|' || status || '|' || detail from grant_checks
order by 1;
"

mapfile -t rows < <(PGOPTIONS='-c default_transaction_read_only=on' sudo -u postgres psql "${DB_NAME}" -v ON_ERROR_STOP=1 -Atq -c "${matrix_sql}")

if [[ "${#rows[@]}" -eq 0 ]]; then
  echo "SMOKE_FAIL: no checks produced by matrix"
  exit 1
fi

fail_count=0
for row in "${rows[@]}"; do
  IFS='|' read -r check_id status detail <<< "${row}"
  echo "${status}: ${check_id} :: ${detail}"
  if [[ "${status}" != "PASS" ]]; then
    fail_count=$((fail_count + 1))
  fi
done

if [[ "${fail_count}" -gt 0 ]]; then
  echo "SMOKE_FAIL: RLS/GRANT matrix detected ${fail_count} violation(s)"
  exit 1
fi

echo "SMOKE_OK: RLS/GRANT matrix passed (${#rows[@]} checks)"
