## 1. RETIRE OLD ENTRYPOINT
- [x] 1.1 Зафиксировать отдельный tooling change package для retirement remote disposable contour.
- [x] 1.2 Убрать рабочий remote bootstrap entrypoint `pg-test-bootstrap.py`.

## 2. DOCS AND PROFILES
- [x] 2.1 Убрать `punktb-test-bootstrap` из `intdb/.env.example`.
- [x] 2.2 Обновить `intdb/README.md`, чтобы он больше не рекламировал retired remote test contour.

## 3. VALIDATION
- [x] 3.1 Проверить diff на отсутствие активных tracked refs на `punkt_b_test`/`intdata_test` как допустимый intdb test target.
