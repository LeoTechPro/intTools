# INT-343

## Summary

Add a public static frontend for intData Tools at `tools.intdata.pro`.

The site is a lightweight documentation and overview surface for the shared intData tooling layer. It is intentionally static and self-contained so it can be served directly from the checked-out repository without build secrets, private runtime dependencies, or a separate application server.

## Why

intData Tools currently has reusable operator tooling, governance workflows, DBA helpers, runtime helpers, and agent-oriented documentation, but no public entry point that explains the tool layer at a high level.

The public frontend should:

- explain what intData Tools is for
- document the major capability groups without exposing private infrastructure
- give operators a stable, low-risk reference page
- be deployable from the canonical repository checkout

## Scope

- Add a static frontend under `web/`
- Add an nginx vhost config for `tools.intdata.pro`
- Document the public site location in `README.md`
- Keep all public copy free of secrets, private workstation paths, private hostnames, and personal data

## Out of Scope

- Publishing secrets, internal endpoints, private usernames, or private host paths
- Adding a backend or database
- Adding analytics, tracking, or external font/script dependencies
- Reworking existing product documentation

## Acceptance

- `web/index.html` opens as a complete public overview page
- The page references only public, non-sensitive concepts and names
- The site works without a build step
- The nginx config serves the static site for `tools.intdata.pro`
- The change is committed and published through `origin/main`
- The remote checkout can be updated from `origin/main` and the public URL can be smoke-tested
