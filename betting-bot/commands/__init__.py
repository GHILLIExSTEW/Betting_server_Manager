# This file makes the commands directory a Python package 

import discord
from discord import app_commands
from typing import List, Type
import logging
from .betting import Betting
from .stats import Stats
from .admin import Admin
from .capper_management import CapperManagement
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
            CapperManagement,
            SetID
        ]
    
    async def register_commands(self):
        """Register all commands with the bot's command tree."""
        try:
            # Clear global commands
            self.bot.tree.clear_commands(guild=None)
            
            # Register each command group globally
            for group_class in self.command_groups:
                group = group_class(self.bot)
                self.bot.tree.add_command(group)
                logger.info(f"Registered command group: {group.name}")
            
            # Sync commands with Discord
            await self.bot.tree.sync()
            logger.info("Successfully synced all commands with Discord")
            
        except Exception as e:
            logger.error(f"Error registering commands: {str(e)}")
            raise

async def setup(bot):
    """Setup function for all commands."""
    command_manager = CommandManager(bot)
    await command_manager.register_commands() 