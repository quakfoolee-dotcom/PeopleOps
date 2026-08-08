# Deployment status

## Current status

PeopleOps Assistant is not deployed during Milestone 1. The repository provides a production-style Docker image and CI container build, while hosted deployment is deliberately scheduled after the real MCP vertical slice is operational.

## Planned endpoints

- Application URL: pending
- Health endpoint: pending
- Deployment provider: pending free-tier-compatible host

## Cold-start plan

The policy index will be built before deployment or packaged as a validated artifact, loaded once during startup, and measured separately for cold and warm requests. The UI and documentation will explain expected wake-up behavior.
