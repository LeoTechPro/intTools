## 1. SPEC-GATE (`add-cross-platform-openspec-entrypoints`)
- [x] 1.1 Зафиксировать process requirement про tracked cross-platform OpenSpec entrypoints.
- [x] 1.2 Зафиксировать owner-approved change package для Linux/Windows launchers.

## 2. IMPLEMENTATION
- [x] 2.1 Добавить `codex/bin/openspec.ps1`.
- [x] 2.2 Добавить `codex/bin/openspec.cmd`.
- [x] 2.3 Обновить `README.md` с командами запуска для Linux и Windows.

## 3. VALIDATION
- [x] 3.1 Прогнать `openspec validate` для нового catalog state.
- [x] 3.2 Проверить diff и selective staging без захвата несвязанного dirty state.
- [x] 3.3 Выполнить локальный commit с change package и launcher-ами.
