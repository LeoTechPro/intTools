## ADDED Requirements

### Requirement: Codex agent-host network recovery source MUST live in intTools
The system MUST keep reusable Codex agent-host v2ray/v2rayA recovery scripts and runbooks under `/int/tools/codex/**` instead of user home, Codex-owned state, or ad-hoc host-local source paths.

#### Scenario: Codex v2rayA recovery tooling is installed on an agent host
- **WHEN** a host-local service or timer repairs Codex v2ray/v2rayA egress on `agents@vds.intdata.pro`
- **THEN** the reusable script source is tracked under `/int/tools/codex/bin/`
- **AND** the canonical operator runbook is tracked under `/int/tools/codex/docs/runbooks/`
- **AND** generated runtime config, service drop-ins, snap-visible hook copies, logs, and secrets remain outside git
- **AND** no repo-owned script writes into Codex home as a source-of-truth or hidden runbook location

#### Scenario: Codex network recovery health check runs
- **WHEN** the health check detects missing v2ray listeners, a crashed v2ray core, stale QUIC sniffing config, a blocked proxied ChatGPT route, or missing Codex proxy environment
- **THEN** it repairs host-local runtime wiring from the tracked `/int/tools/codex/**` source
- **AND** it verifies that `https://chatgpt.com/backend-api/codex/responses` reaches the endpoint through the local proxy without the incident Cloudflare `403` response
