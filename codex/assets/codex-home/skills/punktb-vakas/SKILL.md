---
name: punktb-vakas
description: Safely operate the Punkt B Vakas-tools integration. Use for Vakas configuration diagnostics, registration/report/order ingress validation, guarded event submission, browser-based inventory of bases/services/rules/links, SmartCaptcha blockers, or questions about Vakas connections to Tilda, GetCourse and amoCRM.
---

# Punkt B Vakas

Keep three surfaces separate:

1. Treat existing Vakas rules and links as the production automation already configured in the cabinet.
2. Use `vakas-mcp` only for local diagnostics, payload validation and guarded ingress submission.
3. Use the Vakas web UI for bases, services, rules, links and event journals; do not infer a management API from browser traffic.

Read [references/architecture.md](references/architecture.md) before inventory, browser management or any submission.

## Workflow

1. Start with `vakas_health`. Report only configuration presence and guard status.
2. Use `vakas_validate_event` before considering a submission.
3. Keep submission tools in their default dry-run mode unless the owner explicitly approves the exact write.
4. For an approved dispatch, require all of:
   - exact event type and minimized payload;
   - caller-provided idempotency key;
   - `confirm_write=true` in the same request;
   - allowlisted HTTPS Vakas-tools destination loaded from protected runtime configuration.
5. Return only redacted field names, counts, status codes and validation errors. Never reveal endpoint paths, query strings, cookies, credentials or personal values.

## Browser management

- Use the single project-wide persistent profile `punkt-b`.
- Use encrypted auth entry `punktb-vakas`; keep service credentials separate from `punktb-getcourse` and later CRM entries.
- Do not use or delete the noncanonical `punkt-b-vakas` profile.
- Do not bypass Yandex SmartCaptcha. If it appears, stop and request one manual CAPTCHA pass; do not call the resulting session authorized until the cabinet opens in the shared profile.
- Inventory only what is visible after normal authorization. Do not create, activate, edit or test bases, rules, links or service connections without a separate exact approval.

## Hard boundaries

- Never send a test event as a connectivity check.
- Never mutate amoCRM, GetCourse, Tilda or Vakas management state during diagnostics.
- Never copy a secret endpoint into repo files, prompts, logs, issue comments or tool output.
- Never treat a successful dry-run as proof that Vakas accepted an event or that downstream rules executed.
- Treat process-local deduplication as a safety layer, not a durable cross-process delivery ledger.
