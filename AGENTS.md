# SPF5000 Agent Guide

This repository is an offline-first Raspberry Pi picture-frame product with a FastAPI backend, a React + TypeScript + Vite frontend, DecentDB-backed metadata, filesystem-backed image storage, and design artifacts under `design/`.

## Required reading

Before changing architecture, product scope, persistence behavior, the display pipeline, or deployment/runtime behavior, read:

- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ADR.md`
- the affected ADRs in `design/adr/`

Accepted ADRs are binding design constraints, not optional suggestions.

## Non-negotiable approval rules

- **Never run `git commit`, `git push`, create a pull request, merge, tag, or rewrite git history without explicit user approval in the current conversation.**
- **Never delete user media, cache, data files, or database contents without explicit user approval.**
- **Never change kiosk/runtime behavior on the Pi, deployment wiring, system services, or destructive filesystem operations without explicit user approval.**
- If a request is ambiguous and the action would be high-impact or destructive, stop and ask instead of guessing.

## ADR policy

Meaningful architectural changes require a new ADR in `design/adr/NNNN-title.md`.

Create or update ADR-related docs when a change affects any of the following:

- framework or runtime choices
- persistence model or storage boundaries
- provider abstraction or sync model
- display rendering strategy or `/display` behavior
- deployment/runtime model on the Pi
- authentication, security, or major API boundary decisions

When working with ADRs:

- follow the existing repository format used in `design/adr/*.md`
- determine the next sequential 4-digit ADR number from `design/adr/`
- use concise lowercase-hyphen filenames such as `0009-example-decision.md`
- add a new ADR to supersede or refine a decision instead of rewriting accepted ADR history away
- update `design/SPEC.md`, `README.md`, or related docs when the ADR changes externally visible architecture or workflow

## Architecture guardrails

- Backend layering is `api/routes -> services -> repositories/providers`.
- Keep routes thin, orchestration in services, and persistence explicit in repositories.
- Backend domain models live in `backend/app/models/` as dataclasses; API contracts live in `backend/app/schemas/` as Pydantic models.
- DecentDB stores metadata and settings; the filesystem stores original images and display-sized derivatives.
- Providers must preserve the protocol boundary in `backend/app/providers/base.py`.
- Frontend data access belongs in `frontend/src/api/` using relative `/api/...` paths so the Vite proxy and future single-service deployment both work.
- The fullscreen `/display` route is intentionally separate from the admin shell and must preserve the no-full-black-frame slideshow intent from ADR 0008.

## Validation and documentation expectations

- Prefer small, surgical changes that follow existing patterns.
- Update directly affected documentation when commands, config, API shape, or user-visible behavior change.
- Use existing commands when validating:
  - `make backend`
  - `make frontend`
  - `make test`
  - `cd backend && pytest tests/test_health.py::test_health`
  - `cd frontend && npm run build`
- If validation cannot run because dependencies are not installed, say so explicitly instead of pretending the check passed.

## Agent assets in this repository

Repository-level agent assets are intentionally small and focused:

- `AGENTS.md` — cross-tool repo guidance for GitHub Copilot, Copilot CLI, and Opencode
- `.github/copilot-instructions.md` — Copilot-specific summary of commands, architecture, and conventions
- `.github/instructions/` — targeted instructions for governance and maintaining agent assets
- `.github/agents/` — focused custom agents for backend, frontend, and ADR work
- `.github/skills/` — reusable skills for ADR creation and Playwright-based web testing
- `.vscode/mcp.json` — workspace Playwright MCP configuration

Keep future agent assets repo-specific, portable, and high-signal. Do not turn this repository into a generic plugin marketplace.
