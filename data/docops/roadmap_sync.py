#!/usr/bin/env python3
"""
Генерирует сводку по Roadmap из GitHub Project #1 и печатает Markdown‑блоки:
- Топ backlog визий
- Прогресс по waves (milestones)
Требует: gh (CLI) и GH_TOKEN в окружении (или авторизацию gh auth login).
"""
import json
import subprocess
import sys

def gh_json(args):
    out = subprocess.check_output(["gh"] + args, text=True)
    return json.loads(out)

OWNER = "LeoTechRu"
PROJ = "1"
try:
    proj = gh_json(["project", "view", PROJ, "--owner", OWNER, "--format", "json"])
except Exception as e:  # noqa: BLE001
    print(f">> Не удалось прочитать Project: {e}", file=sys.stderr)
    sys.exit(0)

print("### Авто‑сводка Project\n")
print(f"- Project: {proj.get('title')} (#{proj.get('number')})")
# Здесь можно дополнить печатью полей/колонок; изменения в файлы не пишет (read‑only).
