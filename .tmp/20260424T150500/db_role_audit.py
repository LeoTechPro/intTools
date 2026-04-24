import subprocess
import sys
from pathlib import Path

OUT = Path(r"D:\int\tools\.tmp\20260424T150500\db_role_audit.out")
ERR = Path(r"D:\int\tools\.tmp\20260424T150500\db_role_audit.err")

sections = []
errors = []

def run(label, argv):
    r = subprocess.run(argv, capture_output=True)
    out = r.stdout.decode('utf-8', 'replace')
    err = r.stderr.decode('utf-8', 'replace')
    sections.append(f"=== {label} ===\n{out}__RC__={r.returncode}\n")
    if err:
        errors.append(f"=== {label} STDERR ===\n{err}\n")

# punkt-b host: existence and legacy/prod role checks
run(
    'punktb_databases',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d postgres -Atqc "select datname || ''|'' || pg_catalog.pg_get_userbyid(datdba) from pg_database where datname in (''punkt_b_prod'',''punkt_b_legacy_prod'') order by datname;"']
)
run(
    'punktb_sessions_all',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d postgres -Atqc "select datname || ''|'' || usename || ''|'' || coalesce(application_name,'''') || ''|'' || coalesce(client_addr::text,'''') || ''|'' || state from pg_stat_activity where usename in (''db_admin_prod'',''db_migrator_prod'',''db_readonly_prod'',''db_readonly_legacy'',''legacy_backend_role'',''punktb_pro'',''db_migrator_dev'',''db_readonly_dev'') order by datname, usename, application_name;"']
)
run(
    'punktb_role_memberships',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d postgres -Atqc "select pg_get_userbyid(member) || ''|'' || pg_get_userbyid(roleid) from pg_auth_members where pg_get_userbyid(member) in (''db_admin_prod'',''db_migrator_prod'',''db_readonly_prod'',''db_readonly_legacy'',''legacy_backend_role'',''punktb_pro'',''db_migrator_dev'',''db_readonly_dev'') or pg_get_userbyid(roleid) in (''db_admin_prod'',''db_migrator_prod'',''db_readonly_prod'',''db_readonly_legacy'',''legacy_backend_role'',''punktb_pro'',''db_migrator_dev'',''db_readonly_dev'') order by 1,2;"']
)
run(
    'legacy_db_priv_matrix',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d postgres -Atqc "select r.rolname || ''|'' || has_database_privilege(r.rolname, ''punkt_b_legacy_prod'', ''CONNECT'')::text from pg_roles r where r.rolname in (''db_readonly_prod'',''db_readonly_legacy'',''db_migrator_prod'',''punktb_pro'',''legacy_backend_role'') order by 1;"']
)
run(
    'legacy_public_schema_usage',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d punkt_b_legacy_prod -Atqc "select r.rolname || ''|'' || has_schema_privilege(r.rolname, ''public'', ''USAGE'')::text from pg_roles r where r.rolname in (''db_readonly_prod'',''db_readonly_legacy'',''legacy_backend_role'',''punktb_pro'') order by 1;"']
)
run(
    'legacy_table_select_sample',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d punkt_b_legacy_prod -Atqc "with t as (select quote_ident(schemaname)||''.''||quote_ident(tablename) as fqtn from pg_tables where schemaname=''public'' order by tablename limit 12) select fqtn || ''|'' || has_table_privilege(''db_readonly_prod'', fqtn, ''SELECT'')::text || ''|'' || has_table_privilege(''db_readonly_legacy'', fqtn, ''SELECT'')::text from t;"']
)
run(
    'legacy_owned_objects',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d punkt_b_legacy_prod -Atqc "select ''table'' || ''|'' || pg_catalog.pg_get_userbyid(relowner) || ''|'' || count(*) from pg_class where relkind in (''r'',''p'',''v'',''m'',''S'',''f'') and pg_catalog.pg_get_userbyid(relowner) in (''legacy_backend_role'',''db_readonly_legacy'',''db_readonly_prod'',''punktb_pro'') group by 2 union all select ''function'' || ''|'' || pg_catalog.pg_get_userbyid(proowner) || ''|'' || count(*) from pg_proc where pg_catalog.pg_get_userbyid(proowner) in (''legacy_backend_role'',''db_readonly_legacy'',''db_readonly_prod'',''punktb_pro'') group by 2 union all select ''schema'' || ''|'' || pg_catalog.pg_get_userbyid(nspowner) || ''|'' || count(*) from pg_namespace where pg_catalog.pg_get_userbyid(nspowner) in (''legacy_backend_role'',''db_readonly_legacy'',''db_readonly_prod'',''punktb_pro'') group by 2 order by 1,2;"']
)
run(
    'prod_owned_objects',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d punkt_b_prod -Atqc "select ''table'' || ''|'' || pg_catalog.pg_get_userbyid(relowner) || ''|'' || count(*) from pg_class where relkind in (''r'',''p'',''v'',''m'',''S'',''f'') and pg_catalog.pg_get_userbyid(relowner) in (''db_migrator_dev'',''db_readonly_dev'',''db_admin_prod'',''db_migrator_prod'',''db_readonly_prod'',''punktb_pro'') group by 2 union all select ''function'' || ''|'' || pg_catalog.pg_get_userbyid(proowner) || ''|'' || count(*) from pg_proc where pg_catalog.pg_get_userbyid(proowner) in (''db_migrator_dev'',''db_readonly_dev'',''db_admin_prod'',''db_migrator_prod'',''db_readonly_prod'',''punktb_pro'') group by 2 union all select ''schema'' || ''|'' || pg_catalog.pg_get_userbyid(nspowner) || ''|'' || count(*) from pg_namespace where pg_catalog.pg_get_userbyid(nspowner) in (''db_migrator_dev'',''db_readonly_dev'',''db_admin_prod'',''db_migrator_prod'',''db_readonly_prod'',''punktb_pro'') group by 2 order by 1,2;"']
)
run(
    'prod_dev_role_privs',
    ['ssh','agents@vds.punkt-b.pro',
     'sudo -u postgres psql -d punkt_b_prod -Atqc "select grantee || ''|'' || table_schema || ''|'' || privilege_type || ''|'' || count(*) from information_schema.table_privileges where grantee in (''db_migrator_dev'',''db_readonly_dev'') group by grantee, table_schema, privilege_type order by grantee, table_schema, privilege_type;"']
)
run(
    'punktb_host_refs',
    ['ssh','agents@vds.punkt-b.pro','bash','-lc',
     "cd /int && grep -RInE 'punkt_b_legacy_prod|db_readonly_legacy|legacy_backend_role|db_readonly_prod|db_migrator_dev|db_readonly_dev|punktb_pro' punkt_b tools 2>/dev/null | head -n 320"]
)

# intdata host: role consumers and ownership
run(
    'intdata_sessions_all',
    ['ssh','agents@vds.intdata.pro',
     'sudo -u postgres psql -d postgres -Atqc "select datname || ''|'' || usename || ''|'' || coalesce(application_name,'''') || ''|'' || coalesce(client_addr::text,'''') || ''|'' || state from pg_stat_activity where usename in (''agents'',''db_admin_dev'',''db_migrator_dev'',''db_readonly_dev'',''intbridge'',''intdata_supabase_user'',''n8n_app'',''punkt_b_test_user'',''postfixadmin'',''webmin'',''zabbix'') order by datname, usename, application_name;"']
)
run(
    'intdata_role_memberships',
    ['ssh','agents@vds.intdata.pro',
     'sudo -u postgres psql -d postgres -Atqc "select pg_get_userbyid(member) || ''|'' || pg_get_userbyid(roleid) from pg_auth_members where pg_get_userbyid(member) in (''agents'',''db_admin_dev'',''db_migrator_dev'',''db_readonly_dev'',''intbridge'',''intdata_supabase_user'',''n8n_app'',''punkt_b_test_user'',''postfixadmin'',''webmin'',''zabbix'') or pg_get_userbyid(roleid) in (''agents'',''db_admin_dev'',''db_migrator_dev'',''db_readonly_dev'',''intbridge'',''intdata_supabase_user'',''n8n_app'',''punkt_b_test_user'',''postfixadmin'',''webmin'',''zabbix'') order by 1,2;"']
)
run(
    'intdata_owned_objects',
    ['ssh','agents@vds.intdata.pro',
     'sudo -u postgres psql -d intdata -Atqc "select ''table'' || ''|'' || pg_catalog.pg_get_userbyid(relowner) || ''|'' || count(*) from pg_class where relkind in (''r'',''p'',''v'',''m'',''S'',''f'') and pg_catalog.pg_get_userbyid(relowner) in (''agents'',''db_admin_dev'',''db_migrator_dev'',''db_readonly_dev'',''intbridge'',''intdata_supabase_user'',''n8n_app'',''punkt_b_test_user'',''postfixadmin'',''webmin'',''zabbix'') group by 2 union all select ''function'' || ''|'' || pg_catalog.pg_get_userbyid(proowner) || ''|'' || count(*) from pg_proc where pg_catalog.pg_get_userbyid(proowner) in (''agents'',''db_admin_dev'',''db_migrator_dev'',''db_readonly_dev'',''intbridge'',''intdata_supabase_user'',''n8n_app'',''punkt_b_test_user'',''postfixadmin'',''webmin'',''zabbix'') group by 2 union all select ''schema'' || ''|'' || pg_catalog.pg_get_userbyid(nspowner) || ''|'' || count(*) from pg_namespace where pg_catalog.pg_get_userbyid(nspowner) in (''agents'',''db_admin_dev'',''db_migrator_dev'',''db_readonly_dev'',''intbridge'',''intdata_supabase_user'',''n8n_app'',''punkt_b_test_user'',''postfixadmin'',''webmin'',''zabbix'') group by 2 order by 1,2;"']
)
run(
    'intdata_custom_role_privs',
    ['ssh','agents@vds.intdata.pro',
     'sudo -u postgres psql -d intdata -Atqc "select grantee || ''|'' || table_schema || ''|'' || privilege_type || ''|'' || count(*) from information_schema.table_privileges where grantee in (''agents'',''db_admin_dev'',''db_migrator_dev'',''db_readonly_dev'',''intbridge'',''intdata_supabase_user'',''n8n_app'',''punkt_b_test_user'',''postfixadmin'',''webmin'',''zabbix'') group by grantee, table_schema, privilege_type order by grantee, table_schema, privilege_type;"']
)
run(
    'intdata_host_refs',
    ['ssh','agents@vds.intdata.pro','bash','-lc',
     "cd /int && grep -RInE 'agents|db_admin_dev|db_migrator_dev|db_readonly_dev|intbridge|intdata_supabase_user|n8n_app|punkt_b_test_user|postfixadmin|webmin|zabbix' tools data assess 2>/dev/null | head -n 320"]
)
run(
    'intdata_systemd_refs',
    ['ssh','agents@vds.intdata.pro','bash','-lc',
     "grep -RInE 'intbridge|n8n_app|postfixadmin|zabbix|db_admin_dev|db_migrator_dev|db_readonly_dev|intdata_supabase_user' /etc/systemd /home/agents/.config/systemd /home/intdata/.config/systemd 2>/dev/null | head -n 200"]
)

OUT.write_text('\n'.join(sections), encoding='utf-8')
ERR.write_text('\n'.join(errors), encoding='utf-8')
print(OUT)
print(ERR)
