# Tailscale Tailnet v1 (local PC / dev / prod)

## Purpose

This runbook defines Tailscale as a private admin and operations channel.
It must not replace existing public ingress (`22/80/443`, reverse-proxy, external domains).

## Scope

- local PC: Windows 11 (`intData-PC`)
- dev host: `vds.intdata.pro`
- prod host: `vds.punkt-b.pro`
- tailnet mode: one owner tailnet
- vpn/proxy-first compatibility: required

## Trust Boundaries (v1)

- `local PC <-> dev`: broad mutual operational access.
- `local PC -> prod`: primary admin/read-first path.
- `dev -> prod`: read-first path only (`ssh`, `icmp`, optional `80/443` smoke).
- `prod -> dev/local PC`: deny by default.
- no default direct tailnet access to prod DB/Redis/admin sidecars.

## Official OpenClaw References

- Gateway: `https://docs.openclaw.ai/gateway`
- Remote Access: `https://docs.openclaw.ai/gateway/remote`
- Security: `https://docs.openclaw.ai/gateway/security`

## Current Baseline (2026-04-13)

- local PC:
  - Tailscale service installed and `Automatic`.
  - state: `Running`.
  - MagicDNS suffix: `tailf0f164.ts.net`.
  - local node DNS: `intdata-pc.tailf0f164.ts.net`.
- dev (`vds.intdata.pro`):
  - `tailscale` installed (`1.96.4`), `tailscaled` enabled.
  - state: `NeedsLogin`.
  - existing proxy contour: `v2raya/v2ray` TPROXY + policy routing.
  - existing bypass already includes `100.64.0.0/10`.
- prod (`vds.punkt-b.pro`):
  - no safe read-only SSH discovery path yet from this workflow.
  - all prod mutations remain blocked until owner-approved access is provided.

## Join and Runtime Commands

### local PC (Windows)

```powershell
$ts = "$env:ProgramFiles\Tailscale\tailscale.exe"
& $ts version
& $ts status --json
```

### dev (Debian/systemd)

```bash
sudo systemctl enable tailscaled
sudo systemctl restart tailscaled
sudo tailscale up --accept-routes=false --accept-dns=false
sudo tailscale status --json
```

Note: if `tailscale up` prints an auth link, complete login in browser with owner account.

### prod (when approved)

```bash
sudo systemctl enable tailscaled
sudo systemctl restart tailscaled
sudo tailscale up --accept-routes=false --accept-dns=false
sudo tailscale status --json
```

Do not continue to SSH/user hardening without explicit owner approval and read-only discovery completed first.

## VPN / Proxy-First Compatibility

### local PC (`Happ` v1 source-of-truth)

- `Happ` routing file: `C:\Users\intData\AppData\Local\Happ\routing.json`
- required direct CIDR:
  - `100.64.0.0/10`
- keep existing RFC1918/local direct ranges unchanged.
- add MagicDNS hostnames after all nodes are joined and names are confirmed from `tailscale status --json`.

### dev (`v2raya/v2ray` contour)

Post-change checks must confirm:

1. `100.64.0.0/10` bypass is still present.
2. Tailscale UDP path is not recaptured by TPROXY chain.
3. `fwmark 0x40/0xc0 -> table 100` behavior still works.

## SSH Access Layer (v1)

- Use standard OpenSSH over tailnet (do not switch to Tailscale SSH by default).
- dev aliases are for `codex`/`openclaw` runtime users, not blanket root.
- prod alias must target restricted read-first user only.
- local PC OpenSSH stays fallback-only unless owner asks to make it primary.

Operator entrypoints in current workspace:

- `ssh vds-intdata-codex`
- `ssh vds-intdata-openclaw`

## Verification Checklist

### Connectivity

```text
local PC <-> dev      : must pass
local PC -> prod      : read-first only
dev -> prod           : read-first only
prod -> dev/local PC  : must not be open by default
```

### Safety Regression

- public `22/80/443` unchanged on dev/prod.
- nginx/docker/public services still reachable from outside.
- no service bind moved to tailnet-only unless explicitly requested.

### Relay Awareness

- if direct P2P is unavailable, DERP relay is acceptable temporary mode.
- record relay region and observed latency in handoff notes.

## Blockers and Stop Conditions

- no read-only SSH path to prod => stop before prod mutation.
- no owner approval for prod user/sudo/firewall change => stop.
- if `Happ` cannot safely represent required bypasses => stop and document manual action.
- if Tailscale introduces ingress regression => rollback Tailscale changes first, then investigate.

## Rollback (Minimal)

### dev/prod

```bash
sudo tailscale down || true
sudo systemctl stop tailscaled || true
```

Optional package rollback only if required by incident policy.

### local PC

```powershell
$ts = "$env:ProgramFiles\Tailscale\tailscale.exe"
& $ts down
```

Do not remove app/config unless explicit owner command requests full uninstall.
