# ChessMate API Security Testing Guide

This guide provides instructions on how to test the security improvements made to the ChessMate API.

## Prerequisites

Before starting the tests, ensure you have:

1. Python 3.8 or higher installed
2. The `requests` library installed (`pip install requests`)
3. A running instance of the ChessMate backend server
4. Redis installed and running locally (or `REDIS_DISABLED=True` set in your environment)

## Setting up for Testing

1. Clone the repository if you haven't already
2. Install the required dependencies
3. Configure the development environment:
   - Set `DEBUG=True` in your environment
   - Set `ENVIRONMENT=development` in your environment
   - If Redis is not available, set `REDIS_DISABLED=True` to use local memory instead
4. Start the backend server using one of these methods:

   ```bash
   # Method 1: Using the run_development.bat script
   run_development.bat

   # Method 2: Starting Django directly with environment variables
   # For Windows CMD:
   set DEBUG=True
   set ENVIRONMENT=development
   set REDIS_DISABLED=True
   python manage.py runserver

   # For Windows PowerShell:
   $env:DEBUG="True"
   $env:ENVIRONMENT="development"
   $env:REDIS_DISABLED="True"
   python manage.py runserver
   
   # For Linux/Mac:
   DEBUG=True ENVIRONMENT=development REDIS_DISABLED=True python manage.py runserver
   ```

## Troubleshooting Server Startup Issues

If you encounter an `AppRegistryNotReady` error when starting the server:

1. Make sure you're using the latest version of the code with the fixed configuration
2. Verify that `core.apps.CoreConfig` is listed in `INSTALLED_APPS` instead of just `core`
3. Try restarting the server with the `REDIS_DISABLED=True` environment variable set
4. If the issue persists, clear any `.pyc` files: 
   ```
   find . -name "*.pyc" -delete  # Linux/Mac
   Get-ChildItem -Path . -Filter "*.pyc" -Recurse | Remove-Item  # PowerShell
   ```

## Authentication Configuration

REST Framework authentication is now configured in the `CoreConfig.ready()` method to avoid circular import issues. The configuration adds the following settings after Django's app initialization:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # Other settings...
}
```

## Using the Test Script

The `test_api.py` script is designed to test various security features of the API.

### Basic Commands

1. Check available endpoints:
   ```
   python test_api.py --check-endpoints
   ```

2. Run all basic tests:
   ```
   python test_api.py
   ```

3. Run with verbose output:
   ```
   python test_api.py --verbose
   ```

### Testing Specific Features

1. Test rate limiting:
   ```
   python test_api.py --rate-limit
   ```

2. Test email verification security:
   ```
   python test_api.py --email-verify
   ```

3. Enable CSRF protection testing:
   ```
   python test_api.py --csrf
   ```

## Verifying Security Improvements

The test script evaluates several key security features:

### 1. JWT Token Security

- Token-based authentication with short-lived access tokens
- Refresh token rotation for improved security
- Token blacklisting after logout

### 2. Email Verification Security

- Email verification process for new accounts
- Secure token validation with proper expiration
- Protection against invalid token attacks

### 3. Rate Limiting

- API rate limiting to prevent brute force attacks
- Different rate limits for authentication vs. other endpoints
- Clear headers showing rate limit information (X-RateLimit-Remaining, X-RateLimit-Reset)

## Troubleshooting

### Connection Refused Errors

If you get "Connection refused" errors, make sure:
- The Django server is running on the expected port (8000 by default)
- The URL configuration in `test_api.py` matches your server setup

### Redis Connection Errors

If Redis-related errors occur:
- Ensure Redis is running, or
- Set `REDIS_DISABLED=True` and restart the server to use memory caching instead

### 404 Not Found Errors

If endpoints return 404 errors:
- Verify the URL patterns in the application match those in the test script
- Check that API endpoints are properly registered in the urlpatterns

## Manual Testing with Postman

You can also test the API manually using Postman:

1. Import the `SECURITY_FIXES.md` file as a collection
2. Run the authentication flow to get valid tokens
3. Use the access token to authenticate protected endpoints
4. Test rate limiting by making multiple rapid requests
5. Verify email verification links work as expected

## References

For more information on the security standards implemented, see:
- OWASP API Security Top 10
- Django Security Best Practices
- JWT Token Security Guidelines

---
*Last Updated: April 4, 2025* 