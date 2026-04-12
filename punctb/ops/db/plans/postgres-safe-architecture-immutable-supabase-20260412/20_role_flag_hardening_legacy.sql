-- DRAFT ONLY
-- Custom roles only for legacy contour.

-- legacy runtime writer profile
ALTER ROLE legacy_backend_role NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;

-- agent readonly profile
ALTER ROLE db_readonly_legacy NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;
ALTER ROLE db_readonly_legacy SET default_transaction_read_only = on;

-- NOTE:
-- SYSTEM Supabase roles are immutable and not changed here.
