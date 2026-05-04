#!/usr/bin/env bash
# =============================================================================
# start.sh — Start all services locally (no Docker)
#
# Run from the prototype/ directory:
#   bash local/start.sh
#
# Services started:
#   • core      http://localhost:8000   (FastAPI — auth, chat, RAG)
#   • chunking  http://localhost:8001   (FastAPI — ingestion pipeline)
#   • admin     http://localhost:8002   (FastAPI — user/role management)
#   • chat-ui   http://localhost:3000   (Vite dev server)
#
# Logs written to:  local/logs/<service>.log
# PIDs stored in:   local/pids/<service>.pid
#
# Stop with:  bash local/stop.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOGS_DIR="$SCRIPT_DIR/logs"
PIDS_DIR="$SCRIPT_DIR/pids"

mkdir -p "$LOGS_DIR" "$PIDS_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[start]${NC} $*"; }
success() { echo -e "${GREEN}[start]${NC} ✓ $*"; }
warn()    { echo -e "${YELLOW}[start]${NC} ⚠ $*"; }
die()     { echo -e "${RED}[start]${NC} ✗ $*" >&2; exit 1; }

# ── Load .env ──────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    die ".env not found. Run 'bash local/setup.sh' first."
fi
set -a; source "$ENV_FILE"; set +a

# ── Check venvs exist ──────────────────────────────────────────────────────────
for svc in core chunking admin; do
    [[ -d "$PROTO_DIR/$svc/.venv" ]] || die "$svc venv missing. Run 'bash local/setup.sh' first."
done

# ── Port conflict check ────────────────────────────────────────────────────────
check_port() {
    local port="$1" name="$2"
    if lsof -ti :"$port" &>/dev/null 2>&1; then
        warn "Port $port already in use — $name may already be running or there's a conflict."
    fi
}
check_port 8000 "core"
check_port 8001 "chunking"
check_port 8002 "admin"
check_port 3000 "chat-ui"

# ── Start a service ────────────────────────────────────────────────────────────
start_service() {
    local name="$1"
    local dir="$2"
    local cmd="$3"
    local log="$LOGS_DIR/$name.log"
    local pid_file="$PIDS_DIR/$name.pid"

    # Kill stale process if pid file exists
    if [[ -f "$pid_file" ]]; then
        local old_pid
        old_pid=$(cat "$pid_file")
        if kill -0 "$old_pid" 2>/dev/null; then
            warn "$name is already running (PID $old_pid). Stopping it first…"
            kill "$old_pid" 2>/dev/null || true
            sleep 1
        fi
        rm -f "$pid_file"
    fi

    info "Starting $name…"
    (
        cd "$dir"
        # shellcheck source=/dev/null
        source .venv/bin/activate
        eval "$cmd" >> "$log" 2>&1 &
        echo $! > "$pid_file"
    )
    success "$name started  →  $log"
}

# ── Core service ──────────────────────────────────────────────────────────────
start_service core "$PROTO_DIR/core" \
    "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# ── Chunking service ──────────────────────────────────────────────────────────
start_service chunking "$PROTO_DIR/chunking" \
    "uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"

# ── Admin service ─────────────────────────────────────────────────────────────
start_service admin "$PROTO_DIR/admin" \
    "uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"

# ── Chat-UI (Vite dev server) ─────────────────────────────────────────────────
info "Starting chat-ui (Vite dev server)…"
CHAT_PID_FILE="$PIDS_DIR/chat-ui.pid"
CHAT_LOG="$LOGS_DIR/chat-ui.log"

if [[ -f "$CHAT_PID_FILE" ]]; then
    old_pid=$(cat "$CHAT_PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        warn "chat-ui already running (PID $old_pid). Stopping it first…"
        kill "$old_pid" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$CHAT_PID_FILE"
fi

(
    cd "$PROTO_DIR/chat-ui"
    VITE_CORE_URL="${CORE_URL:-http://localhost:8000}" \
        npm run dev -- --port 3000 >> "$CHAT_LOG" 2>&1 &
    echo $! > "$CHAT_PID_FILE"
)
success "chat-ui started  →  $CHAT_LOG"

# ── Wait for services to be ready ─────────────────────────────────────────────
echo ""
info "Waiting for services to come up…"

wait_for() {
    local name="$1" url="$2"
    local attempts=0
    while [[ $attempts -lt 20 ]]; do
        if curl -sf "$url" &>/dev/null; then
            success "$name is up at $url"
            return 0
        fi
        sleep 1
        ((attempts++))
    done
    warn "$name did not respond at $url after 20s — check logs/$(echo "$name" | tr '[:upper:]' '[:lower:]').log"
}

wait_for core    "http://localhost:8000/health"
wait_for chunking "http://localhost:8001/health"
wait_for admin   "http://localhost:8002/health"

# chat-ui takes a bit longer to compile
sleep 4
if curl -sf "http://localhost:3000" &>/dev/null; then
    success "chat-ui is up at http://localhost:3000"
else
    warn "chat-ui not ready yet — it may still be compiling. Check logs/chat-ui.log"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  All services running${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Chat UI    →  http://localhost:3000"
echo "  Core API   →  http://localhost:8000/docs"
echo "  Admin API  →  http://localhost:8002/docs"
echo "  Chunking   →  http://localhost:8001/docs"
echo ""
echo "  Logs:  local/logs/<service>.log"
echo "  Stop:  bash local/stop.sh"
echo ""
