# betting-bot/services/admin_service.py

"""Admin service for managing server settings and permissions."""

import discord
import logging
# import aiosqlite # Remove direct usage if using db_manager
from typing import Dict, Any, Optional, Tuple
# Assuming DatabaseManager type hint comes from the correct path
# If db_manager is passed, don't need to import it here unless for type hinting
# from data.db_manager import DatabaseManager # Example path

# Use relative imports assuming services/ is sibling to utils/
try:
    from ..utils.errors import AdminServiceError
except ImportError:
    from utils.errors import AdminServiceError # Fallback

logger = logging.getLogger(__name__)

class AdminService:
    # Corrected __init__ signature
    def __init__(self, bot, db_manager): # Accept bot and the shared db_manager
        """Initializes the Admin Service.

        Args:
            bot: The discord bot instance.
            db_manager: The shared DatabaseManager instance.
        """
        self.bot = bot
        self.db = db_manager # Use the passed-in db_manager instance
        # self.db_path = '...' # Path is no longer needed here


    async def setup_server(self, guild_id: int, settings: Dict[str, Any]) -> None:
        """Set up or update server settings using the shared db_manager.

        Args:
            guild_id: The ID of the guild to set up.
            settings: A dictionary containing settings like channel and role IDs.

        Raises:
            AdminServiceError: If saving settings fails.
        """
        try:
            # Use self.db (DatabaseManager instance)
            # Use $ placeholders for asyncpg (PostgreSQL)
            # Use ON CONFLICT...DO UPDATE for atomic insert/update
            # Ensure all columns from your schema are included with defaults for INSERT
            # Ensure EXCLUDED.column syntax for UPDATE part
            await self.db.execute("""
                INSERT INTO guild_settings (
                    guild_id, embed_channel_1, command_channel_1, admin_channel_1,
                    admin_role, authorized_role, is_active, subscription_level, is_paid,
                    voice_channel_id, yearly_channel_id, total_units_channel_id -- Add voice channel cols
                ) VALUES ($1, $2, $3, $4, $5, $6, TRUE, 0, FALSE, NULL, NULL, NULL) -- Provide defaults
                ON CONFLICT (guild_id) DO UPDATE SET
                    embed_channel_1 = EXCLUDED.embed_channel_1,
                    command_channel_1 = EXCLUDED.command_channel_1,
                    admin_channel_1 = EXCLUDED.admin_channel_1,
                    admin_role = EXCLUDED.admin_role,
                    authorized_role = EXCLUDED.authorized_role,
                    is_active = TRUE -- Optionally reset other fields on update if needed
            """,
                guild_id,
                # Use .get() with default None for optional settings, cast to int if ID
                int(settings['embed_channel_1']) if settings.get('embed_channel_1') else None,
                int(settings['command_channel_1']) if settings.get('command_channel_1') else None,
                int(settings['admin_channel_1']) if settings.get('admin_channel_1') else None,
                int(settings['admin_role']) if settings.get('admin_role') else None,
                int(settings['authorized_role']) if settings.get('authorized_role') else None
            )
            logger.info(f"Server settings saved/updated for guild {guild_id}")
        except Exception as e:
            logger.exception(f"Error setting up server {guild_id}: {e}")
            raise AdminServiceError(f"Failed to set up server: {str(e)}")


    async def get_server_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get server settings using the shared db_manager.

        Args:
            guild_id: The ID of the guild.

        Returns:
            A dictionary containing the server settings, or None if not found or error.
        """
        try:
            # Use self.db (DatabaseManager instance)
            settings_dict = await self.db.fetch_one(
                # Select all columns from the guild_settings table
                "SELECT * FROM guild_settings WHERE guild_id = $1",
                guild_id
            )
            return settings_dict # Already returns a dict or None from db_manager
        except Exception as e:
            logger.exception(f"Error getting server settings for guild {guild_id}: {e}")
            # Return None to indicate settings not found or error occurred
            return None


    async def sync_commands(self, guild_id: int) -> None:
        """Sync application commands for a specific guild.

        Args:
            guild_id: The ID of the guild to sync commands for.

        Raises:
            AdminServiceError: If syncing fails due to non-permission errors.
        """
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.error(f"Cannot sync commands: Guild {guild_id} not found in bot's cache.")
                # Don't raise an error, as the bot might just not see the guild yet.
                return

            # Assuming self.bot.tree is the CommandTree instance initialized in the bot class
            await self.bot.tree.sync(guild=guild)
            logger.info(f"Commands synced for guild {guild.name} ({guild_id})")
        except discord.errors.Forbidden:
             logger.error(f"Permission error syncing commands for guild {guild_id}. Bot might lack 'application.commands' scope or necessary permissions in that guild.")
             # You might want to inform the admin who ran the setup command if possible.
        except Exception as e:
            logger.exception(f"Unexpected error syncing commands for guild {guild_id}: {e}")
            raise AdminServiceError(f"Failed to sync commands: {str(e)}")


    async def is_guild_paid(self, guild_id: int) -> bool:
        """Check if a guild has a paid subscription using the shared db_manager.

        Args:
            guild_id: The ID of the guild.

        Returns:
            True if the guild is marked as paid, False otherwise or on error.
        """
        try:
            # Check the 'is_paid' column (BOOLEAN/BIT type in DB)
            result = await self.db.fetch_one(
                "SELECT is_paid FROM guild_settings WHERE guild_id = $1",
                guild_id
            )
            # Returns dict or None. Check if result exists and is_paid is True.
            # The fetch_one should return {'is_paid': True} or {'is_paid': False} or None
            return bool(result and result.get('is_paid'))
        except Exception as e:
            logger.exception(f"Error checking guild subscription status for guild {guild_id}: {e}")
            return False # Default to False on error for safety


    async def set_monthly_channel(self, guild_id: int, channel_id: Optional[int]) -> bool:
        """Set the monthly unit tracking voice channel using the shared db_manager.

        Args:
            guild_id: The ID of the guild.
            channel_id: The ID of the voice channel, or None to remove it.

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            # Column name is 'voice_channel_id' based on schema discussions
            status = await self.db.execute(
                "UPDATE guild_settings SET voice_channel_id = $1 WHERE guild_id = $2",
                channel_id, guild_id
            )
            # Check if the execute command indicated an update occurred
            success = status is not None and 'UPDATE 1' in status
            if success:
                 action = "set" if channel_id else "removed"
                 logger.info(f"Successfully {action} monthly channel ({channel_id}) for guild {guild_id}")
            else:
                 logger.warning(f"Failed to update monthly channel for guild {guild_id}. Guild settings might not exist or value unchanged.")
            return success
        except Exception as e:
            logger.exception(f"Error setting/removing monthly channel for guild {guild_id}: {e}")
            return False


    async def set_yearly_channel(self, guild_id: int, channel_id: Optional[int]) -> bool:
        """Set the yearly unit tracking voice channel using the shared db_manager.

        Args:
            guild_id: The ID of the guild.
            channel_id: The ID of the voice channel, or None to remove it.

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            status = await self.db.execute(
                "UPDATE guild_settings SET yearly_channel_id = $1 WHERE guild_id = $2",
                channel_id, guild_id
            )
            success = status is not None and 'UPDATE 1' in status
            if success:
                 action = "set" if channel_id else "removed"
                 logger.info(f"Successfully {action} yearly channel ({channel_id}) for guild {guild_id}")
            else:
                 logger.warning(f"Failed to update yearly channel for guild {guild_id}. Guild settings might not exist or value unchanged.")
            return success
        except Exception as e:
            logger.exception(f"Error setting/removing yearly channel for guild {guild_id}: {e}")
            return False


    async def remove_monthly_channel(self, guild_id: int) -> bool:
        """Remove the monthly unit tracking voice channel setting for a guild.

        Args:
            guild_id: The ID of the guild.

        Returns:
            True if the update was successful, False otherwise.
        """
        # Setting the channel ID to NULL effectively removes it
        return await self.set_monthly_channel(guild_id, None)


    async def remove_yearly_channel(self, guild_id: int) -> bool:
        """Remove the yearly unit tracking voice channel setting for a guild.

        Args:
            guild_id: The ID of the guild.

        Returns:
            True if the update was successful, False otherwise.
        """
        # Setting the channel ID to NULL effectively removes it
        return await self.set_yearly_channel(guild_id, None)


    async def get_voice_channels(self, guild_id: int) -> Tuple[Optional[int], Optional[int]]:
        """Get the configured monthly and yearly voice channel IDs for a guild.

        Args:
            guild_id: The ID of the guild.

        Returns:
            A tuple containing (monthly_channel_id, yearly_channel_id).
            Values can be None if not set or if an error occurs.
        """
        try:
            result = await self.db.fetch_one(
                # Select the specific columns needed
                "SELECT voice_channel_id, yearly_channel_id FROM guild_settings WHERE guild_id = $1",
                guild_id
            )
            if result:
                # Access by key name, assuming db_manager returns dicts
                monthly_id = result.get('voice_channel_id')
                yearly_id = result.get('yearly_channel_id')
                return monthly_id, yearly_id
            else:
                # Guild settings row not found for this guild_id
                logger.debug(f"No guild settings found for guild {guild_id} when getting voice channels.")
                return None, None
        except Exception as e:
            logger.exception(f"Error getting voice channels for guild {guild_id}: {e}")
            # Return None tuple on error to indicate failure
            return None, None
