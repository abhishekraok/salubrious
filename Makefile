.PHONY: server client dev seed db-reset

server:
	cd server && uvicorn app.main:app --reload --port 8000

client:
	cd client && npm run dev

dev:
	@echo "Run 'make server' and 'make client' in separate terminals"

seed:
	cd server && python -m app.seed

db-reset:
	rm -f server/salubrious.db
	cd server && python -m app.seed
