import discord
from discord import app_commands
import logging
from typing import Optional
from datetime import datetime, timedelta
from services.analytics_service import AnalyticsService
from utils.stats_image_generator import StatsImageGenerator
import aiosqlite
import os

logger = logging.getLogger(__name__)

class ChannelSelect(discord.ui.Select):
    def __init__(self, channels: list):
        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"ID: {channel.id}"
            ) for channel in channels
        ]
        super().__init__(
            placeholder="Select a channel",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.values[0])
            channel = interaction.guild.get_channel(channel_id)
            
            # Get the stats data from the view
            stats_data = self.view.stats_data
            is_server = self.view.is_server
            
            # Generate the stats image
            image_generator = StatsImageGenerator()
            image_path = await image_generator.generate_stats_image(
                stats_data=stats_data,
                is_server=is_server,
                guild_id=interaction.guild_id,
                user_id=self.view.selected_user_id,
                guild_image_mask=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            # Send the image to the selected channel
            file = discord.File(image_path, filename="stats.png")
            await channel.send(file=file)
            
            # Clean up the temporary file
            os.remove(image_path)
            
            await interaction.response.send_message(
                f"✅ Statistics image sent to {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error sending stats to channel: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to send statistics image. Check logs for details.",
                ephemeral=True
            )

class StatsView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.analytics_service = AnalyticsService(bot)
        self.guild_id = guild_id
        self.stats_data = None
        self.is_server = False
        self.selected_user_id = None

    @discord.ui.select(
        placeholder="Select a capper",
        options=[]  # Will be populated dynamically
    )
    async def select_capper(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            if select.values[0] == "server":
                # Get server-wide stats
                self.stats_data = await self.analytics_service.get_guild_stats(self.guild_id)
                self.is_server = True
                self.selected_user_id = None
            else:
                # Get individual capper stats
                self.selected_user_id = int(select.values[0])
                self.stats_data = await self.analytics_service.get_user_stats(self.guild_id, self.selected_user_id)
                self.is_server = False

            # Generate the stats image
            image_generator = StatsImageGenerator()
            image_path = await image_generator.generate_stats_image(
                stats_data=self.stats_data,
                is_server=self.is_server,
                guild_id=self.guild_id,
                user_id=self.selected_user_id,
                guild_image_mask=interaction.guild.icon.url if interaction.guild.icon else None
            )

            # Send the image
            file = discord.File(image_path, filename="stats.png")
            await interaction.response.send_message(file=file, ephemeral=True)

            # Clean up the temporary file
            os.remove(image_path)

        except Exception as e:
            logger.error(f"Error in stats command: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while generating statistics. Please try again later.",
                ephemeral=True
            )

    async def populate_cappers(self, interaction: discord.Interaction):
        """Populate the select menu with cappers from the guild."""
        try:
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                # Get all cappers from the guild
                async with db.execute(
                    """
                    SELECT user_id, username 
                    FROM cappers 
                    WHERE guild_id = ?
                    ORDER BY username
                    """,
                    (self.guild_id,)
                ) as cursor:
                    cappers = await cursor.fetchall()

                # Create options for the select menu
                options = []
                for capper in cappers:
                    user = interaction.guild.get_member(capper[0])
                    if user:
                        options.append(
                            discord.SelectOption(
                                label=user.display_name,
                                value=str(capper[0]),
                                description=f"View {user.display_name}'s stats"
                            )
                        )

                # Add Server option
                options.append(
                    discord.SelectOption(
                        label="Server",
                        value="server",
                        description="View overall server statistics"
                    )
                )

                # Update the select menu
                self.select_capper.options = options
        except Exception as e:
            logger.error(f"Error populating cappers: {str(e)}")
            raise

class Stats(discord.app_commands.Group):
    """Group of commands for statistics operations."""
    def __init__(self, bot):
        super().__init__(name="stats", description="Statistics commands")
        self.bot = bot
        self.analytics_service = AnalyticsService(bot)

    @app_commands.command(name="view", description="View betting statistics for cappers or the server")
    async def view(self, interaction: discord.Interaction):
        """View betting statistics."""
        try:
            # Check if the guild has access to the stats command
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                async with db.execute(
                    """
                    SELECT commands_registered 
                    FROM server_settings 
                    WHERE guild_id = ?
                    """,
                    (interaction.guild_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    if not result or not result[0]:
                        await interaction.response.send_message(
                            "❌ This server does not have access to the stats command. Please contact an admin.",
                            ephemeral=True
                        )
                        return

            view = StatsView(self.bot, interaction.guild_id)
            await view.populate_cappers(interaction)
            await interaction.response.send_message(
                "Select a capper to view their statistics:",
                view=view,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in stats command: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while processing the stats command.",
                ephemeral=True
            )

async def setup(bot):
    """Add the stats commands to the bot."""
    stats_group = Stats(bot)
    bot.tree.add_command(stats_group) 