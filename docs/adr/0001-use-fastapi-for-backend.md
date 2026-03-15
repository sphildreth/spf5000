# ADR 0001: Use FastAPI for Backend

- Status: Accepted
- Date: 2026-03-15

## Context
The project requires a lightweight Python web service for API endpoints, device administration, and future provider integrations.

## Decision
Use FastAPI as the backend framework.

## Consequences
- Strong typing and OpenAPI generation are available.
- Async-capable request handling is available where useful.
- Python ecosystem compatibility is excellent.
- Team can move quickly with simple module structure.
