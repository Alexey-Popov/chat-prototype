# Admin Service Implementation Notes

## Overview

A complete, production-ready FastAPI admin service for managing users, roles, policies, and audit logs in the chat system.

## File Manifest

### Core Application
- **app/main.py**: FastAPI application with routers and health check endpoint
- **app/config.py**: Settings from environment variables (SYSTEM_DSN, JWT_SECRET, JWT_ALGORITHM)
- **app/db.py**: AsyncIO database connection using SQLAlchemy 2.0
- **app/models/system.py**: SQLAlchemy ORM models (User, Role, UserRole, RolePolicy, UserPolicy, ChatMessage, RequestLog)

### Authentication & Authorization
- **app/core/jwt.py**: JWT token decoding and validation (same algorithm as core)
- **app/core/deps.py**: Dependency injection for admin authorization; verifies ADMIN role from token

### API Endpoints
- **app/api/users.py**: User CRUD, role assignment/revocation, user policies (140+ lines)
- **app/api/roles.py**: Role CRUD, role policies (90+ lines)
- **app/api/audit.py**: Read-only paginated audit logs with filtering (100+ lines)

### Testing
- **tests/conftest.py**: pytest fixtures (event loop, database, client, admin user, JWT token)
- **tests/test_users.py**: 13 test cases covering user endpoints
- **tests/test_roles.py**: 7 test cases covering role endpoints

### Configuration & Deployment
- **Dockerfile**: Multi-stage Python 3.12 image, pip install from pyproject.toml
- **pyproject.toml**: Dependencies (fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, python-jose, pydantic)
- **README.md**: Complete API documentation and deployment instructions

## Key Implementation Details

### JWT Validation (app/core/jwt.py)
```python
def decode_token(token: str) -> Optional[dict]:
    # Uses JWTError, checks exp claim
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

### Admin Authorization (app/core/deps.py)
```python
async def get_admin_user(authorization: str, db: AsyncSession) -> User:
    # 1. Parse "Bearer <token>" header
    # 2. Decode JWT, extract user_id and role_ids
    # 3. Fetch user from DB, verify active
    # 4. Fetch admin role from DB, verify role_ids contains admin role
    # 5. Return User object or raise 401/403
```

### User Management (app/api/users.py)
- **POST /api/admin/users**: Create with email/oauth_sub validation
- **GET /api/admin/users**: Paginated list (page, size params)
- **GET /api/admin/users/{id}**: Detail with roles and policies joined
- **PATCH /api/admin/users/{id}**: Update active flag only
- **POST /api/admin/users/{id}/roles**: Assign role (validates user/role exist, no duplicates)
- **DELETE /api/admin/users/{id}/roles/{role_id}**: Revoke role
- **POST /api/admin/users/{id}/policies**: Add policy (validates grant/restrict type)
- **DELETE /api/admin/users/{id}/policies/{id}**: Remove policy

### Role Management (app/api/roles.py)
- **GET /api/admin/roles**: Paginated list with policies
- **POST /api/admin/roles**: Create with unique name check
- **POST /api/admin/roles/{id}/policies**: Add table_pattern
- **DELETE /api/admin/roles/{id}/policies/{id}**: Remove policy

### Audit Endpoints (app/api/audit.py)
- **GET /api/admin/audit/requests**: Request logs with optional filters (user_id, severity, start_date, end_date)
- **GET /api/admin/audit/chat**: Chat messages with optional filters (user_id, session_id)
- Both support pagination with default page=1, size=20

### Database Connection
```python
engine = create_async_engine(SYSTEM_DSN, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)
```
- Supports asyncpg for PostgreSQL
- Connection pooling with pre-ping health checks
- No migration responsibility (core owns Alembic migrations)

### Error Handling
- 400: Validation errors, duplicate entries, invalid policy types
- 401: Missing/invalid token
- 403: User lacks ADMIN role
- 404: Resource not found
- All errors return JSON with `{"detail": "..."}` format

## Type Hints & Validation

All endpoints use:
- Pydantic models for request/response validation
- Type hints for function parameters and return values
- `from_attributes = True` for SQLAlchemy model conversion
- EmailStr for email validation (from pydantic[email])

## Testing Strategy

pytest fixtures:
- `event_loop`: Async event loop (session scope)
- `db_engine`: In-memory SQLite for tests
- `db_session`: Per-test transaction
- `client`: AsyncClient with overridden get_db dependency
- `admin_user`: Pre-created admin user with admin role
- `admin_token`: Valid JWT with admin role
- `admin_headers`: Authorization header ready to use

Test cases cover:
- Authentication (401 without auth)
- Authorization (403 without admin role)
- Happy path CRUD for users and roles
- Validation (duplicates, invalid types)
- Not found (404 for nonexistent resources)
- Policy operations (grant/restrict types)

## Deployment Checklist

1. Set environment variables:
   ```bash
   SYSTEM_DSN=postgresql+asyncpg://user:pass@host:5432/systemdb
   JWT_SECRET=your-secret-key
   JWT_ALGORITHM=HS256
   ```

2. Database:
   - Core service must have run Alembic migrations
   - Admin service connects read/write to same system_db

3. Docker:
   ```bash
   docker build -t admin-service .
   docker run -e SYSTEM_DSN=... -e JWT_SECRET=... -p 8002:8002 admin-service
   ```

4. Verification:
   ```bash
   curl http://localhost:8002/health
   curl -H "Authorization: Bearer <token>" http://localhost:8002/api/admin/users
   ```

## Notes

- All endpoints are fully implemented with working code (no TODO/pass statements)
- Every function has complete type hints and docstrings
- Database models use UUID primary keys with PostgreSQL dialect
- Pagination defaults to page=1, size=20, max size=100
- Audit endpoints are read-only (no DELETE on audit tables)
- Policy changes take effect immediately on next core request
- Service is stateless; no in-memory caching
- All database operations use async/await with asyncio
