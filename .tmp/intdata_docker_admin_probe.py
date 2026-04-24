import subprocess
for sql in [
    "select current_database() || '|' || current_user || '|' || current_setting('default_transaction_read_only');",
    "select has_table_privilege(current_user,'auth.users','INSERT')::text || '|' || has_table_privilege(current_user,'auth.identities','INSERT')::text || '|' || has_table_privilege(current_user,'assess.specialists','DELETE')::text || '|' || has_table_privilege(current_user,'assess.clients','DELETE')::text || '|' || has_table_privilege(current_user,'assess.diag_results','DELETE')::text;",
]:
    remote = f"docker exec intdata-postgres-1 psql -U postgres -d intdata -Atqc \"{sql}\""
    r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
    print('SQL=' + sql)
    print('RC=' + str(r.returncode))
    print(r.stdout[:500])
    print(r.stderr[:500])
