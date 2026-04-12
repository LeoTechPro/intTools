-- DRAFT ONLY. SAFE TO RUN (READ-ONLY CHECKS).
-- Validate role model, privilege split, and environment guardrails.

\set ON_ERROR_STOP on

-- A) context
SELECT
  current_database() AS db,
  current_user AS role,
  inet_server_addr()::text AS server_addr,
  inet_server_port() AS server_port,
  current_setting('transaction_read_only') AS tx_read_only,
  now() AS checked_at;

-- B) role attributes (edit list per environment)
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolbypassrls
FROM pg_roles
WHERE rolname IN (
  'db_admin_prod','db_migrator_prod','db_readonly_prod',
  'db_admin_dev','db_migrator_dev','db_readonly_dev',
  'db_readonly_legacy','legacy_backend_role',
  'supabase_read_only_user','authenticator','service_role'
)
ORDER BY rolname;

-- C) schema owners
SELECT nspname, pg_catalog.pg_get_userbyid(nspowner) AS owner
FROM pg_namespace
WHERE nspname IN ('app','public')
ORDER BY nspname;

-- D) table privileges summary for app/public
SELECT grantee, table_schema, privilege_type, count(*) AS objects
FROM information_schema.role_table_grants
WHERE table_schema IN ('app','public')
GROUP BY grantee, table_schema, privilege_type
ORDER BY grantee, table_schema, privilege_type;

-- E) identify roles that can still write in legacy/public (run in punkt_b_legacy_prod)
SELECT grantee,
       max((privilege_type='SELECT')::int)   AS can_select,
       max((privilege_type='INSERT')::int)   AS can_insert,
       max((privilege_type='UPDATE')::int)   AS can_update,
       max((privilege_type='DELETE')::int)   AS can_delete,
       max((privilege_type='TRUNCATE')::int) AS can_truncate
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
GROUP BY grantee
ORDER BY grantee;

-- F) SECURITY DEFINER inventory (for later hardening pass)
SELECT
  n.nspname AS schema_name,
  p.proname AS function_name,
  pg_get_userbyid(p.proowner) AS owner_name,
  p.prosecdef AS is_security_definer
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname IN ('app','public')
  AND p.prosecdef = true
ORDER BY n.nspname, p.proname;
