import discord
from discord import app_commands
from typing import Dict, List, Optional
import logging
from datetime import datetime
import json
import aiohttp
import asyncio
from bot.data.db_manager import db_manager
from bot.data.cache_manager import cache_manager
from bot.utils.errors import GameServiceError, APIError
from bot.config.settings import (
    API_KEY,
    API_BASE_URL,
    GAME_CACHE_TTL,
    LEAGUE_CACHE_TTL,
    TEAM_CACHE_TTL
)

logger = logging.getLogger(__name__)

class GameService:
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.update_task: Optional[asyncio.Task] = None
        self.active_games: Dict[str, Dict] = {}

    async def start(self):
        """Initialize the game service"""
        try:
            self.session = aiohttp.ClientSession()
            await self._setup_commands()
            self.update_task = asyncio.create_task(self._update_games_loop())
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
        self.active_games.clear()

    async def _setup_commands(self):
        """Register game-related commands"""
        @self.command_tree.command(
            name="games",
            description="View active games"
        )
        @app_commands.describe(
            league="Filter by league (optional)"
        )
        async def games(interaction: discord.Interaction, league: Optional[str] = None):
            try:
                await self._view_games(interaction, league)
            except Exception as e:
                logger.error(f"Error in games command: {e}")
                await interaction.response.send_message(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

        @self.command_tree.command(
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

    async def _update_games_loop(self):
        """Background task to update game data"""
        while True:
            try:
                await self._update_games()
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error(f"Error in game update loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _update_games(self):
        """Fetch and update game data"""
        try:
            # Get active games from API
            async with self.session.get(
                f"{API_BASE_URL}/games/active",
                headers={"Authorization": f"Bearer {API_KEY}"}
            ) as response:
                if response.status != 200:
                    raise APIError(f"API returned status {response.status}")
                games = await response.json()

            # Update database and cache
            for game in games:
                game_id = game['id']
                self.active_games[game_id] = game

                # Update database
                await db_manager.execute(
                    """
                    INSERT INTO games (game_id, league, home_team, away_team, start_time, status, score, odds)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        status = VALUES(status),
                        score = VALUES(score),
                        odds = VALUES(odds),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        game_id,
                        game['league'],
                        game['home_team'],
                        game['away_team'],
                        game['start_time'],
                        game['status'],
                        json.dumps(game.get('score', {})),
                        json.dumps(game.get('odds', {}))
                    )
                )

                # Update cache
                await cache_manager.set(
                    f"game:{game_id}",
                    game,
                    ttl=GAME_CACHE_TTL
                )

            logger.info(f"Updated {len(games)} active games")
        except Exception as e:
            logger.error(f"Error updating games: {e}")
            raise GameServiceError("Failed to update games")

    async def _view_games(self, interaction: discord.Interaction, league: Optional[str] = None):
        """View active games"""
        try:
            if league:
                games = await db_manager.fetch(
                    """
                    SELECT * FROM games
                    WHERE league = %s AND status = 'active'
                    ORDER BY start_time
                    """,
                    (league,)
                )
            else:
                games = await db_manager.fetch(
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
            cached_game = await cache_manager.get_json(f"game:{game_id}")
            if cached_game:
                game = cached_game
            else:
                # Get from database
                game = await db_manager.fetch_one(
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

    async def get_game(self, game_id: str) -> Optional[Dict]:
        """Get game data by ID"""
        try:
            # Try cache first
            cached_game = await cache_manager.get_json(f"game:{game_id}")
            if cached_game:
                return cached_game

            # Get from database
            game = await db_manager.fetch_one(
                """
                SELECT * FROM games
                WHERE game_id = %s
                """,
                (game_id,)
            )
            if game:
                # Update cache
                await cache_manager.set(
                    f"game:{game_id}",
                    game,
                    ttl=GAME_CACHE_TTL
                )
            return game
        except Exception as e:
            logger.error(f"Error getting game {game_id}: {e}")
            return None 