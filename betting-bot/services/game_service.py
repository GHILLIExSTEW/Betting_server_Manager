# betting-bot/services/game_service.py

import discord
from discord import app_commands
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta, timezone # Ensure timezone is imported
import json
import aiohttp
import asyncio
import sys
import os
from dotenv import load_dotenv

# --- Relative Imports (assuming services/ is a sibling to config/, data/, utils/, api/) ---
# Adjust these paths if your project structure is different
try:
    from ..config.api_settings import (
        API_ENABLED,
        API_HOSTS,
        API_KEY,
        API_TIMEOUT,
        API_RETRY_ATTEMPTS,
        API_RETRY_DELAY
    )
    from ..utils.errors import (
        GameServiceError,
        APIError,
        GameDataError,
        LeagueNotFoundError,
        ScheduleError
    )
    from ..api.sports_api import SportsAPI
    # Import CacheManager if you instantiate it here, otherwise not needed if passed in
    from ..data.cache_manager import CacheManager
    # Import DatabaseManager only for type hinting if needed, don't instantiate
    # from ..data.db_manager import DatabaseManager
except ImportError:
    # Fallback for different execution contexts or structures
    from config.api_settings import API_ENABLED, API_HOSTS, API_KEY, API_TIMEOUT, API_RETRY_ATTEMPTS, API_RETRY_DELAY
    from utils.errors import GameServiceError, APIError, GameDataError, LeagueNotFoundError, ScheduleError
    from api.sports_api import SportsAPI
    from data.cache_manager import CacheManager
    # from data.db_manager import DatabaseManager

# load_dotenv() # Usually loaded once in main entry point (main.py)

logger = logging.getLogger(__name__)

class GameService:
    # Corrected __init__ signature
    def __init__(self, bot, db_manager): # Accept bot and the shared db_manager instance
        self.bot = bot
        self.db = db_manager # Use the passed-in db_manager instance
        self.cache = CacheManager() # Instantiate CacheManager here (or pass it in if managed centrally)
        self.session: Optional[aiohttp.ClientSession] = None
        self.update_task: Optional[asyncio.Task] = None
        self.active_games: Dict[str, Dict] = {} # In-memory state (consider if needed long-term)
        self.games: Dict[int, Dict] = {}  # In-memory state (consider if needed long-term)
        self.api = SportsAPI() if API_ENABLED else None
        self._poll_task: Optional[asyncio.Task] = None
        self.running = False
        # self.db_path = '...' # Not needed if db_manager is passed
        self.api_hosts = API_HOSTS # Use imported config


    async def start(self):
        """Initialize the game service's async components."""
        try:
            self.session = aiohttp.ClientSession()
            logger.info("GameService aiohttp session created.")

            # Ensure cache connects if it has an async connect method
            if hasattr(self.cache, 'connect'):
                 await self.cache.connect()
                 logger.info("GameService CacheManager connected.")

            if API_ENABLED and self.api:
                if hasattr(self.api, 'start'):
                    await self.api.start()
                    logger.info("GameService SportsAPI started.")
                # Fetch initial data immediately after starting API
                await self._fetch_initial_games()
                # Start background tasks
                self.update_task = asyncio.create_task(self._update_games())
                self._poll_task = asyncio.create_task(self._poll_games())
                logger.info("GameService background tasks created.")
            else:
                 logger.info("API is disabled, skipping initial fetch and polling.")

            self.running = True
            logger.info("Game service started successfully.")
        except Exception as e:
            logger.exception(f"Failed to start game service: {e}")
            # Cleanup partially started resources
            if self.session: await self.session.close()
            if API_ENABLED and self.api and hasattr(self.api, 'close'): await self.api.close()
            if hasattr(self.cache, 'close'): await self.cache.close()
            raise GameServiceError("Failed to start game service")

    async def stop(self):
        """Clean up resources used by the game service."""
        self.running = False # Signal loops to stop
        logger.info("Stopping GameService...")
        tasks_to_wait_for = []
        if self.update_task:
            self.update_task.cancel()
            tasks_to_wait_for.append(self.update_task)
            logger.info("Game service update task cancellation requested.")
        if self._poll_task:
             self._poll_task.cancel()
             tasks_to_wait_for.append(self._poll_task)
             logger.info("Game service poll task cancellation requested.")

        # Wait for tasks to finish cancelling
        if tasks_to_wait_for:
            try:
                await asyncio.wait(tasks_to_wait_for, timeout=5.0) # Wait max 5 seconds
            except asyncio.TimeoutError:
                 logger.warning("GameService background tasks did not finish cancelling within timeout.")
            except asyncio.CancelledError:
                 pass # Expected
            except Exception as e:
                 logger.error(f"Error awaiting task cancellation: {e}")


        if self.session:
            await self.session.close()
            logger.info("Game service aiohttp session closed.")
        # DB pool closing is handled centrally by the main bot class

        self.active_games.clear()
        self.games.clear()
        if API_ENABLED and self.api:
             if hasattr(self.api, 'close'):
                 await self.api.close()
                 logger.info("GameService SportsAPI closed.")
        if hasattr(self.cache, 'close'):
             await self.cache.close()
             logger.info("GameService CacheManager closed.")
        logger.info("Game service stopped successfully")

    async def _setup_commands(self):
        """(Deprecated here - Command setup should be centralized)."""
        # Commands have been moved to individual command files or a central manager
        pass

    async def _update_games(self):
        """Periodically update game statuses based on scheduled times."""
        await self.bot.wait_until_ready() # Ensure bot cache is ready
        while self.running:
            try:
                logger.debug("Running periodic game status update...")
                now_utc = datetime.now(timezone.utc)

                # Find games scheduled to start
                starting_games = await self.db.fetch_all(
                    """
                    SELECT id, guild_id, league_id, home_team_name, away_team_name FROM games
                    WHERE status = $1 AND start_time <= $2
                    """, 'scheduled', now_utc
                )

                for game in starting_games:
                    logger.info(f"Game starting: ID {game['id']} in guild {game['guild_id']}")
                    await self.update_game_status(
                        game['guild_id'], game['id'], 'live'
                    )
                    await self.add_game_event(
                        game['guild_id'], game['id'], 'game_start', 'Game has started'
                    )
                    # TODO: Notify relevant channels/users

                # Find games scheduled to end (use estimated duration or API end time if available)
                # This requires an 'end_time' column or estimated duration logic
                # Placeholder logic assuming an 'end_time' column exists:
                ending_games = await self.db.fetch_all(
                     """
                     SELECT id, guild_id, score FROM games
                     WHERE status = $1 AND end_time IS NOT NULL AND end_time <= $2
                     """, 'live', now_utc
                 )

                for game in ending_games:
                     logger.info(f"Game ending: ID {game['id']} in guild {game['guild_id']}")
                     # Fetch final score if needed from API before marking completed
                     final_score_str = json.dumps(game.get('score', {})) # Get score from DB or fetch final
                     await self.update_game_status(
                         game['guild_id'],
                         game['id'],
                         'completed',
                         final_score_str # Pass final score as JSON string
                     )
                     await self.add_game_event(
                         game['guild_id'],
                         game['id'],
                         'game_end',
                         f"Game has ended. Final Score: {final_score_str}"
                     )
                     # TODO: Trigger bet resolution for this game

                await asyncio.sleep(60) # Check every minute
            except asyncio.CancelledError:
                logger.info("Game status update loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error in game status update loop: {e}")
                await asyncio.sleep(120) # Wait longer after an error

    async def _fetch_initial_games(self) -> None:
        """Fetch initial game data for supported leagues on startup."""
        if not API_ENABLED or not self.api:
            logger.info("API disabled or not initialized, skipping initial game fetch.")
            return
        logger.info("Fetching initial game data...")
        try:
            # Get configured/supported leagues from DB (assuming 'leagues' table exists)
            supported_leagues = await self.db.fetch_all(
                "SELECT id, sport FROM leagues" # Fetch sport too if needed by API call
            )
            if not supported_leagues:
                 logger.warning("No supported leagues found in the database for initial fetch.")
                 return

            today = datetime.now(timezone.utc)
            # Fetch games for today and maybe tomorrow? Adjust range as needed.
            fetch_tasks = []
            for league in supported_leagues:
                 league_id = league['id']
                 sport = league['sport'] # Assumes sport column exists
                 # Schedule fetching task
                 fetch_tasks.append(self.get_games(sport, str(league_id), today))

            # Run fetches concurrently
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            # Process results (and store in DB/cache)
            for idx, result in enumerate(results):
                league_id = supported_leagues[idx]['id']
                if isinstance(result, Exception):
                     logger.error(f"Error fetching initial games for league {league_id}: {result}")
                elif isinstance(result, list):
                     logger.info(f"Fetched {len(result)} initial games for league {league_id}.")
                     # TODO: Store these fetched games in the database (games table)
                     # You'll need to adapt the game structure from the API response
                     # to match your 'games' table schema.
                else:
                     logger.warning(f"Unexpected result type fetching initial games for league {league_id}: {type(result)}")

        except Exception as e:
            logger.exception(f"Error fetching initial games overall: {e}")
            # Don't raise here, allow service to continue running

    async def _poll_games(self) -> None:
        """Periodically poll external API for live game updates."""
        if not API_ENABLED or not self.api:
            logger.info("API disabled or not initialized, skipping game polling.")
            return

        await self.bot.wait_until_ready()
        while self.running:
            try:
                logger.debug("Polling for live game updates...")
                # Get leagues with currently live games from our DB
                live_game_leagues = await self.db.fetch_all(
                    """
                    SELECT DISTINCT league_id, sport
                    FROM games
                    WHERE status = $1
                    """, 'live'
                )
                if not live_game_leagues:
                     logger.debug("No leagues with live games found in DB to poll.")
                     await asyncio.sleep(120) # Poll less frequently if nothing is live
                     continue

                poll_tasks = []
                for league in live_game_leagues:
                    league_id = league['league_id']
                    sport = league['sport']
                    # Schedule polling task for this league's live fixtures
                    # Note: API might need specific 'live' parameter, adjust SportsAPI call
                    poll_tasks.append(self.api.get_live_fixtures(sport, str(league_id))) # Assuming get_live_fixtures exists

                # Run polls concurrently
                results = await asyncio.gather(*poll_tasks, return_exceptions=True)

                # Process results
                for idx, result in enumerate(results):
                     league_id = live_game_leagues[idx]['league_id']
                     if isinstance(result, Exception):
                          logger.error(f"Error polling live games for league {league_id}: {result}")
                     elif isinstance(result, list):
                          logger.debug(f"Polled {len(result)} live games for league {league_id}.")
                          # Compare with DB/cache and update if scores/status changed
                          await self._process_live_game_updates(league_id, result)
                     else:
                          logger.warning(f"Unexpected result type polling live games for league {league_id}: {type(result)}")

                await asyncio.sleep(60) # Poll every 60 seconds (adjust as needed)
            except asyncio.CancelledError:
                logger.info("Game polling loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error in game polling loop: {e}")
                await asyncio.sleep(120) # Wait longer after error

    async def _process_live_game_updates(self, league_id: int, api_games: List[Dict]):
        """Compare API results with stored data and update DB/notify."""
        # This function needs detailed logic:
        # 1. Fetch current live games for this league_id from your DB.
        # 2. Create a map of game_id -> db_game_data.
        # 3. Iterate through api_games:
        #    a. If game exists in your DB map:
        #       i. Compare score, status, time from API with DB data.
        #       ii. If changed, call self.update_game_status() and self.add_game_event().
        #       iii. Maybe update cache.
        #       iv. Potentially trigger notifications via self._notify_game_updates().
        #    b. If game *doesn't* exist in DB map (e.g., started between polls):
        #       i. Add the new game to your DB.
        #       ii. Trigger notifications.
        # 4. Potentially check for games in DB map that are *not* in api_games (maybe they finished?).
        logger.debug(f"Processing {len(api_games)} live updates for league {league_id}...")
        # Placeholder for actual comparison logic
        pass


    async def _notify_game_updates(self, game_data: Dict) -> None:
        """Notify relevant channels about a specific game update."""
        # This function needs detailed logic:
        # 1. Find relevant guilds/channels subscribed to this game's league or teams.
        # 2. Format an embed using _create_game_embed().
        # 3. Send the embed to the appropriate channels.
        logger.debug(f"Notifying about update for game {game_data.get('id')}")
        # Placeholder
        pass

    def _create_game_embed(self, game: Dict) -> discord.Embed:
        """Create a Discord embed for a game update."""
        # Adapt based on your actual 'games' table structure / API response stored
        home_team = game.get('home_team_name', 'Home')
        away_team = game.get('away_team_name', 'Away')
        league = game.get('league_name', game.get('league_id', 'N/A')) # Need league name ideally
        status = game.get('status', 'N/A')
        score_data = game.get('score', {})
        if isinstance(score_data, str): # Handle if score is stored as JSON string
            try:
                score_data = json.loads(score_data)
            except json.JSONDecodeError:
                score_data = {}
        home_score = score_data.get('home', score_data.get('homescore', '?'))
        away_score = score_data.get('away', score_data.get('awayscore', '?'))
        game_time = game.get('time_elapsed', game.get('current_period', '')) # Example: get time/period if available

        embed = discord.Embed(
            title=f"{home_team} vs {away_team}",
            description=f"League: {league}",
            color=discord.Color.blue() if status.lower() == 'live' else discord.Color.greyple()
        )
        embed.add_field(name="Score", value=f"{home_score} - {away_score}", inline=True)
        if game_time:
             embed.add_field(name="Time/Period", value=str(game_time), inline=True)
        embed.add_field(name="Status", value=status.title(), inline=True)
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    # --- Methods for Commands ---

    async def get_game(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific game by its database ID."""
        try:
             # Use the shared db manager instance
            return await self.db.fetch_one('SELECT * FROM games WHERE id = $1', game_id)
        except Exception as e:
             logger.exception(f"Error getting game {game_id}: {e}")
             return None

    async def get_league_games(self, guild_id: int, league: str, status: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get games for a specific league, optionally filtered by status."""
        try:
            # This query might need adjustment - assumes 'league' is a name/code in the games table
            # Ideally, query by league_id
            query = """
                SELECT g.*, l.name as league_name -- Join to get league name
                FROM games g
                LEFT JOIN leagues l ON g.league_id = l.id
                WHERE g.guild_id = $1 AND l.name = $2 -- Assuming league name search
            """
            params: List[Any] = [guild_id, league]
            param_index = 3 # Start parameter index at 3

            if status:
                query += f" AND g.status = ${param_index}"
                params.append(status)
                param_index += 1

            query += f" ORDER BY g.start_time DESC NULLS LAST LIMIT ${param_index}"
            params.append(limit)

            return await self.db.fetch_all(query, *params)
        except Exception as e:
            logger.exception(f"Error getting league games for league '{league}': {e}")
            return []

    async def get_upcoming_games(self, guild_id: int, hours: int = 24, limit: int = 20) -> List[Dict]:
        """Get upcoming scheduled games within the specified hours."""
        try:
            now_utc = datetime.now(timezone.utc)
            future_utc = now_utc + timedelta(hours=hours)
            return await self.db.fetch_all(
                """
                SELECT * FROM games
                WHERE guild_id = $1
                AND status = $2
                AND start_time BETWEEN $3 AND $4
                ORDER BY start_time ASC
                LIMIT $5
                """,
                guild_id,
                'scheduled',
                now_utc,
                future_utc,
                limit
            )
        except Exception as e:
            logger.exception(f"Error getting upcoming games: {e}")
            return []

    async def get_live_games(self, guild_id: int, limit: int = 20) -> List[Dict]:
        """Get currently live games."""
        try:
            return await self.db.fetch_all(
                """
                SELECT * FROM games
                WHERE guild_id = $1
                AND status = $2
                ORDER BY start_time DESC
                LIMIT $3
                """,
                guild_id, 'live', limit
            )
        except Exception as e:
            logger.exception(f"Error getting live games: {e}")
            return []

    async def update_game_status(self, guild_id: int, game_id: int, status: str, score: Optional[str] = None) -> Optional[Dict]:
        """Update the status and score of a game."""
        try:
            # Update game in database
            await self.db.execute(
                """
                UPDATE games
                SET status = $1, score = $2::jsonb, updated_at = $3 -- Cast score string to JSONB
                WHERE id = $4 AND guild_id = $5
                """,
                status, score, datetime.now(timezone.utc), game_id, guild_id
            )
            # Fetch the updated game data to return (optional)
            updated_game = await self.get_game(game_id)
            logger.info(f"Updated status for game {game_id} to {status}")
            # TODO: Update cache if implementing game caching
            return updated_game
        except Exception as e:
            logger.exception(f"Error updating game status for game {game_id}: {e}")
            raise GameServiceError(f"Failed to update game status: {str(e)}")

    async def add_game_event(self, guild_id: int, game_id: int, event_type: str, details: str) -> Optional[Dict]:
        """Add an event to a game's record."""
        try:
            # Add event to database
            event = await self.db.fetch_one( # Use fetch_one with RETURNING
                """
                INSERT INTO game_events (
                    guild_id, game_id, event_type, details, created_at
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING * -- Return the newly inserted row
                """,
                guild_id, game_id, event_type, details, datetime.now(timezone.utc)
            )
            logger.info(f"Added event '{event_type}' for game {game_id}")
            return event
        except Exception as e:
            logger.exception(f"Error adding game event for game {game_id}: {e}")
            raise GameServiceError(f"Failed to add game event: {str(e)}")

    async def get_game_events(self, guild_id: int, game_id: int, limit: int = 10) -> List[Dict]:
        """Get the most recent events for a specific game."""
        try:
            return await self.db.fetch_all(
                """
                SELECT * FROM game_events
                WHERE guild_id = $1 AND game_id = $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                guild_id, game_id, limit
            )
        except Exception as e:
            logger.exception(f"Error getting game events for game {game_id}: {e}")
            return []

    # --- API Interaction Helper ---
    async def _make_request(self, sport: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make an API request via SportsAPI with retry logic."""
        if not API_ENABLED or not self.api:
             raise GameServiceError("API support is not enabled or initialized.")
        if not self.session or self.session.closed:
            logger.warning("aiohttp session closed or not initialized. Recreating.")
            self.session = aiohttp.ClientSession()

        # Use the SportsAPI instance for the actual call if it encapsulates logic
        # Or implement retry logic here directly. Assuming SportsAPI handles it for now.
        try:
            # This assumes SportsAPI has methods corresponding to endpoints
            # e.g., self.api.get_fixtures(sport=sport, endpoint=endpoint, params=params)
            # Or a generic method:
            # return await self.api.make_request(sport=sport, endpoint=endpoint, params=params)

            # --- Direct Implementation Example ---
            if sport not in self.api_hosts or not self.api_hosts[sport]:
                raise GameServiceError(f"Unsupported sport or missing API host: {sport}")

            base_url = self.api_hosts[sport]
            # Ensure API_KEY is loaded
            if not API_KEY:
                 raise ConfigurationError("API_KEY is not configured.")

            headers = {
                "x-rapidapi-key": API_KEY,
                "x-rapidapi-host": base_url.split('//')[1] # Extract host from URL
            }
            full_url = f"{base_url}/{endpoint}" # Ensure endpoint doesn't have leading /

            for attempt in range(API_RETRY_ATTEMPTS):
                try:
                    logger.debug(f"API Request (Attempt {attempt+1}/{API_RETRY_ATTEMPTS}): GET {full_url} PARAMS: {params}")
                    async with self.session.get(
                        full_url,
                        params=params,
                        headers=headers,
                        timeout=API_TIMEOUT
                    ) as response:
                        logger.debug(f"API Response Status: {response.status}")
                        if response.status == 200:
                            data = await response.json()
                            if not isinstance(data, dict) or 'response' not in data:
                                 logger.error(f"Invalid API response format: {data}")
                                 raise GameDataError("Invalid response format from API")
                            # Rate limit headers (example, adjust to actual API)
                            limit_remaining = response.headers.get('X-RateLimit-Remaining')
                            if limit_remaining: logger.debug(f"API Rate Limit Remaining: {limit_remaining}")
                            return data # Return the full response dict
                        elif response.status == 404:
                            logger.warning(f"API endpoint not found (404): {full_url} with params {params}")
                            raise LeagueNotFoundError(f"API resource not found: {endpoint}")
                        elif response.status == 429:
                            logger.warning(f"API rate limit hit (429). Retrying in {API_RETRY_DELAY}s...")
                            await asyncio.sleep(API_RETRY_DELAY * (attempt + 1)) # Exponential backoff basic
                            continue # Go to next attempt
                        else:
                            error_text = await response.text()
                            logger.error(f"API request failed: Status {response.status}, URL: {full_url}, Response: {error_text[:200]}")
                            raise APIError(f"API request failed with status {response.status}")
                except asyncio.TimeoutError:
                    logger.warning(f"API request timed out: {full_url}. Attempt {attempt+1}/{API_RETRY_ATTEMPTS}")
                    if attempt == API_RETRY_ATTEMPTS - 1:
                        raise APIError("API request timed out after multiple retries")
                    await asyncio.sleep(API_RETRY_DELAY * (attempt + 1)) # Exponential backoff basic
                except aiohttp.ClientError as ce:
                     logger.error(f"API client error: {ce}. Attempt {attempt+1}/{API_RETRY_ATTEMPTS}")
                     if attempt == API_RETRY_ATTEMPTS - 1:
                          raise APIError(f"API request failed after multiple retries: {ce}")
                     await asyncio.sleep(API_RETRY_DELAY * (attempt + 1))

            # If loop finishes without returning/raising specifically, something went wrong
            raise APIError("API request failed after all retry attempts.")
            # --- End Direct Implementation Example ---

        except Exception as e:
            logger.exception(f"Error making API request to {endpoint}: {e}")
            raise # Re-raise exceptions like GameServiceError, APIError, etc.


    # --- Specific API Call Methods ---
    # These might call _make_request or go via self.api

    async def get_games(self, sport: str, league_id: str, date: Optional[datetime] = None) -> List[Dict]:
        """Get games for a specific sport, league ID and date."""
        try:
            # Standardize date format if provided
            date_str = date.strftime("%Y-%m-%d") if date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
            cache_key = f"games:{sport}:{league_id}:{date_str}"

            # Check cache first
            cached_games = await self.cache.get(cache_key) # Use await if cache methods are async
            if cached_games and isinstance(cached_games, list):
                logger.debug(f"Cache hit for {cache_key}")
                return cached_games

            logger.debug(f"Cache miss for {cache_key}. Fetching from API.")
            # Make API request
            params = {"league": league_id, "date": date_str, "season": str(datetime.now(timezone.utc).year)}
            response_data = await self._make_request(sport, "fixtures", params)

            games_list = response_data.get('response', [])

            # Cache the results
            # Consider appropriate TTL from config/settings.py: from config.settings import GAME_CACHE_TTL
            await self.cache.set(cache_key, games_list, ttl=300) # Cache for 5 mins example

            return games_list

        except Exception as e:
            logger.exception(f"Error getting games for {sport}/{league_id}: {e}")
            # Don't raise here? Or raise specific error? Depends on desired behavior.
            return [] # Return empty list on error


    async def get_game_details(self, sport: str, game_id: str) -> Optional[Dict]:
        """Get detailed information about a specific game by API ID."""
        # Note: game_id here is likely the API's ID, not your DB's primary key 'id'
        try:
            cache_key = f"game_detail:{sport}:{game_id}"
            cached_game = await self.cache.get(cache_key)
            if cached_game and isinstance(cached_game, dict):
                logger.debug(f"Cache hit for {cache_key}")
                return cached_game

            logger.debug(f"Cache miss for {cache_key}. Fetching from API.")
            # Endpoint might be fixtures?id=xxx or similar depending on API
            params = {"id": game_id}
            response_data = await self._make_request(sport, "fixtures", params) # Assuming 'fixtures' endpoint takes 'id'

            game_details_list = response_data.get('response', [])
            if not game_details_list:
                 logger.warning(f"No game details found in API response for {sport} game ID {game_id}")
                 return None

            game_detail = game_details_list[0] # Assuming ID lookup returns a list with one item

            # Cache the results (short TTL for potentially live games?)
            await self.cache.set(cache_key, game_detail, ttl=120) # Cache for 2 mins example

            return game_detail

        except Exception as e:
            logger.exception(f"Error getting game details for {sport} game ID {game_id}: {e}")
            return None


    async def get_league_schedule(self, sport: str, league_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get the schedule for a league between two dates."""
        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            cache_key = f"schedule:{sport}:{league_id}:{start_str}_{end_str}"

            cached_schedule = await self.cache.get(cache_key)
            if cached_schedule and isinstance(cached_schedule, list):
                logger.debug(f"Cache hit for {cache_key}")
                return cached_schedule

            logger.debug(f"Cache miss for {cache_key}. Fetching from API.")
            # Make API request
            params = {
                "league": league_id,
                "season": str(start_date.year), # Season might be needed
                "from": start_str,
                "to": end_str
            }
            response_data = await self._make_request(sport, "fixtures", params) # Assuming 'fixtures' handles date ranges

            schedule_list = response_data.get('response', [])

            # Cache the results (longer TTL for schedules?)
            await self.cache.set(cache_key, schedule_list, ttl=3600) # Cache for 1 hour example

            return schedule_list

        except Exception as e:
            logger.exception(f"Error getting league schedule for {sport}/{league_id}: {e}")
            return [] # Return empty list on error
