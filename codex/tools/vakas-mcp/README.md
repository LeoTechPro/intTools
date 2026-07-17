# Vakas MCP

Guarded MCP client for the documented Vakas-tools ingress webhooks. It validates registration, report and order payloads locally and performs no network request unless `confirm_write=true` and a caller-supplied idempotency key are present.

This is not a management API. Bases, connected services, rules, links and event journals remain browser-managed in the Vakas cabinet.

## Tools

- `vakas_health`: configuration presence and safety posture without endpoint values.
- `vakas_validate_event`: local allowlist and payload validation.
- `vakas_submit_registration`: registration dry-run or guarded dispatch.
- `vakas_submit_report`: webinar report dry-run or guarded dispatch.
- `vakas_submit_order`: order/payment dry-run or guarded dispatch.

## Configuration

Store each full ingress endpoint in a mode `0600` or `0400` file outside the repository. Point the corresponding `VAKAS_*_ENDPOINT_FILE` variable at that file. Inline `VAKAS_*_ENDPOINT` variables are supported for managed secret injection but must not be placed in repo files, shell history or logs.

Only HTTPS destinations on `vakas-tools.ru` or its subdomains are accepted. Endpoint paths, query strings, payload values and response bodies are never returned by MCP tools.

## Local run

```bash
python -m vakas_mcp
```

Run tests without configuring an endpoint; dry-run and validation require no cabinet access.
