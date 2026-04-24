import subprocess
hosts=['agents@vds.intdata.pro','agents@vds.punkt-b.pro']
roles=['agents','db_admin_dev','db_migrator_dev','db_readonly_dev','db_admin_prod','db_migrator_prod','db_readonly_prod','db_readonly_legacy','legacy_backend_role','punktb_pro','intdata_supabase_user','intbridge','n8n_app','postfixadmin','webmin','zabbix','supabase_admin','supabase_auth_admin','supabase_functions_admin','supabase_realtime_admin','supabase_replication_admin','supabase_storage_admin','service_role','anon','authenticated','authenticator','pgbouncer']
for host in hosts:
    print('HOST='+host)
    for role in roles:
        remote=f"grep -RInE '\\b{role}\\b' /int 2>/dev/null | head -n 12"
        r=subprocess.run(['ssh','-o','BatchMode=yes',host,remote],capture_output=True,text=True,encoding='utf-8',errors='replace')
        lines=[ln for ln in r.stdout.splitlines() if ln]
        if lines:
            print('ROLE='+role)
            for ln in lines:
                print(ln)
