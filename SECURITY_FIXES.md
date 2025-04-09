# ChessMate Security Improvements

This document summarizes the security improvements made to the ChessMate application.

## Authentication Improvements

### JWT Authentication Configuration

Added proper authentication classes to the Django REST Framework configuration to ensure JWT tokens are validated correctly. The configuration is now applied in a way that avoids circular import issues during Django startup:

1. Initial REST_FRAMEWORK configuration in settings.py without authentication classes:
```python
# Initial minimal configuration without causing import issues
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ) if not DEBUG else (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'core.error_handling.exception_handler',
}
```

2. Updated CoreConfig in core/apps.py to add authentication classes after Django initialization:
```python
class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "ChessMate Core"

    def ready(self):
        """Initialize app-specific components."""
        # Configure REST Framework authentication after apps are loaded
        self._configure_rest_framework()
        
        # Other initialization code...

    def _configure_rest_framework(self):
        """Configure REST Framework settings after app initialization."""
        from django.conf import settings
        
        settings.REST_FRAMEWORK.update({
            'DEFAULT_AUTHENTICATION_CLASSES': (
                'rest_framework_simplejwt.authentication.JWTAuthentication',
                'rest_framework.authentication.SessionAuthentication',
            ),
            'DEFAULT_PERMISSION_CLASSES': (
                'rest_framework.permissions.IsAuthenticated',
            ),
        })
```

3. Updated INSTALLED_APPS to use our custom AppConfig:
```python
INSTALLED_APPS = [
    # Other apps...
    "core.apps.CoreConfig",  # Use our custom AppConfig instead of just "core"
    # Other apps...
]
```

This approach ensures that authentication classes are loaded after Django's app registry is fully initialized, avoiding circular import issues.

### Token Security

- Reduced JWT token lifetime from 24 hours to 30 minutes for access tokens
- Implemented token refresh mechanism with proper validation
- Added token blacklisting after logout to prevent token reuse

## API Security Enhancements

### Rate Limiting

- Implemented rate limiting for API endpoints to prevent brute force attacks
- Added different rate limits for authentication endpoints (more restrictive) vs. general endpoints
- Rate limit headers show remaining requests and reset time
- Redis backend for production rate limiting with fallback to in-memory for development

### Redis Optional Configuration

- Made Redis optional for development environments
- Added `REDIS_DISABLED` flag to skip Redis-dependent features when Redis is not available
- Implemented a `DummyRedis` class that logs operations instead of performing them when Redis is unavailable

### Input Validation

- Added schema-based request validation for all API endpoints
- Type checking for all input fields
- Value validation for critical fields
- Custom validators for email, password, etc.

## Improved Error Handling

- Standardized API error responses
- Added detailed error information for debugging
- Implemented proper HTTP status codes for different error types
- Added API error handler decorator to consistently handle exceptions

## Logging Improvements

- Improved logging configuration for better debugging
- Added log rotation to prevent log files from growing too large
- Different log levels for development and production
- Separated error logs from general logs

## Request Tracing

- Added request ID generation to track requests through the system
- Request ID added to response headers
- Request ID included in all log messages
- Thread-local storage to ensure request ID is available throughout request processing

## Security Headers

- Added Content Security Policy headers
- X-Content-Type-Options: nosniff
- Referrer-Policy: same-origin
- X-Frame-Options: DENY
- Permissions-Policy to restrict access to sensitive features

## Email Verification Security

- Secure token generation for email verification
- Token expiration after a configurable period
- Token blacklisting after use
- Proper validation of verification tokens

## Testing Tools

- Created comprehensive API security testing script
- Added token validation functionality
- Implemented endpoint availability checking
- Detailed documentation for testing procedures

## Future Improvements

1. Implement IP-based rate limiting in addition to token-based rate limiting
2. Add two-factor authentication for sensitive operations
3. Implement API key management for third-party integrations
4. Regular security audit process and penetration testing
5. Add automated security scanning in CI/CD pipeline

## References

- OWASP API Security Top 10: https://owasp.org/www-project-api-security/
- Django Security Best Practices: https://docs.djangoproject.com/en/stable/topics/security/
- JWT Security Best Practices: https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/
- Redis Security: https://redis.io/topics/security

## 1. Email Verification Token Security

### What Was Fixed
- The `EmailVerificationToken.is_valid()` method previously always returned `True`, making token validation ineffective.
- Updated to implement proper validation including:
  - Token existence checks
  - Profile association validation
  - Expiration checks (tokens expire after 7 days)
  - Prevention of token reuse

### How to Test
1. Register a new user with a valid email
2. Check the logs to see the verification token
3. Try accessing the verification URL with an invalid token:
   ```
   http://localhost:8000/api/verify-email/<valid_uidb64>/invalid-token/
   ```
4. Observe that verification fails with a proper error message

## 2. JWT Token Security

### What Was Fixed
- Reduced access token lifetime from 24 hours to 30 minutes
- Reduced refresh token lifetime from 7 days to 1 day
- Enabled refresh token rotation and blacklisting after use
- Added proper token type claims and user tracking

### How to Test
1. Log in to the API to get an access token and refresh token
2. Decode the access token at https://jwt.io/ to verify the expiration time (30 minutes)
3. Use the access token to access a protected endpoint
4. Use the refresh endpoint to get a new access token
5. Try using the old refresh token again - it should be rejected

## 3. Security Headers and CORS

### What Was Fixed
- Ensured security headers are consistently applied
- Updated CORS configuration for better security
- Added proper documentation for frontend developers

### How to Test
1. Use a tool like Postman to make a request to any API endpoint
2. Examine the response headers for security-related headers

## 4. Rate Limiting

### What Was Fixed
- Confirmed rate limiting on authentication endpoints
- Verified correct configuration for different endpoint types

### How to Test
1. Make repeated requests to the login endpoint
2. Observe the `X-RateLimit-Remaining` header decreasing
3. After reaching the limit, observe a 429 Too Many Requests response

## 5. Documentation

### What Was Added
- Created a comprehensive security audit document (SECURITY_AUDIT.md)
- Added API security guidelines for frontend developers (API_SECURITY.md)
- Updated project status to reflect security improvements

## Additional Recommendations

These improvements are scheduled for future implementation:

1. **Account-specific rate limiting**:
   - Implementing IP + account combined rate limiting
   - Adding temporary account lockouts after repeated failed attempts

2. **Multi-factor authentication**:
   - Adding support for TOTP-based MFA
   - Implementing backup codes for recovery

3. **IP-based threat detection**:
   - Implementing suspicious login detection
   - Adding location-based alerts

## Testing in Postman

To test the API security improvements using Postman:

1. **Register a new user**:
   - POST to `/api/register/`
   - Body: `{"username": "test_user", "email": "test@example.com", "password": "SecurePass123!"}`

2. **Login**:
   - POST to `/api/login/`
   - Body: `{"email": "test@example.com", "password": "SecurePass123!"}`
   - Save the returned access and refresh tokens

3. **Access a protected endpoint**:
   - GET to `/api/profile/`
   - Header: `Authorization: Bearer <access_token>`

4. **Refresh the token**:
   - POST to `/api/token/refresh/`
   - Body: `{"refresh": "<refresh_token>"}`
   - Save the new access and refresh tokens

5. **Try the old refresh token**:
   - POST to `/api/token/refresh/`
   - Body: `{"refresh": "<old_refresh_token>"}`
   - Observe that it's rejected

---
*Last Updated: April 4, 2025* 