## 1. Spec and scope

- [x] 1.1 Verify current lockctl/gatesctl runtime state defaults on Windows.
- [x] 1.2 Create OpenSpec package for `INT-260`.
- [x] 1.3 Document acceptance for removing implicit Codex-home fallback reads.

## 2. Implementation

- [x] 2.1 Remove automatic `.codex/memories` migration reads from lockctl/gatesctl.
- [x] 2.2 Remove `$CODEX_HOME/var` and `~/.codex/var` secret/env fallbacks.
- [x] 2.3 Require explicit source inputs for IntBrain Codex session memory reads/imports.
- [x] 2.4 Update active docs and skill cards.

## 3. Verification

- [x] 3.1 Update focused unit tests.
- [x] 3.2 Add verifier guard for implicit Codex-home fallback patterns.
- [x] 3.3 Run targeted tests and plugin verifier.
