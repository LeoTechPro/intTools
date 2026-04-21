# Design: Local Windows `/int/data` retirement

The smallest safe routing change is to keep `intdb` local-file semantics but remove implicit Windows discovery of `D:\int\data`.

`intdb` migration commands still need a filesystem checkout for owner scripts such as `init/010_supabase_migrate.sh`, `init/schema.sql`, and `migration_manifest.lock`. An SSH location is not a drop-in replacement for the `--repo` argument, so the tool must not substitute `agents@vds.intdata.pro:/int/data` into `--repo`.

Instead:

- Windows local runs without explicit `--repo`/`INTDB_DATA_REPO` fail with a message that points to `agents@vds.intdata.pro:/int/data`.
- Linux remote runs can still auto-discover sibling `/int/data` next to `/int/tools`.
- Intentional disposable/local testing remains possible by passing an explicit local repo path.
