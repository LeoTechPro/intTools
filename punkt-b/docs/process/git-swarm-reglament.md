# Swarm Git Регламент (opt-in)

## Цель
Стабильная интеграция изменений без скрытых git-операций и без риска потери правок.

## Принцип безопасности
Приоритет N1: **не потерять изменения**. Поэтому любые “гейты”/очереди/автопроцессы допускаются только как явный opt-in.

## NOW (активный режим)
- Обязателен issue-driven flow с machine-wide `lockctl`: каждый коммит должен содержать `Refs #<issue_id>`, а файлы коммита должны иметь активные lease-locks этой же issue.
- Hard gate: новые агентные файлы в `docs/**` запрещены (исключение только через явный owner override `PUNCTB_DOCS_OWNER_APPROVED=YES`).
- Локальные hooks (`git-hooks/commit-msg`, `git-hooks/pre-push`, `git-hooks/post-commit`) обязательны к установке (`npm run issue:hooks:install`).
- CI fallback-аудит `issue-link-audit.yml` запускается на `push`/`pull_request`.
- Никаких автоматических git-действий (rebase/pull/push/commit) без явного запуска команд владельцем/агентом.
- Автоматизированные сценарии (очереди/автопуш/cron), которые выполняют git без прямого запуска команды человеком, должны требовать явного opt-in владельца (`PUNCTB_GIT_APPROVED=YES`).
- Вся обычная разработка и все штатные push идут только через ветку `dev`.
- `main` трактуется как prod-like ветка и обновляется только fast-forward promotion на commit, уже находящийся в `origin/dev`.
- Дополнительные рабочие ветки вне `dev` не используются без явной команды владельца.
- Если используется `safe_autopush.sh`, коммит должен выполняться через `issue_commit.sh` с последующим `issue_audit_local`; push допускается только в `dev`, а sync перед push обязан быть fast-forward only.
- `issue:done` и `issue:push:done` — dev-only команды; для `main` используем release-path (`release:prepare` / `release:main`).
- Для user-visible задач release note живёт в issue (`label: release-note` + `## Release note`), а `docs/release.md` обновляется только из release issue с label `release`.
- GitHub Project поддерживаем через `Status` и worklog в issue; отдельный workflow/секрет для синхронизации `Updation Date` не используем.

## Локи
Локи файлов ведём через `lockctl` по глобальным правилам `/home/leon/.codex/AGENTS.md` и project-specific issue discipline этого репозитория.

## Runbook
Полное описание `lockctl`-based процесса: `docs/process/issue-commit-flow.md`.
