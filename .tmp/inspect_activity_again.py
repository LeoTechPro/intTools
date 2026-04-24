import subprocess
remote = '''set -euo pipefail
set -a
. /int/data/.env
set +a
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "select pid || '|' || usename || '|' || state || '|' || wait_event_type || '|' || coalesce(wait_event,'') || '|' || left(query,140) from pg_stat_activity where datname = current_database() order by pid;"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:5000])
print(r.stderr[:1000])
