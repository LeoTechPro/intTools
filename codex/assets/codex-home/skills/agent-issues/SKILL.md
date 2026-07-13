---
name: agent-issues
description: 'GitHub-first процесс для INT-задач: LeoTechPro/int Issues, OpenSpec requirements, coordctl coordination, evidence/status и closeout.'
metadata:
  knowledge_mode: hybrid-core-reference
  last_verified_at: "2026-07-13"
  refresh_interval_days: 30
  official_sources:
    - https://github.com/LeoTechPro/int/issues
---

# Agent Issues

## Роли источников истины

- OpenSpec хранит requirements и acceptance.
- `LeoTechPro/int` GitHub Issues хранит `INT-*` scope, status, links и material evidence.
- `coordctl` хранит только локальную coordination provenance и overlap warnings.
- Codex tasks являются execution/review plane. Issue status и Project membership не заменяют review или owner approval.
- Git history хранит source changes и проверяемые commit ranges.

## Intake gate

1. Прочитай ближайший `AGENTS.md`, relevant OpenSpec и текущий Git state.
2. Определи один reachable `INT-*` для нетривиальной tracked work.
3. Разрешай issue через workspace resolver и authenticated `gh` против `LeoTechPro/int`.
4. Legacy номера ниже `direct_numbering_from` разрешаются только через tracked `.github/int-legacy-map.json`; новые номера отображаются напрямую.
5. Убедись, что target является Issue, marker соответствует `INT-*`, а status однозначен.

Если `gh`, auth, repository/API, mapping или issue недоступны, fail closed для issue-gated/outward действий. Stale disk cache не является fallback или authorization source.

## Issue state contract

- Открытая issue имеет ровно один label `status:*`.
- `status:backlog`, `status:todo`, `status:in-progress`, `status:in-review`, `status:blocked` отражают активное состояние.
- Закрытая issue с reason `completed` означает `done`.
- Закрытая issue с reason `not planned` означает `cancelled`.
- Project fields являются представлением и не подменяют issue labels/state.
- Не публикуй prompts, reasoning, transcripts, raw task outputs или secrets в Issues/comments.

## Coordination gate

- Перед tracked edits начни или переиспользуй `coordctl` session и зарегистрируй file/region intent для каждого изменяемого пути.
- Используй только file paths/regions, не директории.
- Реальный same-region overlap с другим owner останавливает работу; warning сам по себе не является механическим запретом.
- Перед commit выполни `coordctl commit-scope-check`.
- После завершения, блокировки или handoff освободи свои leases/session.
- Не редактируй coordctl runtime storage вручную.

## Commit и outward gates

- `commit-msg` остаётся offline: проверяет `INT-[1-9][0-9]*`, русский Conventional Commit subject и запрещённые trailers по правилам workspace.
- Issue existence/status проверяется pull/push/outward hooks через `gh`.
- Любой GitHub/API/auth error, PR target, marker mismatch, отсутствующий или неоднозначный status блокирует outward action.
- Наличие issue никогда не разрешает push, publication, deploy, DB apply, production или destructive action.
- Push, publication, deploy, live apply и destructive operations требуют отдельного exact owner approval.
- Не используй stash/reset/restore/clean/rebase/amend или partial-file staging для обхода foreign dirty state.

## Рабочий цикл

1. Inventory: issue, OpenSpec, Git status, reachable related tasks, runtime contour.
2. Coordination: `coordctl` session/intents и overlap check.
3. Mutation: только approved scope, минимальные изменения, foreign state не трогать.
4. Verification: focused tests, strict OpenSpec при spec changes, `git diff --check`, repo gates.
5. Commit: whole-file staging, `coordctl commit-scope-check`, `INT-*` в сообщении.
6. Review: stable exact range, risk-based independent review до outward action.
7. Evidence: один concise comment только для material decision, blocker, candidate range, outward result или closeout.
8. Closeout: фактические SHAs, checks, gaps, risks и следующий approval gate.

## Goal discipline

- Codex goal — continuation state текущей задачи, а не durable source-of-truth.
- Goal не заменяет OpenSpec, GitHub Issue, acceptance, Git history или release notes.
- При pause/handoff durable comment может содержать только `Goal`, `Current state`, `Verified`, `Next action`, links/SHAs и риски.
- Goal завершается только после фактического выполнения stopping condition; близость к budget не является completion.

## Closeout comment template

```md
## Результат
- Scope: ...
- OpenSpec: ...
- Commits/range: ...

## Проверено
- `command` — GREEN

## Не проверено
- ...

## Риски и следующий gate
- ...
```

## Дополнительные материалы

- `references/ledger-rules.md` — границы coordination/evidence.
- `references/session-close-checklist.md` — универсальный closeout checklist.
