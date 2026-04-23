# Design: Codex v2rayA recovery source

## Context

`snap.v2raya.v2raya.service` can remain `active` while the v2ray core process has crashed. In the observed incident, v2ray core `5.28.0` panicked in QUIC sniffing (`github.com/v2fly/v2ray-core/v5/common/protocol/quic.SniffQUIC`), leaving no local proxy listeners for Codex. Because the wrapper service stayed active, systemd did not restart it automatically.

Codex `app-server` also needs an explicit user-service proxy environment. A healthy v2rayA wrapper is not enough if the Codex service starts without `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY`.

## Approach

Keep reusable source in `/int/tools/codex/**` and let host-local systemd consume it directly:

- `codex/bin/v2raya-core-hook-remove-quic.sh` is copied by the health script into snap-visible runtime storage under `/var/snap/v2raya/current/etc/`.
- `codex/bin/v2raya-codex-health.sh` is the canonical health entrypoint for the systemd oneshot service/timer.
- The health script writes only host-local runtime configuration:
  - `/etc/systemd/system/snap.v2raya.v2raya.service.d/10-codex-core-hook.conf`
  - `/home/agents/.config/systemd/user/codex-app-server.service.d/10-v2ray-proxy.conf`
  - installed snap hook copy under `/var/snap/v2raya/current/etc/`

No repo-owned tool writes into Codex home. The Codex user unit drop-in is runtime service configuration, not Codex-owned application state.

## Recovery Checks

The health script treats the following as repair triggers:

- missing v2ray HTTP/SOCKS listeners on `127.0.0.1:20171` and `127.0.0.1:20170`;
- missing `v2ray` core process while `v2raya` wrapper is active;
- generated v2ray config still containing `"quic"`;
- proxied ChatGPT endpoint returning the incident `403` instead of the expected `405` for `HEAD`;
- Codex app-server process missing proxy environment.

## Trade-offs

The script keeps a snap-visible hook copy under `/var/snap/v2raya/current/etc/` because snap confinement made a hook in `/usr/local/sbin` ineffective. That copy is installed runtime state; the source of truth remains `/int/tools/codex/bin/v2raya-core-hook-remove-quic.sh`.
