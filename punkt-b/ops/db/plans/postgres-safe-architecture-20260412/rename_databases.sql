-- DRAFT ONLY. DO NOT APPLY WITHOUT APPROVED CHANGE WINDOW.
-- Goal:
--   punctb_prod -> punkt_b_prod
--   punkt_b     -> punkt_b_legacy_prod

\set ON_ERROR_STOP on

-- 0) Preflight checks
SELECT
  current_database() AS db,
  current_user AS role,
  inet_server_addr()::text AS server_addr,
  inet_server_port() AS server_port,
  now() AS checked_at;

SELECT datname
FROM pg_database
WHERE datname IN ('punctb_prod', 'punkt_b', 'punkt_b_prod', 'punkt_b_legacy_prod')
ORDER BY datname;

-- Optional hard-stop check: ensure no target names already exist.
-- TODO: enforce via external gate script before execution.

-- 1) Terminate active sessions (except self)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname IN ('punctb_prod', 'punkt_b')
  AND pid <> pg_backend_pid();

-- 2) Rename databases
ALTER DATABASE punctb_prod RENAME TO punkt_b_prod;
ALTER DATABASE punkt_b RENAME TO punkt_b_legacy_prod;

-- 3) Validation
SELECT datname
FROM pg_database
WHERE datname IN ('punkt_b_prod', 'punkt_b_legacy_prod')
ORDER BY datname;

-- 4) Rollback (manual, only if needed and if names are free)
-- ALTER DATABASE punkt_b_prod RENAME TO punctb_prod;
-- ALTER DATABASE punkt_b_legacy_prod RENAME TO punkt_b;
