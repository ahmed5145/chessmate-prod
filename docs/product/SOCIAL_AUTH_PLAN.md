# Social & OAuth Authentication Plan

**Status:** Phase 1 (Google) implemented — EB configured; publish consent screen to **In production** (not Testing)  
**Last updated:** 2026-06-10  
**Audience:** Engineering + product  

## Summary

ChessMate today uses **email + password** with **JWT** (`rest_framework_simplejwt`) and mandatory **email verification** before login (`core/auth_views.py`, `Profile.email_verified`). Users manually enter `lichess_username` and `chess_com_username` on their profile; game import uses **public APIs** (`LichessService`, `ChessComService` in `core/chess_services.py`) — not OAuth.

This document audits adding:

| Provider | Register | Sign in | Self-service? | Recommendation |
|----------|----------|---------|---------------|----------------|
| **Google** | Yes | Yes | Yes (Google Cloud Console) | **Phase 1** — lowest friction, standard UX |
| **Lichess** | Yes | Yes | Yes (no client registration) | **Phase 2** — strong product fit, auto-fill username |
| **Chess.com** | Yes | Yes | **No** — apply via form | **Phase 3** — apply early; ship username import until approved |

---

## Current architecture

### Backend

- Endpoints under `/api/v1/auth/` (`core/urls_auth.py`):
  - `register/`, `login/`, `logout/`, `token/refresh/`
  - Password reset, email verify/resend, CSRF helpers
- Auth logic: `core/auth_views.py`
- User model: Django `User` + `Profile` (`core/models.py`)
  - `email_verified`, `email_verification_token`
  - `chess_com_username`, `lichess_username` (plain text, user-edited)
- Abuse limits on signup/login/reset (`core/abuse_limits.py`)
- No `django-allauth`, `social-auth-app-django`, or Google/Lichess/Chess.com OAuth code in repo today

### Frontend

- `frontend/src/components/Login.js`, `Register.js` — email/password only
- Tokens via `frontend/src/utils/tokenStorage.js` + `apiRequests`
- No “Continue with Google/Lichess/Chess.com” buttons

### Implications for OAuth

1. **Email verification gate** — OAuth users with verified provider email should be treated as verified (skip token flow).
2. **JWT issuance** — After OAuth callback, backend creates/links `User`, then returns same JWT pair as password login (keep frontend auth unchanged).
3. **Account linking** — Same email from Google + existing password account must merge or prompt, not duplicate.
4. **Credits / referrals** — Signup abuse limits still apply; OAuth is not a bypass.

---

## Phase 1 — Google Sign-In / Register

### Why first

- Self-service setup in [Google Cloud Console](https://console.cloud.google.com/)
- Users expect it on SaaS products
- Provides verified email without custom mail flow
- No dependency on Chess.com approval

### Recommended approach

**Option A (recommended):** Lightweight custom OAuth 2.0 flow

- Backend endpoints:
  - `GET /api/v1/auth/google/start/` — redirect to Google with `state` + PKCE (if SPA) or server-side code flow
  - `GET /api/v1/auth/google/callback/` — exchange code, upsert user, issue JWT, redirect to frontend with tokens or set httpOnly cookies
- Store minimal data: `google_sub` (stable Google user id), email, name
- New model or `Profile.preferences` field: `oauth_providers: { google: { sub, linked_at } }`

**Option B:** `django-allauth` or `social-auth-app-django`

- Faster if we want many providers later
- Heavier dependency; must integrate with existing JWT + custom `Profile` signals
- Only worth it if Lichess + Chess.com + Google all land in one library

### Google Cloud setup

1. Create OAuth 2.0 Client (Web application) — name e.g. **ChessMate Login**
2. **Authorized redirect URIs** (backend callback — required):
   - Dev: `http://localhost:8000/api/v1/auth/google/callback/`
   - Prod: `https://www.chess-mate.online/api/v1/auth/google/callback/`
   - (Optional) EB hostname if users hit it directly: `https://chessmate-prod.us-east-2.elasticbeanstalk.com/api/v1/auth/google/callback/`
3. **Authorized JavaScript origins** (optional for our server redirect flow; safe to add):
   - Dev: `http://localhost:3000`
   - Prod: `https://www.chess-mate.online`
4. Scopes: `openid email profile` (minimum — non-sensitive)
5. Store `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` in env (never commit)

### OAuth consent screen — branding (production)

Fill **Branding** so the consent screen is trustworthy:

| Field | Value |
|-------|--------|
| App name | ChessMate |
| User support email | Public support inbox (e.g. `support@chess-mate.online`) |
| Authorized domains | `chess-mate.online` |
| Application home page | `https://www.chess-mate.online/` |
| Application privacy policy link | `https://www.chess-mate.online/privacy` |
| Application terms of service link | `https://www.chess-mate.online/terms` |

**App logo:** Skip until ready for Google verification. Uploading a logo can require **app verification** even when scopes are basic.

**Publishing status (required for real users):**

- **Testing** = only accounts listed under **Audience → Test users** (max 100) can sign in. Everyone else sees *access blocked*.
- **In production** = any Google user can sign in.

To leave Testing:

1. Complete branding links above (home, privacy, terms must be live HTTPS).
2. **Google Auth Platform → Audience** → **Publishing status** → **Publish app** → **In production**.
3. ChessMate only requests `openid`, `email`, `profile` — usually **no full verification** required for production without a logo. If Google prompts for verification, submit the form; typical turnaround is days, not weeks.

Do **not** rely on Testing in prod after launch — add test users only for pre-launch QA, then publish.

### Troubleshooting `redirect_uri_mismatch` (Error 400)

Google compares the `redirect_uri` query param **byte-for-byte** with **Authorized redirect URIs**. Common mismatches:

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| Local dev fails | OAuth started on `:3000` instead of Django `:8000` | Put `REACT_APP_API_URL=http://localhost:8000` in `chess_mate/frontend/.env.local`; or rely on fixed `googleAuth.js` default |
| Local dev fails | Used `127.0.0.1` but Console has `localhost` | Add **both** to Google Console, or always use `localhost` |
| Prod fails | Django built `http://…` but Console has `https://…` | Set EB `FRONTEND_URL=https://www.chess-mate.online` and redeploy; or set explicit `GOOGLE_OAUTH_REDIRECT_URI` (below) |
| Prod fails | Site opened as `chess-mate.online` (no `www`) | Add `https://chess-mate.online/api/v1/auth/google/callback/` to Console **or** redirect apex → `www` |
| Any env | Django sent `/api/api/v1/...` (double `api`) | Fixed in code — canonical path is `/api/v1/auth/google/callback/`; redeploy backend |
| Any env | Missing trailing `/` | Console URIs must end with `/` — our backend normalizes to trailing slash |

**See the exact URI Django sends:** check Django logs after clicking Continue with Google:

```text
Google OAuth start redirect_uri=https://...
```

That string must appear **verbatim** in Google Console.

**Explicit override (recommended on EB after first mismatch):**

| Env | Variable |
|-----|----------|
| Local root `.env` | `GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback/` |
| EB | `GOOGLE_OAUTH_REDIRECT_URI=https://www.chess-mate.online/api/v1/auth/google/callback/` |

Restart Django / EB app servers after changing env.

**Minimum Google Console redirect URIs (recommended set):**

1. `http://localhost:8000/api/v1/auth/google/callback/`
2. `http://127.0.0.1:8000/api/v1/auth/google/callback/` (optional, if you use 127.0.0.1)
3. `https://www.chess-mate.online/api/v1/auth/google/callback/`
4. `https://chess-mate.online/api/v1/auth/google/callback/` (optional, if apex URL is used)

### User flows

**New user (register via Google)**

1. Click “Continue with Google” on Register or Login
2. Google consent → callback
3. If no `User` with that email: create `User` + `Profile`, set `email_verified=True`, issue JWT
4. Redirect to dashboard / onboarding (optional: prompt for Lichess/Chess.com username)

**Existing email/password user**

1. If Google email matches existing `User`:
   - **Preferred:** Link Google to account after password confirmation OR one-time “link” from Settings
   - **Avoid:** Silent merge without user consent (security risk)
2. If emails differ: treat as separate account unless user explicitly links

**Login**

- Same as register path; if user exists and Google linked (or email match policy), issue JWT

### Frontend work (done)

- `GoogleSignInButton` on `Login.js` and `Register.js`
- `/auth/google/callback` reads JWT hash, stores tokens, redirects to dashboard
- Button hidden unless `GET /api/v1/public/site-config/` → `google_oauth_enabled: true`

### Tests

- Callback creates user + verified profile
- Callback logs in existing linked user
- Duplicate email policy
- Rate limits still enforced where applicable
- JWT payload unchanged for frontend

---

## Phase 2 — Lichess Sign-In / Register

### Feasibility: **Yes — fully self-service**

Lichess supports **OAuth 2.0 Authorization Code + PKCE** with **no client registration**. Pick any unique `client_id` string (e.g. `chessmate-prod`).

Official spec: [lichess-org/api — lichess-api.yaml](https://github.com/lichess-org/api/blob/master/doc/specs/lichess-api.yaml)

| Item | Value |
|------|--------|
| Authorization | `https://lichess.org/oauth` |
| Token | `POST https://lichess.org/api/token` |
| PKCE | Required; only `S256` |
| Client secret | None |
| Refresh tokens | **Not supported** |
| Access token lifetime | ~1 year (until revoked) |
| Account info | `GET /api/account` (username, perfs, etc.) |
| Email | `GET /api/account/email` — requires `email:read` scope |

### Recommended scopes for ChessMate

| Scope | Purpose |
|-------|---------|
| `preference:read` | Light profile context (optional) |
| `email:read` | Stable account identity + linking |

Do **not** request write/board scopes unless we add features that need them (principle of least privilege).

### Implementation flow

1. `GET /api/v1/auth/lichess/start/` — generate `state`, `code_verifier`, redirect to Lichess
2. `GET /api/v1/auth/lichess/callback/` — exchange code with `code_verifier`, fetch `/api/account` + `/api/account/email`
3. Upsert user:
   - Set `Profile.lichess_username` from account id
   - Optionally store encrypted Lichess access token for future private API use (game fetch today is public by username)
4. Issue JWT → frontend

### Product benefits

- One-click signup for Lichess-heavy audience
- Username pre-filled for batch game import
- Marketing alignment with “connect your games” story

### Risks / notes

- Email may be absent or user may deny `email:read` — fallback: link by Lichess username + require email capture step
- Long-lived tokens: store encrypted at rest; allow disconnect/revoke in Settings
- Token in DB is sensitive — never expose to frontend

### PKCE reference (backend)

```
code_verifier  = random 43–128 chars
code_challenge = BASE64URL(SHA256(code_verifier))
authorize URL  = lichess.org/oauth?response_type=code&client_id=...&redirect_uri=...&scope=email:read&code_challenge_method=S256&code_challenge=...
token POST     = grant_type=authorization_code&code=...&code_verifier=...&client_id=...&redirect_uri=...
```

---

## Phase 3 — Chess.com Sign-In / Register

### Feasibility: **Yes, but not self-service**

Chess.com OAuth exists but requires **approval**:

- [Developer Community club](https://www.chess.com/club/chess-com-developer-community) — “OAuth & Connected Board Access”
- [Application form](https://docs.google.com/forms/d/e/1FAIpQLSds2AeKLj9xqgu96Pu-rEAS0ItyqDbZbSgUFer0Mo6qMRx4Jg/viewform) (also linked from [PubAPI help](https://support.chess.com/en/articles/9650547-what-is-the-pubapi-and-how-do-i-use-it))

Until approved:

- **Cannot** ship production Chess.com OAuth buttons
- **Can** continue public username-based game fetch (current behavior)
- **Should** submit application now with staging redirect URIs to reduce calendar risk

### Known endpoints (post-approval)

From community docs and developer examples:

| Step | URL |
|------|-----|
| Authorize | `https://oauth.chess.com/authorize` |
| Token | `POST https://oauth.chess.com/token` |
| Flow | Authorization code + PKCE (`S256`) |
| Typical scope | `openid` (confirm additional scopes with Chess.com when approved) |

You receive `client_id` (and possibly secret) after approval — unlike Lichess.

### Implementation (after credentials)

Mirror Lichess pattern:

1. Start/callback endpoints under `/api/v1/auth/chesscom/`
2. Set `Profile.chess_com_username` from token/userinfo
3. Issue JWT

### Interim UX

- “Import from Chess.com” remains username entry
- Settings: “Link Chess.com (coming soon)” or hide until approved
- Do not hardcode client IDs in repo

---

## Data model (proposed)

Minimal extension without over-engineering:

```python
# Option A: JSON on Profile.preferences (fastest)
preferences = {
  "oauth": {
    "google": {"sub": "...", "linked_at": "..."},
    "lichess": {"username": "...", "linked_at": "..."},
    "chesscom": {"username": "...", "linked_at": "..."}
  }
}

# Option B: dedicated SocialAccount model (cleaner if multiple providers per user)
class SocialAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20)  # google | lichess | chesscom
    provider_user_id = models.CharField(max_length=255)
    extra_data = models.JSONField(default=dict)
    access_token_encrypted = models.TextField(blank=True)  # lichess/chesscom only if needed
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = [("provider", "provider_user_id")]
```

**Recommendation:** Start with **Option B** if implementing 2+ providers; avoids messy JSON migrations and supports “disconnect provider” cleanly.

---

## Security checklist

- [ ] `state` parameter on all OAuth starts (CSRF)
- [ ] PKCE on Lichess and Chess.com (and Google public clients)
- [ ] HTTPS-only redirect URIs in prod/staging
- [ ] Encrypt provider tokens at rest (Fernet or DB field encryption)
- [ ] Never log access tokens or authorization codes
- [ ] Account takeover: require re-auth (password or existing session) before linking a new provider to an logged-in account
- [ ] Abuse: apply signup rate limits to OAuth-created accounts (by IP + provider id)
- [ ] Email collision policy documented and tested

---

## Environment variable consolidation (pre-staging)

**Problem:** Secrets and URLs are split across repo root `.env`, `.env.local`, `.env.production`, `chess_mate/frontend/.env.local`, and Elastic Beanstalk. Easy to put Google keys in the wrong file or forget EB restart.

**Source of truth (target):**

| Layer | File / store | What belongs here |
|-------|----------------|-------------------|
| **Django (local)** | Repo root only: `chessmate_prod/.env` or `.env.local` | `GOOGLE_OAUTH_*`, `FRONTEND_URL`, `SECRET_KEY`, DB, Redis, Stripe, OpenAI |
| **Django (prod)** | **EB environment properties** only | Same keys as prod needs; never commit |
| **React (local `npm start`)** | `chess_mate/frontend/.env.local` | **`REACT_APP_API_URL=http://localhost:8000`** (required for API calls; Google OAuth also needs Django on :8000) |
| **React (prod build)** | Empty `REACT_APP_API_URL` | Same-origin `/api/v1/...` — do **not** set on EB or CI |

### Redis (local)

| Mode | `REDIS_DISABLED` | `ENABLE_CELERY` | When |
|------|------------------|-----------------|------|
| **Full dev** (batch/analysis) | `False` | `true` | Run Redis + Celery worker (`start_services.bat` or `docker compose up redis`) |
| **UI / OAuth only** | `True` | `false` | Login, Google sign-in, browse UI — no async analysis |

`REDIS_PASSWORD` — leave **empty** for local Redis and EB bundled Redis (`127.0.0.1:6379`, no auth). Only set when your Redis provider requires a password.

Do **not** set `REDIS_DISABLED=True` with `ENABLE_CELERY=true` — Celery still expects Redis and analysis jobs will stick at `PENDING`.

Django loads env from **repo root** (`PROJECT_ROOT` in `chess_mate/chess_mate/settings.py`), in order:

1. `.env.{ENVIRONMENT}.local`
2. `.env.local`
3. `.env.{ENVIRONMENT}`
4. `.env`

There is **no** `chess_mate/.env` — do not create one for OAuth.

**Google OAuth checklist:**

| Where | Variables |
|-------|-----------|
| Local root `.env` | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `FRONTEND_URL=http://localhost:3000`, optional `GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback/` |
| EB | Same client ID/secret, `FRONTEND_URL=https://www.chess-mate.online`, optional `GOOGLE_OAUTH_REDIRECT_URI=https://www.chess-mate.online/api/v1/auth/google/callback/` |
| Frontend | None (no Google secrets in CRA) |

After EB changes: **Restart app server(s)**.

**Consolidation task (before dedicated staging env):**

- [ ] Document one local template: root `.env.example` (already includes Google vars)
- [ ] Delete or stop using stray `chess_mate/.env` if it exists
- [ ] Keep `frontend/.env.local` limited to `REACT_APP_*`
- [ ] Mirror prod secrets only on EB (and optional gitignored `.env.production` for local `manage.py` against prod RDS — same pattern as Stripe in `docs/PROD_OPS.md`)
- [ ] When staging exists: separate EB env + Google redirect URI `https://staging.chess-mate.online/api/v1/auth/google/callback/` (or subdomain you choose)

---

## Phased rollout

| Phase | Scope | Env | Success metric |
|-------|--------|-----|----------------|
| **0** | Chess.com OAuth application submitted | N/A | Approval received |
| **0b** | Env consolidation + Google consent **In production** | Prod EB + root `.env` | Any user can Google sign-in; no Testing gate |
| **1** | Google login/register | Staging → prod | % signups via Google; fewer verification support tickets |
| **2** | Lichess login/register + auto username | Staging → prod | Faster onboarding to first batch |
| **3** | Chess.com login (if approved) | Staging → prod | Chess.com users skip manual username |
| **4** | Settings: link/unlink providers | Prod | Users merge accounts safely |

**Staging first** — per `docs/SHIP_CONTRACT.md`, auth flows should be validated on staging before prod smoke (once staging EB exists).

---

## Open questions for product

1. **Email collision:** Auto-link if Google email matches verified account, or always require password?
2. **OAuth-only accounts:** Allow users with no password (password reset becomes “set password” in Settings)?
3. **Lichess without email:** Block signup or collect email in a second step?
4. **Marketing:** Show all three buttons at launch or Google-only until others ready?
5. **Referral codes:** Preserve `referral_code` on OAuth signup when `?ref=` present?

---

## Effort estimate (engineering)

| Item | Rough effort |
|------|----------------|
| Google OAuth (backend + frontend + tests) | 2–4 days |
| Lichess OAuth | 1–2 days (after Google pattern exists) |
| Chess.com OAuth | 1–2 days **after approval** |
| SocialAccount model + Settings UI | 2–3 days |
| **Total (Google + Lichess + linking UI)** | ~1–2 weeks |

Chess.com calendar depends on Chess.com response time, not implementation.

---

## References

- Lichess API auth: https://github.com/lichess-org/api/blob/master/doc/specs/lichess-api.yaml
- Lichess OAuth demo: https://lichess-org.github.io/api-demo/
- Chess.com developer club: https://www.chess.com/club/chess-com-developer-community
- Chess.com OAuth application: https://docs.google.com/forms/d/e/1FAIpQLSds2AeKLj9xqgu96Pu-rEAS0ItyqDbZbSgUFer0Mo6qMRx4Jg/viewform
- Google OAuth 2.0: https://developers.google.com/identity/protocols/oauth2
- ChessMate auth today: `chess_mate/core/auth_views.py`, `chess_mate/core/urls_auth.py`
