# Chat System Core Service

FastAPI service providing OAuth2 authentication, access control, and RAG-powered chat with OpenAI.

## Purpose

This service implements:
- **OAuth2 Login**: Google-based authentication with JWT issuance
- **Access Control**: Per-request policy resolution from system_db
- **RAG Chain**: LangChain-based retrieval-augmented generation from pgvector
- **Post-Generation Guardrail**: Verification that user can access all chunks used in response
- **Full Audit Trail**: Request logging and chat message persistence

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SYSTEM_DSN` | Yes | - | PostgreSQL DSN for system database (read/write) |
| `VECTOR_DSN` | Yes | - | PostgreSQL DSN for vector database (read-only) |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `JWT_SECRET` | Yes | - | Secret key for JWT signing |
| `JWT_ALGORITHM` | No | HS256 | JWT algorithm |
| `JWT_EXPIRY_MINUTES` | No | 15 | JWT expiry time in minutes |
| `OAUTH_PROVIDER` | No | google | OAuth provider (only google supported) |
| `OAUTH_CLIENT_ID` | Yes | - | Google OAuth client ID |
| `OAUTH_CLIENT_SECRET` | Yes | - | Google OAuth client secret |
| `LLM_PROVIDER` | No | openai | LLM provider |
| `LLM_MODEL` | No | gpt-4o | LLM model name |
| `EMBEDDING_MODEL` | No | text-embedding-3-small | Embedding model name |
| `DEV_MOCK_USER` | No | - | Dev-only: email for bypass login (e.g., test@example.com) |

## Running Locally (Standalone)

```bash
# Install dependencies
pip install -e .

# Set environment variables
export SYSTEM_DSN="postgresql+asyncpg://user:pass@localhost:5432/systemdb"
export VECTOR_DSN="postgresql+asyncpg://user:pass@localhost:5432/vectordb"
export OPENAI_API_KEY="sk-..."
export JWT_SECRET="your-secret-key"
export OAUTH_CLIENT_ID="..."
export OAUTH_CLIENT_SECRET="..."
export DEV_MOCK_USER="dev@example.com"  # For local dev

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Dev login: `curl http://localhost:8000/auth/dev-login`

## Running with Docker Compose

```bash
# In project root with docker-compose.yml
docker-compose up -d core

# Service runs on http://localhost:8000
```

## API Endpoints

- `GET /health` - Health check
- `GET /auth/login` - Redirect to OAuth provider
- `GET /auth/callback` - OAuth callback (returns JWT)
- `GET /auth/dev-login` - Dev-only JWT issuance
- `POST /api/chat` - Chat with RAG (SSE streaming)
- `GET /api/chat/history` - Get user's chat history

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Database Schema

System database tables (created by Alembic):
- `users` - User accounts
- `roles` - Role definitions
- `user_roles` - User role assignments
- `role_policies` - Policies granted via roles
- `user_policies` - User-specific policy overrides
- `chat_sessions` - Chat session records
- `chat_messages` - Chat message records
- `request_log` - All API request logs

Vector database (read-only):
- `chunks` - Embeddings with metadata and access control

## Implementation Notes

- **Async/await throughout**: SQLAlchemy 2.0 async, asyncio patterns
- **Type hints**: Full type coverage
- **Access control**: Resolved fresh on every request from system_db
- **Guardrails**: Post-LLM verification prevents data leakage
- **Stateless RAG**: No conversation history - only current context
- **Metadata stripped**: LLM never sees chunk metadata, only content
