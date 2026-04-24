import subprocess
remote = '''set -euo pipefail
set -a
. /int/data/.env
set +a
docker run --rm --network container:multica-postgres-1 -e PGPASSWORD="$POSTGRES_PASSWORD" postgres:17-alpine psql -h "$DB_HOST" -p "$DB_PORT" -U agents -d "$POSTGRES_DB" -Atqc "select current_database() || '|' || current_user || '|' || current_setting('default_transaction_read_only');"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('RC=' + str(r.returncode))
print(r.stdout[:500])
print(r.stderr[:700])
