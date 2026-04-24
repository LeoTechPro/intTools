import subprocess
from pathlib import Path
script = """#!/usr/bin/env bash
set -euo pipefail
for db in postgres intdata intnexusdb webmin; do
  sudo -u postgres psql -d "$db" -v ON_ERROR_STOP=1 -c \"DROP OWNED BY zabbix;\" || true
done
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS zabbix;\"
sudo -u postgres psql -d postgres -F '|' -Atqc \"select rolname from pg_roles where rolname in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intnexus','intdata_supabase_user','n8n_app','postfixadmin','punkt_b_test_user','webmin','zabbix') order by rolname;\"
sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, pg_catalog.pg_get_userbyid(datdba) from pg_database where datname in ('intdata','intnexusdb','bridge-intdatadb','n8n','webmin') order by datname;\"
docker ps -a --format '{{.Names}}|{{.Status}}' | grep -Ei 'n8n|bridge|nexus' | head -n 50 || true
systemctl list-unit-files --type=service --no-pager | grep -Ei 'n8n|intbridge|bridge-bot|intnexus|nexus-bot' | head -n 50 || true
"""
r = subprocess.run(['ssh','agents@vds.intdata.pro','bash','-s'], input=script.encode('utf-8'), capture_output=True)
Path(r'D:\int\tools\.tmp\20260424T161500\final_stdout.txt').write_bytes(r.stdout)
Path(r'D:\int\tools\.tmp\20260424T161500\final_stderr.txt').write_bytes(r.stderr)
print(r.returncode)
print(r'D:\int\tools\.tmp\20260424T161500\final_stdout.txt')
print(r'D:\int\tools\.tmp\20260424T161500\final_stderr.txt')
