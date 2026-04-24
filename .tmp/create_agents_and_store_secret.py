import secrets
import subprocess
from pathlib import Path

repo = Path(r'D:\int\tools')
env_path = repo / 'intdb' / '.env'
text = env_path.read_text(encoding='utf-8')
secret = secrets.token_urlsafe(24)
remote = f'''set -euo pipefail
set -a
. /int/data/.env
set +a
cat <<'SQL' | docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1
DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agents') THEN ALTER ROLE agents WITH LOGIN SUPERUSER CREATEROLE CREATEDB REPLICATION BYPASSRLS PASSWORD '{secret}'; ELSE CREATE ROLE agents LOGIN SUPERUSER CREATEROLE CREATEDB REPLICATION BYPASSRLS PASSWORD '{secret}'; END IF; END $$;
SQL
docker exec -e PGPASSWORD="{secret}" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U agents -d "$POSTGRES_DB" -Atqc "select current_database() || '|' || current_user || '|' || rolsuper::text from pg_roles where rolname = current_user;"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('REMOTE_RC=' + str(r.returncode))
print(r.stdout[:500])
print(r.stderr[:500])
if r.returncode != 0:
    raise SystemExit(r.returncode)
text = text.replace('INTDB_PROFILE__INTDATA_DEV_ADMIN__PGUSER=db_admin_dev', 'INTDB_PROFILE__INTDATA_DEV_ADMIN__PGUSER=agents')
marker = 'INTDB_PROFILE__INTDATA_DEV_ADMIN__PGPASSWORD='
out = []
for line in text.splitlines():
    if line.startswith(marker):
        out.append(marker + secret)
    else:
        out.append(line)
env_path.write_text('\n'.join(out) + '\n', encoding='utf-8')
print('LOCAL_ENV_UPDATED=1')
