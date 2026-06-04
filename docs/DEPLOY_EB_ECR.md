# Elastic Beanstalk deploy (ECR)

Production deploys build the Docker image in **GitHub Actions**, push to **ECR**, and Elastic Beanstalk only **pulls** the image (fast). EB no longer runs `npm` / full `pip install` during deploy.

## One-time AWS setup

### 1. Region

Your environment is in **us-east-2**. Set GitHub secret **`AWS_REGION`** = `us-east-2` (if not already).

### 2. ECR repository

The CD workflow creates `chessmate` automatically on first run. Or create manually:

```bash
aws ecr create-repository --repository-name chessmate --region us-east-2
```

### 3. IAM for GitHub Actions user (`chessmate-deploy`)

This is **separate** from the EC2 instance role. GitHub uses access keys for user **`chessmate-deploy`**.

**Easiest (console):**

1. IAM → **Users** → **chessmate-deploy**
2. **Add permissions** → **Attach policies directly**
3. Search and attach: **`AmazonEC2ContainerRegistryPowerUser`**
4. Save

That allows `ecr:GetAuthorizationToken` (required on `*`) and push/pull to your private repos.

You already have Beanstalk deploy on this user; only ECR push was missing.

**Do not use** the public ECR repo (`public.ecr.aws/...`) for CD. Use only:

`381492194867.dkr.ecr.us-east-2.amazonaws.com/chessmate`

**Optional custom policy** (instead of PowerUser) — IAM → user → Add permissions → Create inline policy → JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EcrAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "EcrPushChessmate",
      "Effect": "Allow",
      "Action": [
        "ecr:DescribeRepositories",
        "ecr:CreateRepository",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:us-east-2:381492194867:repository/chessmate"
    }
  ]
}
```

### 4. IAM for EB EC2 instance role (required for pull)

EB → **Chessmate-env-2** → **Configuration** → **Security** → **EC2 instance profile** → attached role must include:

**`AmazonEC2ContainerRegistryReadOnly`**

Without this, deploy pulls fail and health stays **Red**.

## After a failed deploy

1. EB → **Environment overview** → **Restart app server(s)**
2. Or redeploy last good **Application version** (e.g. `chessmate-172`)
3. Confirm: `curl http://chessmate-prod.us-east-2.elasticbeanstalk.com/health/`

## Elastic Beanstalk environment variables

### Free tier (no ElastiCache) — bundled Redis in the Docker image

The image runs **redis-server on 127.0.0.1:6379** inside the same container. Set on EB (or rely on image defaults):

| Variable | Value |
|----------|--------|
| `USE_BUNDLED_REDIS` | `true` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` |
| `REDIS_HOST` | `127.0.0.1` |
| `REDIS_PORT` | `6379` |
| `ENABLE_CELERY` | `true` |
| `SECRET_KEY` | (strong random) |
| `DB_*` / RDS vars | Your Postgres |

Do **not** set `REDIS_DISABLED=true` on EB if you want Celery/batches.

Do **not** set `REACT_APP_API_URL` anywhere on EB or GitHub (CD builds with empty value → `/api/v1/...` only).

### Later: ElastiCache (paid)

Replace bundled Redis with:

| Variable | Value |
|----------|--------|
| `USE_BUNDLED_REDIS` | `false` |
| `REDIS_URL` | `redis://your-cluster.cache.amazonaws.com:6379/0` |
| `REDIS_HOST` | ElastiCache endpoint |

### Local development

Copy repo template: `cp .env.example .env` and `cp chess_mate/frontend/.env.example chess_mate/frontend/.env.local`.  
Run Redis via `docker compose up redis` or install Redis locally.

## Production admin / RDS / stuck batches

RDS is not reachable from your home PC (security group). Run `manage.py` **inside the EB container** — see **[PROD_OPS.md](./PROD_OPS.md)** (`list_users`, `grant_credits`, `cancel_batch`, `reset_user_password`).

## Logs (no SSH required)

You do **not** run `docker exec` on your PC. Logs live on the EB instance.

1. AWS Console → **Elastic Beanstalk** → environment **ChessMate-Production** (or your env name).
2. Left menu → **Logs** → **Request logs** → choose **Last 100 lines** (quick) or **Full logs** (zip, ~few minutes).
3. Open the downloaded bundle and read:
   - `var/log/eb-docker/containers/eb-current-app/*-stdouterr.log` — Django/Gunicorn (login, import, API errors)
   - `var/log/eb-engine.log` — deploy, migrations, **“Celery worker pid=…”** at startup
   - `var/log/nginx/access.log` — HTTP status codes

### What to search for after deploy

| Symptom | Search in stdouterr.log / eb-engine.log |
|---------|----------------------------------------|
| Batch stuck `0/5` | `Celery worker`, `batch=`, `analyze_single_game_subtask`, `Chord callback` |
| Import 0 games | `Import returned 0 games` |
| Celery dead | `ERROR: Celery worker exited immediately` |

After the Celery fix, **eb-engine.log** on deploy should include:

```text
Celery worker pid=123 (log: /app/chess_mate/logs/celery.log)
Celery worker is running.
```

If you use **eb cli** and SSH: `eb ssh` → `sudo docker ps` → `sudo docker exec -it <container_id> tail -f /app/chess_mate/logs/celery.log`

### Batch status `0/5` for hours

- Status only moves when **Celery workers** run the 5 analysis subtasks (Stockfish). The API sets `in_progress` immediately; `completed_games` increments as each game finishes.
- Batches **#1–#3** started before a healthy worker will not finish; start a **new** batch after redeploy.
- Confirm EB env var **`ENABLE_CELERY=true`**, then redeploy so the entrypoint starts the worker with queues `default,analysis,batch_analysis`.
