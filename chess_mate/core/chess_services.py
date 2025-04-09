"""
This module provides services for interacting with external chess platforms such as Chess.com
and Lichess. It includes classes and methods to fetch game data, filter games by type, and
save game details to the database.
"""

import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import ndjson  # type: ignore
import requests
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import get_current_timezone, make_aware

from .eco_codes import get_opening_name
from .models import Game, Profile

logger = logging.getLogger(__name__)


class ChessComService:
    """
    Service class to interact with Chess.com API.
    """

    BASE_URL = "https://api.chess.com/pub/player"
    platform = "chess.com"

    # Rate limiting settings
    MIN_REQUEST_INTERVAL = 2  # Minimum seconds between requests
    MAX_RETRIES = 5  # Maximum number of retries
    INITIAL_RETRY_DELAY = 2  # Initial retry delay in seconds
    MAX_RETRY_DELAY = 32  # Maximum retry delay in seconds
    REQUEST_TIMEOUT = 10  # Request timeout in seconds

    _last_request_time = 0

    @classmethod
    def _wait_for_rate_limit(cls):
        """Wait for rate limit if needed."""
        current_time = time.time()
        time_since_last = current_time - cls._last_request_time
        if time_since_last < cls.MIN_REQUEST_INTERVAL:
            time.sleep(cls.MIN_REQUEST_INTERVAL - time_since_last)
        cls._last_request_time = time.time()

    @classmethod
    def _make_request(cls, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """Make a request with retries and rate limiting."""
        if not headers:
            headers = {"User-Agent": "ChessMate/1.0", "Accept": "application/json"}

        retry_delay = cls.INITIAL_RETRY_DELAY
        last_error = None

        for attempt in range(cls.MAX_RETRIES):
            try:
                cls._wait_for_rate_limit()
                response = requests.get(url, headers=headers, timeout=cls.REQUEST_TIMEOUT)

                if response.status_code == 429:  # Rate limit hit
                    retry_after = int(response.headers.get("Retry-After", retry_delay))
                    logger.warning(f"Rate limit hit, waiting {retry_after}s before retry")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < cls.MAX_RETRIES - 1:
                    logger.warning(
                        f"Request failed ({str(e)}), attempt {attempt + 1}/{cls.MAX_RETRIES}. Waiting {retry_delay}s"
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, cls.MAX_RETRY_DELAY)
                    continue

        raise last_error or Exception(f"Failed after {cls.MAX_RETRIES} attempts")

    @staticmethod
    def fetch_archives(username: str) -> List[str]:
        """Fetch the list of archives for a given username."""
        try:
            url = f"{ChessComService.BASE_URL}/{username}/games/archives"
            response = ChessComService._make_request(url)
            archives = response.json().get("archives", [])
            logger.info(f"Successfully fetched {len(archives)} archives for {username}")
            return archives
        except Exception as e:
            logger.error(f"Failed to fetch archives for {username}: {str(e)}")
            return []

    @staticmethod
    def _extract_pgn_info(pgn_text):
        """Extract information from PGN text."""
        info = {}
        if not pgn_text:
            logger.warning("Empty PGN text")
            return info

        logger.info(f"Extracting info from PGN: {pgn_text[:200]}...")  # Log first 200 chars

        # Extract date from [UTCDate "YYYY.MM.DD"] or [Date "YYYY.MM.DD"]
        date_match = re.search(r'\[(UTCDate|Date)\s+"(\d{4}\.\d{2}\.\d{2})"\]', pgn_text)
        if date_match:
            date_str = date_match.group(2)
            try:
                year, month, day = map(int, date_str.split("."))
                info["date"] = datetime(year, month, day)
            except (ValueError, TypeError):
                logger.warning(f"Invalid date format: {date_str}")
                info["date"] = None

        # Extract time from [UTCTime "HH:mm:ss"]
        time_match = re.search(r'\[UTCTime\s+"(\d{2}:\d{2}:\d{2})"\]', pgn_text)
        if time_match:
            time_str = time_match.group(1)
            try:
                info["time"] = datetime.strptime(time_str, "%H:%M:%S").time()
            except ValueError:
                logger.warning(f"Invalid time format: {time_str}")
                info["time"] = None

        # Extract opening information
        eco_url_match = re.search(r'\[ECOUrl\s+"[^"]+/openings/([^"]+)"\]', pgn_text)
        if eco_url_match:
            info["opening"] = eco_url_match.group(1).replace("-", " ")
        else:
            opening_match = re.search(r'\[Opening\s+"([^"]+)"\]', pgn_text)
            if opening_match:
                info["opening"] = opening_match.group(1)
            else:
                eco_match = re.search(r'\[ECO\s+"([^"]+)"\]', pgn_text)
                info["opening"] = eco_match.group(1) if eco_match else "Unknown Opening"

        # Combine date and time
        if info.get("date") and info.get("time"):
            info["played_at"] = make_aware(datetime.combine(info["date"], info["time"]))
        elif info.get("date"):
            info["played_at"] = make_aware(datetime.combine(info["date"], datetime.min.time()))
        else:
            info["played_at"] = make_aware(datetime.now())
            logger.warning("No date found in PGN, using current time")

        return info

    @staticmethod
    def _format_result(result: str, username: str) -> str:
        """Format the game result."""
        if result == "win":
            return "win"
        elif result in ["checkmated", "resigned", "timeout", "abandoned"]:
            return "loss"
        elif result in ["stalemate", "agreed", "repetition", "insufficient"]:
            return "draw"
        logger.warning(f"Unknown result format: {result}")
        return "unknown"

    @staticmethod
    def fetch_games(username: str, user: User, game_type: str = "rapid", limit: int = 10) -> Dict[str, Any]:
        """
        Fetch games from Chess.com API.
        """
        try:
            # Get the user profile from the logged-in user
            try:
                user_profile = Profile.objects.get(user=user)
            except Profile.DoesNotExist:
                logger.error(f"Profile not found for user {user.username}")
                return {"games": [], "total_found": 0, "saved": 0, "skipped": 0, "message": "Profile not found"}

            # Fetch archives
            archives = ChessComService.fetch_archives(username)
            if not archives:
                logger.warning(f"No archives found for user {username}")
                return {"games": [], "total_found": 0, "saved": 0, "skipped": 0, "message": "No archives found"}

            logger.info(f"Processing archives for {username}, game type: {game_type}, limit: {limit}")

            formatted_games = []
            skipped_count = 0
            saved_count = 0
            unique_games = set()
            target_count = limit  # Initial target count
            service = ChessComService()  # Create service instance

            # Process archives in reverse chronological order
            for archive_url in reversed(archives):
                try:
                    # Stop if we've reached the target count of saved games
                    if saved_count >= limit:
                        break

                    # Fetch games from archive
                    response = ChessComService._make_request(archive_url)
                    if response.status_code != 200:
                        continue

                    archive_data = response.json()
                    games = archive_data.get("games", [])

                    # Filter games by type
                    matching_games = (
                        [g for g in games if g.get("time_class") == game_type] if game_type != "all" else games
                    )

                    for game in matching_games:
                        # Stop if we've reached the target count of saved games
                        if saved_count >= limit:
                            break

                        # Extract game ID and check uniqueness
                        game_id = game.get("url", "").split("/")[-1]
                        if (
                            game_id in unique_games
                            or Game.objects.filter(game_id=game_id, platform="chess.com", user=user).exists()
                        ):
                            skipped_count += 1
                            continue

                        unique_games.add(game_id)

                        # Extract game information
                        pgn_info = ChessComService._extract_pgn_info(game.get("pgn", ""))
                        white = game.get("white", {}).get("username", "Unknown")
                        black = game.get("black", {}).get("username", "Unknown")

                        # Determine if the user was white or black
                        is_white = username.lower() == white.lower()
                        player_result = game.get("white" if is_white else "black", {}).get("result", "")

                        # Get ECO code and opening name
                        eco_code = None
                        eco_match = re.search(r'\[ECO\s+"([^"]+)"\]', game.get("pgn", ""))
                        if eco_match:
                            eco_code = eco_match.group(1)
                        opening_name = get_opening_name(eco_code) if eco_code else "Unknown Opening"

                        # Format game data
                        formatted_game = {
                            "game_id": game_id,
                            "platform": "chess.com",
                            "white": white,
                            "black": black,
                            "opponent": black if is_white else white,
                            "result": ChessComService._format_result(player_result, username),
                            "pgn": game.get("pgn", ""),
                            "date_played": pgn_info.get("played_at"),
                            "opening_name": opening_name,
                            "eco_code": eco_code,
                            "white_rating": game.get("white", {}).get("rating"),
                            "black_rating": game.get("black", {}).get("rating"),
                            "time_control": game.get("time_control"),
                        }

                        # Save the game using the service instance
                        saved_game = service.save_game(formatted_game, username, user)
                        if saved_game:
                            saved_count += 1
                            formatted_games.append(formatted_game)

                except Exception as e:
                    logger.error(f"Error processing archive {archive_url}: {str(e)}")
                    continue

            logger.info(f"Completed fetching games. Saved: {saved_count}, Skipped: {skipped_count}")
            return {
                "games": formatted_games[:limit],
                "total_found": len(formatted_games) + skipped_count,
                "skipped": skipped_count,
                "saved": saved_count,
                "message": f"Successfully imported {saved_count} {game_type} games",
            }

        except Exception as e:
            logger.error(f"Error fetching games from Chess.com: {str(e)}")
            return {"games": [], "total_found": 0, "skipped": 0, "saved": 0, "message": f"Error: {str(e)}"}

    def save_game(self, game_data: Dict[str, Any], username: str, user: User) -> Optional[Game]:
        """Save a Chess.com game to the database."""
        try:
            # Get the user profile
            try:
                profile = Profile.objects.get(user=user)
                if not profile.chess_com_username:
                    profile.chess_com_username = username
                    profile.save()
            except Profile.DoesNotExist:
                logger.error(f"Profile not found for user {user.username}")
                return None

            # Check if game already exists for this user
            game_id = game_data.get("game_id")
            if not game_id:
                logger.error("Game ID not found in game data")
                return None

            if Game.objects.filter(game_id=game_id, platform=self.platform, user=user).exists():
                logger.warning(f"Game {game_id} already exists for user {user.username}")
                return None

            # Create the game object with transaction
            with transaction.atomic():
                game = Game.objects.create(
                    user=user,
                    platform=self.platform,
                    game_id=game_id,
                    white=game_data.get("white", "Unknown"),
                    black=game_data.get("black", "Unknown"),
                    opponent=game_data.get("opponent", "Unknown"),
                    result=game_data.get("result", "unknown"),
                    pgn=game_data.get("pgn", ""),
                    date_played=game_data.get("date_played", timezone.now()),
                    opening_name=game_data.get("opening_name", "Unknown Opening"),
                    white_elo=game_data.get("white_rating"),
                    black_elo=game_data.get("black_rating"),
                    time_control=game_data.get("time_control"),
                )

                # Update user's rating if available
                time_category = game.get_time_control_category()
                if time_category:
                    user_played_as_white = username.lower() == game_data.get("white", "").lower()
                    if user_played_as_white and game_data.get("white_rating"):
                        profile.update_rating(time_category, int(game_data["white_rating"]))
                    elif not user_played_as_white and game_data.get("black_rating"):
                        profile.update_rating(time_category, int(game_data["black_rating"]))

                logger.info(f"Successfully saved game {game_id} for user {user.username}")
            return game

        except Exception as e:
            logger.error(f"Error saving game: {str(e)}")
            return None

    def get_games(self, username: str, limit: int = 10, game_type: str = "all") -> List[Dict[str, Any]]:
        """
        Get games for a user from Chess.com.
        This is a wrapper around fetch_games that returns a list of game data objects.
        
        Args:
            username: The Chess.com username
            limit: Maximum number of games to fetch (default: 10)
            game_type: Type of games to fetch (blitz, bullet, rapid, classical, all)
            
        Returns:
            List of game data objects
        """
        try:
            # Create a dummy user if needed for testing/API functionality
            user, _ = User.objects.get_or_create(username="api_system_user")
            
            # Fetch games
            result = self.fetch_games(username, user, game_type, limit)
            logger.info(f"Retrieved {len(result.get('games', []))} games for {username}")
            
            # Return the games list
            return result.get('games', [])
        except Exception as e:
            logger.error(f"Error getting games for {username}: {str(e)}", exc_info=True)
            return []


class LichessService:
    """
    Service class to interact with Lichess API.
    """

    BASE_URL = "https://lichess.org/api"
    platform = "lichess"

    @staticmethod
    def _format_pgn(game_data: Dict[str, Any]) -> str:
        """Format game data into a valid PGN string."""
        # Format the result string
        winner = game_data.get("winner")
        if winner == "white":
            result = "1-0"
        elif winner == "black":
            result = "0-1"
        else:
            result = "1/2-1/2"

        # Convert timestamp to date
        try:
            date = datetime.fromtimestamp(game_data.get("createdAt", 0) / 1000.0).strftime("%Y.%m.%d")
        except:
            date = "????.??.??"

        # Get time control
        clock = game_data.get("clock", {})
        initial = int(clock.get("initial", 0)) // 60  # Convert to minutes
        increment = clock.get("increment", 0)
        time_control = f"{initial}+{increment}"

        # Required PGN headers
        pgn = [
            f'[Event "Rated {game_data.get("speed", "game")}"]',
            f'[Site "https://lichess.org/{game_data.get("id", "")}"]',
            f'[Date "{date}"]',
            f'[White "{game_data.get("players", {}).get("white", {}).get("user", {}).get("name", "?")}"]',
            f'[Black "{game_data.get("players", {}).get("black", {}).get("user", {}).get("name", "?")}"]',
            f'[Result "{result}"]',
            f'[WhiteElo "{game_data.get("players", {}).get("white", {}).get("rating", "?")}"]',
            f'[BlackElo "{game_data.get("players", {}).get("black", {}).get("rating", "?")}"]',
            f'[TimeControl "{time_control}"]',
            f'[ECO "{game_data.get("opening", {}).get("eco", "?")}"]',
            f'[Opening "{game_data.get("opening", {}).get("name", "?")}"]',
            f'[Termination "{game_data.get("status", "Unknown")}"]',
        ]

        # Add moves
        moves = game_data.get("moves", "")
        if moves:
            # Add blank line between headers and moves as per PGN spec
            pgn.extend(["", moves])

        # Add final result after moves
        pgn.extend(["", result])

        # Join with newlines
        return "\n".join(pgn)

    @staticmethod
    def fetch_games(username: str, user: User, game_type: str = "rapid", limit: int = 10) -> Dict[str, Any]:
        """
        Fetch games from Lichess API.
        Args:
            username: Lichess username
            user: Django user object
            game_type: Type of games to fetch (blitz, bullet, rapid, classical, all)
            limit: Number of new games to fetch
        Returns:
            Dictionary containing:
            - success: Whether the operation was successful
            - games_saved: Number of new games saved
            - games_skipped: Number of games skipped (already in user's account)
            - message: Status message
        """
        try:
            # Get the user profile
            try:
                profile = Profile.objects.get(user=user)
                if not profile.lichess_username:
                    profile.lichess_username = username
                    profile.save()
            except Profile.DoesNotExist:
                logger.error(f"Profile not found for user {user.username}")
                return {"success": False, "games_saved": 0, "games_skipped": 0, "message": "Profile not found"}

            # Map game types to Lichess perfTypes
            game_type_map = {
                "blitz": "blitz",
                "bullet": "bullet",
                "rapid": "rapid",
                "classical": "classical",
                "all": None,
            }
            perf_type = game_type_map.get(game_type)

            games_saved = 0
            games_skipped = 0
            batch_size = 100  # Number of games to fetch per request
            since = None  # Timestamp to fetch games after

            logger.info(f"Fetching {limit} Lichess games for {username}, type: {game_type}")

            while games_saved < limit:
                # Prepare request parameters
                headers = {"Accept": "application/x-ndjson"}
                params = {"max": batch_size, "perfType": perf_type, "opening": True, "clocks": True, "evals": True}

                # Add since parameter for pagination if we have it
                if since is not None:
                    params["until"] = since

                # Remove None values from params
                params = {k: v for k, v in params.items() if v is not None}

                # Make request
                response = httpx.get(
                    f"{LichessService.BASE_URL}/games/user/{username}", headers=headers, params=params, timeout=10.0
                )
                response.raise_for_status()

                # Parse response
                games = list(ndjson.loads(response.text))
                if not games:
                    # No more games available
                    break

                # Update since for next request if needed
                since = games[-1].get("createdAt", 0)

                # Process games
                for game in games:
                    try:
                        game_id = game.get("id")
                        if not game_id:
                            continue

                        # Skip if game already exists for this user
                        if Game.objects.filter(game_id=game_id, platform="lichess", user=user).exists():
                            games_skipped += 1
                            continue

                        # Extract player usernames
                        white = game.get("players", {}).get("white", {}).get("user", {}).get("name", "Unknown")
                        black = game.get("players", {}).get("black", {}).get("user", {}).get("name", "Unknown")

                        # Skip if neither player matches the username
                        if username.lower() not in [white.lower(), black.lower()]:
                            continue

                        # Format game data
                        formatted_game = {
                            "game_id": game_id,
                            "platform": "lichess",
                            "white": white,
                            "black": black,
                            "opponent": black if username.lower() == white.lower() else white,
                            "result": LichessService._format_result(game.get("winner"), username),
                            "pgn": LichessService._format_pgn(game),
                            "date_played": make_aware(datetime.fromtimestamp(game.get("createdAt", 0) / 1000.0)),
                            "opening_name": game.get("opening", {}).get("name", "Unknown Opening"),
                            "eco_code": game.get("opening", {}).get("eco"),
                            "white_rating": game.get("players", {}).get("white", {}).get("rating"),
                            "black_rating": game.get("players", {}).get("black", {}).get("rating"),
                            "time_control": game.get("speed", game_type),
                        }

                        # Save the game
                        saved_game = LichessService().save_game(formatted_game, username, user)
                        if saved_game:
                            games_saved += 1
                            logger.info(f"Saved game {game_id} for user {user.username}")

                            if games_saved >= limit:
                                break

                    except Exception as e:
                        logger.error(f"Error processing game: {str(e)}")
                        continue

                if len(games) < batch_size:
                    # No more games available
                    break

            # Return results
            success = games_saved > 0
            message = (
                f"Successfully imported {games_saved} new {game_type} games "
                f"(skipped {games_skipped} existing games)"
            )

            logger.info(f"Finished fetching games. Saved: {games_saved}, Skipped: {games_skipped}")
            return {"success": success, "games_saved": games_saved, "games_skipped": games_skipped, "message": message}

        except Exception as e:
            logger.error(f"Error fetching games from Lichess: {str(e)}")
            return {"success": False, "games_saved": 0, "games_skipped": 0, "message": f"Error: {str(e)}"}

    @staticmethod
    def _format_result(winner: Optional[str], username: str) -> str:
        """Format the game result."""
        if winner is None:
            return "draw"
        elif winner == username:
            return "win"
        else:
            return "loss"

    def save_game(self, game_data: Dict[str, Any], username: str, user: User) -> Optional[Game]:
        """Save a game to the database."""
        try:
            # Extract game data safely with get() method
            game_id = game_data.get("game_id")
            if not game_id:
                logger.error("Game ID not found in game data")
                return None

            # Check if game already exists for this user
            if Game.objects.filter(game_id=game_id, platform="lichess", user=user).exists():
                logger.info(f"Game {game_id} already exists for user {user.username}, skipping")
                return None

            # Get the user profile
            try:
                profile = Profile.objects.get(user=user)
                if not profile.lichess_username:
                    profile.lichess_username = username
                    profile.save()
                    logger.info(f"Updated Lichess username for user {user.username} to {username}")
            except Profile.DoesNotExist:
                logger.error(f"Profile not found for user {user.username}")
                return None

            # Extract other game data safely with detailed logging
            white = game_data.get("white", "Unknown")
            black = game_data.get("black", "Unknown")
            result = game_data.get("result")
            opening_name = game_data.get("opening_name", "Unknown Opening")
            date_played = game_data.get("date_played", timezone.now())
            white_elo = game_data.get("white_rating")
            black_elo = game_data.get("black_rating")
            time_control = game_data.get("time_control")
            pgn = game_data.get("pgn", "")

            if not pgn:
                logger.error(f"PGN data missing for game {game_id}")
                return None

            # Log game details for debugging
            logger.debug(f"Saving game {game_id}:")
            logger.debug(f"- White: {white} ({white_elo})")
            logger.debug(f"- Black: {black} ({black_elo})")
            logger.debug(f"- Result: {result}")
            logger.debug(f"- Time Control: {time_control}")
            logger.debug(f"- Opening: {opening_name}")

            # Create game object with transaction
            with transaction.atomic():
                game = Game.objects.create(
                    user=user,
                    platform="lichess",
                    game_id=game_id,
                    white=white,
                    black=black,
                    result=result,
                    opponent=black if username.lower() == white.lower() else white,
                    opening_name=opening_name,
                    date_played=date_played,
                    white_elo=white_elo,
                    black_elo=black_elo,
                    time_control=time_control,
                    pgn=pgn,
                )

                # Update user's rating if available
                time_category = game.get_time_control_category()
                if time_category:
                    user_played_as_white = username.lower() == white.lower()
                    if user_played_as_white and white_elo:
                        profile.update_rating(time_category, white_elo)
                        logger.info(f"Updated {time_category} rating for user {user.username} to {white_elo}")
                    elif not user_played_as_white and black_elo:
                        profile.update_rating(time_category, black_elo)
                        logger.info(f"Updated {time_category} rating for user {user.username} to {black_elo}")

                logger.info(f"Successfully saved game {game_id} for user {user.username}")
            return game

        except Exception as e:
            logger.error(f"Error saving game {game_id if game_id else 'unknown'}: {str(e)}")
            return None

    def get_games(self, username: str, limit: int = 10, game_type: str = "all") -> List[Dict[str, Any]]:
        """
        Get games for a user from Lichess.
        This is a wrapper around fetch_games that returns a list of game data objects.
        
        Args:
            username: The Lichess username
            limit: Maximum number of games to fetch (default: 10)
            game_type: Type of games to fetch (blitz, bullet, rapid, classical, all)
            
        Returns:
            List of game data objects
        """
        try:
            # Create a dummy user if needed for testing/API functionality
            user, _ = User.objects.get_or_create(username="api_system_user")
            
            # Fetch games
            result = self.fetch_games(username, user, game_type, limit)
            logger.info(f"Retrieved {len(result.get('games', []))} games for {username}")
            
            # Return the games list
            return result.get('games', [])
        except Exception as e:
            logger.error(f"Error getting games for {username}: {str(e)}", exc_info=True)
            return []


def save_game(game: Dict[str, Any], username: str, user: User) -> Optional[Game]:
    """
    Save a game to the database.
    Args:
        game: The game data from the chess platform
        username: The username from the form input (NOT the logged-in user's username)
        user: The logged-in user object
    """
    try:
        # Convert input username to lowercase for comparison
        input_username = username.lower()

        # Get white and black player usernames and ratings
        white_username = str(game.get("white", "")).lower()
        black_username = str(game.get("black", "")).lower()
        white_rating = game.get("white_rating")
        black_rating = game.get("black_rating")

        # Determine if the input user was white or black
        is_white = white_username == input_username
        is_black = black_username == input_username

        if not (is_white or is_black):
            logger.warning(
                f"Game does not belong to requested player. Input: {input_username}, White: {white_username}, Black: {black_username}"
            )
            return None

        # First check for duplicate games by game_id if available
        game_id = game.get("game_id")
        game_url = game.get("url")
        
        # Log the game information for debugging
        logger.info(f"Checking for duplicate game - ID: {game_id}, URL: {game_url}, User: {user.id}")
        
        if game_id and Game.objects.filter(game_id=game_id, user=user).exists():
            logger.info(f"Game with ID {game_id} already exists for user {user.id}. Skipping.")
            return None
        
        # Also check by URL as fallback
        if game_url and Game.objects.filter(game_url=game_url, user=user).exists():
            logger.info(f"Game with URL {game_url} already exists for user {user.id}. Skipping.")
            return None

        # Set opponent and result based on player color
        opponent = black_username if is_white else white_username
        final_result = ChessComService._format_result(game.get("result", ""), input_username)

        # Get played_at date
        played_at = game.get("date_played") or timezone.now()

        # Get the rating for the player we're importing
        player_rating = white_rating if is_white else black_rating
        opponent_rating = black_rating if is_white else white_rating

        # Create the game with the original case-sensitive usernames for display
        saved_game = Game.objects.create(
            user=user,
            opponent=opponent or "Unknown",
            result=final_result,
            white=game.get("white", ""),  # Keep original case for display
            black=game.get("black", ""),  # Keep original case for display
            white_elo=white_rating,
            black_elo=black_rating,
            time_control=game.get("time_control"),
            platform=game.get("platform", "chess.com"),  # Use platform from game data
            game_id=game.get("game_id", ""),
            pgn=game.get("pgn", ""),
            date_played=played_at,
            opening_name=game.get("opening_name", "Unknown Opening"),
            game_url=game_url,
        )

        logger.info(
            f"Successfully saved game {game_id or game_url} for user {user.id} (played as {'white' if is_white else 'black'} with rating {player_rating})"
        )
        return saved_game

    except Exception as e:
        logger.error(f"Error saving game: {str(e)}", exc_info=True)
        return None
