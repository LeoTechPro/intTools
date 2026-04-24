import subprocess
remote = '''sudo -u postgres psql -d intdata -Atqc "select count(*) from assess.clients where coalesce(nullif(btrim(first_name),''), nullif(btrim(family_name),''), nullif(btrim(patronymic),'')) is not null; select count(*) from assess.clients where nullif(btrim(family_name),'') is not null; select email || '|' || coalesce(first_name,'') || '|' || coalesce(family_name,'') || '|' || coalesce(patronymic,'') from assess.clients where nullif(btrim(family_name),'') is not null order by updated_at desc nulls last limit 20;"'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:4000])
print(r.stderr[:800])
