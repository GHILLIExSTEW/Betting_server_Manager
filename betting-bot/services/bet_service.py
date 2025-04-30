# betting-bot/services/bet_service.py

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta, timezone # Ensure timezone is imported
import discord
from discord import Embed, Color, ButtonStyle
from discord.ui import View, Select, Modal, TextInput, Button
from discord.ext import commands # Import commands for type hint
import json

# --- Relative Imports (assuming services/ is sibling to data/, utils/) ---
try:
    # Import DatabaseManager only for type hinting if needed
    # from ..data.db_manager import DatabaseManager
    from ..utils.errors import BetServiceError, ValidationError, InsufficientUnitsError # Added InsufficientUnitsError
    # from ..config.settings import MIN_UNITS, MAX_UNITS, DEFAULT_UNITS # If needed
except ImportError:
     # Fallback for different execution contexts
     # from data.db_manager import DatabaseManager
     from utils.errors import BetServiceError, ValidationError, InsufficientUnitsError
     # from config.settings import MIN_UNITS, MAX_UNITS, DEFAULT_UNITS

# --- UI Classes Placeholder ---
# Assuming UI components like BetResolutionView are defined in betting.py
# --- End UI Classes Placeholder ---


logger = logging.getLogger(__name__)

class BetService:
    # Corrected __init__ signature
    def __init__(self, bot: commands.Bot, db_manager): # Accept bot and db_manager
        self.bot = bot # Store bot instance
        self.db = db_manager # Store shared db_manager instance
        self.logger = logging.getLogger(__name__)
        self._update_task: Optional[asyncio.Task] = None
        # Dictionary to track bets awaiting reaction for resolution
        # Key: message_id, Value: {'bet_id': ..., 'user_id': ..., ... other relevant info ...}
        self.pending_reactions: Dict[int, Dict] = {}


    async def start(self):
        """Start the bet service background tasks."""
        try:
            # No need to manage DB pool here if handled centrally
            self.logger.info("Bet service starting update task.")
            self._update_task = asyncio.create_task(self._update_bets())
            self.logger.info("Bet service update task created.")
        except Exception as e:
            self.logger.exception(f"Failed to start bet service tasks: {e}")
            raise # Re-raise to indicate service start failure

    async def stop(self):
        """Stop the bet service background tasks."""
        self.logger.info("Stopping BetService...")
        if self._update_task:
            self._update_task.cancel()
            try:
                # Wait for the task to actually finish cancelling
                await asyncio.wait_for(self._update_task, timeout=5.0)
            except asyncio.CancelledError:
                self.logger.info("Bet update task cancelled successfully.")
            except asyncio.TimeoutError:
                 self.logger.warning("Bet update task did not cancel within timeout.")
            except Exception as e:
                 self.logger.error(f"Error awaiting bet update task cancellation: {e}")
            self._update_task = None
        # No pool closing needed here
        self.logger.info("Bet service stopped.")

    async def _update_bets(self):
        """Background task to update bet statuses (e.g., expire old pending bets)."""
        await self.bot.wait_until_ready() # Wait for bot cache
        while True: # Loop indefinitely until service is stopped
            await asyncio.sleep(3600) # Check hourly initially
            try:
                # Example: Expire pending bets older than N days (e.g., 7 days)
                expiration_threshold = datetime.now(timezone.utc) - timedelta(days=7)

                # Use self.db (the passed-in DatabaseManager)
                # Corrected query for MySQL: Use %s placeholders, select bet_id, check expiration_time
                # Ensure expiration_time column is added to bets table schema in db_manager
                expired_bets = await self.db.fetch_all("""
                    SELECT bet_id, guild_id, user_id
                    FROM bets
                    WHERE status = %s
                    AND expiration_time IS NOT NULL AND expiration_time < %s
                """, 'pending', expiration_threshold)

                if expired_bets:
                     self.logger.info(f"Found {len(expired_bets)} pending bets past expiration threshold.")
                     for bet in expired_bets:
                          try:
                               await self.update_bet_status(bet['bet_id'], 'expired', 'Expired due to age')
                               self.logger.info(f"Expired pending bet {bet['bet_id']} for user {bet['user_id']} in guild {bet['guild_id']}")
                               # Optionally notify user/channel
                          except Exception as inner_e:
                               self.logger.error(f"Error expiring bet {bet['bet_id']}: {inner_e}")
                else:
                     self.logger.debug("No expired pending bets found.")

            except asyncio.CancelledError:
                 self.logger.info("Bet update loop cancelled.")
                 break # Exit loop cleanly
            except ConnectionError as ce:
                 self.logger.error(f"Database connection error in bet update loop: {ce}. Retrying later.")
                 await asyncio.sleep(600) # Wait 10 mins after connection error
            except Exception as e:
                # Use logger.exception to include traceback in logs
                self.logger.exception(f"Error in bet update loop: {e}")
                # Wait longer after an error before retrying
                await asyncio.sleep(300) # Wait 5 minutes after other errors

    async def create_bet(
        self,
        guild_id: int,
        user_id: int,
        game_id: Optional[Union[str, int]], # Allow int or str from selection
        bet_type: str,
        selection: str, # e.g., "Team A -3.5", "Over 210.5", "Player X > 15.5 Points"
        units: float, # Use float for units
        odds: float, # Use float for odds
        channel_id: int,
        message_id: Optional[int] = None, # Optional: Track the message ID if needed immediately
        expiration_time: Optional[datetime] = None # Added expiration time
    ) -> int: # Return the database bet_id (lastrowid from execute)
        """Create a new bet in the database."""
        bet_id = None # Initialize bet_id
        try:
            # --- Input Validation ---
            # Example validation (Load limits from config ideally)
            # from config.settings import MIN_UNITS, MAX_UNITS, MIN_ODDS, MAX_ODDS
            MIN_UNITS, MAX_UNITS = 0.1, 10.0 # Example float range
            MIN_ODDS, MAX_ODDS = -10000, 10000 # Example odds range

            if not (MIN_UNITS <= units <= MAX_UNITS):
                raise ValidationError(f"Units ({units}) must be between {MIN_UNITS} and {MAX_UNITS}")
            if not (MIN_ODDS <= odds <= MAX_ODDS):
                 raise ValidationError(f"Odds ({odds}) must be between {MIN_ODDS} and {MAX_ODDS}")
            if -100 < odds < 100:
                 raise ValidationError("Odds cannot be between -99 and 99.")
            if not bet_type: raise ValidationError("Bet Type cannot be empty.")
            if not selection: raise ValidationError("Selection cannot be empty.")
            # --- End Validation ---

            # Convert game_id if necessary (e.g., from string 'Other' or string ID)
            try:
                db_game_id = int(game_id) if game_id and str(game_id).isdigit() else None
            except (ValueError, TypeError):
                db_game_id = None # Handle non-integer game_ids

            now_utc = datetime.now(timezone.utc) # Use timezone-aware timestamp

            # Use the shared DatabaseManager instance (self.db)
            # Corrected query for MySQL: Use %s placeholders, ensure all columns match schema
            # Use default for status ('pending'), pass explicit timestamps
            last_id = await self.db.execute(
                 """
                 INSERT INTO bets (
                      guild_id, user_id, game_id, bet_type,
                      selection, units, odds, channel_id,
                      created_at, status, updated_at, expiration_time
                 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)
                 """,
                 guild_id, user_id, db_game_id, bet_type,
                 selection, units, odds, channel_id,
                 now_utc, now_utc, expiration_time
            )

            # execute should return lastrowid for INSERT on MySQL
            bet_id = last_id

            if bet_id:
                 logger.info(f"Bet {bet_id} created successfully for user {user_id} in guild {guild_id}.")
                 # If message_id is provided later (e.g., after posting), track it
                 # This logic is moved to where the message is actually sent in betting.py
                 return bet_id
            else:
                 # This case might happen if AUTO_INCREMENT is not set up correctly or execute returns something else
                 raise BetServiceError("Failed to retrieve bet_id after insertion. Check DB schema and execute method.")

        except ValidationError as ve:
             self.logger.warning(f"Bet creation validation failed for user {user_id}: {ve}")
             raise # Re-raise validation errors to be handled by the command caller
        except ConnectionError as ce:
             self.logger.error(f"Database connection error during bet creation for user {user_id}: {ce}")
             raise BetServiceError("Database connection error. Please try again later.") from ce
        except Exception as e:
            # Use logger.exception to capture traceback
            self.logger.exception(f"Error creating bet for user {user_id}: {e}")
            # Raise a generic BetServiceError for the command caller
            raise BetServiceError("An internal error occurred while creating the bet.")


    async def update_bet_status(
        self,
        bet_id: int,
        status: str, # e.g., 'won', 'lost', 'push', 'canceled', 'expired'
        result_description: Optional[str] = None, # Renamed from result
        result_value: Optional[float] = None # Calculated profit/loss
    ) -> bool:
        """Update the status, result description, and result value of a bet."""
        try:
            # Ensure status is one of the allowed values
            allowed_statuses = ['won', 'lost', 'push', 'canceled', 'expired', 'pending'] # Include pending if reverting
            if status not in allowed_statuses:
                 logger.error(f"Invalid status '{status}' provided for bet {bet_id}")
                 return False

             # Use the shared DatabaseManager instance
            # Corrected query for MySQL: Use %s placeholders, set updated_at implicitly via schema default
            # Use COALESCE to handle None for result_value/description if needed, but None should be acceptable for nullable columns
            rowcount = await self.db.execute("""
                UPDATE bets
                SET status = %s, result_value = %s, result_description = %s
                WHERE bet_id = %s
            """, status, result_value, result_description, bet_id)

            # Check if the execute method returns rowcount for UPDATE
            success = rowcount is not None and rowcount > 0
            if success:
                 logger.info(f"Updated status for bet {bet_id} to {status}. Result Value: {result_value}")
            else:
                 logger.warning(f"Failed to update status for bet {bet_id} (Maybe bet_id not found or status unchanged?). Rows affected: {rowcount}")
            return success
        except ConnectionError as ce:
            self.logger.error(f"Database connection error during bet status update for bet {bet_id}: {ce}")
            raise BetServiceError("Database connection error. Please try again later.") from ce
        except Exception as e:
            self.logger.exception(f"Error updating bet status for bet_id {bet_id}: {e}")
            raise BetServiceError("Failed to update bet status.")


    async def get_bet(self, bet_id: int) -> Optional[Dict]:
         """Get a single bet by its ID."""
         try:
              # Use %s placeholder for MySQL
              return await self.db.fetch_one("SELECT * FROM bets WHERE bet_id = %s", bet_id)
         except ConnectionError as ce:
              self.logger.error(f"Database connection error getting bet {bet_id}: {ce}")
              raise BetServiceError("Database connection error.") from ce
         except Exception as e:
              self.logger.exception(f"Error retrieving bet {bet_id}: {e}")
              return None # Return None on general error


    async def is_user_authorized(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is in the cappers table for the guild."""
        try:
            # Query the cappers table using %s placeholders
            result = await self.db.fetch_one("""
                SELECT 1 FROM cappers
                WHERE guild_id = %s AND user_id = %s
                LIMIT 1
            """, guild_id, user_id)
            return bool(result) # Returns True if a row is found, False otherwise
        except ConnectionError as ce:
            self.logger.error(f"Database connection error checking auth for user {user_id} in guild {guild_id}: {ce}")
            raise BetServiceError("Database connection error.") from ce
        except Exception as e:
            self.logger.exception(f"Error checking user authorization for user {user_id} in guild {guild_id}: {e}")
            # Default to False on error for security? Or raise an error?
            # Raising might be better to indicate a system problem.
            raise BetServiceError("Failed to check user authorization.")


    async def record_bet_result(self, bet_id: int, guild_id: int, user_id: int, units: float, odds: float, result_value: float):
         """Records the outcome units in the unit_records table."""
         try:
             now = datetime.now(timezone.utc)
             # Use %s placeholders for MySQL
             await self.db.execute(
                 """
                 INSERT INTO unit_records (bet_id, guild_id, user_id, year, month, units, odds, result_value, created_at)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                 """,
                 bet_id, guild_id, user_id, now.year, now.month, units, odds, result_value, now
             )
             logger.info(f"Recorded result for bet {bet_id}: {result_value:+.2f} units.")
         except ConnectionError as ce:
            self.logger.error(f"Database connection error recording result for bet {bet_id}: {ce}")
            # Consider how to handle this - does the bet status need reverting?
            raise BetServiceError("Database connection error while recording result.") from ce
         except Exception as e:
             self.logger.exception(f"Error recording result for bet {bet_id}: {e}")
             # Consider how to handle failure here - retry? Log and move on?


    async def remove_bet_result_record(self, bet_id: int):
         """Removes the outcome record from unit_records, e.g., if a bet is reverted."""
         try:
              # Use %s placeholders for MySQL
              await self.db.execute(
                  """
                  DELETE FROM unit_records WHERE bet_id = %s
                  """,
                  bet_id
              )
              logger.info(f"Removed result record for bet {bet_id}.")
         except ConnectionError as ce:
            self.logger.error(f"Database connection error removing result record for bet {bet_id}: {ce}")
            raise BetServiceError("Database connection error while removing result record.") from ce
         except Exception as e:
              self.logger.exception(f"Error removing result record for bet {bet_id}: {e}")


    def _calculate_result_value(self, units: float, odds: float, outcome: str) -> float:
         """Calculate profit/loss based on American odds. Returns the net gain/loss."""
         if outcome == 'won':
              if odds > 0: # Positive odds (underdog)
                   return units * (odds / 100.0)
              elif odds < 0: # Negative odds (favorite)
                   return units * (100.0 / abs(odds))
              else: # Should not happen with validation, but handle odds == 0 case
                   return 0.0
         elif outcome == 'lost':
              return -abs(units) # Loss is always the number of units risked (ensure negative)
         elif outcome == 'push':
              return 0.0
         else: # Handle canceled, expired? Default to 0?
              logger.warning(f"Calculating result value for unhandled outcome '{outcome}'. Returning 0.")
              return 0.0

    # --- Reaction Handling Logic ---

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction adds for bet outcomes."""
        if payload.user_id == self.bot.user.id: return # Ignore reactions from the bot itself
        if not payload.guild_id: return # Ignore reactions in DMs

        # Check if the message ID is one we are tracking
        bet_info = self.pending_reactions.get(payload.message_id)
        if not bet_info:
            # logger.debug(f"Reaction add on untracked message {payload.message_id}. Ignored.")
            return

        bet_id = bet_info['bet_id']
        guild_id = bet_info['guild_id']
        original_user_id = bet_info['user_id'] # The user who placed the bet

        logger.info(f"Reaction added on tracked message {payload.message_id} (Bet: {bet_id}) by user {payload.user_id}")

        # --- Authorization Check for Reaction ---
        # Fetch member object to check roles/permissions
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return # Should not happen if guild_id is present
        reactor_member = guild.get_member(payload.user_id)
        if not reactor_member:
             try: reactor_member = await guild.fetch_member(payload.user_id)
             except discord.NotFound:
                  logger.warning(f"Reactor user {payload.user_id} not found in guild {guild_id}.")
                  return
             except Exception as e:
                  logger.error(f"Error fetching reactor member {payload.user_id}: {e}")
                  return

        # Check if reactor is the original user OR an admin
        is_original_user = reactor_member.id == original_user_id
        # Check admin role (replace 'AdminRoleName' with actual role name/ID from config/DB)
        # Example check (needs role ID/name):
        # admin_role_id = await self.db.fetchval("SELECT admin_role FROM guild_settings WHERE guild_id = %s", guild_id)
        # has_admin_role = any(role.id == admin_role_id for role in reactor_member.roles) if admin_role_id else False
        has_admin_permissions = reactor_member.guild_permissions.administrator # Alternative check

        if not (is_original_user or has_admin_permissions):
             logger.info(f"Ignoring reaction on bet {bet_id} msg {payload.message_id} by unauthorized user {reactor_member.id}.")
             # Optionally remove the reaction if bot has perms?
             # try: await payload.member.remove_reaction(payload.emoji, payload.message)
             # except: pass
             return
        # --- End Authorization Check ---


        # Fetch the current bet status from DB to prevent race conditions/double processing
        try:
            original_bet = await self.get_bet(bet_id)
        except Exception as e:
             logger.error(f"Failed to fetch bet {bet_id} during reaction handling: {e}")
             return # Cannot proceed without bet data

        if not original_bet:
             logger.warning(f"Bet {bet_id} not found in database for reaction handling. Removing from tracking.")
             if payload.message_id in self.pending_reactions: del self.pending_reactions[payload.message_id]
             return
        if original_bet['status'] != 'pending':
             logger.info(f"Reaction added to already resolved bet {bet_id} (Status: {original_bet['status']}). Ignored.")
             # Clean up tracking if somehow still present
             if payload.message_id in self.pending_reactions: del self.pending_reactions[payload.message_id]
             return

        # Proceed with processing based on emoji
        emoji = str(payload.emoji)
        units = float(original_bet['units']) # Ensure float
        odds = float(original_bet['odds'])   # Ensure float
        result_value = 0.0
        new_status = None
        result_desc = None

        # Handle checkmark (won)
        if emoji in ['✅', '☑️', '✔️']: # Add variations if needed
            result_value = self._calculate_result_value(units, odds, 'won')
            new_status = 'won'
            result_desc = f'Won (Reacted by {reactor_member.display_name})'
        # Handle cross (lost)
        elif emoji in ['❌', '✖️', '❎']:
            result_value = self._calculate_result_value(units, odds, 'lost')
            new_status = 'lost'
            result_desc = f'Lost (Reacted by {reactor_member.display_name})'
        # Handle push (e.g., using a specific emoji like 🅿️ or 🤷)
        elif emoji in ['🅿️', '🤷', '🤷‍♂️', '🤷‍♀️']: # Example push emojis
             result_value = self._calculate_result_value(units, odds, 'push')
             new_status = 'push'
             result_desc = f'Push (Reacted by {reactor_member.display_name})'
        # Handle cancel (e.g., 🚫) - Should this adjust balance? Usually not.
        elif emoji in ['🚫', '🗑️']:
             new_status = 'canceled'
             result_value = 0.0 # Canceled bets usually have 0 impact
             result_desc = f'Canceled (Reacted by {reactor_member.display_name})'

        # If a valid resolution emoji was used
        if new_status:
            logger.info(f"Processing resolution for Bet {bet_id}: Status -> {new_status}, Value -> {result_value:.2f}")
            try:
                # --- Database Transaction (Ideally wrap these in a DB transaction) ---
                # 1. Update Bet Status
                updated = await self.update_bet_status(bet_id, new_status, result_desc, result_value)

                if updated:
                     # 2. Record Result Units (only if won or lost)
                     if new_status in ['won', 'lost']:
                          await self.record_bet_result(bet_id, guild_id, original_user_id, units, odds, result_value)

                     # 3. Update User Balance (call UserService) - only if won or lost
                     if new_status in ['won', 'lost'] and hasattr(self.bot, 'user_service'):
                          transaction_type = 'bet_win' if new_status == 'won' else 'bet_loss'
                          await self.bot.user_service.update_user_balance(original_user_id, result_value, transaction_type)


                     # 4. Remove from pending reactions *only if update was successful*
                     if payload.message_id in self.pending_reactions:
                          del self.pending_reactions[payload.message_id]
                          logger.debug(f"Removed message {payload.message_id} from pending reactions.")

                     # 5. Send notification (optional)
                     await self._send_bet_status_notification(bet_info, new_status, result_value)

                     # 6. Update voice channels if applicable (call voice service method)
                     if hasattr(self.bot, 'voice_service') and hasattr(self.bot.voice_service, 'update_on_bet_resolve'):
                          asyncio.create_task(self.bot.voice_service.update_on_bet_resolve(guild_id))

                     # 7. Optionally remove resolution buttons from original message
                     try:
                          channel = self.bot.get_channel(payload.channel_id)
                          if channel:
                               message = await channel.fetch_message(payload.message_id)
                               await message.edit(view=None) # Remove view with buttons
                     except Exception as e:
                          logger.warning(f"Could not remove view from message {payload.message_id}: {e}")

                else:
                     # Update failed, log warning
                     logger.warning(f"Database update failed when trying to resolve bet {bet_id} via reaction.")
                     # Do not proceed with unit recording or balance updates if status didn't change

                # --- End Database Transaction ---

            except InsufficientUnitsError as iu_error:
                 # Handle specific error from balance update if needed
                 logger.error(f"Insufficient units error processing bet {bet_id} result: {iu_error}")
                 # Potentially revert bet status update or notify admin?
                 # For now, log and maybe notify in channel
                 try:
                      channel = self.bot.get_channel(payload.channel_id)
                      if channel:
                           await channel.send(f"⚠️ Error processing bet {bet_id}: {iu_error}. Please check user balance.")
                 except Exception: pass
            except Exception as e:
                self.logger.exception(f"Error handling reaction add resolution for bet {bet_id}: {e}")
                # Consider sending an error message to the user/channel

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction removes IF we want to revert bet status."""
        # As discussed, automatically reverting is complex and often not desired.
        # Manual admin commands are usually better for corrections.
        # If implementing, need robust checks and state management.
        # logger.debug(f"Reaction remove event on message {payload.message_id}. Reverting logic is currently disabled.")
        pass # Keep it simple: no automatic reverting


    async def _send_bet_status_notification(self, bet_info: Dict, status: str, result_value: float) -> None:
        """Send notification about bet status change (Helper)."""
        try:
            # Fetch full bet details if needed (bet_info might not have all)
            bet = await self.get_bet(bet_info['bet_id'])
            if not bet:
                 logger.warning(f"Could not find bet {bet_info['bet_id']} to send notification.")
                 return

            # Determine color based on status
            color = discord.Color.greyple()
            status_emoji = "ℹ️" # Default info emoji
            if status == 'won':
                color = discord.Color.green()
                status_emoji = "✅"
            elif status == 'lost':
                color = discord.Color.red()
                status_emoji = "❌"
            elif status == 'push':
                color = discord.Color.blue()
                status_emoji = "🅿️"
            elif status == 'canceled':
                 color = discord.Color.orange()
                 status_emoji = "🚫"
            elif status == 'expired':
                 color = discord.Color.dark_grey()
                 status_emoji = "⏰"


            # Fetch user object for mention
            user = self.bot.get_user(bet['user_id'])
            user_mention = user.mention if user else f"User ID: {bet['user_id']}"
            capper_name = user.display_name if user else f"User {bet['user_id']}"

            embed = Embed(
                title=f"{status_emoji} Bet {status.title()}",
                description=f"Bet ID: `{bet['bet_id']}` placed by {user_mention}",
                color=color,
                timestamp=datetime.now(timezone.utc)
            )
            # Add Author with capper's name and avatar
            embed.set_author(name=f"{capper_name}'s Bet Result", icon_url=user.display_avatar.url if user and user.display_avatar else None)


            embed.add_field(name="Selection", value=f"`{bet['selection']}`", inline=False)
            embed.add_field(name="Units", value=f"{float(bet['units']):.2f}u", inline=True)
            embed.add_field(name="Odds", value=f"{float(bet['odds']):+}", inline=True) # Show sign

            # Show result value clearly
            if status in ['won', 'lost', 'push']:
                 embed.add_field(name="Result", value=f"**{result_value:+.2f} Units**", inline=True) # Show +/- units
            else: # Canceled/Expired
                 embed.add_field(name="Result", value=status.title(), inline=True)

            embed.set_footer(text=f"Resolved at") # Timestamp added automatically

            # Send to the original channel where the bet was posted
            channel = self.bot.get_channel(bet['channel_id'])
            if channel and isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)
            else:
                logger.warning(f"Could not find channel {bet['channel_id']} to send bet status notification for bet {bet['bet_id']}.")

        except Exception as e:
            self.logger.exception(f"Error sending bet status notification for bet {bet_info.get('bet_id')}: {e}")
