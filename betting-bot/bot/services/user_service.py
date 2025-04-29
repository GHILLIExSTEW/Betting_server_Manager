import discord
from discord import app_commands
from typing import Dict, Optional
import logging
from datetime import datetime
from bot.data.db_manager import db_manager
from bot.data.cache_manager import cache_manager
from bot.utils.errors import UserServiceError
from bot.config.settings import USER_CACHE_TTL

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, bot):
        self.bot = bot
        self.active_users: Dict[int, Dict] = {}

    async def start(self):
        """Initialize the user service"""
        try:
            await self._setup_commands()
            logger.info("User service started successfully")
        except Exception as e:
            logger.error(f"Failed to start user service: {e}")
            raise UserServiceError("Failed to start user service")

    async def stop(self):
        """Clean up resources"""
        self.active_users.clear()

    async def _setup_commands(self):
        """Register user-related commands"""
        @self.command_tree.command(
            name="balance",
            description="View your betting balance"
        )
        async def balance(interaction: discord.Interaction):
            try:
                await self._view_balance(interaction)
            except Exception as e:
                logger.error(f"Error in balance command: {e}")
                await interaction.response.send_message(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

        @self.command_tree.command(
            name="leaderboard",
            description="View the betting leaderboard"
        )
        @app_commands.describe(
            timeframe="Timeframe for leaderboard (daily/weekly/monthly)"
        )
        async def leaderboard(
            interaction: discord.Interaction,
            timeframe: str = "weekly"
        ):
            try:
                await self._view_leaderboard(interaction, timeframe)
            except Exception as e:
                logger.error(f"Error in leaderboard command: {e}")
                await interaction.response.send_message(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data by ID"""
        try:
            # Try cache first
            cached_user = await cache_manager.get_json(f"user:{user_id}")
            if cached_user:
                return cached_user

            # Get from database
            user = await db_manager.fetch_one(
                """
                SELECT * FROM users
                WHERE user_id = %s
                """,
                (user_id,)
            )
            if user:
                # Update cache
                await cache_manager.set(
                    f"user:{user_id}",
                    user,
                    ttl=USER_CACHE_TTL
                )
            return user
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def create_user(self, user_id: int, username: str) -> Dict:
        """Create a new user"""
        try:
            # Check if user exists
            existing_user = await self.get_user(user_id)
            if existing_user:
                return existing_user

            # Create new user
            await db_manager.execute(
                """
                INSERT INTO users (user_id, username, balance, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, username, 1000.0, datetime.utcnow())
            )

            # Get the created user
            user = await self.get_user(user_id)
            if not user:
                raise UserServiceError("Failed to create user")

            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            raise UserServiceError("Failed to create user")

    async def update_balance(
        self,
        user_id: int,
        amount: float,
        transaction_type: str
    ) -> Dict:
        """Update user balance"""
        try:
            # Get current user
            user = await self.get_user(user_id)
            if not user:
                raise UserServiceError(f"User {user_id} not found")

            # Calculate new balance
            new_balance = user['balance'] + amount
            if new_balance < 0:
                raise UserServiceError("Insufficient balance")

            # Update database
            await db_manager.execute(
                """
                UPDATE users
                SET balance = %s
                WHERE user_id = %s
                """,
                (new_balance, user_id)
            )

            # Record transaction
            await db_manager.execute(
                """
                INSERT INTO transactions (
                    user_id, amount, type, created_at
                ) VALUES (%s, %s, %s, %s)
                """,
                (user_id, amount, transaction_type, datetime.utcnow())
            )

            # Update cache
            user['balance'] = new_balance
            await cache_manager.set(
                f"user:{user_id}",
                user,
                ttl=USER_CACHE_TTL
            )

            return user
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
            raise UserServiceError("Failed to update balance")

    async def _view_balance(self, interaction: discord.Interaction):
        """View user balance"""
        try:
            user = await self.get_user(interaction.user.id)
            if not user:
                user = await self.create_user(
                    interaction.user.id,
                    interaction.user.name
                )

            embed = discord.Embed(
                title="Your Balance",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Current Balance",
                value=f"${user['balance']:.2f}",
                inline=False
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error viewing balance: {e}")
            raise UserServiceError("Failed to view balance")

    async def _view_leaderboard(
        self,
        interaction: discord.Interaction,
        timeframe: str
    ):
        """View betting leaderboard"""
        try:
            # Validate timeframe
            valid_timeframes = ["daily", "weekly", "monthly"]
            if timeframe not in valid_timeframes:
                raise UserServiceError(
                    f"Invalid timeframe. Use one of: {', '.join(valid_timeframes)}"
                )

            # Calculate date range
            now = datetime.utcnow()
            if timeframe == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif timeframe == "weekly":
                start_date = now.replace(
                    day=now.day - now.weekday(),
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )
            else:  # monthly
                start_date = now.replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

            # Get leaderboard data
            leaderboard = await db_manager.fetch(
                """
                SELECT u.username, SUM(t.amount) as total_profit
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.created_at >= %s
                AND t.type = 'win'
                GROUP BY u.user_id, u.username
                ORDER BY total_profit DESC
                LIMIT 10
                """,
                (start_date,)
            )

            if not leaderboard:
                await interaction.response.send_message(
                    "No betting activity found for this timeframe.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"{timeframe.capitalize()} Leaderboard",
                color=discord.Color.gold()
            )

            for i, entry in enumerate(leaderboard, 1):
                embed.add_field(
                    name=f"{i}. {entry['username']}",
                    value=f"${entry['total_profit']:.2f}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error viewing leaderboard: {e}")
            raise UserServiceError("Failed to view leaderboard") 