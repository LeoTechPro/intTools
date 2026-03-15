# React/UI Review Checklist

## Correctness
- Verify state and props flow; avoid hidden coupling.
- Check hooks usage: no conditional hooks, correct dependency arrays, no stale closures.
- Ensure async flows handle loading/error/empty states and cleanup.
- Confirm form validation and submit flows are idempotent when required.

## UX and Accessibility
- Check labels, aria attributes, keyboard navigation, focus management.
- Ensure error messages are visible and actionable.
- Confirm responsive layout and overflow behavior.

## Performance
- Avoid heavy computations in render; use memoization when needed.
- Check list rendering for large datasets (pagination or virtualization).
- Avoid unnecessary re-renders (stable callbacks, memoized components).

## Security and Safety
- Avoid dangerouslySetInnerHTML unless sanitized.
- Ensure user input is validated/sanitized before use.

## Project Fit
- Prefer existing components and styles in web/src/components and web/src/styles.
- Check route definitions in web/src/App.tsx and shared data in web/src/data.
- Avoid new global CSS unless there is a clear justification.

## Tests
- Add or update tests if behavior changes; note missing coverage in report.
