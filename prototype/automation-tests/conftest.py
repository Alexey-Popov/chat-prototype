"""
Automation test fixtures.

Requires running services (docker compose up) and DEV_MOCK_USER enabled in core.
Seeds system_db and vector_db before the test session, rolls back after.
"""
import asyncio
import json
import os
from typing import AsyncGenerator, Callable
from uuid import uuid4

import asyncpg
import httpx
import psycopg2
import pytest
from dotenv import load_dotenv

load_dotenv()

# ── Service URLs ──────────────────────────────────────────────────────────────
CORE_URL     = os.getenv("CORE_URL",     "http://localhost:8000")
ADMIN_URL    = os.getenv("ADMIN_URL",    "http://localhost:8002")
CHUNKING_URL = os.getenv("CHUNKING_URL", "http://localhost:8001")

# ── DB connection strings ─────────────────────────────────────────────────────
SYSTEM_DB_DSN = os.getenv(
    "SYSTEM_DB_DSN",
    "host=localhost port=5435 dbname=systemdb user=user password=password",
)
VECTOR_DB_DSN = os.getenv(
    "VECTOR_DB_DSN",
    "postgresql://user:password@localhost:5434/vectordb",
)

# ── Test data definitions ─────────────────────────────────────────────────────
ROLES = ["SUPPORT", "FINANCE", "BIZDEV", "ADMIN"]

USERS: dict[str, dict] = {
    "u_support":    {"email": "support@test.com",    "role": "SUPPORT"},
    "u_finance":    {"email": "finance@test.com",    "role": "FINANCE"},
    "u_bizdev":     {"email": "bizdev@test.com",     "role": "BIZDEV"},
    "u_admin":      {"email": "admin@test.com",      "role": "ADMIN"},
    "u_override":   {"email": "override@test.com",   "role": "SUPPORT"},   # + grant transactions
    "u_restricted": {"email": "restricted@test.com", "role": "FINANCE"},   # - restrict transactions
}

CHUNKS: dict[str, dict] = {
    "c_support_1":   {"content": "Support ticket about login issue",
                      "table_name": "tickets",           "allowed_roles": ["SUPPORT"]},
    "c_finance_1":   {"content": "Finance report Q1 revenue",
                      "table_name": "financial_reports", "allowed_roles": ["FINANCE"]},
    "c_finance_txn": {"content": "Transaction record amount 1500",
                      "table_name": "transactions",      "allowed_roles": ["FINANCE"]},
    "c_bizdev_1":    {"content": "Deal memo partner acquisition",
                      "table_name": "deals",             "allowed_roles": ["BIZDEV"]},
    "c_shared_1":    {"content": "Company profile Acme Corp",
                      "table_name": "companies",
                      "allowed_roles": ["SUPPORT", "FINANCE", "BIZDEV"]},
}

# Populated by seed_system_db; used across fixtures
_role_ids:  dict[str, str] = {}
_user_ids:  dict[str, str] = {}
_chunk_ids: dict[str, str] = {}


# ── Seed helpers ──────────────────────────────────────────────────────────────

def seed_system_db() -> None:
    conn = psycopg2.connect(SYSTEM_DB_DSN)
    cur = conn.cursor()
    try:
        # Roles
        for name in ROLES:
            rid = str(uuid4())
            cur.execute(
                "INSERT INTO roles (id, name) VALUES (%s, %s) "
                "ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id",
                (rid, name),
            )
            _role_ids[name] = cur.fetchone()[0]

        # Users + role assignments + user policies
        for key, info in USERS.items():
            uid = str(uuid4())
            cur.execute(
                "INSERT INTO users (id, oauth_sub, email, active) "
                "VALUES (%s, %s, %s, TRUE) "
                "ON CONFLICT (email) DO UPDATE SET active=TRUE RETURNING id",
                (uid, f"test|{info['email']}", info["email"]),
            )
            _user_ids[key] = str(cur.fetchone()[0])

            role_id = _role_ids[info["role"]]
            cur.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (_user_ids[key], role_id),
            )

        # u_override: grant access to transactions table
        cur.execute(
            "INSERT INTO user_policies (id, user_id, table_pattern, policy_type) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (str(uuid4()), _user_ids["u_override"], "transactions", "grant"),
        )
        # u_restricted: restrict access to transactions table
        cur.execute(
            "INSERT INTO user_policies (id, user_id, table_pattern, policy_type) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (str(uuid4()), _user_ids["u_restricted"], "transactions", "restrict"),
        )

        # Role policies (table patterns per role)
        role_patterns = {
            "SUPPORT": ["tickets", "customer_contacts", "faq_entries", "companies", "products"],
            "FINANCE": ["transactions", "ledger_entries", "financial_reports", "companies", "products"],
            "BIZDEV":  ["deals", "company_history", "partner_agreements", "companies", "products"],
            "ADMIN":   [],
        }
        for role_name, patterns in role_patterns.items():
            for pattern in patterns:
                cur.execute(
                    "INSERT INTO role_policies (id, role_id, table_pattern) "
                    "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (str(uuid4()), _role_ids[role_name], pattern),
                )

        conn.commit()
    finally:
        cur.close()
        conn.close()


async def seed_vector_db() -> None:
    conn = await asyncpg.connect(VECTOR_DB_DSN)
    try:
        await conn.execute("DELETE FROM chunks WHERE metadata->>'row_id' LIKE 'test_%'")
        for key, info in CHUNKS.items():
            chunk_id = str(uuid4())
            _chunk_ids[key] = chunk_id
            metadata = json.dumps({
                "allowed_roles": info["allowed_roles"],
                "allowed_users": [],
                "table_name": info["table_name"],
                "row_id": f"test_{key}",
                "schema_hash": "test",
            })
            dummy_embedding = "[" + ",".join(["0.0"] * 1536) + "]"
            await conn.execute(
                "INSERT INTO chunks (id, content, embedding, metadata) "
                "VALUES ($1, $2, $3::vector, $4::jsonb)",
                chunk_id, info["content"], dummy_embedding, metadata,
            )
    finally:
        await conn.close()


async def cleanup_vector_db() -> None:
    conn = await asyncpg.connect(VECTOR_DB_DSN)
    try:
        await conn.execute("DELETE FROM chunks WHERE metadata->>'row_id' LIKE 'test_%'")
    finally:
        await conn.close()


# ── Session-scoped fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def seed_databases(event_loop):
    seed_system_db()
    event_loop.run_until_complete(seed_vector_db())
    yield
    event_loop.run_until_complete(cleanup_vector_db())


@pytest.fixture(scope="session")
def role_ids() -> dict[str, str]:
    return _role_ids


@pytest.fixture(scope="session")
def user_ids() -> dict[str, str]:
    return _user_ids


@pytest.fixture(scope="session")
def chunk_ids() -> dict[str, str]:
    return _chunk_ids


# ── Per-test HTTP clients ─────────────────────────────────────────────────────

@pytest.fixture
async def core(event_loop) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=CORE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture
async def admin(event_loop) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=ADMIN_URL, timeout=30.0) as c:
        yield c


@pytest.fixture
async def chunking(event_loop) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=CHUNKING_URL, timeout=30.0) as c:
        yield c


# ── Token helpers ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def tokens(event_loop) -> dict[str, str]:
    """Fetch dev JWTs for all test users (requires DEV_MOCK_USER enabled in core)."""
    async def _fetch():
        result = {}
        async with httpx.AsyncClient(base_url=CORE_URL, timeout=30.0) as c:
            for key, info in USERS.items():
                r = await c.get("/auth/dev-login", params={"email": info["email"]})
                assert r.status_code == 200, f"Dev login failed for {key}: {r.text}"
                result[key] = r.json()["access_token"]
        return result
    return event_loop.run_until_complete(_fetch())


@pytest.fixture
def auth(tokens) -> Callable[[str], dict[str, str]]:
    """Returns Authorization header dict for a given user key."""
    def _header(user_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {tokens[user_key]}"}
    return _header
