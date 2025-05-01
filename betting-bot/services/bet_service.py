# betting-bot/services/bet_service.py

"""Service for handling betting operations."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta, timezone
import discord
from discord import Embed, Color, ButtonStyle
from discord.ui import View, Select, Modal, TextInput, Button
from discord.ext import commands
import json

try:
    from ..utils.errors import BetServiceError, ValidationError, InsufficientUnitsError
except ImportError:
    from utils.errors import BetServiceError, ValidationError, InsufficientUnitsError

logger = logging.getLogger(__name__)


class BetService:
    def __init__(self, bot: commands.Bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self._update_task: Optional[asyncio.Task] = None
        self.pending_reactions: Dict[int, Dict[str, Any]] = {}

    async def start(self):
        """Start the bet service background tasks."""
        try:
            self.logger.info("Bet service starting update task.")
            self._update_task = asyncio.create_task(self._update_bets())
            self.logger.info("Bet service update task created.")
        except Exception as e:
            self.logger.exception(f"Failed to start bet service tasks: {e}")
            raise

    async def stop(self):
        """Stop the bet service background tasks."""
        self.logger.info("Stopping BetService...")
        if self._update_task:
            self._update_task.cancel()
            try:
                await asyncio.wait_for(self._update_task, timeout=5.0)
            except asyncio.CancelledError:
                self.logger.info("Bet update task cancelled successfully.")
            except asyncio.TimeoutError:
                self.logger.warning("Bet update task did not finish cancelling within timeout.")
            except Exception as e:
                self.logger.error(f"Error awaiting bet update task cancellation: {e}")
            finally:
                self._update_task = None
        self.logger.info("Bet service stopped.")

    async def _update_bets(self):
        """Background task to update bet statuses (e.g., expire old pending bets)."""
        await self.bot.wait_until_ready()
        while True:
            try:
                expiration_threshold = datetime.now(timezone.utc) - timedelta(days=7)
                expired_bets = await self.db.fetch_all("""
                    SELECT bet_serial, guild_id, user_id
                    FROM bets
                    WHERE status = %s
                    AND expiration_time IS NOT NULL AND expiration_time < %s
                """, 'pending', expiration_threshold)

                if expired_bets:
                    self.logger.info(f"Found {len(expired_bets)} pending bets past expiration threshold.")
                    for bet in expired_bets:
                        try:
                            await self.update_bet_status(bet['bet_serial'], 'expired', 'Expired due to age')
                            self.logger.info(f"Expired pending bet {bet['bet_serial']} for user {bet['user_id']} in guild {bet['guild_id']}")
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
                break
            except ConnectionError as ce:
                self.logger.error(f"Database connection error in bet update loop: {ce}. Retrying later.")
                await asyncio.sleep(600)
            except Exception as e:
                self.logger.exception(f"Error in bet update loop: {e}")
                await asyncio.sleep(300)

            await asyncio.sleep(3600)

    async def create_bet(
        self,
        guild_id: int,
        user_id: int,
        game_id: Optional[Union[str, int]],
        bet_type: str,
        team_name: str,
        units: float,
        odds: float,
        channel_id: int,
        message_id: Optional[int] = None,
        expiration_time: Optional[datetime] = None
    ) -> int:
        """Create a new bet in the database. Returns the bet_serial."""
        bet_serial = None
        try:
            guild_settings = await self.bot.admin_service.get_server_settings(guild_id)
            MIN_UNITS = float(guild_settings.get('min_units', 0.1)) if guild_settings else 0.1
            MAX_UNITS = float(guild_settings.get('max_units', 10.0)) if guild_settings else 10.0
            MIN_ODDS, MAX_ODDS = -10000, 10000

            if not (MIN_UNITS <= units <= MAX_UNITS):
                raise ValidationError(f"Units ({units}) must be between {MIN_UNITS:.2f} and {MAX_UNITS:.2f} for this server.")
            if not (MIN_ODDS <= odds <= MAX_ODDS):
                raise ValidationError(f"Odds ({odds}) must be between {MIN_ODDS} and {MAX_ODDS}")
            if -100 < odds < 100:
                raise ValidationError("Odds cannot be between -99 and 99.")
            if not bet_type:
                raise ValidationError("Bet Type cannot be empty.")
            if not team_name:
                raise ValidationError("Team name/Selection cannot be empty.")

            db_game_id = str(game_id) if game_id else None
            now_utc_for_db = datetime.now(timezone.utc)

            last_id = await self.db.execute(
                """
                INSERT INTO bets (
                    guild_id, user_id, game_id, bet_type,
                    team_name, stake, odds, channel_id, message_id,
                    created_at, status, updated_at, expiration_time,
                    result_value, result_description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(), 'pending', UTC_TIMESTAMP(), %s, NULL, NULL)
                """,
                guild_id, user_id, db_game_id, bet_type,
                team_name, units, odds, channel_id, message_id,
                expiration_time
            )

            bet_serial = last_id

            if bet_serial:
                self.logger.info(f"Bet {bet_serial} created successfully for user {user_id} in guild {guild_id}.")
                return bet_serial
            else:
                raise BetServiceError("Failed to retrieve bet_serial after insertion. Check DB schema (AUTO_INCREMENT on bet_serial).")

        except ValidationError as ve:
            self.logger.warning(f"Bet creation validation failed for user {user_id}: {ve}")
            raise
        except ConnectionError as ce:
            self.logger.error(f"Database connection error during bet creation for user {user_id}: {ce}")
            raise BetServiceError("Database connection error. Please try again later.") from ce
        except Exception as e:
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

            rowcount = await self.db.execute("""
                UPDATE bets
                SET status = %s, result_value = %s, result_description = %s, updated_at = UTC_TIMESTAMP()
                WHERE bet_serial = %s
            """, status, result_value, result_description, bet_serial)

            success = rowcount is not None and rowcount > 0
            if success:
                self.logger.info(f"Updated status for bet {bet_serial} to {status}. Result Value: {result_value}")
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
            return await self.db.fetch_one("SELECT * FROM bets WHERE bet_serial = %s", bet_serial)
        except ConnectionError as ce:
            self.logger.error(f"Database connection error getting bet {bet_serial}: {ce}")
            raise BetServiceError("Database connection error.") from ce
        except Exception as e:
            self.logger.exception(f"Error retrieving bet {bet_serial}: {e}")
            return None

    async def is_user_authorized(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is in the cappers table for the guild."""
        try:
            result = await self.db.fetch_one("""
                SELECT 1 FROM cappers
                WHERE guild_id = %s AND user_id = %s
                LIMIT 1
            """, guild_id, user_id)
            return bool(result)
        except ConnectionError as ce:
            self.logger.error(f"DB connection error checking auth for user {user_id} in guild {guild_id}: {ce}")
            raise BetServiceError("Database connection error checking authorization.") from ce
        except Exception as e:
            self.logger.exception(f"Error checking user authorization for user {user_id} in guild {guild_id}: {e}")
            raise BetServiceError("Failed to check user authorization.")

    async def record_bet_result(self, bet_serial: int, guild_id: int, user_id: int, units: float, odds: float, result_value: float):
        """Records the outcome units in the unit_records table."""
        try:
            now = datetime.now(timezone.utc)
            current_year = now.year
            current_month = now.month
            await self.db.execute(
                """
                INSERT INTO unit_records (bet_serial, guild_id, user_id, year, month, units, odds, result_value, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())
                """,
                bet_serial, guild_id, user_id, current_year, current_month, units, odds, result_value
            )
            self.logger.info(f"Recorded result for bet {bet_serial}: {result_value:+.2f} units.")
        except ConnectionError as ce:
            self.logger.error(f"DB connection error recording result for bet {bet_serial}: {ce}")
            raise BetServiceError("Database connection error while recording result.") from ce
        except Exception as e:
            self.logger.exception(f"Error recording result for bet {bet_serial}: {e}")

    async def remove_bet_result_record(self, bet_serial: int):
        """Removes the outcome record from unit_records, e.g., if a bet is reverted."""
        try:
            await self.db.execute(
                """
                DELETE FROM unit_records WHERE bet_serial = %s
                """,
                bet_serial
            )
            self.logger.info(f"Removed result record for bet {bet_serial}.")
        except ConnectionError as ce:
            self.logger.error(f"DB connection error removing result record for bet {bet_serial}: {ce}")
            raise BetServiceError("Database connection error while removing result record.") from ce
        except Exception as e:
            self.logger.exception(f"Error removing result record for bet {bet_serial}: {e}")

    def _calculate_result_value(self, units: float, odds: float, outcome: str) -> float:
        """Calculate profit/loss based on American odds. Returns the net gain/loss."""
        if outcome == 'won':
            if odds > 0:
                return units * (odds / 100.0)
            elif odds < 0:
                return units * (100.0 / abs(odds))
            else:
                return 0.0
        elif outcome == 'lost':
            return -abs(units)
        elif outcome == 'push':
            return 0.0
        else:
            self.logger.warning(f"Calculating result value for unhandled outcome '{outcome}'. Returning 0.")
            return 0.0

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction adds for bet outcomes using the pending_reactions dict."""
        if payload.user_id == self.bot.user.id:
            return
        if not payload.guild_id:
            return

        bet_info = self.pending_reactions.get(payload.message_id)
        if not bet_info:
            return

        bet_serial = bet_info['bet_serial']
        guild_id = bet_info['guild_id']
        original_user_id = bet_info['user_id']

        self.logger.info(f"Reaction '{payload.emoji}' added on tracked msg {payload.message_id} (Bet: {bet_serial}) by user {payload.user_id}")

        reactor_member = payload.member
        if not reactor_member:
            try:
                guild = self.bot.get_guild(payload.guild_id)
                if not guild:
                    return
                reactor_member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                self.logger.warning(f"Reactor {payload.user_id} not found in guild {guild_id}.")
                return
            except Exception as e:
                self.logger.error(f"Error fetching reactor member {payload.user_id}: {e}")
                return

        is_original_user = reactor_member.id == original_user_id
        has_admin_permissions = reactor_member.guild_permissions.administrator

        if not (is_original_user or has_admin_permissions):
            self.logger.info(f"Ignoring reaction on bet {bet_serial} msg {payload.message_id} by unauthorized user {reactor_member.id}.")
            return

        try:
            original_bet = await self.get_bet(bet_serial)
        except Exception as e:
            self.logger.error(f"Failed to fetch bet {bet_serial} during reaction handling: {e}")
            return

        if not original_bet:
            self.logger.warning(f"Bet {bet_serial} not found in DB for reaction handling. Removing from tracking.")
            if payload.message_id in self.pending_reactions:
                del self.pending_reactions[payload.message_id]
            return
        if original_bet['status'] != 'pending':
            self.logger.info(f"Reaction added to already resolved bet {bet_serial} (Status: {original_bet['status']}). Ignored.")
            if payload.message_id in self.pending_reactions:
                del self.pending_reactions[payload.message_id]
            return

        emoji = str(payload.emoji)
        units = float(original_bet['stake'])
        odds = float(original_bet['odds'])
        result_value = 0.0
        new_status = None
        result_desc = f'Reacted by {reactor_member.display_name}'

        if emoji in ['✅', '☑️', '✔️']:
            new_status = 'won'
        elif emoji in ['❌', '✖️', '❎']:
            new_status = 'lost'
        elif emoji in ['🅿️', '🤷', '🤷‍♂️', '🤷‍♀️']:
            new_status = 'push'
        elif emoji in ['🚫', '🗑️']:
            new_status = 'canceled'

        if new_status:
            result_value = self._calculate_result_value(units, odds, new_status if new_status != 'canceled' else 'push')
            result_desc = f'{new_status.title()} ({result_desc})'

            self.logger.info(f"Processing resolution for Bet {bet_serial}: Status -> {new_status}, Value -> {result_value:.2f}")
            try:
                updated = await self.update_bet_status(bet_serial, new_status, result_desc, result_value)

                if updated:
                    if new_status in ['won', 'lost', 'push']:
                        await self.record_bet_result(bet_serial, guild_id, original_user_id, units, odds, result_value)

                    if new_status in ['won', 'lost'] and hasattr(self.bot, 'user_service'):
                        transaction_type = 'bet_win' if new_status == 'won' else 'bet_loss'
                        await self.bot.user_service.update_user_balance(original_user_id, result_value, transaction_type)

                    if payload.message_id in self.pending_reactions:
                        del self.pending_reactions[payload.message_id]
                        self.logger.debug(f"Removed message {payload.message_id} from pending reactions after resolution.")

                    await self._send_bet_status_notification(bet_info, new_status, result_value)

                    if hasattr(self.bot, 'voice_service') and hasattr(self.bot.voice_service, 'update_on_bet_resolve'):
                        asyncio.create_task(self.bot.voice_service.update_on_bet_resolve(guild_id))

                    try:
                        channel = self.bot.get_channel(payload.channel_id)
                        if channel and isinstance(channel, discord.TextChannel):
                            message = await channel.fetch_message(payload.message_id)
                            await message.edit(view=None)
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
                    self.logger.warning(f"Database update failed when trying to resolve bet {bet_serial} via reaction.")

            except InsufficientUnitsError as iu_error:
                self.logger.error(f"Insufficient units error processing bet {bet_serial} result: {iu_error}")
                try:
                    channel = self.bot.get_channel(payload.channel_id)
                    if channel:
                        await channel.send(f"⚠️ Error resolving bet `{bet_serial}`: {iu_error}. Bet status not updated.", delete_after=60)
                except Exception:
                    pass
            except Exception as e:
                self.logger.exception(f"Error handling reaction add resolution for bet {bet_serial}: {e}")

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction removes if reverting bet status is desired."""
        pass

    async def _send_bet_status_notification(self, bet_info: Dict, status: str, result_value: float) -> None:
        """Send notification about bet status change."""
        try:
            bet = await self.get_bet(bet_info['bet_serial'])
            if not bet:
                self.logger.warning(f"Could not find bet {bet_info['bet_serial']} to send notification.")
                return

            color = discord.Color.greyple()
            status_emoji = "ℹ️"
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

            user = self.bot.get_user(bet['user_id'])
            if not user:
                user = await self.bot.fetch_user(bet['user_id'])
            user_mention = user.mention if user else f"User ID: {bet['user_id']}"
            capper_name = user.display_name if user else f"User {bet['user_id']}"
            avatar_url = user.display_avatar.url if user and user.display_avatar else None

            embed = Embed(
                title=f"{status_emoji} Bet {status.title()}",
                description=f"Bet ID: `{bet['bet_serial']}` placed by {user_mention}",
                color=color,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=f"{capper_name}'s Bet Result", icon_url=avatar_url)
            embed.add_field(name="Selection", value=f"`{bet['team_name']}`", inline=False)
            embed.add_field(name="Units", value=f"{float(bet['stake']):.2f}u", inline=True)
            embed.add_field(name="Odds", value=f"{float(bet['odds']):+}", inline=True)

            if status in ['won', 'lost', 'push']:
                embed.add_field(name="Result", value=f"**{result_value:+.2f} Units**", inline=True)
            else:
                embed.add_field(name="Result", value=status.title(), inline=True)

            if bet.get('result_description'):
                embed.set_footer(text=f"{bet['result_description']}")
            else:
                embed.set_footer(text="Resolved at")

            channel = self.bot.get_channel(bet['channel_id'])
            if channel and isinstance(channel, discord.TextChannel):
                if channel.permissions_for(channel.guild.me).send_messages:
                    await channel.send(embed=embed)
                else:
                    self.logger.warning(f"Missing SEND_MESSAGES permission in channel {bet['channel_id']} for guild {bet['guild_id']}")
            else:
                self.logger.warning(f"Could not find channel {bet['channel_id']} to send notification for bet {bet['bet_serial']}.")

        except Exception as e:
            self.logger.exception(f"Error sending bet status notification for bet {bet_info.get('bet_serial')}: {e}")
