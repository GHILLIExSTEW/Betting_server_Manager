# betting-bot/services/admin_service.py

"""Service for handling administrative commands and tasks."""

import logging
import discord
from discord.ext import commands
from discord import app_commands

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

    async def setup_guild(self, guild_id: int, settings: dict):
        """Set up guild settings in the database.
        
        Args:
            guild_id: The Discord guild ID.
            settings: Dictionary of settings to save.
        """
        logger.info(f"Setting up guild {guild_id} with settings: {settings}")
        try:
            # Build the update query dynamically based on provided settings
            set_clauses = []
            params = []
            
            for key, value in settings.items():
                set_clauses.append(f"{key} = %s")
                params.append(value)
            
            # Add guild_id to params
            params.append(guild_id)
            
            query = f"""
                INSERT INTO guild_settings (guild_id, {', '.join(settings.keys())})
                VALUES (%s, {', '.join(['%s'] * len(settings))})
                ON DUPLICATE KEY UPDATE {', '.join(set_clauses)}
            """
            
            await self.db_manager.execute(query, params)
            logger.info(f"Guild settings updated for guild {guild_id}")
        except Exception as e:
            logger.error(f"Failed to set up guild settings for guild {guild_id}: {e}", exc_info=True)
            raise AdminServiceError(f"Failed to set up guild settings: {str(e)}")

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
