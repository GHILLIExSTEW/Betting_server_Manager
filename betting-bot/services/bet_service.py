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

# --- Relative Imports (assuming services/ is a sibling to data/, utils/) ---
try:
    # Import DatabaseManager only for type hinting if needed
    # from ..data.db_manager import DatabaseManager
    from ..utils.errors import BetServiceError, ValidationError
    # from ..config.settings import MIN_UNITS, MAX_UNITS, DEFAULT_UNITS # If needed
except ImportError:
     # Fallback for different execution contexts
     # from data.db_manager import DatabaseManager
     from utils.errors import BetServiceError, ValidationError
     # from config.settings import MIN_UNITS, MAX_UNITS, DEFAULT_UNITS

# --- UI Classes (Define or Import if needed) ---
# These were defined in the commands/betting.py file originally.
# If BetService needs to create these views/modals itself, they should be defined here
# or imported properly. For now, assuming they are handled by the command caller.
# class BetTypeSelect(Select): ...
# class LeagueSelect(Select): ...
# class GameSelect(Select): ...
# class BetDetailsModal(Modal, title="Enter Bet Details"): ...
# class UnitsSelect(Select): ...
# class ChannelSelect(Select): ...
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
                await self._update_task
            except asyncio.CancelledError:
                self.logger.info("Bet update task cancelled.")
            except Exception as e:
                 self.logger.error(f"Error awaiting bet update task cancellation: {e}")
            self._update_task = None
        # No pool closing needed here
        self.logger.info("Bet service stopped.")

    async def _update_bets(self):
        """Background task to update bet statuses (e.g., expire old pending bets)."""
        await self.bot.wait_until_ready() # Wait for bot cache
        while True: # Loop indefinitely until service is stopped
            try:
                # Example: Expire pending bets older than N days (e.g., 7 days)
                expiration_threshold = datetime.now(timezone.utc) - timedelta(days=7)

                # Use self.db (the passed-in DatabaseManager)
                # Assumes PostgreSQL syntax ($ placeholders)
                expired_bets = await self.db.fetch_all("""
                    SELECT bet_id, guild_id, user_id FROM bets
                    WHERE status = $1
                    AND created_at < $2
                """, 'pending', expiration_threshold)

                for bet in expired_bets:
                    try:
                        await self.update_bet_status(bet['bet_id'], 'expired', 'Expired due to age')
                        logger.info(f"Expired pending bet {bet['bet_id']} for user {bet['user_id']} in guild {bet['guild_id']}")
                        # Optionally notify user/channel
                    except Exception as inner_e:
                         logger.error(f"Error expiring bet {bet['bet_id']}: {inner_e}")

            except asyncio.CancelledError:
                 self.logger.info("Bet update loop cancelled.")
                 break # Exit loop cleanly
            except Exception as e:
                # Use logger.exception to include traceback in logs
                self.logger.exception(f"Error in bet update loop: {e}")
                # Wait longer after an error before retrying
                await asyncio.sleep(300) # Wait 5 minutes after error
            else:
                # Wait for the next cycle if no errors occurred
                await asyncio.sleep(3600) # Check hourly for expired bets, for example

    async def create_bet(
        self,
        guild_id: int,
        user_id: int,
        game_id: Optional[Union[str, int]], # Allow int or str from selection
        bet_type: str,
        selection: str, # e.g., "Team A -3.5", "Over 210.5", "Player X > 15.5 Points"
        units: int,
        odds: float,
        channel_id: int,
        message_id: Optional[int] = None, # Optional: Track the message ID if needed immediately
        # Add expiration time if applicable
        expiration_time: Optional[datetime] = None
    ) -> int: # Return the database bet_id
        """Create a new bet in the database."""
        try:
            # --- Input Validation ---
            # Example validation (Load limits from config ideally)
            # from config.settings import MIN_UNITS, MAX_UNITS
            MIN_UNITS, MAX_UNITS = 1, 3 # Placeholder values
            if not (MIN_UNITS <= units <= MAX_UNITS):
                raise ValidationError(f"Units must be between {MIN_UNITS} and {MAX_UNITS}")
            # Add odds validation if needed
            # Add bet_type validation if needed
            # Add selection validation if needed
            # --- End Validation ---

            # Convert game_id if necessary (e.g., from string 'Other' or string ID)
            try:
                db_game_id = int(game_id) if game_id and str(game_id).isdigit() else None
            except (ValueError, TypeError):
                db_game_id = None # Handle non-integer game_ids

            # Use the shared DatabaseManager instance (self.db)
            # Query assumes PostgreSQL ($ placeholders, RETURNING)
            result = await self.db.fetch_one("""
                INSERT INTO bets (
                    guild_id, user_id, game_id, bet_type,
                    selection, units, odds, channel_id,
                    created_at, status, updated_at, expiration_time
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending', $9, $10)
                RETURNING bet_id -- Get the generated bet_id back
            """, (
                guild_id, user_id, db_game_id, bet_type,
                selection, units, odds, channel_id,
                datetime.now(timezone.utc), # Use timezone-aware timestamp
                expiration_time # Pass expiration if applicable, otherwise NULL
            ))

            if result and 'bet_id' in result:
                 bet_id = result['bet_id']
                 logger.info(f"Bet {bet_id} created successfully for user {user_id} in guild {guild_id}.")
                 # If message_id is provided, store it for reaction tracking
                 if message_id:
                      self.pending_reactions[message_id] = {
                           'bet_id': bet_id,
                           'user_id': user_id,
                           'guild_id': guild_id,
                           'channel_id': channel_id
                           # Add other details if needed for notifications (selection, units, odds)
                      }
                      logger.debug(f"Tracking reactions for message {message_id} (Bet ID: {bet_id})")
                 return bet_id
            else:
                 # This case should be rare if RETURNING works and sequence generates ID
                 raise BetServiceError("Failed to retrieve bet_id after insertion.")

        except ValidationError as ve:
             self.logger.warning(f"Bet validation failed: {ve}")
             raise # Re-raise validation errors to be handled by the command caller
        except Exception as e:
            # Use logger.exception to capture traceback
            self.logger.exception(f"Error creating bet: {e}")
            # Raise a generic BetServiceError for the command caller
            raise BetServiceError(f"An internal error occurred while creating the bet.")


    async def update_bet_status(
        self,
        bet_id: int,
        status: str, # e.g., 'won', 'lost', 'push', 'canceled', 'expired'
        result: Optional[str] = None, # Optional description or final score
        result_value: Optional[float] = None # Calculated profit/loss
    ) -> bool:
        """Update the status, result description, and result value of a bet."""
        try:
             # Use the shared DatabaseManager instance
            # Query assumes PostgreSQL syntax
            status_code = await self.db.execute("""
                UPDATE bets
                SET status = $1, result_value = $2, updated_at = $3, result_description = $4
                WHERE bet_id = $5
            """, status, result_value, datetime.now(timezone.utc), result, bet_id)
            # Check status_code (e.g., "UPDATE 1") to confirm update happened
            success = status_code is not None and 'UPDATE 1' in status_code
            if success:
                 logger.info(f"Updated status for bet {bet_id} to {status}. Result Value: {result_value}")
            else:
                 logger.warning(f"Failed to update status for bet {bet_id} (Maybe bet_id not found?). Status code: {status_code}")
            return success
        except Exception as e:
            self.logger.exception(f"Error updating bet status for bet_id {bet_id}: {e}")
            raise BetServiceError(f"Failed to update bet status: {str(e)}")


    async def get_bet(self, bet_id: int) -> Optional[Dict]:
         """Get a single bet by its ID."""
         try:
              return await self.db.fetch_one("SELECT * FROM bets WHERE bet_id = $1", bet_id)
         except Exception as e:
              self.logger.exception(f"Error retrieving bet {bet_id}: {e}")
              return None


    async def is_user_authorized(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is in the cappers table for the guild."""
        try:
            # Query the cappers table
            result = await self.db.fetch_one("""
                SELECT 1 FROM cappers
                WHERE guild_id = $1 AND user_id = $2
            """, guild_id, user_id)
            return bool(result) # Returns True if a row is found, False otherwise
        except Exception as e:
            self.logger.exception(f"Error checking user authorization for user {user_id} in guild {guild_id}: {e}")
            # Default to False on error for security? Or raise an error?
            # Raising might be better to indicate a system problem.
            raise BetServiceError(f"Failed to check user authorization: {str(e)}")


    async def record_bet_result(self, bet_id: int, guild_id: int, user_id: int, units: int, odds: float, result_value: float):
         """Records the outcome units in the unit_records table."""
         try:
             now = datetime.now(timezone.utc)
             await self.db.execute(
                 """
                 INSERT INTO unit_records (bet_id, guild_id, user_id, year, month, units, odds, result_value, created_at)
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                 """,
                 bet_id, guild_id, user_id, now.year, now.month, units, odds, result_value, now
             )
             logger.info(f"Recorded result for bet {bet_id}: {result_value} units.")
         except Exception as e:
             self.logger.exception(f"Error recording result for bet {bet_id}: {e}")
             # Consider how to handle failure here - retry? Log and move on?

    async def remove_bet_result_record(self, bet_id: int):
         """Removes the outcome record from unit_records, e.g., if a bet is reverted."""
         try:
              await self.db.execute(
                  """
                  DELETE FROM unit_records WHERE bet_id = $1
                  """,
                  bet_id
              )
              logger.info(f"Removed result record for bet {bet_id}.")
         except Exception as e:
              self.logger.exception(f"Error removing result record for bet {bet_id}: {e}")


    async def _calculate_result_value(self, units: int, odds: float, outcome: str) -> float:
         """Calculate profit/loss based on American odds."""
         if outcome == 'won':
              if odds > 0: # Positive odds
                   return units * (odds / 100.0)
              else: # Negative odds
                   return units * (100.0 / abs(odds))
         elif outcome == 'lost':
              return -float(units) # Loss is always the number of units risked
         elif outcome == 'push':
              return 0.0
         else: # Handle canceled, expired? Default to 0?
              return 0.0

    # --- Reaction Handling Logic ---

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction adds for bet outcomes."""
        if payload.message_id not in self.pending_reactions:
            return # Not a message we are tracking

        bet_info = self.pending_reactions[payload.message_id]

        # Optional: Check if the reactor is the user who placed the bet or an admin
        # member = payload.member # Member object if in guild, None if in DMs
        # if not member or member.id != bet_info['user_id']:
        #    # Add logic here to check for admin role if needed
        #    is_admin = False # Placeholder
        #    if not is_admin:
        #         logger.debug(f"Ignoring reaction on msg {payload.message_id} by non-owner/non-admin {payload.user_id}")
        #         return

        emoji = str(payload.emoji)
        bet_id = bet_info['bet_id']
        original_bet = await self.get_bet(bet_id)

        if not original_bet or original_bet['status'] != 'pending':
             logger.warning(f"Reaction added to non-pending or non-existent bet {bet_id}. Ignored.")
             # Maybe clean up self.pending_reactions[payload.message_id] here?
             return

        units = original_bet['units']
        odds = original_bet['odds']
        result_value = 0.0
        new_status = None
        result_desc = None

        # Handle checkmark (won)
        if emoji in ['✅', '☑️', '✔️']:
            result_value = self._calculate_result_value(units, odds, 'won')
            new_status = 'won'
            result_desc = 'Won via reaction'
        # Handle cross (lost)
        elif emoji in ['❌', '✖️', '❎']:
            result_value = self._calculate_result_value(units, odds, 'lost')
            new_status = 'lost'
            result_desc = 'Lost via reaction'
        # Handle push (e.g., using a specific emoji like 🅿️ or 🤷)
        elif emoji in ['🅿️', '🤷', '🤷‍♂️', '🤷‍♀️']: # Example push emojis
             result_value = self._calculate_result_value(units, odds, 'push')
             new_status = 'push'
             result_desc = 'Push via reaction'

        if new_status:
            try:
                # Update DB
                updated = await self.update_bet_status(bet_id, new_status, result_desc, result_value)
                if updated:
                     # Record result if won or lost (not push)
                     if new_status in ['won', 'lost']:
                          await self.record_bet_result(bet_id, bet_info['guild_id'], bet_info['user_id'], units, odds, result_value)

                     # Remove from pending reactions *only if update was successful*
                     if payload.message_id in self.pending_reactions:
                          del self.pending_reactions[payload.message_id]
                          logger.debug(f"Removed message {payload.message_id} from pending reactions.")

                     # Send notification (optional)
                     await self._send_bet_status_notification(bet_info, new_status, result_value)

                     # Update voice channels if applicable (call voice service method)
                     if hasattr(self.bot, 'voice_service') and hasattr(self.bot.voice_service, 'update_on_bet_resolve'):
                          asyncio.create_task(self.bot.voice_service.update_on_bet_resolve(bet_info['guild_id']))

            except Exception as e:
                self.logger.exception(f"Error handling reaction add for bet {bet_id}: {e}")
                # Consider sending an error message to the user/channel

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction removes IF we want to revert bet status."""
        # --- Decide if reverting is desired ---
        # Reverting based on reaction removal can be complex and maybe undesirable.
        # If a bet is marked won/lost, should removing the checkmark/cross revert it?
        # For simplicity, often it's better *not* to revert based on reaction removal.
        # Admins would need a command to manually revert/edit bets.
        # If you *do* want reverting:
        # 1. Check if payload.message_id is in a list of *resolved* tracked messages (needs new state tracking).
        # 2. Check if the remover is the resolver or an admin.
        # 3. Fetch the bet. If it's 'won'/'lost'/'push':
        #    a. Update status back to 'pending'.
        #    b. Remove the record from unit_records using self.remove_bet_result_record(bet_id).
        #    c. Add the message_id back to self.pending_reactions.
        #    d. Notify users.
        # logger.debug(f"Reaction remove event on message {payload.message_id}. Reverting logic is currently disabled.")
        pass # Keep it simple: no automatic reverting on reaction removal


    async def _send_bet_status_notification(self, bet_info: Dict, status: str, result_value: float) -> None:
        """Send notification about bet status change (Helper)."""
        try:
            # Fetch full bet details if needed (bet_info might only have IDs)
            bet = await self.get_bet(bet_info['bet_id'])
            if not bet: return

            user = self.bot.get_user(bet['user_id']) # Fetch user object
            if not user:
                user_mention = f"User ID: {bet['user_id']}"
            else:
                user_mention = user.mention

            color = discord.Color.greyple()
            if status == 'won':
                color = discord.Color.green()
            elif status == 'lost':
                color = discord.Color.red()
            elif status == 'push':
                color = discord.Color.blue()

            embed = Embed(
                title=f"Bet {status.title()}",
                description=f"Bet ID: `{bet['bet_id']}`",
                color=color,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="Capper", value=user_mention, inline=True)
            # Add league/game info if available in 'bet' dict
            embed.add_field(name="Selection", value=f"`{bet['selection']}`", inline=False)
            embed.add_field(name="Units", value=str(bet['units']), inline=True)
            embed.add_field(name="Odds", value=str(bet['odds']), inline=True)
            embed.add_field(name="Result", value=f"{result_value:+.2f} Units", inline=True) # Show +/- units

            # Send to the original channel
            channel = self.bot.get_channel(bet['channel_id'])
            if channel and isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)
            else:
                logger.warning(f"Could not find channel {bet['channel_id']} to send bet status notification for bet {bet['bet_id']}.")

        except Exception as e:
            self.logger.exception(f"Error sending bet status notification for bet {bet_info.get('bet_id')}: {e}")
