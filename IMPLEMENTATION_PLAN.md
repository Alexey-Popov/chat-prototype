# Implementation Plan — 2-Week Prototype

## Milestones

| # | Milestone | Day |
|---|-----------|-----|
| M1 | Infra running; source_db ingested into vector_db | 3 |
| M2 | Auth + access-filtered RAG query working via REST API | 7 |
| M3 | Web chat UI complete | 10 |
| M4 | Admin UI + Docker Compose demo + smoke tests | 14 |

---

## Repo Structure

```
/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (chat, auth, admin)
│   │   ├── core/         # config, JWT, middleware
│   │   ├── rag/          # LangChain chain, retriever, LLM abstraction
│   │   ├── ingest/       # DataConnector base + PostgreSQL connector
│   │   ├── access/       # policy engine
│   │   └── models/       # SQLAlchemy ORM models
│   ├── ingest.py         # CLI entrypoint
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── chat/         # Chat UI
│   │   └── admin/        # Admin panel
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Week 1 — Core Loop

### Day 1: Scaffold
- [ ] Repo init, `.env.example`, `docker-compose.yml`
- [ ] Services: `source_db` (plain PostgreSQL), `vector_db` (pgvector image), `system_db` (plain PostgreSQL), `backend`, `frontend`
- [ ] Each DB has its own DSN env var: `SOURCE_DSN`, `VECTOR_DSN`, `SYSTEM_DSN`
- [ ] FastAPI app: health check, CORS, settings via `pydantic-settings`
- [ ] SQLAlchemy async engines: separate engine per DB; system_db for runtime writes, vector_db for retriever reads

### Day 2: DB Schema + Test Data Seed + Ingestion Pipeline
- [ ] Alembic migration (system_db): `users`, `roles`, `user_roles`, `role_policies`, `user_policies`, `chat_sessions`, `chat_messages`, `request_log`
- [ ] Alembic migration (vector_db): `chunks` table with pgvector extension
- [ ] `scripts/seed_source_db.py` — populate source_db with realistic fintech test data scoped per role:
  - **SUPPORT tables**: `tickets`, `customer_contacts`, `faq_entries`
  - **FINANCE tables**: `transactions`, `ledger_entries`, `financial_reports`
  - **BIZDEV tables**: `deals`, `company_history`, `partner_agreements`
  - Shared tables: `companies`, `products` (accessible to all roles)
- [ ] Seed script is idempotent; safe to re-run on `docker compose up`
- [ ] `DataConnector` abstract base class
- [ ] `PostgreSQLConnector`: schema introspection → row batches → text chunks
- [ ] Chunk tagging: attach `allowed_roles` / `allowed_users` metadata from policy config YAML
- [ ] Embed via `openai.embeddings` → upsert into `chunks` table

### Day 3: Ingestion CLI + Smoke Test
- [ ] `ingest.py --source-dsn $SOURCE_DSN --vector-dsn $VECTOR_DSN --policy-config policies.yaml`
- [ ] Schema hash stored; re-index only on change
- [ ] Verify: query pgvector directly, confirm chunks present with correct metadata

### Day 4: Access Policy Engine
- [ ] `PolicyEngine.resolve(user_id) → {allowed_tags: set}`
- [ ] Role policies + user overrides merged correctly
- [ ] Unit tests: 3 roles, user override grant, user override deny

### Day 5: RAG Chain + Access Guardrail
- [ ] `AccessFilteredRetriever(PGVectorRetriever)`: injects tag filter into similarity search
- [ ] `ChunkSerializer.to_text(chunk) → str`: strips all metadata (table, row_id, allowed_roles, allowed_users); LLM receives plain text only (P8)
- [ ] LangChain chain: retriever → serializer → prompt template → `ChatOpenAI`; context is current turn only — no prior messages appended (P6)
- [ ] `LLMProvider` abstraction: env var `LLM_PROVIDER=openai` selects implementation
- [ ] Manual test: same question, two roles → different chunks returned
- [ ] `AccessGuardrail.verify(chunk_ids, user_policy)`:
  - Re-fetches `allowed_roles`/`allowed_users` for each chunk ID used in generation
  - Checks intersection with user's effective policy
  - Returns `PASS` or `BLOCK` + list of violating chunk IDs
- [ ] If `BLOCK`: return 403, log violation with severity=HIGH to `request_log`, do not persist to `chat_messages`
- [ ] Unit tests: guardrail catches a chunk that bypassed retrieval filter (simulate tagging bug)

### Day 6: Auth (OAuth2)
- [ ] Authlib integration: Google OAuth2 (configurable provider via env)
- [ ] `/auth/login`, `/auth/callback`, `/auth/logout`
- [ ] JWT issued on callback: `{user_id, role_ids, exp}`
- [ ] `require_auth` FastAPI dependency (validates JWT, injects user)

### Day 7: Chat API
- [ ] `POST /api/chat` → `{message}` → streamed response (SSE)
- [ ] Each turn is stateless: only system prompt + current retrieved chunks + current message sent to LLM. No prior chat_messages rows included (P6)
- [ ] Middleware: resolve user → policy → pass tags to retriever
- [ ] Persist every request to `request_log` via FastAPI middleware (all endpoints)
- [ ] Persist user prompt + assistant response + chunk IDs to `chat_messages` after each chat turn
- [ ] Integration test: authenticated request, correct chunks, LLM responds

---

## Week 2 — UI + Admin + Polish

### Day 8–9: Web Chat UI
- [ ] React + Vite SPA
- [ ] Login page → OAuth redirect → JWT stored in memory (not localStorage)
- [ ] Chat window: message input, streamed response rendering, markdown support
- [ ] Basic session handling (refresh, logout)

### Day 10–11: Admin UI
- [ ] User list: create, deactivate, assign roles
- [ ] Role list: create, assign table-pattern policies
- [ ] User policy overrides: grant/deny per user
- [ ] Audit log viewer (read-only, paginated)

### Day 12: Integration Pass
- [ ] End-to-end test: 3 user accounts (Support, Finance, BizDev), verify data isolation
- [ ] Confirm Docker Compose cold start works: `docker compose up` → demo ready in < 2 min
- [ ] `.env.example` covers all required vars

### Day 13–14: Hardening + Handoff
- [ ] Error handling: expired JWT, LLM timeout, empty retrieval
- [ ] Basic rate limiting on `/api/chat`
- [ ] README: setup steps, how to add a new data source, how to add an OAuth provider
- [ ] Smoke test script: `scripts/smoke_test.sh`

---

## Key Dependencies

| Lib | Purpose |
|-----|---------|
| `fastapi` | REST backend |
| `authlib` | OAuth2 + JWT |
| `langchain`, `langchain-openai` | RAG chain + LLM abstraction |
| `pgvector` | PostgreSQL vector extension Python client |
| `sqlalchemy[asyncio]` | ORM + async DB access |
| `alembic` | DB migrations |
| `openai` | Embeddings + LLM |
| `pydantic-settings` | Config from `.env` |
| `pytest`, `httpx` | Testing |

---

## Extensibility Checklist (built from Day 1)

- [ ] `DataConnector` ABC → new source = one class
- [ ] `LLMProvider` ABC → new model = one class + env var
- [ ] Authlib provider config is env-driven → new OAuth provider = zero code
- [ ] LangChain `VectorStoreRetriever` interface → swap pgvector later without touching chain
- [ ] Policy config in YAML → non-engineers can adjust without code changes
