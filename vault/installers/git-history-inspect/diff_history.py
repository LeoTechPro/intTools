from difflib import unified_diff
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
path_str = 'Resources/systems/Obsidian.md'
path = ROOT / path_str
current = path.read_text(encoding='utf-8')
def load(commit_hex):
    return subprocess.check_output(
        ['git', '-C', str(ROOT), 'show', f'{commit_hex}:{path_str}'],
        text=True,
    )
old_commit = bytes.fromhex(
    '37653034333334343335653835356262393638646561323937376264363336366637313933653738'
).decode('ascii')
old = load(old_commit)
for line in unified_diff(old.splitlines(), current.splitlines(), fromfile='old', tofile='head', lineterm=''): 
    print(line)
