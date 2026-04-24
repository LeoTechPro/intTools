# Change: Absorb Roistat core into intTools

## Why

`D:\int\roistat` is no longer intended to remain an independent GitHub project,
but it contains useful Roistat CRM/webhook integration code. The dashboard,
Bitrix monitoring experiments, and old host deploy contour are not reusable
tooling.

## What Changes

- Add `roistat/` as a reusable helper contour under `/int/tools`.
- Keep only Roistat core PHP integration files.
- Keep real config, SQLite/cursor state, and logs in ignored
  `/int/tools/.runtime/roistat/**`.
- Exclude old dashboard, Bitrix monitoring, and `ops/**` deploy/nginx material.

## Issue

- INT-350
