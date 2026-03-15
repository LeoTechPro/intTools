# Supabase Edge Functions Review Checklist

## Auth and Access
- Verify request authentication (Authorization header, JWT validation).
- Use service role key only for admin operations with explicit authorization checks.
- Ensure RLS expectations are documented when bypassing with service role.

## Input Validation
- Validate request body and query params (type, required fields, limits).
- Handle malformed JSON and missing fields with clear errors.

## CORS and HTTP
- Handle OPTIONS preflight and set correct CORS headers.
- Return appropriate HTTP status codes and stable error shapes.

## Secrets and Logging
- Read secrets via Deno.env.get; never hardcode secrets.
- Avoid logging PII, tokens, or credentials.

## Reliability
- Use try/catch around external calls and database operations.
- Enforce timeouts and safe defaults for external requests.

## Project Fit
- Keep function code in backend/supabase/functions/<name>/.
- Follow existing patterns for createClient, error responses, and JSON structure.
- If frontend invokes the function, check the caller for auth and error handling.
