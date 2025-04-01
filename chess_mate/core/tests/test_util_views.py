"""
Tests for utility views.
"""

import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import psutil
import redis

from .. import util_views

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user():
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )
    return user

@pytest.fixture
def authenticated_client(api_client, test_user):
    url = reverse('login')
    data = {
        'email': 'test@example.com',
        'password': 'testpassword123'
    }
    response = api_client.post(url, data, format='json')
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api_client

@pytest.mark.django_db
class TestUtilViews:
    def test_health_check(self, api_client):
        # Mock psutil and redis functionality
        with patch.object(psutil, 'virtual_memory') as mock_memory:
            mock_memory.return_value = MagicMock(
                total=16000000000,  # 16GB
                available=8000000000  # 8GB
            )
            
            with patch.object(util_views, 'get_redis_connection') as mock_redis_connection:
                mock_redis = MagicMock()
                mock_redis.ping.return_value = True
                mock_redis_connection.return_value = mock_redis
                
                with patch.object(psutil, 'cpu_percent', return_value=25.0):
                    url = reverse('health_check')
                    response = api_client.get(url)
                    
                    assert response.status_code == status.HTTP_200_OK
                    
                    # Check database status
                    assert response.data['database']['status'] == 'ok'
                    
                    # Check redis status
                    assert response.data['redis']['status'] == 'ok'
                    
                    # Check system stats
                    assert response.data['system']['cpu_usage'] == 25.0
                    assert response.data['system']['memory']['total_gb'] == 16.0
                    assert response.data['system']['memory']['available_gb'] == 8.0
                    assert response.data['system']['memory']['usage_percent'] == 50.0
    
    def test_health_check_redis_error(self, api_client):
        # Mock psutil and redis functionality with redis failure
        with patch.object(psutil, 'virtual_memory') as mock_memory:
            mock_memory.return_value = MagicMock(
                total=16000000000,  # 16GB
                available=8000000000  # 8GB
            )
            
            with patch.object(util_views, 'get_redis_connection') as mock_redis_connection:
                mock_redis = MagicMock()
                mock_redis.ping.side_effect = redis.ConnectionError("Connection refused")
                mock_redis_connection.return_value = mock_redis
                
                with patch.object(psutil, 'cpu_percent', return_value=25.0):
                    url = reverse('health_check')
                    response = api_client.get(url)
                    
                    assert response.status_code == status.HTTP_200_OK
                    
                    # Check database status should still be ok
                    assert response.data['database']['status'] == 'ok'
                    
                    # Check redis status should be error
                    assert response.data['redis']['status'] == 'error'
                    assert 'Connection refused' in response.data['redis']['error']
    
    def test_health_check_database_error(self, api_client):
        # Mock database error by patching the database check function
        with patch.object(util_views, 'check_database_connection') as mock_db_check:
            mock_db_check.return_value = (False, "Connection failed")
            
            with patch.object(psutil, 'virtual_memory') as mock_memory:
                mock_memory.return_value = MagicMock(
                    total=16000000000,  # 16GB
                    available=8000000000  # 8GB
                )
                
                with patch.object(util_views, 'get_redis_connection') as mock_redis_connection:
                    mock_redis = MagicMock()
                    mock_redis.ping.return_value = True
                    mock_redis_connection.return_value = mock_redis
                    
                    with patch.object(psutil, 'cpu_percent', return_value=25.0):
                        url = reverse('health_check')
                        response = api_client.get(url)
                        
                        assert response.status_code == status.HTTP_200_OK
                        
                        # Check database status should be error
                        assert response.data['database']['status'] == 'error'
                        assert response.data['database']['error'] == "Connection failed"
                        
                        # Check redis status should still be ok
                        assert response.data['redis']['status'] == 'ok'
    
    def test_version_check(self, api_client):
        # Mock the version data
        with patch.object(util_views, 'VERSION_DATA', {
            'version': '1.2.3',
            'build_date': '2023-05-15T12:00:00Z',
            'git_commit': 'abc1234',
            'environment': 'test'
        }):
            url = reverse('version')
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data['version'] == '1.2.3'
            assert response.data['build_date'] == '2023-05-15T12:00:00Z'
            assert response.data['git_commit'] == 'abc1234'
            assert response.data['environment'] == 'test'
    
    def test_csrf_token(self, api_client):
        url = reverse('csrf')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'csrfToken' in response.data
        assert response.cookies.get('csrftoken') is not None
    
    def test_error_trigger_authorized(self, authenticated_client):
        url = reverse('trigger_error')
        response = authenticated_client.get(url)
        
        # This should raise a deliberate exception that gets caught by middleware
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'message' in response.data
        assert 'Deliberate error triggered' in response.data['message']
    
    def test_error_trigger_unauthorized(self, api_client):
        url = reverse('trigger_error')
        response = api_client.get(url)
        
        # Without authentication, this should be unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_rate_limiter_info(self, authenticated_client):
        # Mock the rate limiter info function
        mock_limiter_info = {
            'global': {
                'total_requests': 1000,
                'blocked_requests': 50
            },
            'endpoints': {
                'login': {
                    'limit': '5/minute',
                    'current_requests': 2
                },
                'register': {
                    'limit': '3/hour',
                    'current_requests': 0
                }
            },
            'ips': {
                '127.0.0.1': {
                    'total_requests': 500,
                    'blocked_requests': 10
                }
            }
        }
        
        with patch.object(util_views.rate_limiter, 'get_rate_limit_info', return_value=mock_limiter_info):
            url = reverse('rate_limiter_info')
            response = authenticated_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data == mock_limiter_info
    
    def test_rate_limiter_info_unauthorized(self, api_client):
        url = reverse('rate_limiter_info')
        response = api_client.get(url)
        
        # Without authentication, this should be unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED 