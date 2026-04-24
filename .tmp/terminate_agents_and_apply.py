import subprocess
from pathlib import Path

env_text = Path(r'D:\int\tools\intdb\.env').read_text(encoding='utf-8')
secret = None
for line in env_text.splitlines():
    if line.startswith('INTDB_PROFILE__INTDATA_DEV_ADMIN__PGPASSWORD='):
        secret = line.split('=', 1)[1]
        break
remote = f'''set -euo pipefail
set -a
. /int/data/.env
set +a
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "select pg_terminate_backend(pid) from pg_stat_activity where usename = 'agents' and pid <> pg_backend_pid();"
cd /tmp/punktb-prod-dev-refresh
python3 - <<'PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('intdb_runtime', '/tmp/punktb-prod-dev-refresh/intdb.py')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
sql = mod._build_punktb_prod_dev_refresh_target_sql(Path('/tmp/punktb-prod-dev-refresh/jsonl-export'), dry_run=False)
Path('/tmp/punktb-prod-dev-refresh/target_refresh_apply.sql').write_text(sql, encoding='utf-8')
print('TARGET_SQL_READY')
PY
docker cp /tmp/punktb-prod-dev-refresh/target_refresh_apply.sql multica-postgres-1:/tmp/punktb-prod-dev-refresh/target_refresh_apply.sql
docker exec -e PGPASSWORD="{secret}" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U agents -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f /tmp/punktb-prod-dev-refresh/target_refresh_apply.sql
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" multica-postgres-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "select 'specialists|'||count(*) from assess.specialists union all select 'clients|'||count(*) from assess.clients union all select 'diag_results|'||count(*) from assess.diag_results order by 1;"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('RC=' + str(r.returncode))
print(r.stdout[:7000])
print(r.stderr[:3000])
