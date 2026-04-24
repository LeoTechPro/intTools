## ADDED Requirements

### Requirement: Public tools frontend contains only safe public documentation

The `/int/tools` repository MUST provide a static public documentation frontend for intData Tools that does not expose private operational data.

#### Scenario: public page is rendered

- **WHEN** a visitor opens the public tools frontend
- **THEN** the page MUST describe intData Tools at a high level
- **AND** it MUST NOT include secrets, private workstation paths, private remote hostnames, private database names, credentials, or personal data
- **AND** it MUST work without a build step or backend service

#### Scenario: public site is deployed

- **WHEN** the public frontend is deployed
- **THEN** it MUST be served from tracked static files in the repository `web/` directory
- **AND** nginx MUST serve the static site for `tools.intdata.pro`
- **AND** the deployment MUST follow the local development, `origin/main`, remote checkout flow
