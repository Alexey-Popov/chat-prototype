# Chat UI

React + TypeScript + Vite chat application frontend.

## Features

- OAuth login redirects to `GET /auth/login` (core service)
- Dev login button: calls `GET /auth/dev-login?email=dev@example.com` (when DEV_MOCK_USER enabled)
- Chat page with text input and SSE streaming from `POST /api/chat`
- JWT stored in memory only (never localStorage/sessionStorage)
- Logout clears JWT from memory

## Development

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Environment Variables

- `VITE_CORE_URL` - Core service URL (default: http://localhost:8000)
- `VITE_DEV_MOCK_USER` - Enable dev login button (set to 'true')

## Build

```bash
npm run build
```

Output in `dist/`

## Docker

```bash
docker build -t chat-ui .
docker run -p 3000:80 chat-ui
```
