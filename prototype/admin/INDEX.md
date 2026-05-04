# Admin Service - Complete Implementation Index

## Quick Start

```bash
# Install dependencies
pip install .

# Set environment variables
export SYSTEM_DSN="postgresql+asyncpg://user:password@system_db:5432/systemdb"
export JWT_SECRET="your-secret-key"

# Run service
uvicorn app.main:app --host 0.0.0.0 --port 8002

# Run tests
pip install ".[dev]"
pytest tests/ -v
```

## Documentation

- **README.md** - Full user guide with API documentation
- **IMPLEMENTATION_NOTES.md** - Technical implementation details
- **API_QUICK_REFERENCE.md** - curl examples for all endpoints
- **FILES.md** - Complete file structure and descriptions

## Key Files by Purpose

### Application Code
- **app/main.py** - FastAPI application entry point
- **app/config.py** - Configuration from environment
- **app/db.py** - Database connection and session management
- **app/models/system.py** - SQLAlchemy ORM models

### Authentication & Authorization
- **app/core/jwt.py** - JWT token validation
- **app/core/deps.py** - Admin authorization dependency injection

### API Endpoints
- **app/api/users.py** - User management (create, list, assign roles, manage policies)
- **app/api/roles.py** - Role management (create, list, manage policies)
- **app/api/audit.py** - Audit log viewers (request logs, chat messages)

### Testing
- **tests/conftest.py** - pytest fixtures and configuration
- **tests/test_users.py** - User endpoint tests (13 test cases)
- **tests/test_roles.py** - Role endpoint tests (7 test cases)

### Deployment
- **Dockerfile** - Container image definition
- **pyproject.toml** - Python dependencies
- **.env.example** - Environment variable template

## API Endpoints at a Glance

### Health
- `GET /health` - Service health check

### Users (8 endpoints)
- `GET /api/admin/users` - List users (paginated)
- `POST /api/admin/users` - Create user
- `GET /api/admin/users/{user_id}` - Get user details
- `PATCH /api/admin/users/{user_id}` - Update user (active flag)
- `POST /api/admin/users/{user_id}/roles` - Assign role
- `DELETE /api/admin/users/{user_id}/roles/{role_id}` - Revoke role
- `POST /api/admin/users/{user_id}/policies` - Add policy
- `DELETE /api/admin/users/{user_id}/policies/{policy_id}` - Remove policy

### Roles (4 endpoints)
- `GET /api/admin/roles` - List roles (paginated)
- `POST /api/admin/roles` - Create role
- `POST /api/admin/roles/{role_id}/policies` - Add table pattern
- `DELETE /api/admin/roles/{role_id}/policies/{policy_id}` - Remove policy

### Audit Logs (2 endpoints, read-only)
- `GET /api/admin/audit/requests` - List request logs (paginated, filterable)
- `GET /api/admin/audit/chat` - List chat messages (paginated, filterable)

## Database Tables

The service uses the following tables from `system_db`:

**Managed by Admin Service:**
- `users` - User accounts
- `roles` - Role definitions
- `user_roles` - User-role associations
- `role_policies` - Role table permissions
- `user_policies` - User table permissions

**Read-Only Audit Tables:**
- `request_log` - API request history
- `chat_messages` - Chat conversation history

Note: Admin service does not manage database schema migrations. The core service owns all Alembic migrations.

## Security Model

All endpoints require `Authorization: Bearer <jwt_token>` header.

The JWT token must include:
- `sub`: User UUID (string)
- `role_ids`: Array of role UUIDs (strings)
- `exp`: Token expiration timestamp

The admin service verifies:
1. Token signature using JWT_SECRET
2. Token has not expired
3. User exists and is active in database
4. User has the 'admin' role

Returns:
- 401 Unauthorized if token is invalid/expired
- 403 Forbidden if user lacks admin role

## Development

### Running Tests
```bash
# Install dev dependencies
pip install ".[dev]"

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_users.py -v

# Run with coverage
pytest tests/ --cov=app
```

### Database for Development

Use PostgreSQL locally:
```bash
# Create test database
createdb systemdb

# Run Alembic migrations from core service first
# Then set environment variable
export SYSTEM_DSN="postgresql://user:password@localhost:5432/systemdb"
```

Or use SQLite in-memory for testing (see conftest.py).

### Code Organization

```
app/
├── main.py              # Application root
├── config.py            # Environment-based settings
├── db.py                # Database setup
├── models/
│   └── system.py        # ORM models (7 models)
├── core/
│   ├── jwt.py           # Token validation
│   └── deps.py          # Authorization dependency
└── api/
    ├── users.py         # User endpoints (8)
    ├── roles.py         # Role endpoints (4)
    └── audit.py         # Audit endpoints (2)
```

## Deployment

### Docker

```bash
# Build image
docker build -t admin-service .

# Run container
docker run \
  -e SYSTEM_DSN="postgresql+asyncpg://user:pass@host:5432/systemdb" \
  -e JWT_SECRET="your-secret-key" \
  -p 8002:8002 \
  admin-service
```

### Environment Variables

| Variable | Required | Example |
|----------|----------|---------|
| SYSTEM_DSN | Yes | postgresql+asyncpg://user:pass@localhost:5432/systemdb |
| JWT_SECRET | Yes | super-secret-key-change-in-prod |
| JWT_ALGORITHM | No | HS256 (default) |

### Health Check

```bash
curl http://localhost:8002/health
```

Response when healthy:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

## Common Tasks

### Create an Admin User
```bash
# First, use the core service or database to create a user
# Then assign the admin role via this service

curl -X POST http://localhost:8002/api/admin/users/{user_id}/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_id":"<admin-role-uuid>"}'
```

### View User Policies
```bash
curl http://localhost:8002/api/admin/users/{user_id} \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### List All Requests from a User
```bash
curl "http://localhost:8002/api/admin/audit/requests?user_id={user_id}" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Filter Request Logs by Severity
```bash
curl "http://localhost:8002/api/admin/audit/requests?severity=ERROR" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Troubleshooting

### "User does not have admin role" (403)
- Verify the JWT token contains admin role ID
- Verify admin role exists in database
- Verify user-role association exists

### "Invalid or expired token" (401)
- Check JWT_SECRET matches what was used to create token
- Check token hasn't expired
- Check Authorization header format: `Bearer <token>`

### "User not found or inactive" (401)
- Verify user exists in database
- Verify user.active = true

### "Cannot connect to database"
- Check SYSTEM_DSN is correct
- Verify PostgreSQL is running and accessible
- Verify connection string format: `postgresql+asyncpg://user:pass@host:port/db`

## Performance Notes

- All database operations use async/await
- Connection pooling with health checks enabled
- Pagination defaults to 20 items, max 100
- No N+1 queries (joins are explicit)
- Filtering is done at database level

## Future Enhancements

Potential improvements for future versions:
- Batch operations for users/roles
- User invitation/email verification
- Role templates/default policies
- Audit log retention policies
- Performance metrics/analytics
- Advanced permission expressions

## License & Support

This is part of the chat system prototype. For issues or questions, refer to the main project documentation.
