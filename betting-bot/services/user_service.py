import discord
from discord import app_commands
from typing import Dict, Optional, List, Any
import logging
from datetime import datetime, timedelta
from data.db_manager import DatabaseManager
from data.cache_manager import CacheManager
from bot.utils.errors import UserServiceError
from bot.config.settings import USER_CACHE_TTL
import aiosqlite

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, bot, db_path: str = 'bot/data/betting.db'):
        self.bot = bot
        self.active_users: Dict[int, Dict] = {}
        self.db_path = db_path

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
        # Commands have been moved to individual command files
        pass

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data by ID"""
        try:
            # Try cache first
            cached_user = await CacheManager.get_json(f"user:{user_id}")
            if cached_user:
                return cached_user

            # Get from database
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT * FROM users WHERE id = ?', (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        # Update cache
                        await CacheManager.set(
                            f"user:{user_id}",
                            dict(row),
                            ttl=USER_CACHE_TTL
                        )
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def create_user(self, user_id: int, username: str) -> int:
        """Create a new user"""
        try:
            # Check if user exists
            existing_user = await self.get_user(user_id)
            if existing_user:
                return existing_user['id']

            # Create new user
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'INSERT INTO users (id, username, created_at) VALUES (?, ?, datetime("now"))',
                    (user_id, username)
                )
                await db.commit()
                return cursor.lastrowid
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
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE users SET balance = ? WHERE id = ?',
                    (new_balance, user_id)
                )
                await db.commit()

            # Update cache
            user['balance'] = new_balance
            await CacheManager.set(
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
            async with aiosqlite.connect(self.db_path) as db:
                leaderboard = await db.execute(
                    'SELECT username, SUM(amount) as total_profit FROM transactions WHERE type = ? AND created_at >= ? GROUP BY user_id, username ORDER BY total_profit DESC LIMIT 10',
                    ('win', start_date)
                )
                rows = await leaderboard.fetchall()

            if not rows:
                await interaction.response.send_message(
                    "No betting activity found for this timeframe.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"{timeframe.capitalize()} Leaderboard",
                color=discord.Color.gold()
            )

            for i, entry in enumerate(rows, 1):
                embed.add_field(
                    name=f"{i}. {entry['username']}",
                    value=f"${entry['total_profit']:.2f}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error viewing leaderboard: {e}")
            raise UserServiceError("Failed to view leaderboard") 