# Security Policy

AI Desk is currently a self-hosted beta codebase. Please treat security reports as private until a fix is available.

## Supported Versions

The active `main` branch is the only supported line before the first tagged release.

## Reporting A Vulnerability

Use GitHub private vulnerability reporting or open a private advisory for this repository. Do not create a public issue that includes exploit details, secrets, private endpoints, tokens, logs with credentials, or customer data.

Include:

- affected component or route
- reproduction steps
- expected impact
- relevant configuration
- whether the issue requires local admin, project member, or unauthenticated access

## Security Model In Scope

- Temporal workflow durability and replay safety
- executor permission policies
- workspace allowlists and write gates
- break-glass approval paths
- memory retention and evidence handling
- provider credential boundaries
- notification and audit ledger integrity

## Out Of Scope

Public availability, stars, forks, and community metrics are not security signals. Local development defaults are not production hardening guarantees.
