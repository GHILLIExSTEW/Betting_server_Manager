# betting-bot/services/voice_service.py

import discord
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta, timezone # Add timezone
import asyncio
from discord import VoiceChannel # Keep specific discord imports

# Use relative imports
try:
    # from ..data.db_manager import DatabaseManager # For type hint
    from ..data.cache_manager import CacheManager # If used, though not used here currently
    from ..utils.errors import VoiceError, ServiceError # Import relevant errors
except ImportError:
    # from data.db_manager import DatabaseManager # Fallback
    from data.cache_manager import CacheManager # Fallback
    from utils.errors import VoiceError, ServiceError # Fallback


logger = logging.getLogger(__name__)

# Define VoiceServiceError if needed, or use ServiceError
# class VoiceServiceError(ServiceError):
#    """Base exception for voice service errors."""
#    pass

class VoiceService:
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager # Use shared db_manager instance
        self.cache = CacheManager() # Instantiate cache (though not heavily used in this version)
        self.running = False
        self._update_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the voice service background tasks."""
        try:
            # No specific async init for CacheManager in this version
            # if hasattr(self.cache, 'connect'): await self.cache.connect()

            self.running = True
            self._update_task = asyncio.create_task(self._update_unit_channels_loop())
            logger.info("Voice service started successfully with background tasks.")
        except Exception as e:
            logger.exception(f"Error starting voice service: {e}")
            # if hasattr(self.cache, 'close'): await self.cache.close()
            self.running = False
            if self._update_task: self._update_task.cancel()
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
                  # Use gather to wait for cancellation
                  await asyncio.gather(*tasks_to_wait_for, return_exceptions=True)
                  logger.info("VoiceService background tasks finished cancelling.")
             except asyncio.CancelledError: pass # Expected
             except Exception as e: logger.error(f"Error awaiting voice service task cancellation: {e}")

        # No specific close for CacheManager unless implemented
        # if hasattr(self.cache, 'close'): await self.cache.close()
        logger.info("Voice service stopped successfully")


    # --- Methods for Updating Unit Stat Channels ---

    async def _update_unit_channels_loop(self):
        """Main loop to update unit voice channel names periodically."""
        await self.bot.wait_until_ready()
        while self.running:
            try:
                logger.debug("Running periodic unit channel update check...")
                # Use %s placeholders
                guilds_to_update = await self.db.fetch_all("""
                    SELECT guild_id, voice_channel_id, yearly_channel_id
                    FROM guild_settings
                    WHERE is_active = TRUE AND is_paid = TRUE
                    AND (voice_channel_id IS NOT NULL OR yearly_channel_id IS NOT NULL)
                """) # No parameters needed here

                if not guilds_to_update:
                     logger.debug("No guilds found needing unit channel updates.")
                     # Check less often if nothing needs updating
                     await asyncio.sleep(600) # Sleep for 10 minutes
                     continue

                update_tasks = [self._update_guild_unit_channels(guild_info) for guild_info in guilds_to_update]

                results = await asyncio.gather(*update_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                         guild_id = guilds_to_update[i].get('guild_id', 'N/A')
                         logger.error(f"Error updating unit channels for guild {guild_id}: {result}", exc_info=isinstance(result, Exception))

                # Regular update interval
                await asyncio.sleep(300) # Update every 5 minutes

            except asyncio.CancelledError:
                 logger.info("Unit channel update loop cancelled.")
                 break
            except Exception as e:
                logger.exception(f"Error in unit channel update loop: {e}")
                await asyncio.sleep(300) # Wait before retrying


    async def _update_guild_unit_channels(self, guild_info: Dict):
        """Updates the unit channels for a single specified guild."""
        guild_id = guild_info['guild_id']
        monthly_ch_id = guild_info.get('voice_channel_id') # Corresponds to 'Monthly Units'
        yearly_ch_id = guild_info.get('yearly_channel_id') # Corresponds to 'Yearly Units'

        try:
            # Use Guild ID to fetch totals
            monthly_total = await self._get_monthly_total_units(guild_id)
            yearly_total = await self._get_yearly_total_units(guild_id)

            # Update channels concurrently
            update_tasks = []
            if monthly_ch_id:
                update_tasks.append(self._update_channel_name(monthly_ch_id, f"Monthly Units: {monthly_total:+.2f}"))
            if yearly_ch_id:
                update_tasks.append(self._update_channel_name(yearly_ch_id, f"Yearly Units: {yearly_total:+.2f}"))

            if update_tasks:
                 await asyncio.gather(*update_tasks, return_exceptions=True) # Log errors if gather fails

        except Exception as e:
             # Log error specific to fetching totals for this guild
             logger.error(f"Failed to fetch unit totals for guild {guild_id} during channel update: {e}")


    async def update_on_bet_resolve(self, guild_id: int):
        """Force update unit channels for a guild immediately after a bet resolves."""
        try:
            logger.info(f"Triggering unit channel update for guild {guild_id} due to bet resolution.")
            # Use %s placeholder
            guild_settings = await self.db.fetch_one("""
                 SELECT guild_id, voice_channel_id, yearly_channel_id, is_paid
                 FROM guild_settings
                 WHERE guild_id = %s AND is_active = TRUE
            """, guild_id) # Use %s

            if guild_settings and guild_settings.get('is_paid'):
                 # Pass the fetched settings dict directly
                 await self._update_guild_unit_channels(guild_settings)
            else:
                 logger.debug(f"Skipping immediate update for guild {guild_id}: Not paid or no settings/channels configured.")

        except Exception as e:
            logger.exception(f"Error updating voice channels on bet resolve for guild {guild_id}: {e}")


    async def _get_monthly_total_units(self, guild_id: int) -> float:
        """Get the total net units for the current month using shared db_manager."""
        # Requires unit_records table has year and month columns
        try:
            now = datetime.now(timezone.utc)
            # Use %s placeholders
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(result_value), 0.0)
                FROM unit_records
                WHERE guild_id = %s AND year = %s AND month = %s
                """, # Use %s
                guild_id, now.year, now.month
            )
            # fetchval returns the value directly or None
            return float(result) if result is not None else 0.0
        except Exception as e:
            logger.exception(f"Error getting monthly total units for guild {guild_id}: {e}")
            return 0.0


    async def _get_yearly_total_units(self, guild_id: int) -> float:
        """Get the total net units for the current year using shared db_manager."""
        # Requires unit_records table has year column
        try:
            now = datetime.now(timezone.utc)
            # Use %s placeholder
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(result_value), 0.0)
                FROM unit_records
                WHERE guild_id = %s AND year = %s
                """, # Use %s
                guild_id, now.year
            )
            return float(result) if result is not None else 0.0
        except Exception as e:
            logger.exception(f"Error getting yearly total units for guild {guild_id}: {e}")
            return 0.0


    async def _update_channel_name(self, channel_id: Optional[int], new_name: str):
        """Safely update a voice channel's name, handling rate limits and errors."""
        if not channel_id: return # Skip if ID is invalid/None

        try:
            # Attempt to get channel from bot cache first is fastest
            channel = self.bot.get_channel(channel_id)
            if not channel:
                 # If not in cache, fetch from Discord API (slower, rate-limited)
                 try:
                      logger.debug(f"Channel {channel_id} not in cache, fetching...")
                      channel = await self.bot.fetch_channel(channel_id)
                 except discord.NotFound:
                      logger.warning(f"Channel ID {channel_id} not found via fetch. Cannot update name.")
                      # TODO: Maybe mark channel ID as invalid in DB guild_settings here?
                      return
                 except discord.Forbidden:
                      logger.error(f"Permission error fetching channel {channel_id}. Bot needs 'View Channel'.")
                      return
                 except Exception as fetch_err:
                      logger.error(f"Error fetching channel {channel_id}: {fetch_err}")
                      return

            if isinstance(channel, discord.VoiceChannel):
                 # Trim name to Discord's 100 char limit if necessary
                 trimmed_name = new_name[:100]
                 if channel.name != trimmed_name:
                      # Only edit if name needs changing
                      await channel.edit(name=trimmed_name, reason="Updating unit stats")
                      logger.info(f"Updated channel {channel_id} name to '{trimmed_name}'")
                 else:
                      logger.debug(f"Channel {channel_id} name already up-to-date ('{channel.name}'). Skipping edit.")
            elif channel: # Channel exists but is not a VoiceChannel
                 logger.warning(f"Channel ID {channel_id} is not a voice channel (type: {channel.type}). Cannot update name.")
            # else case means channel is None even after fetch attempt (logged above)

        except discord.RateLimited as rl:
             retry_after = getattr(rl, 'retry_after', 5.0)
             logger.warning(f"Rate limited updating channel {channel_id}. Discord asks to retry after {retry_after:.2f}s")
             # The periodic loop will naturally retry later. Avoid sleeping here.
        except discord.errors.NotFound:
             logger.warning(f"Channel {channel_id} not found during edit attempt (possibly deleted just now).")
             # TODO: Mark invalid in DB?
        except discord.errors.Forbidden:
             logger.error(f"Permission error updating channel {channel_id} name. Bot needs 'Manage Channels' permission.")
             # TODO: Disable updates for this channel/guild in DB?
        except Exception as e:
            # Catch any other unexpected errors during the edit attempt
            logger.exception(f"Unexpected error updating channel name for {channel_id}: {e}")
