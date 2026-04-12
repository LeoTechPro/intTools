# migration-runner-dev-test

## DEV (`intdata`)

```bash
python /int/tools/intdb/bin/pg-dev-migrate.py --path <sql-file> --write --confirm-target intdata
```

- использовать `db_migrator_dev`.
- `intdata` не дропать и не пересоздавать.

## TEST (`punkt_b_test`)

```bash
python /int/tools/intdb/bin/pg-test-bootstrap.py --path <sql-file> --write --confirm-target punkt_b_test
```

- `punkt_b_test` disposable.
- bootstrap/reset допустимы только в test-контуре.
