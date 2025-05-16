"""Sync command cog for manually syncing bot commands."""

import logging
import discord
from discord import app_commands
from discord.ext import commands
import asyncio

logger = logging.getLogger(__name__)

class SyncCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="sync", description="Manually sync bot commands (admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_command(self, interaction: discord.Interaction):
        logger.info(
            "Manual sync initiated by %s in guild %s",
            interaction.user, interaction.guild_id
        )
        try:
            await interaction.response.defer(ephemeral=True)
            commands_list = [cmd.name for cmd in self.bot.tree.get_commands()]
            logger.debug("Commands to sync: %s", commands_list)

            # Clear existing commands
            self.bot.tree.clear_commands(guild=None)
            
            # Register commands for Cookin' Books guild
            cookin_books_guild = discord.Object(id=1328126227013439601)
            self.bot.tree.clear_commands(guild=cookin_books_guild)
            
            # First sync global commands
            await self.bot.sync_commands_with_retry()
            
            # Copy global commands to Cookin' Books
            self.bot.tree.copy_global_to(guild=cookin_books_guild)
            
            # Sync guild commands for Cookin' Books
            await self.bot.tree.sync(guild=cookin_books_guild)

            await interaction.followup.send(
                "Commands synced successfully!", ephemeral=True
            )
        except Exception as e:
            logger.error("Failed to sync commands: %s", e, exc_info=True)
            if not interaction.response.is_done():
                 await interaction.response.send_message(f"Failed to sync commands: {e}",ephemeral=True)
            else:
                 await interaction.followup.send(f"Failed to sync commands: {e}",ephemeral=True)

async def setup_sync_cog(bot):
    """Setup function to register the SyncCog."""
    await bot.add_cog(SyncCog(bot))
    logger.info("SyncCog loaded") 