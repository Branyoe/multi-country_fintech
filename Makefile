.PHONY: dev dev-build dev-down dev-clean prod prod-build prod-down prod-clean logs-dev logs-prod

# ── Dev (hot-reload) ───────────────────────────────────────────────────────────
dev-build:
	docker compose -f docker-compose.dev.yml build

dev:
	docker compose -f docker-compose.dev.yml up

dev-down:
	docker compose -f docker-compose.dev.yml down

dev-clean:
	docker compose -f docker-compose.dev.yml down -v

# ── Prod ───────────────────────────────────────────────────────────────────────
prod-build:
	docker compose -f docker-compose.prod.yml build

prod:
	docker compose -f docker-compose.prod.yml up

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-clean:
	docker compose -f docker-compose.prod.yml down -v

# ── Utilidades ─────────────────────────────────────────────────────────────────
logs-dev:
	docker compose -f docker-compose.dev.yml logs -f

logs-prod:
	docker compose -f docker-compose.prod.yml logs -f
