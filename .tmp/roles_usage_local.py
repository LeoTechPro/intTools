import subprocess
paths=[r'D:\int\tools', r'D:\int\data', r'D:\int\assess', r'D:\int\brain']
roles=['agents','db_admin_dev','db_migrator_dev','db_readonly_dev','db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro','intdata_supabase_user','intbridge','n8n_app','postfixadmin','webmin','zabbix','supabase_admin','supabase_auth_admin','supabase_functions_admin','supabase_realtime_admin','supabase_replication_admin','supabase_storage_admin','service_role','anon','authenticated','authenticator','pgbouncer']
for role in roles:
    cmd=['rg','-n',rf'\b{role}\b',*paths,'-S']
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace')
    lines=[ln for ln in r.stdout.splitlines()[:20]]
    if lines:
        print('ROLE='+role)
        for ln in lines:
            print(ln)
