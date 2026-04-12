-- DRAFT ONLY. DO NOT APPLY.
-- DEV roles for intdata/intdata_test.

\set ON_ERROR_STOP on

CREATE ROLE db_admin_dev
  LOGIN
  NOSUPERUSER
  INHERIT
  CREATEROLE
  CREATEDB
  REPLICATION
  BYPASSRLS;

CREATE ROLE db_migrator_dev
  LOGIN
  NOSUPERUSER
  NOINHERIT
  NOCREATEROLE
  NOCREATEDB
  NOREPLICATION
  NOBYPASSRLS;

CREATE ROLE db_readonly_dev
  LOGIN
  NOSUPERUSER
  NOINHERIT
  NOCREATEROLE
  NOCREATEDB
  NOREPLICATION
  NOBYPASSRLS;

-- TODO:
-- - confirm whether intdata_test gets separate test-specific login or reuses db_migrator_dev in CI.
-- - enforce distinct DSN names per environment/role in deploy tooling.
