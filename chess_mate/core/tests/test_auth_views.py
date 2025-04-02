"""
Tests for authentication views.
"""

import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from ..models import Profile
from .. import auth_views

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
    Profile.objects.create(
        user=user,
        email_verified=True,
        credits=10
    )
    return user

@pytest.fixture
def unverified_user():
    user = User.objects.create_user(
        username='unverified',
        email='unverified@example.com',
        password='testpassword123'
    )
    Profile.objects.create(
        user=user,
        email_verified=False,
        email_verification_token='test-token-123',
        credits=10
    )
    return user

@pytest.mark.django_db
class TestAuthViews:
    def test_login_success(self, api_client, test_user):
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['email'] == test_user.email
        assert response.data['username'] == test_user.username
    
    def test_login_invalid_credentials(self, api_client):
        url = reverse('login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Invalid email or password' in response.data['error']
    
    def test_login_unverified_email(self, api_client, unverified_user):
        url = reverse('login')
        data = {
            'email': 'unverified@example.com',
            'password': 'testpassword123'
        }
        
        # Mock email sending
        with patch('django.core.mail.send_mail', return_value=1) as mock_send:
            response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Email not verified' in response.data['error']
        # Should have sent verification email
        assert mock_send.called
    
    def test_register_success(self, api_client):
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'Strong.Password.123',
        }
        
        # Mock email sending
        with patch('django.core.mail.send_mail', return_value=1):
            response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'user_id' in response.data
        assert response.data['email'] == data['email']
        
        # Verify user was created
        user = User.objects.get(email=data['email'])
        assert user.username == data['username']
        
        # Verify profile was created
        profile = Profile.objects.get(user=user)
        assert profile.email_verified is False
        assert profile.email_verification_token is not None
    
    def test_register_duplicate_email(self, api_client, test_user):
        url = reverse('register')
        data = {
            'username': 'anotheruser',
            'email': 'test@example.com',  # Same as test_user
            'password': 'Strong.Password.123',
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email already exists' in response.data['error'].lower()
    
    def test_register_weak_password(self, api_client):
        url = reverse('register')
        data = {
            'username': 'weakpwduser',
            'email': 'weak@example.com',
            'password': 'password',  # Too simple
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data['error'].lower()
    
    def test_logout(self, api_client, test_user):
        # First login to get token
        login_url = reverse('login')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        
        login_response = api_client.post(login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # Now logout
        logout_url = reverse('logout')
        logout_data = {
            'refresh': refresh_token
        }
        
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        response = api_client.post(logout_url, logout_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'success' in response.data['message'].lower()
    
    def test_token_refresh(self, api_client, test_user):
        # First login to get token
        login_url = reverse('login')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        
        login_response = api_client.post(login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # Now refresh token
        refresh_url = reverse('token_refresh')
        refresh_data = {
            'refresh': refresh_token
        }
        
        response = api_client.post(refresh_url, refresh_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert response.data['access'] != login_response.data['access']
    
    def test_request_password_reset(self, api_client, test_user):
        url = reverse('request_password_reset')
        data = {
            'email': 'test@example.com'
        }
        
        # Mock email sending
        with patch('django.core.mail.send_mail', return_value=1) as mock_send:
            response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        # Should have sent reset email
        assert mock_send.called
    
    def test_reset_password(self, api_client, test_user):
        # Mock token validation
        with patch('django.contrib.auth.tokens.default_token_generator.check_token', return_value=True):
            url = reverse('reset_password')
            data = {
                'token': 'valid-token',
                'user_id': str(test_user.id),
                'password': 'NewStrong.Password.123'
            }
            
            response = api_client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_200_OK
            assert 'success' in response.data['message'].lower()
            
            # Verify password was changed
            user = User.objects.get(id=test_user.id)
            assert user.check_password('NewStrong.Password.123')
    
    def test_verify_email(self, api_client, unverified_user):
        # Mock the verification function
        with patch.object(auth_views.EmailVerificationToken, 'is_valid', return_value=True):
            url = reverse('verify_email', kwargs={'token': 'test-token-123'})
            
            # Use Django test client for this one since it's a GET with redirect
            response = api_client.get(url)
            
            # Should redirect to login
            assert response.status_code == status.HTTP_302_FOUND
            
            # Verify user is now verified
            profile = Profile.objects.get(user=unverified_user)
            assert profile.email_verified is True
    
    def test_csrf_token(self, api_client):
        url = reverse('csrf')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'detail' in response.data
        # Check if CSRF cookie was set
        assert 'csrftoken' in response.cookies 

@pytest.mark.django_db
class TestErrorHandling:
    """Test the standardized error handling in auth views."""
    
    def test_validation_error_format(self, api_client):
        """Test that validation errors follow the standard format."""
        # Test with missing fields in registration
        url = reverse('register')
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        # Check error response structure
        assert data['status'] == 'error'
        assert 'code' in data
        assert 'message' in data
        assert 'details' in data
        assert 'request_id' in data
        
        # Check that specific validation errors are included
        errors = data['details']['errors']
        fields = [error['field'] for error in errors]
        assert 'username' in fields
        assert 'email' in fields
        assert 'password' in fields
    
    def test_auth_error_format(self, api_client):
        """Test that authentication errors follow the standard format."""
        # Try to login with invalid credentials
        url = reverse('login')
        response = api_client.post(url, {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        # Check error response structure
        assert data['status'] == 'error'
        assert 'code' in data
        assert 'message' in data
        assert 'invalid credentials' in data['message'].lower()
    
    def test_success_response_format(self, api_client):
        """Test that success responses follow the standard format."""
        # Register a new user
        url = reverse('register')
        response = api_client.post(url, {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePassword123!'
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Check success response structure
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'email' in data['data'] 
        assert data['data']['email'] == 'test@example.com' 