# Design: intdb-backed PunktB legacy migrator

## Context
The release migration source is `punkt_b_legacy_prod` on `vds.punkt-b.pro`. Its actual legacy schema has `public.clients`, `public.managers`, `public.diagnostics`; client diagnostic results are stored in `public.clients.results jsonb`.

The current dev target shape is `intdata` on `vds.intdata.pro`, exposed through `api.intdata.pro` and used as the model for the upcoming `punkt_b_prod` release target. The target identity model uses `auth.users` and `assess.clients` / `assess.specialists` / `assess.diag_results`.

## Decisions
- `intdb` owns the reusable execution core: profile loading, source export, target staging, dry-run/apply gates, report writing, and prod write guardrails.
- PunktB owns only thin wrappers and mapping defaults.
- The migrator uses native PostgreSQL CLI (`psql`) instead of a Python DB driver, because this matches existing `intdb` dependency boundaries and avoids requiring local `psycopg2`.
- The source profile is always read-only. The target profile must pass the existing `intdb` write guard for apply; dry-run opens a target transaction and rolls it back.
- Client idempotency is based on `lower(trim(email))`. Numeric legacy ids are not target identity; the selected legacy client id is stored in `assess.clients.slug` for search/display compatibility and all merged legacy ids remain in import metadata.
- Specialist idempotency is based on `lower(trim(login))`. Numeric legacy manager ids are not target identity; the selected legacy manager id is stored in `assess.specialists.slug` for search/display compatibility and all merged legacy ids remain in import metadata.
- Duplicate source clients with the same normalized email are merged into one target client. Their result arrays are all attached to the same target client.
- Duplicate target clients by normalized email are a hard preflight error because the migrator cannot choose the canonical target row safely.
- Target slug collisions with a different normalized email are a hard preflight error because numeric slugs are legacy search/display metadata and must not be reassigned silently.
- Diagnostic result ids are deterministic UUIDs derived from `(normalized_email, legacy_client_id, legacy_result_index, diagnostic_id, result_at)`.
- Legacy diagnostic ids are mapped through an explicit PunktB mapping table so legacy ids that shifted in the new catalog do not silently land on the wrong diagnostic.

## Risks / Trade-offs
- Legacy managers do not have a dedicated email column; `login` is treated as the specialist email because it is email-shaped for the observed rows.
- Legacy diagnostics 15-17 are present in result JSON but absent from `public.diagnostics`; they require explicit mapping to target diagnostics.
- There is no target unique index on `assess.clients.email`; uniqueness is enforced by preflight checks and deterministic lookup logic in the migrator.

## Rehearsal Plan
1. Confirm source inventory counts and JSONB shape from `punkt_b_legacy_prod`.
2. Run target preflight against `intdata`.
3. Run `dry-run` migration into `intdata` and verify planned inserted/updated/skipped counts.
4. Only after dry-run succeeds, keep prod apply command ready for release window.
