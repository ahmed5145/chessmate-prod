# Testing Unification Plan

## Current CI Gaps (2026-04-09)

The following issues were identified during the latest CI-like validation and are not fully fixed in this pass. They are now tracked here for focused follow-up work:

1. Backend full-suite contract drift outside the stabilized compatibility tests
- Missing legacy exports referenced by tests:
   - `core.cache_invalidation.invalidate_cache_on_delete`
   - `core.cache_invalidation.get_redis_connection`
   - `core.cache.cache_memoize`
- Health-check contract mismatches (status codes/payload shape/component naming) in `core.tests.health.*`.
- OpenAI feedback test expectations for `GameAnalyzer._generate_ai_feedback` in `core.tests.test_openai_feedback`.

2. Stockfish-dependent test instability
- Several failures in `core.tests.test_stockfish_analyzer` depend on engine availability/behavior and memory conditions.
- CI needs deterministic engine test mode (mocked engine or constrained deterministic fixture path).

3. Frontend test noise cleanup (non-blocking)
- React Router v7 future warning was addressed in targeted tests, but test logs still include intentional `console.error` and `console.log` calls from error-path assertions and component diagnostics.
- Follow-up should suppress expected console output in tests where it does not add signal.

4. Validation scope note
- Targeted backend suites remain green (`test_analysis_tasks`, `test_feedback_views`, `test_profile_views`).
- Remaining failures are in broader backend coverage paths and should be handled in a dedicated hardening pass.

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
