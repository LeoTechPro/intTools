import subprocess
remote = '''sudo -u postgres psql -d intdata -Atqc "select to_char(updated_at,'YYYY-MM-DD HH24:MI') || '|' || coalesce(first_name,'') || '|' || coalesce(family_name,'') || '|' || coalesce(patronymic,'') || '|' || coalesce(email,'') from assess.clients order by updated_at desc nulls last limit 15;"'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:4000])
print(r.stderr[:800])
