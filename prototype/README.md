# Internal Assistant — Prototype

Role-based RAG chat system for fintech data. One `docker compose up` starts everything.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2) running locally
- An [OpenAI API key](https://platform.openai.com/api-keys) (used by **core** for chat/embeddings and by **chunking** for ingestion embeddings)

---

## Quick start

```bash
cd prototype   # repository root may differ; compose file lives here
cp .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Notes |
|----------|--------|
| `OPENAI_API_KEY` | Required |
| `JWT_SECRET` | Required (long random string) |
| `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` | Required for **process startup**; use real Google values for OAuth login, or keep the example placeholders for dev-only API use |

Start the stack (foreground logs):

```bash
docker compose up --build
```

Or detached:

```bash
docker compose up -d --build
```

| Service    | URL                         | Purpose                          |
|------------|-----------------------------|----------------------------------|
| Chat UI    | http://localhost:3000       | React chat interface             |
| Admin UI   | http://localhost:3001       | React admin console (demo login) |
| Core API   | http://localhost:8000/docs  | FastAPI — auth, chat, RAG        |
| Admin API  | http://localhost:8002/docs  | FastAPI — users, roles, policies |
| Chunking   | http://localhost:8001/docs  | Ingestion status endpoint        |

Three PostgreSQL instances start automatically:

| DB        | Port | Contains                                      |
|-----------|------|-----------------------------------------------|
| source_db | 5433 | Fintech test data (read-only for the system)  |
| vector_db | 5434 | pgvector embeddings + chunk metadata          |
| system_db | 5435 | Users, roles, policies, chat history, logs    |

`source_db` is seeded on first `docker compose up` via the `seed` service.

---

## Verify the stack

With services running (`docker compose up -d` is enough after the first build):

```bash
curl -sS http://localhost:8000/health
curl -sS http://localhost:8001/health
curl -sS http://localhost:8002/health
```

Optional: dev JWT on **core** (requires `DEV_MOCK_USER` in `.env` — see below):

```bash
curl -sS "http://localhost:8000/auth/dev-login?email=support@test.com"
```

Optional: dev JWT on **admin** (same `DEV_MOCK_USER`; grants the `admin` role in `system_db`):

```bash
curl -sS "http://localhost:8002/auth/dev-login?email=support@test.com"
```

You should see JSON including `access_token`.

---

## Ingest data into vector_db

After `source_db` and `vector_db` are up, run the ingestion CLI **from the same Compose project** so container DNS resolves `source_db` / `vector_db`:

```bash
docker compose run --rm chunking python ingest.py \
  --source-dsn "postgresql://user:password@source_db:5432/sourcedb" \
  --vector-dsn "postgresql+asyncpg://user:password@vector_db:5432/vectordb" \
  --policy-config policies.yaml
```

`docker compose run` loads `env_file: .env` from the `chunking` service, so `OPENAI_API_KEY` is available for embeddings.

Use `--force` to re-embed after policy or schema changes.

Or locally (with DBs already exposed on the host ports above):

```bash
cd chunking
pip install -e .
python ingest.py \
  --source-dsn "postgresql://user:password@localhost:5433/sourcedb" \
  --vector-dsn "postgresql+asyncpg://user:password@localhost:5434/vectordb" \
  --policy-config policies.yaml
```

---

## Dev login / demo mode (no OAuth required)

Use this for demos and local testing.

1. **Backends** — in `.env` set `DEV_MOCK_USER` (e.g. `support@test.com`). This enables:
   - **Core:** `GET http://localhost:8000/auth/dev-login?email=...` — JWT for the chat UI and RAG APIs.
   - **Admin:** `GET http://localhost:8002/auth/dev-login?email=...` — JWT with the **admin** role (user is created/linked in `system_db` as needed).

2. **Docker-built UIs** — demo controls are compiled in only when `VITE_DEV_MOCK_USER=true` at **image build** time. In `.env`:

   ```bash
   DEV_MOCK_USER=support@test.com
   VITE_DEV_MOCK_USER=true
   ```

   Compose passes `DEV_MOCK_USER` into both SPAs as `VITE_DEV_DEFAULT_EMAIL` so **“Continue as …”** matches the backend default.

   Rebuild front-ends:

   ```bash
   docker compose build chat_ui admin_ui && docker compose up -d
   ```

   - **Chat:** http://localhost:3000 — demo sign-in + optional OAuth.
   - **Admin:** http://localhost:3001 — demo sign-in and user list (calls admin API with Bearer token).

   For local Vite dev (`npm run dev`), set `VITE_DEV_MOCK_USER=true` and `VITE_DEV_DEFAULT_EMAIL` in `chat-ui/.env.local` or `admin-ui/.env.local` as needed.

Example API calls:

```bash
curl "http://localhost:8000/auth/dev-login?email=support@test.com"
curl "http://localhost:8002/auth/dev-login?email=support@test.com"
```

---

## Services

```
prototype/
├── core/           FastAPI — auth, chat API, RAG chain, access guardrail
├── chunking/       Ingestion CLI + FastAPI status endpoint
├── admin/          FastAPI — user/role/policy management, audit log
├── chat-ui/        React + Vite SPA (chat)
├── admin-ui/       React + Vite SPA (admin console, demo login)
├── scripts/        seed_source_db.py (run by the seed Docker service)
├── automation-tests/  Integration test suite
├── docker-compose.yml
└── .env.example
```

### core
```bash
cd core && pip install -e ".[dev]"
pytest tests/ -v
uvicorn app.main:app --reload --port 8000
```

### chunking
```bash
cd chunking && pip install -e ".[dev]"
pytest tests/ -v
```

### admin
```bash
cd admin && pip install -e ".[dev]"
pytest tests/ -v
uvicorn app.main:app --reload --port 8002
```

### chat-ui
```bash
cd chat-ui && npm install
npm run dev      # http://localhost:5173
npm run build
```

---

## Automation tests

Requires all services running + `DEV_MOCK_USER` set.

```bash
cd automation-tests
pip install -r requirements.txt
pytest -v
```

See `automation-tests/README.md` for full details.

---

## Environment variables

| Variable              | Required | Description                                    |
|-----------------------|----------|------------------------------------------------|
| `OPENAI_API_KEY`      | Yes      | Used by core (embeddings + LLM) and chunking   |
| `JWT_SECRET`          | Yes      | HS256 signing key — must match across services |
| `OAUTH_CLIENT_ID`     | Startup  | Google OAuth2 client ID (placeholders OK for dev if you only use dev-login) |
| `OAUTH_CLIENT_SECRET` | Startup  | Google OAuth2 client secret                    |
| `DEV_MOCK_USER`       | Dev only | Enables `/auth/dev-login` on core              |
| `VITE_DEV_MOCK_USER`  | Dev UI   | Set to `true` + rebuild `chat_ui` for Dev Login in the Docker SPA |
| `CORS_ORIGINS`        | No       | Comma-separated browser origins for core (defaults include localhost:3000) |
| `LLM_MODEL`           | No       | Default: `gpt-4o`                              |
| `EMBEDDING_MODEL`     | No       | Default: `text-embedding-3-small`              |

---

## Troubleshooting

- **Core exits on startup / migration errors** — if `system_db` was left in a half-migrated state, reset only that volume: `docker compose down`, `docker volume rm prototype_system_db_data`, then `docker compose up -d --build` again (you will lose local system DB data).
- **Ingestion / vector errors after schema experiments** — same pattern with `prototype_vector_db_data`.

---

## Adding a new data source

1. Implement `DataConnector` ABC in `chunking/app/connectors/`
2. Register it in `chunking/ingest.py`
3. Add table → role mappings in `chunking/policies.yaml`
4. Re-run the ingestion CLI

## Adding an OAuth provider

Change `OAUTH_PROVIDER`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` in `.env`.
Authlib handles Google, GitHub, and any OIDC-compatible provider with no code changes.
