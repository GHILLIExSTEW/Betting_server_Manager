# betting-bot/services/game_service.py

"""Service for managing game data and interactions with sports APIs."""

import discord
from discord import app_commands
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta, timezone
import json
import aiohttp
import asyncio
import sys
import os

try:
    from ..config.api_settings import (
        API_ENABLED, API_HOSTS, API_KEY, API_TIMEOUT,
        API_RETRY_ATTEMPTS, API_RETRY_DELAY
    )
    from ..utils.errors import (
        GameServiceError, APIError, GameDataError, LeagueNotFoundError,
        ScheduleError, ConfigurationError
    )
    from ..api.sports_api import SportsAPI
    from ..data.cache_manager import CacheManager
except ImportError:
    from config.api_settings import API_ENABLED, API_HOSTS, API_KEY, API_TIMEOUT, API_RETRY_ATTEMPTS, API_RETRY_DELAY
    from utils.errors import GameServiceError, APIError, GameDataError, LeagueNotFoundError, ScheduleError, ConfigurationError
    from api.sports_api import SportsAPI
    from data.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class GameService:
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.cache = CacheManager()
        self.session: Optional[aiohttp.ClientSession] = None
        self.update_task: Optional[asyncio.Task] = None
        self.active_games: Dict[str, Dict] = {}
        self.games: Dict[int, Dict] = {}
        self.api = SportsAPI() if API_ENABLED else None
        self._poll_task: Optional[asyncio.Task] = None
        self.running = False
        self.api_hosts = API_HOSTS

    async def start(self):
        """Initialize the game service's async components."""
        try:
            self.session = aiohttp.ClientSession()
            logger.info("GameService aiohttp session created.")
            if hasattr(self.cache, 'connect'):
                await self.cache.connect()
                logger.info("GameService CacheManager connected.")

            if API_ENABLED and self.api:
                if hasattr(self.api, 'start'):
                    await self.api.start()
                    logger.info("GameService SportsAPI started.")
                self.update_task = asyncio.create_task(self._update_games())
                self._poll_task = asyncio.create_task(self._poll_games())
                logger.info("GameService background tasks created.")
            else:
                logger.info("API is disabled, skipping initial fetch and polling.")

            self.running = True
            logger.info("Game service started successfully.")
        except Exception as e:
            logger.exception(f"Failed to start game service: {e}")
            if self.session:
                await self.session.close()
            if API_ENABLED and self.api and hasattr(self.api, 'close'):
                await self.api.close()
            if hasattr(self.cache, 'close'):
                await self.cache.close()
            raise GameServiceError("Failed to start game service")

    async def stop(self):
        """Clean up resources used by the game service."""
        self.running = False
        logger.info("Stopping GameService...")
        tasks_to_wait_for = []
        if self.update_task:
            self.update_task.cancel()
            tasks_to_wait_for.append(self.update_task)
        if self._poll_task:
            self._poll_task.cancel()
            tasks_to_wait_for.append(self._poll_task)

        if tasks_to_wait_for:
            try:
                await asyncio.gather(*tasks_to_wait_for, return_exceptions=True)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error awaiting task cancellation: {e}")

        if self.session:
            await self.session.close()
        self.active_games.clear()
        self.games.clear()
        if API_ENABLED and self.api and hasattr(self.api, 'close'):
            await self.api.close()
        if hasattr(self.cache, 'close'):
            await self.cache.close()
        logger.info("Game service stopped successfully")

    async def _update_games(self):
        """Periodically update game statuses."""
        await self.bot.wait_until_ready()
        while self.running:
            try:
                logger.debug("Running periodic game status update...")
                now_utc = datetime.now(timezone.utc)

                starting_games = await self.db.fetch_all(
                    """
                    SELECT id, guild_id, league_id, home_team_name, away_team_name
                    FROM games
                    WHERE status = %s AND start_time <= %s
                    """,
                    'scheduled', now_utc
                )
                for game in starting_games:
                    logger.info(f"Game starting: ID {game['id']} in guild {game.get('guild_id', 'N/A')}")
                    await self.update_game_status(game.get('guild_id'), game['id'], 'live')
                    await self.add_game_event(game.get('guild_id'), game['id'], 'game_start', 'Game has started')

                ending_games = await self.db.fetch_all(
                    """
                    SELECT id, guild_id, score
                    FROM games
                    WHERE status = %s AND end_time IS NOT NULL AND end_time <= %s
                    """,
                    'live', now_utc
                )
                for game in ending_games:
                    logger.info(f"Game ending: ID {game['id']} in guild {game.get('guild_id', 'N/A')}")
                    final_score_str = json.dumps(game.get('score', {}))
                    await self.update_game_status(game.get('guild_id'), game['id'], 'completed', final_score_str)
                    await self.add_game_event(game.get('guild_id'), game['id'], 'game_end', f"Game has ended. Final Score: {final_score_str}")

                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("Game status update loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error in game status update loop: {e}")
                await asyncio.sleep(120)

    async def _fetch_initial_games(self) -> None:
        """Fetch initial game data from APIs."""
        if not API_ENABLED or not self.api:
            return
        logger.info("Fetching initial game data...")
        try:
            supported_leagues = await self.db.fetch_all("SELECT id, sport FROM leagues")
            if not supported_leagues:
                return

            today = datetime.now(timezone.utc)
            fetch_tasks = [self.get_games(league['sport'], str(league['id']), today) for league in supported_leagues]
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                league_id = supported_leagues[idx]['id']
                sport = supported_leagues[idx]['sport']
                if isinstance(result, Exception):
                    logger.error(f"Error fetching initial games for league {league_id} (Sport: {sport}): {result}")
                elif isinstance(result, list):
                    logger.info(f"Fetched {len(result)} initial games for league {league_id} (Sport: {sport}).")
                    await self._upsert_games_from_api(result, sport)
                else:
                    logger.warning(f"Unexpected result type fetching initial games for league {league_id}: {type(result)}")
        except Exception as e:
            logger.exception(f"Error fetching initial games overall: {e}")

    async def _poll_games(self) -> None:
        """Poll for live game updates."""
        if not API_ENABLED or not self.api:
            return
        await self.bot.wait_until_ready()
        while self.running:
            try:
                logger.debug("Polling for live game updates...")
                live_game_leagues = await self.db.fetch_all(
                    """
                    SELECT DISTINCT g.league_id, l.sport
                    FROM games g
                    JOIN leagues l ON g.league_id = l.id
                    WHERE g.status = %s
                    """,
                    'live'
                )
                if not live_game_leagues:
                    logger.debug("No leagues with live games found.")
                    await asyncio.sleep(120)
                    continue

                poll_tasks = []
                for league in live_game_leagues:
                    if hasattr(self.api, 'get_live_fixtures'):
                        poll_tasks.append(self.api.get_live_fixtures(league['sport'], str(league['league_id'])))
                    else:
                        poll_tasks.append(self._make_request(league['sport'], "fixtures", {"live": "all", "league": str(league['league_id'])}))

                results = await asyncio.gather(*poll_tasks, return_exceptions=True)

                for idx, result in enumerate(results):
                    league_id = live_game_leagues[idx]['league_id']
                    sport = live_game_leagues[idx]['sport']
                    if isinstance(result, Exception):
                        logger.error(f"Error polling league {league_id} (Sport: {sport}): {result}")
                    elif isinstance(result, dict) and 'response' in result:
                        await self._process_live_game_updates(league_id, result.get('response', []), sport)
                    elif isinstance(result, list):
                        await self._process_live_game_updates(league_id, result, sport)
                    else:
                        logger.warning(f"Unexpected result type polling league {league_id}: {type(result)}")

                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("Game polling loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error in game polling loop: {e}")
                await asyncio.sleep(120)

    async def _process_live_game_updates(self, league_id: int, api_games: List[Dict], sport: str):
        """Process updates for live games."""
        logger.debug(f"Processing {len(api_games)} live updates for league {league_id}...")
        if not api_games:
            return
        try:
            db_games_list = await self.db.fetch_all(
                """
                SELECT id, status, score, updated_at
                FROM games
                WHERE league_id = %s AND status = %s
                """,
                league_id, 'live'
            )
            db_games_map = {game['id']: game for game in db_games_list}
            games_to_update = []

            for api_game_entry in api_games:
                fixture = api_game_entry.get('fixture', {})
                api_game_id = fixture.get('id')
                if not api_game_id:
                    continue
                api_status = fixture.get('status', {}).get('short', 'UNK')
                api_score_obj = {
                    'home': api_game_entry.get('goals', {}).get('home'),
                    'away': api_game_entry.get('goals', {}).get('away')
                }
                api_score_str = json.dumps(api_score_obj)
                api_updated_at = datetime.now(timezone.utc)
                db_game = db_games_map.get(api_game_id)

                if db_game:
                    db_score_str = json.dumps(db_game.get('score', {}))
                    if db_game.get('status') != api_status or db_score_str != api_score_str:
                        logger.info(
                            f"Change detected for live game {api_game_id}: "
                            f"Status '{db_game.get('status')}'->'{api_status}', "
                            f"Score '{db_score_str}'->'{api_score_str}'"
                        )
                        games_to_update.append({
                            'id': api_game_id,
                            'status': api_status,
                            'score': api_score_str,
                            'updated_at': api_updated_at
                        })
                else:
                    logger.warning(f"Live game {api_game_id} from API not found in DB as 'live'. Status: {api_status}")

            if games_to_update:
                update_query = """
                    UPDATE games
                    SET status = %s, score = %s, updated_at = %s
                    WHERE id = %s
                """
                updated_count = 0
                for game_upd in games_to_update:
                    rows_affected = await self.db.execute(
                        update_query,
                        game_upd['status'], game_upd['score'], game_upd['updated_at'], game_upd['id']
                    )
                    if rows_affected is not None and rows_affected > 0:
                        updated_count += 1
                    else:
                        logger.warning(f"Failed to update game {game_upd['id']} during live update processing.")
                logger.info(f"Updated {updated_count}/{len(games_to_update)} live games in DB for league {league_id}.")
        except Exception as e:
            logger.exception(f"Error processing live game updates for league {league_id}: {e}")

    async def _notify_game_updates(self, game_data: Dict) -> None:
        """Notify about game updates (placeholder)."""
        logger.debug(f"Placeholder: Notifying about update for game {game_data.get('id')}")
        pass

    def _create_game_embed(self, game: Dict) -> discord.Embed:
        """Create a Discord embed for a game."""
        home_team = game.get('home_team_name', 'Home')
        away_team = game.get('away_team_name', 'Away')
        league = game.get('league_name', game.get('league_id', 'N/A'))
        status = game.get('status', 'N/A')
        score_data = game.get('score', {})
        if isinstance(score_data, str):
            try:
                score_data = json.loads(score_data)
            except json.JSONDecodeError:
                score_data = {}
        home_score = score_data.get('home', '?')
        away_score = score_data.get('away', '?')
        game_time_info = game.get('fixture', {}).get('status', {}).get('elapsed')

        embed = discord.Embed(
            title=f"{home_team} vs {away_team}",
            description=f"League: {league}",
            color=discord.Color.green() if 'live' in status.lower() or status == 'IN' else discord.Color.greyple()
        )
        embed.add_field(name="Score", value=f"{home_score} - {away_score}", inline=True)
        if game_time_info:
            embed.add_field(name="Time", value=str(game_time_info), inline=True)
        embed.add_field(name="Status", value=status.upper(), inline=True)
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    async def get_game(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get a single game by its ID."""
        try:
            return await self.db.fetch_one("SELECT * FROM games WHERE id = %s", game_id)
        except Exception as e:
            logger.exception(f"Error getting game {game_id}: {e}")
            return None

    async def get_league_games(
        self,
        guild_id: Optional[int],
        league: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get games for a specific league."""
        try:
            league_id_int = None
            try:
                league_id_int = int(league)
            except ValueError:
                pass

            filters = []
            params: List[Any] = []

            base_query = """
                SELECT g.*, l.name as league_name
                FROM games g
                LEFT JOIN leagues l ON g.league_id = l.id
                WHERE
            """

            if league_id_int:
                filters.append("g.league_id = %s")
                params.append(league_id_int)
            else:
                filters.append("l.name LIKE %s")
                params.append(f"%{league}%")

            if status:
                filters.append("g.status = %s")
                params.append(status)

            query = base_query + " AND ".join(filters)
            query += " ORDER BY g.start_time DESC NULLS LAST LIMIT %s"
            params.append(limit)

            return await self.db.fetch_all(query, *params)
        except Exception as e:
            logger.exception(f"Error getting league games for league '{league}': {e}")
            return []

    async def get_upcoming_games(
        self,
        guild_id: Optional[int],
        hours: int = 24,
        limit: int = 20
    ) -> List[Dict]:
        """Get upcoming games within a specified time frame."""
        try:
            now_utc = datetime.now(timezone.utc)
            future_utc = now_utc + timedelta(hours=hours)
            query = """
                SELECT *
                FROM games
                WHERE status = %s AND start_time BETWEEN %s AND %s
            """
            params: List[Any] = ['scheduled', now_utc, future_utc]

            query += " ORDER BY start_time ASC LIMIT %s"
            params.append(limit)

            return await self.db.fetch_all(query, *params)
        except Exception as e:
            logger.exception(f"Error getting upcoming games: {e}")
            return []

    async def get_live_games(self, guild_id: Optional[int], limit: int = 20) -> List[Dict]:
        """Get currently live games."""
        try:
            query = "SELECT * FROM games WHERE status = %s"
            params: List[Any] = ['live']

            query += " ORDER BY start_time DESC LIMIT %s"
            params.append(limit)

            return await self.db.fetch_all(query, *params)
        except Exception as e:
            logger.exception(f"Error getting live games: {e}")
            return []

    async |def update_game_status(
        self,
        guild_id: Optional[int],
        game_id: int,
        status: str,
        score: Optional[str] = None
    ) -> Optional[Dict]:
        """Update the status and score of a game."""
        try:
            update_query = """
                UPDATE games
                SET status = %s, score = %s, updated_at = %s
                WHERE id = %s
            """
            params: List[Any] = [status, score, datetime.now(timezone.utc), game_id]

            update_status = await self.db.execute(update_query, *params)

            if update_status is not None and update_status > 0:
                logger.info(f"Updated status for game {game_id} to {status}")
                return await self.get_game(game_id)
            else:
                logger.warning(f"Game {game_id} status update failed (rows affected: {update_status}).")
                return None
        except Exception as e:
            logger.exception(f"Error updating game status for game {game_id}: {e}")
            raise GameServiceError(f"Failed to update game status: {str(e)}")

    async def add_game_event(
        self,
        guild_id: Optional[int],
        game_id: int,
        event_type: str,
        details: str
    ) -> Optional[Dict]:
        """Add an event for a game."""
        try:
            insert_query = """
                INSERT INTO game_events (guild_id, game_id, event_type, details, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """
            last_id = await self.db.execute(
                insert_query,
                guild_id, game_id, event_type, details, datetime.now(timezone.utc)
            )
            if last_id:
                logger.info(f"Added event '{event_type}' for game {game_id}")
                return await self.db.fetch_one("SELECT * FROM game_events WHERE event_id = %s", last_id)
            else:
                logger.error(f"Failed to add event '{event_type}' for game {game_id} (no last ID returned).")
                return None
        except Exception as e:
            logger.exception(f"Error adding game event for game {game_id}: {e}")
            raise GameServiceError(f"Failed to add game event: {str(e)}")

    async def get_game_events(
        self,
        guild_id: Optional[int],
        game_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Get events for a specific game."""
        try:
            query = "SELECT * FROM game_events WHERE game_id = %s"
            params: List[Any] = [game_id]

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            return await self.db.fetch_all(query, *params)
        except Exception as e:
            logger.exception(f"Error getting game events for game {game_id}: {e}")
            return []

    async def _make_request(self, sport: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make an API request to the sports API."""
        if not API_ENABLED:
            raise GameServiceError("API support is not enabled.")
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        if sport not in self.api_hosts or not self.api_hosts[sport]:
            raise GameServiceError(f"Unsupported sport: {sport}")
        base_url = self.api_hosts[sport]
        if not API_KEY:
            raise ConfigurationError("API_KEY is not configured.")
        headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": base_url.split('//')[1]}
        full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        for attempt in range(API_RETRY_ATTEMPTS):
            try:
                logger.debug(f"API Request (Attempt {attempt+1}/{API_RETRY_ATTEMPTS}): GET {full_url} PARAMS: {params}")
                async with self.session.get(full_url, params=params, headers=headers, timeout=API_TIMEOUT) as response:
                    logger.debug(f"API Response Status: {response.status} for {full_url}")
                    if 200 <= response.status < 300:
                        return await response.json()
                    elif response.status == 404:
                        raise LeagueNotFoundError(f"API resource not found: {endpoint}")
                    elif response.status == 429:
                        retry_delay = API_RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"API rate limit hit. Retrying in {retry_delay:.2f}s...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        error_text = await response.text()
                        logger.error(f"API request failed: Status {response.status}, URL: {full_url}, Response: {error_text[:200]}")
                        response.raise_for_status()
            except asyncio.TimeoutError:
                logger.warning(f"API request timed out: {full_url}. Attempt {attempt+1}")
                await asyncio.sleep(API_RETRY_DELAY * (2 ** attempt))
            except aiohttp.ClientError as ce:
                logger.error(f"API client error: {ce}. Attempt {attempt+1}")
                await asyncio.sleep(API_RETRY_DELAY * (2 ** attempt))
            except json.JSONDecodeError as jde:
                logger.error(f"Failed to decode JSON response from {full_url}: {jde}")
                raise GameDataError("Invalid JSON received.")
            if attempt == API_RETRY_ATTEMPTS - 1:
                raise APIError(f"API request failed after {API_RETRY_ATTEMPTS} attempts: {full_url}")
        raise APIError(f"API request failed unexpectedly after retries: {full_url}")

    async def _upsert_games_from_api(self, api_games: List[Dict], sport: str):
        """Upsert games from API response into the database."""
        processed_count = 0
        upsert_query = """
            INSERT INTO games (
                id, league_id, home_team_id, away_team_id, home_team_name,
                away_team_name, home_team_logo, away_team_logo, start_time,
                status, score, venue, referee, sport, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                league_id=VALUES(league_id), home_team_id=VALUES(home_team_id),
                away_team_id=VALUES(away_team_id), home_team_name=VALUES(home_team_name),
                away_team_name=VALUES(away_team_name), start_time=VALUES(start_time),
                status=VALUES(status), score=VALUES(score), venue=VALUES(venue),
                referee=VALUES(referee), sport=VALUES(sport), updated_at=VALUES(updated_at),
                home_team_logo=VALUES(home_team_logo), away_team_logo=VALUES(away_team_logo)
        """

        for game_entry in api_games:
            fixture = game_entry.get('fixture', {})
            league_data = game_entry.get('league', {})
            teams_data = game_entry.get('teams', {})
            goals_data = game_entry.get('goals', {})
            score_full = game_entry.get('score', {})
            if not fixture.get('id'):
                continue
            game_timestamp_str = fixture.get('date')
            game_start_time = None
            if game_timestamp_str:
                try:
                    game_start_time = datetime.fromisoformat(game_timestamp_str.replace('Z', '+00:00')).astimezone(timezone.utc)
                except ValueError:
                    pass
            score_obj = {
                'home': goals_data.get('home'),
                'away': goals_data.get('away'),
                'halftime': score_full.get('halftime'),
                'fulltime': score_full.get('fulltime'),
                'extratime': score_full.get('extratime'),
                'penalty': score_full.get('penalty')
            }
            score_json = json.dumps({k: v for k, v in score_obj.items() if v is not None}) or None

            try:
                await self.db.execute(
                    upsert_query,
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
        logger.info(f"Upserted {processed_count}/{len(api_games)} games from API response for sport {sport}.")

    async def get_games(self, sport: str, league_id: str, date: Optional[datetime] = None) -> List[Dict]:
        """Get games for a specific league and date."""
        try:
            date_str = date.strftime("%Y-%m-%d") if date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
            cache_key = f"games:{sport}:{league_id}:{date_str}"
            cached_games = await self.cache.get(cache_key)
            if cached_games and isinstance(cached_games, list):
                return cached_games
            params = {"league": league_id, "date": date_str, "season": str(datetime.now(timezone.utc).year)}
            response_data = await self._make_request(sport, "fixtures", params)
            games_list = response_data.get('response', [])
            await self.cache.set(cache_key, games_list, ttl=300)
            return games_list
        except Exception as e:
            logger.error(f"Error in get_games({sport}, {league_id}): {e}")
            return []

    async def get_game_details(self, sport: str, game_id: str) -> Optional[Dict]:
        """Get details for a specific game."""
        try:
            cache_key = f"game_detail:{sport}:{game_id}"
            cached_game = await self.cache.get(cache_key)
            if cached_game and isinstance(cached_game, dict):
                return cached_game
            params = {"id": game_id}
            response_data = await self._make_request(sport, "fixtures", params)
            game_details_list = response_data.get('response', [])
            if not game_details_list:
                return None
            game_detail = game_details_list[0]
            await self.cache.set(cache_key, game_detail, ttl=120)
            return game_detail
        except Exception as e:
            logger.error(f"Error in get_game_details({sport}, {game_id}): {e}")
            return None

    async def get_league_schedule(
        self,
        sport: str,
        league_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get the schedule for a league within a date range."""
        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            cache_key = f"schedule:{sport}:{league_id}:{start_str}_{end_str}"
            cached_schedule = await self.cache.get(cache_key)
            if cached_schedule and isinstance(cached_schedule, list):
                return cached_schedule
            params = {
                "league": league_id,
                "season": str(start_date.year),
                "from": start_str,
                "to": end_str
            }
            response_data = await self._make_request(sport, "fixtures", params)
            schedule_list = response_data.get('response', [])
            await self.cache.set(cache_key, schedule_list, ttl=3600)
            return schedule_list
        except Exception as e:
            logger.error(f"Error in get_league_schedule({sport}, {league_id}): {e}")
            return []
