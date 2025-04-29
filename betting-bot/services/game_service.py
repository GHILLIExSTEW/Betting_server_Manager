import discord
from discord import app_commands
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
import json
import aiohttp
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import the config settings
from config.api_settings import (
    API_ENABLED,
    API_HOSTS,
    API_KEY,
    API_TIMEOUT,
    API_RETRY_ATTEMPTS,
    API_RETRY_DELAY
)

# Import other modules after path setup
from data.db_manager import DatabaseManager
from data.cache_manager import CacheManager
from utils.errors import (
    GameServiceError,
    APIError,
    GameDataError,
    LeagueNotFoundError,
    ScheduleError
)
from api.sports_api import SportsAPI
import aiosqlite

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class GameService:
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.update_task: Optional[asyncio.Task] = None
        self.active_games: Dict[str, Dict] = {}
        self.games: Dict[int, Dict] = {}  # guild_id -> games
        self.api = SportsAPI() if API_ENABLED else None
        self.db = DatabaseManager()
        self.cache = CacheManager()
        self._poll_task: Optional[asyncio.Task] = None
        self.running = False
        self.db_path = 'bot/data/betting.db'
        self.api_hosts = API_HOSTS

    async def start(self):
        """Initialize the game service"""
        try:
            self.session = aiohttp.ClientSession()
            await self._setup_commands()
            if API_ENABLED:
                await self.api.start()
                await self._fetch_initial_games()
                self.update_task = asyncio.create_task(self._update_games())
                self._poll_task = asyncio.create_task(self._poll_games())
            self.running = True
            logger.info("Game service started successfully")
        except Exception as e:
            logger.error(f"Failed to start game service: {e}")
            raise GameServiceError("Failed to start game service")

    async def stop(self):
        """Clean up resources"""
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        if self.session:
            await self.session.close()
        if self.db:
            await self.db.close()
        self.active_games.clear()
        self.games.clear()
        if API_ENABLED:
            await self.api.close()
        self.running = False
        logger.info("Game service stopped successfully")

    async def _setup_commands(self):
        """Setup slash commands for the game service."""
        try:
            @self.bot.tree.command(
                name="games",
                description="View active games"
            )
            async def view_games(interaction: discord.Interaction, league: Optional[str] = None):
                await self._view_games(interaction, league)

            @self.bot.tree.command(
                name="odds",
                description="View odds for a game"
            )
            @app_commands.describe(
                game_id="The game ID"
            )
            async def odds(interaction: discord.Interaction, game_id: str):
                try:
                    await self._view_odds(interaction, game_id)
                except Exception as e:
                    logger.error(f"Error in odds command: {e}")
                    await interaction.response.send_message(
                        f"An error occurred: {str(e)}",
                        ephemeral=True
                    )

            logger.info("Game service commands registered successfully")
        except Exception as e:
            logger.error(f"Error setting up game service commands: {e}")
            raise GameServiceError("Failed to setup game service commands")

    async def _update_games(self):
        """Periodically update game statuses."""
        while self.running:
            try:
                # Get all active guilds
                guilds = await self.db.fetch(
                    "SELECT guild_id FROM guild_settings WHERE is_active = true"
                )

                for guild in guilds:
                    guild_id = guild['guild_id']

                    # Get scheduled games that should start
                    starting_games = await self.db.fetch(
                        """
                        SELECT * FROM games
                        WHERE guild_id = $1
                        AND status = 'scheduled'
                        AND start_time <= $2
                        """,
                        guild_id, datetime.utcnow()
                    )

                    for game in starting_games:
                        # Update game status to live
                        await self.update_game_status(
                            guild_id,
                            game['game_id'],
                            'live'
                        )

                        # Add game start event
                        await self.add_game_event(
                            guild_id,
                            game['game_id'],
                            'game_start',
                            'Game has started'
                        )

                    # Get live games that should end
                    ending_games = await self.db.fetch(
                        """
                        SELECT * FROM games
                        WHERE guild_id = $1
                        AND status = 'live'
                        AND end_time <= $2
                        """,
                        guild_id, datetime.utcnow()
                    )

                    for game in ending_games:
                        # Update game status to completed
                        await self.update_game_status(
                            guild_id,
                            game['game_id'],
                            'completed',
                            game.get('score', '0-0')
                        )

                        # Add game end event
                        await self.add_game_event(
                            guild_id,
                            game['game_id'],
                            'game_end',
                            'Game has ended'
                        )

                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in game update loop: {str(e)}")
                await asyncio.sleep(60)

    async def _view_games(self, interaction: discord.Interaction, league: Optional[str] = None):
        """View active games"""
        try:
            if league:
                games = await self.db.fetch_all(
                    """
                    SELECT * FROM games
                    WHERE league = ? AND status = 'active'
                    ORDER BY start_time
                    """,
                    league
                )
            else:
                games = await self.db.fetch_all(
                    """
                    SELECT * FROM games
                    WHERE status = 'active'
                    ORDER BY start_time
                    """
                )

            if not games:
                await interaction.response.send_message(
                    "No active games found.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Active Games",
                color=discord.Color.blue()
            )

            for game in games:
                score = json.loads(game['score'])
                embed.add_field(
                    name=f"{game['home_team']} vs {game['away_team']}",
                    value=(
                        f"League: {game['league']}\n"
                        f"Status: {game['status']}\n"
                        f"Score: {score.get('home', 0)} - {score.get('away', 0)}\n"
                        f"Start Time: {game['start_time']}"
                    ),
                    inline=False
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error viewing games: {e}")
            raise GameServiceError("Failed to view games")

    async def _view_odds(self, interaction: discord.Interaction, game_id: str):
        """View odds for a specific game"""
        try:
            # Try to get from cache first
            cached_game = await self.cache.get_json(f"game:{game_id}")
            if cached_game:
                game = cached_game
            else:
                # Get from database
                game = await self.db.fetch_one(
                    """
                    SELECT * FROM games
                    WHERE game_id = %s
                    """,
                    (game_id,)
                )
                if not game:
                    raise GameServiceError(f"Game {game_id} not found")

            odds = json.loads(game['odds'])
            embed = discord.Embed(
                title=f"Odds for {game['home_team']} vs {game['away_team']}",
                color=discord.Color.green()
            )

            for market, values in odds.items():
                embed.add_field(
                    name=market,
                    value=(
                        f"Home: {values.get('home', 'N/A')}\n"
                        f"Away: {values.get('away', 'N/A')}\n"
                        f"Draw: {values.get('draw', 'N/A')}"
                    ),
                    inline=True
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error viewing odds: {e}")
            raise GameServiceError("Failed to view odds")

    async def get_game(self, game_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM games WHERE id = ?', (game_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    async def create_game(self, name: str, description: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO games (name, description, created_at) VALUES (?, ?, datetime("now"))',
                (name, description)
            )
            await db.commit()
            return cursor.lastrowid

    async def _fetch_initial_games(self) -> None:
        """Fetch initial game data for all supported leagues."""
        if not API_ENABLED:
            logger.info("API is disabled, skipping initial game fetch")
            return

        try:
            # Get all supported leagues from settings
            leagues = await self.db.fetch_all(
                "SELECT league_code FROM supported_leagues WHERE is_active = true"
            )
            
            for league in leagues:
                league_code = league['league_code']
                games = await self.api.get_live_fixtures(league_code)
                if games:
                    self.games[league_code] = {game['id']: game for game in games}
                    # Cache the games
                    await self.cache.set(
                        f"games:{league_code}",
                        self.games[league_code],
                        ttl=3600  # Cache for 1 hour
                    )
        except Exception as e:
            logger.error(f"Error fetching initial games: {str(e)}")
            raise GameServiceError(f"Failed to fetch initial games: {str(e)}")

    async def _poll_games(self) -> None:
        """Periodically poll for game updates."""
        if not API_ENABLED:
            logger.info("API is disabled, skipping game polling")
            return

        while True:
            try:
                # Get all active leagues
                leagues = await self.db.fetch_all(
                    "SELECT league_code FROM supported_leagues WHERE is_active = true"
                )
                
                for league in leagues:
                    league_code = league['league_code']
                    # Get live fixtures
                    games = await self.api.get_live_fixtures(league_code)
                    if games:
                        # Update games dictionary
                        self.games[league_code] = {game['id']: game for game in games}
                        # Update cache
                        await self.cache.set(
                            f"games:{league_code}",
                            self.games[league_code],
                            ttl=3600
                        )
                        # Notify about game updates
                        await self._notify_game_updates(league_code, games)
                
                # Wait before next poll
                await asyncio.sleep(60)  # Poll every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in game polling: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _notify_game_updates(self, league_code: str, games: List[Dict]) -> None:
        """Notify about game updates to relevant channels."""
        try:
            # Get channels subscribed to this league
            channels = await self.db.fetch(
                """
                SELECT channel_id FROM league_subscriptions
                WHERE league_code = $1 AND is_active = true
                """,
                league_code
            )
            
            for channel in channels:
                channel_id = channel['channel_id']
                discord_channel = self.bot.get_channel(channel_id)
                if discord_channel:
                    for game in games:
                        # Create and send game update embed
                        embed = self._create_game_embed(game)
                        await discord_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error notifying game updates: {str(e)}")

    def _create_game_embed(self, game: Dict) -> discord.Embed:
        """Create a Discord embed for a game update."""
        embed = discord.Embed(
            title=f"{game['home_team']} vs {game['away_team']}",
            description=f"League: {game['league']}",
            color=discord.Color.blue()
        )
        
        # Add game details
        embed.add_field(name="Score", value=f"{game['home_score']} - {game['away_score']}", inline=True)
        embed.add_field(name="Time", value=game['time'], inline=True)
        embed.add_field(name="Status", value=game['status'], inline=True)
        
        # Add timestamp
        embed.timestamp = datetime.utcnow()
        
        return embed

    async def get_league_games(self, guild_id: int, league: str, status: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get games for a specific league."""
        try:
            query = """
                SELECT * FROM games
                WHERE guild_id = $1 AND league = $2
            """
            params = [guild_id, league]

            if status:
                query += " AND status = $3"
                params.append(status)

            query += " ORDER BY start_time DESC LIMIT $4"
            params.append(limit)

            return await self.db.fetch(query, *params)
        except Exception as e:
            logger.error(f"Error getting league games: {str(e)}")
            return []

    async def get_upcoming_games(self, guild_id: int, hours: int = 24, limit: int = 20) -> List[Dict]:
        """Get upcoming games within the specified hours."""
        try:
            return await self.db.fetch(
                """
                SELECT * FROM games
                WHERE guild_id = $1
                AND start_time BETWEEN $2 AND $3
                AND status = 'scheduled'
                ORDER BY start_time ASC
                LIMIT $4
                """,
                guild_id,
                datetime.utcnow(),
                datetime.utcnow() + timedelta(hours=hours),
                limit
            )
        except Exception as e:
            logger.error(f"Error getting upcoming games: {str(e)}")
            return []

    async def get_live_games(self, guild_id: int, limit: int = 20) -> List[Dict]:
        """Get currently live games."""
        try:
            return await self.db.fetch(
                """
                SELECT * FROM games
                WHERE guild_id = $1
                AND status = 'live'
                ORDER BY start_time DESC
                LIMIT $2
                """,
                guild_id, limit
            )
        except Exception as e:
            logger.error(f"Error getting live games: {str(e)}")
            return []

    async def update_game_status(self, guild_id: int, game_id: int, status: str, score: Optional[str] = None) -> Dict:
        """Update the status of a game."""
        try:
            # Update game in database
            await self.db.execute(
                """
                UPDATE games
                SET status = $1, score = $2, updated_at = $3
                WHERE game_id = $4 AND guild_id = $5
                """,
                status, score, datetime.utcnow(), game_id, guild_id
            )

            # Get updated game
            game = await self.db.fetch_one(
                """
                SELECT * FROM games WHERE game_id = $1
                """,
                game_id
            )

            # Update cache
            if guild_id in self.games and game_id in self.games[guild_id]:
                self.games[guild_id][game_id] = game

            return game
        except Exception as e:
            logger.error(f"Error updating game status: {str(e)}")
            raise GameServiceError(f"Failed to update game status: {str(e)}")

    async def add_game_event(self, guild_id: int, game_id: int, event_type: str, details: str) -> Dict:
        """Add an event to a game."""
        try:
            # Add event to database
            event_id = await self.db.execute(
                """
                INSERT INTO game_events (
                    guild_id, game_id, event_type, details, created_at
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING event_id
                """,
                guild_id, game_id, event_type, details, datetime.utcnow()
            )

            # Get event details
            event = await self.db.fetch_one(
                """
                SELECT * FROM game_events WHERE event_id = $1
                """,
                event_id
            )

            return event
        except Exception as e:
            logger.error(f"Error adding game event: {str(e)}")
            raise GameServiceError(f"Failed to add game event: {str(e)}")

    async def get_game_events(self, guild_id: int, game_id: int, limit: int = 10) -> List[Dict]:
        """Get events for a specific game."""
        try:
            return await self.db.fetch(
                """
                SELECT * FROM game_events
                WHERE guild_id = $1 AND game_id = $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                guild_id, game_id, limit
            )
        except Exception as e:
            logger.error(f"Error getting game events: {str(e)}")
            return []

    async def _make_request(self, sport: str, endpoint: str, params: Dict = None) -> Dict:
        """Make an API request with retry logic."""
        if not self.session:
            raise GameServiceError("Game service not started")

        if sport not in self.api_hosts or not self.api_hosts[sport]:
            raise GameServiceError(f"Unsupported sport or missing API host: {sport}")

        base_url = self.api_hosts[sport]
        headers = {
            "x-rapidapi-key": API_KEY,
            "x-rapidapi-host": base_url.split('//')[1]
        }

        for attempt in range(API_RETRY_ATTEMPTS):
            try:
                async with self.session.get(
                    f"{base_url}/{endpoint}",
                    params=params,
                    headers=headers,
                    timeout=API_TIMEOUT
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        raise LeagueNotFoundError(f"League not found: {endpoint}")
                    else:
                        raise APIError(f"API request failed with status {response.status}")
            except asyncio.TimeoutError:
                if attempt == API_RETRY_ATTEMPTS - 1:
                    raise APIError("API request timed out")
                await asyncio.sleep(API_RETRY_DELAY)
            except Exception as e:
                if attempt == API_RETRY_ATTEMPTS - 1:
                    raise APIError(f"API request failed: {str(e)}")
                await asyncio.sleep(API_RETRY_DELAY)

    async def get_games(self, sport: str, league: str, date: Optional[datetime] = None) -> List[Dict]:
        """Get games for a specific sport, league and date."""
        try:
            # Check cache first
            cache_key = f"games_{sport}_{league}_{date.strftime('%Y-%m-%d') if date else 'today'}"
            cached_games = self.cache.get(cache_key)
            if cached_games:
                return cached_games

            # Make API request
            params = {"league": league}
            if date:
                params["date"] = date.strftime("%Y-%m-%d")
            
            response = await self._make_request(sport, "fixtures", params)
            
            # Validate response
            if not isinstance(response, dict) or 'response' not in response:
                raise GameDataError("Invalid response format from API")

            # Cache the results
            self.cache.set(cache_key, response['response'], ttl=3600)
            
            return response['response']

        except Exception as e:
            logger.error(f"Error getting games: {str(e)}")
            raise

    async def get_game_details(self, sport: str, game_id: str) -> Dict:
        """Get detailed information about a specific game."""
        try:
            # Check cache first
            cache_key = f"game_{sport}_{game_id}"
            cached_game = self.cache.get(cache_key)
            if cached_game:
                return cached_game

            # Make API request
            response = await self._make_request(sport, f"fixtures/{game_id}")
            
            # Validate response
            if not isinstance(response, dict) or 'response' not in response:
                raise GameDataError("Invalid response format from API")

            # Cache the results
            self.cache.set(cache_key, response['response'], ttl=3600)
            
            return response['response']

        except Exception as e:
            logger.error(f"Error getting game details: {str(e)}")
            raise

    async def get_league_schedule(self, sport: str, league: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get the schedule for a league between two dates."""
        try:
            # Check cache first
            cache_key = f"schedule_{sport}_{league}_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
            cached_schedule = self.cache.get(cache_key)
            if cached_schedule:
                return cached_schedule

            # Make API request
            params = {
                "league": league,
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d")
            }
            
            response = await self._make_request(sport, "fixtures", params)
            
            # Validate response
            if not isinstance(response, dict) or 'response' not in response:
                raise ScheduleError("Invalid response format from API")

            # Cache the results
            self.cache.set(cache_key, response['response'], ttl=3600)
            
            return response['response']

        except Exception as e:
            logger.error(f"Error getting league schedule: {str(e)}")
            raise 
