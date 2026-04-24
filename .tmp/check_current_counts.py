import subprocess
remote = '''set -euo pipefail
set -a
. /int/data/.env
set +a
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "select 'specialists|'||count(*) from assess.specialists union all select 'clients|'||count(*) from assess.clients union all select 'diag_results|'||count(*) from assess.diag_results order by 1;"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:1000])
print(r.stderr[:500])
