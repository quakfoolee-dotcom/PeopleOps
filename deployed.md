# Deployment status

## Current status

The Phase 4 application and deployment package are ready. Real MCP discovery and invocation are
operational, the production image serves the UI and API together, and `render.yaml` defines a free
Render web service gated on passing GitHub checks. Creating the external service requires connecting
the GitHub repository to a Render account.

## Planned endpoints

- Application URL: pending
- Health endpoint: pending
- Deployment provider: Render Blueprint prepared; account connection pending

## Cold-start plan

Render's free web service can spin down after 15 minutes without inbound traffic and can take about
one minute to wake. The committed policy corpus and synthetic records are read-only, so Render's
ephemeral filesystem is safe for this phase. Phase 10 will measure cold and warm latency separately.

## Publish procedure

1. In Render, create a new Blueprint and select this repository's `render.yaml` from `main`.
2. Confirm the free plan and create the `peopleops-assistant-demo` service.
3. Wait for the GitHub checks and Render health check to pass.
4. Open the assigned `onrender.com` URL, then verify `/health` reports `status=ok`.
5. Record the application and health URLs above and attach the smoke-test evidence to GitHub issue #5.
