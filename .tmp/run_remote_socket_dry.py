import subprocess
remote = '''set -euo pipefail
cd /tmp/punktb-prod-dev-refresh
python3 - <<'PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('intdb_runtime', '/tmp/punktb-prod-dev-refresh/intdb.py')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
sql = mod._build_punktb_prod_dev_refresh_target_sql(Path('/tmp/punktb-prod-dev-refresh/jsonl-export'), dry_run=True)
Path('/tmp/punktb-prod-dev-refresh/target_refresh_dry_socket.sql').write_text(sql, encoding='utf-8')
print('TARGET_SQL_READY')
PY
sudo -u postgres psql -d intdata -v ON_ERROR_STOP=1 -f /tmp/punktb-prod-dev-refresh/target_refresh_dry_socket.sql
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('RC=' + str(r.returncode))
print(r.stdout[:6000])
print(r.stderr[:2500])
