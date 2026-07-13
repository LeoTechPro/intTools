# Session close checklist

1. Сверить фактический scope с OpenSpec и текущей GitHub `INT-*` issue.
2. Выполнить repo-specific quality gates и `git diff --check`.
3. Проверить foreign dirty state и не включать/не откатывать его без authority.
4. Для commit использовать whole-file staging, `coordctl commit-scope-check` и русское Conventional Commit сообщение с `INT-*`.
5. Записать в issue только material closeout: SHAs/range, checks, gaps, risks и следующий gate.
6. Обновить status/state только по фактическому результату.
7. Освободить свои coordctl sessions/intents.
8. Не выполнять push, deploy, DB apply, production или destructive action без отдельного exact owner approval.
