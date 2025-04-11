# ChessMate Documentation Structure

This document provides an overview of the ChessMate documentation organization to help you find the information you need quickly.

## Documentation Organization

### Root-level Documents

- [README.md](../README.md) - Project overview, features, and quick start
- [INSTALLATION.md](../INSTALLATION.md) - Comprehensive installation instructions for all platforms
- [SECURITY.md](../SECURITY.md) - Security features, configurations, and best practices
- [TESTING.md](../TESTING.md) - Testing framework, writing tests, and running tests
- [CHANGELOG.md](../CHANGELOG.md) - Version history and project status

### Detailed Documentation

- [api.md](api.md) - Complete API reference and endpoint documentation
- [MONITORING.md](MONITORING.md) - Monitoring, health checks, and alerting
- [CACHE_INVALIDATION.md](CACHE_INVALIDATION.md) - Cache system and invalidation strategies
- [REDIS_TYPE_FIXES.md](REDIS_TYPE_FIXES.md) - Redis integration details and type fixes
- [ci_cd.md](ci_cd.md) - Continuous Integration and Deployment setup
- [PRE_COMMIT.md](PRE_COMMIT.md) - Pre-commit hooks and development workflow

## Documentation Conventions

1. **Root-level Documents**: Contain essential information needed by most users
2. **docs/ Directory**: Contains specialized and detailed documentation
3. **Markdown Format**: All documentation is in Markdown for consistency
4. **Cross-linking**: Documents link to each other where relevant

## Deprecated Documents

The following documents have been consolidated into other files and should no longer be used:

- HOW_TO_RUN.md → INSTALLATION.md
- WINDOWS_SETUP.md → INSTALLATION.md
- SECURITY_AUDIT.md → SECURITY.md
- API_SECURITY.md → SECURITY.md
- PROJECT_STATUS.md → CHANGELOG.md

## Maintenance Guidelines

When updating documentation:

1. **Keep README.md Concise**: Only include essential information
2. **Follow Sections**: Add content to the appropriate file based on topic
3. **Cross-link Documents**: Add links between related documents
4. **Update This Guide**: When adding new documentation files

## Documentation Gaps

If you identify missing documentation, please create a new Markdown file in the appropriate location and update this guide. 