import subprocess
remote = '''set -euo pipefail
set -a
. /int/data/.env
set +a
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "select a.pid || '|' || a.usename || '|' || l.mode || '|' || l.granted::text || '|' || c.relname from pg_locks l join pg_stat_activity a on a.pid=l.pid left join pg_class c on c.oid=l.relation where c.relname in ('users','identities') order by a.pid, c.relname, l.mode;"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:5000])
print(r.stderr[:1000])
