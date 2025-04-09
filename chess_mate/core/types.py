"""
Type definitions for the chess_mate models.

This module provides type hints and stub definitions to support static type checking
for the chess_mate application, especially for models. These are NOT actual Django models
but type stubs to assist with type checking.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from django.db.models import Manager, Model, QuerySet

# Type variables for models
T = TypeVar('T', bound=Model)

# Type annotations for Django model managers
class ProfileManager(Manager['ProfileType']):
    """Type stub for Profile manager."""
    def get(self, *args: Any, **kwargs: Any) -> 'ProfileType': ...
    def filter(self, *args: Any, **kwargs: Any) -> QuerySet['ProfileType']: ...
    def create(self, **kwargs: Any) -> 'ProfileType': ...
    def get_or_create(self, **kwargs: Any) -> tuple['ProfileType', bool]: ...
    def all(self) -> QuerySet['ProfileType']: ...

class GameManager(Manager['GameType']):
    """Type stub for Game manager."""
    def get(self, *args: Any, **kwargs: Any) -> 'GameType': ...
    def filter(self, *args: Any, **kwargs: Any) -> QuerySet['GameType']: ...
    def create(self, **kwargs: Any) -> 'GameType': ...
    def get_or_create(self, **kwargs: Any) -> tuple['GameType', bool]: ...
    def all(self) -> QuerySet['GameType']: ...

class UserManager(Manager['UserType']):
    """Type stub for User manager."""
    def get(self, *args: Any, **kwargs: Any) -> 'UserType': ...
    def filter(self, *args: Any, **kwargs: Any) -> QuerySet['UserType']: ...
    def create(self, **kwargs: Any) -> 'UserType': ...
    def get_or_create(self, **kwargs: Any) -> tuple['UserType', bool]: ...
    def all(self) -> QuerySet['UserType']: ...
    def create_user(self, username: str, email: str, password: str, **kwargs: Any) -> 'UserType': ...
    def create_superuser(self, username: str, email: str, password: str, **kwargs: Any) -> 'UserType': ...

# Model stubs - these are just TYPE HINTS, not actual models
class ProfileType(Model):
    """Type stub for Profile model."""
    objects: ProfileManager
    DoesNotExist: Type[Exception]
    user: 'UserType'
    credits: int
    bullet_rating: int
    blitz_rating: int
    rapid_rating: int
    classical_rating: int
    email_verified: bool
    email_verification_token: Optional[str]
    email_verification_sent_at: Optional[Any]  # DateTimeField
    email_verified_at: Optional[Any]  # DateTimeField
    preferences: Dict[str, Any]
    created_at: Any  # DateTimeField
    updated_at: Any  # DateTimeField
    chess_com_username: str
    lichess_username: str
    rating_history: Dict[str, Any]
    bio: str
    rating: int
    last_credit_purchase: Any  # DateTimeField

class UserType(Model):
    """Type stub for User model."""
    objects: UserManager
    DoesNotExist: Type[Exception]
    id: int
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    date_joined: Any  # DateTimeField
    last_login: Optional[Any]  # DateTimeField
    profile: ProfileType

class GameType(Model):
    """Type stub for Game model."""
    objects: GameManager
    DoesNotExist: Type[Exception]
    user: UserType
    platform: str
    game_id: str
    white: str
    black: str
    date_played: Any  # DateTimeField
    result: str
    white_elo: Optional[int]
    black_elo: Optional[int]
    time_control: str
    analysis_status: str
    pgn: str
    created_at: Any  # DateTimeField
    updated_at: Any  # DateTimeField

class GameAnalysisType(Model):
    """Type stub for GameAnalysis model."""
    objects: Manager['GameAnalysisType']
    DoesNotExist: Type[Exception]
    game: GameType
    depth: int
    result: Dict[str, Any]
    created_at: Any  # DateTimeField

class SubscriptionTierType(Model):
    """Type stub for SubscriptionTier model."""
    objects: Manager['SubscriptionTierType']
    DoesNotExist: Type[Exception]
    name: str
    description: str
    price: float
    credits_per_period: int
    period_length: int
    is_active: bool

class SubscriptionType(Model):
    """Type stub for Subscription model."""
    objects: Manager['SubscriptionType']
    DoesNotExist: Type[Exception]
    user: UserType
    tier: SubscriptionTierType
    stripe_subscription_id: str
    start_date: Any  # DateTimeField
    end_date: Any  # DateTimeField
    is_active: bool
    credits_per_period: int
    id: int 