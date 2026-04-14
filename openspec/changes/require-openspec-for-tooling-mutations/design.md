# Design: mandatory OpenSpec governance for `/int/tools`

## Context

`/int/tools` — не продуктовый shell, а machine-wide ops/tooling contour. Здесь tracked-изменения в wrapper-скриптах, publish flows, launchers, prompts/rules/skills и governance docs влияют на поведение агентов и host automation. Для такого репозитория optional bootstrap-model недостаточна.

## Decision

Вводится единый governance rule:

1. сначала owner-approved OpenSpec change package;
2. затем tracked mutation в repo-owned tooling/process assets;
3. затем validation, commit и дальнейшие repo-level gates.

## Source-of-truth model

- `openspec/specs/process/spec.md` — canonical long-lived process capability.
- `openspec/changes/<change-id>/*` — change-specific proposal/tasks/design/spec-delta.
- `AGENTS.md` и `README.md` — repo-facing mirrors этого процесса, но не самостоятельный источник истины.

## Consequences

- mutate-first path для tracked tooling/process assets становится policy violation;
- governance docs больше нельзя менять отдельно от OpenSpec source;
- новые process changes должны расширять существующую capability `process`, а не создавать параллельные capability directories без owner approval.
