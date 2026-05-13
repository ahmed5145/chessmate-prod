Production setup notes
======================

Steps to finalize production after deploy:

1. TLS / ALB
   - Ensure the Application Load Balancer (ALB) used by Elastic Beanstalk has an HTTPS listener on port 443 with a valid ACM certificate for your domain (e.g. chess-mate.online and chessmate-prod.us-east-2.elasticbeanstalk.com or your custom domain).
   - If you enable `SECURE_SSL_REDIRECT` (default in `settings_prod.py`), make sure the ALB terminates TLS and forwards `X-Forwarded-Proto: https` so Django can detect secure requests.

2. Redis
   - Provide a `REDIS_URL` environment variable in Elastic Beanstalk config (format: `redis://[:password@]host:port/db`).
   - Example: `redis://:p@ssw0rd@my-redis.example.com:6379/0` or use AWS ElastiCache endpoint.
   - Without `REDIS_URL`, the app falls back to in-memory storage for task queue/cache (not suitable for multi-instance or production workloads).

3. ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS
   - `ALLOWED_HOSTS` can be set in the environment as a comma-separated list (e.g. `chess-mate.online,chessmate-prod.us-east-2.elasticbeanstalk.com`).
   - `CSRF_TRUSTED_ORIGINS` can also be set via env (comma-separated), otherwise it is derived from `ALLOWED_HOSTS`.

4. Frontend
   - The Docker image now attempts to build `chess_mate/frontend` during `docker build` (Node 18). CI also builds frontend and packages `chess_mate/frontend/build/` into the deploy bundle.
   - If using local EB deploys, ensure `chess_mate/frontend/build` is present before creating the application version.

5. Environment variables to configure in Elastic Beanstalk (recommended):
   - `SECRET_KEY` (required)
   - `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`
   - `REDIS_URL`
   - `ALLOWED_HOSTS` (comma-separated)
   - `SECURE_SSL_REDIRECT` (True/False)

6. Post-deploy checks
   - Visit `https://<your-domain>/health/` to validate the ALB health check responds with 200.
   - Visit `/` to confirm the landing page renders.
