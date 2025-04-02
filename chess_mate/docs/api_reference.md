# ChessMate API Reference

This document provides detailed specifications for the ChessMate API endpoints.

## Table of Contents

1. [Standard Response Format](#standard-response-format)
2. [Authentication API](#authentication-api)
3. [Game Management API](#game-management-api)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)

## Standard Response Format

### Success Response

All successful responses follow this format:

```json
{
  "status": "success",
  "data": {
    // Response data specific to the endpoint
  },
  "message": "Operation was successful", // Optional message
  "request_id": "unique-request-id" // Helpful for debugging
}
```

### Error Response

All error responses follow this format:

```json
{
  "status": "error",
  "code": "error_code",
  "message": "A human-readable error message",
  "details": {
    // Additional error details if available
  },
  "request_id": "unique-request-id"
}
```

## Authentication API

### CSRF Token

Retrieve a CSRF token for secure requests.

**URL**: `/api/csrf/`

**Method**: `GET`

**Authentication**: None

**Response Example**:

```json
{
  "status": "success",
  "data": {
    "csrfToken": "somecsrftoken"
  }
}
```

### Register

Register a new user with email verification.

**URL**: `/api/register/`

**Method**: `POST`

**Authentication**: None

**Request Body**:

| Field    | Type   | Required | Description                |
|----------|--------|----------|----------------------------|
| username | string | Yes      | User's chosen username     |
| email    | string | Yes      | User's email address       |
| password | string | Yes      | User's password (min 8 characters) |

**Success Response (201 Created)**:

```json
{
  "status": "success",
  "data": {
    "message": "Registration successful! Please check your email to verify your account.",
    "email": "user@example.com"
  }
}
```

**Error Response (400 Bad Request)**:

```json
{
  "status": "error",
  "code": "validation_error",
  "message": "Validation failed",
  "details": {
    "errors": [
      {
        "field": "email",
        "message": "Email already registered"
      }
    ]
  },
  "request_id": "req-1234567890"
}
```

### Login

Authenticate a user and obtain JWT tokens.

**URL**: `/api/login/`

**Method**: `POST`

**Authentication**: None

**Request Body**:

| Field    | Type   | Required | Description         |
|----------|--------|----------|---------------------|
| email    | string | Yes      | User's email address|
| password | string | Yes      | User's password     |

**Success Response (200 OK)**:

```json
{
  "status": "success",
  "data": {
    "refresh": "eyJ0eXAiOiJKV...", // Refresh token
    "access": "eyJ0eXAiOiJKV...",  // Access token
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe"
    }
  }
}
```

**Error Response (401 Unauthorized)**:

```json
{
  "status": "error",
  "code": "authentication_failed",
  "message": "Invalid credentials",
  "request_id": "req-1234567890"
}
```

### Logout

Invalidate a refresh token.

**URL**: `/api/logout/`

**Method**: `POST`

**Authentication**: Required

**Request Body**:

| Field   | Type   | Required | Description     |
|---------|--------|----------|-----------------|
| refresh | string | Yes      | Refresh token   |

**Success Response (200 OK)**:

```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

### Refresh Token

Get a new access token using a refresh token.

**URL**: `/api/token/refresh/`

**Method**: `POST`

**Authentication**: None

**Request Body**:

| Field   | Type   | Required | Description    |
|---------|--------|----------|----------------|
| refresh | string | Yes      | Refresh token  |

**Success Response (200 OK)**:

```json
{
  "status": "success",
  "data": {
    "access": "eyJ0eXAiOiJKV...",  // New access token
    "refresh": "eyJ0eXAiOiJKV..."  // New refresh token (optional)
  }
}
```

### Request Password Reset

Send a password reset email.

**URL**: `/api/password-reset/request/`

**Method**: `POST`

**Authentication**: None

**Request Body**:

| Field | Type   | Required | Description         |
|-------|--------|----------|---------------------|
| email | string | Yes      | User's email address|

**Success Response (200 OK)**:

```json
{
  "status": "success",
  "data": {
    "message": "Password reset link has been sent to your email if an account exists."
  }
}
```

### Reset Password

Reset a user's password using a token.

**URL**: `/api/password-reset/confirm/`

**Method**: `POST`

**Authentication**: None

**Request Body**:

| Field       | Type   | Required | Description          |
|-------------|--------|----------|----------------------|
| uid         | string | Yes      | User ID (encoded)    |
| token       | string | Yes      | Reset token          |
| new_password| string | Yes      | New password         |

**Success Response (200 OK)**:

```json
{
  "status": "success",
  "data": {
    "message": "Password has been reset successfully."
  }
}
```

### Verify Email

Verify a user's email address.

**URL**: `/api/verify-email/<uidb64>/<token>/`

**Method**: `GET`

**Authentication**: None

**Response**: Redirects to the login page with a success parameter.

## Game Management API

### Get User Games

Retrieve all games for the authenticated user.

**URL**: `/api/games/`

**Method**: `GET`

**Authentication**: Required

**Query Parameters**:

| Parameter | Type   | Required | Description                         |
|-----------|--------|----------|-------------------------------------|
| page      | number | No       | Page number for pagination (default: 1) |
| limit     | number | No       | Number of games per page (default: 20) |
| sort      | string | No       | Sort by: 'date', 'rating', 'result' (default: 'date') |
| order     | string | No       | Sort order: 'asc' or 'desc' (default: 'desc') |

**Success Response (200 OK)**:

```json
{
  "status": "success",
  "data": {
    "games": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 ...",
        "white_player": "johndoe",
        "black_player": "opponent",
        "result": "1-0",
        "date_played": "2025-03-15T14:30:00Z",
        "source": "lichess",
        "white_rating": 1850,
        "black_rating": 1820,
        "analyzed": true,
        "imported_at": "2025-03-16T10:15:00Z"
      },
      // more games...
    ],
    "pagination": {
      "total": 158,
      "pages": 8,
      "current_page": 1,
      "limit": 20
    }
  }
}
```

### Fetch Games from External Services

Import games from chess.com or lichess.org.

**URL**: `/api/games/fetch/`

**Method**: `POST`

**Authentication**: Required

**Request Body**:

| Field      | Type   | Required | Description                       |
|------------|--------|----------|-----------------------------------|
| username   | string | Yes      | Username on the external service  |
| source     | string | Yes      | Source: 'chess.com' or 'lichess'  |
| max_games  | number | No       | Maximum games to import (default: 20) |
| time_period| string | No       | 'last_week', 'last_month', 'last_year', 'all' (default: 'last_month') |

**Success Response (202 Accepted)**:

```json
{
  "status": "success",
  "data": {
    "message": "Game import started",
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "games_requested": 20,
    "estimated_completion_time": "30 seconds",
    "credits_used": 1
  }
}
```

### Analyze Game

Request analysis for a specific game.

**URL**: `/api/games/{game_id}/analyze/`

**Method**: `POST`

**Authentication**: Required

**Path Parameters**:

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| game_id   | string | Yes      | Game UUID   |

**Request Body**:

| Field             | Type    | Required | Description                        |
|-------------------|---------|----------|------------------------------------|
| depth             | number  | No       | Analysis depth (default: 20)       |
| include_variations| boolean | No       | Include move variations (default: true) |
| analyze_blunders  | boolean | No       | Focus on blunders (default: true)  |

**Success Response (202 Accepted)**:

```json
{
  "status": "success",
  "data": {
    "message": "Analysis started",
    "task_id": "123e4567-e89b-12d3-a456-426614174001",
    "game_id": "123e4567-e89b-12d3-a456-426614174000",
    "estimated_completion_time": "60 seconds",
    "credits_used": 2
  }
}
```

### Get Game Analysis

Retrieve analysis for a specific game.

**URL**: `/api/games/{game_id}/analysis/`

**Method**: `GET`

**Authentication**: Required

**Path Parameters**:

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| game_id   | string | Yes      | Game UUID   |

**Success Response (200 OK)**:

```json
{
  "status": "success",
  "data": {
    "game_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "completed",
    "completed_at": "2025-03-16T11:25:00Z",
    "analysis": {
      "evaluation": [
        {
          "ply": 1,
          "move": "e4",
          "score": 0.32,
          "best_move": "e4",
          "comment": "Good opening move"
        },
        // more move evaluations...
      ],
      "summary": {
        "white_accuracy": 92.5,
        "black_accuracy": 87.3,
        "critical_positions": [
          {
            "ply": 24,
            "move_played": "Qd7",
            "evaluation_before": 0.2,
            "evaluation_after": -1.5,
            "best_move": "Bd7",
            "classification": "mistake"
          }
          // more critical positions...
        ],
        "game_phases": {
          "opening": {
            "name": "Ruy Lopez, Berlin Defense",
            "accuracy": {
              "white": 95.2,
              "black": 94.1
            }
          },
          "middlegame": {
            "accuracy": {
              "white": 93.1,
              "black": 85.2
            }
          },
          "endgame": {
            "accuracy": {
              "white": 89.2,
              "black": 82.6
            }
          }
        }
      }
    }
  }
}
```

### Check Analysis Status

Check the status of an analysis task.

**URL**: `/api/tasks/{task_id}/status/`

**Method**: `GET`

**Authentication**: Required

**Path Parameters**:

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| task_id   | string | Yes      | Task UUID   |

**Success Response (200 OK)**:

```json
{
  "status": "success",
  "data": {
    "task_id": "123e4567-e89b-12d3-a456-426614174001",
    "task_type": "game_analysis",
    "status": "in_progress",
    "progress_percentage": 65,
    "estimated_completion_time": "25 seconds",
    "created_at": "2025-03-16T11:24:00Z"
  }
}
```

### Batch Analyze Games

Request analysis for multiple games.

**URL**: `/api/games/batch-analyze/`

**Method**: `POST`

**Authentication**: Required

**Request Body**:

| Field     | Type         | Required | Description                 |
|-----------|--------------|----------|-----------------------------|
| game_ids  | array[string]| Yes      | Array of game UUIDs         |
| depth     | number       | No       | Analysis depth (default: 18)|

**Success Response (202 Accepted)**:

```json
{
  "status": "success",
  "data": {
    "message": "Batch analysis started",
    "batch_task_id": "123e4567-e89b-12d3-a456-426614174002",
    "game_count": 5,
    "estimated_completion_time": "5 minutes",
    "credits_used": 10,
    "individual_tasks": [
      {
        "game_id": "123e4567-e89b-12d3-a456-426614174000",
        "task_id": "123e4567-e89b-12d3-a456-426614174003"
      },
      // more task entries...
    ]
  }
}
```

*Additional game management endpoints will be documented as they are implemented.*

## Error Handling

Please refer to the [Error Handling Documentation](error_handling.md) for detailed information about error codes, error response formats, and exception handling.

## Rate Limiting

The ChessMate API implements rate limiting to ensure fair usage and protect our infrastructure. Different types of endpoints have different rate limits.

### Rate Limit Headers

All API responses include the following headers:

| Header               | Description                                           |
|----------------------|-------------------------------------------------------|
| X-RateLimit-Limit    | Maximum number of requests allowed in the time window |
| X-RateLimit-Remaining| Number of requests remaining in the current window    |
| X-RateLimit-Reset    | Time in seconds until the rate limit resets           |

### Rate Limit Categories

| Category  | Limit                  | Description                                |
|-----------|------------------------|--------------------------------------------|
| DEFAULT   | 100 requests per hour  | Default limit for uncategorized endpoints  |
| AUTH      | 20 requests per hour   | Authentication-related endpoints           |
| GAME      | 50 requests per hour   | Game retrieval and management endpoints    |
| ANALYSIS  | 30 requests per hour   | Game analysis endpoints                    |
| FEEDBACK  | 20 requests per hour   | AI feedback endpoints                      |
| PROFILE   | 60 requests per hour   | User profile and subscription endpoints    |
| DASHBOARD | 60 requests per hour   | Dashboard and analytics endpoints          |

### Rate Limit Exceeded Response

When a rate limit is exceeded, the API returns a 429 Too Many Requests response:

```json
{
  "status": "error",
  "code": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please try again in 3600 seconds.",
  "details": {
    "reset_time": 3600,
    "endpoint_type": "AUTH"
  },
  "request_id": "unique-request-id"
}
```

### Best Practices

To avoid hitting rate limits:

1. Implement proper backoff and retry logic in your client
2. Cache API responses when appropriate
3. Use batch endpoints where available (e.g., `batch-analyze` instead of multiple `analyze` calls)
4. Monitor the rate limit headers to track your usage

For more detailed information, see the [Rate Limiting Documentation](rate_limiting.md).

---

*Last Updated: April 2, 2025*
