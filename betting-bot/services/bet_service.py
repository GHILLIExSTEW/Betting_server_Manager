import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import discord
from discord import Embed, Color, Button, ButtonStyle
from discord.ui import View, Select, Modal, TextInput
import sys
import os
import aiosqlite
import aiomysql
from ..config.database import DB_CONFIG

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db_manager import DatabaseManager
from data.cache_manager import CacheManager
from utils.errors import BetServiceError, ValidationError
from config.settings import MIN_UNITS, MAX_UNITS, DEFAULT_UNITS
from utils.image_generator import BetSlipGenerator
import json

logger = logging.getLogger(__name__)

class BetServiceError(Exception):
    """Base exception for bet service errors."""
    pass

class BetTypeSelect(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.bet_type = None

    @discord.ui.button(label="Straight", style=ButtonStyle.primary)
    async def straight(self, interaction: discord.Interaction, button: Button):
        self.bet_type = "Straight"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Parlay", style=ButtonStyle.primary)
    async def parlay(self, interaction: discord.Interaction, button: Button):
        self.bet_type = "Parlay"
        await interaction.response.defer()
        self.stop()

class LeagueSelect(Select):
    def __init__(self, leagues: List[str]):
        options = [
            discord.SelectOption(label=league, value=league)
            for league in leagues
        ]
        options.append(discord.SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select League", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_league = self.values[0]
        await interaction.response.defer()
        self.view.stop()

class GameSelect(Select):
    def __init__(self, games: List[Dict]):
        options = [
            discord.SelectOption(
                label=f"{game['home_team']} vs {game['away_team']}",
                value=str(game['game_id'])
            )
            for game in games
        ]
        options.append(discord.SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select Game", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_game = self.values[0]
        await interaction.response.defer()
        self.view.stop()

class OtherGameModal(Modal, title="Enter Game Details"):
    team = TextInput(label="Team", placeholder="Enter team name")
    opponent = TextInput(label="Opponent", placeholder="Enter opponent name")
    game_time = TextInput(label="Game Time", placeholder="Enter game time (e.g., 7:30 PM EST)")

    async def on_submit(self, interaction: discord.Interaction):
        self.view.game_details = {
            "team": self.team.value,
            "opponent": self.opponent.value,
            "game_time": self.game_time.value
        }
        await interaction.response.defer()
        self.view.stop()

class BetTypeSelectView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.bet_type = None

    @discord.ui.button(label="Game Bet", style=ButtonStyle.primary)
    async def game_bet(self, interaction: discord.Interaction, button: Button):
        self.bet_type = "Game"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Player Prop", style=ButtonStyle.primary)
    async def player_prop(self, interaction: discord.Interaction, button: Button):
        self.bet_type = "Player"
        await interaction.response.defer()
        self.stop()

class GameBetModal(Modal, title="Enter Bet Details"):
    line = TextInput(label="Line", placeholder="Enter line (e.g., -150)")
    odds = TextInput(label="Odds", placeholder="Enter odds (e.g., -150)")

    async def on_submit(self, interaction: discord.Interaction):
        self.view.bet_details = {
            "line": self.line.value,
            "odds": self.odds.value
        }
        await interaction.response.defer()
        self.view.stop()

class PlayerPropModal(Modal, title="Enter Player Prop Details"):
    player_name = TextInput(label="Player Name", placeholder="Enter player name")
    line = TextInput(label="Line", placeholder="Enter line (e.g., Over 2.5)")
    odds = TextInput(label="Odds", placeholder="Enter odds (e.g., -150)")

    async def on_submit(self, interaction: discord.Interaction):
        self.view.bet_details = {
            "player_name": self.player_name.value,
            "line": self.line.value,
            "odds": self.odds.value
        }
        await interaction.response.defer()
        self.view.stop()

class UnitsSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=str(i), value=str(i))
            for i in [1, 2, 3]
        ]
        super().__init__(placeholder="Select Units", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_units = int(self.values[0])
        await interaction.response.defer()
        self.view.stop()

class ChannelSelect(Select):
    def __init__(self, channels: List[discord.TextChannel]):
        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id)
            )
            for channel in channels
        ]
        super().__init__(placeholder="Select Channel", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_channel = int(self.values[0])
        await interaction.response.defer()
        self.view.stop()

class BetService:
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None
        self.logger = logging.getLogger(__name__)
        self._update_task = None

    async def start(self):
        """Initialize the bet service and start the update loop"""
        try:
            self.pool = await aiomysql.create_pool(**DB_CONFIG)
            self.logger.info("Database connection pool created successfully")
            self._update_task = asyncio.create_task(self._update_bets())
        except Exception as e:
            self.logger.error(f"Failed to initialize bet service: {e}")
            raise

    async def stop(self):
        """Stop the bet service and cleanup resources"""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def _update_bets(self):
        """Background task to update bet statuses"""
        while True:
            try:
                if not self.pool:
                    self.logger.error("Database pool not initialized")
                    await asyncio.sleep(60)
                    continue

                async with self.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        # Get all pending bets
                        await cursor.execute("""
                            SELECT * FROM bets 
                            WHERE status = 'pending' 
                            AND expiration_time <= NOW()
                        """)
                        bets = await cursor.fetchall()

                        for bet in bets:
                            try:
                                # Check if bet has expired
                                if bet['expiration_time'] <= datetime.now():
                                    # Update bet status to expired
                                    await cursor.execute("""
                                        UPDATE bets 
                                        SET status = 'expired' 
                                        WHERE id = %s
                                    """, (bet['id'],))
                                    await conn.commit()
                                    continue

                                # Check reactions for win/loss
                                # ... rest of the bet update logic ...

                            except Exception as e:
                                self.logger.error(f"Error processing bet {bet['id']}: {e}")
                                continue

            except Exception as e:
                self.logger.error(f"Error in bet update loop: {e}")
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(30)  # Check every 30 seconds

    async def create_bet(
        self,
        guild_id: int,
        user_id: int,
        game_id: Optional[str],
        bet_type: str,
        selection: str,
        units: int,
        odds: float,
        channel_id: int
    ) -> int:
        """Create a new bet."""
        try:
            # Validate bet
            if units < 1 or units > 3:
                raise ValidationError("Units must be between 1 and 3")
            
            # Create bet in database
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO bets (
                        guild_id, user_id, game_id, bet_type,
                        selection, units, odds, channel_id,
                        created_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'pending')
                """, (
                    guild_id, user_id, game_id, bet_type,
                    selection, units, odds, channel_id
                ))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating bet: {e}")
            raise BetServiceError(f"Failed to create bet: {str(e)}")

    async def get_user_bets(
        self,
        guild_id: int,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get bets for a user."""
        try:
            query = """
                SELECT * FROM bets
                WHERE guild_id = ? AND user_id = ?
            """
            params = [guild_id, user_id]

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user bets: {e}")
            raise BetServiceError(f"Failed to get user bets: {str(e)}")

    async def update_bet_status(
        self,
        bet_id: int,
        status: str,
        result: Optional[str] = None
    ) -> None:
        """Update bet status."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE bets
                    SET status = ?, result = ?, updated_at = datetime('now')
                    WHERE id = ?
                """, (status, result, bet_id))
                await db.commit()
        except Exception as e:
            logger.error(f"Error updating bet status: {e}")
            raise BetServiceError(f"Failed to update bet status: {str(e)}")

    async def is_user_authorized(self, guild_id: int, user_id: int) -> bool:
        """Check if user is authorized to place bets."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT user_id FROM cappers
                    WHERE guild_id = ? AND user_id = ?
                """, (guild_id, user_id)) as cursor:
                    return bool(await cursor.fetchone())
        except Exception as e:
            logger.error(f"Error checking user authorization: {e}")
            raise BetServiceError(f"Failed to check user authorization: {str(e)}")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction adds for bet outcomes."""
        try:
            # Check if this is a bet message we're monitoring
            if payload.message_id not in self.pending_reactions:
                return

            bet_info = self.pending_reactions[payload.message_id]
            if payload.user_id != bet_info['user_id']:
                return

            # Get the emoji
            emoji = str(payload.emoji)

            # Handle checkmark (won)
            if emoji in ['✅', '☑️', '✔️']:
                await self._handle_bet_won(payload.message_id, bet_info)
            # Handle cross (lost)
            elif emoji in ['❌', '✖️', '❎']:
                await self._handle_bet_lost(payload.message_id, bet_info)

        except Exception as e:
            logger.error(f"Error handling reaction add: {str(e)}")

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction removes for bet outcomes."""
        try:
            # Check if this is a bet message we're monitoring
            if payload.message_id not in self.pending_reactions:
                return

            bet_info = self.pending_reactions[payload.message_id]
            if payload.user_id != bet_info['user_id']:
                return

            # Get the emoji
            emoji = str(payload.emoji)

            # Handle checkmark removal
            if emoji in ['✅', '☑️', '✔️']:
                await self._handle_bet_unwon(payload.message_id, bet_info)
            # Handle cross removal
            elif emoji in ['❌', '✖️', '❎']:
                await self._handle_bet_unlost(payload.message_id, bet_info)

        except Exception as e:
            logger.error(f"Error handling reaction remove: {str(e)}")

    async def _handle_bet_won(self, message_id: int, bet_info: Dict) -> None:
        """Handle bet won."""
        try:
            # Get the original bet details
            bet = await self.db.fetch_one(
                """
                SELECT * FROM bets WHERE bet_id = ?
                """,
                bet_info['bet_id']
            )

            # Calculate result based on units and odds
            result = bet['units'] * bet['odds']

            # Update bet status to won
            await self.db.execute(
                """
                UPDATE bets
                SET status = 'won', 
                    result = 'won',
                    bet_won = 1,
                    result_value = ?
                WHERE bet_id = ?
                """,
                result,
                bet_info['bet_id']
            )

            # Record the result in unit_records
            await self.db.execute(
                """
                INSERT INTO unit_records (bet_id, units, odds, result_value, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                bet_info['bet_id'],
                bet['units'],
                bet['odds'],
                result,
                datetime.utcnow()
            )

            # Remove from pending reactions
            del self.pending_reactions[message_id]

            # Send won notification
            await self._send_bet_status_notification(bet_info, 'won', result)

        except Exception as e:
            logger.error(f"Error handling bet won: {str(e)}")

    async def _handle_bet_lost(self, message_id: int, bet_info: Dict) -> None:
        """Handle bet lost."""
        try:
            # Get the original bet details
            bet = await self.db.fetch_one(
                """
                SELECT * FROM bets WHERE bet_id = ?
                """,
                bet_info['bet_id']
            )

            # Calculate result based on units and odds
            result = bet['units'] * bet['odds']

            # Update bet status to lost
            await self.db.execute(
                """
                UPDATE bets
                SET status = 'lost', 
                    result = 'lost',
                    bet_loss = 1,
                    result_value = ?
                WHERE bet_id = ?
                """,
                -result,
                bet_info['bet_id']
            )

            # Record the result in unit_records
            await self.db.execute(
                """
                INSERT INTO unit_records (bet_id, units, odds, result_value, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                bet_info['bet_id'],
                bet['units'],
                bet['odds'],
                -result,
                datetime.utcnow()
            )

            # Remove from pending reactions
            del self.pending_reactions[message_id]

            # Send lost notification
            await self._send_bet_status_notification(bet_info, 'lost', -result)

        except Exception as e:
            logger.error(f"Error handling bet lost: {str(e)}")

    async def _handle_bet_unwon(self, message_id: int, bet_info: Dict) -> None:
        """Handle bet unwon."""
        try:
            # Update bet status back to pending and reset bet_won
            await self.db.execute(
                """
                UPDATE bets
                SET status = 'pending', 
                    result = NULL,
                    bet_won = 0
                WHERE bet_id = ?
                """,
                bet_info['bet_id']
            )

            # Remove the unit record for this bet
            await self.db.execute(
                """
                DELETE FROM unit_records
                WHERE bet_id = ?
                """,
                bet_info['bet_id']
            )

            # Send status update notification
            await self._send_bet_status_notification(bet_info, 'pending', 0)

        except Exception as e:
            logger.error(f"Error handling bet unwon: {str(e)}")

    async def _handle_bet_unlost(self, message_id: int, bet_info: Dict) -> None:
        """Handle bet unlost."""
        try:
            # Update bet status back to pending and reset bet_loss
            await self.db.execute(
                """
                UPDATE bets
                SET status = 'pending', 
                    result = NULL,
                    bet_loss = 0
                WHERE bet_id = ?
                """,
                bet_info['bet_id']
            )

            # Remove the unit record for this bet
            await self.db.execute(
                """
                DELETE FROM unit_records
                WHERE bet_id = ?
                """,
                bet_info['bet_id']
            )

            # Send status update notification
            await self._send_bet_status_notification(bet_info, 'pending', 0)

        except Exception as e:
            logger.error(f"Error handling bet unlost: {str(e)}")

    async def _send_bet_status_notification(self, bet_info: Dict, status: str, result: int) -> None:
        """Send notification about bet status change."""
        try:
            user = self.bot.get_user(bet_info['user_id'])
            if not user:
                return

            embed = Embed(
                title=f"Bet {status.title()}",
                color=Color.green() if status == 'won' else Color.red(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="Bet ID", value=f"{bet_info['bet_id']}", inline=True)
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="League", value=bet_info['league'], inline=True)
            embed.add_field(name="Type", value=bet_info['bet_type'], inline=True)
            embed.add_field(name="Selection", value=bet_info['selection'], inline=True)
            embed.add_field(name="Units", value=f"{bet_info['units']}", inline=True)
            embed.add_field(name="Odds", value=f"{bet_info['odds']}", inline=True)
            embed.add_field(name="Result", value=f"{result}", inline=True)
            embed.add_field(name="Status", value=status.title(), inline=True)

            # Get the channel where the bet was placed
            channel = self.bot.get_channel(bet_info['channel_id'])
            if channel:
                await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error sending bet status notification: {str(e)}")

    async def get_bet(self, guild_id: int, bet_id: int) -> Optional[Dict]:
        """Get details of a specific bet."""
        try:
            # Get from database
            bet = await self.db.fetch_one(
                """
                SELECT * FROM bets
                WHERE bet_id = ? AND guild_id = ?
                """,
                bet_id, guild_id
            )

            return bet
        except Exception as e:
            logger.error(f"Error getting bet: {str(e)}")
            return None

    async def get_guild_bets(
        self,
        guild_id: int,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get all bets for a guild."""
        try:
            query = """
                SELECT * FROM bets
                WHERE guild_id = ?
            """
            params = [guild_id]

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            return await self.db.fetch(query, *params)
        except Exception as e:
            logger.error(f"Error getting guild bets: {str(e)}")
            return []

    async def _view_pending_bets(self, interaction: discord.Interaction):
        """View user's pending bets"""
        try:
            bets = await self.db.fetch(
                """
                SELECT * FROM bets
                WHERE guild_id = $1 AND user_id = $2 AND status = 'pending'
                ORDER BY created_at DESC
                """,
                interaction.guild_id, interaction.user.id
            )
        except Exception as e:
            logger.error(f"Database error fetching pending bets: {e}")
            raise BetServiceError("Failed to fetch pending bets")

        if not bets:
            await interaction.response.send_message(
                "You have no pending bets.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Your Pending Bets",
            color=discord.Color.blue()
        )

        for bet in bets:
            details = json.loads(bet['bet_details'])
            embed.add_field(
                name=f"Bet #{bet['bet_serial']}",
                value=(
                    f"League: {details['league']}\n"
                    f"Type: {details['bet_type']}\n"
                    f"Selection: {details['selection']}\n"
                    f"Units: {details['units']:.1f}\n"
                    f"Placed: {details['timestamp']}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    async def _get_user_balance(self, guild_id: int, user_id: int) -> float:
        """Get user's current balance"""
        try:
            result = await self.db.fetch_one(
                """
                SELECT units_balance FROM guild_users
                WHERE guild_id = $1 AND user_id = $2
                """,
                guild_id, user_id
            )
            return result['units_balance'] if result else 0.0
        except Exception as e:
            logger.error(f"Database error getting user balance: {e}")
            raise BetServiceError("Failed to get user balance")

    async def _update_user_balance(self, guild_id: int, user_id: int, amount: float):
        """Update user's balance"""
        try:
            await self.db.execute(
                """
                UPDATE guild_users
                SET units_balance = units_balance + $1
                WHERE guild_id = $2 AND user_id = $3
                """,
                amount, guild_id, user_id
            )
        except Exception as e:
            logger.error(f"Database error updating user balance: {e}")
            raise BetServiceError("Failed to update user balance")

    async def resolve_bet(self, bet_serial: int, result: str):
        """Resolve a bet with the given result"""
        try:
            # Get bet details
            bet = await self.db.fetch_one(
                """
                SELECT * FROM bets
                WHERE bet_serial = $1
                """,
                bet_serial
            )
            if not bet:
                raise BetServiceError(f"Bet #{bet_serial} not found")

            # Update bet status
            await self.update_bet_status(bet['bet_id'], 'resolved', result)

            # Calculate winnings
            details = json.loads(bet['bet_details'])
            units = details['units']
            winnings = units if result == 'won' else -units

            # Update user balance
            await self._update_user_balance(bet['guild_id'], bet['user_id'], winnings)

            # Update lifetime units
            await self.db.execute(
                """
                UPDATE guild_users
                SET lifetime_units = lifetime_units + $1
                WHERE guild_id = $2 AND user_id = $3
                """,
                winnings, bet['guild_id'], bet['user_id']
            )

            # Update monthly record
            now = datetime.utcnow()
            await self.db.execute(
                """
                INSERT INTO unit_records (guild_id, user_id, year, month, units)
                VALUES ($1, $2, $3, $4, $5)
                ON DUPLICATE KEY UPDATE units = units + $5
                """,
                bet['guild_id'],
                bet['user_id'],
                now.year,
                now.month,
                winnings
            )

            logger.info(f"Bet #{bet_serial} resolved as {result}")
            return True
        except Exception as e:
            logger.error(f"Error resolving bet #{bet_serial}: {e}")
            raise BetServiceError(f"Failed to resolve bet: {e}")

    async def create_bet(self, user_id: int, amount: float, prediction: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO bets (user_id, amount, prediction, created_at) VALUES (?, ?, ?, datetime("now"))',
                (user_id, amount, prediction)
            )
            await db.commit()
            return cursor.lastrowid 