import discord
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import asyncio
from discord import VoiceChannel
from ..data.db_manager import DatabaseManager
from ..data.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class VoiceServiceError(Exception):
    """Base exception for voice service errors."""
    pass

class VoiceService:
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.cache = CacheManager()
        self.running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self.active_channels: Dict[int, Dict] = {}  # guild_id -> channel_info
        self.temporary_channels: Set[int] = set()  # channel_ids
        self._update_task: Optional[asyncio.Task] = None
        self._monthly_total_task: Optional[asyncio.Task] = None
        self._yearly_total_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the voice service."""
        try:
            self.running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_channels())
            self._update_task = asyncio.create_task(self._update_loop())
            self._monthly_total_task = asyncio.create_task(self._monthly_total_loop())
            self._yearly_total_task = asyncio.create_task(self._yearly_total_loop())
            logger.info("Voice service started successfully")
        except Exception as e:
            logger.error(f"Error starting voice service: {str(e)}")
            raise VoiceServiceError(f"Failed to start voice service: {str(e)}")

    async def stop(self) -> None:
        """Stop the voice service."""
        try:
            self.running = False
            if self._cleanup_task:
                self._cleanup_task.cancel()
            if self._update_task:
                self._update_task.cancel()
            if self._monthly_total_task:
                self._monthly_total_task.cancel()
            if self._yearly_total_task:
                self._yearly_total_task.cancel()
            self.active_channels.clear()
            self.temporary_channels.clear()
            logger.info("Voice service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping voice service: {str(e)}")

    async def create_game_channel(
        self,
        guild_id: int,
        game_id: int,
        game_name: str,
        category_id: Optional[int] = None
    ) -> discord.VoiceChannel:
        """Create a voice channel for a specific game."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise VoiceServiceError(f"Guild {guild_id} not found")

            # Get or create category
            category = None
            if category_id:
                category = guild.get_channel(category_id)
            if not category:
                category = await self._get_or_create_game_category(guild)

            # Create voice channel
            channel = await guild.create_voice_channel(
                name=f"🎮 {game_name}",
                category=category,
                reason=f"Game channel for {game_name}"
            )

            # Store channel info
            self.active_channels[guild_id] = {
                'game_id': game_id,
                'channel_id': channel.id,
                'created_at': datetime.utcnow()
            }

            # Add to temporary channels
            self.temporary_channels.add(channel.id)

            return channel
        except Exception as e:
            logger.error(f"Error creating game channel: {str(e)}")
            raise VoiceServiceError(f"Failed to create game channel: {str(e)}")

    async def create_betting_channel(
        self,
        guild_id: int,
        game_id: int,
        game_name: str,
        category_id: Optional[int] = None
    ) -> discord.VoiceChannel:
        """Create a voice channel for betting discussions."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise VoiceServiceError(f"Guild {guild_id} not found")

            # Get or create category
            category = None
            if category_id:
                category = guild.get_channel(category_id)
            if not category:
                category = await self._get_or_create_betting_category(guild)

            # Create voice channel
            channel = await guild.create_voice_channel(
                name=f"💰 {game_name} Bets",
                category=category,
                reason=f"Betting channel for {game_name}"
            )

            # Store channel info
            self.active_channels[guild_id] = {
                'game_id': game_id,
                'channel_id': channel.id,
                'created_at': datetime.utcnow()
            }

            # Add to temporary channels
            self.temporary_channels.add(channel.id)

            return channel
        except Exception as e:
            logger.error(f"Error creating betting channel: {str(e)}")
            raise VoiceServiceError(f"Failed to create betting channel: {str(e)}")

    async def delete_channel(self, channel_id: int) -> None:
        """Delete a voice channel."""
        try:
            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                await channel.delete(reason="Game or betting session ended")
                self.temporary_channels.discard(channel_id)
        except Exception as e:
            logger.error(f"Error deleting channel: {str(e)}")
            raise VoiceServiceError(f"Failed to delete channel: {str(e)}")

    async def move_member(
        self,
        member_id: int,
        channel_id: int,
        guild_id: int
    ) -> None:
        """Move a member to a specific voice channel."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise VoiceServiceError(f"Guild {guild_id} not found")

            member = guild.get_member(member_id)
            if not member:
                raise VoiceServiceError(f"Member {member_id} not found")

            channel = guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                raise VoiceServiceError(f"Channel {channel_id} not found")

            await member.move_to(channel)
        except Exception as e:
            logger.error(f"Error moving member: {str(e)}")
            raise VoiceServiceError(f"Failed to move member: {str(e)}")

    async def _get_or_create_game_category(
        self,
        guild: discord.Guild
    ) -> discord.CategoryChannel:
        """Get or create the game category."""
        try:
            # Try to find existing category
            for category in guild.categories:
                if category.name == "🎮 Games":
                    return category

            # Create new category
            return await guild.create_category(
                "🎮 Games",
                reason="Game category for voice channels"
            )
        except Exception as e:
            logger.error(f"Error getting/creating game category: {str(e)}")
            raise VoiceServiceError(f"Failed to get/create game category: {str(e)}")

    async def _get_or_create_betting_category(
        self,
        guild: discord.Guild
    ) -> discord.CategoryChannel:
        """Get or create the betting category."""
        try:
            # Try to find existing category
            for category in guild.categories:
                if category.name == "💰 Betting":
                    return category

            # Create new category
            return await guild.create_category(
                "💰 Betting",
                reason="Betting category for voice channels"
            )
        except Exception as e:
            logger.error(f"Error getting/creating betting category: {str(e)}")
            raise VoiceServiceError(f"Failed to get/create betting category: {str(e)}")

    async def _cleanup_channels(self) -> None:
        """Periodically clean up empty temporary channels."""
        while self.running:
            try:
                for channel_id in list(self.temporary_channels):
                    channel = self.bot.get_channel(channel_id)
                    if channel and isinstance(channel, discord.VoiceChannel):
                        # Check if channel is empty
                        if len(channel.members) == 0:
                            # Check if channel is old enough to delete
                            guild_id = channel.guild.id
                            if guild_id in self.active_channels:
                                channel_info = self.active_channels[guild_id]
                                if (datetime.utcnow() - channel_info['created_at']) > timedelta(hours=1):
                                    await self.delete_channel(channel_id)

                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in channel cleanup: {str(e)}")
                await asyncio.sleep(300)

    async def _get_current_month_units(self, guild_id: int) -> float:
        """Get total units for the current month."""
        try:
            now = datetime.utcnow()
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(units), 0)
                FROM unit_records
                WHERE guild_id = $1 AND year = $2 AND month = $3
                """,
                guild_id, now.year, now.month
            )
            return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Error getting current month units: {str(e)}")
            return 0.0

    async def _get_yearly_units(self, guild_id: int) -> float:
        """Get total units for the current year."""
        try:
            now = datetime.utcnow()
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(units), 0)
                FROM unit_records
                WHERE guild_id = $1 AND year = $2
                """,
                guild_id, now.year
            )
            return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Error getting yearly units: {str(e)}")
            return 0.0

    async def _calculate_monthly_total(self, guild_id: int, year: int, month: int) -> float:
        """Calculate total units for a specific month."""
        try:
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(units), 0)
                FROM unit_records
                WHERE guild_id = $1 AND year = $2 AND month = $3
                """,
                guild_id, year, month
            )
            return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Error calculating monthly total: {str(e)}")
            return 0.0

    async def _update_monthly_total(self, guild_id: int, year: int, month: int) -> None:
        """Update the monthly total in the database."""
        try:
            total = await self._calculate_monthly_total(guild_id, year, month)
            await self.db.execute(
                """
                INSERT INTO monthly_totals (guild_id, year, month, total)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, year, month) DO UPDATE
                SET total = $4
                """,
                guild_id, year, month, total
            )
        except Exception as e:
            logger.error(f"Error updating monthly total: {str(e)}")

    async def _check_past_months_totals(self, guild_id: int) -> None:
        """Check and update missing monthly totals."""
        try:
            now = datetime.utcnow()
            # Get all months that need updating
            months = await self.db.fetch(
                """
                SELECT DISTINCT year, month
                FROM unit_records
                WHERE guild_id = $1
                AND (year < $2 OR (year = $2 AND month < $3))
                EXCEPT
                SELECT year, month
                FROM monthly_totals
                WHERE guild_id = $1
                """,
                guild_id, now.year, now.month
            )
            
            for month in months:
                await self._update_monthly_total(guild_id, month['year'], month['month'])
        except Exception as e:
            logger.error(f"Error checking past months totals: {str(e)}")

    async def _update_yearly_totals(self, guild_id: int, year: int) -> None:
        """Update yearly totals in the database."""
        try:
            # Calculate total for the year
            total = await self._calculate_yearly_total(guild_id, year)
            
            # Update yearly total
            await self.db.execute(
                """
                INSERT INTO yearly_totals (guild_id, year, total)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, year) DO UPDATE
                SET total = $3
                """,
                guild_id, year, total
            )
        except Exception as e:
            logger.error(f"Error updating yearly totals: {str(e)}")

    async def _calculate_yearly_total(self, guild_id: int, year: int) -> float:
        """Calculate total units for a specific year."""
        try:
            result = await self.db.fetchval(
                """
                SELECT COALESCE(SUM(units), 0)
                FROM unit_records
                WHERE guild_id = $1 AND year = $2
                """,
                guild_id, year
            )
            return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Error calculating yearly total: {str(e)}")
            return 0.0

    async def _get_total_units_channel(self, guild_id: int) -> Optional[VoiceChannel]:
        """Get the configured total units voice channel."""
        try:
            channel_id = await self.db.fetchval(
                "SELECT total_units_channel_id FROM guild_settings WHERE guild_id = $1",
                guild_id
            )
            if channel_id:
                return self.bot.get_channel(channel_id)
            return None
        except Exception as e:
            logger.error(f"Error getting total units channel: {str(e)}")
            return None

    async def _get_yearly_channel(self, guild_id: int) -> Optional[VoiceChannel]:
        """Get the configured yearly units voice channel."""
        try:
            channel_id = await self.db.fetchval(
                "SELECT yearly_units_channel_id FROM guild_settings WHERE guild_id = $1",
                guild_id
            )
            if channel_id:
                return self.bot.get_channel(channel_id)
            return None
        except Exception as e:
            logger.error(f"Error getting yearly channel: {str(e)}")
            return None

    async def _is_premium_guild(self, guild_id: int) -> bool:
        """Check if a guild has premium subscription."""
        try:
            result = await self.db.fetchval(
                "SELECT is_premium FROM guild_settings WHERE guild_id = $1",
                guild_id
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking premium status: {str(e)}")
            return False

    async def _update_all_guilds(self) -> None:
        """Update voice channels for all configured guilds."""
        try:
            guilds = await self.db.fetch(
                "SELECT guild_id FROM guild_settings WHERE is_active = true"
            )
            
            for guild in guilds:
                guild_id = guild['guild_id']
                if await self._is_premium_guild(guild_id):
                    # Update total units channel
                    total_channel = await self._get_total_units_channel(guild_id)
                    if total_channel:
                        current_total = await self._get_current_month_units(guild_id)
                        await total_channel.edit(name=f"Total Units: {current_total:.2f}")
                    
                    # Update yearly channel
                    yearly_channel = await self._get_yearly_channel(guild_id)
                    if yearly_channel:
                        yearly_total = await self._get_yearly_units(guild_id)
                        await yearly_channel.edit(name=f"Yearly Units: {yearly_total:.2f}")
        except Exception as e:
            logger.error(f"Error updating all guilds: {str(e)}")

    async def _update_loop(self) -> None:
        """Main loop to update voice channel names periodically."""
        while self.running:
            try:
                await self._update_all_guilds()
                await asyncio.sleep(300)  # Update every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in update loop: {str(e)}")
                await asyncio.sleep(300)

    async def _monthly_total_loop(self) -> None:
        """Periodic loop to check/update past monthly totals."""
        while self.running:
            try:
                guilds = await self.db.fetch(
                    "SELECT guild_id FROM guild_settings WHERE is_active = true"
                )
                for guild in guilds:
                    await self._check_past_months_totals(guild['guild_id'])
                await asyncio.sleep(3600)  # Check every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monthly total loop: {str(e)}")
                await asyncio.sleep(3600)

    async def _yearly_total_loop(self) -> None:
        """Periodic loop to update current yearly totals."""
        while self.running:
            try:
                now = datetime.utcnow()
                guilds = await self.db.fetch(
                    "SELECT guild_id FROM guild_settings WHERE is_active = true"
                )
                for guild in guilds:
                    await self._update_yearly_totals(guild['guild_id'], now.year)
                await asyncio.sleep(3600)  # Update every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in yearly total loop: {str(e)}")
                await asyncio.sleep(3600) 