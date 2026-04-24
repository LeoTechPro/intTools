import subprocess
import sys

def run(label, host, remote_cmd):
    print(f'=== {label} ===')
    r = subprocess.run(['ssh', host, remote_cmd], capture_output=True, text=True)
    if r.stdout:
        print(r.stdout, end='')
    if r.stderr:
        print(r.stderr, end='', file=sys.stderr)
    print(f'__RC__={r.returncode}')

run(
    'clients_sample_dev',
    'agents@vds.intdata.pro',
    "sudo -u postgres psql -d intdata -Atqc \"select id || '|' || first_name || '|' || coalesce(family_name,'') || '|' || coalesce(patronymic,'') from assess.clients where nullif(btrim(family_name),'') is not null order by updated_at desc nulls last limit 12;\""
)
run(
    'roles_dev_config',
    'agents@vds.intdata.pro',
    "sudo -u postgres psql -d intdata -Atqc \"select rolname || '|' || coalesce(array_to_string(rolconfig, '; '), '') from pg_roles where rolname in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix','anon','authenticated','authenticator','service_role','supabase_admin','supabase_auth_admin','supabase_functions_admin','supabase_read_only_user','supabase_realtime_admin','supabase_replication_admin','supabase_storage_admin','pgbouncer') order by rolname;\""
)
run(
    'roles_prod_config',
    'agents@vds.punkt-b.pro',
    "sudo -u postgres psql -d punkt_b_prod -Atqc \"select rolname || '|' || coalesce(array_to_string(rolconfig, '; '), '') from pg_roles where rolname in ('db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro','db_migrator_dev','db_readonly_dev','anon','authenticated','authenticator','service_role','supabase_admin','supabase_auth_admin','supabase_functions_admin','supabase_read_only_user','supabase_realtime_admin','supabase_replication_admin','supabase_storage_admin') order by rolname;\""
)
run(
    'refs_dev_hosts',
    'agents@vds.intdata.pro',
    "bash -lc \"cd /int && grep -RInE 'db_admin_dev|db_migrator_dev|db_readonly_dev|intbridge|intdata_supabase_user|n8n_app|punkt_b_test_user|postfixadmin|webmin|zabbix|service_role|anon|authenticated|authenticator|supabase_admin|supabase_auth_admin|supabase_functions_admin|supabase_read_only_user|supabase_realtime_admin|supabase_replication_admin|supabase_storage_admin|pgbouncer' tools data assess 2>/dev/null | head -n 240\""
)
run(
    'refs_prod_hosts',
    'agents@vds.punkt-b.pro',
    "bash -lc \"cd /int && grep -RInE 'db_admin_prod|db_migrator_prod|db_readonly_prod|db_readonly_legacy|legacy_backend_role|punktb_pro|db_migrator_dev|db_readonly_dev|service_role|anon|authenticated|authenticator|supabase_admin|supabase_auth_admin|supabase_functions_admin|supabase_read_only_user|supabase_realtime_admin|supabase_replication_admin|supabase_storage_admin' punkt_b tools 2>/dev/null | head -n 240\""
)
