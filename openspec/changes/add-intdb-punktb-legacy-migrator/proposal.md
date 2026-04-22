# Change: Add intdb-backed PunktB legacy migrator

## Why
INT-290 needs a rehearsable migration path for tomorrow's PunktB cutover. The current `punkt-b/legacy_assess_sync.py` does not match the actual legacy source schema (`public.clients.results jsonb`) or the current target identity schema (`auth.users` + `assess.*`).

## What Changes
- Add an `intdb` project-migration core that can move data between configured PostgreSQL profiles using native PostgreSQL CLI tooling and explicit dry-run/apply gates.
- Add a thin PunktB wrapper that selects the legacy source and dev/prod target profiles without owning migration logic.
- Support PunktB legacy client migration from `punkt_b_legacy_prod.public.clients` into the current `assess.clients` / `assess.diag_results` target shape.
- Make client/person migration idempotent by normalized email, not numeric legacy ids.
- Merge duplicate legacy client rows that share the same normalized email into one target client and attach all legacy results to that target client.
- Decompose legacy `clients.results` JSONB array into target diagnostic result rows with stable deterministic UUIDs and import metadata.
- Require rehearsal against `intdata` dev before prod apply and keep `punkt_b_prod` protected by prod write confirmation.

## Impact
- Affected specs: `intdb`
- Affected code: `intdb/lib/intdb.py`, `intdb/tests/test_intdb.py`, PunktB thin wrapper/docs
- Runtime targets: source `punkt_b_legacy_prod` read-only; rehearsal target `intdata`; release target `punkt_b_prod`
- Issue: `INT-290`
