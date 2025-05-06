# betting-bot/services/bet_service.py

"""Service for managing bets and handling bet-related reactions."""

import logging
from typing import Dict, List, Optional, Union
# MODIFIED: Import timedelta from datetime
from datetime import datetime, timezone, timedelta
import uuid
import discord
import json

# Use relative imports if possible
try:
    from ..utils.errors import BetServiceError, ValidationError
    from ..data.db_manager import DatabaseManager # Added import for type hint if needed elsewhere
except ImportError:
    from utils.errors import BetServiceError, ValidationError
    from data.db_manager import DatabaseManager # Fallback

logger = logging.getLogger(__name__)

class BetService:
    def __init__(self, bot, db_manager: DatabaseManager): # Added type hint
        """
        Initialize the BetService.

        Args:
            bot: The Discord bot instance.
            db_manager: The database manager instance.
        """
        self.bot = bot
        self.db_manager = db_manager
        self.pending_reactions: Dict[int, Dict[str, Union[str, int, List]]] = {}
        logger.info("BetService initialized")

    async def start(self):
        """Start the BetService and perform any necessary setup."""
        logger.info("Starting BetService")
        try:
            # Example: Check for expired pending bets
            await self.cleanup_expired_bets()
            logger.info("BetService started successfully")
        except Exception as e:
            logger.error(f"Failed to start BetService: {e}", exc_info=True)
            raise BetServiceError(f"Could not start BetService: {str(e)}")

    async def stop(self):
        """Stop the BetService and perform any necessary cleanup."""
        logger.info("Stopping BetService")
        try:
            self.pending_reactions.clear()
            logger.info("BetService stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop BetService: {e}", exc_info=True)
            raise BetServiceError(f"Could not stop BetService: {str(e)}")

    async def cleanup_expired_bets(self):
        """Remove expired pending bets from the database."""
        logger.debug("Checking for expired pending bets")
        try:
            # Convert timestamp to MySQL DATETIME format
            # Using 24 hours as expiration
            # MODIFIED: Use timedelta directly from datetime module
            expiration_datetime = datetime.now(timezone.utc) - timedelta(hours=24)
            # Using bet expiry time if set, otherwise created_at
            query = """
                DELETE FROM bets
                WHERE status = 'pending'
                AND COALESCE(expiration_time, created_at) < %s
            """
            result = await self.db_manager.execute(query, (expiration_datetime,))
            # Assuming execute returns (rowcount, last_id) tuple
            rowcount = result[0] if result and result[0] is not None else 0
            if rowcount > 0:
                logger.info(f"Cleaned up {rowcount} expired pending bets.")
            else:
                logger.debug("No expired pending bets found to clean up.")
        except Exception as e:
            logger.error(f"Failed to clean up expired bets: {e}", exc_info=True)
            # Avoid raising error here if cleanup is not critical path
            # raise BetServiceError(f"Could not clean up expired bets: {str(e)}")


    async def cleanup_unconfirmed_bets(self):
        """Delete unconfirmed bets that are older than 5 minutes."""
        logger.info("Starting cleanup of unconfirmed bets")
        try:
            # MODIFIED: Use timedelta directly
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)

            # First get the bets that need to be cleaned up
            # Adjusted query for MySQL interval syntax
            query_select = """
                SELECT bet_serial, guild_id, user_id
                FROM bets
                WHERE confirmed = 0
                AND created_at < %s
            """
            expired_bets = await self.db_manager.fetch_all(query_select, (cutoff_time,))

            if not expired_bets:
                logger.debug("No unconfirmed bets to clean up")
                return

            logger.info(f"Found {len(expired_bets)} unconfirmed bets to clean up")

            deleted_count = 0
            for bet in expired_bets:
                bet_serial_int = int(bet['bet_serial']) # Ensure bet_serial is int if needed
                logger.debug(f"Attempting to clean up unconfirmed bet: {bet_serial_int}")
                try:
                    # Using the shared db_manager transaction context if available
                    # If not, individual executes are fine with autocommit pool
                    # Note: Assuming no separate bet_legs or bet_images tables based on schema provided

                    # Delete the bet itself
                    delete_query = "DELETE FROM bets WHERE bet_serial = %s AND confirmed = 0"
                    # Assuming execute returns (rowcount, last_id) tuple
                    rowcount, _ = await self.db_manager.execute(delete_query, (bet_serial_int,))

                    if rowcount is not None and rowcount > 0:
                        logger.info(f"Successfully cleaned up unconfirmed bet {bet_serial_int} for user {bet['user_id']} in guild {bet['guild_id']}")
                        deleted_count += 1
                    else:
                        logger.warning(f"Did not delete bet {bet_serial_int}. It might have been confirmed or deleted already.")

                except Exception as e:
                    logger.error(f"Failed to clean up bet {bet_serial_int}: {e}")
                    continue # Continue with the next bet

            logger.info(f"Finished cleanup. Deleted {deleted_count} unconfirmed bets.")

        except Exception as e:
            logger.error(f"Error in cleanup_unconfirmed_bets: {e}", exc_info=True)
            # Avoid raising error if cleanup is background task
            # raise BetServiceError(f"Failed to clean up unconfirmed bets: {str(e)}")


    async def confirm_bet(self, bet_serial: int, channel_id: int) -> bool:
        """Mark a bet as confirmed when the image is sent to a channel."""
        try:
            query = """
                UPDATE bets
                SET confirmed = 1,
                    channel_id = %s
                WHERE bet_serial = %s AND confirmed = 0
            """
            rowcount, _ = await self.db_manager.execute(query, (channel_id, bet_serial))
            if rowcount is not None and rowcount > 0:
                logger.info(f"Bet {bet_serial} confirmed in channel {channel_id}.")
                return True
            else:
                logger.warning(f"Failed to confirm bet {bet_serial}. Rowcount: {rowcount}. May already be confirmed or deleted.")
                # Check if it was already confirmed
                existing = await self.db_manager.fetch_one("SELECT confirmed, channel_id FROM bets WHERE bet_serial = %s", (bet_serial,))
                if existing and existing['confirmed'] == 1 and existing['channel_id'] == channel_id:
                    logger.info(f"Bet {bet_serial} was already confirmed in channel {channel_id}.")
                    return True # Treat as success if already in desired state
                return False
        except Exception as e:
            logger.error(f"Error confirming bet {bet_serial}: {e}", exc_info=True)
            return False

    async def create_straight_bet(
        self, guild_id: int, user_id: int, game_id: Optional[str],
        bet_type: str, team: str, opponent: str, line: str,
        units: float, odds: float, channel_id: Optional[int],
        league: str
    ) -> Optional[int]:
        """Create a straight bet."""
        try:
            # Convert bet_details to JSON string
            bet_details_dict = {
                # Use consistent keys matching your data model
                'game_id': game_id,
                'bet_type': bet_type, # e.g., 'moneyline', 'spread', 'total', 'player_prop'
                'team': team,         # Team being bet on (or involved if total/prop)
                'opponent': opponent, # Opponent team
                'line': line          # Specific line (e.g., "-7.5", "Over 210.5", "Player X Points Over 20.5")
                # Add player info if it's a player prop
            }
            bet_details_json = json.dumps(bet_details_dict)

            query = """
                INSERT INTO bets (
                    guild_id, user_id, league, bet_type, bet_details,
                    units, odds, channel_id, confirmed,
                    status -- Set initial status
                    -- bet_serial is auto_increment, no need to specify NULL unless required by strict SQL mode
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """

            # Execute and get rowcount and lastrowid directly
            # Assuming execute returns (rowcount, last_id) tuple
            rowcount, last_id = await self.db_manager.execute(
                query,
                guild_id, user_id, league, bet_type, bet_details_json,
                units, odds, channel_id,
                1 if channel_id else 0, # confirmed status
                'pending' # initial status
            )

            # Check if insert was successful AND we got a valid ID
            if rowcount is not None and rowcount > 0 and last_id is not None and last_id > 0:
                logger.info(f"Straight bet created successfully with bet_serial: {last_id}")
                return last_id
            else:
                logger.error(f"Failed to create straight bet or retrieve valid ID. Rowcount: {rowcount}, Last ID: {last_id}")
                # Optionally, query the table to see if the bet exists anyway (e.g., if LAST_INSERT_ID failed but insert succeeded)
                return None

        except Exception as e:
            logger.exception(f"Error creating straight bet: {e}") # Use exception logger
            return None

    async def create_parlay_bet(
        self, guild_id: int, user_id: int, legs: List[Dict],
        channel_id: Optional[int], league: str # League here might be the primary league or need adjustment
    ) -> Optional[int]:
        """Create a parlay bet."""
        try:
            # Calculate total odds from individual leg odds
            # Ensure legs have 'odds' key
            total_odds = self._calculate_parlay_odds([leg for leg in legs if 'odds' in leg])

            # Determine total units (is it sum of leg units, or a fixed stake for the parlay?)
            # Assuming a fixed stake for the whole parlay for now, adjust if needed.
            # Use a default or perhaps require it as a parameter. Let's use 1.0 as default.
            total_units = 1.0 # Placeholder: Define how parlay units/stake works

            # Prepare bet_details JSON
            bet_details_dict = {
                'legs': legs, # Store individual leg details
                # 'total_odds': total_odds # Redundant if storing in main odds column? Decide convention.
            }
            bet_details_json = json.dumps(bet_details_dict)

            query = """
                INSERT INTO bets (
                    guild_id, user_id, league, bet_type, bet_details,
                    units, odds, channel_id, confirmed,
                    status, legs -- Store number of legs
                    -- bet_serial is auto_increment
                ) VALUES (
                    %s, %s, %s, 'parlay', %s, %s, %s, %s, %s, %s, %s
                )
            """

            rowcount, last_id = await self.db_manager.execute(
                query,
                guild_id, user_id, league, # Use the passed 'league' as the overall league?
                bet_details_json, total_units, total_odds,
                channel_id, 1 if channel_id else 0, # confirmed
                'pending', # status
                len(legs) # number of legs
            )

            if rowcount is not None and rowcount > 0 and last_id is not None and last_id > 0:
                # Optional: If you need a separate table for legs, insert them here using last_id
                # Example:
                # for leg_data in legs:
                #     await self.db_manager.execute(
                #         "INSERT INTO bet_legs (bet_serial, league, team, line, odds, ...) VALUES (%s, %s, ...)",
                #         last_id, leg_data.get('league'), leg_data.get('team'), ...
                #     )
                logger.info(f"Parlay bet created successfully with bet_serial: {last_id}")
                return last_id
            else:
                logger.error(f"Failed to create parlay bet or retrieve valid ID. Rowcount: {rowcount}, Last ID: {last_id}")
                return None

        except Exception as e:
            logger.exception(f"Error creating parlay bet: {e}")
            return None

    def _calculate_parlay_odds(self, legs: List[Dict]) -> float:
        """Calculate total American odds for a parlay bet from American odds legs."""
        if not legs:
            return 0.0

        total_decimal_odds = 1.0
        try:
            for leg in legs:
                odds = float(leg.get('odds', 0)) # Make sure odds key exists and is floatable
                if odds == 0: continue # Skip legs with 0 odds? Or handle differently?

                if odds > 0:
                    decimal_leg = (odds / 100.0) + 1.0
                else: # Negative odds
                    decimal_leg = (100.0 / abs(odds)) + 1.0
                total_decimal_odds *= decimal_leg

            if total_decimal_odds <= 1.0: # No valid legs or calculation error?
                return 0.0 # Or handle as error

            # Convert back to American odds
            if total_decimal_odds >= 2.0:
                american_odds = (total_decimal_odds - 1.0) * 100.0
            else:
                american_odds = -100.0 / (total_decimal_odds - 1.0)

            return round(american_odds) # Return rounded integer American odds

        except (ValueError, TypeError, KeyError) as e:
             logger.error(f"Error calculating parlay odds: Invalid odds format in legs. {e}")
             return 0.0 # Indicate error or invalid calculation

    async def update_straight_bet_channel(self, bet_serial: int, channel_id: int):
        """
        Update the channel ID for a straight bet. (Type check added)

        Args:
            bet_serial (int): Unique bet serial number.
            channel_id (int): ID of the channel to associate with the bet.

        Raises:
            BetServiceError: If the update fails.
        """
        logger.debug(f"Updating channel_id for bet {bet_serial} to {channel_id}")
        try:
            # Ensure bet_type is 'straight' if needed, or remove check if any bet can be updated
            query = """
                UPDATE bets
                SET channel_id = %s, confirmed = 1
                WHERE bet_serial = %s
            """ # Removed bet_type check for flexibility, added confirmed=1
            rowcount, _ = await self.db_manager.execute(query, (channel_id, bet_serial))
            if rowcount is not None and rowcount > 0:
                 logger.debug(f"Bet {bet_serial} channel updated to {channel_id}")
            else:
                 logger.warning(f"Did not update channel for bet {bet_serial}. Rowcount: {rowcount}")

        except Exception as e:
            logger.error(f"Failed to update channel for bet {bet_serial}: {e}", exc_info=True)
            raise BetServiceError(f"Could not update channel for bet {bet_serial}: {str(e)}")


    async def update_parlay_bet_channel(self, bet_serial: int, channel_id: int):
        """
        Update the channel ID for a parlay bet. (Type check added)

        Args:
            bet_serial (int): Unique bet serial number.
            channel_id (int): ID of the channel to associate with the bet.

        Raises:
            BetServiceError: If the update fails.
        """
        logger.debug(f"Updating channel_id for parlay bet {bet_serial} to {channel_id}")
        try:
            query = """
                UPDATE bets
                SET channel_id = %s, confirmed = 1
                WHERE bet_serial = %s AND bet_type = 'parlay'
            """
            rowcount, _ = await self.db_manager.execute(query, (channel_id, bet_serial))
            if rowcount is not None and rowcount > 0:
                logger.debug(f"Parlay bet {bet_serial} channel updated to {channel_id}")
            else:
                 logger.warning(f"Did not update channel for parlay bet {bet_serial}. Rowcount: {rowcount}")

        except Exception as e:
            logger.error(f"Failed to update channel for bet {bet_serial}: {e}", exc_info=True)
            raise BetServiceError(f"Could not update channel for bet {bet_serial}: {str(e)}")

    async def delete_bet(self, bet_serial: int):
        """
        Delete a bet and its associated data (reactions, unit_records) from the database.

        Args:
            bet_serial (int): Unique bet serial number.

        Raises:
            BetServiceError: If the deletion fails.
        """
        logger.info(f"Attempting to delete bet {bet_serial} and associated data.")
        try:
            # Use the shared db_manager transaction context if available
            # Assuming CASCADE DELETE handles unit_records and bet_reactions based on schema FKs

            # Delete the bet itself (FKs should handle cascades)
            bet_query = "DELETE FROM bets WHERE bet_serial = %s"
            rowcount, _ = await self.db_manager.execute(bet_query, (bet_serial,))

            if rowcount is not None and rowcount > 0:
                # Remove from pending reactions cache
                self.pending_reactions = {
                    msg_id: data for msg_id, data in self.pending_reactions.items()
                    if data.get('bet_serial') != bet_serial
                }
                logger.info(f"Bet {bet_serial} deleted successfully.")
            else:
                logger.warning(f"Bet {bet_serial} not found for deletion or delete failed. Rowcount: {rowcount}")
                # Attempt to remove from cache anyway, in case DB state is inconsistent
                self.pending_reactions = {
                    msg_id: data for msg_id, data in self.pending_reactions.items()
                    if data.get('bet_serial') != bet_serial
                }


        except Exception as e:
            logger.error(f"Failed to delete bet {bet_serial}: {e}", exc_info=True)
            raise BetServiceError(f"Could not delete bet {bet_serial}: {str(e)}")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Handle a reaction added to a bet slip message.

        Args:
            payload: The raw reaction event payload.
        """
        # Ignore reactions from the bot itself
        if payload.user_id == self.bot.user.id:
            return

        message_id = payload.message_id
        logger.debug(f"Handling reaction add for message {message_id} by user {payload.user_id}")

        try:
            # Check if this message ID is being tracked for reactions
            if message_id not in self.pending_reactions:
                # logger.debug(f"No pending reaction data for message {message_id}")
                return # Silently ignore reactions on non-tracked messages

            reaction_data = self.pending_reactions[message_id]
            bet_serial = reaction_data.get('bet_serial')
            original_user_id = reaction_data.get('user_id') # User who placed the bet
            guild_id = reaction_data.get('guild_id')
            channel_id = reaction_data.get('channel_id')
            emoji_str = str(payload.emoji)

            # --- Authorization Check (Example: Only original user or admin?) ---
            # Add your own logic here if needed. E.g., check roles.
            # For now, allow any user reaction on a tracked message.

            logger.info(
                f"Reaction '{emoji_str}' added to bet {bet_serial} by user {payload.user_id} "
                f"in channel {channel_id} (guild {guild_id})"
            )

            # --- Record Reaction in DB ---
            # Use INSERT IGNORE or similar logic if you only want one reaction per user/emoji/bet
            # Ensure emoji column supports utf8mb4
            reaction_query = """
                INSERT IGNORE INTO bet_reactions (
                    bet_serial, user_id, emoji, channel_id, message_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            reaction_params = (
                bet_serial, payload.user_id, emoji_str, channel_id,
                message_id, datetime.now(timezone.utc) # Use DB's CURRENT_TIMESTAMP if preferred
            )
            await self.db_manager.execute(reaction_query, reaction_params)

            # --- Handle Bet Resolution (Win/Loss/Push) ---
            resolve_emoji_map = {
                '✅': 'won',  # Check mark
                '❌': 'lost', # Cross mark
                '➖': 'push'  # Heavy minus sign (or choose another like 🅿️)
            }

            if emoji_str in resolve_emoji_map:
                 # Add permission check: only original user or admin can resolve?
                 # Example:
                 # if payload.user_id != original_user_id and not payload.member.guild_permissions.administrator:
                 #      logger.warning(f"User {payload.user_id} tried to resolve bet {bet_serial} placed by {original_user_id}")
                 #      # Optionally notify user they can't resolve it
                 #      return

                 new_status = resolve_emoji_map[emoji_str]
                 logger.info(f"Attempting to resolve bet {bet_serial} as '{new_status}' by user {payload.user_id}")

                 # --- Fetch Bet Details for Calculation ---
                 bet_query = """
                    SELECT guild_id, user_id, units, odds, status, bet_details, league, bet_type
                    FROM bets
                    WHERE bet_serial = %s
                 """
                 bet_data = await self.db_manager.fetch_one(bet_query, (bet_serial,))

                 if not bet_data:
                      logger.error(f"Cannot resolve bet: Bet {bet_serial} not found in DB.")
                      return
                 if bet_data['status'] not in ['pending', 'live']: # Only resolve pending/live bets
                      logger.warning(f"Bet {bet_serial} cannot be resolved. Current status: {bet_data['status']}")
                      # Optionally remove the reaction if it's invalid state
                      # await self.on_raw_reaction_remove(payload) # Be careful of loops
                      return

                 # --- Update Bet Status ---
                 status_query = "UPDATE bets SET status = %s, updated_at = %s WHERE bet_serial = %s"
                 update_time = datetime.now(timezone.utc)
                 rowcount, _ = await self.db_manager.execute(status_query, (new_status, update_time, bet_serial))

                 if rowcount is None or rowcount == 0:
                      logger.error(f"Failed to update status for bet {bet_serial} to {new_status}.")
                      return # Don't proceed if status update failed

                 logger.info(f"Bet {bet_serial} status updated to '{new_status}'.")

                 # --- Calculate Result and Update Unit Records ---
                 units_staked = bet_data.get('units')
                 odds = bet_data.get('odds')
                 result_value = 0.0

                 if new_status == 'won':
                     if odds is None or units_staked is None:
                         logger.error(f"Missing odds or units for winning bet {bet_serial}")
                         return
                     if odds > 0:
                         result_value = units_staked * (odds / 100.0)
                     else: # Negative odds
                         result_value = units_staked * (100.0 / abs(odds))
                 elif new_status == 'lost':
                     if units_staked is None:
                         logger.error(f"Missing units for losing bet {bet_serial}")
                         return
                     result_value = -units_staked
                 # else: status is 'push', result_value remains 0.0

                 # Ensure we have necessary data
                 if units_staked is None or odds is None:
                      logger.error(f"Missing units or odds for bet {bet_serial}. Cannot record result.")
                      return

                 # --- Update Unit Records Table ---
                 now = datetime.now(timezone.utc)
                 year = now.year
                 month = now.month

                 # Use INSERT ... ON DUPLICATE KEY UPDATE to handle existing records for the bet
                 unit_query = """
                     INSERT INTO unit_records (
                         bet_serial, guild_id, user_id, year, month, units, odds, monthly_result_value, created_at
                     ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                     ON DUPLICATE KEY UPDATE
                         monthly_result_value = VALUES(monthly_result_value),
                         created_at = VALUES(created_at) # Update timestamp on resolve
                 """
                 unit_params = (
                     bet_serial, bet_data['guild_id'], bet_data['user_id'], year, month,
                     units_staked, odds, result_value,
                     update_time # Use the same timestamp as status update
                 )
                 await self.db_manager.execute(unit_query, unit_params)
                 logger.info(f"Unit record updated for bet {bet_serial}. Result Value: {result_value:.2f}")

                 # --- Trigger Voice Channel Update ---
                 if hasattr(self.bot, 'voice_service') and hasattr(self.bot.voice_service, 'update_on_bet_resolve'):
                    # Run update in background task to avoid blocking reaction handler
                    asyncio.create_task(self.bot.voice_service.update_on_bet_resolve(bet_data['guild_id']))
                    logger.debug(f"Triggered voice channel update for guild {bet_data['guild_id']}")

                 # Optional: Remove message from pending_reactions after resolution?
                 # Depends if you want further reactions (e.g., comments) tracked.
                 # if message_id in self.pending_reactions:
                 #     del self.pending_reactions[message_id]

        except Exception as e:
            logger.error(f"Failed to handle reaction add for message {message_id}: {e}", exc_info=True)


    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Handle a reaction removed from a bet slip message.

        Args:
            payload: The raw reaction event payload.
        """
        if payload.user_id == self.bot.user.id:
            return

        message_id = payload.message_id
        logger.debug(f"Handling reaction remove for message {message_id} by user {payload.user_id}")

        try:
            # Check if this message ID is being tracked
            if message_id not in self.pending_reactions:
                # logger.debug(f"No pending reaction data for message {message_id}")
                return

            reaction_data = self.pending_reactions[message_id]
            bet_serial = reaction_data.get('bet_serial')
            guild_id = reaction_data.get('guild_id')
            channel_id = reaction_data.get('channel_id')
            emoji_str = str(payload.emoji)

            # Example: Log the reaction removal
            logger.info(
                f"Reaction '{emoji_str}' removed from bet {bet_serial} by user {payload.user_id} "
                f"in channel {channel_id} (guild {guild_id})"
            )

            # Remove the reaction record from the database
            query = """
                DELETE FROM bet_reactions
                WHERE bet_serial = %s AND user_id = %s AND emoji = %s AND message_id = %s
            """
            params = (bet_serial, payload.user_id, emoji_str, message_id)
            await self.db_manager.execute(query, params)

            # --- Handle potential reversal of bet resolution (Optional/Complex) ---
            # If a resolution emoji (✅, ❌, ➖) is removed, should the bet status revert?
            # This adds complexity: Need to check if other resolution reactions exist.
            # Generally, it's simpler *not* to revert status automatically on reaction removal.
            # Admins might need a separate command to void/revert resolved bets if needed.
            # For now, we only log and remove the DB record for the specific reaction.

        except Exception as e:
            logger.error(f"Failed to handle reaction remove for message {message_id}: {e}", exc_info=True)
