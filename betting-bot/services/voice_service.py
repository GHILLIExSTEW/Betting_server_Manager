# betting-bot/services/voice_service.py

import discord
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta, timezone # Add timezone
import asyncio
from discord import VoiceChannel # Keep specific discord imports

# Use relative imports
try:
    # from ..data.db_manager import DatabaseManager # Not needed if passed in
    from ..data.cache_manager import CacheManager
    from ..utils.errors import VoiceError # Define VoiceError in utils/errors.py if needed
except ImportError:
    # from data.db_manager import DatabaseManager
    from data.cache_manager import CacheManager
    from utils.errors import VoiceError # Ensure VoiceError exists

# Remove direct aiosqlite import
# import aiosqlite

logger = logging.getLogger(__name__)

# Define VoiceServiceError if not in utils/errors.py
# class VoiceServiceError(Exception):
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
        self._cleanup_task: Optional[asyncio.Task] = None
        # These might need rethinking - managing channel state in memory can be tricky
        # across restarts or multiple bot instances. Consider storing relevant state in DB.
        self.active_channels: Dict[int, Dict] = {} # guild_id -> channel_info (TEMPORARY STATE)
        self.temporary_channels: Set[int] = set() # channel_ids (TEMPORARY STATE)
        # --- Background tasks for updating unit channels ---
        self._update_task: Optional[asyncio.Task] = None # Periodic update loop
        self._monthly_total_task: Optional[asyncio.Task] = None # Monthly calc check
        self._yearly_total_task: Optional[asyncio.Task] = None # Yearly calc check
        # self.db_path = '...' # Not needed

    async def start(self) -> None:
        """Start the voice service background tasks."""
        try:
            if hasattr(self.cache, 'connect'): await self.cache.connect()

            self.running = True
            # Start background tasks managed by this service
            # self._cleanup_task = asyncio.create_task(self._cleanup_channels()) # Manages temporary game channels
            self._update_task = asyncio.create_task(self._update_unit_channels_loop()) # Manages stat channels
            # self._monthly_total_task = asyncio.create_task(self._monthly_total_loop()) # Manages historical totals
            # self._yearly_total_task = asyncio.create_task(self._yearly_total_loop()) # Manages historical totals
            logger.info("Voice service started successfully with background tasks.")
        except Exception as e:
            logger.exception(f"Error starting voice service: {e}")
            if hasattr(self.cache, 'close'): await self.cache.close()
            self.running = False # Ensure running is False if start fails
            # Cancel any tasks that might have partially started
            if self._update_task: self._update_task.cancel()
            # if self._monthly_total_task: self._monthly_total_task.cancel()
            # if self._yearly_total_task: self._yearly_total_task.cancel()
            raise VoiceError(f"Failed to start voice service: {e}") # Use VoiceError

    async def stop(self) -> None:
        """Stop the voice service background tasks."""
        self.running = False
        logger.info("Stopping VoiceService...")
        tasks_to_wait_for = []
        # if self._cleanup_task:
        #     self._cleanup_task.cancel()
        #     tasks_to_wait_for.append(self._cleanup_task)
        if self._update_task:
            self._update_task.cancel()
            tasks_to_wait_for.append(self._update_task)
        # if self._monthly_total_task:
        #     self._monthly_total_task.cancel()
        #     tasks_to_wait_for.append(self._monthly_total_task)
        # if self._yearly_total_task:
        #     self._yearly_total_task.cancel()
        #     tasks_to_wait_for.append(self._yearly_total_task)

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


        # self.active_channels.clear() # Clear temporary state
        # self.temporary_channels.clear() # Clear temporary state
        if hasattr(self.cache, 'close'): await self.cache.close()
        logger.info("Voice service stopped successfully")

    # --- Methods related to temporary game/betting channels ---
    # These might be less relevant if focusing only on stat channels, keep if needed

    async def create_game_channel(
        self,
        guild_id: int,
        game_id: int,
        game_name: str,
        category_id: Optional[int] = None
    ) -> Optional[discord.VoiceChannel]:
        """Create a temporary voice channel for a specific game."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                # Maybe log instead of raising? Depends on caller.
                logger.error(f"Guild {guild_id} not found when trying to create game channel.")
                return None # Return None if guild not found

            # Get or create category
            category = None
            if category_id:
                category = guild.get_channel(category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                 # Fallback to finding/creating default category
                 category = await self._get_or_create_category(guild, "Game Channels") # Example category name


            channel_name = f"🎮 {game_name}" # Simplified name example
            # Create voice channel within the category
            channel = await guild.create_voice_channel(
                name=channel_name[:100], # Ensure name is within Discord limits
                category=category,
                reason=f"Temp channel for game {game_name}"
            )

            # Store channel info (Consider DB instead of memory for persistence)
            # self.active_channels[guild_id] = { ... }
            # self.temporary_channels.add(channel.id)
            logger.info(f"Created temporary game channel '{channel.name}' ({channel.id}) in guild {guild_id}")
            return channel
        except discord.errors.Forbidden:
             logger.error(f"Permission error creating game channel in guild {guild_id}.")
             raise VoiceError("Bot lacks permissions to create voice channels.")
        except Exception as e:
            logger.exception(f"Error creating game channel in guild {guild_id}: {e}")
            raise VoiceError(f"Failed to create game channel: {e}")

    async def delete_channel(self, channel_id: int, reason: str = "Temporary channel cleanup") -> None:
        """Delete a voice channel by ID."""
        try:
            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                await channel.delete(reason=reason)
                # self.temporary_channels.discard(channel_id) # Remove from temp state
                logger.info(f"Deleted voice channel {channel.name} ({channel_id}). Reason: {reason}")
            elif channel:
                 logger.warning(f"Attempted to delete non-voice channel {channel_id} ({channel.type}).")
            else:
                 logger.warning(f"Attempted to delete non-existent channel {channel_id}.")
        except discord.errors.NotFound:
             logger.warning(f"Attempted to delete channel {channel_id}, but it was already deleted.")
             # self.temporary_channels.discard(channel_id) # Ensure cleanup from state
        except discord.errors.Forbidden:
             logger.error(f"Permission error deleting channel {channel_id}.")
             # Consider raising VoiceError or just logging
        except Exception as e:
            logger.exception(f"Error deleting channel {channel_id}: {e}")
            # Consider raising VoiceError or just logging

    async def _get_or_create_category(
        self,
        guild: discord.Guild,
        category_name: str
    ) -> Optional[discord.CategoryChannel]:
         """Gets or creates a category channel by name."""
         try:
              # Try to find existing category (case-insensitive search)
              for category in guild.categories:
                   if category.name.lower() == category_name.lower():
                        return category

              # Create new category if not found
              logger.info(f"Category '{category_name}' not found in guild {guild.id}, creating...")
              return await guild.create_category(
                   category_name,
                   reason=f"Auto-created category for {category_name}"
              )
         except discord.errors.Forbidden:
              logger.error(f"Permission error creating category '{category_name}' in guild {guild.id}")
              return None # Indicate failure due to permissions
         except Exception as e:
              logger.exception(f"Error getting/creating category '{category_name}' in guild {guild.id}: {e}")
              return None # Indicate general failure

    # --- Methods for Updating Unit Stat Channels ---

    async def _update_unit_channels_loop(self):
        """Main loop to update unit voice channel names periodically."""
        await self.bot.wait_until_ready()
        while self.running:
            try:
                logger.debug("Running periodic unit channel update check...")
                # Get all guilds that have at least one unit channel configured AND are marked as paid
                # Ensure guild_settings table has 'is_paid' column
                guilds_to_update = await self.db.fetch_all("""
                    SELECT guild_id, voice_channel_id, yearly_channel_id
                    FROM guild_settings
                    WHERE is_active = TRUE AND is_paid = TRUE
                    AND (voice_channel_id IS NOT NULL OR yearly_channel_id IS NOT NULL)
                """)

                update_tasks = []
                for guild_info in guilds_to_update:
                     # Create a task for each guild to update its channels
                     update_tasks.append(self._update_guild_unit_channels(guild_info))

                # Run updates concurrently
                if update_tasks:
                    await asyncio.gather(*update_tasks, return_exceptions=True) # Add return_exceptions=True to log errors

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
            monthly_total = await self._get_monthly_total_units(guild_id)
            await self._update_channel_name(monthly_ch_id, f"Monthly Units: {monthly_total:+.2f}") # Show sign +/-

        # Update yearly channel if configured
        if yearly_ch_id:
            yearly_total = await self._get_yearly_total_units(guild_id)
            await self._update_channel_name(yearly_ch_id, f"Yearly Units: {yearly_total:+.2f}") # Show sign +/-


    async def update_on_bet_resolve(self, guild_id: int):
        """Force update unit channels for a guild immediately after a bet resolves."""
        try:
            logger.info(f"Triggering unit channel update for guild {guild_id} due to bet resolution.")
            # Fetch guild settings, check if paid and channels configured
            guild_settings = await self.db.fetch_one("""
                 SELECT guild_id, voice_channel_id, yearly_channel_id, is_paid
                 FROM guild_settings
                 WHERE guild_id = $1 AND is_active = TRUE
            """, guild_id)

            if guild_settings and guild_settings.get('is_paid'):
                 # Directly call the update logic for this guild
                 await self._update_guild_unit_channels(guild_settings)
            else:
                 logger.debug(f"Skipping immediate update for guild {guild_id}: Not paid or no channels configured.")

        except Exception as e:
            logger.exception(f"Error updating voice channels on bet resolve for guild {guild_id}: {e}")


    async def _get_monthly_total_units(self, guild_id: int) -> float:
        """Get the total net units for the current month."""
        try:
            now = datetime.now(timezone.utc)
            # Assumes unit_records table stores results per bet
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(result_value), 0.0)
                FROM unit_records
                WHERE guild_id = $1 AND year = $2 AND month = $3
                """,
                guild_id, now.year, now.month
            )
            # fetchval returns the value directly or None
            return float(result) if result is not None else 0.0
        except Exception as e:
            logger.exception(f"Error getting monthly total units for guild {guild_id}: {e}")
            return 0.0


    async def _get_yearly_total_units(self, guild_id: int) -> float:
        """Get the total net units for the current year."""
        try:
            now = datetime.now(timezone.utc)
            # Assumes unit_records table stores results per bet
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
            return 0.0


    async def _update_channel_name(self, channel_id: int, new_name: str):
        """Safely update a voice channel's name, handling rate limits and errors."""
        try:
            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, discord.VoiceChannel):
                 # Check if name actually needs changing to avoid unnecessary API calls
                 # Discord normalizes channel names (e.g., lowercase, hyphens)
                 # We compare simply; Discord handles exact format on edit.
                 # Limit name length
                 trimmed_name = new_name[:100]
                 if channel.name != trimmed_name:
                      await channel.edit(name=trimmed_name, reason="Updating unit stats")
                      logger.debug(f"Updated channel {channel_id} name to '{trimmed_name}'")
                 else:
                      logger.debug(f"Channel {channel_id} name ('{channel.name}') already up-to-date. Skipping edit.")
            elif channel:
                 logger.warning(f"Channel ID {channel_id} is not a voice channel (type: {channel.type}). Cannot update name.")
            else:
                 logger.warning(f"Channel ID {channel_id} not found in bot cache. Cannot update name.")
        except discord.errors.RateLimited:
             logger.warning(f"Rate limited while trying to update channel {channel_id} name. Will retry later.")
             # The loop will naturally retry later. No specific action needed here.
        except discord.errors.NotFound:
             logger.warning(f"Channel {channel_id} not found during edit attempt (possibly deleted).")
             # TODO: Maybe mark this channel ID as invalid in guild_settings?
        except discord.errors.Forbidden:
             logger.error(f"Permission error updating channel {channel_id} name. Check bot permissions.")
             # TODO: Maybe disable updates for this channel/guild temporarily?
        except Exception as e:
            logger.exception(f"Error updating channel name for {channel_id}: {e}")

    # Removed methods related to managing historical totals (_monthly_total_loop, _yearly_total_loop)
    # as the core logic relies on SUMming unit_records. If historical tables like
    # monthly_totals/yearly_totals are needed for performance on very large datasets,
    # those loops would need to be added back, using self.db.

    # Removed unused/duplicate methods like get_voice_channel, create_voice_channel from original file context
    # if they are not used by the core unit channel update logic.
