# Admin Service

A FastAPI-based admin service for managing users, roles, and policies in the chat system. All endpoints require JWT authentication with the ADMIN role.

## Features

- **User Management**: Create, list, retrieve, and update users; assign/revoke roles; manage user-level policies
- **Role Management**: Create roles, list roles, assign table patterns to roles
- **Audit Logging**: Read-only paginated views of request logs and chat messages
- **JWT Authentication**: All endpoints require valid Bearer token with ADMIN role
- **Database Integration**: Connects to PostgreSQL system_db for persistence

## Architecture

```
admin/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration from environment
│   ├── db.py                # Database connection and sessions
│   ├── models/
│   │   ├── __init__.py
│   │   └── system.py        # SQLAlchemy ORM models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── jwt.py           # JWT token validation
│   │   └── deps.py          # Dependency injection
│   └── api/
│       ├── __init__.py
│       ├── users.py         # User management endpoints
│       ├── roles.py         # Role management endpoints
│       └── audit.py         # Audit log endpoints
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # pytest configuration
│   ├── test_users.py        # User endpoint tests
│   └── test_roles.py        # Role endpoint tests
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Installation

### Prerequisites
- Python 3.12+
- PostgreSQL with system_db database
- Environment variables:
  - `SYSTEM_DSN`: postgresql+asyncpg://user:password@host:5432/systemdb
  - `JWT_SECRET`: Secret key for JWT validation
  - `JWT_ALGORITHM`: HS256 (default)

### Setup

```bash
# Install dependencies
pip install .

# Or with dev dependencies
pip install ".[dev]"

# Run service
uvicorn app.main:app --host 0.0.0.0 --port 8002

# Run tests
pytest tests/
```

## Environment Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| SYSTEM_DSN | str | Yes | - | PostgreSQL connection string |
| JWT_SECRET | str | Yes | - | Secret for JWT validation |
| JWT_ALGORITHM | str | No | HS256 | JWT algorithm |

## API Endpoints

All endpoints require `Authorization: Bearer <token>` header with valid admin JWT.

### Health Check
```
GET /health
```
Returns service health and database connection status.

### User Management

#### List Users
```
GET /api/admin/users?page=1&size=20
```
Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "oauth_sub": "sub123",
      "active": true,
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20
}
```

#### Create User
```
POST /api/admin/users
```
Request:
```json
{
  "email": "newuser@example.com",
  "oauth_sub": "oauth-sub-123"
}
```

#### Get User Details
```
GET /api/admin/users/{user_id}
```
Response includes roles and policies.

#### Update User
```
PATCH /api/admin/users/{user_id}
```
Request:
```json
{
  "active": false
}
```

#### Assign Role to User
```
POST /api/admin/users/{user_id}/roles
```
Request:
```json
{
  "role_id": "role-uuid"
}
```

#### Revoke Role from User
```
DELETE /api/admin/users/{user_id}/roles/{role_id}
```

#### Add User Policy
```
POST /api/admin/users/{user_id}/policies
```
Request:
```json
{
  "table_pattern": "users_*",
  "policy_type": "grant"
}
```
Policy types: `"grant"` | `"restrict"`

#### Remove User Policy
```
DELETE /api/admin/users/{user_id}/policies/{policy_id}
```

### Role Management

#### List Roles
```
GET /api/admin/roles?page=1&size=20
```

#### Create Role
```
POST /api/admin/roles
```
Request:
```json
{
  "name": "editor"
}
```

#### Add Table Pattern to Role
```
POST /api/admin/roles/{role_id}/policies
```
Request:
```json
{
  "table_pattern": "users_*"
}
```

#### Remove Policy from Role
```
DELETE /api/admin/roles/{role_id}/policies/{policy_id}
```

### Audit Logs

#### List Request Logs
```
GET /api/admin/audit/requests?page=1&size=20&user_id=&severity=&start_date=&end_date=
```
Optional filters:
- `user_id`: Filter by user
- `severity`: Filter by severity level
- `start_date`: ISO 8601 datetime (inclusive)
- `end_date`: ISO 8601 datetime (inclusive)

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "endpoint": "/api/chat",
      "method": "POST",
      "status_code": 200,
      "latency_ms": 145,
      "violation_chunk_ids": null,
      "severity": "INFO",
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "total": 500,
  "page": 1,
  "size": 20
}
```

#### List Chat Messages
```
GET /api/admin/audit/chat?page=1&size=20&user_id=&session_id=
```
Optional filters:
- `user_id`: Filter by user
- `session_id`: Filter by session

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "session_id": "uuid",
      "user_id": "uuid",
      "role": "user",
      "content": "Hello, assistant!",
      "chunk_ids": null,
      "guardrail_result": null,
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "total": 1000,
  "page": 1,
  "size": 20
}
```

## Authentication

JWT tokens must include:
- `sub`: User ID (UUID string)
- `role_ids`: Array of role IDs (UUID strings)

The token must contain the admin role ID to access any endpoint.

Example decoded token:
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "role_ids": ["550e8400-e29b-41d4-a716-446655440001"],
  "exp": 1234567890
}
```

## Database Schema

The service uses the following tables from system_db:

- **users**: User accounts
- **roles**: Role definitions
- **user_roles**: User-role associations
- **role_policies**: Role-level table pattern policies
- **user_policies**: User-level table pattern policies
- **request_log**: Request audit trail
- **chat_messages**: Chat message history

All tables are managed by the core service's Alembic migrations.

## Error Handling

All errors return JSON with appropriate HTTP status codes:

```json
{
  "detail": "Error message"
}
```

Common status codes:
- 200: Success
- 201: Created
- 400: Bad request
- 401: Unauthorized
- 403: Forbidden
- 404: Not found
- 500: Internal server error

## Testing

Run tests with pytest:

```bash
pytest tests/
pytest tests/test_users.py -v
pytest tests/test_roles.py -v
```

The test suite includes:
- Authentication and authorization tests
- CRUD operations for users and roles
- Policy management tests
- Pagination tests
- Error handling tests

## Docker

Build and run with Docker:

```bash
docker build -t admin-service .
docker run -e SYSTEM_DSN="postgresql+asyncpg://..." \
           -e JWT_SECRET="your-secret" \
           -p 8002:8002 \
           admin-service
```

## Notes

- All endpoints are read-write for users/roles, read-only for audit logs
- Policy changes take effect immediately on the next request to core
- Pagination defaults: page=1, size=20 (max 100)
- Dates in filters use ISO 8601 format
- The service does not manage system_db schema; core service owns migrations
