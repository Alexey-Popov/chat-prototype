# Quick Start Guide

## Setup (5 minutes)

### 1. Install Python dependencies
```bash
cd /path/to/core
pip install -e .
pip install -e ".[dev]"  # For testing
```

### 2. Create .env file
```bash
cp .env.example .env
# Edit .env with your credentials:
# - OPENAI_API_KEY
# - OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET
# - JWT_SECRET (any random string)
```

### 3. Run database migrations
```bash
alembic upgrade head
```

### 4. Start the service
```bash
# Option A: Direct
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option B: Docker
docker build -t chat-core .
docker run -p 8000:8000 --env-file .env chat-core
```

## Testing the API

### 1. Health check
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 2. Dev login (if DEV_MOCK_USER set)
```bash
curl http://localhost:8000/auth/dev-login
# {"access_token":"eyJ0eXAi...","token_type":"bearer"}
```

### 3. Chat (with SSE streaming)
```bash
TOKEN="your-token-from-dev-login"

curl -N http://localhost:8000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, what can you help with?"}'
```

### 4. Chat history
```bash
curl http://localhost:8000/api/chat/history \
  -H "Authorization: Bearer $TOKEN"
```

## File Overview

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app entry point |
| `app/config.py` | Environment variable loading |
| `app/db.py` | Database engines and sessions |
| `app/models/system.py` | ORM models (users, roles, etc.) |
| `app/core/jwt.py` | JWT token operations |
| `app/core/deps.py` | FastAPI dependency injection |
| `app/core/middleware.py` | Request logging middleware |
| `app/access/policy_engine.py` | Access control policy resolution |
| `app/rag/retriever.py` | Vector DB chunk retrieval (access-filtered) |
| `app/rag/serializer.py` | Chunk metadata stripping |
| `app/rag/guardrail.py` | Post-LLM access verification |
| `app/rag/chain.py` | LangChain RAG pipeline |
| `app/api/auth.py` | OAuth2 and JWT endpoints |
| `app/api/chat.py` | Chat RAG and history endpoints |
| `alembic/versions/001_initial.py` | Database schema |

## Key Design Points

1. **Stateless**: No session history - each request uses current context only
2. **Access control**: Fresh from DB every request, enforced at query level and post-generation
3. **Metadata stripped**: LLM never sees access metadata
4. **Async throughout**: All I/O operations are async/await
5. **Type safe**: Full type hints in all functions
6. **Logged**: Every request and every chat turn is logged

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_policy_engine.py::test_policy_engine_resolve_with_roles -v

# Coverage report
pytest tests/ --cov=app --cov-report=html
```

## Troubleshooting

**"Connection refused" to database**
- Ensure PostgreSQL is running on SYSTEM_DSN/VECTOR_DSN
- Check DSN credentials in .env

**"Invalid token" errors**
- Verify JWT_SECRET is set and consistent
- Check token hasn't expired (JWT_EXPIRY_MINUTES)

**OpenAI errors**
- Verify OPENAI_API_KEY is correct
- Check you have API credits

**Migrations fail**
- Drop and recreate databases
- Run `alembic upgrade head` again

## Common Tasks

### Reset database
```bash
alembic downgrade base  # Drop all tables
alembic upgrade head    # Recreate all tables
```

### Create a test user/role manually
```python
# In Python REPL:
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models import User, Role, UserRole
from uuid import uuid4

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/systemdb")

async def setup():
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession)
    async with SessionLocal() as db:
        user = User(id=uuid4(), oauth_sub="test", email="test@example.com")
        role = Role(id=uuid4(), name="user")
        db.add(user)
        db.add(role)
        await db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()

asyncio.run(setup())
```

## Next: Integration

Once core service is running:

1. **Chunking service** should:
   - Read from source_db
   - Generate embeddings via OpenAI
   - Insert chunks to vector_db with metadata

2. **Admin service** should:
   - Create/manage users, roles, policies
   - Use same system_db

3. **Chat UI** should:
   - Call `/api/chat` with SSE support
   - Display streamed tokens in real-time
   - Show `/api/chat/history`
