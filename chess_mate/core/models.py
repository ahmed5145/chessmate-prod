"""
This module defines the database models for the ChessMate application.

Models:
- Player: Represents a player in the application.
- Profile: Represents a user profile with additional information.
- Game: Represents a chess game played by a user.
- GameAnalysis: Represents the analysis of a chess game, including move details and scores.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from typing import Any, List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

class Player(models.Model):
    """Model representing a player."""
    username = models.CharField(max_length=100, unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.username)

class Profile(models.Model):
    """User profile model."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credits = models.IntegerField(default=10)
    bullet_rating = models.IntegerField(default=1200)
    blitz_rating = models.IntegerField(default=1200)
    rapid_rating = models.IntegerField(default=1200)
    classical_rating = models.IntegerField(default=1200)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(null=True)
    email_verified_at = models.DateTimeField(null=True)
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Add chess platform usernames
    chesscom_username = models.CharField(max_length=100, blank=True, null=True)
    lichess_username = models.CharField(max_length=100, blank=True, null=True)
    rating_history = models.JSONField(default=dict, blank=True)  # Store rating history

    def total_games(self) -> int:
        """Return total number of games played."""
        return Game.objects.filter(user=self.user).count()

    def get_platform_username(self, platform: str) -> Optional[str]:
        """Get the user's username for a specific platform."""
        if platform == 'chess.com':
            return self.chesscom_username
        elif platform == 'lichess':
            return self.lichess_username
        return None

    def set_platform_username(self, platform: str, username: str) -> None:
        """Set the user's username for a specific platform."""
        if platform == 'chess.com':
            self.chesscom_username = username
        elif platform == 'lichess':
            self.lichess_username = username
        self.save()

    def is_platform_username(self, platform: str, username: str) -> bool:
        """Check if the given username matches the stored platform username."""
        platform_username = self.get_platform_username(platform)
        if not platform_username:
            return False
        return platform_username.lower() == username.lower()

    def win_rate(self) -> float:
        """Calculate and return win rate as a percentage."""
        total = self.total_games()
        if total == 0:
            return 0.0
        wins = Game.objects.filter(user=self.user, result='win').count()
        return round((wins / total) * 100, 2)

    def get_rating_history(self) -> Dict[str, Dict[str, int]]:
        """Get user's rating history from games and stored history."""
        try:
            if not self.rating_history:
                self.rating_history = {}
                
            # Get all games ordered by date
            games = Game.objects.filter(user=self.user).order_by('date_played')
            
            # Track ratings by date
            current_ratings = {
                'bullet': self.bullet_rating,
                'blitz': self.blitz_rating,
                'rapid': self.rapid_rating,
                'classical': self.classical_rating
            }
            
            for game in games:
                try:
                    date = game.date_played.date().isoformat()
                    time_category = game.get_time_control_category()
                    if not time_category:
                        continue
                    
                    # Get the player's rating from the game
                    is_white = False
                    try:
                        if (game.platform == 'chess.com' and self.chesscom_username and 
                            game.white and self.chesscom_username):
                            is_white = game.white.lower() == self.chesscom_username.lower()
                        elif (game.platform == 'lichess' and self.lichess_username and 
                              game.white and self.lichess_username):
                            is_white = game.white.lower() == self.lichess_username.lower()
                    except AttributeError as e:
                        logger.error(
                            f"Error comparing usernames in get_rating_history: game={game.id}, "
                            f"platform={game.platform}, white={game.white}, black={game.black}, "
                            f"chesscom_username={self.chesscom_username}, "
                            f"lichess_username={self.lichess_username}. Error: {str(e)}"
                        )
                        continue
                    
                    rating = game.white_elo if is_white else game.black_elo
                    
                    if rating is not None:
                        current_ratings[time_category] = rating
                        self.rating_history[date] = current_ratings.copy()
                except Exception as e:
                    logger.error(
                        f"Error processing game {game.id} in get_rating_history: {str(e)}", 
                        exc_info=True
                    )
                    continue
            
            # Sort history by date
            sorted_history = dict(sorted(self.rating_history.items()))
            self.rating_history = sorted_history
            self.save()
            
            return sorted_history
        except Exception as e:
            logger.error(
                f"Error getting rating history for user {self.user.username}: {str(e)}", 
                exc_info=True
            )
            return {}

    def get_current_rating(self, time_category: str) -> int:
        """Get current rating for a specific time control category."""
        if time_category == 'bullet':
            return self.bullet_rating
        elif time_category == 'blitz':
            return self.blitz_rating
        elif time_category == 'rapid':
            return self.rapid_rating
        elif time_category == 'classical':
            return self.classical_rating
        return 1200  # Default rating

    def update_rating(self, time_category: str, new_rating: int) -> int:
        """Update rating for a specific time control category and return the rating change."""
        old_rating = self.get_current_rating(time_category)
        rating_change = new_rating - old_rating
        
        # Update current rating
        if time_category == 'bullet':
            self.bullet_rating = new_rating
        elif time_category == 'blitz':
            self.blitz_rating = new_rating
        elif time_category == 'rapid':
            self.rapid_rating = new_rating
        elif time_category == 'classical':
            self.classical_rating = new_rating
            
        # Update rating history
        current_date = timezone.now().date().isoformat()
        if not self.rating_history:
            self.rating_history = {}
        
        # Get or create today's ratings
        if current_date not in self.rating_history:
            self.rating_history[current_date] = {
                'bullet': self.bullet_rating,
                'blitz': self.blitz_rating,
                'rapid': self.rapid_rating,
                'classical': self.classical_rating
            }
        
        # Update the specific time category
        self.rating_history[current_date][time_category] = new_rating
        
        # Store rating change in preferences
        if not self.preferences:
            self.preferences = {}
        self.preferences[f'last_rating_change_{time_category}'] = rating_change
        
        self.save()
        return rating_change

    def __str__(self):
        return f"{self.user.username}'s profile"

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]

    def verify_email(self):
        """Mark email as verified."""
        self.email_verified = True
        self.email_verified_at = timezone.now()
        self.email_verification_token = None
        self.save()

    def get_preference(self, key, default=None):
        """Get a specific preference value."""
        return self.preferences.get(key, default)

    def set_preference(self, key, value):
        """Set a specific preference value."""
        self.preferences[key] = value
        self.save()

    def update_ratings_for_existing_games(self):
        """Update ratings for all existing games after linking an account."""
        try:
            # Reset ratings to default
            self.bullet_rating = 1200
            self.blitz_rating = 1200
            self.rapid_rating = 1200
            self.classical_rating = 1200
            self.save()  # Save the reset ratings
            
            # Get all games for this user with ratings, ordered by date
            games = Game.objects.filter(
                user=self.user,
                date_played__isnull=False
            ).exclude(
                white_elo__isnull=True,
                black_elo__isnull=True
            ).order_by('date_played')
            
            # Filter games based on platform and username
            platform_games = []
            if self.chesscom_username:
                platform_games.extend(
                    games.filter(
                        platform='chess.com'
                    ).filter(
                        models.Q(white__iexact=self.chesscom_username) |
                        models.Q(black__iexact=self.chesscom_username)
                    )
                )
            
            if self.lichess_username:
                platform_games.extend(
                    games.filter(
                        platform='lichess'
                    ).filter(
                        models.Q(white__iexact=self.lichess_username) |
                        models.Q(black__iexact=self.lichess_username)
                    )
                )
            
            # Sort all games by date
            platform_games.sort(key=lambda x: x.date_played)
            
            # Process each game and update ratings
            for game in platform_games:
                try:
                    # Get time control category
                    time_category = game.get_time_control_category()
                    if not time_category:
                        continue
                    
                    # Determine if user was white or black
                    is_white = False
                    try:
                        if game.platform == 'chess.com' and self.chesscom_username and game.white:
                            is_white = game.white.lower() == self.chesscom_username.lower()
                        elif game.platform == 'lichess' and self.lichess_username and game.white:
                            is_white = game.white.lower() == self.lichess_username.lower()
                    except AttributeError as e:
                        logger.error(f"Error determining player color: {str(e)}")
                        continue
                    
                    # Get the rating from the game
                    rating = game.white_elo if is_white else game.black_elo
                    
                    if rating is not None:
                        # Update the rating for this time category
                        if time_category == 'bullet':
                            self.bullet_rating = rating
                        elif time_category == 'blitz':
                            self.blitz_rating = rating
                        elif time_category == 'rapid':
                            self.rapid_rating = rating
                        elif time_category == 'classical':
                            self.classical_rating = rating
                        
                        # Update rating history
                        date = game.date_played.date().isoformat()
                        if not self.rating_history:
                            self.rating_history = {}
                        
                        self.rating_history[date] = {
                            'bullet': self.bullet_rating,
                            'blitz': self.blitz_rating,
                            'rapid': self.rapid_rating,
                            'classical': self.classical_rating
                        }
                        
                        # Save after each game to ensure we don't lose progress
                        self.save()
                        
                        logger.info(
                            f"Updated {time_category} rating to {rating} for game on {date}"
                        )
                    
                except Exception as e:
                    logger.error(f"Error processing game {game.id}: {str(e)}")
                    continue
            
            # Final save to ensure all updates are persisted
            self.save()
            
            logger.info(
                f"Completed rating updates for user {self.user.username}. "
                f"Final ratings - Bullet: {self.bullet_rating}, Blitz: {self.blitz_rating}, "
                f"Rapid: {self.rapid_rating}, Classical: {self.classical_rating}"
            )
            
        except Exception as e:
            logger.error(f"Error updating ratings: {str(e)}")
            raise

    def get_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """Calculate performance statistics for each time control."""
        try:
            games = Game.objects.filter(user=self.user)
            stats = {}
            
            # Calculate total games for percentage calculation
            total_games = games.count()
            
            # Process each time control category
            for time_control in ['bullet', 'blitz', 'rapid', 'classical']:
                time_control_games = []
                peak_rating = getattr(self, f"{time_control}_rating", 1200)
                total_rating = 0
                
                for game in games:
                    category = game.get_time_control_category()
                    if category == time_control:
                        time_control_games.append(game)
                        
                        # Get player's rating from this game
                        try:
                            is_white = False
                            if game.platform == 'chess.com' and self.chesscom_username and game.white:
                                is_white = game.white.lower() == self.chesscom_username.lower()
                            elif game.platform == 'lichess' and self.lichess_username and game.white:
                                is_white = game.white.lower() == self.lichess_username.lower()
                            
                            rating = game.white_elo if is_white else game.black_elo
                            if rating is not None:
                                total_rating += rating
                                peak_rating = max(peak_rating, rating)
                        except Exception as e:
                            logger.error(f"Error getting rating from game {game.id}: {str(e)}")
                            continue
                
                if not time_control_games:
                    stats[time_control] = {
                        'games': 0,
                        'winRate': 0,
                        'drawRate': 0,
                        'lossRate': 0,
                        'avgRating': getattr(self, f"{time_control}_rating", 1200),
                        'peakRating': getattr(self, f"{time_control}_rating", 1200),
                        'wins': 0,
                        'losses': 0,
                        'draws': 0
                    }
                    continue
                    
                # Calculate wins, losses, draws
                wins = losses = draws = 0
                for game in time_control_games:
                    # Skip if no usernames are linked
                    if not self.chesscom_username and not self.lichess_username:
                        continue
                        
                    # Determine if user was white or black
                    is_white = False
                    try:
                        if game.platform == 'chess.com' and self.chesscom_username and game.white:
                            is_white = game.white.lower() == self.chesscom_username.lower()
                        elif game.platform == 'lichess' and self.lichess_username and game.white:
                            is_white = game.white.lower() == self.lichess_username.lower()
                    except AttributeError as e:
                        logger.error(
                            f"Error comparing usernames in get_performance_stats: game={game.id}, "
                            f"platform={game.platform}, white={game.white}, black={game.black}, "
                            f"chesscom_username={self.chesscom_username}, "
                            f"lichess_username={self.lichess_username}. Error: {str(e)}"
                        )
                        continue
                    
                    # Count result
                    if game.result == 'win':
                        wins += 1
                    elif game.result == 'loss':
                        losses += 1
                    else:
                        draws += 1
                
                # Calculate percentages
                total = len(time_control_games)
                if total > 0:
                    win_rate = round((wins / total) * 100, 2)
                    draw_rate = round((draws / total) * 100, 2)
                    loss_rate = round((losses / total) * 100, 2)
                    avg_rating = round(total_rating / total) if total_rating > 0 else getattr(self, f"{time_control}_rating", 1200)
                    
                    stats[time_control] = {
                        'games': total,
                        'winRate': win_rate,
                        'drawRate': draw_rate,
                        'lossRate': loss_rate,
                        'avgRating': avg_rating,
                        'peakRating': peak_rating,
                        'wins': wins,
                        'losses': losses,
                        'draws': draws
                    }
            
            return stats
        except Exception as e:
            logger.error(
                f"Error calculating performance stats for user {self.user.username}: {str(e)}", 
                exc_info=True
            )
            return {}

@receiver(post_save, sender=User)
def create_or_save_user_profile(sender: Any, instance: User, created: bool, **kwargs: Any) -> None:
    """Create or save a Profile instance when a User is created or saved."""
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            Profile.objects.get_or_create(user=instance)

    # Remove the old signal handlers
    try:
        post_save.disconnect(create_user_profile, sender=User)
        post_save.disconnect(save_user_profile, sender=User)
    except Exception:
        pass

def get_default_user():
    """Get or create a default user for legacy data."""
    return User.objects.get_or_create(username='legacy_user')[0].id

class Game(models.Model):
    """Model representing a chess game."""
    TIME_CONTROL_CHOICES = [
        ('bullet', 'Bullet'),
        ('blitz', 'Blitz'),
        ('rapid', 'Rapid'),
        ('classical', 'Classical')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('analyzing', 'Analyzing'),
        ('analyzed', 'Analyzed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games', default=get_default_user)
    platform = models.CharField(max_length=20)  # 'chess.com' or 'lichess'
    game_id = models.CharField(max_length=100)
    pgn = models.TextField()
    result = models.CharField(max_length=10)  # win, loss, draw
    white = models.CharField(max_length=100)
    black = models.CharField(max_length=100)
    opponent = models.CharField(max_length=100, default="Unknown")
    opening_name = models.CharField(max_length=200, default="Unknown Opening")
    date_played = models.DateTimeField()
    
    # Enhanced fields
    time_control = models.CharField(max_length=50, default='blitz')
    time_control_type = models.CharField(max_length=20, choices=TIME_CONTROL_CHOICES, default='blitz')
    eco_code = models.CharField(max_length=3, null=True)  # ECO code for the opening
    opening_played = models.CharField(max_length=200, default="Unknown Opening")
    opening_variation = models.CharField(max_length=200, default="Unknown Variation")
    opponent_opening = models.CharField(max_length=200, default='Unknown Opponent Opening')
    analysis_version = models.IntegerField(default=1)
    last_analysis_date = models.DateTimeField(null=True)
    analysis_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    analysis_priority = models.IntegerField(default=0)  # For batch processing
    
    # Existing fields
    analysis = models.JSONField(null=True, blank=True)
    feedback = models.JSONField(null=True, blank=True)  # Store analysis feedback
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    white_elo = models.IntegerField(null=True, blank=True)
    black_elo = models.IntegerField(null=True, blank=True)
    
    player_color = models.CharField(max_length=5, choices=[('white', 'White'), ('black', 'Black')], default='white')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    analysis_completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'games'
        unique_together = ('user', 'platform', 'game_id')
        ordering = ['-date_played']
        indexes = [
            models.Index(fields=['user', 'platform']),
            models.Index(fields=['date_played']),
            models.Index(fields=['analysis_status']),
            models.Index(fields=['time_control_type']),
            models.Index(fields=['eco_code']),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} vs {self.opponent} ({self.result})"

    def save(self, *args, **kwargs):
        """Override save to handle rating updates."""
        try:
            # Get time control category before saving
            time_category = self.get_time_control_category()
            if time_category:
                self.time_control = time_category
                
            super().save(*args, **kwargs)
            
            # Rating update logic commented out for now
            # if not hasattr(self, 'user') or not self.user:
            #     logger.debug("Skipping rating update: no user associated with game")
            #     return
            
            # try:
            #     profile = self.user.profile
            #     if not profile:
            #         logger.debug("Skipping rating update: no profile found for user")
            #         return
                
            #     # Check if this game belongs to the user's linked account
            #     is_users_game = False
                
            #     # Handle chess.com games
            #     if self.platform == 'chess.com' and profile.chesscom_username:
            #         try:
            #             if self.white and self.black:  # Ensure usernames exist
            #                 white_lower = self.white.lower()
            #                 black_lower = self.black.lower()
            #                 username_lower = profile.chesscom_username.lower()
            #                 is_users_game = (white_lower == username_lower or 
            #                                black_lower == username_lower)
            #         except AttributeError as e:
            #             logger.error(
            #                 f"Error comparing chess.com usernames: white={self.white}, "
            #                 f"black={self.black}, username={profile.chesscom_username}. "
            #                 f"Error: {str(e)}"
            #             )
                
            #     # Handle lichess games
            #     elif self.platform == 'lichess' and profile.lichess_username:
            #         try:
            #             if self.white and self.black:  # Ensure usernames exist
            #                 white_lower = self.white.lower()
            #                 black_lower = self.black.lower()
            #                 username_lower = profile.lichess_username.lower()
            #                 is_users_game = (white_lower == username_lower or 
            #                                black_lower == username_lower)
            #         except AttributeError as e:
            #             logger.error(
            #                 f"Error comparing lichess usernames: white={self.white}, "
            #                 f"black={self.black}, username={profile.lichess_username}. "
            #                 f"Error: {str(e)}"
            #             )
                
            #     if is_users_game:
            #         # Determine if user was white or black
            #         is_white = False
            #         try:
            #             if self.platform == 'chess.com' and profile.chesscom_username and self.white:
            #                 is_white = self.white.lower() == profile.chesscom_username.lower()
            #             elif self.platform == 'lichess' and profile.lichess_username and self.white:
            #                 is_white = self.white.lower() == profile.lichess_username.lower()
            #         except AttributeError as e:
            #             logger.error(
            #                 f"Error determining player color: white={self.white}, "
            #                 f"platform={self.platform}, error={str(e)}"
            #             )
            #             return
                    
            #         # Get the user's rating from this game
            #         rating = self.white_elo if is_white else self.black_elo
                    
            #         if rating is not None:
            #             # Update the rating using the profile's update_rating method
            #             profile.update_rating(time_category, rating)
            #             logger.info(
            #                 f"Updated {time_category} rating for user {self.user.username} "
            #                 f"to {rating} (game {self.id})"
            #             )
            #         else:
            #             logger.debug(
            #                 f"Skipping rating update: no valid rating found for "
            #                 f"game {self.id} ({time_category})"
            #             )
            # except Exception as e:
            #     logger.error(
            #         f"Error updating rating for game {self.id}: {str(e)}", 
            #         exc_info=True
            #     )
        except Exception as e:
            logger.error(f"Error in Game.save(): {str(e)}", exc_info=True)
            raise

    def get_time_control_category(self) -> Optional[str]:
        """Determine the time control category of the game."""
        try:
            # First check if we already have a time_control field set
            if self.time_control and self.time_control in ['bullet', 'blitz', 'rapid', 'classical']:
                return self.time_control
                
            # Extract total time in minutes
            if self.platform == 'chess.com':
                # Try TimeControl tag first
                time_pattern = r'\[TimeControl "(\d+)(?:\+(\d+))?"'
                match = re.search(time_pattern, self.pgn)
                if match:
                    base_seconds = int(match.group(1))
                    increment = int(match.group(2)) if match.group(2) else 0
                    total_minutes = (base_seconds + (increment * 40)) / 60  # Assume 40 moves
                else:
                    # Try Event tag for time control info
                    event_pattern = r'\[Event "[^"]*?(?:Bullet|Blitz|Rapid|Classical)[^"]*?"'
                    event_match = re.search(event_pattern, self.pgn, re.IGNORECASE)
                    if event_match:
                        event = event_match.group(0).lower()
                        if 'bullet' in event:
                            return 'bullet'
                        elif 'blitz' in event:
                            return 'blitz'
                        elif 'rapid' in event:
                            return 'rapid'
                        elif 'classical' in event:
                            return 'classical'
                    return None
            else:  # lichess
                # Try direct time control pattern
                time_pattern = r'(?:TimeControl |^)(\d+)\+(\d+)'
                match = re.search(time_pattern, self.pgn)
                if match:
                    base_minutes = int(match.group(1))
                    increment = int(match.group(2))
                    total_minutes = base_minutes + (increment * 40 / 60)  # Assume 40 moves
                else:
                    # Try Event tag for time control info
                    event_pattern = r'\[Event "[^"]*?(?:Bullet|Blitz|Rapid|Classical)[^"]*?"'
                    event_match = re.search(event_pattern, self.pgn, re.IGNORECASE)
                    if event_match:
                        event = event_match.group(0).lower()
                        if 'bullet' in event:
                            return 'bullet'
                        elif 'blitz' in event:
                            return 'blitz'
                        elif 'rapid' in event:
                            return 'rapid'
                        elif 'classical' in event:
                            return 'classical'
                    return None
            
            # Categorize based on total time
            if total_minutes < 3:
                return 'bullet'
            elif total_minutes < 10:
                return 'blitz'
            elif total_minutes < 30:
                return 'rapid'
            else:
                return 'classical'
        except Exception as e:
            logger.error(f"Error determining time control category: {str(e)}")
            return None

    def get_player_rating(self, username: str) -> Optional[int]:
        """Get the rating of a specific player in this game."""
        if self.white.lower() == username.lower():
            return self.white_elo
        elif self.black.lower() == username.lower():
            return self.black_elo
        return None

    def get_opponent_username(self, username: str) -> Optional[str]:
        """Get the opponent's username for a given player."""
        if self.white.lower() == username.lower():
            return self.black
        elif self.black.lower() == username.lower():
            return self.white
        return None

    def get_result_for_player(self, username: str) -> Optional[str]:
        """Get the game result from a specific player's perspective."""
        if not username:
            return None
            
        if self.white.lower() == username.lower():
            if self.result == '1-0':
                return 'win'
            elif self.result == '0-1':
                return 'loss'
            elif self.result == '1/2-1/2':
                return 'draw'
        elif self.black.lower() == username.lower():
            if self.result == '1-0':
                return 'loss'
            elif self.result == '0-1':
                return 'win'
            elif self.result == '1/2-1/2':
                return 'draw'
        return None

class GameAnalysis(models.Model):
    """Model representing a detailed game analysis."""
    game = models.OneToOneField(Game, on_delete=models.CASCADE)
    
    # Enhanced fields
    metrics = models.JSONField(default=dict)
    phase_metrics = models.JSONField(default=dict)  # Opening, middlegame, endgame
    time_metrics = models.JSONField(default=dict)
    tactical_metrics = models.JSONField(default=dict)
    positional_metrics = models.JSONField(default=dict)
    feedback = models.JSONField(default=dict)
    time_control_feedback = models.JSONField(default=dict)
    study_plan = models.JSONField(default=dict)
    cache_key = models.CharField(max_length=100, unique=True, default='default_cache_key')
    analysis_metadata = models.JSONField(default=dict)  # Version, settings used, etc.
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'game_analysis'
        indexes = [
            models.Index(fields=['cache_key']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f"Analysis for {self.game}"

class AnalysisCache(models.Model):
    """Model to track cache usage and implement eviction policies."""
    key = models.CharField(max_length=100, primary_key=True)
    size_bytes = models.IntegerField()
    last_accessed = models.DateTimeField(auto_now=True)
    priority = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'analysis_cache'
        indexes = [
            models.Index(fields=['last_accessed']),
            models.Index(fields=['priority']),
            models.Index(fields=['expires_at']),
        ]

class Transaction(models.Model):
    """Model representing a credit transaction."""
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('usage', 'Usage'),
        ('refund', 'Refund'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credits = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    stripe_payment_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.transaction_type} - {self.credits} credits for {self.user.username}"

    class Meta:
        db_table = 'transactions'

class BatchAnalysis(models.Model):
    """Model representing a batch analysis of multiple games."""
    name = models.CharField(max_length=100)
    description = models.TextField()
    games = models.ManyToManyField(Game, related_name='batch_analyses')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')  # e.g., 'pending', 'completed'

    def __str__(self):
        return self.name
