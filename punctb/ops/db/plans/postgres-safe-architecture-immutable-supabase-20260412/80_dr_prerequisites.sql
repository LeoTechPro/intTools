-- DRAFT ONLY
-- DR prerequisites for separate Postgres instance on dev-host.
-- This script is intentionally partial: network/cluster-level setup is external.

-- TODO(required): confirm DR instance endpoint/port and pg_hba rules.
-- TODO(required): confirm replication slot retention policy and storage budget.

-- Option A: dedicated custom replication role (preferred vs reusing runtime role)
CREATE ROLE db_dr_replica WITH LOGIN REPLICATION PASSWORD '<set-outside-git>';

-- Optionally restrict databases at cluster config / pg_hba layer.
-- SQL-only publication examples are for logical fallback (not primary recommendation).

-- Logical fallback for punkt_b_prod
-- CREATE PUBLICATION punkt_b_prod_pub FOR ALL TABLES;

-- Logical fallback for punkt_b_legacy_prod
-- CREATE PUBLICATION punkt_b_legacy_prod_pub FOR ALL TABLES;

-- NOTE:
-- No mutation of SYSTEM Supabase roles.
