# Testing Unification Plan

## 1. Project Structure Changes

### 1.1 Consolidate Test Locations
- Move standalone tests (`test_utils_standalone.py`, `test_utils_parameterized.py`, `test_cache_mock.py`) to `chess_mate/core/tests/standalone/`
- Update imports and references in these files
- Remove duplicate test cases between standalone and Django tests

### 1.2 Configuration Simplification
- Unify pytest.ini files into a single file at the project root
- Clean up and simplify the root conftest.py
- Create a common fixtures module in `chess_mate/core/tests/fixtures.py`

### 1.3 Test Runner Unification
- Update `run_tests.py` to handle the new structure
- Make the shell scripts (`run_tests.bat`, `run_tests.sh`) simple wrappers

## 2. Test Quality Improvements

### 2.1 Standardize Test Style
- Convert all tests to use pytest style (with fixtures and assertions)
- Remove Django TestCase base class where not needed
- Standardize on pytest's parameterization for similar test cases

### 2.2 Implement Proper Mocking
- Replace custom Redis mock with fakeredis
- Create standardized mock fixtures for external services
- Use patch decorators consistently

### 2.3 Improve Test Isolation
- Ensure each test properly cleans up after itself
- Use pytest-django's transactional test features
- Avoid test interdependencies

## 3. CI/CD Pipeline Streamlining

### 3.1 Consolidate Workflows
- Create a single reusable workflow for testing
- Use matrix for testing with different Python versions
- Extract common setup steps to reusable components

### 3.2 Standardize Commands
- Use consistent commands across all CI workflows
- Ensure coverage is always reported
- Add threshold checking for test coverage

## 4. Coverage Improvements

### 4.1 Identify Coverage Gaps
- Run coverage report to identify low-coverage modules
- Prioritize critical components for testing
- Create tests for uncovered code paths

### 4.2 Create Missing Test Types
- Add integration tests for critical API flows
- Implement contract tests for external interfaces
- Add performance tests for critical paths

### 4.3 Frontend Testing
- Implement React component tests
- Add end-to-end tests for critical user flows

## 5. Documentation Updates

### 5.1 Testing Documentation
- Update TESTING.md with the new approach
- Document best practices for writing tests
- Create examples for different test types

### 5.2 Workflow Documentation
- Document how to run tests locally
- Explain CI/CD pipeline
- Add documentation for coverage reporting

## Implementation Order

1. **Phase 1: Configuration Cleanup**
   - Unify pytest.ini files
   - Clean up conftest.py
   - Update run_tests.py for new structure

2. **Phase 2: Test Structure Reorganization**
   - Move standalone tests to new location
   - Create common fixtures module
   - Update imports and references

3. **Phase 3: Test Style Standardization**
   - Convert to pytest style
   - Implement proper mocking
   - Ensure test isolation

4. **Phase 4: Coverage Improvements**
   - Create tests for low-coverage modules
   - Implement missing test types
   - Add frontend tests

5. **Phase 5: CI/CD Updates**
   - Consolidate workflows
   - Standardize commands
   - Add coverage thresholds

6. **Phase 6: Documentation**
   - Update testing documentation
   - Document workflows
   - Create examples
