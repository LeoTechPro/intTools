#!/usr/bin/env python3
"""Поиск дубликатов файлов по SHA-1.

По умолчанию сканирует `/int/brain/web/static/diagnostics`, исключая .git, venv, node_modules и build-артефакты.
Завершает работу кодом 0 при отсутствии дублей и 1, если найдены совпадения.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Iterable, Set

DEFAULT_EXCLUDE = {
    '.git',
    'venv',
    '.venv',
    'node_modules',
    '__pycache__',
    '.next',
}


def iter_files(root: Path, exclude: Set[str]) -> Iterable[Path]:
    for path in root.rglob('*'):
        if path.is_dir():
            continue
        parts = {part for part in path.parts}
        if parts & exclude:
            continue
        yield path


def hash_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description='Поиск дубликатов файлов по SHA-1.')
    parser.add_argument(
        'root', nargs='?', default='/int/brain/web/static/diagnostics',
        help='Каталог для проверки (по умолчанию /int/brain/web/static/diagnostics)'
    )
    parser.add_argument(
        '--exclude', '-e', action='append', default=[],
        help='Дополнительные имена каталогов для исключения (можно указывать несколько раз).'
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f'Каталог не найден: {root}', file=sys.stderr)
        return 2

    exclude = DEFAULT_EXCLUDE | set(args.exclude)

    hashes: dict[str, list[Path]] = {}
    for file_path in iter_files(root, exclude):
        digest = hash_file(file_path)
        hashes.setdefault(digest, []).append(file_path)

    duplicates = {digest: paths for digest, paths in hashes.items() if len(paths) > 1}

    if not duplicates:
        print('Дубликаты не обнаружены.')
        return 0

    print('Найдены дубликаты:')
    for paths in duplicates.values():
        for path in paths:
            print(f'  - {path.as_posix()}')
        print()
    return 1


if __name__ == '__main__':
    sys.exit(main())
