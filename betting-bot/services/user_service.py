# betting-bot/services/user_service.py

import discord
from typing import Dict, Optional, List, Any
import logging
from datetime import datetime, timezone # Keep timezone

# Use relative imports
try:
    from ..data.cache_manager import CacheManager
    from ..utils.errors import UserServiceError, InsufficientUnitsError
    from ..config.settings import USER_CACHE_TTL # Import TTL setting
except ImportError:
    from data.cache_manager import CacheManager
    from utils.errors import UserServiceError, InsufficientUnitsError
    # Define USER_CACHE_TTL here or handle missing import
    USER_CACHE_TTL = 3600 # Default TTL (1 hour)

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.cache = CacheManager()

    async def start(self):
        """Initialize async components if needed."""
        try:
            # No explicit connect needed for CacheManager unless implemented
            # if hasattr(self.cache, 'connect'): await self.cache.connect()
            logger.info("User service started successfully.")
        except Exception as e:
            logger.exception(f"Failed to start user service: {e}")
            # if hasattr(self.cache, 'close'): await self.cache.close() # Close if connect failed
            raise UserServiceError("Failed to start user service")

    async def stop(self):
        """Clean up resources."""
        logger.info("Stopping UserService...")
        # No explicit close needed for CacheManager unless implemented
        # if hasattr(self.cache, 'close'): await self.cache.close()
        logger.info("User service stopped.")


    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data by ID (from cache or DB)."""
        cache_key = f"user:{user_id}"
        try:
            # Try cache first (assuming cache methods are sync or already awaited if async)
            cached_user = self.cache.get(cache_key) # Use sync get for file/memory cache
            if cached_user:
                logger.debug(f"Cache hit for user {user_id}")
                # Ensure balance is float
                if 'balance' in cached_user and cached_user['balance'] is not None:
                    cached_user['balance'] = float(cached_user['balance'])
                return cached_user

            logger.debug(f"Cache miss for user {user_id}. Fetching from DB.")
            # Use %s placeholder
            # Use correct primary key column name 'user_id' from your schema
            user_data = await self.db.fetch_one(
                "SELECT user_id, username, balance, created_at FROM users WHERE user_id = %s", # Use %s and correct PK 'user_id'
                user_id
            )

            if user_data:
                # Ensure balance is float before caching
                if 'balance' in user_data and user_data['balance'] is not None:
                    user_data['balance'] = float(user_data['balance'])
                # Update cache
                self.cache.set(cache_key, user_data, ttl=USER_CACHE_TTL) # Use sync set
                return user_data
            else:
                 return None # User not found
        except Exception as e:
            logger.exception(f"Error getting user {user_id}: {e}")
            return None

    async def get_or_create_user(self, user_id: int, username: Optional[str] = None) -> Optional[Dict[str, Any]]:
         """Gets a user, creating them in the DB if they don't exist."""
         user = await self.get_user(user_id)
         if user:
              # Optionally update username if provided and different
              if username and user.get('username') != username:
                   # Use %s placeholders
                   await self.db.execute("UPDATE users SET username = %s WHERE user_id = %s", username, user_id) # Use %s
                   user['username'] = username # Update dict
                   self.cache.delete(f"user:{user_id}") # Invalidate cache
              return user
         else:
              # Try to create user
              logger.info(f"User {user_id} not found, attempting to create.")
              if not username:
                  try:
                      discord_user = await self.bot.fetch_user(user_id)
                      username = discord_user.name if discord_user else f"User_{user_id}"
                  except (discord.NotFound, Exception) as fetch_err:
                      username = f"User_{user_id}"
                      logger.warning(f"Could not fetch username for new user {user_id}: {fetch_err}")

              try:
                   default_balance = 0.0 # Or load from config
                   # Use INSERT IGNORE for MySQL equivalent of ON CONFLICT DO NOTHING
                   # Use UTC_TIMESTAMP() for MySQL default timestamp
                   # Ensure table columns match: user_id, username, balance, created_at (assuming join_date is default)
                   await self.db.execute(
                        """
                        INSERT IGNORE INTO users (user_id, username, balance, created_at)
                        VALUES (%s, %s, %s, UTC_TIMESTAMP())
                        """, # Use %s placeholders
                        user_id, username, default_balance
                   )
                   # Fetch again to get the created or existing user data
                   return await self.get_user(user_id)
              except Exception as e:
                   logger.exception(f"Error creating user {user_id}: {e}")
                   raise UserServiceError("Failed to create user")


    async def update_user_balance(self, user_id: int, amount: float, transaction_type: str) -> Optional[Dict[str, Any]]:
        """Update user balance and record transaction using shared db_manager."""
        # This requires a 'transactions' table as defined in db_manager init? If not, remove transaction logic.
        # Assuming no transactions table for now based on provided schema.
        try:
            user = await self.get_or_create_user(user_id)
            if not user:
                raise UserServiceError(f"User {user_id} could not be fetched or created.")

            current_balance = float(user.get('balance', 0.0) or 0.0)
            new_balance = current_balance + amount

            if amount < 0 and new_balance < 0:
                raise InsufficientUnitsError(f"User {user_id} has {current_balance:.2f}, cannot subtract {-amount:.2f}")

            # Use %s placeholders
            updated_rows = await self.db.execute(
                "UPDATE users SET balance = %s WHERE user_id = %s", # Use %s
                new_balance, user_id
            )

            # Check if update affected any rows
            if updated_rows is None or updated_rows == 0:
                 # User might not exist if get_or_create_user failed silently somehow, or balance was unchanged.
                 logger.error(f"Failed to update balance for user {user_id}. User might not exist or balance unchanged. Rows affected: {updated_rows}")
                 raise UserServiceError("Failed to update user balance.")

            logger.info(f"Updated balance for user {user_id}. New balance: {new_balance:.2f}. Amount change: {amount:+.2f} ({transaction_type})")

            # --- Transaction Recording (Remove if no transactions table) ---
            # if hasattr(self.db, 'table_exists') and await self.db.table_exists('transactions'): # Check if table exists
            #    await self.db.execute(
            #         """
            #         INSERT INTO transactions (user_id, type, amount, created_at)
            #         VALUES (%s, %s, %s, UTC_TIMESTAMP())
            #         """, # Use %s
            #         user_id, transaction_type, amount
            #    )
            # else:
            #    logger.debug("Transactions table not found, skipping transaction record.")
            # --- End Transaction Recording ---


            # --- Cache Update ---
            user['balance'] = new_balance # Update the balance in the user dict
            cache_key = f"user:{user_id}"
            self.cache.set(cache_key, user, ttl=USER_CACHE_TTL) # Update cache
            # --- End Cache Update ---

            return user # Return the updated user dict

        except InsufficientUnitsError as e:
             logger.warning(f"Balance update failed for user {user_id}: {e}")
             raise # Re-raise
        except Exception as e:
            logger.exception(f"Error updating balance for user {user_id}: {e}")
            raise UserServiceError("An internal error occurred while updating balance.")


    async def get_user_balance(self, user_id: int) -> float:
        """Get a user's current balance directly."""
        try:
            user = await self.get_user(user_id) # Uses cache/DB logic
            # Ensure return value is float
            return float(user.get('balance', 0.0) or 0.0) if user else 0.0
        except Exception as e:
            logger.exception(f"Error getting balance for user {user_id}: {e}")
            return 0.0

    async def get_leaderboard_data(
         self,
         timeframe: str = 'weekly',
         limit: int = 10,
         guild_id: Optional[int] = None # Optional guild filter
         ) -> List[Dict]:
        """Get leaderboard data (profit/loss) based on transactions."""
        # This method assumes a 'transactions' table exists.
        # If it doesn't, this needs to be calculated differently (e.g., from unit_records).
        # Keeping original logic but adding %s placeholders and checks.
        logger.warning("get_leaderboard_data relies on a 'transactions' table, which might not exist in the defined schema.")
        # TODO: Refactor this method if 'transactions' table is not used. It might need to query 'unit_records'.

        try:
             now = datetime.now(timezone.utc)
             start_date = None
             if timeframe == 'daily': start_date = now - timedelta(days=1)
             elif timeframe == 'weekly': start_date = now - timedelta(weeks=1)
             elif timeframe == 'monthly': start_date = now - timedelta(days=30)
             elif timeframe == 'yearly': start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)

             # Use %s placeholders
             query = """
                SELECT
                    t.user_id,
                    COALESCE(u.username, 'Unknown User') as username,
                    SUM(t.amount) as total_profit_loss
                FROM transactions t -- Requires transactions table
                LEFT JOIN users u ON t.user_id = u.user_id -- Join on user_id
                WHERE 1=1
             """
             params: List[Any] = []

             # Add Guild Filter if transactions table has guild_id
             # if guild_id:
             #     query += " AND t.guild_id = %s"
             #     params.append(guild_id)

             if start_date:
                 query += " AND t.created_at >= %s" # Use %s
                 params.append(start_date)

             query += f" GROUP BY t.user_id, u.username ORDER BY total_profit_loss DESC LIMIT %s" # Use %s
             params.append(limit)

             return await self.db.fetch_all(query, *params)

        except Exception as e:
            logger.exception(f"Error getting leaderboard data: {e}")
            return [] # Return empty list on error
