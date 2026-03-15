.PHONY: backend frontend test

backend:
	cd backend && python -m app

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest
