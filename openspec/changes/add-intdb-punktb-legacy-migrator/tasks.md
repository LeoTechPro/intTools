## 1. Specification
- [x] 1.1 Add intdb project migrator requirements.
- [x] 1.2 Validate OpenSpec change.

## 2. Implementation
- [x] 2.1 Add `intdb project-migrate punktb-legacy-assess` orchestration.
- [x] 2.2 Build source export through read-only PostgreSQL CLI profile.
- [x] 2.3 Build target staging/apply SQL for `auth.users`, `assess.clients`, `assess.specialists`, and `assess.diag_results`.
- [x] 2.4 Add explicit dry-run/apply/prod confirmation gates.
- [x] 2.5 Add thin PunktB wrapper entrypoint.

## 3. Verification
- [x] 3.1 Add focused unit tests for SQL generation, profile gates, and command routing.
- [x] 3.2 Run intdb unit tests.
- [x] 3.3 Run read-only source inventory against `punkt_b_legacy_prod`.
- [x] 3.4 Run dry-run rehearsal against `intdata` target.
