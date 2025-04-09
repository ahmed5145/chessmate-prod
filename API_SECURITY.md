# API Security Guidelines

This document provides security guidelines for frontend developers working with the ChessMate API.

## Authentication

### Token Handling

ChessMate uses JWT (JSON Web Tokens) for authentication. Here are best practices for handling tokens:

1. **Token Storage**:
   - **DO NOT** store tokens in localStorage or sessionStorage, as they are vulnerable to XSS attacks
   - **DO** store tokens in HttpOnly cookies when possible
   - If cookies are not an option, store tokens in memory (JavaScript variables)

2. **Token Expiration**:
   - Access tokens expire after 30 minutes
   - Refresh tokens expire after 1 day
   - Your app should handle token expiration gracefully by using the refresh endpoint

3. **Refresh Flow**:
   - When an API call returns a 401 Unauthorized error, use the refresh token to get a new access token
   - If the refresh fails, redirect the user to the login page
   - The refresh endpoint automatically rotates refresh tokens, so always store the new refresh token

### CSRF Protection

For endpoints that accept cookies (when using HttpOnly cookies for tokens), ChessMate uses CSRF protection:

1. **Getting a CSRF Token**:
   ```javascript
   // Make a GET request to the CSRF endpoint
   const response = await fetch('/api/csrf/', {
     credentials: 'include'  // Important for cookies
   });
   const { csrfToken } = await response.json();
   ```

2. **Using the CSRF Token**:
   ```javascript
   // Include the token in your headers for POST/PUT/DELETE requests
   const response = await fetch('/api/endpoint/', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'X-CSRFToken': csrfToken
     },
     credentials: 'include',  // Important for cookies
     body: JSON.stringify(data)
   });
   ```

## Security Headers

ChessMate API returns several security headers that you should not override:

- **Content-Security-Policy**: Restricts the sources of content
- **X-Content-Type-Options**: Prevents MIME type sniffing
- **X-Frame-Options**: Prevents your site from being framed (clickjacking protection)
- **Referrer-Policy**: Controls how much referrer information is sent

## Rate Limiting

The API implements rate limiting to protect against abuse:

- Authentication endpoints: 5 requests per minute
- Analysis endpoints: 3 requests per minute
- Standard endpoints: 100 requests per minute

Rate limit headers are included in responses:
- `X-RateLimit-Remaining`: Number of requests remaining in the current window
- `X-RateLimit-Reset`: Seconds until the rate limit resets

## Best Practices

1. **Always validate input** before sending to the API
2. **Implement proper error handling** for all API calls
3. **Use HTTPS** for all communications
4. **Keep tokens secure** and refresh them properly
5. **Log out users** properly by:
   - Clearing tokens from storage
   - Calling the logout endpoint to blacklist the refresh token

## Example Authentication Flow

```javascript
// Login
async function login(email, password) {
  const response = await fetch('/api/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password })
  });
  
  if (response.ok) {
    const data = await response.json();
    // Store tokens securely (preferably in HttpOnly cookies)
    return data;
  } else {
    // Handle errors
    const error = await response.json();
    throw new Error(error.message);
  }
}

// Using a protected endpoint
async function fetchProtectedResource(accessToken) {
  const response = await fetch('/api/protected-resource/', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  if (response.status === 401) {
    // Token expired, try to refresh
    const newTokens = await refreshTokens(refreshToken);
    if (newTokens) {
      // Retry with new token
      return fetchProtectedResource(newTokens.access);
    } else {
      // Refresh failed, redirect to login
      window.location.href = '/login';
    }
  }
  
  return response.json();
}
```

## Security Contacts

If you discover a security vulnerability, please contact:
- Email: security@chessmate.com
- Do not disclose security vulnerabilities publicly

---

Last updated: April 2025
