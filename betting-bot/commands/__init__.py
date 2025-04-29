# This file makes the commands directory a Python package 

import discord
from discord import app_commands
import logging
import os

logger = logging.getLogger(__name__)

class CommandManager:
    """Manages the registration and synchronization of all bot commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def register_commands(self):
        """Register all commands with the bot's command tree."""
        try:
            # Get test guild ID from environment
            test_guild_id = int(os.getenv('TEST_GUILD_ID', 0))
            
            # Clear global commands
            self.bot.tree.clear_commands(guild=None)
            logger.info("Cleared all global commands")
            
            # Clear test guild commands if guild ID is provided
            if test_guild_id:
                self.bot.tree.clear_commands(guild=discord.Object(id=test_guild_id))
                logger.info(f"Cleared all commands for test guild {test_guild_id}")
            
            # Import and register each command
            from .admin import setup as setup_admin
            from .setid import setup as setup_setid
            from .betting import setup as setup_betting
            from .stats import setup as setup_stats
            from .load_logos import setup as setup_load_logos
            from .remove_user import setup as setup_remove_user
            
            await setup_admin(self.bot)
            await setup_setid(self.bot)
            await setup_betting(self.bot)
            await setup_stats(self.bot)
            await setup_load_logos(self.bot.tree)
            await setup_remove_user(self.bot)
            
            # Sync commands with Discord
            await self.bot.tree.sync()
            if test_guild_id:
                await self.bot.tree.sync(guild=discord.Object(id=test_guild_id))
            logger.info("Successfully synced all commands with Discord")
            
        except Exception as e:
            logger.error(f"Error registering commands: {str(e)}")
            raise

async def setup(bot):
    """Setup function for all commands."""
    command_manager = CommandManager(bot)
    await command_manager.register_commands() 