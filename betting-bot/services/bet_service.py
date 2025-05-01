# betting-bot/services/bet_service.py

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta, timezone
import discord
from discord import Embed, Color, ButtonStyle
from discord.ui import View, Select, Modal, TextInput, Button
from discord.ext import commands
import json

# --- Relative Imports ---
try:
    from ..utils.errors import BetServiceError, ValidationError, InsufficientUnitsError
    # Import other services if needed for type hints, accessed via self.bot
    # from .user_service import UserService
    # from .voice_service import VoiceService
except ImportError:
    from utils.errors import BetServiceError, ValidationError, InsufficientUnitsError
    # from services.user_service import UserService
    # from services.voice_service import VoiceService


logger = logging.getLogger(__name__)

class BetService:
    # Pass bot instance (commands.Bot) and db_manager
    def __init__(self, bot: commands.Bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.logger = logging.getLogger(__name__) # Use instance logger
        self._update_task: Optional[asyncio.Task] = None
        # Stores message_id -> bet details for reaction handling
        self.pending_reactions: Dict[int, Dict[str, Any]] = {}

    async def start(self):
        """Start the bet service background tasks."""
        try:
            self.logger.info("Bet service starting update task.")
            self._update_task = asyncio.create_task(self._update_bets())
            self.logger.info("Bet service update task created.")
        except Exception as e:
            self.logger.exception(f"Failed to start bet service tasks: {e}")
            raise # Re-raise to signal failure

    async def stop(self):
        """Stop the bet service background tasks."""
        self.logger.info("Stopping BetService...")
        if self._update_task:
            self._update_task.cancel()
            try:
                # Wait briefly for the task to acknowledge cancellation
                await asyncio.wait_for(self._update_task, timeout=5.0)
            except asyncio.CancelledError:
                self.logger.info("Bet update task cancelled successfully.")
            except asyncio.TimeoutError:
                self.logger.warning("Bet update task did not finish cancelling within timeout.")
            except Exception as e:
                # Log errors during task cancellation wait
                self.logger.error(f"Error awaiting bet update task cancellation: {e}")
            finally:
                self._update_task = None # Clear task reference
        # Clear pending reactions on stop? Optional.
        # self.pending_reactions.clear()
        self.logger.info("Bet service stopped.")

    async def _update_bets(self):
        """Background task to update bet statuses (e.g., expire old pending bets)."""
        await self.bot.wait_until_ready()
        while True:
            try:
                # Check for expired pending bets - Use %s
                expiration_threshold = datetime.now(timezone.utc) - timedelta(days=7) # Example: 7 days
                expired_bets = await self.db.fetch_all("""
                    SELECT bet_serial, guild_id, user_id
                    FROM bets
                    WHERE status = %s
                    AND expiration_time IS NOT NULL AND expiration_time < %s
                """, 'pending', expiration_threshold) # Use %s

                if expired_bets:
                    self.logger.info(f"Found {len(expired_bets)} pending bets past expiration threshold.")
                    for bet in expired_bets:
                        try:
                            # Call update_bet_status which now uses %s
                            await self.update_bet_status(bet['bet_serial'], 'expired', 'Expired due to age')
                            self.logger.info(f"Expired pending bet {bet['bet_serial']} for user {bet['user_id']} in guild {bet['guild_id']}")
                            # Remove from reaction tracking if expired
                            message_id_to_remove = None
                            for msg_id, details in self.pending_reactions.items():
                                if details['bet_serial'] == bet['bet_serial']:
                                    message_id_to_remove = msg_id
                                    break
                            if message_id_to_remove:
                                del self.pending_reactions[message_id_to_remove]
                                logger.debug(f"Removed expired bet {bet['bet_serial']} (message {message_id_to_remove}) from reaction tracking.")

                        except Exception as inner_e:
                            self.logger.error(f"Error expiring bet {bet['bet_serial']}: {inner_e}")
                else:
                    self.logger.debug("No expired pending bets found.")

            except asyncio.CancelledError:
                self.logger.info("Bet update loop cancelled.")
                break # Exit loop cleanly
            except ConnectionError as ce: # Catch potential DB connection issues
                self.logger.error(f"Database connection error in bet update loop: {ce}. Retrying later.")
                await asyncio.sleep(600) # Wait longer after connection error
            except Exception as e:
                self.logger.exception(f"Error in bet update loop: {e}")
                await asyncio.sleep(300) # Wait 5 mins after other errors

            await asyncio.sleep(3600) # Check hourly

    async def create_bet(
        self,
        guild_id: int,
        user_id: int,
        game_id: Optional[Union[str, int]], # Keep flexible type hint
        bet_type: str,
        team_name: str, # Changed from selection
        units: float,
        odds: float,
        channel_id: int,
        message_id: Optional[int] = None, # Keep message_id optional here
        expiration_time: Optional[datetime] = None
    ) -> int:
        """Create a new bet in the database. Returns the bet_serial (auto-increment ID)."""
        bet_serial = None # Initialize
        try:
            # --- Validation ---
            # Fetch guild-specific limits if available, otherwise use defaults
            guild_settings = await self.bot.admin_service.get_server_settings(guild_id)
            MIN_UNITS = float(guild_settings.get('min_units', 0.1)) if guild_settings else 0.1
            MAX_UNITS = float(guild_settings.get('max_units', 10.0)) if guild_settings else 10.0
            MIN_ODDS, MAX_ODDS = -10000, 10000 # Keep standard odds range

            if not (MIN_UNITS <= units <= MAX_UNITS):
                raise ValidationError(f"Units ({units}) must be between {MIN_UNITS:.2f} and {MAX_UNITS:.2f} for this server.")
            if not (MIN_ODDS <= odds <= MAX_ODDS):
                raise ValidationError(f"Odds ({odds}) must be between {MIN_ODDS} and {MAX_ODDS}")
            if -100 < odds < 100:
                raise ValidationError("Odds cannot be between -99 and 99.")
            if not bet_type: raise ValidationError("Bet Type cannot be empty.")
            if not team_name: raise ValidationError("Team name/Selection cannot be empty.")
            # --- End Validation ---

            # Ensure game_id is string or None for DB (assuming VARCHAR game_id)
            db_game_id = str(game_id) if game_id else None

            # Get current time - Use MySQL compatible function
            now_utc_for_db = datetime.now(timezone.utc) # Keep Python object for expiration check if needed
            # Use UTC_TIMESTAMP() for MySQL inside the query

            # Use %s placeholders
            # Use UTC_TIMESTAMP() for MySQL timestamps
            # `execute` returns lastrowid for INSERT with AUTO_INCREMENT in aiomysql
            last_id = await self.db.execute(
                """
                INSERT INTO bets (
                    guild_id, user_id, game_id, bet_type,
                    team_name, stake, odds, channel_id, message_id,
                    created_at, status, updated_at, expiration_time,
                    result_value, result_description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(), 'pending', UTC_TIMESTAMP(), %s, NULL, NULL)
                """, # Use %s placeholders
                guild_id, user_id, db_game_id, bet_type,
                team_name, units, odds, channel_id, message_id, # Pass message_id if available
                expiration_time # Pass Python datetime object, driver handles conversion
            )

            bet_serial = last_id # Get the auto-incremented ID

            if bet_serial:
                self.logger.info(f"Bet {bet_serial} created successfully for user {user_id} in guild {guild_id}.")
                return bet_serial
            else:
                # This shouldn't happen if AUTO_INCREMENT is set up correctly
                raise BetServiceError("Failed to retrieve bet_serial after insertion. Check DB schema (AUTO_INCREMENT on bet_serial).")

        except ValidationError as ve:
            self.logger.warning(f"Bet creation validation failed for user {user_id}: {ve}")
            raise # Re-raise for command handler
        except ConnectionError as ce: # Catch DB connection errors
            self.logger.error(f"Database connection error during bet creation for user {user_id}: {ce}")
            raise BetServiceError("Database connection error. Please try again later.") from ce
        except Exception as e:
            # Catch other potential DB errors (constraint violations, etc.) or coding errors
            self.logger.exception(f"Error creating bet for user {user_id}: {e}")
            raise BetServiceError("An internal error occurred while creating the bet.")


    async def update_bet_status(
        self,
        bet_serial: int,
        status: str,
        result_description: Optional[str] = None,
        result_value: Optional[float] = None
    ) -> bool:
        """Update the status, result description, and result value of a bet."""
        try:
            allowed_statuses = ['won', 'lost', 'push', 'canceled', 'expired', 'pending']
            if status not in allowed_statuses:
                self.logger.error(f"Invalid status '{status}' provided for bet {bet_serial}")
                return False

            # Use %s placeholders and UTC_TIMESTAMP()
            rowcount = await self.db.execute("""
                UPDATE bets
                SET status = %s, result_value = %s, result_description = %s, updated_at = UTC_TIMESTAMP()
                WHERE bet_serial = %s
            """, status, result_value, result_description, bet_serial) # Use %s

            # aiomysql execute returns number of affected rows for UPDATE
            success = rowcount is not None and rowcount > 0
            if success:
                self.logger.info(f"Updated status for bet {bet_serial} to {status}. Result Value: {result_value}")
                # If bet is no longer pending, remove from reaction tracking
                if status != 'pending':
                    message_id_to_remove = None
                    for msg_id, details in self.pending_reactions.items():
                         if details['bet_serial'] == bet_serial:
                              message_id_to_remove = msg_id
                              break
                    if message_id_to_remove:
                         del self.pending_reactions[message_id_to_remove]
                         logger.debug(f"Removed resolved bet {bet_serial} (message {message_id_to_remove}) from reaction tracking.")
            else:
                self.logger.warning(f"Failed to update status for bet {bet_serial} (Maybe not found or status unchanged?). Rows affected: {rowcount}")
            return success
        except ConnectionError as ce:
            self.logger.error(f"Database connection error during bet status update for bet {bet_serial}: {ce}")
            raise BetServiceError("Database connection error. Please try again later.") from ce
        except Exception as e:
            self.logger.exception(f"Error updating bet status for bet_serial {bet_serial}: {e}")
            raise BetServiceError("Failed to update bet status.")

    async def get_bet(self, bet_serial: int) -> Optional[Dict]:
        """Get a single bet by its ID."""
        try:
            # Use %s placeholder
            return await self.db.fetch_one("SELECT * FROM bets WHERE bet_serial = %s", bet_serial) # Use %s
        except ConnectionError as ce:
            self.logger.error(f"Database connection error getting bet {bet_serial}: {ce}")
            raise BetServiceError("Database connection error.") from ce
        except Exception as e:
            self.logger.exception(f"Error retrieving bet {bet_serial}: {e}")
            return None

    async def is_user_authorized(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is in the cappers table for the guild."""
        try:
            # Use %s placeholder
            # Assumes 'cappers' table exists with guild_id, user_id
            result = await self.db.fetch_one("""
                SELECT 1 FROM cappers
                WHERE guild_id = %s AND user_id = %s
                LIMIT 1
            """, guild_id, user_id) # Use %s
            return bool(result)
        except ConnectionError as ce:
            self.logger.error(f"DB connection error checking auth for user {user_id} in guild {guild_id}: {ce}")
            # Decide behavior: Default to False for security or raise? Raising is probably better.
            raise BetServiceError("Database connection error checking authorization.") from ce
        except Exception as e:
            self.logger.exception(f"Error checking user authorization for user {user_id} in guild {guild_id}: {e}")
            raise BetServiceError("Failed to check user authorization.")


    async def record_bet_result(self, bet_serial: int, guild_id: int, user_id: int, units: float, odds: float, result_value: float):
        """Records the outcome units in the unit_records table."""
        # IMPORTANT: This requires 'year' and 'month' columns in unit_records table!
        try:
            now = datetime.now(timezone.utc)
            current_year = now.year
            current_month = now.month
            # Use %s placeholders and UTC_TIMESTAMP()
            # Add year and month columns to the INSERT statement
            await self.db.execute(
                """
                INSERT INTO unit_records (bet_serial, guild_id, user_id, year, month, units, odds, result_value, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())
                """, # Use %s
                bet_serial, guild_id, user_id, current_year, current_month, units, odds, result_value # Pass year and month
            )
            self.logger.info(f"Recorded result for bet {bet_serial}: {result_value:+.2f} units.")
        except ConnectionError as ce:
            self.logger.error(f"DB connection error recording result for bet {bet_serial}: {ce}")
            raise BetServiceError("Database connection error while recording result.") from ce
        except Exception as e:
            self.logger.exception(f"Error recording result for bet {bet_serial}: {e}")
            # Consider if this should raise an error or just log

    async def remove_bet_result_record(self, bet_serial: int):
        """Removes the outcome record from unit_records, e.g., if a bet is reverted."""
        try:
            # Use %s placeholder
            await self.db.execute(
                """
                DELETE FROM unit_records WHERE bet_serial = %s
                """, # Use %s
                bet_serial
            )
            self.logger.info(f"Removed result record for bet {bet_serial}.")
        except ConnectionError as ce:
            self.logger.error(f"DB connection error removing result record for bet {bet_serial}: {ce}")
            raise BetServiceError("Database connection error while removing result record.") from ce
        except Exception as e:
            self.logger.exception(f"Error removing result record for bet {bet_serial}: {e}")
            # Consider if this should raise

    def _calculate_result_value(self, units: float, odds: float, outcome: str) -> float:
        """Calculate profit/loss based on American odds. Returns the net gain/loss."""
        # This logic remains the same
        if outcome == 'won':
            if odds > 0: return units * (odds / 100.0)
            elif odds < 0: return units * (100.0 / abs(odds))
            else: return 0.0
        elif outcome == 'lost': return -abs(units)
        elif outcome == 'push': return 0.0
        else: self.logger.warning(f"Calculating result value for unhandled outcome '{outcome}'. Returning 0."); return 0.0


    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction adds for bet outcomes using the pending_reactions dict."""
        # Ignore bot's own reactions
        if payload.user_id == self.bot.user.id: return
        if not payload.guild_id: return # Ignore DMs

        # Check if the reaction is on a message we are tracking
        bet_info = self.pending_reactions.get(payload.message_id)
        if not bet_info:
            # logger.debug(f"Reaction on untracked message {payload.message_id}. Ignoring.")
            return

        bet_serial = bet_info['bet_serial']
        guild_id = bet_info['guild_id']
        original_user_id = bet_info['user_id'] # The user who placed the bet

        self.logger.info(f"Reaction '{payload.emoji}' added on tracked msg {payload.message_id} (Bet: {bet_serial}) by user {payload.user_id}")

        # --- Authorization Check ---
        reactor_member = payload.member # Member object is included in payload if reaction is in guild
        if not reactor_member: # Fetch member if not cached in payload (less likely for reaction_add)
             try:
                  guild = self.bot.get_guild(payload.guild_id)
                  if not guild: return # Cannot check permissions without guild
                  reactor_member = await guild.fetch_member(payload.user_id)
             except discord.NotFound: self.logger.warning(f"Reactor {payload.user_id} not found in guild {guild_id}."); return
             except Exception as e: self.logger.error(f"Error fetching reactor member {payload.user_id}: {e}"); return

        # Allow original user OR admin to resolve
        is_original_user = reactor_member.id == original_user_id
        has_admin_permissions = reactor_member.guild_permissions.administrator # Check admin perm

        if not (is_original_user or has_admin_permissions):
            self.logger.info(f"Ignoring reaction on bet {bet_serial} msg {payload.message_id} by unauthorized user {reactor_member.id}.")
            # Optionally remove their reaction? Needs manage_messages perm.
            # try:
            #     channel = self.bot.get_channel(payload.channel_id)
            #     if channel:
            #         message = await channel.fetch_message(payload.message_id)
            #         await message.remove_reaction(payload.emoji, reactor_member)
            # except Exception as e:
            #     logger.warning(f"Could not remove unauthorized reaction: {e}")
            return
        # --- End Authorization Check ---

        # Get the current bet status from DB to prevent double processing
        try:
            original_bet = await self.get_bet(bet_serial) # Uses %s now
        except Exception as e:
            self.logger.error(f"Failed to fetch bet {bet_serial} during reaction handling: {e}")
            return

        if not original_bet:
            self.logger.warning(f"Bet {bet_serial} not found in DB for reaction handling. Removing from tracking.")
            if payload.message_id in self.pending_reactions: del self.pending_reactions[payload.message_id]
            return
        # CRITICAL: Check if bet is still pending before processing resolution
        if original_bet['status'] != 'pending':
            self.logger.info(f"Reaction added to already resolved bet {bet_serial} (Status: {original_bet['status']}). Ignored.")
            # Remove from tracking if it's somehow still there
            if payload.message_id in self.pending_reactions: del self.pending_reactions[payload.message_id]
            return

        # --- Process Reaction ---
        emoji = str(payload.emoji)
        units = float(original_bet['stake'])
        odds = float(original_bet['odds'])
        result_value = 0.0
        new_status = None
        result_desc = f'Reacted by {reactor_member.display_name}' # Base description

        # Map emojis to outcomes
        if emoji in ['✅', '☑️', '✔️']: new_status = 'won'
        elif emoji in ['❌', '✖️', '❎']: new_status = 'lost'
        elif emoji in ['🅿️', '🤷', '🤷‍♂️', '🤷‍♀️']: new_status = 'push' # Push emoji
        elif emoji in ['🚫', '🗑️']: new_status = 'canceled' # Cancel emoji

        if new_status:
            # Calculate result value based on outcome
            result_value = self._calculate_result_value(units, odds, new_status if new_status != 'canceled' else 'push') # Cancel counts as 0 units change
            result_desc = f'{new_status.title()} ({result_desc})' # e.g., "Won (Reacted by User)"

            self.logger.info(f"Processing resolution for Bet {bet_serial}: Status -> {new_status}, Value -> {result_value:.2f}")
            try:
                # Update bet status in DB (uses %s now)
                updated = await self.update_bet_status(bet_serial, new_status, result_desc, result_value)

                if updated:
                    # Record unit changes for resolved bets (win/loss/push)
                    # Ensure record_bet_result uses %s and has year/month
                    if new_status in ['won', 'lost', 'push']:
                        await self.record_bet_result(bet_serial, guild_id, original_user_id, units, odds, result_value)

                    # Update user balance if applicable (win/loss)
                    # Assumes user_service is available and handles potential errors
                    if new_status in ['won', 'lost'] and hasattr(self.bot, 'user_service'):
                        transaction_type = 'bet_win' if new_status == 'won' else 'bet_loss'
                        # User service update should handle InsufficientUnitsError if it occurs during loss update
                        await self.bot.user_service.update_user_balance(original_user_id, result_value, transaction_type)

                    # Remove from reaction tracking ONLY if successful
                    if payload.message_id in self.pending_reactions:
                        del self.pending_reactions[payload.message_id]
                        self.logger.debug(f"Removed message {payload.message_id} from pending reactions after resolution.")

                    # Send notification (uses %s implicitly via get_bet)
                    await self._send_bet_status_notification(bet_info, new_status, result_value)

                    # Trigger voice channel update (uses %s implicitly via DB calls)
                    if hasattr(self.bot, 'voice_service') and hasattr(self.bot.voice_service, 'update_on_bet_resolve'):
                        asyncio.create_task(self.bot.voice_service.update_on_bet_resolve(guild_id))

                    # Remove resolution buttons from original message
                    try:
                        channel = self.bot.get_channel(payload.channel_id)
                        if channel and isinstance(channel, discord.TextChannel):
                            message = await channel.fetch_message(payload.message_id)
                            await message.edit(view=None) # Remove the view with buttons
                            self.logger.debug(f"Removed resolution view from message {payload.message_id}")
                        else:
                             self.logger.warning(f"Could not find channel {payload.channel_id} to remove view from message {payload.message_id}")
                    except discord.NotFound:
                         self.logger.warning(f"Message {payload.message_id} not found, could not remove view.")
                    except discord.Forbidden:
                         self.logger.warning(f"Missing permissions to edit message {payload.message_id} or remove reactions.")
                    except Exception as e:
                        self.logger.warning(f"Could not remove view/reactions from message {payload.message_id}: {e}")

                else:
                    # This case means the DB update failed (e.g., bet_serial didn't exist, DB error)
                    self.logger.warning(f"Database update failed when trying to resolve bet {bet_serial} via reaction.")
                    # Should we notify the user who reacted?
                    # await reactor_member.send(f"Failed to update bet {bet_serial} status.") # DMs might be disabled

            except InsufficientUnitsError as iu_error:
                # Specific handling if updating balance fails due to insufficient funds
                self.logger.error(f"Insufficient units error processing bet {bet_serial} result: {iu_error}")
                # Notify in the channel where the reaction happened
                try:
                    channel = self.bot.get_channel(payload.channel_id)
                    if channel: await channel.send(f"⚠️ Error resolving bet `{bet_serial}`: {iu_error}. Bet status not updated.", delete_after=60)
                except Exception: pass # Ignore notification errors
                # IMPORTANT: Bet status was NOT updated, leave it pending. Do NOT remove from tracking.
            except Exception as e:
                self.logger.exception(f"Error handling reaction add resolution for bet {bet_serial}: {e}")
                # Potentially notify user if possible


    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction removes IF we want to revert bet status."""
        # Generally, it's safer NOT to revert bets automatically on reaction removal.
        # This requires careful permission checks and logging.
        # If implementing, ensure only authorized users (original better or admin)
        # can trigger a revert, and log the action extensively.
        pass # Keep empty for now


    async def _send_bet_status_notification(self, bet_info: Dict, status: str, result_value: float) -> None:
        """Send notification about bet status change (Helper)."""
        try:
            # bet_info might not have all details if fetched from pending_reactions
            # Fetch the full bet details from DB for the embed
            bet = await self.get_bet(bet_info['bet_serial']) # Uses %s now
            if not bet:
                self.logger.warning(f"Could not find bet {bet_info['bet_serial']} to send notification.")
                return

            color = discord.Color.greyple(); status_emoji = "ℹ️"
            if status == 'won': color = discord.Color.green(); status_emoji = "✅"
            elif status == 'lost': color = discord.Color.red(); status_emoji = "❌"
            elif status == 'push': color = discord.Color.blue(); status_emoji = "🅿️"
            elif status == 'canceled': color = discord.Color.orange(); status_emoji = "🚫"
            elif status == 'expired': color = discord.Color.dark_grey(); status_emoji = "⏰"

            # Use fetched bet details
            user = self.bot.get_user(bet['user_id']) # Try cache
            if not user: user = await self.bot.fetch_user(bet['user_id']) # Fetch if needed
            user_mention = user.mention if user else f"User ID: {bet['user_id']}"
            capper_name = user.display_name if user else f"User {bet['user_id']}"
            avatar_url = user.display_avatar.url if user and user.display_avatar else None

            # Create embed using DB data
            embed = Embed(
                title=f"{status_emoji} Bet {status.title()}",
                description=f"Bet ID: `{bet['bet_serial']}` placed by {user_mention}",
                color=color,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{capper_name}'s Bet Result", icon_url=avatar_url)
            embed.add_field(name="Selection", value=f"`{bet['team_name']}`", inline=False) # Use team_name
            embed.add_field(name="Units", value=f"{float(bet['stake']):.2f}u", inline=True) # Use stake
            embed.add_field(name="Odds", value=f"{float(bet['odds']):+}", inline=True)

            if status in ['won', 'lost', 'push']:
                embed.add_field(name="Result", value=f"**{result_value:+.2f} Units**", inline=True)
            else:
                embed.add_field(name="Result", value=status.title(), inline=True)

            # Include result description (who resolved it)
            if bet.get('result_description'):
                 embed.set_footer(text=f"{bet['result_description']}")
            else:
                 embed.set_footer(text=f"Resolved at") # Fallback footer

            # Send to the original bet channel
            channel = self.bot.get_channel(bet['channel_id'])
            if channel and isinstance(channel, discord.TextChannel):
                # Check bot permissions before sending
                if channel.permissions_for(channel.guild.me).send_messages:
                    await channel.send(embed=embed)
                else:
                    self.logger.warning(f"Missing SEND_MESSAGES permission in channel {bet['channel_id']} for guild {bet['guild_id']}")
            else:
                self.logger.warning(f"Could not find channel {bet['channel_id']} to send notification for bet {bet['bet_serial']}.")

        except Exception as e:
            self.logger.exception(f"Error sending bet status notification for bet {bet_info.get('bet_serial')}: {e}")
