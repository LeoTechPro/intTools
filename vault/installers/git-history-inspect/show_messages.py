import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REL_PATH = 'Resources/systems/Obsidian.md'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True)


commits = git('log', '--follow', '--format=%H%x09%ct%x09%s', '--', REL_PATH).splitlines()
for row in commits:
    commit_id, instant, message = row.split('\t', 2)
    text = git('show', f'{commit_id}:{REL_PATH}')
    line_count = len(text.splitlines())
    byte_count = len(text.encode('utf-8'))
    print(f'{commit_id}\t{instant}\t{message}\t{line_count}\t{byte_count}')
