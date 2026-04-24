import subprocess
from pathlib import Path
out=[]
err=[]

def run(label, host, remote_cmd):
    r = subprocess.run(['ssh', host, remote_cmd], capture_output=True)
    out.append(f"=== {label} ===\n{r.stdout.decode('utf-8', 'replace')}__RC__={r.returncode}\n")
    if r.stderr:
        err.append(f"=== {label} STDERR ===\n{r.stderr.decode('utf-8', 'replace')}\n")

run('legacy_sessions_detail','agents@vds.punkt-b.pro',"sudo -u postgres psql -d postgres -F '|' -Atqc \"select pid, datname, usename, coalesce(application_name,''), coalesce(client_addr::text,''), backend_start from pg_stat_activity where datname='punkt_b_legacy_prod';\"")
run('punktb_session_counts','agents@vds.punkt-b.pro',"sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, usename, count(*) from pg_stat_activity where usename in ('db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro','db_migrator_dev','db_readonly_dev') group by datname, usename order by datname, usename;\"")
run('intdata_session_counts','agents@vds.intdata.pro',"sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, usename, count(*) from pg_stat_activity where usename in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') group by datname, usename order by datname, usename;\"")
run('legacy_host_refs','agents@vds.punkt-b.pro',"grep -RInE 'POSTGRES_USER|DB_USER|DATABASE_URL|punkt_b_legacy_prod|legacy_backend_role' /int/punkt_b_legacy /int/punkt_b 2>/dev/null | head -n 240")
Path(r'D:\int\tools\.tmp\20260424T151500\live_counts_probe.out').write_text('\n'.join(out), encoding='utf-8')
Path(r'D:\int\tools\.tmp\20260424T151500\live_counts_probe.err').write_text('\n'.join(err), encoding='utf-8')
print(r'D:\int\tools\.tmp\20260424T151500\live_counts_probe.out')
print(r'D:\int\tools\.tmp\20260424T151500\live_counts_probe.err')
