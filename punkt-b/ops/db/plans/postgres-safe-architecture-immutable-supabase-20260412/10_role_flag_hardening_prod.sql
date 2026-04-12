-- DRAFT ONLY
-- Custom roles only. SYSTEM Supabase roles are immutable and excluded.

-- db_migrator_prod: non-admin migrator profile
ALTER ROLE db_migrator_prod NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;

-- db_readonly_prod: strict readonly profile
ALTER ROLE db_readonly_prod NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;
ALTER ROLE db_readonly_prod SET default_transaction_read_only = on;

-- db_admin_prod: breakglass admin (intentional elevated profile)
ALTER ROLE db_admin_prod NOSUPERUSER CREATEROLE CREATEDB NOREPLICATION BYPASSRLS;

-- punktb_pro: runtime/service role; keep runtime-only.
-- TODO(decision): if replication is not required for runtime, set NOREPLICATION.
-- ALTER ROLE punktb_pro NOREPLICATION;
ALTER ROLE punktb_pro NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS;

-- NOTE:
-- No ALTER for authenticator/anon/authenticated/service_role/supabase_*.
