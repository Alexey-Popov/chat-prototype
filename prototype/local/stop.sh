#!/usr/bin/env bash
# =============================================================================
# stop.sh — Stop all locally running services
#
# Run from the prototype/ directory:
#   bash local/stop.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS_DIR="$SCRIPT_DIR/pids"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
success() { echo -e "${GREEN}[stop]${NC} ✓ $*"; }
warn()    { echo -e "${YELLOW}[stop]${NC} ⚠ $*"; }

stop_service() {
    local name="$1"
    local pid_file="$PIDS_DIR/$name.pid"

    if [[ ! -f "$pid_file" ]]; then
        warn "$name — no PID file found (not running or already stopped)"
        return
    fi

    local pid
    pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        # Wait up to 5s for clean exit
        local waited=0
        while kill -0 "$pid" 2>/dev/null && [[ $waited -lt 5 ]]; do
            sleep 1; ((waited++))
        done
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        success "$name stopped (PID $pid)"
    else
        warn "$name — PID $pid not running (already dead)"
    fi

    rm -f "$pid_file"
}

# Also kill any child uvicorn --reload workers (they fork)
kill_port() {
    local port="$1" name="$2"
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        success "$name port $port cleared"
    fi
}

stop_service core
stop_service chunking
stop_service admin
stop_service chat-ui

# Belt-and-suspenders: clear the ports in case reload workers are still alive
kill_port 8000 core
kill_port 8001 chunking
kill_port 8002 admin
kill_port 3000 chat-ui

echo ""
echo -e "${GREEN}All services stopped.${NC}"
echo ""
