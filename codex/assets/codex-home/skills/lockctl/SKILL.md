---
name: lockctl
description: Кроссплатформенный workflow для machine-wide lockctl через MCP (предпочтительно) и CLI fallback.
---

# lockctl

Используй этот skill, когда задача требует file lease-lock в `/int/*`.

## Правила
- Сначала пробуй MCP tools: `lockctl_acquire`, `lockctl_renew`, `lockctl_release_path`, `lockctl_release_issue`, `lockctl_status`, `lockctl_gc`.
- Если MCP недоступен, используй CLI `lockctl` из PATH.
- Не редактируй SQLite/events вручную.

## Минимальный поток
1. `lockctl_acquire` перед файловой мутацией по конкретному файлу.
2. При длинной правке продлевай lease через `lockctl_renew`.
3. После завершения снимай лок через `lockctl_release_path` или `lockctl_release_issue`.
4. Для диагностики используй `lockctl_status`.

## CLI fallback
- Linux/macOS: `lockctl ...`
- Windows PowerShell: `lockctl ...` (или `lockctl.ps1 ...`, если PATH ещё не обновлён)
- Универсально: `python /int/tools/lockctl/lockctl.py ...`
