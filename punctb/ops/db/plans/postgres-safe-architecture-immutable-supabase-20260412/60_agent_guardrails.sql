-- DRAFT ONLY
-- SQL-side custom-role guardrails (supporting process policy).

-- Readonly roles defaults
ALTER ROLE db_readonly_prod SET default_transaction_read_only = on;
ALTER ROLE db_readonly_legacy SET default_transaction_read_only = on;
ALTER ROLE db_readonly_dev SET default_transaction_read_only = on;

-- Optional safety defaults
ALTER ROLE db_readonly_prod SET statement_timeout = '30s';
ALTER ROLE db_readonly_legacy SET statement_timeout = '30s';
ALTER ROLE db_readonly_dev SET statement_timeout = '30s';

ALTER ROLE db_migrator_prod SET lock_timeout = '5s';
ALTER ROLE db_migrator_dev SET lock_timeout = '5s';

-- NOTE:
-- No restrictions here can fully replace wrapper/process controls.
-- SYSTEM Supabase roles remain untouched.
