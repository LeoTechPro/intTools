import subprocess
remote = '''cd /tmp/punktb-prod-dev-refresh
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
PY'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:1000])
print(r.stderr[:1000])
raise SystemExit(r.returncode)
