"""
Tests for the rate limiting middleware.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse

from core.middleware import RateLimitMiddleware
from core.rate_limiter import RateLimiter

@pytest.fixture
def rate_limiter_mock():
    with patch('core.middleware.RateLimiter') as mock:
        limiter_instance = MagicMock()
        limiter_instance.get_rate_limit_config.return_value = {'MAX_REQUESTS': 100, 'TIME_WINDOW': 3600}
        limiter_instance.get_remaining_requests.return_value = 99
        limiter_instance.get_reset_time.return_value = 3600
        mock.return_value = limiter_instance
        yield limiter_instance

@pytest.fixture
def middleware(rate_limiter_mock):
    def get_response(request):
        return HttpResponse("Test response")
    
    return RateLimitMiddleware(get_response)

@pytest.fixture
def auth_request(db):
    factory = RequestFactory()
    user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
    request = factory.get('/api/games/')
    request.user = user
    return request

@pytest.fixture
def anon_request():
    factory = RequestFactory()
    request = factory.get('/api/games/')
    request.user = AnonymousUser()
    request.META['REMOTE_ADDR'] = '127.0.0.1'
    return request

class TestRateLimitMiddleware:
    
    def test_non_api_request_bypasses_rate_limiting(self, middleware, rate_limiter_mock):
        """Test that non-API requests bypass rate limiting."""
        factory = RequestFactory()
        request = factory.get('/non-api-path/')
        request.user = AnonymousUser()
        
        response = middleware(request)
        
        assert response.status_code == 200
        assert response.content.decode() == "Test response"
        rate_limiter_mock.is_rate_limited.assert_not_called()
    
    def test_excluded_path_bypasses_rate_limiting(self, middleware, rate_limiter_mock):
        """Test that excluded paths bypass rate limiting."""
        factory = RequestFactory()
        request = factory.get('/api/health/')
        request.user = AnonymousUser()
        
        with patch.object(middleware, 'endpoint_patterns', {'DEFAULT': [r'^/api/.*$']}):
            with patch.object(middleware, '_get_endpoint_type', return_value='DEFAULT'):
                response = middleware(request)
                
                assert response.status_code == 200
                assert response.content.decode() == "Test response"
                rate_limiter_mock.is_rate_limited.assert_not_called()
    
    def test_authenticated_user_rate_limiting(self, middleware, rate_limiter_mock, auth_request):
        """Test rate limiting for authenticated users."""
        rate_limiter_mock.is_rate_limited.return_value = False
        
        with patch.object(middleware, 'endpoint_patterns', {'GAME': [r'^/api/games/?$']}):
            response = middleware(auth_request)
            
            assert response.status_code == 200
            assert response.content.decode() == "Test response"
            
            # Check if rate limiting was applied with correct key
            rate_limiter_mock.is_rate_limited.assert_called_once()
            args, _ = rate_limiter_mock.is_rate_limited.call_args
            assert args[0].startswith(f"rate_limit:user:{auth_request.user.id}")
            assert args[1] == 'GAME'
            
            # Check headers
            assert response['X-RateLimit-Limit'] == '100'
            assert response['X-RateLimit-Remaining'] == '99'
            assert response['X-RateLimit-Reset'] == '3600'
    
    def test_anonymous_user_rate_limiting(self, middleware, rate_limiter_mock, anon_request):
        """Test rate limiting for anonymous users (IP-based)."""
        rate_limiter_mock.is_rate_limited.return_value = False
        
        with patch.object(middleware, 'endpoint_patterns', {'GAME': [r'^/api/games/?$']}):
            response = middleware(anon_request)
            
            assert response.status_code == 200
            assert response.content.decode() == "Test response"
            
            # Check if rate limiting was applied with correct key
            rate_limiter_mock.is_rate_limited.assert_called_once()
            args, _ = rate_limiter_mock.is_rate_limited.call_args
            assert args[0].startswith("rate_limit:ip:127.0.0.1")
            assert args[1] == 'GAME'
    
    def test_rate_limit_exceeded(self, middleware, rate_limiter_mock, auth_request):
        """Test when rate limit is exceeded."""
        rate_limiter_mock.is_rate_limited.return_value = True
        rate_limiter_mock.get_reset_time.return_value = 3600
        
        with patch.object(middleware, 'endpoint_patterns', {'GAME': [r'^/api/games/?$']}):
            with patch('core.middleware.create_error_response') as mock_error:
                mock_error.return_value = HttpResponse("Rate limit exceeded", status=429)
                response = middleware(auth_request)
                
                assert response.status_code == 429
                assert response.content.decode() == "Rate limit exceeded"
                
                mock_error.assert_called_once_with(
                    error_type="rate_limit_exceeded",
                    message="Rate limit exceeded. Please try again in 3600 seconds.",
                    status_code=429,
                    details={
                        "reset_time": 3600,
                        "endpoint_type": 'GAME'
                    }
                )
    
    def test_get_endpoint_type(self, middleware):
        """Test the _get_endpoint_type method."""
        # Setup patterns
        middleware.endpoint_patterns = {
            'AUTH': [r'^/api/login/?$', r'^/api/register/?$'],
            'GAME': [r'^/api/games/?$'],
            'ANALYSIS': [r'^/api/games/\d+/analyze/?$']
        }
        
        # Test matching
        assert middleware._get_endpoint_type('/api/login/') == 'AUTH'
        assert middleware._get_endpoint_type('/api/register/') == 'AUTH'
        assert middleware._get_endpoint_type('/api/games/') == 'GAME'
        assert middleware._get_endpoint_type('/api/games/123/analyze/') == 'ANALYSIS'
        
        # Test default
        assert middleware._get_endpoint_type('/api/unknown/') == 'DEFAULT'
