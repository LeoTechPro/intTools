import subprocess
remote = '''set -euo pipefail
set -a
. /int/data/.env
set +a
export PGHOST="$DB_HOST"
export PGPORT="$DB_PORT"
export PGDATABASE="$POSTGRES_DB"
export PGUSER="$POSTGRES_USER"
export PGPASSWORD="$POSTGRES_PASSWORD"
psql -Atqc "select current_database() || '|' || current_user || '|' || current_setting('default_transaction_read_only');"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('RC=' + str(r.returncode))
print(r.stdout[:500])
print(r.stderr[:500])
