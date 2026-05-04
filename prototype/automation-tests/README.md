# Automation Tests

Integration test suite covering all access-control, audit, and security requirements.
Tests run against live services (docker compose up) — no mocking.

---

## Prerequisites

- All services running: `docker compose up` from `prototype/`
- `.env` present with `DEV_MOCK_USER` **uncommented** (required for test JWT issuance)
- Python 3.12+

---

## Setup

```bash
cd prototype/automation-tests
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # edit OPENAI_API_KEY and JWT_SECRET
```

---

## Run

```bash
# Full suite
pytest -v

# By group (marks defined in pytest.ini)
pytest -m auth        -v   # A-series: authentication
pytest -m access      -v   # R/U/SL-series: role access, user policies, stateless
pytest -m guardrail   -v   # G-series: post-generation guardrail
pytest -m audit       -v   # H-series: chat history & request logging
pytest -m admin       -v   # AD-series: admin API operations
pytest -m fail_secure -v   # F-series: fail-secure behaviour
pytest -m metadata    -v   # M-series: metadata isolation
pytest -m edge        -v   # E-series: edge cases
```

---

## How it works

**Fixtures** (`conftest.py`):

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `seed_databases` | session | Seeds system_db (users/roles/policies) and vector_db (test chunks) before all tests; rolls back after |
| `core` | function | `httpx.AsyncClient` → core service (port 8000) |
| `admin` | function | `httpx.AsyncClient` → admin service (port 8002) |
| `chunking` | function | `httpx.AsyncClient` → chunking service (port 8001) |
| `tokens` | session | Dict of JWTs for all test users, fetched via `/auth/dev-login` |
| `auth` | function | Callable: `auth("u_support")` → `{"Authorization": "Bearer ..."}` |
| `user_ids` | session | Dict of user UUIDs seeded into system_db |
| `chunk_ids` | session | Dict of chunk UUIDs seeded into vector_db |

**Test users**:

| Key | Role | Notes |
|-----|------|-------|
| `u_support` | SUPPORT | base role only |
| `u_finance` | FINANCE | base role only |
| `u_bizdev` | BIZDEV | base role only |
| `u_admin` | ADMIN | no table access |
| `u_override` | SUPPORT | + grant: `transactions` table |
| `u_restricted` | FINANCE | − restrict: `transactions` table |

**Test chunks** (seeded into vector_db with dummy 1536-dim zero embeddings):

| Key | Table | Allowed roles |
|-----|-------|---------------|
| `c_support_1` | tickets | SUPPORT |
| `c_finance_1` | financial_reports | FINANCE |
| `c_finance_txn` | transactions | FINANCE |
| `c_bizdev_1` | deals | BIZDEV |
| `c_shared_1` | companies | SUPPORT, FINANCE, BIZDEV |

---

## Coverage

| File | Cases | What it tests |
|------|-------|---------------|
| `test_auth.py` | A01–A05 | JWT validation, expired/malformed tokens, dev login |
| `test_role_access.py` | R01–R09 | Per-role data isolation, shared chunks |
| `test_user_policies.py` | U01–U04 | User-level grants and restrictions |
| `test_guardrail.py` | G01–G04 | Post-generation re-verification, 403 on block, no chat_message on block |
| `test_audit.py` | H01–H06 | chat_messages and request_log persistence, DELETE → 405 |
| `test_admin.py` | AD01–AD06 | Admin CRUD for users, roles, policies |
| `test_fail_secure.py` | F01–F05 | Error codes on system failures, no partial writes |
| `test_stateless.py` | SL01–SL02 | LLM context contains no prior turns |
| `test_metadata.py` | M01–M05 | No table names / role names / chunk metadata in responses |
| `test_edge_cases.py` | E01–E04 | Empty results, no-role users, no write endpoints |

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CORE_URL` | `http://localhost:8000` | Core service URL |
| `ADMIN_URL` | `http://localhost:8002` | Admin service URL |
| `CHUNKING_URL` | `http://localhost:8001` | Chunking service URL |
| `SYSTEM_DB_DSN` | `host=localhost port=5435 ...` | Direct DB access for seed/verify |
| `VECTOR_DB_DSN` | `postgresql://...localhost:5434/vectordb` | Direct DB access for chunk seed |
| `JWT_SECRET` | — | Must match core service value |
