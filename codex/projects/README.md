# Codex Project Overlays

Здесь лежат tracked project-specific overlay-файлы для Codex runtime.

Правила:
- этот каталог — канонический источник project overlays вместо ручных файлов в `~/.codex/projects/*`;
- синхронизация в runtime выполняется через `/int/tools/codex/sync_runtime_from_repo.sh`;
- в tracked overlay не храним секреты;
- реальные env-файлы живут в `/int/.runtime/codex-secrets/`.
