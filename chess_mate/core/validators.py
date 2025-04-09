"""
Validation utility functions for the ChessMate application.
"""

import logging
import re
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def validate_password_complexity(password):
    """
    Validate that a password meets security requirements.
    
    Password requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character
    
    Args:
        password: The password to validate
        
    Raises:
        ValidationError: If password doesn't meet requirements
    """
    errors = []
    
    # Check length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for number
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number")
    
    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    # If there are errors, raise ValidationError
    if errors:
        logger.warning(f"Password validation failed: {', '.join(errors)}")
        raise ValidationError(errors)
    
    return True

def validate_username(username):
    """
    Validate that a username meets the requirements.
    
    Username requirements:
    - Between 3 and 30 characters long
    - Contains only alphanumeric characters, underscores, and hyphens
    - Does not start or end with underscore or hyphen
    - Does not contain consecutive underscores or hyphens
    
    Args:
        username: The username to validate
        
    Raises:
        ValidationError: If username doesn't meet requirements
    """
    errors = []
    
    # Check length
    if len(username) < 3:
        errors.append("Username must be at least 3 characters long")
    elif len(username) > 30:
        errors.append("Username cannot be longer than 30 characters")
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        errors.append("Username can only contain letters, numbers, underscores, and hyphens")
    
    # Check for valid start and end characters
    if username.startswith(('-', '_')):
        errors.append("Username cannot start with an underscore or hyphen")
    if username.endswith(('-', '_')):
        errors.append("Username cannot end with an underscore or hyphen")
    
    # Check for consecutive special characters
    if '--' in username or '__' in username:
        errors.append("Username cannot contain consecutive underscores or hyphens")
    
    # If there are errors, raise ValidationError
    if errors:
        logger.warning(f"Username validation failed for '{username}': {', '.join(errors)}")
        raise ValidationError(errors)
    
    return True

def validate_email_domain(email):
    """
    Validate that an email's domain is allowed.
    This can be used to block disposable email domains.
    
    Args:
        email: The email to validate
        
    Raises:
        ValidationError: If email domain is not allowed
    """
    # List of blocked domains (can be expanded)
    blocked_domains = [
        'tempmail.com', 'throwawaymail.com', 'mailinator.com',
        'guerrillamail.com', 'guerrillamail.net', 'sharklasers.com',
    ]
    
    # Check if domain is in blocked list
    domain = email.split('@')[-1].lower()
    if domain in blocked_domains:
        logger.warning(f"Email validation failed: domain '{domain}' is blocked")
        raise ValidationError(f"Email domain '{domain}' is not allowed")
    
    return True
