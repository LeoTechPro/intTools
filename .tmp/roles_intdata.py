import subprocess
remote = '''hostname
whoami
sudo -u postgres psql -d intdata -Atqc "select current_database() || '|' || current_user;"
sudo -u postgres psql -d intdata -Atqc "select rolname || '|' || rolsuper::text || '|' || rolcreaterole::text || '|' || rolcreatedb::text || '|' || rolreplication::text || '|' || rolbypassrls::text from pg_roles order by rolname;"
'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('RC=' + str(r.returncode))
print(r.stdout[:12000])
print(r.stderr[:2000])
