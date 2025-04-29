import asyncio
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
import discord
from discord import Embed, Color
from ..data.db_manager import DatabaseManager
from ..data.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class NotificationServiceError(Exception):
    """Base exception for notification service errors."""
    pass

class NotificationService:
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.cache = CacheManager()
        self.running = False
        self._notification_tasks: Dict[int, asyncio.Task] = {}  # guild_id -> task
        self._notification_queues: Dict[int, asyncio.Queue] = {}  # guild_id -> queue

    async def start(self) -> None:
        """Start the notification service."""
        try:
            self.running = True
            await self._load_notification_settings()
            logger.info("Notification service started successfully")
        except Exception as e:
            logger.error(f"Error starting notification service: {str(e)}")
            raise NotificationServiceError(f"Failed to start notification service: {str(e)}")

    async def stop(self) -> None:
        """Stop the notification service."""
        try:
            self.running = False
            for task in self._notification_tasks.values():
                task.cancel()
            self._notification_tasks.clear()
            self._notification_queues.clear()
            logger.info("Notification service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping notification service: {str(e)}")

    async def _load_notification_settings(self) -> None:
        """Load notification settings for all guilds."""
        try:
            guilds = await self.db.fetch(
                "SELECT guild_id FROM guild_settings WHERE is_active = true"
            )
            for guild in guilds:
                guild_id = guild['guild_id']
                self._notification_queues[guild_id] = asyncio.Queue()
                self._notification_tasks[guild_id] = asyncio.create_task(
                    self._process_notifications(guild_id)
                )
        except Exception as e:
            logger.error(f"Error loading notification settings: {str(e)}")

    async def _process_notifications(self, guild_id: int) -> None:
        """Process notifications for a specific guild."""
        queue = self._notification_queues[guild_id]
        while self.running:
            try:
                notification = await queue.get()
                await self._send_notification(guild_id, notification)
                queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing notification for guild {guild_id}: {str(e)}")
                await asyncio.sleep(1)

    async def _send_notification(
        self,
        guild_id: int,
        notification: Dict[str, Union[str, Embed, List[Embed]]]
    ) -> None:
        """Send a notification to the appropriate channels."""
        try:
            # Get notification settings for the guild
            settings = await self.db.fetch(
                """
                SELECT channel_id, notification_type, is_enabled
                FROM notification_settings
                WHERE guild_id = $1 AND is_enabled = true
                """,
                guild_id
            )

            for setting in settings:
                channel_id = setting['channel_id']
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue

                # Check if the notification type matches
                if setting['notification_type'] != notification.get('type'):
                    continue

                # Send the notification
                if isinstance(notification.get('content'), Embed):
                    await channel.send(embed=notification['content'])
                elif isinstance(notification.get('content'), list):
                    for embed in notification['content']:
                        await channel.send(embed=embed)
                else:
                    await channel.send(str(notification.get('content', '')))
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")

    async def send_bet_notification(
        self,
        guild_id: int,
        user_id: int,
        bet_details: Dict,
        result: Optional[str] = None
    ) -> None:
        """Send a notification about a bet."""
        try:
            user = self.bot.get_user(user_id)
            if not user:
                return

            embed = Embed(
                title="New Bet Placed" if not result else f"Bet {result.title()}",
                color=Color.green() if not result else (Color.green() if result == "won" else Color.red()),
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="League", value=bet_details.get('league', 'N/A'), inline=True)
            embed.add_field(name="Type", value=bet_details.get('bet_type', 'N/A'), inline=True)
            embed.add_field(name="Selection", value=bet_details.get('selection', 'N/A'), inline=True)
            embed.add_field(name="Units", value=f"{bet_details.get('units', 0):.2f}", inline=True)

            if result:
                embed.add_field(name="Result", value=result.title(), inline=True)
                embed.add_field(
                    name="Payout",
                    value=f"{bet_details.get('units', 0) * (1 if result == 'won' else -1):.2f}",
                    inline=True
                )

            await self._notification_queues[guild_id].put({
                'type': 'bet',
                'content': embed
            })
        except Exception as e:
            logger.error(f"Error sending bet notification: {str(e)}")

    async def send_game_notification(
        self,
        guild_id: int,
        game_details: Dict,
        event_type: str
    ) -> None:
        """Send a notification about a game event."""
        try:
            embed = Embed(
                title=f"Game Update: {event_type.title()}",
                color=Color.blue(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="Match",
                value=f"{game_details.get('home_team', 'N/A')} vs {game_details.get('away_team', 'N/A')}",
                inline=True
            )
            embed.add_field(name="League", value=game_details.get('league', 'N/A'), inline=True)
            embed.add_field(name="Score", value=game_details.get('score', 'N/A'), inline=True)
            embed.add_field(name="Time", value=game_details.get('time', 'N/A'), inline=True)
            embed.add_field(name="Status", value=game_details.get('status', 'N/A'), inline=True)

            if event_type == 'goal':
                embed.add_field(
                    name="Goal Scorer",
                    value=game_details.get('scorer', 'N/A'),
                    inline=True
                )
            elif event_type == 'card':
                embed.add_field(
                    name="Card",
                    value=f"{game_details.get('card_type', 'N/A')} - {game_details.get('player', 'N/A')}",
                    inline=True
                )

            await self._notification_queues[guild_id].put({
                'type': 'game',
                'content': embed
            })
        except Exception as e:
            logger.error(f"Error sending game notification: {str(e)}")

    async def send_system_notification(
        self,
        guild_id: int,
        title: str,
        message: str,
        level: str = "info"
    ) -> None:
        """Send a system notification."""
        try:
            color_map = {
                "info": Color.blue(),
                "warning": Color.yellow(),
                "error": Color.red(),
                "success": Color.green()
            }

            embed = Embed(
                title=title,
                description=message,
                color=color_map.get(level, Color.blue()),
                timestamp=datetime.utcnow()
            )

            await self._notification_queues[guild_id].put({
                'type': 'system',
                'content': embed
            })
        except Exception as e:
            logger.error(f"Error sending system notification: {str(e)}")

    async def configure_notification_channel(
        self,
        guild_id: int,
        channel_id: int,
        notification_type: str,
        is_enabled: bool
    ) -> None:
        """Configure a notification channel for a specific type."""
        try:
            await self.db.execute(
                """
                INSERT INTO notification_settings (guild_id, channel_id, notification_type, is_enabled)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, channel_id, notification_type) DO UPDATE
                SET is_enabled = $4
                """,
                guild_id, channel_id, notification_type, is_enabled
            )
        except Exception as e:
            logger.error(f"Error configuring notification channel: {str(e)}")
            raise NotificationServiceError(f"Failed to configure notification channel: {str(e)}")

    async def get_notification_settings(self, guild_id: int) -> List[Dict]:
        """Get notification settings for a guild."""
        try:
            return await self.db.fetch(
                """
                SELECT channel_id, notification_type, is_enabled
                FROM notification_settings
                WHERE guild_id = $1
                """,
                guild_id
            )
        except Exception as e:
            logger.error(f"Error getting notification settings: {str(e)}")
            return [] 