---
name: playwright-testing
description: Планирование, генерация и починка Playwright-тестов.
---

# Playwright Testing Workflow

## Overview

Unified workflow for test planning, test generation, and test healing for Playwright-based QA.

## 1) Plan

Use when the user asks for a test plan or coverage matrix.

Workflow:
1. Ask for target URL/routes/features.
2. Identify critical user journeys, edge cases, and validation rules.
3. Produce a markdown plan with scenarios, steps, and expected results.
4. Save plan to a requested path (default `docs/test-plan.md`).

Plan format:
- Short overview of the area under test.
- Scenarios grouped by feature/flow.
- Each scenario has steps + expected outcomes.
- Assumptions about initial state.

## 2) Generate

Use when the user asks to create Playwright tests from scenarios.

Workflow:
1. Collect inputs: base URL, auth credentials, test data, target pages, expected results.
2. If selectors are unclear, use `npx playwright codegen <url>`.
3. Write a concise test plan (steps + expected results) per scenario.
4. Implement one test per file (ask for target folder; default `tests/` or `e2e/`).
5. Run `npx playwright test <file>` to validate.
6. Iterate until tests pass.

Conventions:
- Use `test.describe` with a clear suite name.
- Test title matches the scenario name.
- Add a short comment before each step.
- Prefer `page.getByRole`, `page.getByLabel`, or `page.getByTestId` over CSS selectors.
- Avoid `networkidle` waits and arbitrary sleeps.

## 3) Heal

Use when tests are flaky or failing.

Workflow:
1. Run the failing tests: `npx playwright test <file>`.
2. Debug with `npx playwright test <file> --debug` or `PWDEBUG=1` if needed.
3. Identify root cause: selectors, timing, data, or app changes.
4. Fix the test using resilient selectors and explicit assertions.
5. Re-run to confirm.
6. If the app is broken and cannot be fixed here, mark with `test.fixme()` and add a short comment.
