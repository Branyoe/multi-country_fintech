#!/usr/bin/env bash
set -euo pipefail

# ─── Colors ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

step()  { echo -e "\n${CYAN}▶ $1${NC}"; }
ok()    { echo -e "  ${GREEN}✓ $1${NC}"; }
warn()  { echo -e "  ${YELLOW}⚠ $1${NC}"; }
error() { echo -e "  ${RED}✗ $1${NC}"; exit 1; }

# ─── Guards ────────────────────────────────────────────────────────────────
command -v uv >/dev/null 2>&1 || error "uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/"

BACKEND="backend"
MANAGE="uv run --project $BACKEND python $BACKEND/manage.py"

# ─── .env ──────────────────────────────────────────────────────────────────
step "Environment"
if [ ! -f "$BACKEND/.env" ]; then
    cp "$BACKEND/.env.example" "$BACKEND/.env"
    warn ".env created from .env.example — review values before proceeding"
else
    ok ".env already exists"
fi

# ─── Dependencies ──────────────────────────────────────────────────────────
step "Installing dependencies"
uv sync --project "$BACKEND"
ok "Dependencies synced"

# ─── Migrations ────────────────────────────────────────────────────────────
step "Migrations"
$MANAGE migrate
ok "Migrations applied"

# ─── Fixtures ──────────────────────────────────────────────────────────────
step "Fixtures"
FIXTURES_DIR="$BACKEND/fixtures"
if [ -d "$FIXTURES_DIR" ] && ls "$FIXTURES_DIR"/*.json >/dev/null 2>&1; then
    for fixture in "$FIXTURES_DIR"/*.json; do
        $MANAGE loaddata "$fixture"
        ok "Loaded $(basename "$fixture")"
    done
else
    warn "No fixtures found in $FIXTURES_DIR — skipping"
fi

# ─── Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Dev environment ready${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${CYAN}Server${NC}    uv run backend/manage.py runserver"
echo -e "  ${CYAN}Admin${NC}     http://localhost:8000/admin"
echo -e "             admin@dev.local / admin123"
echo -e "  ${CYAN}Tests${NC}     cd backend && uv run pytest users/tests/ -v"
echo ""
