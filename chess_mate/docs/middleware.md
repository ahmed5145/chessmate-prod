# Request Validation Middleware

## Overview

The Request Validation Middleware provides automatic validation for API requests in the ChessMate application. It ensures that incoming requests contain all required fields with the correct data types before they reach the view functions, helping to:

- Prevent invalid data from reaching the application logic
- Standardize error responses for validation failures
- Reduce code duplication in views by centralizing validation logic
- Improve security by rejecting malformed requests

## How It Works

The middleware intercepts all API requests (`/api/*`) and validates them against predefined schemas. 
The validation process includes:

1. **Path matching**: Determine if the request path matches any validation schema
2. **Method checking**: Check if there's a schema for the HTTP method (POST, PUT, etc.)
3. **Required field validation**: Ensure all required fields are present
4. **Type validation**: Verify field values match expected types
5. **Value validation**: Apply custom validation rules to field values
6. **Custom validation**: Run more complex validation functions

If validation fails, the middleware returns a standardized error response with details about which fields failed validation and why.

## Adding New Validation Schemas

To add validation for a new API endpoint, update the `VALIDATION_SCHEMAS` dictionary in `core/middleware.py`.

### Schema Structure

```python
r'^/api/your-endpoint/$': {
    'HTTP_METHOD': {
        'required': ['field1', 'field2'],  # Required fields
        'optional': ['field3', 'field4'],  # Optional fields (for documentation)
        'type_validation': {               # Type checks for fields
            'field1': str,
            'field2': int,
            'field3': bool,
            'field4': list
        },
        'value_validation': {              # Value range/format checks
            'field2': lambda x: 1 <= x <= 100,
            'field4': lambda x: len(x) <= 50
        },
        'custom_validators': {             # Custom validation functions
            'field1': lambda x: re.match(r'^[a-z]+$', x)
        }
    }
}
```

### Example Schema

```python
# Endpoint that analyzes a chess game
r'^/api/games/\d+/analyze/$': {
    'POST': {
        'optional': ['depth', 'lines'],
        'type_validation': {
            'depth': int,
            'lines': int
        },
        'value_validation': {
            'depth': lambda x: 1 <= x <= 30,
            'lines': lambda x: 1 <= x <= 5
        }
    }
}
```

## Testing

The validation middleware has a comprehensive test suite in `core/tests/test_middleware.py` that verifies:

- Valid requests pass validation
- Missing required fields are rejected
- Invalid data types are rejected
- Invalid data formats are rejected
- Value range validation works correctly
- Custom validators function properly
- GET requests and non-API endpoints bypass validation

## Error Responses

When validation fails, the middleware returns a JSON response with:

```json
{
    "status": "error",
    "message": "Invalid request data",
    "errors": [
        {
            "field": "depth",
            "message": "Field 'depth' must be an integer"
        },
        {
            "field": "lines",
            "message": "Field 'lines' has an invalid value"
        }
    ]
}
```

## Performance Considerations

The validation middleware is designed to be lightweight and efficient:

1. It only validates API requests (paths starting with `/api/`)
2. GET, HEAD, and OPTIONS requests are not validated
3. Validation only occurs when there's a matching schema
4. Early exit on the first validation failure for each check type

## Implementation Details

The middleware is registered in the Django settings:

```python
MIDDLEWARE = [
    # ... other middleware
    'core.middleware.RequestValidationMiddleware',
]
```

The middleware is active in both production and test environments, ensuring consistent behavior across all environments.