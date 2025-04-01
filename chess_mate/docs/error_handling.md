# Error Handling

This document describes the standardized error handling approach used in the ChessMate API.

## Error Response Format

All API errors follow a consistent format:

```json
{
  "status": "error",
  "code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": { /* Additional error details */ },
  "request_id": "unique-request-id"
}
```

- **status**: Always "error" for error responses
- **code**: A unique error code (e.g., "AUTH_001")
- **message**: A human-readable error message
- **details**: Additional error details (can be null)
- **request_id**: A unique ID for the request (for traceability)

## Error Codes

Error codes use the following format: `CATEGORY_NUMBER`, where:

- **CATEGORY**: Indicates the type of error (e.g., AUTH, VAL, RES)
- **NUMBER**: A unique number within the category (e.g., 001, 002)

### Categories

| Prefix | Description                      | Examples                        |
|--------|----------------------------------|--------------------------------|
| AUTH   | Authentication/Authorization     | Invalid token, missing token   |
| VAL    | Validation                       | Invalid field, missing field   |
| RES    | Resource                         | Not found, already exists      |
| EXT    | External service                 | API error, service unavailable |
| RATE   | Rate limiting                    | Too many requests, credit limit |
| SRV    | Server                           | Database error, cache error    |
| OP     | Operation                        | Method not allowed, unsupported |
| GEN    | Generic                          | Bad request, internal error    |

## Using Error Handling

### Decorator Usage

The simplest way to implement consistent error handling is to use the `api_error_handler` decorator:

```python
from core.error_handling import api_error_handler, create_success_response, ResourceNotFoundError

@api_error_handler
def get_game(request, game_id):
    game = Game.objects.filter(id=game_id).first()
    if not game:
        raise ResourceNotFoundError("Game", game_id)
    
    # Process the game...
    return create_success_response({
        "id": game.id,
        "title": game.title,
        # ... other game fields
    })
```

The decorator will:

1. Catch any exceptions raised in the view
2. Log the exception with traceback
3. Convert the exception to a standardized error response
4. Include the request ID for traceability

### Custom Exception Classes

Use custom exception classes to indicate specific error conditions:

```python
from core.error_handling import ResourceNotFoundError, InvalidOperationError, CreditLimitError

# When a resource is not found
raise ResourceNotFoundError("Game", game_id)

# When an operation is invalid
raise InvalidOperationError("analyze game", "game is already being analyzed")

# When a user doesn't have enough credits
raise CreditLimitError(required=10, available=5)

# For validation errors
errors = [
    {"field": "email", "message": "Invalid email format"},
    {"field": "password", "message": "Password too short"}
]
raise ValidationError(errors)

# For external service errors
raise ChessServiceError("Chess.com", "API timeout")
```

### Direct Usage

For more control, you can create error responses directly:

```python
from core.error_handling import create_error_response
from rest_framework import status

return create_error_response(
    error_type="resource_not_found",
    message="Game not found",
    status_code=status.HTTP_404_NOT_FOUND,
    details={"game_id": game_id},
    request_id=request.request_id
)
```

### Success Responses

For consistency, success responses follow a similar format:

```json
{
  "status": "success",
  "data": { /* Response data */ },
  "message": "Optional success message"
}
```

Create them using the `create_success_response` function:

```python
from core.error_handling import create_success_response
from rest_framework import status

return create_success_response(
    data={"game_id": game.id, "status": "complete"},
    message="Game analysis complete",
    status_code=status.HTTP_201_CREATED
)
```

## Request IDs

Every request is assigned a unique ID via the `RequestIDMiddleware`. The ID is:

1. Added to the request object as `request.request_id`
2. Included in error responses
3. Added to response headers as `X-Request-ID`
4. Included in log messages

This allows tracing a request through logs and response data for debugging.

## REST Framework Integration

The custom exception handler is registered in Django REST Framework's settings:

```python
REST_FRAMEWORK = {
    # ... other settings
    'EXCEPTION_HANDLER': 'core.error_handling.custom_exception_handler',
}
```

This ensures all DRF exceptions (like `ValidationError`, `AuthenticationFailed`, etc.) are also converted to the standardized format.

## Error Logging

All errors are logged with:

- Error message
- Request ID
- Full traceback (in development mode)
- Request details (if available)

The log level depends on the error type:

- HTTP 500 errors: ERROR level
- HTTP 400-499 errors: WARNING level
- Validation errors: INFO level 