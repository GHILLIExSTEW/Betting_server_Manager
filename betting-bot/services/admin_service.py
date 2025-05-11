# betting-bot/services/admin_service.py

"""Service for handling administrative commands and tasks."""

import logging
import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AdminServiceError(Exception):
    """Custom exception for admin service errors."""
    pass

class AdminService:
    def __init__(self, bot, db_manager):
        """
        Initialize the AdminService.

        Args:
            bot: The Discord bot instance.
            db_manager: The database manager instance.
        """
        self.bot = bot
        self.db_manager = db_manager
        logger.info("AdminService initialized")

    async def start(self):
        """Start the AdminService and perform any necessary setup."""
        logger.info("Starting AdminService")
        try:
            # Example: Perform initialization tasks
            logger.info("AdminService started successfully")
        except Exception as e:
            logger.error(f"Failed to start AdminService: {e}", exc_info=True)
            raise RuntimeError(f"Could not start AdminService: {str(e)}")

    async def stop(self):
        """Stop the AdminService and perform any necessary cleanup."""
        logger.info("Stopping AdminService")
        try:
            logger.info("AdminService stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop AdminService: {e}", exc_info=True)
            raise RuntimeError(f"Could not stop AdminService: {str(e)}")

    async def check_guild_subscription(self, guild_id: int) -> bool:
        """Check if a guild has an active paid subscription."""
        try:
            result = await self.db_manager.fetch_one(
                "SELECT is_paid FROM guild_settings WHERE guild_id = %s",
                guild_id
            )
            return bool(result and result.get('is_paid', False))
        except Exception as e:
            logger.error(f"Error checking guild subscription for {guild_id}: {e}")
            return False

    async def setup_guild(self, guild_id: int, settings: Dict[str, any]) -> bool:
        """Set up or update guild settings."""
        try:
            # Check if guild already exists
            existing = await self.db_manager.fetch_one(
                "SELECT * FROM guild_settings WHERE guild_id = %s",
                guild_id
            )

            if existing:
                # Update existing settings
                await self.db_manager.execute(
                    """
                    UPDATE guild_settings 
                    SET embed_channel_1 = %s,
                        embed_channel_2 = %s,
                        command_channel_1 = %s,
                        command_channel_2 = %s,
                        admin_channel_1 = %s,
                        admin_role = %s,
                        authorized_role = %s,
                        member_role = %s,
                        voice_channel_id = %s,
                        yearly_channel_id = %s,
                        daily_report_time = %s,
                        bot_name_mask = %s,
                        bot_image_mask = %s,
                        guild_background = %s,
                        guild_default_image = %s,
                        default_parlay_image = %s,
                        min_units = %s,
                        max_units = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE guild_id = %s
                    """,
                    settings.get('embed_channel_1'),
                    settings.get('embed_channel_2'),
                    settings.get('command_channel_1'),
                    settings.get('command_channel_2'),
                    settings.get('admin_channel_1'),
                    settings.get('admin_role'),
                    settings.get('authorized_role'),
                    settings.get('member_role'),
                    settings.get('voice_channel_id'),
                    settings.get('yearly_channel_id'),
                    settings.get('daily_report_time'),
                    settings.get('bot_name_mask'),
                    settings.get('bot_image_mask'),
                    settings.get('guild_background'),
                    settings.get('guild_default_image'),
                    settings.get('default_parlay_image'),
                    settings.get('min_units'),
                    settings.get('max_units'),
                    guild_id
                )
            else:
                # Insert new guild settings
                await self.db_manager.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id, embed_channel_1, embed_channel_2, command_channel_1,
                        command_channel_2, admin_channel_1, admin_role, authorized_role,
                        member_role, voice_channel_id, yearly_channel_id, daily_report_time,
                        bot_name_mask, bot_image_mask, guild_background, guild_default_image,
                        default_parlay_image, min_units, max_units, is_paid
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    guild_id,
                    settings.get('embed_channel_1'),
                    settings.get('embed_channel_2'),
                    settings.get('command_channel_1'),
                    settings.get('command_channel_2'),
                    settings.get('admin_channel_1'),
                    settings.get('admin_role'),
                    settings.get('authorized_role'),
                    settings.get('member_role'),
                    settings.get('voice_channel_id'),
                    settings.get('yearly_channel_id'),
                    settings.get('daily_report_time'),
                    settings.get('bot_name_mask'),
                    settings.get('bot_image_mask'),
                    settings.get('guild_background'),
                    settings.get('guild_default_image'),
                    settings.get('default_parlay_image'),
                    settings.get('min_units'),
                    settings.get('max_units'),
                    settings.get('is_paid', False)
                )

            return True
        except Exception as e:
            logger.error(f"Error setting up guild {guild_id}: {e}")
            return False

    async def get_guild_settings(self, guild_id: int) -> Optional[Dict[str, any]]:
        """Get guild settings."""
        try:
            return await self.db_manager.fetch_one(
                "SELECT * FROM guild_settings WHERE guild_id = %s",
                guild_id
            )
        except Exception as e:
            logger.error(f"Error getting guild settings for {guild_id}: {e}")
            return None

    async def update_guild_settings(self, guild_id: int, settings: Dict[str, any]) -> bool:
        """Update specific guild settings."""
        try:
            # Build dynamic update query based on provided settings
            set_clauses = []
            values = []
            for key, value in settings.items():
                if key != 'guild_id':  # Skip guild_id in SET clause
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            if not set_clauses:
                return False

            values.append(guild_id)  # Add guild_id for WHERE clause
            query = f"""
                UPDATE guild_settings 
                SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = %s
            """
            
            await self.db_manager.execute(query, *values)
            return True
        except Exception as e:
            logger.error(f"Error updating guild settings for {guild_id}: {e}")
            return False

class AdminCog(commands.Cog):
    def __init__(self, bot, admin_service):
        """
        Initialize the AdminCog.

        Args:
            bot: The Discord bot instance.
            admin_service: The AdminService instance.
        """
        self.bot = bot
        self.admin_service = admin_service
        logger.info("AdminCog loaded")

    @app_commands.command(name="setup", description="Set up guild settings (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction):
        """Set up guild settings in the database."""
        logger.info(f"Setup command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            query = """
                INSERT INTO guild_settings (guild_id, is_active, subscription_level)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE is_active = %s, subscription_level = %s
            """
            params = (interaction.guild_id, True, 0, True, 0)
            await self.bot.db_manager.execute(query, params)
            await interaction.response.send_message("Guild settings initialized successfully!", ephemeral=True)
            logger.debug(f"Guild settings set up for guild {interaction.guild_id}")
        except Exception as e:
            logger.error(f"Failed to set up guild settings for guild {interaction.guild_id}: {e}", exc_info=True)
            await interaction.response.send_message(f"Failed to set up guild settings: {str(e)}", ephemeral=True)

    @app_commands.command(name="setchannel", description="Set embed channel for bets (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setchannel_command(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the embed channel for bet postings."""
        logger.info(f"Setchannel command initiated by {interaction.user} in guild {interaction.guild_id} for channel {channel.id}")
        try:
            query = """
                UPDATE guild_settings
                SET embed_channel_1 = %s
                WHERE guild_id = %s
            """
            params = (channel.id, interaction.guild_id)
            await self.bot.db_manager.execute(query, params)
            await interaction.response.send_message(f"Embed channel set to {channel.mention}!", ephemeral=True)
            logger.debug(f"Embed channel set to {channel.id} for guild {interaction.guild_id}")
        except Exception as e:
            logger.error(f"Failed to set embed channel for guild {interaction.guild_id}: {e}", exc_info=True)
            await interaction.response.send_message(f"Failed to set embed channel: {str(e)}", ephemeral=True)

async def setup(bot):
    """Setup function to register the AdminCog."""
    admin_service = bot.admin_service
    await bot.add_cog(AdminCog(bot, admin_service))
    logger.info("AdminCog setup completed")
