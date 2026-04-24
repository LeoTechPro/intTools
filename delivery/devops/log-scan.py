#!/usr/bin/env python3
import re
import sys
from pathlib import Path

def main() -> int:
    if len(sys.argv) < 2:
        print('usage: log-scan.py <log-file> [pattern]', file=sys.stderr)
        return 2
    log_path = Path(sys.argv[1])
    if not log_path.exists():
        print(f'log file not found: {log_path}', file=sys.stderr)
        return 2
    pattern = sys.argv[2] if len(sys.argv) > 2 else (
        'ERROR|FATAL|CRITICAL|Traceback|Unhandled|panic|OOM|bind: address already in use|Migrations failed|connection refused'
    )
    regex = re.compile(pattern, re.IGNORECASE)
    matches = []
    for idx, line in enumerate(log_path.read_text(errors='ignore').splitlines(), start=1):
        if regex.search(line):
            matches.append((idx, line.strip()))
    if not matches:
        print(f'{log_path.name}: OK — no matched patterns ({pattern})')
        return 0
    print(f'{log_path.name}: FOUND {len(matches)} pattern hits ({pattern})')
    for idx, line in matches[:20]:
        print(f'  line {idx}: {line[:200]}')
    if len(matches) > 20:
        print(f'  ... ещё {len(matches) - 20} совпадений')
    return 1

if __name__ == '__main__':
    sys.exit(main())
