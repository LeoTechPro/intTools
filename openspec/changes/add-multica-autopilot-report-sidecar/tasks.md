## 1. Spec
- [x] 1.1 Add OpenSpec change package for the sidecar.
- [x] 1.2 Define fail-closed target mapping and delivery behavior.

## 2. Implementation
- [x] 2.1 Add deterministic sidecar CLI in `delivery/bin/`.
- [x] 2.2 Use Multica CLI comments and Probe outbox CLI boundary.
- [x] 2.3 Keep dedupe/runtime state outside git.
- [x] 2.4 Document the operator command and runtime variables.

## 3. Validation
- [x] 3.1 Add unit tests for missing mapping, dedupe, comment failure, and Probe failure.
- [x] 3.2 Run targeted unit tests.
- [ ] 3.3 Run live smoke against `6053a2d3-682f-48ca-a76a-ba1f09faa5e5` after owner confirms the master issue mapping is ready for production delivery.
