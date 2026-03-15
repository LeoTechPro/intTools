# Postgres Procedures / Migrations Review Checklist

## Security and RLS
- For SECURITY DEFINER functions, set a safe search_path explicitly.
- Confirm RLS policies cover new tables or access patterns.
- Use auth.uid() / auth.jwt() patterns consistent with existing code.

## Correctness
- Validate function arguments and handle NULLs explicitly.
- Use strictness and volatility attributes appropriately (STRICT, IMMUTABLE/STABLE/VOLATILE).
- Ensure writes are in transactions where consistency matters.

## Performance
- Check for missing indexes on new query paths.
- Avoid unbounded queries in critical paths; add limits where appropriate.

## Migrations
- Ensure migration order and dependencies are correct.
- Avoid destructive changes without explicit approval.
- Document required extensions (e.g., pgcrypto) if newly introduced.

## Project Fit
- Follow existing schema naming conventions (e.g., app.*).
- Keep SQL changes in backend/supabase/migrations unless explicitly directed otherwise.
