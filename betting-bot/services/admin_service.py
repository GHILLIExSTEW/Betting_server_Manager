# betting-bot/services/admin_service.py

"""Admin service for managing server settings and permissions."""

import discord
import logging
from typing import Dict, Any, Optional, Tuple

# Use relative imports assuming services/ is sibling to utils/
try:
    from ..utils.errors import AdminServiceError
except ImportError:
    from utils.errors import AdminServiceError

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager

    async def setup_server(self, guild_id: int, settings: Dict[str, Any]) -> None:
        """Set up or update server settings using the shared db_manager."""
        try:
            # Convert IDs safely
            embed_ch_id = int(settings['embed_channel_1']) if settings.get('embed_channel_1') else None
            command_ch_id = int(settings['command_channel_1']) if settings.get('command_channel_1') else None
            admin_ch_id = int(settings['admin_channel_1']) if settings.get('admin_channel_1') else None
            admin_role_id = int(settings['admin_role']) if settings.get('admin_role') else None
            auth_role_id = int(settings['authorized_role']) if settings.get('authorized_role') else None

            # Use %s placeholders and MySQL's ON DUPLICATE KEY UPDATE
            await self.db.execute("""
                INSERT INTO guild_settings (
                    guild_id, embed_channel_1, command_channel_1, admin_channel_1,
                    admin_role, authorized_role, is_active, subscription_level, is_paid,
                    voice_channel_id, yearly_channel_id, total_units_channel_id, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, TRUE, 0, FALSE, NULL, NULL, NULL, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    embed_channel_1 = VALUES(embed_channel_1),
                    command_channel_1 = VALUES(command_channel_1),
                    admin_channel_1 = VALUES(admin_channel_1),
                    admin_role = VALUES(admin_role),
                    authorized_role = VALUES(authorized_role),
                    is_active = TRUE,
                    updated_at = NOW()
            """,
                guild_id,
                embed_ch_id,
                command_ch_id,
                admin_ch_id,
                admin_role_id,
                auth_role_id
            )
            logger.info(f"Server settings saved/updated for guild {guild_id}")
        except Exception as e:
            logger.exception(f"Error setting up server {guild_id}: {e}")
            raise AdminServiceError(f"Failed to set up server: {str(e)}")

    async def get_server_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get server settings using the shared db_manager."""
        try:
            settings_dict = await self.db.fetch_one(
                "SELECT * FROM guild_settings WHERE guild_id = %s",
                guild_id
            )
            return settings_dict
        except Exception as e:
            logger.exception(f"Error getting server settings for guild {guild_id}: {e}")
            return None

    async def sync_commands(self, guild_id: int) -> None:
        """Sync commands for a guild using the Discord API."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.error(f"Cannot sync commands: Guild {guild_id} not found.")
                return
            await self.bot.tree.sync(guild=guild)
            logger.info(f"Commands synced for guild {guild.name} ({guild_id})")
        except discord.errors.Forbidden:
            logger.error(f"Permission error syncing commands for guild {guild_id}.")
        except Exception as e:
            logger.exception(f"Unexpected error syncing commands for guild {guild_id}: {e}")
            raise AdminServiceError(f"Failed to sync commands: {str(e)}")

    async def is_guild_paid(self, guild_id: int) -> bool:
        """Check if a guild has a paid subscription using the shared db_manager."""
        try:
            result = await self.db.fetch_one(
                "SELECT is_paid FROM guild_settings WHERE guild_id = %s",
                guild_id
            )
            return bool(result and result.get('is_paid'))
        except Exception as e:
            logger.exception(f"Error checking guild subscription status for guild {guild_id}: {e}")
            return False

    async def set_monthly_channel(self, guild_id: int, channel_id: Optional[int]) -> bool:
        """Set the monthly unit tracking voice channel using the shared db_manager."""
        try:
            status = await self.db.execute(
                "UPDATE guild_settings SET voice_channel_id = %s, updated_at = NOW() WHERE guild_id = %s",
                channel_id, guild_id
            )
            success = status is not None and status > 0
            if success:
                action = "set" if channel_id else "removed"
                logger.info(f"Successfully {action} monthly channel ({channel_id}) for guild {guild_id}")
            else:
                logger.warning(f"Failed to update monthly channel for guild {guild_id}. Guild settings might not exist or value unchanged. Rows affected: {status}")
            return success
        except Exception as e:
            logger.exception(f"Error setting/removing monthly channel for guild {guild_id}: {e}")
            return False

    async def set_yearly_channel(self, guild_id: int, channel_id: Optional[int]) -> bool:
        """Set the yearly unit tracking voice channel using the shared db_manager."""
        try:
            status = await self.db.execute(
                "UPDATE guild_settings SET yearly_channel_id = %s, updated_at = NOW() WHERE guild_id = %s",
                channel_id, guild_id
            )
            success = status is not None and status > 0
            if success:
                action = "set" if channel_id else "removed"
                logger.info(f"Successfully {action} yearly channel ({channel_id}) for guild {guild_id}")
            else:
                logger.warning(f"Failed to update yearly channel for guild {guild_id}. Guild settings might not exist or value unchanged. Rows affected: {status}")
            return success
        except Exception as e:
            logger.exception(f"Error setting/removing yearly channel for guild {guild_id}: {e}")
            return False

    async def remove_monthly_channel(self, guild_id: int) -> bool:
        """Remove the monthly unit tracking voice channel setting for a guild."""
        return await self.set_monthly_channel(guild_id, None)

    async def remove_yearly_channel(self, guild_id: int) -> bool:
        """Remove the yearly unit tracking voice channel setting for a guild."""
        return await self.set_yearly_channel(guild_id, None)

    async def get_voice_channels(self, guild_id: int) -> Tuple[Optional[int], Optional[int]]:
        """Get the configured monthly and yearly voice channel IDs for a guild."""
        try:
            result = await self.db.fetch_one(
                "SELECT voice_channel_id, yearly_channel_id FROM guild_settings WHERE guild_id = %s",
                guild_id
            )
            if result:
                monthly_id = result.get('voice_channel_id')
                yearly_id = result.get('yearly_channel_id')
                return monthly_id, yearly_id
            else:
                logger.debug(f"No guild settings found for guild {guild_id} when getting voice channels.")
                return None, None
        except Exception as e:
            logger.exception(f"Error getting voice channels for guild {guild_id}: {e}")
            return None, None
