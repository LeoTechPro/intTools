-- DRAFT ONLY. DO NOT APPLY.
-- Legacy contour roles for punkt_b_legacy_prod.

\set ON_ERROR_STOP on

-- 1) Rename existing legacy runtime login role
ALTER ROLE punkt_b RENAME TO legacy_backend_role;

-- 2) Create read-only role for agents
CREATE ROLE db_readonly_legacy
  LOGIN
  NOSUPERUSER
  NOINHERIT
  NOCREATEROLE
  NOCREATEDB
  NOREPLICATION
  NOBYPASSRLS;

-- 3) Optional compatibility helper (if needed)
-- CREATE ROLE punkt_b NOLOGIN;
-- GRANT legacy_backend_role TO punkt_b;

-- TODO:
-- - verify all legacy DSN/config references are switched to legacy_backend_role before apply.
-- - verify app/container startup scripts do not hard-fail on old role name.
