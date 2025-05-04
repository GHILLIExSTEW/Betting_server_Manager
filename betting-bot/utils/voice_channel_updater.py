import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import aiosqlite
from discord import VoiceChannel, Client

logger = logging.getLogger(__name__)

class VoiceChannelUpdater:
    def __init__(self, bot: Client, db_path: str):
        self.bot = bot
        self.db_path = db_path
        self.running = False
        self._update_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the voice channel update service."""
        self.running = True
        self._update_task = asyncio.create_task(self._update_loop())
        logger.info("Voice channel updater started")

    async def stop(self):
        """Stop the voice channel update service."""
        self.running = False
        if self._update_task:
            self._update_task.cancel()
        logger.info("Voice channel updater stopped")

    async def _update_loop(self):
        """Main update loop that runs every 5 minutes."""
        while self.running:
            try:
                await self.update_all_channels()
                await asyncio.sleep(300)  # 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in voice channel update loop: {str(e)}")
                await asyncio.sleep(300)

    async def update_all_channels(self):
        """Update all voice channels for all guilds."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get all guilds with voice channels configured
                async with db.execute(
                    """
                    SELECT guild_id, voice_channel_id, yearly_channel_id, is_paid
                    FROM guild_settings
                    WHERE voice_channel_id IS NOT NULL OR yearly_channel_id IS NOT NULL
                    """
                ) as cursor:
                    guilds = await cursor.fetchall()

                for guild in guilds:
                    guild_id, voice_channel_id, yearly_channel_id, is_paid = guild
                    
                    if not is_paid:
                        continue

                    # Update monthly channel if configured
                    if voice_channel_id:
                        monthly_total = await self._get_monthly_total(db, guild_id)
                        await self._update_channel_name(voice_channel_id, f"Monthly Units: {monthly_total}")

                    # Update yearly channel if configured
                    if yearly_channel_id:
                        yearly_total = await self._get_yearly_total(db, guild_id)
                        await self._update_channel_name(yearly_channel_id, f"Yearly Units: {yearly_total}")

        except Exception as e:
            logger.error(f"Error updating voice channels: {str(e)}")

    async def update_on_bet_resolve(self, guild_id: int):
        """Update voice channels when a bet is resolved."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get guild settings
                async with db.execute(
                    """
                    SELECT voice_channel_id, yearly_channel_id, is_paid
                    FROM guild_settings
                    WHERE guild_id = ?
                    """,
                    (guild_id,)
                ) as cursor:
                    guild = await cursor.fetchone()

                if not guild or not guild[2]:  # Not paid
                    return

                voice_channel_id, yearly_channel_id, _ = guild

                # Update monthly channel if configured
                if voice_channel_id:
                    monthly_total = await self._get_monthly_total(db, guild_id)
                    await self._update_channel_name(voice_channel_id, f"Monthly Units: {monthly_total}")

                # Update yearly channel if configured
                if yearly_channel_id:
                    yearly_total = await self._get_yearly_total(db, guild_id)
                    await self._update_channel_name(yearly_channel_id, f"Yearly Units: {yearly_total}")

        except Exception as e:
            logger.error(f"Error updating voice channels on bet resolve: {str(e)}")

    async def _get_monthly_total(self, db: aiosqlite.Connection, guild_id: int) -> float:
        """Get the total units for the current month."""
        try:
            now = datetime.utcnow()
            start_of_month = datetime(now.year, now.month, 1)
            
            async with db.execute(
                """
                SELECT COALESCE(SUM(result_value), 0.0) as total
                FROM unit_records
                WHERE guild_id = ? AND year = ? AND month = ?
                """,
                (guild_id, now.year, now.month)
            ) as cursor:
                result = await cursor.fetchone()
                return result['total'] if result and result['total'] is not None else 0.0
        except Exception as e:
            logger.error(f"Error getting monthly total: {str(e)}")
            return 0.0

    async def _get_yearly_total(self, db: aiosqlite.Connection, guild_id: int) -> float:
        """Get the total units for the current year."""
        try:
            now = datetime.utcnow()
            
            async with db.execute(
                """
                SELECT COALESCE(SUM(result_value), 0.0) as total
                FROM unit_records
                WHERE guild_id = ? AND year = ?
                """,
                (guild_id, now.year)
            ) as cursor:
                result = await cursor.fetchone()
                return result['total'] if result and result['total'] is not None else 0.0
        except Exception as e:
            logger.error(f"Error getting yearly total: {str(e)}")
            return 0.0

    async def _update_channel_name(self, channel_id: int, new_name: str):
        """Update a voice channel's name."""
        try:
            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, VoiceChannel):
                await channel.edit(name=new_name)
        except Exception as e:
            logger.error(f"Error updating channel name: {str(e)}")

    async def handle_month_end(self):
        """Handle end of month tasks."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get all guilds
                async with db.execute(
                    """
                    SELECT guild_id, voice_channel_id, yearly_channel_id, is_paid
                    FROM guild_settings
                    """
                ) as cursor:
                    guilds = await cursor.fetchall()

                for guild in guilds:
                    guild_id, voice_channel_id, yearly_channel_id, is_paid = guild
                    
                    if not is_paid:
                        continue

                    # Reset monthly units
                    await db.execute(
                        """
                        UPDATE unit_records
                        SET monthly_result_value = 0
                        WHERE guild_id = ?
                        """,
                        (guild_id,)
                    )

                    # Update voice channel to show reset
                    if voice_channel_id:
                        await self._update_channel_name(voice_channel_id, "Monthly Units: 0")

                await db.commit()
        except Exception as e:
            logger.error(f"Error handling month end: {str(e)}")

    async def handle_year_end(self):
        """Handle end of year tasks."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get all guilds
                async with db.execute(
                    """
                    SELECT guild_id, yearly_channel_id, is_paid
                    FROM guild_settings
                    """
                ) as cursor:
                    guilds = await cursor.fetchall()

                for guild in guilds:
                    guild_id, yearly_channel_id, is_paid = guild
                    
                    if not is_paid:
                        continue

                    # Get yearly total
                    yearly_total = await self._get_yearly_total(db, guild_id)

                    # Update subscribers table
                    await db.execute(
                        """
                        UPDATE subscribers
                        SET year_total = ?,
                            lifetime_units = lifetime_units + ?
                        WHERE guild_id = ?
                        """,
                        (yearly_total, yearly_total, guild_id)
                    )

                    # Reset yearly total
                    await db.execute(
                        """
                        UPDATE unit_records
                        SET total_result_value = 0
                        WHERE guild_id = ?
                        """,
                        (guild_id,)
                    )

                    # Update voice channel to show reset
                    if yearly_channel_id:
                        await self._update_channel_name(yearly_channel_id, "Yearly Units: 0")

                await db.commit()
        except Exception as e:
            logger.error(f"Error handling year end: {str(e)}") 