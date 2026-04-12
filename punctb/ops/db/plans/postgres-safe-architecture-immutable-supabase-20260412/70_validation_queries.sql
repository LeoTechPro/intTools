-- DRAFT ONLY
-- Validation queries after custom-role changes.

-- 1) Ensure system roles untouched (manual compare against baseline snapshot).
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname IN (
  'authenticator','anon','authenticated','service_role',
  'supabase_read_only_user','dashboard_user',
  'supabase_admin','supabase_auth_admin','supabase_functions_admin',
  'supabase_realtime_admin','supabase_replication_admin','supabase_storage_admin'
)
ORDER BY rolname;

-- 2) Custom flags sanity
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname IN (
  'db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro',
  'db_admin_dev','db_migrator_dev','db_readonly_dev','intdata_test_bootstrap','intdata_test_runner','punkt_b_test_user'
)
ORDER BY rolname;

-- 3) readonly roles must have no write grants in app/public
SELECT grantee, table_schema, privilege_type, count(*)
FROM information_schema.role_table_grants
WHERE grantee IN ('db_readonly_prod','db_readonly_legacy','db_readonly_dev')
  AND privilege_type IN ('INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')
GROUP BY grantee, table_schema, privilege_type
ORDER BY grantee, table_schema, privilege_type;

-- 4) legacy write should remain only for legacy runtime role (custom scope)
SELECT grantee, privilege_type, count(*)
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND grantee IN ('legacy_backend_role','db_readonly_legacy')
GROUP BY grantee, privilege_type
ORDER BY grantee, privilege_type;
