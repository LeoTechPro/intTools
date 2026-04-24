import subprocess
remote = '''sudo -u postgres psql -d intdata -Atqc "select pid || '|' || usename || '|' || state || '|' || wait_event_type || '|' || coalesce(wait_event,'') || '|' || left(query,140) from pg_stat_activity where datname = current_database() order by pid; select '---'; select 'specialists|'||count(*) from assess.specialists union all select 'clients|'||count(*) from assess.clients union all select 'diag_results|'||count(*) from assess.diag_results order by 1;"'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:5000])
print(r.stderr[:1000])
