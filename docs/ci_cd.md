# CI/CD Pipeline Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline setup for the ChessMate project.

## Overview

ChessMate uses GitHub Actions for automated testing, building, and deployment. The CI/CD pipeline ensures that code changes are automatically tested, and when approved, deployed to the appropriate environments.

## CI/CD Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Developer  │────▶│  GitHub     │────▶│ Automated   │────▶│  Staging    │
│  Commit     │     │  Repository │     │ Testing     │     │  Environment│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
                                                           ┌─────────────┐
                                                           │  Production │
                                                           │  Environment│
                                                           └─────────────┘
```

## Workflow Files

The CI/CD pipeline is defined in the following workflow files:

1. `.github/workflows/ci.yml`: Continuous Integration
2. `.github/workflows/cd.yml`: Continuous Deployment
3. `.github/workflows/security-scan.yml`: Security Scanning

## Continuous Integration

The CI workflow (`ci.yml`) is triggered on:
- Push to `main` and `develop` branches
- Pull requests to `main` and `develop` branches

It consists of the following jobs:

### Backend Testing

- Sets up Python 3.10
- Installs project dependencies
- Installs Stockfish
- Runs pytest tests
- Performs linting with flake8

### Frontend Testing

- Sets up Node.js 18
- Installs npm dependencies
- Runs Jest tests
- Performs linting

### Build

- Builds the application
- Collects static files
- Uploads build artifacts

## Continuous Deployment

The CD workflow (`cd.yml`) is triggered on:
- Push to `main` and `staging` branches
- Manual workflow dispatch

It supports two environments:
- Staging
- Production

The workflow:
1. Builds the application
2. Collects static files
3. Runs database migrations
4. Packages the application
5. Deploys to the appropriate environment:
   - AWS Elastic Beanstalk for production
   - Custom server for staging
6. Performs post-deployment health checks

## Security Scanning

The security scanning workflow (`security-scan.yml`) runs:
- Weekly on Sunday at midnight
- On manual trigger

It performs:
- Python dependency security scanning with `safety`
- Python code security linting with `bandit`
- npm dependency auditing
- OWASP ZAP baseline scanning against the staging environment

## Docker Configuration

The project uses Docker for containerization:

- `Dockerfile`: Backend container configuration
- `frontend/Dockerfile`: Frontend container configuration
- `docker-compose.yml`: Local development environment setup
- `docker-entrypoint.sh`: Container startup script

## Local Development

For local development with Docker:

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Deployment Process

### Staging Deployment

1. Push to the `staging` branch or manually trigger deployment
2. GitHub Actions builds the application
3. The application is deployed to the staging server
4. Post-deployment health checks are performed

### Production Deployment

1. Push to the `main` branch or manually trigger deployment with `production` environment
2. GitHub Actions builds the application
3. The application is deployed to AWS Elastic Beanstalk
4. Post-deployment health checks are performed

## Environment Variables

The following environment variables need to be configured as GitHub repository secrets:

- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_REGION`: AWS region
- `STAGING_HOST`: Staging server hostname
- `STAGING_USERNAME`: Staging server username
- `STAGING_SSH_KEY`: SSH key for staging server
- `STAGING_PORT`: SSH port for staging server

## Troubleshooting

If a deployment fails:

1. Check the GitHub Actions logs
2. Verify that all required environment variables are set
3. Check the application logs on the deployment server
4. Verify that the application health checks are passing

For specific deployment issues:

- **Deployment to Elastic Beanstalk fails**: Check AWS credentials and permissions
- **Deployment to staging server fails**: Check SSH access and server credentials
- **Tests fail**: Address the failing tests before deploying
- **Security scan finds vulnerabilities**: Address security issues before deploying

---

*Last Updated: April 2, 2024* 