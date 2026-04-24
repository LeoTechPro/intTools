import subprocess
from pathlib import Path
out=[]
err=[]
checks = [
    ('prod_roles', 'agents@vds.punkt-b.pro', "sudo -u postgres psql -d postgres -F '|' -Atqc \"select rolname from pg_roles where rolname in ('agents','db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','db_migrator_dev','db_readonly_dev','legacy_backend_role','punktb_pro') order by rolname;\""),
    ('prod_sessions', 'agents@vds.punkt-b.pro', "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, usename, count(*) from pg_stat_activity where usename in ('agents','db_migrator_prod','db_readonly_prod','legacy_backend_role','punktb_pro') group by datname, usename order by datname, usename;\""),
    ('legacy_read_check', 'agents@vds.punkt-b.pro', "sudo -u postgres psql -d punkt_b_legacy_prod -F '|' -Atqc \"with t as (select quote_ident(schemaname)||'.'||quote_ident(tablename) as fqtn from pg_tables where schemaname='public' order by tablename limit 12) select fqtn, has_table_privilege('db_readonly_prod', fqtn, 'SELECT')::text from t;\""),
    ('intdata_roles', 'agents@vds.intdata.pro', "sudo -u postgres psql -d postgres -F '|' -Atqc \"select rolname from pg_roles where rolname in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intnexus','intdata_supabase_user','n8n_app','postfixadmin','punkt_b_test_user','webmin','zabbix') order by rolname;\""),
    ('intdata_dbs', 'agents@vds.intdata.pro', "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, pg_catalog.pg_get_userbyid(datdba) from pg_database where datname in ('intdata','intnexusdb','bridge-intdatadb','n8n','webmin') order by datname;\""),
    ('intdata_units', 'agents@vds.intdata.pro', "systemctl list-unit-files --type=service --no-pager | grep -Ei 'n8n|intbridge|bridge-bot|intnexus|nexus-bot' | head -n 50 || true"),
    ('intdata_containers', 'agents@vds.intdata.pro', "docker ps -a --format '{{.Names}}|{{.Status}}' | grep -Ei 'n8n|bridge|nexus' | head -n 50 || true"),
]
for label, host, cmd in checks:
    r = subprocess.run(['ssh', host, cmd], capture_output=True)
    out.append(f'=== {label} ===\n{r.stdout.decode("utf-8","replace")}__RC__={r.returncode}\n')
    if r.stderr:
        err.append(f'=== {label} STDERR ===\n{r.stderr.decode("utf-8","replace")}\n')
Path(r'D:\int\tools\.tmp\20260424T162500\out.txt').write_text('\n'.join(out), encoding='utf-8')
Path(r'D:\int\tools\.tmp\20260424T162500\err.txt').write_text('\n'.join(err), encoding='utf-8')
print(r'D:\int\tools\.tmp\20260424T162500\out.txt')
print(r'D:\int\tools\.tmp\20260424T162500\err.txt')
