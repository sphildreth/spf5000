---
description: 'Repository-wide governance for SPF5000. Apply to all changes so agents respect ADRs, preserve architecture boundaries, and avoid high-impact actions without approval.'
applyTo: '**'
---

# SPF5000 Repository Governance

## Mandatory rules

- Read `AGENTS.md`, `README.md`, `design/PRD.md`, `design/SPEC.md`, `design/ADR.md`, and any affected ADRs before changing architecture or product scope.
- Never run `git commit`, `git push`, create a pull request, merge, tag, or rewrite history without explicit user approval.
- Never delete user media, cache, database contents, or Pi/runtime configuration without explicit user approval.
- Do not silently diverge from an accepted ADR. If the requested change conflicts with an accepted ADR, create a new ADR or explicitly surface the conflict.

## Architecture requirements

- Preserve the backend layering of routes, services, repositories, and providers.
- Keep persistence explicit; do not introduce an ad hoc ORM-style layer.
- Keep frontend API calls in `frontend/src/api/` with relative `/api/...` paths.
- Preserve the dedicated `/display` route and the no-black-frame display intent.

## ADR requirements

- Create a new ADR in `design/adr/NNNN-title.md` for meaningful architecture changes.
- Follow the existing ADR structure already used in `design/adr/*.md`.
- Prefer superseding with a new ADR over rewriting historical ADRs.
- Update related design docs when an ADR changes external behavior or architecture.

## Documentation sync

- Update relevant docs when commands, configuration, API contracts, or user-visible behavior change.
- Treat documentation as part of the feature, not a separate afterthought.
