# Obsidian Desktop Config (Repo-managed)

Все канонические конфиги и инструкции для desktop-интеграции Obsidian хранятся в `/git/tools/codex/tools/obsidian-desktop`.
Они открывают root-vault агента `/2brain`.

## Файлы
- `launcher.sh` — запуск Obsidian на vault `/2brain`
- `obsidian-memory.desktop` — desktop entry
- `obsidian.json` — канонический список vault-ов
- `install.sh` — ставит симлинки в `~/.local` и `~/.config`

## Применение
```bash
bash /git/tools/codex/tools/obsidian-desktop/install.sh
```

После запуска:
- `~/.local/bin/obsidian -> /git/tools/codex/tools/obsidian-desktop/launcher.sh`
- `~/.local/share/applications/obsidian-memory.desktop -> /git/tools/codex/tools/obsidian-desktop/obsidian-memory.desktop`
- `~/.config/obsidian/obsidian.json -> /git/tools/codex/tools/obsidian-desktop/obsidian.json`

Это гарантирует, что конфиги и launcher'ы не зависят от `~/.codex/tools`.
