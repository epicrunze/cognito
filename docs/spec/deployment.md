# Deployment

## Docker Compose

Three containers, all behind Cloudflare tunnels (no ports exposed to the internet):

| Container | Internal Port | Tunnel URL |
|-----------|--------------|------------|
| Vikunja | 3456 | `tasks.epicrunze.com` (admin only) |
| Frontend (nginx) | 80 | `cognito.epicrunze.com` |
| Backend (FastAPI) | 8000 | `api-cognito.epicrunze.com` |

## Network Architecture

```
Internet -> Cloudflare Tunnels -> Docker containers
                                   |
Frontend (nginx:80) -----> Backend (FastAPI:8000) -----> Vikunja (3456)
                    /api                          internal Docker network
```

- **Backend to Vikunja**: Internal Docker network only (`http://vikunja:3456`). Set via `VIKUNJA_URL` env var.
- **Frontend to Backend**: Via Cloudflare tunnel in production. In dev, Vite proxy (`/api` -> `localhost:8000`).

## Frontend API URL

`PUBLIC_API_URL` is a **SvelteKit build-time env var** (baked in by static adapter). Pass as Docker build arg:

```yaml
args:
  PUBLIC_API_URL: ${BACKEND_URL}
```

In dev, leave unset -- falls back to `/api` (Vite proxy).

## CORS

`FRONTEND_URL` origin is allowed with credentials in `backend/app/main.py`. Must match the frontend's Cloudflare tunnel URL exactly.

## Cookies

`COOKIE_DOMAIN=.epicrunze.com` -- covers both `cognito.epicrunze.com` (frontend) and `api-cognito.epicrunze.com` (backend) subdomains. JWT stored as HttpOnly cookie.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VIKUNJA_API_TOKEN` | Yes | Vikunja API bearer token |
| `VIKUNJA_URL` | No | Vikunja base URL (default: `http://vikunja:3456`) |
| `GEMINI_API_KEY` | Yes* | Google Gemini API key (*or use Ollama) |
| `GEMINI_MODEL` | No | Gemini model name |
| `OLLAMA_URL` | No | Ollama server URL |
| `OLLAMA_MODEL` | No | Ollama model name |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth2 client secret |
| `ALLOWED_EMAIL` | Yes | Email allowed to log in |
| `JWT_SECRET` | Yes | Secret for JWT signing |
| `COOKIE_DOMAIN` | No | Cookie domain (default: localhost) |
| `FRONTEND_URL` | Yes | Frontend origin for CORS |
| `PUBLIC_API_URL` | No | Build-time backend URL for frontend |
