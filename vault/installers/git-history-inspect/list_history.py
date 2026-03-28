from datetime import datetime, timezone
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REL_PATH = 'Resources/systems/Obsidian.md'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True)


for row in git('log', '--follow', '--format=%H%x09%ct%x09%s', '--', REL_PATH).splitlines():
    commit_id, instant_raw, message_first = row.split('\t', 2)
    text = git('show', f'{commit_id}:{REL_PATH}')
    line_count = len(text.splitlines())
    byte_count = len(text.encode('utf-8'))
    instant = datetime.fromtimestamp(int(instant_raw), timezone.utc).isoformat()
    print(commit_id, instant, message_first, line_count, byte_count, sep='\t')
