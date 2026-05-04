# Local Setup (no Docker)

Run the full prototype on your machine without Docker.  
All three Python services and the React dev server run as local processes.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.10 | `brew install python@3.12` |
| Node | ≥ 18 | `brew install node` |
| PostgreSQL | ≥ 14 | `brew install postgresql@16` |
| pgvector | matching PostgreSQL | `brew install pgvector` |

**macOS quick install:**
```bash
brew install python@3.12 node postgresql@16 pgvector
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt install python3.12 python3.12-venv nodejs postgresql postgresql-16-pgvector
sudo systemctl start postgresql
```

---

## First-time setup

```bash
# From the prototype/ directory:
cd prototype

# 1. Run setup (≈ 2 min)
bash local/setup.sh
```

This will:
- Create three local databases: `sourcedb`, `vectordb`, `systemdb`
- Enable the `pgvector` extension in `vectordb`
- Create Python virtualenvs in `core/.venv`, `chunking/.venv`, `admin/.venv`
- Run Alembic migrations and seed fintech test data
- Run `npm install` for `chat-ui`
- Copy `local/.env.local` → `local/.env` if not present

**Then edit `local/.env`** before starting:

```bash
# Required — get from platform.openai.com
OPENAI_API_KEY=sk-...

# Required — any random string ≥ 32 chars
JWT_SECRET=change-me-to-a-random-secret-at-least-32-chars

# For OAuth login (or leave DEV_MOCK_USER set to skip OAuth entirely)
OAUTH_CLIENT_ID=your-google-client-id
OAUTH_CLIENT_SECRET=your-google-client-secret
```

---

## Start

```bash
bash local/start.sh
```

| Service | URL |
|---------|-----|
| Chat UI | http://localhost:3000 |
| Core API | http://localhost:8000/docs |
| Admin API | http://localhost:8002/docs |
| Chunking API | http://localhost:8001/docs |

Logs are written to `local/logs/<service>.log`.  
All services run with `--reload` so code changes are picked up automatically.

---

## Stop

```bash
bash local/stop.sh
```

---

## Database access

All databases live on your local PostgreSQL instance (default port 5432):

```bash
psql -h localhost -U user sourcedb    # source data (read-only for services)
psql -h localhost -U user vectordb    # embeddings + chunks
psql -h localhost -U user systemdb    # users, roles, policies, audit log
```

Password: `password` (set in `local/.env`).

---

## Re-seed / Reset

```bash
# Re-seed source data only
SOURCE_DSN="host=localhost port=5432 dbname=sourcedb user=user password=password" \
    python3 scripts/seed_source_db.py

# Full reset: drop and recreate all tables, re-run migrations
psql -h localhost -U user -c "DROP DATABASE IF EXISTS sourcedb; CREATE DATABASE sourcedb OWNER user;" postgres
psql -h localhost -U user -c "DROP DATABASE IF EXISTS vectordb; CREATE DATABASE vectordb OWNER user;" postgres
psql -h localhost -U user -c "DROP DATABASE IF EXISTS systemdb; CREATE DATABASE systemdb OWNER user;" postgres
bash local/setup.sh
```

---

## Troubleshooting

**`pg_isready` fails / PostgreSQL not running**
```bash
brew services start postgresql@16      # macOS
sudo systemctl start postgresql        # Linux
```

**`pgvector` extension not found**
```bash
brew install pgvector                  # macOS
sudo apt install postgresql-16-pgvector  # Ubuntu
# Then re-run setup.sh
```

**Port already in use**
```bash
bash local/stop.sh   # kills any previously started services
```

**Alembic migration fails with auth error**  
Make sure `PG_USER` / `PG_PASS` in `local/.env` match the PostgreSQL role created by `setup.sh`.

**Chat-UI shows blank / can't connect to core**  
Check `VITE_CORE_URL` in `local/.env` and that `core` is running: `curl http://localhost:8000/health`.

---

## Layout

```
local/
├── setup.sh        # one-time setup
├── start.sh        # start all services
├── stop.sh         # stop all services
├── .env.local      # template — copy to .env and edit
├── .env            # your local config (git-ignored)
├── logs/           # service log files
│   └── <service>.log
└── pids/           # process IDs for stop.sh
    └── <service>.pid
```
