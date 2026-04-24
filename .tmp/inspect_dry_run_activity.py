import subprocess
remote = '''set -euo pipefail
set -a
. /int/data/.env
set +a
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "select pid || '|' || state || '|' || wait_event_type || '|' || coalesce(wait_event,'') || '|' || left(query,120) from pg_stat_activity where datname = current_database() and usename in ('agents','supabase_admin') order by pid;"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:4000])
print(r.stderr[:1000])
