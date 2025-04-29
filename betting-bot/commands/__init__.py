# This file makes the commands directory a Python package 

import discord
from discord import app_commands
from typing import List, Type
import logging
import os
from .betting import Betting
from .stats import Stats
from .admin import Admin
from .setid import SetID

logger = logging.getLogger(__name__)

class CommandManager:
    """Manages the registration and synchronization of all bot commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.command_groups: List[Type[discord.app_commands.Group]] = [
            Betting,
            Stats,
            Admin,
            SetID
        ]
    
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
            
            # Register each command group globally
            for group_class in self.command_groups:
                group = group_class(self.bot)
                self.bot.tree.add_command(group)
                logger.info(f"Registered command group: {group.name}")
            
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