import subprocess
from pathlib import Path

ENV_PATH = Path(r'D:\int\tools\intdb\.env')
text = ENV_PATH.read_text(encoding='utf-8')
vals = {}
for line in text.splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    vals[k.strip()] = v.strip()
password = vals['INTDB_PROFILE__INTDATA_DEV_ADMIN__PGPASSWORD']
password_sql = password.replace("'", "''")
script = """#!/usr/bin/env bash
set -euo pipefail
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agents') THEN
    EXECUTE 'CREATE ROLE agents LOGIN SUPERUSER CREATEROLE CREATEDB REPLICATION BYPASSRLS PASSWORD ''__PASS__''';
  ELSE
    EXECUTE 'ALTER ROLE agents WITH LOGIN SUPERUSER CREATEROLE CREATEDB REPLICATION BYPASSRLS PASSWORD ''__PASS__''';
  END IF;
END
$$;
SQL
mapfile -t DBS < <(sudo -u postgres psql -d postgres -Atqc \"select datname from pg_database where datallowconn and not datistemplate and datname <> 'postgres' order by datname\")
for db in \"${DBS[@]}\"; do
  sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"GRANT CONNECT ON DATABASE \\\"$db\\\" TO db_readonly_prod;\"
  sudo -u postgres psql -d \"$db\" -Atqc \"select format('GRANT USAGE ON SCHEMA %I TO db_readonly_prod;', nspname) from pg_namespace where nspname not in ('pg_catalog','information_schema') and nspname not like 'pg_toast%' and nspname not like 'pg_temp_%' order by 1\" | sudo -u postgres psql -d \"$db\" -v ON_ERROR_STOP=1
  sudo -u postgres psql -d \"$db\" -Atqc \"select format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO db_readonly_prod;', nspname) from pg_namespace where nspname not in ('pg_catalog','information_schema') and nspname not like 'pg_toast%' and nspname not like 'pg_temp_%' order by 1\" | sudo -u postgres psql -d \"$db\" -v ON_ERROR_STOP=1
  sudo -u postgres psql -d \"$db\" -Atqc \"select format('GRANT SELECT ON ALL SEQUENCES IN SCHEMA %I TO db_readonly_prod;', nspname) from pg_namespace where nspname not in ('pg_catalog','information_schema') and nspname not like 'pg_toast%' and nspname not like 'pg_temp_%' order by 1\" | sudo -u postgres psql -d \"$db\" -v ON_ERROR_STOP=1
  sudo -u postgres psql -d \"$db\" -Atqc \"select format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT ON TABLES TO db_readonly_prod;', pg_catalog.pg_get_userbyid(nspowner), nspname) from pg_namespace where nspname not in ('pg_catalog','information_schema') and nspname not like 'pg_toast%' and nspname not like 'pg_temp_%' order by 1\" | sudo -u postgres psql -d \"$db\" -v ON_ERROR_STOP=1
  sudo -u postgres psql -d \"$db\" -Atqc \"select format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT ON SEQUENCES TO db_readonly_prod;', pg_catalog.pg_get_userbyid(nspowner), nspname) from pg_namespace where nspname not in ('pg_catalog','information_schema') and nspname not like 'pg_toast%' and nspname not like 'pg_temp_%' order by 1\" | sudo -u postgres psql -d \"$db\" -v ON_ERROR_STOP=1
  sudo -u postgres psql -d \"$db\" -v ON_ERROR_STOP=1 -c \"DROP OWNED BY db_readonly_legacy, db_migrator_dev, db_readonly_dev, db_admin_prod;\"
done
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS db_readonly_legacy;\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS db_migrator_dev;\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS db_readonly_dev;\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS db_admin_prod;\"
sudo -u postgres psql -d postgres -F '|' -Atqc \"select rolname from pg_roles where rolname in ('agents','db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','db_migrator_dev','db_readonly_dev','legacy_backend_role','punktb_pro') order by rolname;\"
""".replace('__PASS__', password_sql)
r = subprocess.run(['ssh','agents@vds.punkt-b.pro','bash','-s'], input=script.encode('utf-8'), capture_output=True)
Path(r'D:\int\tools\.tmp\20260424T160500\stdout.txt').write_bytes(r.stdout)
Path(r'D:\int\tools\.tmp\20260424T160500\stderr.txt').write_bytes(r.stderr)
print(r.returncode)
print(r'D:\int\tools\.tmp\20260424T160500\stdout.txt')
print(r'D:\int\tools\.tmp\20260424T160500\stderr.txt')
