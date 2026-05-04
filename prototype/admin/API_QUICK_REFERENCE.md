# Admin Service API Quick Reference

## Authorization
All requests require: `Authorization: Bearer <admin_jwt_token>`

## Health Check
```bash
curl http://localhost:8002/health
```

## User Endpoints

### List Users (paginated)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8002/api/admin/users?page=1&size=20'
```

### Create User
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","oauth_sub":"oauth-123"}' \
  http://localhost:8002/api/admin/users
```

### Get User Detail
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8002/api/admin/users/{user_id}
```

### Update User Active Status
```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"active":false}' \
  http://localhost:8002/api/admin/users/{user_id}
```

### Assign Role to User
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_id":"role-uuid"}' \
  http://localhost:8002/api/admin/users/{user_id}/roles
```

### Revoke Role from User
```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8002/api/admin/users/{user_id}/roles/{role_id}
```

### Add User Policy
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"table_pattern":"users_*","policy_type":"grant"}' \
  http://localhost:8002/api/admin/users/{user_id}/policies
```

### Remove User Policy
```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8002/api/admin/users/{user_id}/policies/{policy_id}
```

## Role Endpoints

### List Roles (paginated)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8002/api/admin/roles?page=1&size=20'
```

### Create Role
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"editor"}' \
  http://localhost:8002/api/admin/roles
```

### Add Table Pattern to Role
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"table_pattern":"users_*"}' \
  http://localhost:8002/api/admin/roles/{role_id}/policies
```

### Remove Policy from Role
```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8002/api/admin/roles/{role_id}/policies/{policy_id}
```

## Audit Endpoints

### List Request Logs (paginated, filterable)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8002/api/admin/audit/requests?page=1&size=20&severity=ERROR&user_id={user_id}&start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59'
```

### List Chat Messages (paginated, filterable)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8002/api/admin/audit/chat?page=1&size=20&user_id={user_id}&session_id={session_id}'
```

## Response Formats

### Paginated Response
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20
}
```

### Error Response
```json
{
  "detail": "Error message"
}
```

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (not admin) |
| 404 | Not found |
| 500 | Server error |

## Common Filters

### Request Logs Filters
- `user_id`: UUID of user
- `severity`: INFO, WARNING, ERROR, CRITICAL
- `start_date`: ISO 8601 datetime (inclusive)
- `end_date`: ISO 8601 datetime (inclusive)

### Chat Messages Filters
- `user_id`: UUID of user
- `session_id`: UUID of session

## Policy Types
- `grant`: Grant access to a table pattern
- `restrict`: Restrict access to a table pattern

## Pagination Defaults
- Default page: 1
- Default size: 20
- Max size: 100
