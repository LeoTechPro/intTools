-- DRAFT ONLY
-- Custom migrator model. No SYSTEM role changes.

-- Apply in punkt_b_prod
GRANT CONNECT ON DATABASE punkt_b_prod TO db_migrator_prod;
GRANT USAGE ON SCHEMA app, public TO db_migrator_prod;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app, public TO db_migrator_prod;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app, public TO db_migrator_prod;

ALTER DEFAULT PRIVILEGES FOR ROLE punktb_pro IN SCHEMA app
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO db_migrator_prod;

ALTER DEFAULT PRIVILEGES FOR ROLE punktb_pro IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO db_migrator_prod;

-- Apply in intdata
GRANT CONNECT ON DATABASE intdata TO db_migrator_dev;
GRANT USAGE ON SCHEMA public TO db_migrator_dev;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO db_migrator_dev;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO db_migrator_dev;

-- NOTE:
-- Migration process guardrails must still enforce wrapper-only entrypoints.
