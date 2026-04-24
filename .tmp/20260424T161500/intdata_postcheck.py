import subprocess
from pathlib import Path
cmds = [
    "sudo -u postgres psql -d postgres -F '|' -Atqc \"select rolname from pg_roles where rolname in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intnexus','intdata_supabase_user','n8n_app','postfixadmin','punkt_b_test_user','webmin','zabbix') order by rolname;\"",
    "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, pg_catalog.pg_get_userbyid(datdba) from pg_database where datname in ('intdata','intnexusdb','bridge-intdatadb','n8n','webmin') order by datname;\"",
    "docker ps -a --format '{{.Names}}|{{.Status}}' | grep -Ei 'n8n|bridge|nexus' | head -n 50 || true",
    "systemctl list-unit-files --type=service --no-pager | grep -Ei 'n8n|intbridge|bridge-bot|intnexus|nexus-bot' | head -n 50 || true",
    "getent passwd deploy || true; getent group devs || true"
]
out=[]
err=[]
for i, cmd in enumerate(cmds, 1):
    r = subprocess.run(['ssh','agents@vds.intdata.pro', cmd], capture_output=True)
    out.append(f'=== check_{i} ===\n{r.stdout.decode("utf-8","replace")}__RC__={r.returncode}\n')
    if r.stderr:
        err.append(f'=== check_{i} STDERR ===\n{r.stderr.decode("utf-8","replace")}\n')
Path(r'D:\int\tools\.tmp\20260424T161500\postcheck.out').write_text('\n'.join(out), encoding='utf-8')
Path(r'D:\int\tools\.tmp\20260424T161500\postcheck.err').write_text('\n'.join(err), encoding='utf-8')
print(r'D:\int\tools\.tmp\20260424T161500\postcheck.out')
print(r'D:\int\tools\.tmp\20260424T161500\postcheck.err')
