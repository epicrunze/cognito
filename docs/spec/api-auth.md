# Auth API — `/api/auth`

Google OAuth2 flow with JWT HttpOnly cookies. Single-user mode controlled by `ALLOWED_EMAIL`.

## Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/auth/login` | No | Redirects to Google OAuth consent screen |
| GET | `/api/auth/callback` | No | OAuth callback — exchanges code, sets JWT cookie |
| GET | `/api/auth/me` | Yes | Returns current user info |
| POST | `/api/auth/logout` | No | Clears JWT cookie and stored refresh token |
| POST | `/api/auth/refresh` | No | Silent token refresh using stored Google refresh token |

## OAuth Flow

1. Frontend redirects to `GET /api/auth/login`
2. Google redirects back to `GET /api/auth/callback?code=...`
3. Backend exchanges code for Google tokens, validates email against `ALLOWED_EMAIL`
4. Creates/updates user in SQLite, stores Google refresh token (365-day expiry)
5. Issues a JWT as an HttpOnly cookie and redirects to `FRONTEND_URL`

## JWT Cookie

- **Cookie name:** `cognito_auth` (from `AUTH_COOKIE_NAME`)
- **Max age:** `jwt_expiry_hours * 3600` (configurable)
- **Flags:** `HttpOnly`, `Secure` (configurable), `SameSite` (configurable)
- **Domain:** Set via `COOKIE_DOMAIN` (e.g., `.epicrunze.com` for cross-subdomain)

## Token Refresh

`POST /api/auth/refresh` accepts **expired** JWTs — it extracts the email from unverified claims, then uses the stored Google refresh token to re-validate. On success, issues a fresh JWT cookie. On failure (e.g., revoked Google token), clears the stored refresh token and returns 401.

## Response: `GET /api/auth/me`

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "User Name",
  "picture": "https://..."
}
```

## Gotchas

- `ALLOWED_EMAIL` restricts access to a single Google account. If unset, any Google account can authenticate.
- The frontend API wrapper (`lib/api.ts`) automatically calls `/api/auth/refresh` on 401 responses before retrying.
- Logout clears both the cookie and the server-side refresh token to prevent silent re-auth.
