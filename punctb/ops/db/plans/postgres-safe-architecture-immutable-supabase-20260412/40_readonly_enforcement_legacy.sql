-- DRAFT ONLY
-- Apply in DB: punkt_b_legacy_prod
-- Objective: enforce legacy immutability for agent/custom readonly roles.

-- Schema access
GRANT CONNECT ON DATABASE punkt_b_legacy_prod TO db_readonly_legacy;
GRANT USAGE ON SCHEMA public TO db_readonly_legacy;

-- Table access
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON ALL TABLES IN SCHEMA public
FROM db_readonly_legacy;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO db_readonly_legacy;

-- Future objects
ALTER DEFAULT PRIVILEGES FOR ROLE legacy_backend_role IN SCHEMA public
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM db_readonly_legacy;

ALTER DEFAULT PRIVILEGES FOR ROLE legacy_backend_role IN SCHEMA public
GRANT SELECT ON TABLES TO db_readonly_legacy;

-- Keep legacy runtime write path
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON ALL TABLES IN SCHEMA public TO legacy_backend_role;

-- NOTE:
-- No grants/revokes for SYSTEM Supabase roles.
