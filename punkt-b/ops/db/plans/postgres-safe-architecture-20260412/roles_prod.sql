-- DRAFT ONLY. DO NOT APPLY.
-- PROD roles for punkt_b_prod.

\set ON_ERROR_STOP on

-- Admin role (human/bootstrap only)
CREATE ROLE db_admin_prod
  LOGIN
  NOSUPERUSER
  INHERIT
  CREATEROLE
  CREATEDB
  REPLICATION
  BYPASSRLS;

-- Migrator role (controlled write + schema changes in approved schemas)
CREATE ROLE db_migrator_prod
  LOGIN
  NOSUPERUSER
  NOINHERIT
  NOCREATEROLE
  NOCREATEDB
  NOREPLICATION
  NOBYPASSRLS;

-- Read-only role for agents/audit
CREATE ROLE db_readonly_prod
  LOGIN
  NOSUPERUSER
  NOINHERIT
  NOCREATEROLE
  NOCREATEDB
  NOREPLICATION
  NOBYPASSRLS;

-- TODO:
-- 1) Attach PASSWORD management via external secret store workflow.
-- 2) Optional connection limits per role.
-- 3) Membership grants if organizational parent roles are introduced.
