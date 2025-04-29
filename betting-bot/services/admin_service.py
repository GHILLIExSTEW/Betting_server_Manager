import logging
import aiosqlite
from typing import Optional

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, bot, db_path: str = 'bot/data/betting.db'):
        self.bot = bot
        self.db_path = db_path

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