# ChessMate Security Documentation

This document provides an overview of the security measures implemented in the ChessMate application, as well as guidance for security-related processes and best practices.

## Security Features

### Authentication and Authorization

- **JWT Authentication**: ChessMate uses JSON Web Tokens (JWT) for secure authentication.
- **Role-Based Access Control**: Different permission levels based on user roles.
- **CSRF Protection**: All non-GET endpoints are protected against Cross-Site Request Forgery attacks.
- **Session Security**: HTTP-only, secure cookies with appropriate SameSite policy.

### Data Protection

- **Database Security**: All sensitive data is encrypted at rest.
- **Input Validation**: Comprehensive input validation on all API endpoints.
- **Output Encoding**: Proper HTML encoding to prevent XSS attacks.
- **Content Security Policy**: Strict CSP implemented to prevent various injection attacks.

### Network Security

- **HTTPS Enforcement**: All communications are encrypted using TLS.
- **Security Headers**: Comprehensive security headers to protect against common attacks:
  - Content-Security-Policy
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Referrer-Policy
  - Strict-Transport-Security

### Rate Limiting and DoS Protection

- **API Rate Limiting**: Prevents abuse through distributed Redis-backed rate limiting.
- **Account Lockout**: Temporary lockout after multiple failed login attempts.
- **Request Size Limiting**: Prevents overflow attacks by limiting request sizes.

### Monitoring and Logging

- **Security Event Logging**: All security-relevant events are logged.
- **Health Check System**: Comprehensive system for monitoring application health.
- **Alerting**: Automatic alerts for suspicious activities.

### Development Practices

- **Dependency Scanning**: Automated scanning for vulnerable dependencies via Dependabot.
- **Security Testing**: Regular security tests integrated into CI/CD pipeline.
- **Code Reviews**: All code changes undergo security review.
- **Pre-commit Hooks**: Enforce security checks before code commits.

## Reporting Security Issues

We take security issues seriously and appreciate your efforts to responsibly disclose your findings. To report a security issue, please email security@chessmate.example.com with a detailed description of the issue.

### When reporting issues, please include:

1. A clear description of the issue
2. Steps to reproduce the vulnerability
3. Potential impact of the vulnerability
4. Any potential mitigations you've identified

Our security team will acknowledge receipt of your report within 48 hours and will send a more detailed response within 72 hours indicating the next steps in handling your report.

## Security Configurations

### Security Headers Configuration

The application implements a comprehensive set of security headers:

```python
# Content Security Policy directives
CSP_DIRECTIVES = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
    'style-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", 'data:'],
    'font-src': ["'self'"],
    'connect-src': ["'self'", 'https://api.chessmate.example.com'],
    'frame-src': ["'none'"],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'frame-ancestors': ["'none'"],
    'upgrade-insecure-requests': []
}
```

### CSRF Protection

All non-GET endpoints are protected with CSRF tokens. The application uses the custom `auth_csrf_exempt` decorator for endpoints that need to bypass CSRF protection (like webhooks), but these require additional authentication.

```python
# CSRF Settings
CSRF_COOKIE_SECURE = True  # Only send over HTTPS
CSRF_COOKIE_HTTPONLY = True  # Not accessible via JavaScript
CSRF_COOKIE_SAMESITE = 'Lax'  # Restrict cross-site requests

# Trusted origins for CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://chessmate.example.com',
    'https://www.chessmate.example.com',
    'https://api.chessmate.example.com',
]
```

### Rate Limiting Configuration

Rate limiting is implemented using Redis-backed storage to track request counts:

```python
# Rate limiting settings
RATE_LIMIT_DEFAULT = '100/hour'
RATE_LIMIT_SENSITIVE = '20/minute'
RATE_LIMIT_LOGIN = '5/minute'
RATE_LIMIT_REGISTRATION = '3/hour'
```

## Security Checklist for Developers

When working on the ChessMate codebase, follow these security best practices:

1. **Input Validation**
   - Always validate and sanitize all user-provided data
   - Use the `validate_request` decorator for API endpoints

2. **Authentication & Authorization**
   - Always check user permissions before performing actions
   - Use `@permission_classes([IsAuthenticated])` for protected endpoints

3. **Secure Data Handling**
   - Never log sensitive data like passwords or tokens
   - Use environment variables for sensitive configuration

4. **Error Handling**
   - Use proper exception handling
   - Don't expose sensitive information in error messages

5. **Dependency Management**
   - Keep dependencies up to date
   - Review security advisories before updating packages

## Security Improvements History

### v1.0 (2023-06-15)
- Initial security implementation

### v1.1 (2023-09-20)
- Added Content Security Policy
- Improved CSRF protection
- Implemented rate limiting

### v1.2 (2024-01-10)
- Added security headers middleware
- Enhanced input validation
- Added Dependabot configuration

### v1.3 (2024-05-28)
- Implemented comprehensive health checks
- Enhanced cache security with tag-based invalidation
- Added advanced rate limiting
- Improved error handling and validation

## Compliance

ChessMate is designed to comply with industry standard security practices, including:

- OWASP Top 10 security risks
- GDPR requirements for user data protection
- NIST Cybersecurity Framework guidelines

## Contact

For security-related questions or concerns, contact our security team at security@chessmate.example.com
