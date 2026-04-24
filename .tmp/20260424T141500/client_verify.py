import subprocess
import sys

def run(label, remote_cmd):
    print(f'=== {label} ===')
    r = subprocess.run(['ssh','agents@vds.intdata.pro', remote_cmd], capture_output=True)
    sys.stdout.write(r.stdout.decode('utf-8', 'replace'))
    sys.stderr.write(r.stderr.decode('utf-8', 'replace'))
    print(f'__RC__={r.returncode}')

run(
    'clients_counts',
    "sudo -u postgres psql -d intdata -Atqc \"select count(*) || '|' || count(*) filter (where nullif(btrim(family_name),'') is not null)::text from assess.clients;\""
)
run(
    'clients_sample',
    "sudo -u postgres psql -d intdata -Atqc \"select user_id::text || '|' || first_name || '|' || coalesce(family_name,'') || '|' || coalesce(patronymic,'') from assess.clients where nullif(btrim(family_name),'') is not null order by updated_at desc nulls last limit 12;\""
)
