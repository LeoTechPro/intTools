import subprocess
remote = '''docker exec multica-postgres-1 sh -lc "ps -ef | grep '[p]sql -h'"'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:2000])
print(r.stderr[:1000])
