# ChessMate Testing Guide

This guide provides comprehensive information on testing the ChessMate application, including unit tests, integration tests, and end-to-end tests.

## Test Environments

ChessMate supports multiple test environments:

- **Development**: Default environment for local testing
- **CI**: Used in continuous integration pipeline
- **Staging**: For pre-production testing

## Running Tests

### Quick Start

To run all tests:

```bash
cd chess_mate
python manage.py test
```

### Running Specific Test Suites

```bash
# Run only unit tests
python manage.py test tests.unit

# Run only integration tests
python manage.py test tests.integration

# Run only API tests
python manage.py test tests.api

# Run only a specific test case
python manage.py test tests.unit.test_analysis.TestMoveQuality
```

### Test with Coverage

```bash
coverage run --source='.' manage.py test
coverage report
```

For HTML coverage report:

```bash
coverage html
# Then open htmlcov/index.html in your browser
```

## API Testing Tools

### Authentication Test Tool

The `check_authentication.py` script provides a comprehensive way to test API authentication:

```bash
python check_authentication.py
```

Options:
- `--base-url`: API base URL (default: http://localhost:8000)
- `--username`: Test username
- `--password`: Test password
- `--verbose`: Enable verbose output
- `--test`: Specific test to run (choices: all, register, login, basic, simple, profile, refresh)

### JWT Token Debugging

The `jwt_debug.py` tool helps debug JWT token issues:

```bash
python jwt_debug.py --token YOUR_JWT_TOKEN
```

Options:
- `--token`: JWT token to analyze
- `--auth-header`: Authorization header containing the token
- `--create-test`: Create a test token
- `--user-id`: User ID for test token
- `--username`: Username for test token
- `--expiry`: Expiry in days for test token

### API Test Suite

```bash
python test_api.py --use-basic-profile --verbose
```

## Frontend Testing

### Jest Tests

```bash
cd frontend
npm test
```

### Cypress E2E Tests

```bash
cd frontend
npm run cypress:open  # Interactive mode
npm run cypress:run   # Headless mode
```

## Writing Tests

### Backend Test Guidelines

1. **Test Structure**: Use Django's TestCase class or pytest fixtures
2. **Isolation**: Each test should be isolated and not depend on other tests
3. **Mocking**: Use mocks for external services (e.g., Stockfish, OpenAI)
4. **Database**: Use in-memory SQLite for test performance

Example test class:

```python
from django.test import TestCase
from chess_mate.core.analysis.metrics_calculator import MetricsCalculator

class TestMetricsCalculator(TestCase):
    def setUp(self):
        # Setup test data
        self.calculator = MetricsCalculator()
        
    def test_calculate_move_quality(self):
        # Test move quality calculation
        result = self.calculator.calculate_move_quality(...)
        self.assertEqual(result['accuracy'], 85)
```

### Frontend Test Guidelines

1. **Component Tests**: Test each React component in isolation
2. **Redux Tests**: Test reducers, actions, and selectors separately
3. **Integration Tests**: Test component interactions
4. **E2E Tests**: Use Cypress for critical user flows

Example Jest test:

```javascript
import React from 'react';
import { render, screen } from '@testing-library/react';
import GameAnalysis from '../components/GameAnalysis';

test('renders game analysis component', () => {
  render(<GameAnalysis gameId={123} />);
  const analysisElement = screen.getByTestId('game-analysis');
  expect(analysisElement).toBeInTheDocument();
});
```

## Performance Testing

The `load_test.py` script can be used to test API performance:

```bash
python load_test.py --endpoint /api/v1/games/ --method GET --users 50 --duration 60
```

## Integration with CI/CD

ChessMate uses GitHub Actions for CI/CD. The pipeline runs:
1. Unit tests
2. Integration tests
3. Linters
4. Security checks
5. Coverage reports

See `.github/workflows/ci.yml` for details.

## Test Data

### Fixture Data

Sample data for testing is available in `tests/fixtures/`:
- `games.json`: Sample chess games for testing
- `users.json`: Sample user accounts
- `analysis.json`: Sample analysis results

### Test Database

To use the test database:

```bash
python manage.py testserver tests/fixtures/games.json
```

## Troubleshooting Tests

### Common Issues

1. **Database Connection Issues**:
   - Ensure test database permissions are set correctly
   - Use in-memory SQLite for isolation

2. **Test Timeouts**:
   - Mock long-running operations like Stockfish analysis
   - Use the `@pytest.mark.slow` decorator for slow tests

3. **Inconsistent Results**:
   - Check for test interdependencies
   - Reset the test database between test classes
