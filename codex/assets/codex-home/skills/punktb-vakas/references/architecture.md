# Vakas integration architecture

## Capability boundary

The documented Vakas API accepts three ingress event families: registrations, webinar reports and orders/payments. The documentation describes per-base webhook links and HTTP submission. It does not document a management API for listing or changing bases, connected services, rules, links or event journals.

Official references:

- [Vakas API](https://vakas-tools.ru/docs/api-servisa-vakas-tools/)
- [Vakas to amoCRM](https://vakas-tools.ru/docs/peredacha-dannyh-iz-vakas-tools-v-amocrm/)
- [GetCourse integration](https://vakas-tools.ru/docs/integraciia-getcourse/)
- [Links](https://vakas-tools.ru/docs/sviazki/)

## What Vakas already does

Cabinet rules determine how accepted registrations, reports and orders are stored and forwarded. The amoCRM integration can create or update contacts and deals, map fields, add notes/tags/tasks, change stages and apply duplicate-search or manager assignment settings. Links can receive CRM events, store them in a Vakas base, execute base actions, call a connected service such as GetCourse and optionally write a result back to CRM.

Do not claim that any particular base, service, rule or link is active until it is observed in an authenticated cabinet session.

## What the MCP does

- Report whether each event endpoint is configured without returning its value.
- Validate documented payload field names and bounded scalar values locally.
- Return redacted dry-run summaries without network access by default.
- Dispatch one event only after allowlist validation, `confirm_write=true` and a caller-provided idempotency key.
- Suppress duplicate idempotency keys within one running MCP process and the configured TTL.

The MCP does not list or manage Vakas cabinet objects and does not verify downstream amoCRM/GetCourse effects.

## What remains browser-only

- Inventory or edit bases and per-base links.
- Connect or reconnect amoCRM, GetCourse or other services.
- Inspect, create, activate, disable or edit rules and actions.
- Inspect or create links and their reverse-write actions.
- Review event journals and downstream execution details.

Use the project-wide profile `/home/agents/.hermes/browser-profiles/punkt-b` on VDS or `D:\int\tools\.runtime\browser-profiles\punkt-b` on PC. Use auth entry `punktb-vakas`. The similarly named VDS profile ending in `punkt-b-vakas` is a noncanonical inactive remainder: do not use or delete it.

Yandex SmartCaptcha currently blocks automated VDS login after form fill. One manual CAPTCHA pass in the shared profile is required to establish cookies. Until then, the presence of an encrypted auth entry or profile directory is not proof of an authorized Vakas session.

## Confirmation matrix

| Action | Default | Required confirmation |
| --- | --- | --- |
| Health/config presence | Read-only | None |
| Payload validation | Dry-run, no network | None |
| Registration/report/order dispatch | Blocked | `confirm_write=true` plus exact payload and idempotency key |
| Browser inventory | Read-only after normal login | None if session already authorized |
| Create/edit/activate rules, bases, services or links | Blocked | Separate approval naming the exact object and action |
| Change amoCRM/GetCourse/Tilda | Blocked | Separate approval in the owning system contour |
