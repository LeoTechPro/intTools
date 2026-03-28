import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
head = subprocess.check_output(
    ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
    text=True,
).strip()
print(head.encode('ascii'))
print(head)
