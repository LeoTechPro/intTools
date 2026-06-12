# External Tools Catalog

This page is the human-readable storefront for third-party tools that intData
recommends or studies. A catalog link is not a vendored copy and not an
intData-maintained fork.

## How To Read This Catalog

| Mode | What lives in `/int/tools` | What does not live here | When to use |
| --- | --- | --- | --- |
| Catalog link | Name, upstream URL, short evaluation, install notes, status | Source code, `.env`, sessions, generated files | Default for recommended third-party tools |
| Reference checkout | A separately approved read-only checkout/submodule | Runtime secrets and local state | Only when agents must inspect source offline |
| Owned fork/tool | intData-maintained source, tests, docs, releases | Upstream-only responsibility | Only after explicit decision to maintain it |

## AutoResearchClaw

- Status: catalog link.
- Owner: external upstream.
- Upstream: <https://github.com/aiming-lab/AutoResearchClaw>
- Why it is listed: useful reference for autonomous research-agent workflows and
  evaluation of research automation patterns.
- How to use it: install or clone from upstream when needed; do not treat this
  repository as an intData-owned tool.
- Boundary: no source code, runtime state, sessions, credentials, generated
  artifacts, or local experiments are stored in `/int/tools` for this tool.
- Escalation path: if we need to patch or productize it, create an explicit
  decision package first and choose between a temporary reference checkout and an
  owned fork.

## Claw Code Parity

- Status: catalog link.
- Owner: external upstream.
- Upstream: <https://github.com/ultraworkers/claw-code-parity>
- Why it is listed: useful reference for agent/code parity research and
  compatibility ideas.
- How to use it: inspect or clone from upstream when needed; do not treat this
  repository as an intData-maintained codebase.
- Boundary: no source checkout, runtime state, sessions, or generated artifacts
  are stored in `/int/tools` for this tool.

## Cabinet

- Status: catalog link.
- Owner: external upstream.
- Upstream: <https://github.com/hilash/cabinet>
- Why it is listed: useful reference for Cabinet-style workspace/product
  patterns.
- How to use it: use upstream directly for study; create an owned fork only if
  we decide to maintain changes.
- Boundary: `/int/tools` keeps recommendation metadata only, not a vendored
  checkout.

## PunktB Cabinet Legacy

- Status: catalog link.
- Owner: external upstream.
- Upstream: `git@github.com:punktbDev/cabinet.git`
- Why it is listed: historical Assess/PunktB compatibility reference.
- How to use it: use upstream or a temporary read-only checkout only for
  migration research.
- Boundary: it is not an active intData product repo and should not be wired as
  a master submodule by default.
