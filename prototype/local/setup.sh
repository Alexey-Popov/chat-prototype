#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-time local setup (no Docker required)
#
# Run once from the prototype/ directory:
#   cd prototype && bash local/setup.sh
#
# What it does:
#   1. Checks prerequisites (Python 3.10+, Node 18+, PostgreSQL)
#   2. Creates three local databases (sourcedb, vectordb, systemdb)
#   3. Enables pgvector extension in vectordb
#   4. Creates Python venvs and installs deps for all three services
#   5. Runs Alembic migrations (core, chunking) and create_all (admin)
#   6. Seeds source_db with test fintech data
#   7. Installs npm deps for chat-ui
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[setup]${NC} $*"; }
success() { echo -e "${GREEN}[setup]${NC} ✓ $*"; }
warn()    { echo -e "${YELLOW}[setup]${NC} ⚠ $*"; }
die()     { echo -e "${RED}[setup]${NC} ✗ $*" >&2; exit 1; }

# ── .env ──────────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$SCRIPT_DIR/.env.local" "$ENV_FILE"
    warn "Created $ENV_FILE from .env.local — edit it to set OPENAI_API_KEY, JWT_SECRET, etc."
fi
# shellcheck source=/dev/null
set -a; source "$ENV_FILE"; set +a

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-user}"
PG_PASS="${PG_PASS:-password}"

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
info "Checking prerequisites…"

# Python ≥ 3.10
if ! command -v python3 &>/dev/null; then
    die "python3 not found. Install Python 3.10+ and retry."
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor:02d}')")
[[ "$PY_VER" -ge 310 ]] || die "Python 3.10+ required (found $(python3 --version))."
success "$(python3 --version)"

# Node ≥ 18
if ! command -v node &>/dev/null; then
    die "node not found. Install Node 18+ (e.g. 'brew install node' or nvm) and retry."
fi
NODE_MAJOR=$(node -e "process.stdout.write(process.version.slice(1).split('.')[0])")
[[ "$NODE_MAJOR" -ge 18 ]] || die "Node 18+ required (found $(node --version))."
success "Node $(node --version)"

# PostgreSQL client
if ! command -v psql &>/dev/null; then
    echo ""
    echo "  psql not found. Install PostgreSQL 14+, for example:"
    echo "    brew install postgresql@16          # macOS"
    echo "    sudo apt install postgresql-client  # Debian/Ubuntu"
    echo ""
    die "psql not found."
fi
success "$(psql --version)"

# PostgreSQL server reachable
if ! pg_isready -q -h "$PG_HOST" -p "$PG_PORT" 2>/dev/null; then
    echo ""
    echo "  PostgreSQL is not running on $PG_HOST:$PG_PORT. Start it, then retry:"
    echo "    brew services start postgresql@16   # macOS Homebrew"
    echo "    sudo systemctl start postgresql     # Linux"
    echo ""
    die "PostgreSQL not reachable at $PG_HOST:$PG_PORT."
fi
success "PostgreSQL reachable at $PG_HOST:$PG_PORT"

# ── Helper: run SQL as superuser (tries current OS user, then postgres) ────────
_psql_super() {
    local db="${1:-postgres}"; shift
    local sql="$*"
    if psql -q -h "$PG_HOST" -p "$PG_PORT" -U "$(whoami)" -c "$sql" "$db" 2>/dev/null; then
        return 0
    fi
    psql -q -h "$PG_HOST" -p "$PG_PORT" -U postgres -c "$sql" "$db"
}

# ── 2. Role + databases ───────────────────────────────────────────────────────
info "Creating PostgreSQL role '$PG_USER'…"
_psql_super postgres "DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$PG_USER') THEN
    CREATE ROLE \"$PG_USER\" WITH LOGIN PASSWORD '$PG_PASS';
  END IF;
END \$\$;" 2>/dev/null || warn "Could not create role (may already exist)."

for DBNAME in sourcedb vectordb systemdb; do
    info "Creating database '$DBNAME'…"
    if _psql_super postgres "SELECT 1 FROM pg_database WHERE datname = '$DBNAME'" \
        | grep -q 1 2>/dev/null; then
        warn "  '$DBNAME' already exists — skipping."
    else
        _psql_super postgres "CREATE DATABASE \"$DBNAME\" OWNER \"$PG_USER\";"
        success "  Created '$DBNAME'"
    fi
done

# pgvector
info "Enabling pgvector extension in vectordb…"
if _psql_super vectordb "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
    success "pgvector extension enabled"
else
    warn "Could not enable pgvector. Install it first:"
    warn "  brew install pgvector          # macOS"
    warn "  sudo apt install postgresql-16-pgvector  # Ubuntu"
    warn "Chunking service will fail at runtime without it."
fi

# pgcrypto (used by core migrations for gen_random_uuid)
_psql_super systemdb "CREATE EXTENSION IF NOT EXISTS pgcrypto;" 2>/dev/null || true
_psql_super vectordb  "CREATE EXTENSION IF NOT EXISTS pgcrypto;" 2>/dev/null || true

# ── 3. Python virtualenvs ─────────────────────────────────────────────────────
setup_venv() {
    local svc="$1"
    local dir="$PROTO_DIR/$svc"
    info "Setting up $svc virtualenv…"
    [[ -d "$dir/.venv" ]] || python3 -m venv "$dir/.venv"
    # shellcheck source=/dev/null
    source "$dir/.venv/bin/activate"
    pip install --upgrade pip -q
    pip install -e "$dir[dev]" -q
    pip install psycopg2-binary -q   # needed for seed + alembic sync runner
    deactivate
    success "$svc venv ready"
}

setup_venv core
setup_venv chunking
setup_venv admin

# ── 4. Database migrations ────────────────────────────────────────────────────
SYS_DSN_SYNC="postgresql://$PG_USER:$PG_PASS@$PG_HOST:$PG_PORT/systemdb"
SYS_DSN_ASYNC="postgresql+asyncpg://$PG_USER:$PG_PASS@$PG_HOST:$PG_PORT/systemdb"
VEC_DSN_ASYNC="postgresql+asyncpg://$PG_USER:$PG_PASS@$PG_HOST:$PG_PORT/vectordb"

info "Running core Alembic migrations → systemdb…"
(
    cd "$PROTO_DIR/core"
    source .venv/bin/activate
    SYSTEM_DSN="$SYS_DSN_SYNC" \
    VECTOR_DSN="$VEC_DSN_ASYNC" \
    JWT_SECRET="${JWT_SECRET:-temp-secret-32-chars-placeholder!}" \
    OPENAI_API_KEY="${OPENAI_API_KEY:-temp}" \
    OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:-temp}" \
    OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-temp}" \
        alembic upgrade head
    deactivate
)
success "core migrations applied"

info "Running chunking Alembic migrations → vectordb…"
(
    cd "$PROTO_DIR/chunking"
    source .venv/bin/activate
    VECTOR_DSN="$VEC_DSN_ASYNC" \
        alembic upgrade head
    deactivate
)
success "chunking migrations applied"

info "Creating admin schema (SQLAlchemy create_all) → systemdb…"
(
    cd "$PROTO_DIR/admin"
    source .venv/bin/activate
    SYSTEM_DSN="$SYS_DSN_ASYNC" \
    JWT_SECRET="${JWT_SECRET:-temp-secret-32-chars-placeholder!}" \
    python3 - <<'PYEOF'
import asyncio, os
from app.db import engine
from app.models.system import Base

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("  admin schema ready")

asyncio.run(main())
PYEOF
    deactivate
)
success "admin schema ready"

# ── 5. Seed source_db ─────────────────────────────────────────────────────────
info "Seeding sourcedb with test fintech data…"
(
    source "$PROTO_DIR/core/.venv/bin/activate"
    SOURCE_DSN="host=$PG_HOST port=$PG_PORT dbname=sourcedb user=$PG_USER password=$PG_PASS" \
        python3 "$PROTO_DIR/scripts/seed_source_db.py"
    deactivate
)
success "sourcedb seeded"

# ── 6. chat-ui npm deps ───────────────────────────────────────────────────────
info "Installing chat-ui npm dependencies…"
(cd "$PROTO_DIR/chat-ui" && npm install --silent)
success "chat-ui deps installed"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Local setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Next steps:"
echo "    1. Edit  local/.env  (set OPENAI_API_KEY, JWT_SECRET, OAuth creds)"
echo "    2. Run   bash local/start.sh"
echo "    3. Open  http://localhost:3000  in your browser"
echo ""
