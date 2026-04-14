# Design: retire remote disposable `intdb` entrypoint

## Decision

Старый wrapper `pg-test-bootstrap.py` сохраняется только как stop-signal, чтобы старые ссылки не вели в удалённый test contour. Рабочий путь на disposable remote DB удаляется из examples и documentation.

## Consequences

- no active CLI entrypoint remains for remote disposable DB;
- migration для operator UX минимальна: старое имя даёт явную ошибку и указывает на local-only replacement.
