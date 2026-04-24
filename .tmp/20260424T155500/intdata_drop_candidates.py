import subprocess
from pathlib import Path
out=[]
err=[]

def run(label, cmd):
    r = subprocess.run(['ssh','agents@vds.intdata.pro', cmd], capture_output=True)
    out.append(f"=== {label} ===\n{r.stdout.decode('utf-8', 'replace')}__RC__={r.returncode}\n")
    if r.stderr:
        err.append(f"=== {label} STDERR ===\n{r.stderr.decode('utf-8', 'replace')}\n")

run('db_owners', "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, pg_catalog.pg_get_userbyid(datdba) from pg_database where pg_catalog.pg_get_userbyid(datdba) in ('postfixadmin','punkt_b_test_user','zabbix') order by datname;\"")
run('owned_objects', "sudo -u postgres psql -d intdata -F '|' -Atqc \"select 'table', pg_catalog.pg_get_userbyid(relowner), count(*) from pg_class where relkind in ('r','p','v','m','S','f') and pg_catalog.pg_get_userbyid(relowner) in ('postfixadmin','punkt_b_test_user','zabbix') group by 1,2 union all select 'function', pg_catalog.pg_get_userbyid(proowner), count(*) from pg_proc where pg_catalog.pg_get_userbyid(proowner) in ('postfixadmin','punkt_b_test_user','zabbix') group by 1,2 union all select 'schema', pg_catalog.pg_get_userbyid(nspowner), count(*) from pg_namespace where pg_catalog.pg_get_userbyid(nspowner) in ('postfixadmin','punkt_b_test_user','zabbix') group by 1,2 order by 1,2;\"")
run('sessions', "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, usename, count(*) from pg_stat_activity where usename in ('postfixadmin','punkt_b_test_user','zabbix') group by datname, usename order by datname, usename;\"")
Path(r'D:\int\tools\.tmp\20260424T155500\out.txt').write_text('\n'.join(out), encoding='utf-8')
Path(r'D:\int\tools\.tmp\20260424T155500\err.txt').write_text('\n'.join(err), encoding='utf-8')
print(r'D:\int\tools\.tmp\20260424T155500\out.txt')
print(r'D:\int\tools\.tmp\20260424T155500\err.txt')
