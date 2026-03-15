---
name: webapp-testing
description: 'Use when testing or debugging the SPF5000 web UI in a real browser, especially the Vite admin app, the fullscreen `/display` route, or flows that benefit from Playwright MCP screenshots, logs, and interaction.'
---

# Web Application Testing

Test and debug the SPF5000 frontend in a real browser.

Prefer the Playwright MCP server configured in `.vscode/mcp.json`. If MCP is unavailable, fall back to a local Playwright setup in Node.js.

## SPF5000 context

- Frontend dev server: `make frontend` or `cd frontend && npm install && npm run dev`
- Backend dev server: `make backend` or `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload`
- Frontend dev server runs on port `5173`
- Backend API runs on port `8000`
- Vite proxies `/api` to the backend
- Important routes:
  - `/` dashboard
  - `/settings`
  - `/sources`
  - `/display`

## When to use this skill

- verify frontend functionality in a real browser
- debug UI regressions or broken interactions
- inspect console errors or browser logs
- capture screenshots for debugging
- validate admin flows and the dedicated display route

## Recommended workflow

1. Confirm the frontend and backend are running
2. Open the relevant route in Playwright
3. Interact with the UI using stable selectors when available
4. Capture screenshots and console logs on failures
5. If the issue involves slideshow/display behavior, test `/display` separately from the admin pages

## Guidelines

- Prefer role-based selectors, labels, or stable IDs over brittle CSS selectors
- Test `/display` independently because it is intentionally separate from the admin shell
- Record console output when UI behavior does not match expectations
- Take screenshots when an interaction or render path fails
- Close the browser cleanly when done

## Bundled helper

Use [`assets/test-helper.js`](./assets/test-helper.js) for reusable helpers such as condition polling, console capture, and screenshot naming.
