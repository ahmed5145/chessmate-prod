# Social & OAuth Authentication Plan

**Status:** Planning / audit (not implemented)  
**Last updated:** 2026-06-08  
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

1. Create OAuth 2.0 Client (Web application)
2. Authorized redirect URIs:
   - Dev: `http://localhost:8000/api/v1/auth/google/callback/`
   - Staging: `https://staging.<domain>/api/v1/auth/google/callback/`
   - Prod: `https://<domain>/api/v1/auth/google/callback/`
3. Scopes: `openid email profile` (minimum)
4. Store `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` in env (never commit)

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

### Frontend work

- Add Google button to `Login.js` and `Register.js` (match MUI/Tailwind patterns)
- Handle callback route e.g. `/auth/google/callback` that reads tokens from query/hash or calls backend session endpoint
- Loading + error states (denied consent, email already used, etc.)

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

## Phased rollout

| Phase | Scope | Env | Success metric |
|-------|--------|-----|----------------|
| **0** | Chess.com OAuth application submitted | N/A | Approval received |
| **1** | Google login/register | Staging → prod | % signups via Google; fewer verification support tickets |
| **2** | Lichess login/register + auto username | Staging → prod | Faster onboarding to first batch |
| **3** | Chess.com login (if approved) | Staging → prod | Chess.com users skip manual username |
| **4** | Settings: link/unlink providers | Prod | Users merge accounts safely |

**Staging first** — per `docs/SHIP_CONTRACT.md`, auth flows should be validated on staging before prod smoke.

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
