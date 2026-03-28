import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
commit_hex = bytes.fromhex(
    '61353239633934363435303839316534303433623038313861356266646237653762343838633361'
).decode('ascii')
try:
    subprocess.check_call(
        ['git', '-C', str(ROOT), 'cat-file', '-e', f'{commit_hex}^{{commit}}'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print('found', commit_hex)
    print(subprocess.check_output(
        ['git', '-C', str(ROOT), 'show', '-s', '--format=%B', commit_hex],
        text=True,
    ).rstrip())
except subprocess.CalledProcessError:
    print('commit missing')
