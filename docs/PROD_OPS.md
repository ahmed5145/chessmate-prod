# Production operations (no direct RDS from your PC)

## Why `psql` from your laptop times out

RDS is almost always in a **private VPC**. The security group allows port **5432 only from the Elastic Beanstalk EC2 instances**, not from the public internet. That is correct for security.

You **cannot** fix this with `sslmode=verify-full` alone. Use one of:

1. **Run Django management commands inside the EB Docker container** (recommended)
2. **AWS Console → EC2 → Connect** (Session Manager or EC2 Instance Connect)
3. **Temporary** “my IP” on the RDS security group (discouraged; remove after)

---

## AWS credentials for EB CLI

`eb init` failed because your shell used IAM user **`s3-cloudfront-dressera-user`**, which has no Elastic Beanstalk permissions.

Use the deploy user from your project docs (e.g. **`chessmate-deploy`**) with access keys that can use EB/ECR:

```powershell
aws configure --profile chessmate-deploy
# Enter Access Key ID, Secret, region us-east-2, output json

$env:AWS_PROFILE = "chessmate-deploy"
cd C:\Users\PCAdmin\Desktop\chessmate_prod\chess_mate
eb init
```

When prompted:

- **Region:** `14` or `us-east-2`
- **Application:** pick the **existing** application (do not create a new one if denied)
- **Environment:** `Chessmate-env-2` (production)

If `eb init` still cannot create an app, in the AWS Console note the exact **Application name** under Elastic Beanstalk and pass it:

```powershell
eb init <existing-application-name> -r us-east-2 --profile chessmate-deploy
eb list
eb ssh Chessmate-env-2
```

---

## Run commands on production (container)

After you reach the EB instance (`eb ssh` or EC2 Connect):

```bash
sudo docker ps
CONTAINER=$(sudo docker ps -q | head -1)
sudo docker exec -it "$CONTAINER" bash -c "cd /app/chess_mate && python manage.py list_users ahmed"
sudo docker exec -it "$CONTAINER" bash -c "cd /app/chess_mate && python manage.py grant_credits ahmedmohamed200354@gmail.com 1000"
sudo docker exec -it "$CONTAINER" bash -c "cd /app/chess_mate && python manage.py cancel_batch --id 5 --reason 'Stuck after deploy'"
sudo docker exec -it "$CONTAINER" bash -c "cd /app/chess_mate && python manage.py reset_user_password your@email.com 'NewSecurePass123!' --superuser"
```

Replace emails/passwords. **Production only** — local `manage.py` uses your local DB.

### EC2 Connect without EB CLI

1. AWS Console → **Elastic Beanstalk** → **Chessmate-env-2**
2. **Environment overview** → click the **EC2 instance id**
3. **Connect** → **EC2 Instance Connect** or **Session Manager** (if enabled)
4. Run the `sudo docker exec` commands above

---

## Django admin without remembering the old password

1. On the **production container**, run `reset_user_password` (above) for **your** email with `--superuser`.
2. Open `https://chessmate-prod.us-east-2.elasticbeanstalk.com/admin/` (or your custom domain).
3. Log in with that email and the new password.
4. **Users** / **Profiles** — edit credits; **Batch analysis reports** — fix stuck batches.

### Optional: new superuser via EB env vars (only if none exists)

Elastic Beanstalk → **Configuration** → **Software** → **Environment properties**:

| Name | Example |
|------|---------|
| `DJANGO_SUPERUSER_USERNAME` | `admin` |
| `DJANGO_SUPERUSER_EMAIL` | `you@example.com` |
| `DJANGO_SUPERUSER_PASSWORD` | (strong password) |

**Redeploy.** Entrypoint runs `createsuperuser --noinput` only when the user does **not** already exist. It does **not** reset an existing password.

---

## Management commands reference

| Command | Purpose |
|---------|---------|
| `python manage.py list_users [substring]` | Find user ids/emails/credits |
| `python manage.py grant_credits <email> <amount>` | Add credits |
| `python manage.py cancel_batch --id 5` | Mark stuck batch failed |
| `python manage.py cancel_batch --task-id <uuid>` | Same, by Celery task id |
| `python manage.py reset_user_password <email> '<pass>' --superuser` | Admin login recovery |

---

## Local superuser

```powershell
cd C:\Users\PCAdmin\Desktop\chessmate_prod\chess_mate
python manage.py reset_user_password your@local.test "LocalDev123!" --superuser
```

Or interactive:

```powershell
python manage.py createsuperuser
```

---

## isort / black paths (Windows)

Run from **`chess_mate`** (where `manage.py` lives), not `chess_mate/chess_mate/...`:

```powershell
cd C:\Users\PCAdmin\Desktop\chessmate_prod\chess_mate
py -3.10 -m pip install black isort
py -3.10 -m isort --profile black core/tasks.py core/management/commands/
py -3.10 -m black --line-length=120 core/tasks.py core/management/commands/
```

Use **Python 3.10** to match Docker/CI (3.12.5 can break Black).
