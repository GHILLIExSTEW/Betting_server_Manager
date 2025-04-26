import discord
from discord import app_commands
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import json
from bot.data.db_manager import db_manager
from bot.data.cache_manager import cache_manager
from bot.utils.errors import BetServiceError, ValidationError
from bot.config.settings import MIN_UNITS, MAX_UNITS, DEFAULT_UNITS

logger = logging.getLogger(__name__)

class BetService:
    def __init__(self, bot, command_tree):
        self.bot = bot
        self.command_tree = command_tree
        self.pending_bets: Dict[int, Dict[int, List[Dict]]] = {}  # guild_id -> user_id -> bets

    async def start(self):
        """Initialize the bet service"""
        try:
            await self._setup_commands()
            logger.info("Bet service started successfully")
        except Exception as e:
            logger.error(f"Failed to start bet service: {e}")
            raise BetServiceError("Failed to start bet service")

    async def stop(self):
        """Clean up resources"""
        self.pending_bets.clear()

    async def _setup_commands(self):
        """Register betting commands"""
        @self.command_tree.command(
            name="bet",
            description="Place a new bet"
        )
        @app_commands.describe(
            league="The league to bet on",
            bet_type="Type of bet (spread, moneyline, total, etc.)",
            selection="Your selection",
            units="Amount of units to bet"
        )
        async def bet(
            interaction: discord.Interaction,
            league: str,
            bet_type: str,
            selection: str,
            units: float = DEFAULT_UNITS
        ):
            try:
                await self._place_bet(interaction, league, bet_type, selection, units)
            except Exception as e:
                logger.error(f"Error in bet command: {e}")
                await interaction.response.send_message(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

        @self.command_tree.command(
            name="pending",
            description="View your pending bets"
        )
        async def pending(interaction: discord.Interaction):
            try:
                await self._view_pending_bets(interaction)
            except Exception as e:
                logger.error(f"Error in pending command: {e}")
                await interaction.response.send_message(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

    async def _place_bet(
        self,
        interaction: discord.Interaction,
        league: str,
        bet_type: str,
        selection: str,
        units: float
    ):
        """Place a new bet"""
        # Validate input
        if units < MIN_UNITS or units > MAX_UNITS:
            raise ValidationError(f"Units must be between {MIN_UNITS} and {MAX_UNITS}")

        # Get user's current balance
        balance = await self._get_user_balance(interaction.guild_id, interaction.user.id)
        if balance < units:
            raise ValidationError(f"Insufficient balance. Current balance: {balance} units")

        # Create bet record
        bet_details = {
            "league": league,
            "bet_type": bet_type,
            "selection": selection,
            "units": units,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Store bet in database
        try:
            await db_manager.execute(
                """
                INSERT INTO bets (guild_id, user_id, league, bet_type, bet_details, units)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    interaction.guild_id,
                    interaction.user.id,
                    league,
                    bet_type,
                    json.dumps(bet_details),
                    units
                )
            )
        except Exception as e:
            logger.error(f"Database error placing bet: {e}")
            raise BetServiceError("Failed to place bet")

        # Update user balance
        await self._update_user_balance(interaction.guild_id, interaction.user.id, -units)

        # Send confirmation
        embed = discord.Embed(
            title="Bet Placed",
            description=f"Your bet has been placed successfully!",
            color=discord.Color.green()
        )
        embed.add_field(name="League", value=league, inline=True)
        embed.add_field(name="Type", value=bet_type, inline=True)
        embed.add_field(name="Selection", value=selection, inline=True)
        embed.add_field(name="Units", value=f"{units:.1f}", inline=True)
        embed.add_field(name="New Balance", value=f"{balance - units:.1f}", inline=True)

        await interaction.response.send_message(embed=embed)

    async def _view_pending_bets(self, interaction: discord.Interaction):
        """View user's pending bets"""
        try:
            bets = await db_manager.fetch(
                """
                SELECT * FROM bets
                WHERE guild_id = %s AND user_id = %s AND status = 'pending'
                ORDER BY created_at DESC
                """,
                (interaction.guild_id, interaction.user.id)
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
            result = await db_manager.fetch_one(
                """
                SELECT units_balance FROM guild_users
                WHERE guild_id = %s AND user_id = %s
                """,
                (guild_id, user_id)
            )
            return result['units_balance'] if result else 0.0
        except Exception as e:
            logger.error(f"Database error getting user balance: {e}")
            raise BetServiceError("Failed to get user balance")

    async def _update_user_balance(self, guild_id: int, user_id: int, amount: float):
        """Update user's balance"""
        try:
            await db_manager.execute(
                """
                UPDATE guild_users
                SET units_balance = units_balance + %s
                WHERE guild_id = %s AND user_id = %s
                """,
                (amount, guild_id, user_id)
            )
        except Exception as e:
            logger.error(f"Database error updating user balance: {e}")
            raise BetServiceError("Failed to update user balance")

    async def resolve_bet(self, bet_serial: int, result: str):
        """Resolve a bet with the given result"""
        try:
            # Get bet details
            bet = await db_manager.fetch_one(
                """
                SELECT * FROM bets
                WHERE bet_serial = %s
                """,
                (bet_serial,)
            )
            if not bet:
                raise BetServiceError(f"Bet #{bet_serial} not found")

            # Update bet status
            await db_manager.execute(
                """
                UPDATE bets
                SET status = %s, result = %s
                WHERE bet_serial = %s
                """,
                ('resolved', result, bet_serial)
            )

            # Calculate winnings
            details = json.loads(bet['bet_details'])
            units = details['units']
            winnings = units if result == 'won' else -units

            # Update user balance
            await self._update_user_balance(bet['guild_id'], bet['user_id'], winnings)

            # Update lifetime units
            await db_manager.execute(
                """
                UPDATE guild_users
                SET lifetime_units = lifetime_units + %s
                WHERE guild_id = %s AND user_id = %s
                """,
                (winnings, bet['guild_id'], bet['user_id'])
            )

            # Update monthly record
            now = datetime.utcnow()
            await db_manager.execute(
                """
                INSERT INTO unit_records (guild_id, user_id, year, month, units)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE units = units + %s
                """,
                (
                    bet['guild_id'],
                    bet['user_id'],
                    now.year,
                    now.month,
                    winnings,
                    winnings
                )
            )

            logger.info(f"Bet #{bet_serial} resolved as {result}")
            return True
        except Exception as e:
            logger.error(f"Error resolving bet #{bet_serial}: {e}")
            raise BetServiceError(f"Failed to resolve bet: {e}") 