-- DRAFT ONLY. DO NOT APPLY.
-- Migration role restrictions and preflight contract.

\set ON_ERROR_STOP on

-- 1) Remove admin-class privileges from migrators
ALTER ROLE db_migrator_prod NOCREATEROLE NOCREATEDB NOBYPASSRLS NOSUPERUSER NOREPLICATION;
ALTER ROLE db_migrator_dev  NOCREATEROLE NOCREATEDB NOBYPASSRLS NOSUPERUSER NOREPLICATION;

-- 2) Force predictable search_path for migration sessions
ALTER ROLE db_migrator_prod SET search_path = app, public;
ALTER ROLE db_migrator_dev  SET search_path = public;

-- 3) Ban direct legacy migration usage (policy guard via grants)
-- Ensure db_migrator_prod has no write access on punkt_b_legacy_prod objects.
-- TODO: enforce with explicit REVOKE statements after full inventory.

-- 4) Preflight contract query (must be executed by controlled script before any apply)
-- Expected output must include: host, db, role, tx_read_only, and explicit PROD marker.
SELECT
  current_database() AS db_name,
  current_user AS role_name,
  inet_server_addr()::text AS server_addr,
  inet_server_port() AS server_port,
  current_setting('transaction_read_only') AS tx_read_only,
  now() AS checked_at;

-- 5) Admin escalation policy
-- Operations below must be blocked in regular migrator flow and handled by db_admin_* only:
-- - CREATE/ALTER ROLE
-- - CREATE EXTENSION
-- - ALTER ... OWNER
-- - ALTER SCHEMA OWNER
-- - cluster-wide settings
