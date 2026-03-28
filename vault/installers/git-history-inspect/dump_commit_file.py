import sys
import subprocess
from pathlib import Path

if len(sys.argv) != 2:
    print('Usage: dump_commit_file.py <commit-hash>')
    sys.exit(1)

commit_hash = sys.argv[1]
ROOT = Path(__file__).resolve().parents[2]
rel_path = 'Resources/systems/Obsidian.md'
try:
    print(subprocess.check_output(
        ['git', '-C', str(ROOT), 'show', f'{commit_hash}:{rel_path}'],
        text=True,
    ))
except subprocess.CalledProcessError:
    print('commit not found', commit_hash)
    raise SystemExit(1)
