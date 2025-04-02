"""
Authentication-related views for the ChessMate application.
Including user registration, login, logout, password reset, and email verification.
"""

# Standard library imports
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Django imports
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.utils.html import strip_tags
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.db.utils import IntegrityError

# Third-party imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

# Local application imports
from .models import Profile
from .validators import validate_password_complexity
from .decorators import rate_limit
from .error_handling import (
    api_error_handler, create_success_response, create_error_response,
    ValidationError as APIValidationError, ResourceNotFoundError,
    InvalidOperationError, CreditLimitError
)

# Configure logging
logger = logging.getLogger(__name__)

class EmailVerificationToken:
    """Helper class for email verification token generation and validation."""
    @staticmethod
    def generate_token():
        return str(uuid.uuid4())

    @staticmethod
    def is_valid(token, max_age_days=7):
        try:
            # Add token validation logic here if needed
            return True
        except Exception:
            return False

@api_view(['GET'])
def csrf(request):
    """
    Endpoint to get a CSRF token for secure requests.
    """
    csrf_token = get_token(request)
    return Response({'csrfToken': csrf_token})

@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
@csrf_exempt  # Exempt registration from CSRF
@api_error_handler
def register_view(request):
    """Handle user registration with email verification."""
    response = Response()  # Create response object early to add CORS headers
    response["Access-Control-Allow-Origin"] = request.headers.get('origin', '*')
    response["Access-Control-Allow-Credentials"] = 'true'
    
    data = request.data
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # Validate required fields
    if not all([username, email, password]):
        errors = []
        if not username:
            errors.append({"field": "username", "message": "Username is required"})
        if not email:
            errors.append({"field": "email", "message": "Email is required"})
        if not password:
            errors.append({"field": "password", "message": "Password is required"})
        raise APIValidationError(errors)

    # Validate email format
    try:
        validate_email(email)
    except DjangoValidationError as e:
        raise APIValidationError([{"field": "email", "message": str(e)}])

    # Check if email already exists
    if User.objects.filter(email=email).exists():
        raise APIValidationError([{"field": "email", "message": "Email already registered"}])

    # Check if username already exists
    if User.objects.filter(username=username).exists():
        raise APIValidationError([{"field": "username", "message": "Username already taken"}])

    # Validate password complexity
    try:
        validate_password_complexity(password)
    except DjangoValidationError as e:
        raise APIValidationError([{"field": "password", "message": str(e)}])

    # Create user
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True  # User is active but email not verified
        )
        
        # Create profile
        profile = Profile.objects.create(
            user=user,
            email_verified=False,
            email_verification_token=EmailVerificationToken.generate_token(),
            email_verification_sent_at=timezone.now()
        )
        
        # Send verification email
        try:
            # Get domain from request
            current_site = get_current_site(request)
            domain = current_site.domain
            
            # Create verification URL
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = profile.email_verification_token
            verification_link = f"http://{domain}/api/verify-email/{uidb64}/{token}/"
            
            # Prepare email content
            mail_subject = 'Activate your ChessMate account'
            message = render_to_string('email/account_activation_email.html', {
                'user': user,
                'verification_link': verification_link,
            })
            
            # Send email
            send_mail(
                subject=mail_subject,
                message=strip_tags(message),
                from_email=None,  # Use DEFAULT_FROM_EMAIL from settings
                recipient_list=[email],
                html_message=message,
            )
            
            logger.info(f"Verification email sent to {email}")
        except Exception as email_error:
            logger.error(f"Error sending verification email: {str(email_error)}")
            # Registration is still successful even if email fails
        
        # Registration successful
        return create_success_response(
            {
                "message": "Registration successful! Please check your email to verify your account.",
                "email": email
            },
            status_code=status.HTTP_201_CREATED
        )
        
    except IntegrityError as e:
        logger.error(f"Error creating user: {str(e)}")
        raise InvalidOperationError("register user", "database integrity error")

@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
@api_error_handler
def login_view(request):
    """Handle user login and return JWT tokens."""
    data = request.data
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        errors = []
        if not email:
            errors.append({"field": "email", "message": "Email is required"})
        if not password:
            errors.append({"field": "password", "message": "Password is required"})
        raise APIValidationError(errors)
    
    # Get user by email
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # We use a generic message for security reasons
        raise InvalidOperationError("authenticate", "invalid credentials")
    
    # Authenticate user
    user = authenticate(username=user.username, password=password)
    if user is None:
        raise InvalidOperationError("authenticate", "invalid credentials")
    
    # Check if email is verified
    try:
        profile = Profile.objects.get(user=user)
        if not profile.email_verified:
            # Re-send verification email if needed
            if profile.email_verification_sent_at is None or \
               (timezone.now() - profile.email_verification_sent_at).days > 1:
                # Update token and sent timestamp
                profile.email_verification_token = EmailVerificationToken.generate_token()
                profile.email_verification_sent_at = timezone.now()
                profile.save()
                
                # Get domain from request
                current_site = get_current_site(request)
                domain = current_site.domain
                
                # Create verification URL
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = profile.email_verification_token
                verification_link = f"http://{domain}/api/verify-email/{uidb64}/{token}/"
                
                # Prepare email content
                mail_subject = 'Activate your ChessMate account'
                message = render_to_string('email/account_activation_email.html', {
                    'user': user,
                    'verification_link': verification_link,
                })
                
                # Send email
                send_mail(
                    subject=mail_subject,
                    message=strip_tags(message),
                    from_email=None,  # Use DEFAULT_FROM_EMAIL from settings
                    recipient_list=[user.email],
                    html_message=message,
                )
                
                logger.info(f"Verification email resent to {user.email}")
            
            # Return error response about unverified email
            return create_error_response(
                error_type="authentication_failed",
                message="Email not verified. Please check your inbox for the verification link.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                details={"email_verified": False, "email": user.email}
            )
    except Profile.DoesNotExist:
        raise ResourceNotFoundError("User profile")
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    # Record login time and save user
    user.last_login = timezone.now()
    user.save()
    
    # Return tokens
    return create_success_response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
    })

@api_view(['POST'])
@api_error_handler
def logout_view(request):
    """Handle user logout by blacklisting the refresh token."""
    data = request.data
    refresh_token = data.get('refresh')
    
    if not refresh_token:
        raise APIValidationError([{"field": "refresh", "message": "Refresh token is required"}])
    
    try:
        # Get token from request
        token = RefreshToken(refresh_token)
        
        # Add to blacklist
        token.blacklist()
        
        # Also handle session logout if relevant
        logout(request)
        
        return create_success_response(
            message="Logged out successfully"
        )
    except Exception as e:
        # Token might be invalid or already blacklisted
        logger.warning(f"Error blacklisting token: {str(e)}")
        raise InvalidOperationError("logout", "invalid or expired token")

@api_view(['POST'])
@api_error_handler
def token_refresh_view(request):
    """Refresh the JWT access token using the refresh token."""
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        raise APIValidationError([{"field": "refresh", "message": "Refresh token is required"}])
    
    try:
        # Validate and refresh token
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        return create_success_response({
            "access": access_token,
            "refresh": str(refresh)  # Optional: return a new refresh token too
        })
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise InvalidOperationError("refresh token", "invalid or expired token")

@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
@api_error_handler
def request_password_reset(request):
    """Send password reset email with token."""
    email = request.data.get('email')
    if not email:
        raise APIValidationError([{"field": "email", "message": "Email is required"}])
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # We still return success to prevent email enumeration
        # This is a security measure - don't let attackers know if an email exists
        return create_success_response({
            "message": "Password reset link has been sent to your email if an account exists."
        })
    
    # Generate password reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Create reset link
    current_site = get_current_site(request)
    domain = current_site.domain
    reset_link = f"http://{domain}/reset-password/{uid}/{token}/"
    
    # Prepare email content
    mail_subject = 'Reset your ChessMate password'
    message = render_to_string('email/password_reset_email.html', {
        'user': user,
        'reset_link': reset_link,
    })
    
    try:
        # Send email
        send_mail(
            subject=mail_subject,
            message=strip_tags(message),
            from_email=None,  # Use DEFAULT_FROM_EMAIL from settings
            recipient_list=[email],
            html_message=message,
        )
        
        logger.info(f"Password reset email sent to {email}")
        
        return create_success_response({
            "message": "Password reset link has been sent to your email."
        })
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        # We don't want to expose that the email exists, so return a success response
        return create_success_response({
            "message": "Password reset link has been sent to your email if an account exists."
        })

@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
@api_error_handler
def reset_password(request):
    """Reset password using the token from the email link."""
    uid = request.data.get('uid')
    token = request.data.get('token')
    new_password = request.data.get('new_password')
    
    # Validate required fields
    errors = []
    if not uid:
        errors.append({"field": "uid", "message": "User ID is required"})
    if not token:
        errors.append({"field": "token", "message": "Token is required"})
    if not new_password:
        errors.append({"field": "new_password", "message": "New password is required"})
    
    if errors:
        raise APIValidationError(errors)
    
    # Validate password complexity
    try:
        validate_password_complexity(new_password)
    except DjangoValidationError as e:
        raise APIValidationError([{"field": "new_password", "message": str(e)}])
    
    try:
        # Get user from uid
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
        
        # Verify token
        if not default_token_generator.check_token(user, token):
            raise InvalidOperationError("reset password", "invalid or expired reset link")
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        logger.info(f"Password reset successful for user {user.email}")
        
        return create_success_response({
            "message": "Password has been reset successfully."
        })
        
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        logger.error(f"Password reset error: {str(e)}")
        raise InvalidOperationError("reset password", "invalid or expired reset link")

@api_view(['GET'])
def verify_email(request, uidb64, token):
    """Verify user email using the token from the verification link."""
    try:
        # Get user from uid
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
        
        try:
            # Get profile and check token
            profile = Profile.objects.get(user=user)
            
            if profile.email_verified:
                # Already verified
                return redirect('/login?verified=already')
            
            if profile.email_verification_token != token:
                logger.warning(f"Invalid verification token for user {user.email}")
                return render(request, 'email/verification_failed.html', {
                    'message': 'Invalid verification link.'
                })
            
            # Mark email as verified
            profile.email_verified = True
            profile.email_verified_at = timezone.now()
            profile.save()
            
            logger.info(f"Email verification successful for user {user.email}")
            
            # Redirect to login page with success message
            return redirect('/login?verified=success')
            
        except Profile.DoesNotExist:
            # Create profile and mark as verified
            Profile.objects.create(
                user=user,
                email_verified=True,
                email_verified_at=timezone.now()
            )
            
            logger.info(f"Profile created and email verified for user {user.email}")
            
            # Redirect to login page with success message
            return redirect('/login?verified=success')
            
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        logger.error(f"Email verification error: {str(e)}")
        return render(request, 'email/verification_failed.html', {
            'message': 'Invalid verification link or user does not exist.'
        })
        
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        return render(request, 'email/verification_failed.html', {
            'message': 'An unexpected error occurred during verification.'
        }) 