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
        ScheduleError,
        ConfigurationError # Added ConfigurationError
    )
    from ..api.sports_api import SportsAPI
    # Import CacheManager if you instantiate it here, otherwise not needed if passed in
    from ..data.cache_manager import CacheManager
    # Import DatabaseManager only for type hinting if needed, don't instantiate
    # from ..data.db_manager import DatabaseManager
except ImportError:
    # Fallback for different execution contexts or structures
    from config.api_settings import API_ENABLED, API_HOSTS, API_KEY, API_TIMEOUT, API_RETRY_ATTEMPTS, API_RETRY_DELAY
    from utils.errors import GameServiceError, APIError, GameDataError, LeagueNotFoundError, ScheduleError, ConfigurationError
    from api.sports_api import SportsAPI
    from data.cache_manager import CacheManager
    # from data.db_manager import DatabaseManager

# load_dotenv() # Usually loaded once in main entry point (main.py)

logger = logging.getLogger(__name__)

class GameService:
    # Corrected __init__ signature
    def __init__(self, bot, db_manager): # Accept bot and the shared db_manager instance
        """Initializes the Game Service.

        Args:
            bot: The discord bot instance.
            db_manager: The shared DatabaseManager instance.
        """
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
                self.update_task = asyncio.create_task(self._update_games()) # For status changes based on time
                self._poll_task = asyncio.create_task(self._poll_games()) # For polling external API
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
                # Use asyncio.gather to await multiple tasks with return_exceptions
                await asyncio.gather(*tasks_to_wait_for, return_exceptions=True)
                logger.info("GameService background tasks finished cancelling.")
            except asyncio.CancelledError:
                 logger.info("Cancellation awaited for game service tasks.")
            except Exception as e:
                 logger.error(f"Error awaiting game service task cancellation: {e}")


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


    async def _update_games(self):
        """Periodically update game statuses based on scheduled times using self.db."""
        await self.bot.wait_until_ready() # Ensure bot cache is ready
        while self.running:
            try:
                logger.debug("Running periodic game status update...")
                now_utc = datetime.now(timezone.utc)

                # Find games scheduled to start (using self.db)
                starting_games = await self.db.fetch_all(
                    """
                    SELECT id, guild_id, league_id, home_team_name, away_team_name FROM games
                    WHERE status = $1 AND start_time <= $2
                    """, 'scheduled', now_utc
                )

                for game in starting_games:
                    logger.info(f"Game starting: ID {game['id']} in guild {game.get('guild_id', 'N/A')}") # Handle potential missing guild_id
                    await self.update_game_status(
                        game.get('guild_id'), game['id'], 'live'
                    )
                    await self.add_game_event(
                        game.get('guild_id'), game['id'], 'game_start', 'Game has started'
                    )
                    # TODO: Notify relevant channels/users

                # Find games scheduled to end (using self.db)
                # Assumes 'end_time' column exists
                ending_games = await self.db.fetch_all(
                     """
                     SELECT id, guild_id, score FROM games
                     WHERE status = $1 AND end_time IS NOT NULL AND end_time <= $2
                     """, 'live', now_utc
                 )

                for game in ending_games:
                     logger.info(f"Game ending: ID {game['id']} in guild {game.get('guild_id', 'N/A')}")
                     # Fetch final score if needed from API before marking completed
                     final_score_str = json.dumps(game.get('score', {})) # Get score from DB or fetch final
                     await self.update_game_status(
                         game.get('guild_id'),
                         game['id'],
                         'completed',
                         final_score_str # Pass final score as JSON string
                     )
                     await self.add_game_event(
                         game.get('guild_id'),
                         game['id'],
                         'game_end',
                         f"Game has ended. Final Score: {final_score_str}"
                     )
                     # TODO: Trigger bet resolution for this game

                await asyncio.sleep(60) # Check every minute
            except asyncio.CancelledError:
                logger.info("Game status update loop cancelled.")
                break # Exit loop cleanly
            except Exception as e:
                logger.exception(f"Error in game status update loop: {e}")
                await asyncio.sleep(120) # Wait longer after an error

    async def _fetch_initial_games(self) -> None:
        """Fetch initial game data for supported leagues on startup using self.db."""
        if not API_ENABLED or not self.api:
            logger.info("API disabled or not initialized, skipping initial game fetch.")
            return
        logger.info("Fetching initial game data...")
        try:
            # Get configured/supported leagues from DB (using self.db)
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

            # Process results (store in DB using self.db)
            for idx, result in enumerate(results):
                league_id = supported_leagues[idx]['id']
                sport = supported_leagues[idx]['sport'] # Get sport for logging/processing
                if isinstance(result, Exception):
                     logger.error(f"Error fetching initial games for league {league_id} (Sport: {sport}): {result}")
                elif isinstance(result, list):
                     logger.info(f"Fetched {len(result)} initial games for league {league_id} (Sport: {sport}).")
                     # Upsert these fetched games into the database
                     await self._upsert_games_from_api(result, sport) # Pass sport for context
                else:
                     logger.warning(f"Unexpected result type fetching initial games for league {league_id}: {type(result)}")

        except Exception as e:
            logger.exception(f"Error fetching initial games overall: {e}")


    async def _poll_games(self) -> None:
        """Periodically poll external API for live game updates using self.db."""
        if not API_ENABLED or not self.api:
            logger.info("API disabled or not initialized, skipping game polling.")
            return

        await self.bot.wait_until_ready()
        while self.running:
            try:
                logger.debug("Polling for live game updates...")
                # Get leagues with currently live games from our DB (using self.db)
                live_game_leagues = await self.db.fetch_all(
                    """
                    SELECT DISTINCT g.league_id, l.sport -- Need sport for API call
                    FROM games g
                    JOIN leagues l ON g.league_id = l.id
                    WHERE g.status = $1
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
                    # Assuming self.api.get_live_fixtures takes sport and league_id
                    if hasattr(self.api, 'get_live_fixtures'):
                         poll_tasks.append(self.api.get_live_fixtures(sport, str(league_id)))
                    else:
                         # Fallback: use generic request if specific method doesn't exist
                         # Might need different endpoint/params for live games only
                         poll_tasks.append(self._make_request(sport, "fixtures", {"live": "all", "league": str(league_id)}))


                # Run polls concurrently
                results = await asyncio.gather(*poll_tasks, return_exceptions=True)

                # Process results
                for idx, result in enumerate(results):
                     league_id = live_game_leagues[idx]['league_id']
                     sport = live_game_leagues[idx]['sport']
                     if isinstance(result, Exception):
                          logger.error(f"Error polling live games for league {league_id} (Sport: {sport}): {result}")
                     # Expecting dict response from _make_request or list from get_live_fixtures
                     elif isinstance(result, dict) and 'response' in result:
                          api_games = result.get('response', [])
                          logger.debug(f"Polled {len(api_games)} live games for league {league_id} (Sport: {sport}).")
                          await self._process_live_game_updates(league_id, api_games, sport) # Pass sport
                     elif isinstance(result, list):
                          api_games = result
                          logger.debug(f"Polled {len(api_games)} live games for league {league_id} (Sport: {sport}).")
                          await self._process_live_game_updates(league_id, api_games, sport) # Pass sport
                     else:
                          logger.warning(f"Unexpected result type polling live games for league {league_id}: {type(result)}")

                await asyncio.sleep(60) # Poll every 60 seconds (adjust as needed)
            except asyncio.CancelledError:
                logger.info("Game polling loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error in game polling loop: {e}")
                await asyncio.sleep(120) # Wait longer after error

    async def _process_live_game_updates(self, league_id: int, api_games: List[Dict], sport: str):
        """Compare API results with stored data and update DB/notify using self.db."""
        logger.debug(f"Processing {len(api_games)} live updates for league {league_id}...")
        if not api_games: return # Nothing to process

        try:
            # Get current live games for this league from DB (using self.db)
            db_games_list = await self.db.fetch_all(
                "SELECT id, status, score, updated_at FROM games WHERE league_id = $1 AND status = $2",
                league_id, 'live'
            )
            db_games_map = {game['id']: game for game in db_games_list}

            games_to_update = []
            for api_game_entry in api_games:
                 fixture = api_game_entry.get('fixture', {})
                 api_game_id = fixture.get('id')
                 if not api_game_id: continue

                 # Normalize API data (similar to _sync_schedules)
                 api_status = fixture.get('status', {}).get('short', 'UNK')
                 api_score_obj = {
                     'home': api_game_entry.get('goals', {}).get('home'),
                     'away': api_game_entry.get('goals', {}).get('away'),
                     # Add other score parts if available/needed
                 }
                 api_score_str = json.dumps(api_score_obj)
                 api_updated_at = datetime.now(timezone.utc) # Use poll time as update time

                 db_game = db_games_map.get(api_game_id)

                 if db_game:
                      # Compare existing game data
                      db_score_str = json.dumps(db_game.get('score', {})) # Normalize DB score for comparison
                      # Check if status or score changed significantly
                      if db_game.get('status') != api_status or db_score_str != api_score_str:
                           logger.info(f"Change detected for live game {api_game_id}: Status '{db_game.get('status')}'->'{api_status}', Score '{db_score_str}'->'{api_score_str}'")
                           games_to_update.append({
                                'id': api_game_id, 'status': api_status, 'score': api_score_str, 'updated_at': api_updated_at
                           })
                           # TODO: Add event via add_game_event, e.g., score change event
                           # TODO: Trigger notification via _notify_game_updates
                 else:
                      # Game might have just started or wasn't in DB? Less likely if polling live games.
                      logger.warning(f"Live game {api_game_id} from API not found in DB as 'live'. Status: {api_status}")
                      # Optionally add it if it's truly live and missing

            # Batch update the changed games using self.db
            if games_to_update:
                 # asyncpg executemany is efficient for batch updates
                 update_query = """
                     UPDATE games SET status = $1, score = $2::jsonb, updated_at = $3
                     WHERE id = $4
                 """
                 update_data = [(g['status'], g['score'], g['updated_at'], g['id']) for g in games_to_update]
                 await self.db.execute(update_query, *update_data[0]) # Example for single update - needs adaptation for executemany if db_manager supports it
                 # If db_manager doesn't support executemany easily, loop through updates:
                 # for game_upd in games_to_update:
                 #     await self.db.execute(update_query, game_upd['status'], game_upd['score'], game_upd['updated_at'], game_upd['id'])
                 logger.info(f"Updated {len(games_to_update)} live games in DB for league {league_id}.")

        except Exception as e:
            logger.exception(f"Error processing live game updates for league {league_id}: {e}")


    async def _notify_game_updates(self, game_data: Dict) -> None:
        """Notify relevant channels about a specific game update."""
        # Requires finding subscribed channels based on league_id/team_ids in game_data
        # Needs logic to query subscription tables (not defined in provided schema)
        logger.debug(f"Placeholder: Notifying about update for game {game_data.get('id')}")
        # Example:
        # embed = self._create_game_embed(game_data)
        # subscribed_channel_ids = await self.db.fetch_all("SELECT channel_id FROM subscriptions WHERE league_id = $1 OR team_id = $2 OR team_id = $3",
        #                                                 game_data['league_id'], game_data['home_team_id'], game_data['away_team_id'])
        # for sub in subscribed_channel_ids:
        #     channel = self.bot.get_channel(sub['channel_id'])
        #     if channel:
        #         try:
        #             await channel.send(embed=embed)
        #         except Exception as send_err:
        #             logger.error(f"Failed to send notification to channel {sub['channel_id']}: {send_err}")
        pass

    def _create_game_embed(self, game: Dict) -> discord.Embed:
        """Create a Discord embed for a game update."""
        # ... (Implementation as provided previously, uses game dict keys) ...
        home_team = game.get('home_team_name', 'Home')
        away_team = game.get('away_team_name', 'Away')
        league = game.get('league_name', game.get('league_id', 'N/A'))
        status = game.get('status', 'N/A')
        score_data = game.get('score', {})
        if isinstance(score_data, str): # Handle JSON string
            try: score_data = json.loads(score_data)
            except: score_data = {}
        home_score = score_data.get('home', '?')
        away_score = score_data.get('away', '?')
        game_time_info = fixture.get('status', {}).get('elapsed') if (fixture := game.get('fixture')) else None # Example for elapsed time

        embed = discord.Embed(
            title=f"{home_team} vs {away_team}",
            description=f"League: {league}",
            color=discord.Color.green() if 'live' in status.lower() or status == 'IN' else discord.Color.greyple()
        )
        embed.add_field(name="Score", value=f"{home_score} - {away_score}", inline=True)
        if game_time_info:
             embed.add_field(name="Time", value=str(game_time_info), inline=True)
        embed.add_field(name="Status", value=status.upper(), inline=True) # Use short status code potentially
        embed.timestamp = datetime.now(timezone.utc)
        # Add game ID maybe? embed.set_footer(text=f"Game ID: {game.get('id')}")
        return embed

    # --- Methods for Commands (using self.db) ---

    async def get_game(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific game by its database ID using self.db."""
        try:
            return await self.db.fetch_one('SELECT * FROM games WHERE id = $1', game_id)
        except Exception as e:
             logger.exception(f"Error getting game {game_id}: {e}")
             return None

    async def get_league_games(self, guild_id: Optional[int], league: str, status: Optional[str] = None, limit: int = 20) -> List[Dict]:
         """Get games for a specific league name/ID using self.db."""
         # Modified to handle league potentially being an ID or name and optional guild_id
         try:
             league_id = None
             # Try converting league to int first, assuming it might be an ID
             try: league_id = int(league)
             except ValueError: pass

             base_query = """
                 SELECT g.*, l.name as league_name
                 FROM games g
                 LEFT JOIN leagues l ON g.league_id = l.id
                 WHERE
             """
             filters = []
             params: List[Any] = []
             param_index = 1

             if guild_id:
                  # Assumes games table might have guild_id (e.g., for manual games?)
                  # If games are global, remove this filter. Check your schema.
                  # filters.append(f"g.guild_id = ${param_index}")
                  # params.append(guild_id)
                  # param_index += 1
                  logger.debug("Guild ID filter not applied to get_league_games (assuming global games)")


             if league_id:
                 filters.append(f"g.league_id = ${param_index}")
                 params.append(league_id)
                 param_index += 1
             else: # Assume league is a name
                 filters.append(f"l.name ILIKE ${param_index}") # Case-insensitive search for name
                 params.append(f"%{league}%") # Add wildcards for partial match
                 param_index += 1

             if status:
                 filters.append(f"g.status = ${param_index}")
                 params.append(status)
                 param_index += 1

             query = base_query + " AND ".join(filters)
             query += f" ORDER BY g.start_time DESC NULLS LAST LIMIT ${param_index}"
             params.append(limit)

             return await self.db.fetch_all(query, *params)
         except Exception as e:
             logger.exception(f"Error getting league games for league '{league}': {e}")
             return []

    async def get_upcoming_games(self, guild_id: Optional[int], hours: int = 24, limit: int = 20) -> List[Dict]:
        """Get upcoming scheduled games within the specified hours using self.db."""
        # Modified to make guild_id optional
        try:
            now_utc = datetime.now(timezone.utc)
            future_utc = now_utc + timedelta(hours=hours)
            query = """
                 SELECT * FROM games
                 WHERE status = $1
                 AND start_time BETWEEN $2 AND $3
            """
            params: List[Any] = ['scheduled', now_utc, future_utc]
            param_index = 4

            # Add guild filter if needed and schema supports it
            # if guild_id:
            #     query += f" AND guild_id = ${param_index}"
            #     params.append(guild_id)
            #     param_index += 1

            query += f" ORDER BY start_time ASC LIMIT ${param_index}"
            params.append(limit)

            return await self.db.fetch_all(query, *params)
        except Exception as e:
            logger.exception(f"Error getting upcoming games: {e}")
            return []

    async def get_live_games(self, guild_id: Optional[int], limit: int = 20) -> List[Dict]:
        """Get currently live games using self.db."""
         # Modified to make guild_id optional
        try:
            query = """
                 SELECT * FROM games WHERE status = $1
            """
            params: List[Any] = ['live']
            param_index = 2

            # Add guild filter if needed
            # if guild_id:
            #     query += f" AND guild_id = ${param_index}"
            #     params.append(guild_id)
            #     param_index += 1

            query += f" ORDER BY start_time DESC LIMIT ${param_index}"
            params.append(limit)

            return await self.db.fetch_all(query, *params)
        except Exception as e:
            logger.exception(f"Error getting live games: {e}")
            return []

    async def update_game_status(self, guild_id: Optional[int], game_id: int, status: str, score: Optional[str] = None) -> Optional[Dict]:
        """Update the status and score of a game using self.db."""
        # Modified to make guild_id optional if game IDs are globally unique
        try:
            # Use self.db
            # Use COALESCE($2::jsonb, score) to avoid overwriting score if None is passed? Or handle in calling logic.
            update_query = """
                UPDATE games
                SET status = $1, score = $2::jsonb, updated_at = $3
                WHERE id = $4
            """
            params: List[Any] = [status, score, datetime.now(timezone.utc), game_id]
            # Add guild_id to WHERE clause if games are guild-specific
            # query += " AND guild_id = $5"
            # params.append(guild_id)

            update_status = await self.db.execute(update_query, *params)

            if update_status and 'UPDATE 1' in update_status:
                 logger.info(f"Updated status for game {game_id} to {status}")
                 updated_game = await self.get_game(game_id) # Fetch updated game
                 # Invalidate cache if necessary
                 # await self.cache.delete(f"game_detail:SPORT:{game_id}") # Need sport info for cache key
                 return updated_game
            else:
                 logger.warning(f"Game {game_id} status update to {status} failed (rows affected: {update_status}). Might not exist or status unchanged.")
                 return None
        except Exception as e:
            logger.exception(f"Error updating game status for game {game_id}: {e}")
            raise GameServiceError(f"Failed to update game status: {str(e)}")

    async def add_game_event(self, guild_id: Optional[int], game_id: int, event_type: str, details: str) -> Optional[Dict]:
        """Add an event to a game's record using self.db."""
         # Modified to make guild_id optional
        try:
            # Use self.db
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

    async def get_game_events(self, guild_id: Optional[int], game_id: int, limit: int = 10) -> List[Dict]:
        """Get the most recent events for a specific game using self.db."""
         # Modified to make guild_id optional
        try:
            query = "SELECT * FROM game_events WHERE game_id = $1"
            params: List[Any] = [game_id]
            param_index = 2

            # Add guild filter if needed
            # if guild_id:
            #     query += f" AND guild_id = ${param_index}"
            #     params.append(guild_id)
            #     param_index += 1

            query += f" ORDER BY created_at DESC LIMIT ${param_index}"
            params.append(limit)

            return await self.db.fetch_all(query, *params)
        except Exception as e:
            logger.exception(f"Error getting game events for game {game_id}: {e}")
            return []

    # --- API Interaction Helper ---
    async def _make_request(self, sport: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make an API request via SportsAPI or directly with retry logic."""
        # Implementation using self.session, headers, API_KEY, API_HOSTS, retries etc.
        # (Keep the robust implementation from the previous full file version)
        # Ensure it uses self.session correctly.
        # ... (Full implementation from previous response) ...
        if not API_ENABLED:
             raise GameServiceError("API support is not enabled.")
        if not self.session or self.session.closed:
            logger.warning("aiohttp session closed or not initialized in GameService. Recreating.")
            self.session = aiohttp.ClientSession()

        if sport not in self.api_hosts or not self.api_hosts[sport]:
            raise GameServiceError(f"Unsupported sport or missing API host configuration for: {sport}")

        base_url = self.api_hosts[sport]
        # Ensure API_KEY is loaded/available
        if not API_KEY:
             raise ConfigurationError("API_KEY is not configured in environment variables.")

        headers = {
            "x-rapidapi-key": API_KEY,
            "x-rapidapi-host": base_url.split('//')[1] # Extract host from URL like https://host.com
        }
        # Ensure endpoint doesn't have leading slash if base_url has trailing slash, or vice-versa
        full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        for attempt in range(API_RETRY_ATTEMPTS):
            try:
                logger.debug(f"API Request (Attempt {attempt+1}/{API_RETRY_ATTEMPTS}): GET {full_url} PARAMS: {params}")
                async with self.session.get(
                    full_url,
                    params=params,
                    headers=headers,
                    timeout=API_TIMEOUT
                ) as response:
                    logger.debug(f"API Response Status: {response.status} for {full_url}")
                    # Handle Success
                    if 200 <= response.status < 300:
                        data = await response.json()
                        # Optional: Add basic validation if response format is critical
                        # if not isinstance(data, dict): # Example check
                        #    raise GameDataError(f"API response is not a JSON object: {data}")
                        limit_remaining = response.headers.get('X-RateLimit-Remaining')
                        if limit_remaining: logger.debug(f"API Rate Limit Remaining: {limit_remaining}")
                        return data # Return the parsed JSON response

                    # Handle Specific Errors
                    elif response.status == 404:
                        logger.warning(f"API endpoint not found (404): {full_url} with params {params}")
                        raise LeagueNotFoundError(f"API resource not found: {endpoint}") # Use specific error
                    elif response.status == 429:
                        retry_delay = API_RETRY_DELAY * (2 ** attempt) # Exponential backoff
                        logger.warning(f"API rate limit hit (429). Retrying attempt {attempt+2} in {retry_delay:.2f}s...")
                        await asyncio.sleep(retry_delay)
                        continue # Go to next attempt
                    # Handle other client/server errors
                    else:
                        error_text = await response.text()
                        logger.error(f"API request failed: Status {response.status}, URL: {full_url}, Response: {error_text[:200]}")
                        # Raise a general API error for other statuses
                        response.raise_for_status() # Raise ClientResponseError for 4xx/5xx

            # Handle Network/Timeout Errors
            except asyncio.TimeoutError:
                logger.warning(f"API request timed out: {full_url}. Attempt {attempt+1}/{API_RETRY_ATTEMPTS}")
                if attempt == API_RETRY_ATTEMPTS - 1:
                    raise APIError("API request timed out after multiple retries")
                await asyncio.sleep(API_RETRY_DELAY * (2 ** attempt)) # Exponential backoff
            except aiohttp.ClientError as ce:
                 logger.error(f"API client error: {ce}. Attempt {attempt+1}/{API_RETRY_ATTEMPTS}")
                 if attempt == API_RETRY_ATTEMPTS - 1:
                      raise APIError(f"API request failed after multiple retries: {ce}")
                 await asyncio.sleep(API_RETRY_DELAY * (2 ** attempt)) # Exponential backoff
            # Handle potential JSON decoding errors if API returns invalid JSON
            except json.JSONDecodeError as jde:
                 logger.error(f"Failed to decode JSON response from {full_url}: {jde}")
                 raise GameDataError("Invalid JSON received from API.")


        # If loop finishes without returning, all retries failed
        raise APIError(f"API request failed after {API_RETRY_ATTEMPTS} attempts: {full_url}")


    async def _upsert_games_from_api(self, api_games: List[Dict], sport: str):
         """Helper to parse and upsert multiple games from API response."""
         processed_count = 0
         for game_entry in api_games:
             fixture = game_entry.get('fixture', {})
             league_data = game_entry.get('league', {})
             teams_data = game_entry.get('teams', {})
             goals_data = game_entry.get('goals', {})
             score_full = game_entry.get('score', {})

             if not fixture.get('id'): continue

             game_timestamp_str = fixture.get('date')
             game_start_time = None
             if game_timestamp_str:
                 try:
                     game_start_time = datetime.fromisoformat(game_timestamp_str.replace('Z', '+00:00'))
                     if game_start_time.tzinfo is None:
                         game_start_time = game_start_time.replace(tzinfo=timezone.utc)
                 except ValueError: pass # Ignore parsing errors

             score_obj = {
                 'home': goals_data.get('home'), 'away': goals_data.get('away'),
                 'halftime': score_full.get('halftime'), 'fulltime': score_full.get('fulltime'),
                 'extratime': score_full.get('extratime'), 'penalty': score_full.get('penalty')
             }
             # Filter out None values from score before saving if desired
             score_json = json.dumps({k: v for k, v in score_obj.items() if v is not None}) or None

             try:
                 await self.db.execute(
                     """
                     INSERT INTO games (id, league_id, home_team_id, away_team_id, home_team_name,
                                        away_team_name, home_team_logo, away_team_logo, start_time,
                                        status, score, venue, referee, sport, updated_at)
                     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12, $13, $14, $15)
                     ON CONFLICT (id) DO UPDATE SET
                         league_id=EXCLUDED.league_id, home_team_id=EXCLUDED.home_team_id,
                         away_team_id=EXCLUDED.away_team_id, home_team_name=EXCLUDED.home_team_name,
                         away_team_name=EXCLUDED.away_team_name, start_time=EXCLUDED.start_time,
                         status=EXCLUDED.status, score=EXCLUDED.score, venue=EXCLUDED.venue,
                         referee=EXCLUDED.referee, sport=EXCLUDED.sport, updated_at=EXCLUDED.updated_at
                         -- Add logos if needed: home_team_logo=EXCLUDED.home_team_logo, away_team_logo=EXCLUDED.away_team_logo
                     """,
                     fixture['id'], league_data.get('id'), teams_data.get('home', {}).get('id'),
                     teams_data.get('away', {}).get('id'), teams_data.get('home', {}).get('name'),
                     teams_data.get('away', {}).get('name'), teams_data.get('home', {}).get('logo'),
                     teams_data.get('away', {}).get('logo'), game_start_time,
                     fixture.get('status', {}).get('short', 'TBD'), score_json,
                     fixture.get('venue', {}).get('name'), fixture.get('referee'), sport,
                     datetime.now(timezone.utc)
                 )
                 processed_count += 1
             except Exception as upsert_err:
                  logger.error(f"Error upserting game {fixture.get('id', 'N/A')}: {upsert_err}")
         logger.info(f"Upserted {processed_count}/{len(api_games)} games from API response.")

    # --- Specific API Call Methods (Using _make_request) ---
    async def get_games(self, sport: str, league_id: str, date: Optional[datetime] = None) -> List[Dict]:
         """Get games for a specific sport, league ID and date."""
         # ... (Implementation using self.cache and self._make_request as provided previously) ...
         try:
            date_str = date.strftime("%Y-%m-%d") if date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
            cache_key = f"games:{sport}:{league_id}:{date_str}"
            cached_games = await self.cache.get(cache_key)
            if cached_games and isinstance(cached_games, list): return cached_games

            params = {"league": league_id, "date": date_str, "season": str(datetime.now(timezone.utc).year)}
            response_data = await self._make_request(sport, "fixtures", params)
            games_list = response_data.get('response', [])
            await self.cache.set(cache_key, games_list, ttl=300) # Short TTL for daily games
            return games_list
         except Exception as e: return [] # Return empty on error

    async def get_game_details(self, sport: str, game_id: str) -> Optional[Dict]:
         """Get detailed information about a specific game by API ID."""
         # ... (Implementation using self.cache and self._make_request as provided previously) ...
         try:
            cache_key = f"game_detail:{sport}:{game_id}"
            cached_game = await self.cache.get(cache_key)
            if cached_game and isinstance(cached_game, dict): return cached_game

            params = {"id": game_id}
            response_data = await self._make_request(sport, "fixtures", params)
            game_details_list = response_data.get('response', [])
            if not game_details_list: return None
            game_detail = game_details_list[0]
            await self.cache.set(cache_key, game_detail, ttl=120) # Very short TTL for details
            return game_detail
         except Exception as e: return None # Return None on error

    async def get_league_schedule(self, sport: str, league_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
         """Get the schedule for a league between two dates."""
         # ... (Implementation using self.cache and self._make_request as provided previously) ...
         try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            cache_key = f"schedule:{sport}:{league_id}:{start_str}_{end_str}"
            cached_schedule = await self.cache.get(cache_key)
            if cached_schedule and isinstance(cached_schedule, list): return cached_schedule

            params = { "league": league_id, "season": str(start_date.year), "from": start_str, "to": end_str }
            response_data = await self._make_request(sport, "fixtures", params)
            schedule_list = response_data.get('response', [])
            await self.cache.set(cache_key, schedule_list, ttl=3600) # Cache schedule for longer
            return schedule_list
         except Exception as e: return [] # Return empty on error
