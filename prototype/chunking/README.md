# Chunking Service

A FastAPI-based service that ingests data from a source PostgreSQL database, embeds rows using OpenAI embeddings, and writes chunks to a vector database with role-based access control.

## Overview

This service is the **sole writer** to the vector database. The core and admin services are read-only consumers. It handles:

- Schema introspection from source_db
- Text serialization of database rows
- Vector embedding via OpenAI API (with exponential backoff)
- Chunk upsert with duplicate detection
- Automatic cleanup of stale chunks
- Role-based access control via policies.yaml
- Schema change detection via hash comparison

## Architecture

```
┌─────────────┐      ┌──────────────────────┐      ┌──────────────┐
│  source_db  │─────▶│  chunking-service    │─────▶│  vector_db   │
│ (read-only) │      │                      │      │ (read/write) │
└─────────────┘      │  • PostgreSQL        │      └──────────────┘
                     │  • Embedding         │
                     │  • Access Control    │
                     └──────────────────────┘
```

## Components

### `app/connectors/`
- `base.py`: Abstract `DataConnector` interface
- `postgresql.py`: PostgreSQL connector with schema introspection and row serialization

### `app/embeddings/`
- `openai_client.py`: OpenAI embedding client with exponential backoff retry logic

### `app/pipeline/`
- `tagger.py`: Applies role-based access control policies to chunks
- `ingestion.py`: Orchestrates source → embedding → vector_db pipeline

### `app/models/`
- `vector.py`: SQLAlchemy ORM model for chunks table

### API
- `GET /health` - Health check
- `POST /api/ingest` - Trigger ingestion (optional body: `{"table": "table_name", "force": false}`)

### CLI
```bash
python ingest.py \
  --source-dsn postgresql+asyncpg://user:pass@source_db:5432/sourcedb \
  --vector-dsn postgresql+asyncpg://user:pass@vector_db:5432/vectordb \
  --policy-config policies.yaml \
  --table tickets \
  --force
```

## Database Schema

### source_db (read-only, pre-seeded with test data)

**SUPPORT role tables:**
- `tickets`: id, title, description, status, customer_id, created_at
- `customer_contacts`: id, name, email, phone, account_id, created_at
- `faq_entries`: id, question, answer, category, created_at

**FINANCE role tables:**
- `transactions`: id, amount, currency, status, account_id, type, created_at
- `ledger_entries`: id, debit, credit, account_id, description, created_at
- `financial_reports`: id, title, period, content, created_at

**BIZDEV role tables:**
- `deals`: id, name, value, status, company_id, created_at
- `company_history`: id, event, description, date, created_at
- `partner_agreements`: id, partner_name, terms, start_date, end_date, created_at

**SHARED tables:**
- `companies`: id, name, industry, size, created_at
- `products`: id, name, description, price, created_at

### vector_db (read/write, owned by chunking service)

```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_metadata ON chunks USING GIN (metadata);
CREATE INDEX idx_chunks_table_row ON chunks ((metadata->>'table_name'), (metadata->>'row_id'));
```

**Metadata structure:**
```json
{
    "table_name": "tickets",
    "row_id": "uuid",
    "allowed_roles": ["SUPPORT"],
    "allowed_users": [],
    "schema_hash": "abc123def456"
}
```

## Configuration

### Environment Variables

```bash
SOURCE_DSN=postgresql+asyncpg://user:password@source_db:5432/sourcedb
VECTOR_DSN=postgresql+asyncpg://user:password@vector_db:5432/vectordb
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small  # default
```

### policies.yaml

Maps table names to allowed roles:

```yaml
tables:
  tickets:
    allowed_roles: [SUPPORT]
    allowed_users: []
  transactions:
    allowed_roles: [FINANCE]
    allowed_users: []
  companies:
    allowed_roles: [SUPPORT, FINANCE, BIZDEV]
    allowed_users: []
```

## Ingestion Pipeline

1. **Get schema** - Introspect source_db table structure, compute schema hash
2. **Check skip condition** - If schema_hash unchanged AND row count matches, skip table
3. **Fetch rows** - Read all rows from source table
4. **Serialize** - Convert each row to text: `"table: {name} | col1: val1 | col2: val2 | ..."`
5. **Embed** - Batch embed texts via OpenAI (batch size 100, exponential backoff on RateLimit)
6. **Upsert** - Insert/update chunks with ON CONFLICT handler on (table_name, row_id)
7. **Cleanup** - Delete chunks for rows no longer in source database

## Running

### FastAPI Server

```bash
# Install
pip install -e .

# Run with migrations
python ingest.py --source-dsn ... --vector-dsn ... --policy-config policies.yaml

# Or directly with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### CLI Ingestion

```bash
# Ingest all tables
python ingest.py \
  --source-dsn postgresql+asyncpg://user:pass@source_db:5432/sourcedb \
  --vector-dsn postgresql+asyncpg://user:pass@vector_db:5432/vectordb

# Ingest specific table
python ingest.py --table tickets --source-dsn ... --vector-dsn ...

# Force re-index (ignore schema hash)
python ingest.py --force --source-dsn ... --vector-dsn ...
```

### Docker

```bash
docker build -t chunking-service .

docker run -e SOURCE_DSN=... \
           -e VECTOR_DSN=... \
           -e OPENAI_API_KEY=... \
           -p 8001:8001 \
           chunking-service
```

## Testing

```bash
pytest tests/
pytest tests/test_connector.py -v
pytest tests/test_tagger.py -v
pytest tests/test_pipeline.py -v
```

## Key Implementation Details

### PostgreSQL Connector

- `serialize_row()` produces: `"table: {table} | col1: val1 | col2: val2 | ..."`
- All columns are joined with ` | ` separator
- Handles None values as "null", UUID objects as strings

### Embedding Service

- Batch size: 100 texts per request
- Model: `text-embedding-3-small` (1536 dimensions)
- Retry logic: Exponential backoff on RateLimitError
- Max retries: 3

### Ingestion Pipeline

- Schema hash is computed from sorted column names
- Detects schema changes and skips tables if unchanged
- Uses ON CONFLICT for upserts to handle duplicates
- Automatically deletes orphaned chunks from deleted rows
- Metadata includes allowed_roles, allowed_users, schema_hash

### Access Control

- Roles: SUPPORT, FINANCE, BIZDEV
- Each chunk's metadata contains allowed roles/users
- Core service filters chunks by user's roles during search
- Admin service can view/manage all chunks

## Alembic Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Error Handling

- Missing policies.yaml: Service fails at startup
- Invalid DSN: Connection error during init
- OpenAI rate limit: Exponential backoff (1s, 2s, 4s)
- Database migration failure: Logged and raised
- Ingestion errors: Per-table, non-blocking (logs error, continues)

## Security Considerations

- Source database credentials in SOURCE_DSN
- Vector database credentials in VECTOR_DSN
- OpenAI API key in OPENAI_API_KEY
- All credentials passed via environment variables
- Never log credentials or sensitive data
- Role-based metadata enforced at query time (core service responsibility)

## Performance

- Batch embedding: 100 texts per API call
- Vector indexing: IVFFLAT with 100 lists
- Metadata indexing: GIN for fast policy queries
- Skip condition: Prevents redundant re-indexing
- Async I/O: Non-blocking database and API calls

## Dependencies

- SQLAlchemy 2.0+ (async)
- Alembic (migrations)
- AsyncPG (PostgreSQL driver)
- PGVector (vector extension)
- OpenAI (embeddings API)
- FastAPI (HTTP server)
- Uvicorn (ASGI server)
- Pydantic (settings, validation)
- PyYAML (policies)
- Pytest (testing)
