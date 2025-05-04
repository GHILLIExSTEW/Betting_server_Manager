# betting-bot/services/voice_service.py

"""Service for managing voice channel updates for unit statistics."""

import discord
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta, timezone
import asyncio
from discord import VoiceChannel

try:
    from ..data.cache_manager import CacheManager
    from ..utils.errors import VoiceError, ServiceError
except ImportError:
    from data.cache_manager import CacheManager
    from utils.errors import VoiceError, ServiceError

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.cache = CacheManager()
        self.running = False
        self._update_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the voice service background tasks."""
        try:
            self.running = True
            self._update_task = asyncio.create_task(self._update_unit_channels_loop())
            logger.info("Voice service started successfully with background tasks.")
        except Exception as e:
            logger.exception(f"Error starting voice service: {e}")
            self.running = False
            if self._update_task:
                self._update_task.cancel()
            raise ServiceError(f"Failed to start voice service: {e}")

    async def stop(self) -> None:
        """Stop the voice service background tasks."""
        self.running = False
        logger.info("Stopping VoiceService...")
        tasks_to_wait_for = []
        if self._update_task:
            self._update_task.cancel()
            tasks_to_wait_for.append(self._update_task)

        if tasks_to_wait_for:
            try:
                await asyncio.gather(*tasks_to_wait_for, return_exceptions=True)
                logger.info("VoiceService background tasks finished cancelling.")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error awaiting voice service task cancellation: {e}")

        logger.info("Voice service stopped successfully")

    async def _update_unit_channels_loop(self):
        """Main loop to update unit voice channel names periodically."""
        await self.bot.wait_until_ready()
        while self.running:
            try:
                logger.debug("Running periodic unit channel update check...")
                guilds_to_update = await self.db.fetch_all("""
                    SELECT guild_id, voice_channel_id, yearly_channel_id, is_active, is_paid
                    FROM guild_settings
                    WHERE (voice_channel_id IS NOT NULL OR yearly_channel_id IS NOT NULL)
                """)

                if not guilds_to_update:
                    logger.debug("No guilds found needing unit channel updates.")
                    await asyncio.sleep(600)
                    continue

                logger.debug(f"Found {len(guilds_to_update)} guilds with voice channels configured")
                for guild in guilds_to_update:
                    logger.debug(f"Guild {guild['guild_id']} settings: active={guild['is_active']}, paid={guild['is_paid']}, "
                               f"monthly_ch={guild['voice_channel_id']}, yearly_ch={guild['yearly_channel_id']}")

                update_tasks = [self._update_guild_unit_channels(guild_info) for guild_info in guilds_to_update]

                results = await asyncio.gather(*update_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        guild_id = guilds_to_update[i].get('guild_id', 'N/A')
                        logger.error(
                            f"Error updating unit channels for guild {guild_id}: {result}",
                            exc_info=isinstance(result, Exception)
                        )

                await asyncio.sleep(300)

            except asyncio.CancelledError:
                logger.info("Unit channel update loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error in unit channel update loop: {e}")
                await asyncio.sleep(300)

    async def _update_guild_unit_channels(self, guild_info: Dict):
        """Update the unit channels for a single specified guild."""
        guild_id = guild_info['guild_id']
        monthly_ch_id = guild_info.get('voice_channel_id')
        yearly_ch_id = guild_info.get('yearly_channel_id')

        try:
            logger.debug(f"Updating channels for guild {guild_id}")
            monthly_total = await self._get_monthly_total_units(guild_id)
            yearly_total = await self._get_yearly_total_units(guild_id)
            logger.debug(f"Guild {guild_id} totals - Monthly: {monthly_total}, Yearly: {yearly_total}")

            update_tasks = []
            if monthly_ch_id:
                update_tasks.append(self._update_channel_name(monthly_ch_id, f"Monthly Units: {monthly_total:+.2f}"))
            if yearly_ch_id:
                update_tasks.append(self._update_channel_name(yearly_ch_id, f"Yearly Units: {yearly_total:+.2f}"))

            if update_tasks:
                await asyncio.gather(*update_tasks, return_exceptions=True)
                logger.debug(f"Channel updates completed for guild {guild_id}")

        except Exception as e:
            logger.error(f"Failed to fetch unit totals for guild {guild_id} during channel update: {e}")

    async def update_on_bet_resolve(self, guild_id: int):
        """Force update unit channels for a guild immediately after a bet resolves."""
        try:
            logger.info(f"Triggering unit channel update for guild {guild_id} due to bet resolution.")
            guild_settings = await self.db.fetch_one("""
                SELECT guild_id, voice_channel_id, yearly_channel_id, is_paid
                FROM guild_settings
                WHERE guild_id = %s AND is_active = TRUE
            """, guild_id)

            if guild_settings and guild_settings.get('is_paid'):
                await self._update_guild_unit_channels(guild_settings)
            else:
                logger.debug(
                    f"Skipping immediate update for guild {guild_id}: "
                    f"Not paid or no settings/channels configured."
                )

        except Exception as e:
            logger.exception(f"Error updating voice channels on bet resolve for guild {guild_id}: {e}")

    async def _get_monthly_total_units(self, guild_id: int) -> float:
        """Get the total net units for the current month using shared db_manager."""
        try:
            now = datetime.now(timezone.utc)
            logger.debug(f"Fetching monthly total for guild {guild_id} - Year: {now.year}, Month: {now.month}")
            result = await self.db.fetchval("""
                SELECT COALESCE(SUM(monthly_result_value), 0.0)
                FROM unit_records
                WHERE guild_id = %s AND year = %s AND month = %s
                """,
                guild_id, now.year, now.month
            )
            total = float(result) if result is not None else 0.0
            logger.debug(f"Monthly total for guild {guild_id}: {total}")
            return total
        except Exception as e:
            logger.exception(f"Error getting monthly total units for guild {guild_id}: {e}")
            return 0.0

    async def _get_yearly_total_units(self, guild_id: int) -> float:
        """Get the total net units for the current year using shared db_manager."""
        try:
            now = datetime.now(timezone.utc)
            logger.debug(f"Fetching yearly total for guild {guild_id} - Year: {now.year}")
            result = await self.db.fetchval("""
                SELECT COALESCE(SUM(total_result_value), 0.0)
                FROM unit_records
                WHERE guild_id = %s AND year = %s
                """,
                guild_id, now.year
            )
            total = float(result) if result is not None else 0.0
            logger.debug(f"Yearly total for guild {guild_id}: {total}")
            return total
        except Exception as e:
            logger.exception(f"Error getting yearly total units for guild {guild_id}: {e}")
            return 0.0

    async def _update_channel_name(self, channel_id: Optional[int], new_name: str):
        """Safely update a voice channel's name, handling rate limits and errors."""
        if not channel_id:
            return

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.debug(f"Channel {channel_id} not in cache, fetching...")
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.NotFound:
                    logger.warning(f"Channel ID {channel_id} not found via fetch. Cannot update name.")
                    return
                except discord.Forbidden:
                    logger.error(f"Permission error fetching channel {channel_id}. Bot needs 'View Channel'.")
                    return
                except Exception as fetch_err:
                    logger.error(f"Error fetching channel {channel_id}: {fetch_err}")
                    return

            if isinstance(channel, discord.VoiceChannel):
                trimmed_name = new_name[:100]
                if channel.name != trimmed_name:
                    await channel.edit(name=trimmed_name, reason="Updating unit stats")
                    logger.info(f"Updated channel {channel_id} name to '{trimmed_name}'")
                else:
                    logger.debug(f"Channel {channel_id} name already up-to-date ('{channel.name}'). Skipping edit.")
            elif channel:
                logger.warning(f"Channel ID {channel_id} is not a voice channel (type: {channel.type}). Cannot update name.")

        except discord.RateLimited as rl:
            retry_after = getattr(rl, 'retry_after', 5.0)
            logger.warning(f"Rate limited updating channel {channel_id}. Discord asks to retry after {retry_after:.2f}s")
        except discord.errors.NotFound:
            logger.warning(f"Channel {channel_id} not found during edit attempt (possibly deleted just now).")
        except discord.errors.Forbidden:
            logger.error(f"Permission error updating channel {channel_id} name. Bot needs 'Manage Channels' permission.")
        except Exception as e:
            logger.exception(f"Unexpected error updating channel name for {channel_id}: {e}")
