"""Admin service for managing server settings and permissions."""

import discord
import logging
import aiosqlite
from typing import Dict, Any, Optional
from utils.errors import AdminServiceError
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'betting-bot/data/betting.db'

    async def setup_server(self, guild_id: int, settings: Dict[str, Any]) -> None:
        """Set up server settings."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO server_settings (
                        guild_id, embed_channel_1, command_channel_1, admin_channel_1,
                        admin_role, authorized_role, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, true)
                """, (
                    guild_id,
                    settings.get('embed_channel_1'),
                    settings.get('command_channel_1'),
                    settings.get('admin_channel_1'),
                    settings.get('admin_role'),
                    settings.get('authorized_role')
                ))
                await db.commit()
                logger.info(f"Server settings saved for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error setting up server {guild_id}: {e}")
            raise AdminServiceError(f"Failed to set up server: {str(e)}")

    async def get_server_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get server settings."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM server_settings WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"Error getting server settings for guild {guild_id}: {e}")
            raise AdminServiceError(f"Failed to get server settings: {str(e)}")

    async def sync_commands(self, guild_id: int) -> None:
        """Sync commands for a guild."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise AdminServiceError(f"Guild {guild_id} not found")
            await self.bot.tree.sync(guild=guild)
            logger.info(f"Commands synced for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error syncing commands for guild {guild_id}: {e}")
            raise AdminServiceError(f"Failed to sync commands: {str(e)}")

    async def is_guild_paid(self, guild_id: int) -> bool:
        """Check if a guild has a paid subscription."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT subscription_level FROM server_settings WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result and result[0] == 2  # 2 represents paid subscription
        except Exception as e:
            logger.error(f"Error checking guild subscription: {str(e)}")
            return False

    async def set_monthly_channel(self, guild_id: int, channel_id: int) -> bool:
        """Set the monthly unit tracking voice channel for a guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE server_settings SET voice_channel_id = ? WHERE guild_id = ?",
                    (channel_id, guild_id)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting monthly channel: {str(e)}")
            return False

    async def set_yearly_channel(self, guild_id: int, channel_id: int) -> bool:
        """Set the yearly unit tracking voice channel for a guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE server_settings SET yearly_channel_id = ? WHERE guild_id = ?",
                    (channel_id, guild_id)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting yearly channel: {str(e)}")
            return False

    async def remove_monthly_channel(self, guild_id: int) -> bool:
        """Remove the monthly unit tracking voice channel for a guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE server_settings SET voice_channel_id = NULL WHERE guild_id = ?",
                    (guild_id,)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing monthly channel: {str(e)}")
            return False

    async def remove_yearly_channel(self, guild_id: int) -> bool:
        """Remove the yearly unit tracking voice channel for a guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE server_settings SET yearly_channel_id = NULL WHERE guild_id = ?",
                    (guild_id,)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing yearly channel: {str(e)}")
            return False

    async def get_voice_channels(self, guild_id: int) -> tuple[Optional[int], Optional[int]]:
        """Get both voice channel IDs for a guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT voice_channel_id, yearly_channel_id FROM server_settings WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        return result[0], result[1]
                    return None, None
        except Exception as e:
            logger.error(f"Error getting voice channels: {str(e)}")
            return None, None 
