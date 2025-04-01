import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from unittest.mock import patch, MagicMock
from core.rate_limiter import RateLimiter
from core.models import Profile
from django.core.cache import cache
from django.db import models
from typing import Type, cast
import redis
import time

UserModel = get_user_model()

TEST_SETTINGS = {
    'RATE_LIMIT': {
        'DEFAULT': {
            'MAX_REQUESTS': 100,
            'TIME_WINDOW': 60,
        },
        'AUTH': {
            'MAX_REQUESTS': 5,
            'TIME_WINDOW': 300,
        },
        'ANALYSIS': {
            'MAX_REQUESTS': 10,
            'TIME_WINDOW': 600,
        }
    },
    'REDIS_URL': None,  # Disable Redis for tests
    'USE_REDIS': False,
    'CACHES': {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    }
}

@override_settings(**TEST_SETTINGS)
class TestRateLimiter(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test user once for all tests
        cls.user = UserModel.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def setUp(self):
        self.client = Client()
        self.rate_limiter = RateLimiter()
        Profile.objects.filter(user=self.user).delete()
        self.profile = Profile.objects.create(user=self.user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_rate_limiter_initialization(self):
        """Test that rate limiter initializes correctly."""
        self.assertIsNotNone(self.rate_limiter.cache)
        self.assertEqual(self.rate_limiter.use_redis, False)

    def test_rate_limit_config(self):
        """Test that rate limit config is retrieved correctly."""
        auth_config = self.rate_limiter.get_rate_limit_config('AUTH')
        self.assertEqual(auth_config['MAX_REQUESTS'], settings.RATE_LIMIT['AUTH']['MAX_REQUESTS'])
        self.assertEqual(auth_config['TIME_WINDOW'], settings.RATE_LIMIT['AUTH']['TIME_WINDOW'])

    def test_rate_limit_exceeded(self):
        """Test that rate limiting works when limit is exceeded."""
        key = 'test:rate:limit'
        endpoint_type = 'AUTH'
        config = self.rate_limiter.get_rate_limit_config(endpoint_type)
        
        # Make requests up to the limit
        for _ in range(config['MAX_REQUESTS']):
            self.assertFalse(self.rate_limiter.is_rate_limited(key, endpoint_type))
        
        # Next request should be rate limited
        self.assertTrue(self.rate_limiter.is_rate_limited(key, endpoint_type))

    def test_remaining_requests(self):
        """Test that remaining requests are calculated correctly."""
        key = 'test:remaining:requests'
        endpoint_type = 'AUTH'
        config = self.rate_limiter.get_rate_limit_config(endpoint_type)
        
        # Initial remaining should be max requests
        self.assertEqual(
            self.rate_limiter.get_remaining_requests(key, endpoint_type),
            config['MAX_REQUESTS']
        )
        
        # Make some requests
        for i in range(3):
            self.rate_limiter.is_rate_limited(key, endpoint_type)
            self.assertEqual(
                self.rate_limiter.get_remaining_requests(key, endpoint_type),
                config['MAX_REQUESTS'] - (i + 1)
            )

    def test_reset_time(self):
        """Test that reset time is calculated correctly."""
        key = 'test:reset:time'
        endpoint_type = 'AUTH'
        window = settings.RATE_LIMIT[endpoint_type]['TIME_WINDOW']
        
        # Set initial window time to 30 seconds ago
        current_time = int(time.time())
        past_time = current_time - 30  # Set window start to 30 seconds ago
        
        # Set window start time in cache
        cache.set(f"{key}:window", str(past_time), window)
        cache.set(f"{key}:counter", "1", window)
        
        # Get reset time
        reset_time = self.rate_limiter.get_reset_time(key)
        
        # The reset time should be the remaining time in the window
        # which should be between window - 30 and window seconds
        self.assertGreater(reset_time, 0)
        self.assertLessEqual(reset_time, window)
        self.assertGreater(reset_time, window - 35)  # Allow 5 seconds tolerance

    def test_rate_limiter_cache_error(self):
        """Test that rate limiter handles cache errors gracefully."""
        with patch('django.core.cache.cache.get') as mock_get:
            mock_get.side_effect = Exception("Test error")
            
            # Rate limiter should fail open (allow requests) on cache errors
            self.assertFalse(
                self.rate_limiter.is_rate_limited('test:error', 'AUTH')
            )

@override_settings(**TEST_SETTINGS)
class TestRateLimitDecorator(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test user once for all tests
        cls.user = UserModel.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def setUp(self):
        self.client = Client()
        self.rate_limiter = RateLimiter()
        Profile.objects.filter(user=self.user).delete()
        self.profile = Profile.objects.create(user=self.user)
        # Login the user
        self.client.login(username='testuser', password='testpass123')
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_login_rate_limit(self):
        """Test rate limiting on login endpoint."""
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'wrongpass'
        }

        # Make requests up to the limit
        for _ in range(settings.RATE_LIMIT['AUTH']['MAX_REQUESTS']):
            response = self.client.post(url, data, content_type='application/json')
            self.assertNotEqual(response.status_code, 429)

        # Next request should be rate limited
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 429)
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertIn('reset_time', response_data)

    def test_rate_limit_headers(self):
        """Test that rate limit headers are included in responses."""
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, content_type='application/json')

        # Headers should be present regardless of authentication success
        self.assertIn('X-RateLimit-Limit', response.headers)
        self.assertIn('X-RateLimit-Remaining', response.headers)
        self.assertIn('X-RateLimit-Reset', response.headers)

        # Verify header values are correct
        config = settings.RATE_LIMIT['AUTH']
        self.assertEqual(response.headers['X-RateLimit-Limit'], str(config['MAX_REQUESTS']))
        remaining = int(response.headers['X-RateLimit-Remaining'])
        self.assertGreaterEqual(remaining, 0)
        self.assertLessEqual(remaining, config['MAX_REQUESTS'])

    def test_unauthenticated_requests_not_rate_limited(self):
        """Test that unauthenticated requests are not rate limited."""
        self.client.logout()
        url = reverse('register')
        
        # Make many requests
        for _ in range(settings.RATE_LIMIT['AUTH']['MAX_REQUESTS'] + 1):
            response = self.client.post(url, {
                'username': f'user{_}',
                'email': f'user{_}@example.com',
                'password': 'testpass123'
            })
            self.assertNotEqual(response.status_code, 429) 