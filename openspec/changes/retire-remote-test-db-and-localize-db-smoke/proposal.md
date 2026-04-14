# Change: Retire remote disposable DB entrypoints from `intdb`

## Why

`intdb` всё ещё содержит historical test-bootstrap path в remote contour `punkt_b_test`/`intdata_test`. Это нарушает новый owner policy:

- remote disposable DB на `vds.intdata.pro` больше не должна быть доступна через active tooling path;
- wrappers/profile examples не должны рекламировать retired contour;
- operator tooling должно явно вести пользователя либо в live dev DB wrappers, либо в новый local-only runner.

## What Changes

- `pg-test-bootstrap.py` перестаёт быть рабочим remote entrypoint и становится tombstone-wrapper с ошибкой о retirement contour;
- `intdb` docs и `.env.example` убирают profile `punktb-test-bootstrap`;
- process delta фиксирует, что tooling не должно сохранять active entrypoint в retired remote disposable contour.

## Scope boundaries

- Scope change — только retirement старого remote test tooling path.
- Новый local runner описывается отдельным change package и capability spec.

## Acceptance (high-level)

- В `/int/tools/intdb` больше нет рабочего entrypoint или profile example для `punkt_b_test`/`intdata_test`.
- Пользователь получает явную ошибку и указание использовать owner-gated local runner.
