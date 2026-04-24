import subprocess
from pathlib import Path
out=[]
err=[]

def run(label, host, remote_cmd):
    r = subprocess.run(['ssh', host, remote_cmd], capture_output=True)
    out.append(f"=== {label} ===\n{r.stdout.decode('utf-8', 'replace')}__RC__={r.returncode}\n")
    if r.stderr:
        err.append(f"=== {label} STDERR ===\n{r.stderr.decode('utf-8', 'replace')}\n")

host='agents@vds.intdata.pro'
run('sessions', host, "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, usename, coalesce(application_name,''), coalesce(client_addr::text,''), state from pg_stat_activity where usename in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') order by datname, usename, application_name;\"")
run('memberships', host, "sudo -u postgres psql -d postgres -F '|' -Atqc \"select pg_get_userbyid(member), pg_get_userbyid(roleid) from pg_auth_members where pg_get_userbyid(member) in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') or pg_get_userbyid(roleid) in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') order by 1,2;\"")
run('owned_objects', host, "sudo -u postgres psql -d intdata -F '|' -Atqc \"select 'table', pg_catalog.pg_get_userbyid(relowner), count(*) from pg_class where relkind in ('r','p','v','m','S','f') and pg_catalog.pg_get_userbyid(relowner) in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') group by 1,2 union all select 'function', pg_catalog.pg_get_userbyid(proowner), count(*) from pg_proc where pg_catalog.pg_get_userbyid(proowner) in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') group by 1,2 union all select 'schema', pg_catalog.pg_get_userbyid(nspowner), count(*) from pg_namespace where pg_catalog.pg_get_userbyid(nspowner) in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') group by 1,2 order by 1,2;\"")
run('custom_role_privs', host, "sudo -u postgres psql -d intdata -F '|' -Atqc \"select grantee, table_schema, privilege_type, count(*) from information_schema.table_privileges where grantee in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') group by grantee, table_schema, privilege_type order by grantee, table_schema, privilege_type;\"")
run('database_owners', host, "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, pg_catalog.pg_get_userbyid(datdba) from pg_database where datname in ('intdata','postgres') order by datname;\"")
Path(r'D:\int\tools\.tmp\20260424T151500\intdata_audit.out').write_text('\n'.join(out), encoding='utf-8')
Path(r'D:\int\tools\.tmp\20260424T151500\intdata_audit.err').write_text('\n'.join(err), encoding='utf-8')
print(r'D:\int\tools\.tmp\20260424T151500\intdata_audit.out')
print(r'D:\int\tools\.tmp\20260424T151500\intdata_audit.err')
