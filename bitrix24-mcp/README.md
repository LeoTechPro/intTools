# Bitrix24 MCP

Agent-agnostic MCP server backed by a reproducible registry of the documented
Bitrix24 public REST API. The committed manifest is generated from the official
[`bitrix24/b24restdocs`](https://github.com/bitrix24/b24restdocs) repository and
records its exact commit SHA.

The package keeps the existing typed read-only CRM tools and adds:

- `bitrix24_api_manifest` — safe source/parity metadata;
- `bitrix24_api_methods` — searchable active methods and explicit exclusions;
- `bitrix24_api_call` — universal call for an active manifest server method.

Events, browser JavaScript APIs and `api-reference/outdated/**` pages are
classified but never accepted by the universal REST transport. The caller cannot
override the configured Bitrix24 host or webhook auth path.

The connector does not add its own confirmation flag. Codex, Hermes or another
MCP host remains responsible for write/destructive approval. Repository and live
acceptance use read-only methods only; write-capable entries are contract-tested
without sending mutations.

## Parity update

Check out the official documentation and regenerate the manifest:

```bash
python3 scripts/update_api_manifest.py --docs-root /path/to/b24restdocs
python3 -m unittest discover -s tests -v
```

Credentials remain outside Git. Configure `BITRIX_WEBHOOK_URL` through the host
secret store; diagnostics and errors redact the webhook auth path.

## Configuration

Use an external runtime secret store or a local ignored `.env` file:

```env
BITRIX_WEBHOOK_URL=https://example.bitrix24.ru/rest/1/webhook-code/
```

`BITRIX_WEBHOOK_BASE_URL` is also accepted.

Do not commit real webhook URLs.

## Smoke checks

```powershell
python -m bitrix24_mcp --check
python -m bitrix24_mcp --profile-smoke
```

## Tools

- `bitrix24_health` - safe configuration status.
- `bitrix24_api_manifest` - official source SHA and parity counts.
- `bitrix24_api_methods` - search callable and excluded manifest entries.
- `bitrix24_api_call` - universal active public REST method transport.
- `bitrix24_profile` - current webhook user profile.
- `bitrix24_deal_fields` / `bitrix24_deal_get` / `bitrix24_deal_list`.
- `bitrix24_contact_fields` / `bitrix24_contact_get` / `bitrix24_contact_list`.
- `bitrix24_company_get` / `bitrix24_company_list`.
- `bitrix24_lead_get` / `bitrix24_lead_list`.
- `bitrix24_activity_list` - read CRM activities.
- `bitrix24_timeline_comment_list` - read timeline comments.
- `bitrix24_status_list` - read CRM status dictionaries.
- `bitrix24_raw_read_call` - generic allowlisted read-only REST call.

The legacy typed/raw read surface remains fail-closed. Write-capable methods are
addressable only through `bitrix24_api_call` and are not exercised by live smoke.
