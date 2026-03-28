import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
lines = subprocess.check_output(
    ['git', '-C', str(ROOT), 'show-ref', '--head'],
    text=True,
).splitlines()
for line in lines:
    sha, ref = line.split(' ', 1)
    print(ref.encode('utf-8'), sha)
