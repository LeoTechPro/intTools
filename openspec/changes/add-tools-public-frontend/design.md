# Design

## Runtime Shape

The frontend is a static site:

- HTML, CSS, and small vanilla JavaScript only
- no build step
- no server-side rendering
- no API calls
- no third-party runtime dependencies

This keeps the public surface low risk and avoids exposing internal runtime configuration.

## Content Safety

The public page must not include:

- secrets or tokens
- private workstation paths
- private remote hostnames
- private database names
- private user data
- operational credentials or connection strings

The page may describe public concepts such as governance, runtime helpers, database tooling, browser checks, OpenSpec, Multica, and reusable automation patterns.

## Deployment

The static files are tracked under `web/`. The nginx vhost points directly at that tracked directory in the deployed checkout.

The deploy flow remains:

1. develop locally
2. publish to `origin/main`
3. fast-forward the remote checkout
4. install or refresh nginx site configuration
5. validate and reload nginx

## Visual Direction

The design should feel like an operator console and field manual rather than a marketing landing page:

- dense but readable information
- restrained dark surface with high-contrast signals
- strong typographic hierarchy
- no secrets or internal topology
- no decorative dependency on external assets
