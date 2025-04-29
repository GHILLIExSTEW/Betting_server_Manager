# betting-bot/services/user_service.py

import discord
# from discord import app_commands # Not needed if commands handled elsewhere
from typing import Dict, Optional, List, Any
import logging
from datetime import datetime, timedelta, timezone # Add timezone

# Use relative imports
try:
    # Import DatabaseManager only for type hinting if needed
    # from ..data.db_manager import DatabaseManager
    from ..data.cache_manager import CacheManager
    # Define/Import InsufficientUnitsError if needed, likely from errors
    from ..utils.errors import UserServiceError, InsufficientUnitsError
    # Load TTL from settings if available
    from ..config.settings import USER_CACHE_TTL
except ImportError:
    # from data.db_manager import DatabaseManager
    from data.cache_manager import CacheManager
    from utils.errors import UserServiceError, InsufficientUnitsError # Fallbacks
    # Define USER_CACHE_TTL here or handle missing import
    USER_CACHE_TTL = 3600 # Default TTL (1 hour) if settings import fails


# Remove aiomysql imports
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


    async def start(self):
        """Initialize async components if needed (like cache connection)."""
        try:
            if hasattr(self.cache, 'connect'):
                await self.cache.connect()
            logger.info("User service started successfully.")
        except Exception as e:
            logger.exception(f"Failed to start user service: {e}")
            if hasattr(self.cache, 'close'):
                 await self.cache.close()
            raise UserServiceError("Failed to start user service")

    async def stop(self):
        """Clean up resources (like cache connection)."""
        logger.info("Stopping UserService...")
        if hasattr(self.cache, 'close'):
             await self.cache.close()
        logger.info("User service stopped.")


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
                "SELECT id, username, balance, created_at FROM users WHERE id = $1", # Using $ placeholder
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

    async def get_or_create_user(self, user_id: int, username: Optional[str] = None) -> Optional[Dict[str, Any]]:
         """Gets a user, creating them in the DB if they don't exist."""
         user = await self.get_user(user_id)
         if user:
              # Optionally update username if provided and different
              if username and user.get('username') != username:
                   await self.db.execute("UPDATE users SET username = $1 WHERE id = $2", username, user_id)
                   user['username'] = username # Update cached/returned dict
                   # Invalidate cache if username changes
                   await self.cache.delete(f"user:{user_id}")
              return user
         else:
              # Try to create user
              logger.info(f"User {user_id} not found, attempting to create.")
              # Fetch username using bot if not provided
              if not username:
                  try:
                      discord_user = await self.bot.fetch_user(user_id)
                      username = discord_user.name if discord_user else f"User_{user_id}"
                  except discord.NotFound:
                      username = f"User_{user_id}"
                      logger.warning(f"Could not fetch username for new user {user_id}")
                  except Exception as fetch_err:
                      username = f"User_{user_id}"
                      logger.error(f"Error fetching username for {user_id}: {fetch_err}")


              try:
                   default_balance = 0.0 # Or load from config
                   # Use ON CONFLICT DO NOTHING for safe concurrent creation attempts
                   await self.db.execute(
                        """
                        INSERT INTO users (id, username, balance, created_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        user_id, username, default_balance, datetime.now(timezone.utc)
                   )
                   logger.info(f"Created user entry for {user_id} ({username}).")
                   # Fetch the newly created or existing user data again to ensure consistency
                   return await self.get_user(user_id)
              except Exception as e:
                   logger.exception(f"Error creating user {user_id}: {e}")
                   raise UserServiceError("Failed to create user")


    async def update_user_balance(self, user_id: int, amount: float, transaction_type: str) -> Optional[Dict[str, Any]]:
        """Update user balance and record transaction using shared db_manager."""
        # This requires a 'transactions' table as defined in db_manager init
        try:
            # Get current user (or create if doesn't exist, safer)
            user = await self.get_or_create_user(user_id) # Fetch or create user
            if not user:
                raise UserServiceError(f"User {user_id} could not be fetched or created.")

            current_balance = user.get('balance', 0.0) or 0.0 # Handle potential None from DB or 0
            new_balance = current_balance + amount

            # Check for sufficient funds only if amount is negative (withdrawal/loss)
            if amount < 0 and new_balance < 0:
                # Raise specific error defined in utils/errors.py
                raise InsufficientUnitsError(f"User {user_id} has {current_balance:.2f}, cannot subtract {-amount:.2f}")

            # --- Database Transaction ---
            # Ideally, balance update and transaction record should be atomic
            # db_manager execute might need enhancement for transactions, or handle here
            # For now, assume separate calls are okay, but consider atomicity
            updated = await self.db.execute(
                "UPDATE users SET balance = $1 WHERE id = $2",
                new_balance, user_id
            )

            if not updated or 'UPDATE 0' in (updated or ''):
                 # This indicates the user ID might not exist OR balance was unchanged
                 logger.error(f"Failed to update balance for user {user_id}. User might not exist or balance unchanged.")
                 raise UserServiceError("Failed to update user balance.")

            # Record the transaction
            await self.db.execute(
                 """
                 INSERT INTO transactions (user_id, type, amount, created_at)
                 VALUES ($1, $2, $3, $4)
                 """,
                 user_id, transaction_type, amount, datetime.now(timezone.utc)
            )
            # --- End Database Transaction ---

            logger.info(f"Updated balance for user {user_id}. New balance: {new_balance:.2f}. Transaction: {transaction_type} ({amount:+.2f})")

            # --- Cache Update ---
            user['balance'] = new_balance # Update the balance in the user dict
            cache_key = f"user:{user_id}"
            await self.cache.set(cache_key, user, ttl=USER_CACHE_TTL) # Update cache
            # --- End Cache Update ---

            return user # Return the updated user dict

        except InsufficientUnitsError as e: # Catch specific error
             logger.warning(f"Balance update failed for user {user_id}: {e}")
             raise # Re-raise to be handled by command caller
        except Exception as e:
            logger.exception(f"Error updating balance for user {user_id}: {e}")
            raise UserServiceError("An internal error occurred while updating balance.")


    async def get_user_balance(self, user_id: int) -> float:
        """Get a user's current balance directly."""
        try:
            user = await self.get_user(user_id) # Uses cache/DB logic
            return user.get('balance', 0.0) if user else 0.0
        except Exception as e:
            logger.exception(f"Error getting balance for user {user_id}: {e}")
            return 0.0 # Return default on error

    async def get_leaderboard_data(
         self,
         timeframe: str = 'weekly',
         limit: int = 10,
         guild_id: Optional[int] = None # Optional guild filter (requires schema support)
         ) -> List[Dict]:
        """Get leaderboard data (profit/loss) based on transactions."""
        # Requires 'transactions' table and optionally linking transactions/users to guilds
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

             # Query assumes transactions table exists
             query = """
                SELECT
                    t.user_id,
                    COALESCE(u.username, 'Unknown User') as username,
                    SUM(t.amount) as total_profit_loss
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                WHERE 1=1
             """
             params: List[Any] = []
             param_index = 1

             # Add Guild Filter if schema supports it (e.g., if transactions have guild_id)
             # if guild_id:
             #     query += f" AND t.guild_id = ${param_index}" # Example
             #     params.append(guild_id)
             #     param_index += 1

             if start_date:
                 query += f" AND t.created_at >= ${param_index}"
                 params.append(start_date)
                 param_index += 1

             query += f" GROUP BY t.user_id, u.username ORDER BY total_profit_loss DESC LIMIT ${param_index}"
             params.append(limit)

             return await self.db.fetch_all(query, *params)

        except Exception as e:
            logger.exception(f"Error getting leaderboard data: {e}")
            return [] # Return empty list on error
