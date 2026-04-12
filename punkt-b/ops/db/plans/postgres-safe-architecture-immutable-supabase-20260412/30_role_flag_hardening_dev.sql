-- DRAFT ONLY
-- Custom dev roles only. supabase_admin and all Supabase roles are immutable in this model.

ALTER ROLE db_migrator_dev NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;

ALTER ROLE db_readonly_dev NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;
ALTER ROLE db_readonly_dev SET default_transaction_read_only = on;

ALTER ROLE db_admin_dev NOSUPERUSER CREATEROLE CREATEDB NOREPLICATION BYPASSRLS;

-- test/bootstrap profiles
ALTER ROLE intdata_test_runner NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;
ALTER ROLE punkt_b_test_user NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;

-- TODO(decision): intdata_test_bootstrap can stay elevated (test-only) or be reduced.
