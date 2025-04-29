# betting-bot/services/user_service.py

import discord
# from discord import app_commands # Not needed if commands handled elsewhere
from typing import Dict, Optional, List, Any
import logging
from datetime import datetime, timedelta, timezone # Add timezone

# Use relative imports
try:
    # from ..data.db_manager import DatabaseManager
    from ..data.cache_manager import CacheManager
    from ..utils.errors import UserServiceError
    from ..config.settings import USER_CACHE_TTL # Assuming this setting exists
except ImportError:
    # from data.db_manager import DatabaseManager
    from data.cache_manager import CacheManager
    from utils.errors import UserServiceError
    from config.settings import USER_CACHE_TTL

# Remove aiomysql imports if switching fully to db_manager
# import aiosqlite
# import aiomysql
# from betting_bot.config.database import DB_CONFIG # Remove this

logger = logging.getLogger(__name__)

class UserService:
    # Corrected __init__
    def __init__(self, bot, db_manager): # Accept bot and db_manager
        """Initializes the User Service.

        Args:
            bot: The discord bot instance.
            db_manager: The shared DatabaseManager instance.
        """
        self.bot = bot
        self.db = db_manager # Use shared db_manager instance
        self.cache = CacheManager() # Instantiate cache here, or pass if managed centrally
        # self.active_users: Dict[int, Dict] = {} # Removed, rely on DB/Cache
        # self.db_path = '...' # Removed
        # self.pool: Optional[aiomysql.Pool] = None # Removed

    async def start(self):
        """Initialize async components if needed (like cache connection)."""
        try:
            # Connect cache if it has an async connect method
            if hasattr(self.cache, 'connect'):
                await self.cache.connect()
            # No need to connect DB pool here if handled centrally
            # self.pool = await aiomysql.create_pool(**DB_CONFIG) # Removed
            logger.info("User service started successfully.")
        except Exception as e:
            logger.exception(f"Failed to start user service: {e}")
            # Clean up cache connection if start failed
            if hasattr(self.cache, 'close'):
                 await self.cache.close()
            raise UserServiceError("Failed to start user service")

    async def stop(self):
        """Clean up resources (like cache connection)."""
        # self.active_users.clear() # Removed
        # Close cache connection if managed here
        if hasattr(self.cache, 'close'):
             await self.cache.close()
        # No pool to close here
        # if self.pool:
        #     self.pool.close()
        #     await self.pool.wait_closed()
        logger.info("User service stopped.")

    # Removed _setup_commands as commands should be separate

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data by ID (from cache or DB)."""
        cache_key = f"user:{user_id}"
        try:
            # Try cache first
            cached_user = await self.cache.get_json(cache_key) # Use await if cache is async
            if cached_user:
                logger.debug(f"Cache hit for user {user_id}")
                return cached_user

            logger.debug(f"Cache miss for user {user_id}. Fetching from DB.")
            # Get from database using shared db_manager
            # Assumes a 'users' table with id, username, balance, created_at
            user_data = await self.db.fetch_one(
                "SELECT * FROM users WHERE id = $1", # Using $ placeholder
                user_id
            )

            if user_data:
                # Update cache (use TTL from config)
                await self.cache.set(
                    cache_key,
                    user_data, # db_manager fetch_one returns dict
                    ttl=USER_CACHE_TTL # Use configured TTL
                )
                return user_data
            else:
                 # User not found in DB
                 return None
        except Exception as e:
            logger.exception(f"Error getting user {user_id}: {e}")
            # Return None on error, command layer should handle user feedback
            return None

    async def get_or_create_user(self, user_id: int, username: str) -> Optional[Dict[str, Any]]:
         """Gets a user, creating them in the DB if they don't exist."""
         user = await self.get_user(user_id)
         if user:
              return user
         else:
              # Try to create user
              logger.info(f"User {user_id} not found, attempting to create.")
              try:
                   # Use default balance of 0? Or load from config?
                   default_balance = 0.0
                   await self.db.execute(
                        """
                        INSERT INTO users (id, username, balance, created_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (id) DO NOTHING -- Avoid error if race condition occurs
                        """,
                        user_id, username, default_balance, datetime.now(timezone.utc)
                   )
                   # Fetch the newly created or existing user data
                   return await self.get_user(user_id)
              except Exception as e:
                   logger.exception(f"Error creating user {user_id}: {e}")
                   raise UserServiceError("Failed to create user")


    async def update_user_balance(self, user_id: int, amount: float, transaction_type: str) -> Optional[Dict[str, Any]]:
        """Update user balance and record transaction using shared db_manager."""
        # This requires a 'transactions' table as defined in db_manager init
        try:
            # Get current user (or create if doesn't exist, safer)
            user = await self.get_or_create_user(user_id, f"User_{user_id}") # Get username properly if possible
            if not user:
                # Should not happen if get_or_create works, but handle defensively
                raise UserServiceError(f"User {user_id} could not be fetched or created.")

            new_balance = (user.get('balance', 0.0) or 0.0) + amount # Handle potential None from DB
            # Check for sufficient funds only if amount is negative (withdrawal/loss)
            if amount < 0 and new_balance < 0:
                # Or check if user['balance'] + amount < 0 *before* calculating new_balance
                raise InsufficientUnitsError(f"Insufficient balance for user {user_id} to apply {amount}") # Need this error type defined

            # Update balance in the users table
            updated = await self.db.execute(
                "UPDATE users SET balance = $1 WHERE id = $2",
                new_balance, user_id
            )

            if not updated:
                 # This indicates the user ID might not exist, despite get_or_create
                 logger.error(f"Failed to update balance for user {user_id}. User might not exist.")
                 raise UserServiceError("Failed to update user balance.")

            # Record the transaction
            await self.db.execute(
                 """
                 INSERT INTO transactions (user_id, type, amount, created_at)
                 VALUES ($1, $2, $3, $4)
                 """,
                 user_id, transaction_type, amount, datetime.now(timezone.utc)
            )

            logger.info(f"Updated balance for user {user_id}. New balance: {new_balance:.2f}. Transaction: {transaction_type} ({amount:.2f})")

            # Update cache after successful DB update
            user['balance'] = new_balance # Update the balance in the fetched dict
            cache_key = f"user:{user_id}"
            await self.cache.set(cache_key, user, ttl=USER_CACHE_TTL)

            return user # Return the updated user dict

        except InsufficientUnitsError: # Catch specific error
             raise # Re-raise to be handled by caller
        except Exception as e:
            logger.exception(f"Error updating balance for user {user_id}: {e}")
            raise UserServiceError("An internal error occurred while updating balance.")


    # Functions like _view_balance and _view_leaderboard should be part of
    # commands (e.g., commands/balance.py, commands/leaderboard.py)
    # and *use* the UserService methods (get_user, get_leaderboard_data etc.)
    # Removed _view_balance and _view_leaderboard implementations from service layer.

    async def get_user_balance(self, user_id: int) -> float:
        """Get a user's current balance directly."""
        # Primarily used internally or by commands
        try:
            user = await self.get_user(user_id)
            # Handle case where user is None (not found) or balance is None
            return user.get('balance', 0.0) if user else 0.0
        except Exception as e:
            logger.exception(f"Error getting balance for user {user_id}: {e}")
            return 0.0 # Return default on error

    # update_user_balance now handles transactions, simpler direct update not usually needed
    # async def update_user_balance_direct(self, user_id: int, amount: float) -> bool: ...

    async def get_leaderboard_data(
         self,
         timeframe: str = 'weekly',
         limit: int = 10,
         guild_id: Optional[int] = None # Optional guild filter
         ) -> List[Dict]:
        """Get leaderboard data (profit/loss) based on transactions."""
        # This should query the 'transactions' table or potentially 'unit_records'
        # depending on how profit/loss is calculated and stored.
        # Example using transactions:
        try:
             now = datetime.now(timezone.utc)
             start_date = None
             if timeframe == 'daily':
                  start_date = now - timedelta(days=1)
             elif timeframe == 'weekly':
                  start_date = now - timedelta(weeks=1)
             elif timeframe == 'monthly':
                  start_date = now - timedelta(days=30) # Approximation
             elif timeframe == 'yearly':
                  start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)

             query = """
                SELECT
                    t.user_id,
                    COALESCE(u.username, 'Unknown User') as username, -- Join users table for username
                    SUM(t.amount) as total_profit_loss
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                WHERE 1=1
             """ # WHERE 1=1 allows easy appending of filters
             params: List[Any] = []
             param_index = 1

             # --- Add Filters ---
             # Only include 'win'/'loss' type transactions? Adjust as needed.
             # query += f" AND t.type IN ('win', 'loss')" # Example filter

             if guild_id:
                 # This requires transactions or users to be linked to guilds,
                 # which isn't explicitly in the current schema examples.
                 # Add guild_id filter if schema supports it.
                 # query += f" AND t.guild_id = ${param_index}" # Example
                 # params.append(guild_id)
                 # param_index += 1
                 logger.warning("Guild filtering for leaderboard not implemented in current schema example.")
                 pass


             if start_date:
                 query += f" AND t.created_at >= ${param_index}"
                 params.append(start_date)
                 param_index += 1

             query += f" GROUP BY t.user_id, u.username ORDER BY total_profit_loss DESC LIMIT ${param_index}"
             params.append(limit)

             return await self.db.fetch_all(query, *params)

        except Exception as e:
            logger.exception(f"Error getting leaderboard data: {e}")
            return []
