-- DRAFT ONLY
-- Цель: собрать factual inventory перед любыми мутациями.

-- 1) Databases and owners
SELECT datname, pg_catalog.pg_get_userbyid(datdba) AS owner
FROM pg_database
WHERE datistemplate = false
ORDER BY datname;

-- 2) Role flags (system + custom)
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls, rolcanlogin
FROM pg_roles
WHERE rolname IN (
  -- system/immutable
  'authenticator','anon','authenticated','service_role',
  'supabase_read_only_user','dashboard_user',
  'supabase_admin','supabase_auth_admin','supabase_functions_admin',
  'supabase_realtime_admin','supabase_replication_admin','supabase_storage_admin',
  -- custom/managed
  'db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy',
  'legacy_backend_role','punktb_pro',
  'db_admin_dev','db_migrator_dev','db_readonly_dev',
  'intdata_test_bootstrap','intdata_test_runner','punkt_b_test_user'
)
ORDER BY rolname;

-- 3) Active sessions by db/role
SELECT usename, datname, state, count(*)
FROM pg_stat_activity
WHERE pid <> pg_backend_pid()
GROUP BY usename, datname, state
ORDER BY datname, usename;

-- 4) app/public grants in punkt_b_prod
SELECT grantee, table_schema, privilege_type, count(*)
FROM information_schema.role_table_grants
WHERE table_schema IN ('app','public')
GROUP BY grantee, table_schema, privilege_type
ORDER BY grantee, table_schema, privilege_type;

-- 5) public grants in legacy
SELECT grantee, privilege_type, count(*)
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
GROUP BY grantee, privilege_type
ORDER BY grantee, privilege_type;
