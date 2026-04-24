import subprocess
from pathlib import Path
script = """#!/usr/bin/env bash
set -euo pipefail
sudo mkdir -p /var/lib/intnexus/sessions /var/lib/intnexus-test/sessions
rename_unit() {
  local old="$1"
  local new="$2"
  if [ -f "/etc/systemd/system/$old" ]; then
    sudo mv "/etc/systemd/system/$old" "/etc/systemd/system/$new"
  fi
}
for old in bridge-bot.service bridge-bot-dev.service intbridge-api-test.service intbridge-worker-whatsapp-test.service intbridge-api.service.disabled intbridge-worker-whatsapp.service.disabled; do
  sudo systemctl stop "$old" >/dev/null 2>&1 || true
done
rename_unit bridge-bot.service nexus-bot.service
rename_unit bridge-bot-dev.service nexus-bot-dev.service
rename_unit intbridge-api-test.service intnexus-api-test.service
rename_unit intbridge-worker-whatsapp-test.service intnexus-worker-whatsapp-test.service
rename_unit intbridge-api.service.disabled intnexus-api.service.disabled
rename_unit intbridge-worker-whatsapp.service.disabled intnexus-worker-whatsapp.service.disabled
for file in /etc/systemd/system/nexus-bot.service /etc/systemd/system/nexus-bot-dev.service /etc/systemd/system/intnexus-api-test.service /etc/systemd/system/intnexus-worker-whatsapp-test.service /etc/systemd/system/intnexus-api.service.disabled /etc/systemd/system/intnexus-worker-whatsapp.service.disabled; do
  [ -f "$file" ] || continue
  sudo perl -0pi -e "s/IntData Bridge/IntData Nexus/g; s/IntBridge/IntNexus/g; s/intbridge-bot/intnexus-bot/g; s#/var/lib/intbridge#/var/lib/intnexus#g; s/bridge-bot-dev/nexus-bot-dev/g; s/bridge-bot/nexus-bot/g; s/intbridge-api/intnexus-api/g; s/intbridge-worker/intnexus-worker/g" "$file"
done
sudo systemctl daemon-reload
mapfile -t DBS < <(sudo -u postgres psql -d postgres -Atqc \"select datname from pg_database where datallowconn and not datistemplate and datname <> 'postgres' order by datname\")
for db in \"${DBS[@]}\"; do
  sudo -u postgres psql -d "$db" -v ON_ERROR_STOP=1 -c \"DROP OWNED BY db_admin_dev, n8n_app, postfixadmin, punkt_b_test_user, zabbix;\" || true
done
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='n8n' AND pid <> pg_backend_pid();\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP DATABASE IF EXISTS n8n;\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS db_admin_dev;\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS n8n_app;\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS postfixadmin;\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS punkt_b_test_user;\"
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \"DROP ROLE IF EXISTS zabbix;\"
sudo -u postgres psql -d postgres -F '|' -Atqc \"select rolname from pg_roles where rolname in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intnexus','intdata_supabase_user','n8n_app','postfixadmin','punkt_b_test_user','webmin','zabbix') order by rolname;\"
sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, pg_catalog.pg_get_userbyid(datdba) from pg_database where datname in ('intdata','intnexusdb','bridge-intdatadb','n8n','webmin') order by datname;\"
systemctl list-unit-files --type=service --no-pager | grep -Ei 'n8n|intbridge|bridge-bot|intnexus|nexus-bot' | head -n 200 || true
"""
r = subprocess.run(['ssh','agents@vds.intdata.pro','bash','-s'], input=script.encode('utf-8'), capture_output=True)
Path(r'D:\int\tools\.tmp\20260424T161500\finish2_stdout.txt').write_bytes(r.stdout)
Path(r'D:\int\tools\.tmp\20260424T161500\finish2_stderr.txt').write_bytes(r.stderr)
print(r.returncode)
print(r'D:\int\tools\.tmp\20260424T161500\finish2_stdout.txt')
print(r'D:\int\tools\.tmp\20260424T161500\finish2_stderr.txt')
