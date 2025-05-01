# betting-bot/services/user_service.py

"""Service for managing user data and balances."""

import discord
from typing import Dict, Optional, List, Any
import logging
from datetime import datetime, timezone

try:
    from ..data.cache_manager import CacheManager
    from ..utils.errors import UserServiceError, InsufficientUnitsError
    from ..config.settings import USER_CACHE_TTL
except ImportError:
    from data.cache_manager import CacheManager
    from utils.errors import UserServiceError, InsufficientUnitsError
    USER_CACHE_TTL = 3600  # Default TTL (1 hour)

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.cache = CacheManager()

    async def start(self):
        """Initialize async components if needed."""
        try:
            logger.info("User service started successfully.")
        except Exception as e:
            logger.exception(f"Failed to start user service: {e}")
            raise UserServiceError("Failed to start user service")

    async def stop(self):
        """Clean up resources."""
        logger.info("Stopping UserService...")
        logger.info("User service stopped.")

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data by ID (from cache or DB)."""
        cache_key = f"user:{user_id}"
        try:
            cached_user = self.cache.get(cache_key)
            if cached_user:
                logger.debug(f"Cache hit for user {user_id}")
                if 'balance' in cached_user and cached_user['balance'] is not None:
                    cached_user['balance'] = float(cached_user['balance'])
                return cached_user

            logger.debug(f"Cache miss for user {user_id}. Fetching from DB.")
            user_data = await self.db.fetch_one(
                """
                SELECT user_id, username, balance, created_at
                FROM users
                WHERE user_id = %s
                """,
                user_id
            )

            if user_data:
                if 'balance' in user_data and user_data['balance'] is not None:
                    user_data['balance'] = float(user_data['balance'])
                self.cache.set(cache_key, user_data, ttl=USER_CACHE_TTL)
                return user_data
            else:
                return None
        except Exception as e:
            logger.exception(f"Error getting user {user_id}: {e}")
            return None

    async def get_or_create_user(self, user_id: int, username: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a user, creating them in the DB if they don't exist."""
        user = await self.get_user(user_id)
        if user:
            if username and user.get('username') != username:
                await self.db.execute(
                    """
                    UPDATE users
                    SET username = %s
                    WHERE user_id = %s
                    """,
                    username, user_id
                )
                user['username'] = username
                self.cache.delete(f"user:{user_id}")
            return user
        else:
            logger.info(f"User {user_id} not found, attempting to create.")
            if not username:
                try:
                    discord_user = await self.bot.fetch_user(user_id)
                    username = discord_user.name if discord_user else f"User_{user_id}"
                except (discord.NotFound, Exception) as fetch_err:
                    username = f"User_{user_id}"
                    logger.warning(f"Could not fetch username for new user {user_id}: {fetch_err}")

            try:
                default_balance = 0.0
                await self.db.execute(
                    """
                    INSERT IGNORE INTO users (user_id, username, balance, created_at)
                    VALUES (%s, %s, %s, UTC_TIMESTAMP())
                    """,
                    user_id, username, default_balance
                )
                return await self.get_user(user_id)
            except Exception as e:
                logger.exception(f"Error creating user {user_id}: {e}")
                raise UserServiceError("Failed to create user")

    async def update_user_balance(
        self,
        user_id: int,
        amount: float,
        transaction_type: str
    ) -> Optional[Dict[str, Any]]:
        """Update user balance and record transaction using shared db_manager."""
        try:
            user = await self.get_or_create_user(user_id)
            if not user:
                raise UserServiceError(f"User {user_id} could not be fetched or created.")

            current_balance = float(user.get('balance', 0.0) or 0.0)
            new_balance = current_balance + amount

            if amount < 0 and new_balance < 0:
                raise InsufficientUnitsError(
                    f"User {user_id} has {current_balance:.2f}, cannot subtract {-amount:.2f}"
                )

            updated_rows = await self.db.execute(
                """
                UPDATE users
                SET balance = %s
                WHERE user_id = %s
                """,
                new_balance, user_id
            )

            if updated_rows is None or updated_rows == 0:
                logger.error(
                    f"Failed to update balance for user {user_id}. "
                    f"User might not exist or balance unchanged. Rows affected: {updated_rows}"
                )
                raise UserServiceError("Failed to update user balance.")

            logger.info(
                f"Updated balance for user {user_id}. "
                f"New balance: {new_balance:.2f}. Amount change: {amount:+.2f} ({transaction_type})"
            )

            user['balance'] = new_balance
            cache_key = f"user:{user_id}"
            self.cache.set(cache_key, user, ttl=USER_CACHE_TTL)

            return user

        except InsufficientUnitsError as e:
            logger.warning(f"Balance update failed for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error updating balance for user {user_id}: {e}")
            raise UserServiceError("An internal error occurred while updating balance.")

    async def get_user_balance(self, user_id: int) -> float:
        """Get a user's current balance directly."""
        try:
            user = await self.get_user(user_id)
            return float(user.get('balance', 0.0) or 0.0) if user else 0.0
        except Exception as e:
            logger.exception(f"Error getting balance for user {user_id}: {e}")
            return 0.0

    async def get_leaderboard_data(
        self,
        timeframe: str = 'weekly',
        limit: int = 10,
        guild_id: Optional[int] = None
    ) -> List[Dict]:
        """Get leaderboard data (profit/loss) based on transactions."""
        logger.warning(
            "get_leaderboard_data relies on a 'transactions' table, "
            "which might not exist in the defined schema."
        )

        try:
            now = datetime.now(timezone.utc)
            start_date = None
            if timeframe == 'daily':
                start_date = now - timedelta(days=1)
            elif timeframe == 'weekly':
                start_date = now - timedelta(weeks=1)
            elif timeframe == 'monthly':
                start_date = now - timedelta(days=30)
            elif timeframe == 'yearly':
                start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)

            query = """
                SELECT
                    t.user_id,
                    COALESCE(u.username, 'Unknown User') as username,
                    SUM(t.amount) as total_profit_loss
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE 1=1
            """
            params: List[Any] = []

            if start_date:
                query += " AND t.created_at >= %s"
                params.append(start_date)

            query += " GROUP BY t.user_id, u.username ORDER BY total_profit_loss DESC LIMIT %s"
            params.append(limit)

            return await self.db.fetch_all(query, *params)

        except Exception as e:
            logger.exception(f"Error getting leaderboard data: {e}")
            return []
