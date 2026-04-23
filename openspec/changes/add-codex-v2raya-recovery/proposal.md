# Change: Add Codex v2rayA recovery tooling

Owning Multica issue: `INT-321`

## Why

Codex on `agents@vds.intdata.pro` must use the local v2ray/v2rayA proxy path for external network access. The live incident showed `chatgpt.com/backend-api/codex/responses` returning a Cloudflare `403 Forbidden` from `DME` when Codex egress was not using the expected proxy route.

The immediate runtime repair was intentionally host-local, but its health script and runbook must not live in `/home/agents`, hidden Codex state, or ad-hoc `/usr/local` source paths. Reusable Codex recovery source belongs in `/int/tools/codex/**`; host paths may keep only installed runtime copies and systemd unit state.

## What Changes

- Add a repo-owned v2rayA core hook source that strips `quic` sniffing from the generated v2ray config before the core starts.
- Add a repo-owned Codex/v2rayA health script that installs the hook, enforces the v2rayA service drop-in, enforces the Codex app-server proxy environment, restarts unhealthy runtime units, and verifies proxied ChatGPT egress.
- Add a canonical runbook under `/int/tools/codex/docs/runbooks/`.
- Document the new canonical script and runbook in `README.md`.

## Out of Scope

- Changing v2rayA subscription/server credentials.
- Storing runtime state, generated config, secrets, or logs in git.
- Mutating `~/.codex`, `C:\Users\intData\.codex`, or other Codex-owned state.
- Replacing the v2ray/v2rayA stack with a different VPN/proxy technology.

## Acceptance

- Repo-owned source paths exist under `/int/tools/codex/**`.
- Host-local systemd can run the health script from `/int/tools/codex/bin/v2raya-codex-health.sh`.
- v2rayA starts a live v2ray core with local HTTP/SOCKS proxy listeners.
- A proxied request to `https://chatgpt.com/backend-api/codex/responses` no longer returns the incident `403`; `405 Method Not Allowed` for `HEAD` is acceptable because it proves the route reaches the endpoint rather than Cloudflare blocking the egress path.
- Codex `app-server` processes run with `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and local `NO_PROXY` environment.
