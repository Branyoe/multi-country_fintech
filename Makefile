.PHONY: dev dev-down dev-clean prod prod-down prod-clean logs-dev logs-prod

DC_DEV  = docker compose -f docker-compose.dev.yml
DC_PROD = docker compose -f docker-compose.prod.yml

# ── Dev (hot-reload) ───────────────────────────────────────────────────────────
dev:
	@test -f backend/.env.dev || (cp backend/.env.example backend/.env.dev && echo "→ Created backend/.env.dev")
	$(DC_DEV) up --build

dev-down:
	$(DC_DEV) down

dev-clean:
	$(DC_DEV) down -v

logs-dev:
	$(DC_DEV) logs -f

# ── Prod ───────────────────────────────────────────────────────────────────────
prod:
	@test -f backend/.env.prod || (cp backend/.env.prod.example backend/.env.prod && echo "→ Created backend/.env.prod")
	$(DC_PROD) up --build

prod-down:
	$(DC_PROD) down

prod-clean:
	$(DC_PROD) down -v

logs-prod:
	$(DC_PROD) logs -f
