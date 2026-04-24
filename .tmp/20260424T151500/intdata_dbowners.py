import subprocess
from pathlib import Path
r = subprocess.run([
    'ssh','agents@vds.intdata.pro',
    "sudo -u postgres psql -d postgres -F '|' -Atqc \"select datname, pg_catalog.pg_get_userbyid(datdba) from pg_database where pg_catalog.pg_get_userbyid(datdba) in ('agents','db_admin_dev','db_migrator_dev','db_readonly_dev','intbridge','intdata_supabase_user','n8n_app','punkt_b_test_user','postfixadmin','webmin','zabbix') order by datname;\""
], capture_output=True)
Path(r'D:\int\tools\.tmp\20260424T151500\intdata_dbowners.out').write_bytes(r.stdout)
Path(r'D:\int\tools\.tmp\20260424T151500\intdata_dbowners.err').write_bytes(r.stderr)
print(r'D:\int\tools\.tmp\20260424T151500\intdata_dbowners.out')
print(r'D:\int\tools\.tmp\20260424T151500\intdata_dbowners.err')
