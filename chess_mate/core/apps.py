"""
Application configuration for the core app.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    """Core app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    label = "core"
    verbose_name = "ChessMate Core"

    def ready(self):
        """
        Initialize app-specific components.
        This is called after Django's app registry is fully populated.
        """
        # Import and initialize custom components
        from .cache_middleware import setup_cache_invalidation
        setup_cache_invalidation()

        # Register signal handlers
        self._register_signals()
        
        # Configure REST Framework after Django has loaded all apps
        self._configure_rest_framework()

    def _register_signals(self):
        """Register signal handlers."""
        # Importing here to avoid circular imports
        from django.db.models.signals import post_save
        from django.contrib.auth.models import User
        from .models import Profile

        # Define the signal handler function
        def create_user_profile(sender, instance, created, **kwargs):
            """Create a profile when a new user is created."""
            if created:
                Profile.objects.get_or_create(user=instance)
        
        # Connect the signal handler properly - not using decorator syntax
        post_save.connect(create_user_profile, sender=User)
        
    def _configure_rest_framework(self):
        """
        Configure REST Framework settings after app initialization.
        This avoids the AppRegistryNotReady error during imports.
        """
        from django.conf import settings
        
        logger.info("Configuring REST Framework authentication classes")
        
        # Only update if REST_FRAMEWORK is defined
        if hasattr(settings, 'REST_FRAMEWORK'):
            try:
                # Add authentication classes
                settings.REST_FRAMEWORK.update({
                    'EXCEPTION_HANDLER': 'core.error_handling.exception_handler',
                    'DEFAULT_AUTHENTICATION_CLASSES': (
                        'rest_framework_simplejwt.authentication.JWTAuthentication',
                        'rest_framework.authentication.SessionAuthentication',
                    ),
                    'DEFAULT_PERMISSION_CLASSES': (
                        'rest_framework.permissions.IsAuthenticated',
                    ),
                })
                logger.info("REST Framework authentication classes configured successfully")
            except Exception as e:
                # Log the error but don't prevent app startup
                logger.error(f"Error configuring REST Framework: {e}")
        else:
            logger.warning("REST_FRAMEWORK setting not found. Authentication classes not configured.")
