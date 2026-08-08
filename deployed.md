# Deployment status

## Current status

PeopleOps Assistant is not deployed during Phases 1 and 2. The repository provides a production-style Docker image and CI container build. Hosted deployment is the Phase 4 thin-vertical-slice exit criterion and will begin after real MCP discovery and invocation are operational.

## Planned endpoints

- Application URL: pending
- Health endpoint: pending
- Deployment provider: pending free-tier-compatible host

## Cold-start plan

The policy index will be built before deployment or packaged as a validated artifact, loaded once during startup, and measured separately for cold and warm requests. The UI and documentation will explain expected wake-up behavior.
