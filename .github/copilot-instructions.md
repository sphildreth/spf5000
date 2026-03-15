# SPF5000 Copilot Instructions

## Start here

- Read `AGENTS.md` first, then `README.md`, `design/PRD.md`, `design/SPEC.md`, `design/ADR.md`, and any affected ADRs in `design/adr/`.
- Never run `git commit`, `git push`, create a PR, merge, or rewrite history without explicit user approval.
- If a requested change conflicts with an accepted ADR, do not silently diverge. Draft or request a new ADR in `design/adr/NNNN-title.md`.
- Use repo agent assets when helpful:
  - `.github/agents/backend-expert.agent.md`
  - `.github/agents/frontend-expert.agent.md`
  - `.github/agents/adr-writer.agent.md`
  - `.github/skills/create-architectural-decision-record/`
  - `.github/skills/webapp-testing/`
  - `.vscode/mcp.json` for Playwright MCP

## Build, test, and run commands

- Backend commands assume `backend/.venv` is active; frontend commands assume `cd frontend && npm install` has already been run.
- Backend dev server: `make backend`
- Frontend dev server: `make frontend`
- Backend tests: `make test`
- Single backend test: `cd backend && pytest tests/test_health.py::test_health`
- Backend setup + dev run: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload`
- Frontend setup + dev run: `cd frontend && npm install && npm run dev`
- Frontend production build: `cd frontend && npm run build`
- Frontend production preview: `cd frontend && npm run preview`
- Convenience scripts: `scripts/dev-backend.sh`, `scripts/dev-frontend.sh`, `scripts/build-frontend.sh`
- Browser testing: use the Playwright MCP server from `.vscode/mcp.json` together with `.github/skills/webapp-testing/`
- Linting: no repo-defined lint command is currently present in `backend/pyproject.toml` or `frontend/package.json`

## High-level architecture

- SPF5000 is an offline-first Raspberry Pi picture-frame stack: FastAPI backend, React + TypeScript + Vite frontend, DecentDB for metadata/state, and the filesystem for image binaries and cache.
- `backend/app/main.py` creates the FastAPI app, mounts `/api`, enables CORS for the Vite dev origin, and can serve built frontend assets when a repo-root `frontend_dist/` directory exists.
- Backend code follows `routes -> services -> repositories/providers`. Keep routes thin, orchestration in services, and persistence in repositories with explicit SQL rather than introducing an ORM-style data layer.
- Providers live under `backend/app/providers/` and must satisfy the `PhotoProvider` protocol in `backend/app/providers/base.py`. Current scaffolding starts with `LocalFilesProvider`.
- `frontend/src/main.tsx` boots the React app, and `frontend/src/App.tsx` splits the fullscreen `/display` route from the admin shell routes under `AdminLayout`.
- Frontend API access lives in `frontend/src/api/`. Use relative `/api/...` paths through the shared HTTP helper so the Vite proxy in `frontend/vite.config.ts` works in development and the single-service deployment model still works later.
- The intended production/runtime model is a Pi kiosk session that boots Chromium into `/display`; the display path is supposed to stay usable even if the admin UI is unavailable.

## Key conventions

- Treat `design/` as the source of truth for architecture and product intent. Accepted ADRs already lock in the stack choices that matter here: FastAPI, React + TypeScript + Vite, DecentDB for metadata/settings, filesystem-backed image storage, provider abstraction, browser kiosk runtime, and a dual-layer slideshow renderer with no full-black transition.
- Meaningful architectural changes require a new ADR under `design/adr/`; do not rewrite accepted ADR history away.
- Backend domain models are dataclasses in `backend/app/models/`; request/response contracts are separate Pydantic models in `backend/app/schemas/`. When an API shape changes, update both layers together.
- `backend/app/db/connection.py` is responsible for creating `data/` and `cache/`, wrapping commit/rollback, and falling back to `NullConnection` when `decentdb` is unavailable. Preserve that graceful-degradation path when touching persistence.
- Repositories are intentionally thin and currently stubbed with placeholder SQL. Extend the existing layers instead of bypassing services or collapsing provider/repository boundaries.
- Frontend pages currently fetch through small typed wrappers in `frontend/src/api/` rather than issuing `fetch` calls inline. Keep new API calls in that layer.
- Keep TypeScript strictness intact; `frontend/tsconfig.app.json` is configured with `strict: true`.
- If you change slideshow behavior, preserve the `/display` route's independence from the admin layout and follow `design/adr/0008-use-dual-layer-slideshow-renderer-with-slide-transition.md`: preload the next image, keep persistent layers, and avoid visible black frames between images.
- If you change build or deployment wiring, reconcile the current static-asset mismatch between Vite's default `frontend/dist` output and FastAPI's `frontend_dist` mount path.
- Backend tests live under `backend/tests/` and currently use `fastapi.testclient.TestClient`.
- Keep agent-facing assets focused and portable: `AGENTS.md` for repo-wide guidance, `.github/instructions/` for targeted rules, `.github/agents/` for specialized agents, and `.github/skills/` for reusable workflows.
