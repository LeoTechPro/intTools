-- DRAFT ONLY. DO NOT APPLY.
-- Grants model for app/public schemas across prod/dev.

\set ON_ERROR_STOP on

-- ===== PROD (punkt_b_prod) =====
-- Run in punkt_b_prod

-- Schema usage
GRANT USAGE ON SCHEMA app TO db_migrator_prod, db_readonly_prod;
GRANT USAGE ON SCHEMA public TO db_migrator_prod, db_readonly_prod;

-- Existing objects
GRANT SELECT ON ALL TABLES IN SCHEMA app TO db_readonly_prod;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO db_readonly_prod;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO db_migrator_prod;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO db_migrator_prod;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO db_migrator_prod, db_readonly_prod;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO db_migrator_prod, db_readonly_prod;

-- Functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA app TO db_migrator_prod, db_readonly_prod;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO db_migrator_prod, db_readonly_prod;

-- ===== DEV (intdata) =====
-- Run in intdata

GRANT USAGE ON SCHEMA public TO db_migrator_dev, db_readonly_dev;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO db_readonly_dev;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO db_migrator_dev;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO db_migrator_dev, db_readonly_dev;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO db_migrator_dev, db_readonly_dev;

-- TODO:
-- - intdata non-public schemas (assess/crm/...) inventory before final grant matrix.
-- - ensure runtime roles keep required privileges and do not inherit admin-like rights.
