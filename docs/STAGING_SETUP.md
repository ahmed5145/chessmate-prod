# Staging environment setup (production parity)

Staging runs the **same stack as production**: GitHub Actions → ECR Docker image → Elastic Beanstalk → bundled Redis + Celery in-container → RDS PostgreSQL → WhiteNoise SPA.

Use staging to validate OAuth, batches, payments, and deploys **before** pushing to `main`.

## Architecture

| Piece | Production | Staging |
|-------|------------|---------|
| EB app | `chessmate` | `chessmate` (same app) |
| EB environment | `Chessmate-env-2` | `ChessMate-Staging` |
| CD trigger | push to `main` | push to `staging` |
| Docker image | ECR `chessmate:chessmate-production-*` | ECR `chessmate:chessmate-staging-*` |
| Database | RDS (prod DB) | **Separate** RDS DB |
| Domain (target) | `www.chess-mate.online` | `staging.chess-mate.online` (or EB default URL) |

## One-time AWS setup

### 1. Create EB environment

1. AWS Console → **Elastic Beanstalk** → Application **chessmate** → **Create environment**.
2. Name: **`ChessMate-Staging`**.
3. Platform: **Docker** (same as prod).
4. Instance: same or smaller tier (e.g. `t3.small`).
5. VPC / security groups: mirror prod so the instance can reach RDS.

### 2. Create staging RDS

Do **not** share the production database.

1. RDS → Create database → PostgreSQL (same major version as prod).
2. DB identifier: e.g. `chessmate-staging`.
3. Database name: e.g. `chessmate_staging`.
4. Place in the same VPC as the staging EB environment.
5. Security group: allow inbound **5432** from the staging EB instance security group only.

### 3. IAM

Reuse the same deploy user (`chessmate-deploy`) and EC2 instance profile as production:

- GitHub user: ECR push + Beanstalk deploy (already in [DEPLOY_EB_ECR.md](./DEPLOY_EB_ECR.md)).
- EB instance role: `AmazonEC2ContainerRegistryReadOnly`.

### 4. TLS (optional but recommended)

1. ACM certificate for `staging.chess-mate.online` (or use EB default `*.elasticbeanstalk.com` for first smoke).
2. ALB HTTPS listener on 443 → forward to container `:8000`.
3. Route 53 CNAME: `staging.chess-mate.online` → staging ALB.

## Elastic Beanstalk environment variables

Set on **ChessMate-Staging** → Configuration → Software → Environment properties.

Copy production values, then override hostnames and keys.

### Required

| Variable | Staging example |
|----------|-----------------|
| `ENVIRONMENT` | `staging` |
| `DEBUG` | `False` |
| `SECRET_KEY` | New random string (not prod's key) |
| `DJANGO_SETTINGS_MODULE` | `chess_mate.settings` |
| `DB_HOST` | Staging RDS endpoint |
| `DB_NAME` | `chessmate_staging` |
| `DB_USER` | RDS user |
| `DB_PASSWORD` | RDS password |
| `DB_PORT` | `5432` |
| `USE_BUNDLED_REDIS` | `true` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` |
| `REDIS_HOST` | `127.0.0.1` |
| `REDIS_PORT` | `6379` |
| `ENABLE_CELERY` | `true` |
| `ALLOWED_HOSTS` | `staging.chess-mate.online,<eb-staging-host>.elasticbeanstalk.com` |
| `FRONTEND_URL` | `https://staging.chess-mate.online` |
| `CSRF_TRUSTED_ORIGINS` | `https://staging.chess-mate.online` |

### Integrations (use test / staging credentials)

| Variable | Notes |
|----------|-------|
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | Same or separate OAuth client; add redirect URI `https://staging.chess-mate.online/api/v1/auth/google/callback/` |
| `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` | **Test mode** keys only |
| `STRIPE_WEBHOOK_SECRET` | Staging webhook endpoint |
| `OPENAI_API_KEY` | Shared or separate; staging is fine for smoke |
| `EMAIL_*` | Staging SMTP or mail catcher; required for password-reset smoke |
| `DJANGO_ADMIN_PATH` | Non-default path (same pattern as prod) |

### Do not set on EB

- `REACT_APP_API_URL` — CD builds with empty value; setting it causes `/api/api/v1/...` double prefix.
- `REDIS_DISABLED=true` — disables Celery/batches.

`ENVIRONMENT=staging` enables Postgres, Redis, Celery, and SMTP behavior via `IS_DEPLOYED` in `chess_mate.settings` (same infra path as production).

## GitHub configuration

### Environment: `staging`

Repository → Settings → Environments → **staging** (create if missing).

| Type | Name | Value |
|------|------|-------|
| Variable | `HEALTHCHECK_URL` | `https://staging.chess-mate.online/readiness/` (or EB URL) |
| Variable | `AWS_REGION` | `us-east-2` |
| Secret | `AWS_ACCESS_KEY_ID` | Same deploy user as prod (or scoped staging user) |
| Secret | `AWS_SECRET_ACCESS_KEY` | … |

Remove legacy SSH staging secrets (`STAGING_HOST`, `STAGING_USERNAME`, `STAGING_SSH_KEY`, `STAGING_PORT`) — CD no longer uses them.

### Deploy flow

```text
feature branch → PR → merge to staging → CD deploys ChessMate-Staging
smoke pass (STAGING_SMOKE.md) → merge staging → main → CD deploys Chessmate-env-2
```

Manual deploy: Actions → **ChessMate CD** → Run workflow → choose `staging` or `production`.

## Post-deploy verification

```bash
curl -fsS https://staging.chess-mate.online/health/
curl -fsS https://staging.chess-mate.online/readiness/
curl -fsS -o /dev/null -w "%{http_code}\n" https://staging.chess-mate.online/static/js/main.*.js
```

EB logs: same paths as prod — see [DEPLOY_EB_ECR.md](./DEPLOY_EB_ECR.md#logs-no-ssh-required).

After deploy, **eb-engine.log** should show:

```text
Starting Celery worker (queues: default, analysis, batch_analysis; ...)
Celery worker is running.
```

## Smoke checklist

Run [STAGING_SMOKE.md](./STAGING_SMOKE.md) on staging before promoting to production.

## Cost notes

Staging is roughly one extra EB environment + small RDS instance. Use a smaller instance type and single-instance config to keep cost low; tear down RDS/EB when not actively testing.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| CD skips deploy | Check GitHub `staging` environment has AWS secrets |
| Health check fails | Set `HEALTHCHECK_URL` in GitHub `staging` environment variables |
| `ImproperlyConfigured` SECRET_KEY | Set strong `SECRET_KEY` on EB |
| Google OAuth redirect mismatch | Add exact staging callback URL in Google Console |
| Batch stuck `0/5` | Confirm `ENABLE_CELERY=true`, `REDIS_URL` set, Celery lines in eb-engine.log |
| SQLite errors | Set `ENVIRONMENT=staging` (not `development`) on EB |
