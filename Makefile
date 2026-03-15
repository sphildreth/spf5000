.PHONY: backend frontend test

backend:
	cd backend && .venv/bin/python -m app

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest
