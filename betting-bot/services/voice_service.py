# betting-bot/services/voice_service.py

import discord
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta, timezone # Add timezone
import asyncio
from discord import VoiceChannel # Keep specific discord imports

# Use relative imports
try:
    # Import DatabaseManager only for type hinting if needed
    # from ..data.db_manager import DatabaseManager
    from ..data.cache_manager import CacheManager
    # Define VoiceError in utils/errors.py if needed, or use a base ServiceError
    from ..utils.errors import VoiceError, ServiceError
except ImportError:
    # from data.db_manager import DatabaseManager # Fallback
    from data.cache_manager import CacheManager # Fallback
    from utils.errors import VoiceError, ServiceError # Fallback

# Remove direct aiosqlite import
# import aiosqlite

logger = logging.getLogger(__name__)

# Define VoiceServiceError if not in utils/errors.py and VoiceError isn't suitable
# class VoiceServiceError(ServiceError): # Example definition
#    """Base exception for voice service errors."""
#    pass

class VoiceService:
    # Corrected __init__
    def __init__(self, bot, db_manager): # Accept bot and db_manager
        """Initializes the Voice Service.

        Args:
            bot: The discord bot instance.
            db_manager: The shared DatabaseManager instance.
        """
        self.bot = bot
        self.db = db_manager # Use shared db_manager instance
        # Decide if cache should be passed in or instantiated here
        self.cache = CacheManager() # Instantiate here for now
        self.running = False
        # Background tasks for updating unit channels
        self._update_task: Optional[asyncio.Task] = None # Periodic update loop
        # State for temporary game channels (Consider if needed or should be DB driven)
        # self.active_channels: Dict[int, Dict] = {}
        # self.temporary_channels: Set[int] = set()


    async def start(self) -> None:
        """Start the voice service background tasks."""
        try:
            if hasattr(self.cache, 'connect'): await self.cache.connect()

            self.running = True
            # Start background tasks managed by this service
            self._update_task = asyncio.create_task(self._update_unit_channels_loop()) # Manages stat channels
            logger.info("Voice service started successfully with background tasks.")
        except Exception as e:
            logger.exception(f"Error starting voice service: {e}")
            if hasattr(self.cache, 'close'): await self.cache.close()
            self.running = False # Ensure running is False if start fails
            if self._update_task: self._update_task.cancel()
            # Use VoiceError or a more specific error type
            raise ServiceError(f"Failed to start voice service: {e}")

    async def stop(self) -> None:
        """Stop the voice service background tasks."""
        self.running = False
        logger.info("Stopping VoiceService...")
        tasks_to_wait_for = []
        if self._update_task:
            self._update_task.cancel()
            tasks_to_wait_for.append(self._update_task)

        # Wait for tasks to finish cancelling
        if tasks_to_wait_for:
             try:
                  await asyncio.wait(tasks_to_wait_for, timeout=5.0)
             except asyncio.TimeoutError:
                  logger.warning("VoiceService background tasks did not finish cancelling within timeout.")
             except asyncio.CancelledError:
                  pass
             except Exception as e:
                  logger.error(f"Error awaiting voice service task cancellation: {e}")

        if hasattr(self.cache, 'close'): await self.cache.close()
        logger.info("Voice service stopped successfully")


    # --- Methods for Updating Unit Stat Channels ---

    async def _update_unit_channels_loop(self):
        """Main loop to update unit voice channel names periodically."""
        await self.bot.wait_until_ready() # Wait for bot cache to be ready
        while self.running:
            try:
                logger.debug("Running periodic unit channel update check...")
                # Get all guilds that have at least one unit channel configured AND are marked as paid
                # Ensure guild_settings table has 'is_paid', 'voice_channel_id', 'yearly_channel_id' columns
                # Use self.db (the shared DatabaseManager)
                guilds_to_update = await self.db.fetch_all("""
                    SELECT guild_id, voice_channel_id, yearly_channel_id
                    FROM guild_settings
                    WHERE is_active = TRUE AND is_paid = TRUE -- Check both flags
                    AND (voice_channel_id IS NOT NULL OR yearly_channel_id IS NOT NULL)
                """) # Removed placeholder WHERE clause

                if not guilds_to_update:
                     logger.debug("No guilds found needing unit channel updates.")
                     await asyncio.sleep(300) # Check less often if nothing to do
                     continue

                update_tasks = []
                for guild_info in guilds_to_update:
                     # Create a task for each guild to update its channels
                     update_tasks.append(self._update_guild_unit_channels(guild_info))

                # Run updates concurrently and log any errors
                results = await asyncio.gather(*update_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                         guild_id = guilds_to_update[i].get('guild_id', 'N/A')
                         logger.error(f"Error updating unit channels for guild {guild_id}: {result}", exc_info=isinstance(result, Exception))


                await asyncio.sleep(300) # Update every 5 minutes (adjust interval as needed)

            except asyncio.CancelledError:
                 logger.info("Unit channel update loop cancelled.")
                 break
            except Exception as e:
                logger.exception(f"Error in unit channel update loop: {e}")
                await asyncio.sleep(300) # Wait before retrying


    async def _update_guild_unit_channels(self, guild_info: Dict):
        """Updates the unit channels for a single specified guild."""
        guild_id = guild_info['guild_id']
        monthly_ch_id = guild_info.get('voice_channel_id')
        yearly_ch_id = guild_info.get('yearly_channel_id')

        # Update monthly channel if configured
        if monthly_ch_id:
            try:
                monthly_total = await self._get_monthly_total_units(guild_id)
                await self._update_channel_name(monthly_ch_id, f"Monthly Units: {monthly_total:+.2f}")
            except Exception as e:
                 logger.error(f"Failed to update monthly channel {monthly_ch_id} for guild {guild_id}: {e}")

        # Update yearly channel if configured
        if yearly_ch_id:
            try:
                yearly_total = await self._get_yearly_total_units(guild_id)
                await self._update_channel_name(yearly_ch_id, f"Yearly Units: {yearly_total:+.2f}")
            except Exception as e:
                 logger.error(f"Failed to update yearly channel {yearly_ch_id} for guild {guild_id}: {e}")


    async def update_on_bet_resolve(self, guild_id: int):
        """Force update unit channels for a guild immediately after a bet resolves."""
        try:
            logger.info(f"Triggering unit channel update for guild {guild_id} due to bet resolution.")
            # Fetch guild settings, check if paid and channels configured
            # Use self.db
            guild_settings = await self.db.fetch_one("""
                 SELECT guild_id, voice_channel_id, yearly_channel_id, is_paid
                 FROM guild_settings
                 WHERE guild_id = $1 AND is_active = TRUE
            """, guild_id)

            if guild_settings and guild_settings.get('is_paid'):
                 if guild_settings.get('voice_channel_id') or guild_settings.get('yearly_channel_id'):
                      await self._update_guild_unit_channels(guild_settings)
                 else:
                      logger.debug(f"Skipping immediate update for guild {guild_id}: No channels configured.")
            else:
                 logger.debug(f"Skipping immediate update for guild {guild_id}: Not paid or no settings found.")

        except Exception as e:
            logger.exception(f"Error updating voice channels on bet resolve for guild {guild_id}: {e}")


    async def _get_monthly_total_units(self, guild_id: int) -> float:
        """Get the total net units for the current month using shared db_manager."""
        try:
            now = datetime.now(timezone.utc)
            # Use self.db; assumes unit_records table exists with needed columns
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(result_value), 0.0)
                FROM unit_records
                WHERE guild_id = $1 AND year = $2 AND month = $3
                """,
                guild_id, now.year, now.month
            )
            return float(result) if result is not None else 0.0
        except Exception as e:
            logger.exception(f"Error getting monthly total units for guild {guild_id}: {e}")
            return 0.0 # Return default on error


    async def _get_yearly_total_units(self, guild_id: int) -> float:
        """Get the total net units for the current year using shared db_manager."""
        try:
            now = datetime.now(timezone.utc)
            # Use self.db
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(result_value), 0.0)
                FROM unit_records
                WHERE guild_id = $1 AND year = $2
                """,
                guild_id, now.year
            )
            return float(result) if result is not None else 0.0
        except Exception as e:
            logger.exception(f"Error getting yearly total units for guild {guild_id}: {e}")
            return 0.0 # Return default on error


    async def _update_channel_name(self, channel_id: int, new_name: str):
        """Safely update a voice channel's name, handling rate limits and errors."""
        if not channel_id: # Skip if channel ID is None or 0
             logger.debug("Skipping channel name update due to invalid channel ID.")
             return

        try:
            channel = self.bot.get_channel(channel_id) # Use bot cache first
            if not channel:
                 # If not in cache, try fetching (might be slow)
                 try:
                      channel = await self.bot.fetch_channel(channel_id)
                 except discord.NotFound:
                      logger.warning(f"Channel ID {channel_id} not found via fetch. Cannot update name.")
                      # TODO: Maybe mark channel ID as invalid in DB here?
                      return
                 except discord.Forbidden:
                      logger.error(f"Permission error fetching channel {channel_id}.")
                      return
                 except Exception as fetch_err:
                      logger.error(f"Error fetching channel {channel_id}: {fetch_err}")
                      return

            if isinstance(channel, discord.VoiceChannel):
                 # Trim name to Discord's 100 char limit
                 trimmed_name = new_name[:100]
                 if channel.name != trimmed_name:
                      await channel.edit(name=trimmed_name, reason="Updating unit stats")
                      logger.info(f"Updated channel {channel_id} name to '{trimmed_name}'")
                 else:
                      logger.debug(f"Channel {channel_id} name ('{channel.name}') already up-to-date. Skipping edit.")
            elif channel:
                 logger.warning(f"Channel ID {channel_id} is not a voice channel (type: {channel.type}). Cannot update name.")
            # else case covered by fetch failure

        except discord.RateLimited as rl:
             retry_after = getattr(rl, 'retry_after', 5.0) # Get retry_after if available
             logger.warning(f"Rate limited updating channel {channel_id}. Retrying after {retry_after:.2f}s")
             # The loop will retry, but we could add specific backoff here if needed
        except discord.errors.NotFound:
             logger.warning(f"Channel {channel_id} not found during edit attempt (possibly deleted).")
             # Consider marking invalid in DB
        except discord.errors.Forbidden:
             logger.error(f"Permission error updating channel {channel_id} name. Check bot's 'Manage Channels' permission.")
             # Consider disabling updates for this channel/guild?
        except Exception as e:
            logger.exception(f"Unexpected error updating channel name for {channel_id}: {e}")

    # Removed other methods from original context if not directly used by unit channel updates
    # (e.g., _cleanup_channels, create_game_channel, move_member, _get_or_create_category)
    # Add them back if that functionality is still required by this service.
