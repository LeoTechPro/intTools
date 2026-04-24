import subprocess
from pathlib import Path

out = []
err = []

def run(label, host, remote_cmd):
    r = subprocess.run(['ssh', host, remote_cmd], capture_output=True)
    out.append(f"=== {label} ===\n{r.stdout.decode('utf-8', 'replace')}__RC__={r.returncode}\n")
    if r.stderr:
        err.append(f"=== {label} STDERR ===\n{r.stderr.decode('utf-8', 'replace')}\n")

host='agents@vds.punkt-b.pro'
run('databases', host, "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, pg_catalog.pg_get_userbyid(datdba) from pg_database where datname in ('punkt_b_prod','punkt_b_legacy_prod') order by datname;\"")
run('sessions', host, "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, usename, coalesce(application_name,''), coalesce(client_addr::text,''), state from pg_stat_activity where usename in ('db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro','db_migrator_dev','db_readonly_dev') order by datname, usename, application_name;\"")
run('memberships', host, "sudo -u postgres psql -d postgres -F '|' -Atqc \"select pg_get_userbyid(member), pg_get_userbyid(roleid) from pg_auth_members where pg_get_userbyid(member) in ('db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro','db_migrator_dev','db_readonly_dev') or pg_get_userbyid(roleid) in ('db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro','db_migrator_dev','db_readonly_dev') order by 1,2;\"")
run('legacy_db_connect', host, "sudo -u postgres psql -d postgres -F '|' -Atqc \"select r.rolname, has_database_privilege(r.rolname, 'punkt_b_legacy_prod', 'CONNECT')::text from pg_roles r where r.rolname in ('db_readonly_prod','db_readonly_legacy','db_migrator_prod','punktb_pro','legacy_backend_role') order by 1;\"")
run('legacy_public_usage', host, "sudo -u postgres psql -d punkt_b_legacy_prod -F '|' -Atqc \"select r.rolname, has_schema_privilege(r.rolname, 'public', 'USAGE')::text from pg_roles r where r.rolname in ('db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro') order by 1;\"")
run('legacy_table_select_sample', host, "sudo -u postgres psql -d punkt_b_legacy_prod -F '|' -Atqc \"with t as (select quote_ident(schemaname)||'.'||quote_ident(tablename) as fqtn from pg_tables where schemaname='public' order by tablename limit 12) select fqtn, has_table_privilege('db_readonly_prod', fqtn, 'SELECT')::text, has_table_privilege('db_readonly_legacy', fqtn, 'SELECT')::text from t;\"")
run('legacy_owned_objects', host, "sudo -u postgres psql -d punkt_b_legacy_prod -F '|' -Atqc \"select 'table', pg_catalog.pg_get_userbyid(relowner), count(*) from pg_class where relkind in ('r','p','v','m','S','f') and pg_catalog.pg_get_userbyid(relowner) in ('legacy_backend_role','db_readonly_legacy','db_readonly_prod','punktb_pro') group by 1,2 union all select 'function', pg_catalog.pg_get_userbyid(proowner), count(*) from pg_proc where pg_catalog.pg_get_userbyid(proowner) in ('legacy_backend_role','db_readonly_legacy','db_readonly_prod','punktb_pro') group by 1,2 union all select 'schema', pg_catalog.pg_get_userbyid(nspowner), count(*) from pg_namespace where pg_catalog.pg_get_userbyid(nspowner) in ('legacy_backend_role','db_readonly_legacy','db_readonly_prod','punktb_pro') group by 1,2 order by 1,2;\"")
run('prod_owned_objects', host, "sudo -u postgres psql -d punkt_b_prod -F '|' -Atqc \"select 'table', pg_catalog.pg_get_userbyid(relowner), count(*) from pg_class where relkind in ('r','p','v','m','S','f') and pg_catalog.pg_get_userbyid(relowner) in ('db_migrator_dev','db_readonly_dev','db_admin_prod','db_migrator_prod','db_readonly_prod','punktb_pro') group by 1,2 union all select 'function', pg_catalog.pg_get_userbyid(proowner), count(*) from pg_proc where pg_catalog.pg_get_userbyid(proowner) in ('db_migrator_dev','db_readonly_dev','db_admin_prod','db_migrator_prod','db_readonly_prod','punktb_pro') group by 1,2 union all select 'schema', pg_catalog.pg_get_userbyid(nspowner), count(*) from pg_namespace where pg_catalog.pg_get_userbyid(nspowner) in ('db_migrator_dev','db_readonly_dev','db_admin_prod','db_migrator_prod','db_readonly_prod','punktb_pro') group by 1,2 order by 1,2;\"")
run('prod_dev_role_privs', host, "sudo -u postgres psql -d punkt_b_prod -F '|' -Atqc \"select grantee, table_schema, privilege_type, count(*) from information_schema.table_privileges where grantee in ('db_migrator_dev','db_readonly_dev') group by grantee, table_schema, privilege_type order by grantee, table_schema, privilege_type;\"")
Path(r'D:\int\tools\.tmp\20260424T151500\punktb_audit.out').write_text('\n'.join(out), encoding='utf-8')
Path(r'D:\int\tools\.tmp\20260424T151500\punktb_audit.err').write_text('\n'.join(err), encoding='utf-8')
print(r'D:\int\tools\.tmp\20260424T151500\punktb_audit.out')
print(r'D:\int\tools\.tmp\20260424T151500\punktb_audit.err')
