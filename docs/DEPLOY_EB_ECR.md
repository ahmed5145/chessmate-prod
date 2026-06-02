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

### 3. IAM for GitHub Actions user

The same IAM user as `AWS_ACCESS_KEY_ID` needs:

- Elastic Beanstalk deploy (existing)
- ECR: `GetAuthorizationToken`, `CreateRepository`, `BatchCheckLayerAvailability`, `PutImage`, `InitiateLayerUpload`, `UploadLayerPart`, `CompleteLayerUpload`

### 4. IAM for EB EC2 instance role (required for pull)

EB → **Chessmate-env-2** → **Configuration** → **Security** → **EC2 instance profile** → attached role must include:

**`AmazonEC2ContainerRegistryReadOnly`**

Without this, deploy pulls fail and health stays **Red**.

## After a failed deploy

1. EB → **Environment overview** → **Restart app server(s)**
2. Or redeploy last good **Application version** (e.g. `chessmate-172`)
3. Confirm: `curl http://chessmate-prod.us-east-2.elasticbeanstalk.com/health/`

## Logs (faster than “last 100 lines”)

EB → **Logs** → **Request environment logs** → **Last 24 hours** → download bundle, open `var/log/eb-docker/containers/eb-current-app/*/stdouterr.log`
