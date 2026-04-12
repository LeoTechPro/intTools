-- DRAFT ONLY. DO NOT APPLY.
-- Enforce read-only behavior for agent/audit roles.

\set ON_ERROR_STOP on

-- ===== LEGACY (punkt_b_legacy_prod) =====
-- db_readonly_legacy must never write
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON ALL TABLES IN SCHEMA public
  FROM db_readonly_legacy;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLES
  FROM db_readonly_legacy;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO db_readonly_legacy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO db_readonly_legacy;

ALTER ROLE db_readonly_legacy SET default_transaction_read_only = on;

-- ===== PROD/DEV readonly roles =====
ALTER ROLE db_readonly_prod SET default_transaction_read_only = on;
ALTER ROLE db_readonly_dev  SET default_transaction_read_only = on;

-- Optional hardening of known problematic legacy names (validate first):
-- REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA app, public FROM supabase_read_only_user;
-- ALTER ROLE supabase_read_only_user NOCREATEROLE NOCREATEDB NOBYPASSRLS;

-- IMPORTANT:
-- default_transaction_read_only at DATABASE level is optional and risky for legacy backend.
-- If enabled at DB level, explicitly override for legacy_backend_role:
-- ALTER DATABASE punkt_b_legacy_prod SET default_transaction_read_only = on;
-- ALTER ROLE legacy_backend_role SET default_transaction_read_only = off;
