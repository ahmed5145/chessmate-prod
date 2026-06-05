# Production operations (no direct RDS from your PC)

## AWS credentials file on Windows (not key.pem)

**`~/.aws/credentials`** on your PC is:

`C:\Users\PCAdmin\.aws\credentials`

That file stores **IAM access keys** for the AWS CLI/EB CLI. Example:

```ini
[chessmate-deploy]
aws_access_key_id = AKIA....................
aws_secret_access_key = ........................................
```

Create keys in IAM → **chessmate-deploy** → Security credentials → Create access key, then:

```bat
aws configure --profile chessmate-deploy
```

**`key.pem` / `cert.pem` in the repo** are old **SSH key** files (server login). They are **not** the same as the credentials file above. Instance Connect does not use your repo `key.pem`. You can leave them gitignored; they are unrelated to `aws sts get-caller-identity`.

Removing `[default]` is fine; always run:

```bat
set AWS_PROFILE=chessmate-deploy
```

---

## Do NOT run `eb ssh --setup` unless you accept downtime

`eb ssh Chessmate-env-2 --setup` **terminates all EC2 instances** and replaces them so EB can install an SSH keypair. The app will be **down during replacement**. Only use that if you explicitly accept that risk.

Prefer **Session Manager** (no port 22) or **temporary RDS access** (below) instead.

```bat
cd C:\Users\PCAdmin\Desktop\chessmate_prod\chess_mate
eb use Chessmate-env-2
```

---

## Run prod `manage.py` from your PC (when SSH fails)

Temporarily allow **your IP** to reach **RDS** (not the whole internet forever):

1. AWS → **RDS** → database **chessmate-db** → **VPC security groups** → click the RDS SG.
2. **Inbound** → **Add rule**: PostgreSQL **5432**, source **My IP** → Save.
3. EB → **Chessmate-env-2** → **Configuration** → **Software** → note `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` (or `RDS_*` names).
4. On your PC (CMD), from `chess_mate`:

**Critical:** `DB_NAME` must match Elastic Beanstalk exactly — usually **`chessmate`** or **`chessmate_prod`**, **not** `postgres`.  
Wrong `DB_NAME` = you change a different database than the live site.

```bat
set REDIS_DISABLED=true
set ENVIRONMENT=production
set DJANGO_SETTINGS_MODULE=chess_mate.settings
set DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
set DB_NAME=chessmate
set DB_USER=your_db_user
set DB_PASSWORD=from-eb-console-only
set DB_PORT=5432
cd C:\Users\PCAdmin\Desktop\chessmate_prod\chess_mate
python manage.py show_db
python manage.py list_users ahmed
python manage.py reset_user_password ahmed.ps5145@gmail.com "YourNewPass123!" --superuser
python manage.py grant_credits --user-id 43 1000
python manage.py showmigrations core | findstr /V "[X]"
python manage.py migrate --noinput
```

5. **Remove** the RDS inbound rule (My IP on 5432) when finished.

---

## Database migrations on production (Windows — recommended)

You **do not need SSH, sudo, or Docker** on Windows. Run Django against prod RDS from your PC (same pattern as `grant_credits` above).

Migrations **do not show up in EB HTTP logs**. Either they ran at deploy (`scripts/entrypoint.sh` → `migrate --noinput`) or you run them manually below.

### Step 1 — Allow your PC to reach RDS (temporary)

1. AWS Console → **RDS** → **chessmate-db** → VPC security group → **Inbound rules**.
2. Add **PostgreSQL 5432**, source **My IP** → Save.

### Step 2 — Copy DB settings from Elastic Beanstalk

1. AWS Console → **Elastic Beanstalk** → **Chessmate-env-2** → **Configuration** → **Software**.
2. Note: `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` (names may be `RDS_*`).

**Important:** `DB_NAME` is usually **`chessmate`** or **`chessmate_prod`**, not `postgres`.

### Step 3 — CMD commands (run from `chess_mate` folder)

```bat
cd C:\Users\PCAdmin\Desktop\chessmate_prod\chess_mate

set REDIS_DISABLED=true
set ENVIRONMENT=production
set DJANGO_SETTINGS_MODULE=chess_mate.settings
set DB_HOST=paste-from-eb-console
set DB_NAME=chessmate
set DB_USER=paste-from-eb-console
set DB_PASSWORD=paste-from-eb-console
set DB_PORT=5432

python manage.py showmigrations core
```

**Read the output:**

- `[X] 0023_batchanalysisreport_credits` → migration **already applied** on prod. Nothing else to do.
- `[ ] 0023_batchanalysisreport_credits` → run:

```bat
python manage.py migrate --noinput
python manage.py showmigrations core
```

### Step 4 — Remove RDS inbound rule

Delete the “My IP on 5432” rule when finished.

### What you already confirmed

Your local run showed all core migrations through **0023** with `[X]` — **prod DB is up to date** for credit-refund columns.

### Optional — EB instance (only if RDS from PC is blocked)

Use **AWS Console → EC2 → Instances → Connect** (Session Manager). Linux commands there use `sudo` — not on your Windows PC. Find container with `docker ps`, then `docker exec` — only if you cannot use Step 1–3.

This hits **production data** — double-check emails and amounts.

---

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
# Access Key + Secret for chessmate-deploy (NOT s3-cloudfront-dressera-user)
aws configure set region us-east-2 --profile chessmate-deploy

# Verify EB CLI will use the right user (must NOT show s3-cloudfront-dressera-user):
aws sts get-caller-identity --profile chessmate-deploy

$env:AWS_PROFILE = "chessmate-deploy"
cd C:\Users\PCAdmin\Desktop\chessmate_prod\chess_mate
eb list
eb ssh Chessmate-env-2
```

If `aws sts get-caller-identity` without `--profile` still shows `s3-cloudfront-dressera-user`, your **[default]** profile is wrong — always set `$env:AWS_PROFILE = "chessmate-deploy"` before `eb`, or rely on **EC2 Instance Connect** (no AWS CLI needed).

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

### EC2 Instance Connect (recommended — SSM offline is OK)

Session Manager **Offline** is common on older EB AMIs. Use **EC2 Instance Connect** instead:

1. AWS Console → **EC2** → **Instances** → select `i-0274eb8d94d0c01e0` (Chessmate-env-2)
2. **Connect** → tab **EC2 Instance Connect**
3. **Username:** `ec2-user` (Amazon Linux on EB — try this before `root`)
4. **Connect** → browser terminal opens on the instance
5. Run:

```bash
sudo docker ps
CONTAINER=$(sudo docker ps -q | head -1)
echo "Using container: $CONTAINER"
sudo docker exec -it "$CONTAINER" bash -c "cd /app/chess_mate && python manage.py list_users"
```

If `ec2-user` fails, retry with username `root`.

### "Failed to connect" / SSH error on Instance Connect

Port 22 may be open only to **another security group** (not the public internet). Check **both** SGs on the instance:

| SG | What to look for |
|----|------------------|
| `AWSEBSecurityGroup` | SSH source = **same SG** or **load balancer only** → Instance Connect from browser **will fail** |
| `chessmate-app-sg` | SSH **My IP** → should work if your IP is correct |

**Fix:** On **AWSEBSecurityGroup** (`sg-02136a5edd0baa663`), **Add** (do not only edit) a **new** inbound rule:

- SSH, port **22**, source **My IP** (must create a *new* rule if the existing SSH rule uses source `sg-...`)

Also try:

- Phone **hotspot** (some ISPs block outbound port 22).
- IAM user **chessmate-deploy** → add inline policy allowing `ec2-instance-connect:SendSSHPublicKey` and `ec2:DescribeInstances` on `*`.

If SSH still fails, use **temporary RDS access** (above) or enable **Session Manager** (below) — do not run `eb ssh --setup` unless you accept instance replacement.

**Alternative:** `eb ssh` (CMD):

```bat
set AWS_PROFILE=chessmate-deploy
cd C:\Users\PCAdmin\Desktop\chessmate_prod\chess_mate
eb ssh Chessmate-env-2
```

Then the same `sudo docker exec` commands below.

### Enable Session Manager later (optional)

SSM **Offline** = instance role missing **`AmazonSSMManagedInstanceCore`** or agent not running.

EB → **Configuration** → **Security** → EC2 instance profile → attach policy **AmazonSSMManagedInstanceCore** → **Restart app server(s)**. Then **Connect** → **Session Manager** works without opening port 22.

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

## Before your next deploy (commands not in the image yet)

If you have **not** pushed the new management commands, use **Django shell** on the same container:

```bash
CONTAINER=$(sudo docker ps -q | head -1)
sudo docker exec -it "$CONTAINER" bash -c "cd /app/chess_mate && python manage.py shell"
```

Then paste:

```python
from django.contrib.auth import get_user_model
from core.models import Profile, BatchAnalysisReport

User = get_user_model()
# List users
for u in User.objects.filter(email__icontains="ahmed"):
    print(u.id, u.username, u.email, getattr(u.profile, "credits", "?"))

# +1000 credits
u = User.objects.get(email__iexact="ahmedmohamed200354@gmail.com")
p, _ = Profile.objects.get_or_create(user=u)
p.credits += 1000
p.save()
print("credits now", p.credits)

# Cancel stuck batch 5
r = BatchAnalysisReport.objects.get(pk=5)
r.status = "failed"
r.save()
print("batch", r.pk, r.status)

# Reset admin password (pick your email)
u = User.objects.get(email__iexact="YOUR_EMAIL@example.com")
u.set_password("ChooseANewStrongPassword123!")
u.is_staff = u.is_superuser = u.is_active = True
u.save()
print("password reset for", u.username)
```

Exit shell with `exit()`.

---

## Password reset email (Gmail on EB)

Production uses **`DJANGO_SETTINGS_MODULE=chess_mate.settings`** (not `settings_prod`).  
SMTP must be set via **EB environment properties** (spelling exact):

| Variable | Notes |
|----------|--------|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | Gmail address |
| `EMAIL_HOST_PASSWORD` | **Google App Password** (16 chars) |
| `DEFAULT_FROM_EMAIL` | Same as `EMAIL_HOST_USER` — not `DEFAUL_FROM_EMAIL` |

Create an app password: Google Account → Security → 2-Step Verification → App passwords.

API response `reason` field (after fix deploy):

- `not_configured` — Django never saw `EMAIL_HOST_*` (wrong settings module or typo in env name)
- `send_failed` — creds present but Gmail SMTP rejected (check Full logs for `Failed to send password reset email`)

If SMTP fails, use `python manage.py reset_user_password` on the **`chessmate`** database instead.

## Batch analysis stuck at 1/5

- Celery runs games **one at a time** (`SEQUENTIAL_BATCH_ANALYSIS=true`).
- Each game can take **several minutes**; UI may sit at `1/5` while game 2 is analyzing.
- Default **`BATCH_ANALYSIS_DEPTH=14`** (set on EB to tune speed vs quality).
- In Full logs → stdouterr, search: `analyze_batch_task started`, `game=game_1 depth=`, `game=game_2`.
- Deploy during a batch **kills** the worker (exit 137); cancel the batch and start a new one after deploy.

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
