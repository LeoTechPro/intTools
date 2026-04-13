# Safe Autopush (queue-based)

## Статус
**Выключен по умолчанию.** Никаких автоматических действий по git не выполняется без явного opt-in владельца.

## Принцип безопасности
Приоритет N1: **не потерять изменения**. Поэтому:
- никаких “тихих” cron-автозапусков;
- запуск только вручную и только opt-in;
- требуются флаги `PUNKTB_GIT_APPROVED=YES` и `ENABLE_SAFE_AUTOPUSH=1`.

## Почему
Старый подход (`git add -A && push main`) создаёт гонки и может запушить чужую незавершённую работу в prod-like ветку.

## Новый подход
Опционально можно использовать `ops/issue/safe_autopush.sh`, который:
- обрабатывает только явные заявки из `~/.codex/tmp/punkt-b/autopush/*.env`;
- требует `ISSUE_ID` в заявке и коммитит только перечисленные файлы через `ops/issue/issue_commit.sh --issue <id>`;
- блокирует пуш, если в рабочем дереве есть несвязанные изменения;
- перед push запускает локальный `codex` CLI review по diff заявленных файлов;
- перед push запускает `bash ops/issue/issue_audit_local.sh --range "<before>..HEAD"`;
- не трогает high-risk пути (`backend/init/migrations`, `.beads`, infra compose);
- перед push делает `git fetch origin dev` и допускает продолжение только если локальный `dev` синхронизируется fast-forward без merge/rebase.
- `TARGET_BRANCH=main` не поддерживается.

Если цель просто интегрировать UI-правки в локальном контуре, по умолчанию используем обычный ручной процесс, без очередей/автопуша.

## Требования для review
- установлен локальный Codex CLI; `safe_autopush.sh` по умолчанию ищет `codex` через `PATH`, а при необходимости путь можно переопределить через `CODEX_BIN`;
- статус `codex login status` должен быть `Logged in`.
- схема ответа review: `templates/codex-review.schema.json`.

## Формат заявки
Пример файла `~/.codex/tmp/punkt-b/autopush/2026-02-13-001.env`:

```bash
REQUEST_ID=shared-org.193.frontend
ISSUE_ID=1037
COMMIT_MESSAGE=web: safe autopush batch
FILES=web/src/App.tsx,web/src/Sidebar.tsx,web/src/lib/api.ts
TARGET_BRANCH=dev
```

## Явное включение (только после прямого “да” владельца)
```bash
PUNKTB_GIT_APPROVED=YES ENABLE_SAFE_AUTOPUSH=1 bash ops/issue/safe_autopush.sh
```

## Статусы заявок
- `.done` — успешно обработано/нечего коммитить.
- `.blocked` — есть несвязанные грязные файлы или Codex-review не прошёл.
- `.rejected` — invalid/forbidden request.

Отчёты ревью сохраняются в `~/.codex/tmp/punkt-b/autopush/reports/` (`<REQUEST_ID>.json` + `<REQUEST_ID>.log`).
