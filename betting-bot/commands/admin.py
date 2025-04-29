"""Admin command for server setup and management."""

import discord
from discord import app_commands
import logging
from typing import Optional, List
import os
from datetime import datetime
import aiosqlite
from services.admin_service import AdminService
from discord.ui import View, Select, Modal, TextInput
from discord.ext import commands
import sys
from utils.errors import AdminServiceError

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

class ChannelSelect(discord.ui.Select):
    def __init__(self, channels: list, placeholder: str, setting_key: str):
        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"ID: {channel.id}"
            ) for channel in channels
        ]
        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1
        )
        self.setting_key = setting_key

    async def callback(self, interaction: discord.Interaction):
        self.view.settings[self.setting_key] = self.values[0]
        await interaction.response.defer()
        await self.view.process_next_selection(interaction)

class RoleSelect(discord.ui.Select):
    def __init__(self, roles: list, placeholder: str, setting_key: str):
        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                description=f"ID: {role.id}"
            ) for role in roles
        ]
        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1
        )
        self.setting_key = setting_key

    async def callback(self, interaction: discord.Interaction):
        self.view.settings[self.setting_key] = self.values[0]
        await interaction.response.defer()
        await self.view.process_next_selection(interaction)

class ServerSettingsView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild
        self.settings = {}
        self.current_step = 0
        self.text_channels = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
        self.roles = [r for r in guild.roles if r.id != guild.id]
        
        # Define selection steps
        self.steps = [
            ("Select Embed Channel", "embed_channel_1", self.text_channels, ChannelSelect),
            ("Select Command Channel", "command_channel_1", self.text_channels, ChannelSelect),
            ("Select Admin Channel", "admin_channel_1", self.text_channels, ChannelSelect),
            ("Select Admin Role", "admin_role", self.roles, RoleSelect),
            ("Select Authorized Role", "authorized_role", self.roles, RoleSelect),
        ]

    async def start_selection(self, interaction: discord.Interaction):
        await self.process_next_selection(interaction)

    async def process_next_selection(self, interaction: discord.Interaction):
        if self.current_step < len(self.steps):
            title, setting_key, items, SelectClass = self.steps[self.current_step]
            self.clear_items()
            self.add_item(SelectClass(items, title, setting_key))
            await interaction.followup.send(
                f"**{title}**",
                view=self,
                ephemeral=True
            )
            self.current_step += 1
        else:
            await self.save_settings(interaction)

    async def save_settings(self, interaction: discord.Interaction):
        try:
            # Create guild directory for logos
            guild_logos_dir = f"betting-bot/assets/logos/{interaction.guild.id}"
            os.makedirs(guild_logos_dir, exist_ok=True)
            logger.info(f"Created guild logos directory: {guild_logos_dir}")

            # Save settings using admin service
            admin_service = AdminService(interaction.client)
            await admin_service.setup_server(interaction.guild_id, self.settings)

            # Sync commands
            await admin_service.sync_commands(interaction.guild_id)

            await interaction.followup.send(
                "✅ Server setup completed successfully!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error saving server settings: {e}")
            await interaction.followup.send(
                "❌ An error occurred while saving settings. Please try again.",
                ephemeral=True
            )

class VoiceChannelSelect(Select):
    def __init__(self, channels: List[discord.VoiceChannel]):
        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"ID: {channel.id}"
            ) for channel in channels
        ]
        super().__init__(
            placeholder="Select a voice channel...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_channel_id = int(self.values[0])
        await interaction.response.defer()
        self.view.stop()

class AdminView(View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.admin_service = AdminService(bot)
        self.selected_channel = None

    @discord.ui.select(
        placeholder="Select an action...",
        options=[
            discord.SelectOption(label="Set Monthly Channel", value="set_monthly"),
            discord.SelectOption(label="Set Yearly Channel", value="set_yearly"),
            discord.SelectOption(label="Remove Monthly Channel", value="remove_monthly"),
            discord.SelectOption(label="Remove Yearly Channel", value="remove_yearly")
        ]
    )
    async def select_action(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return

        guild_id = interaction.guild_id
        is_paid = await self.admin_service.is_guild_paid(guild_id)
        if not is_paid:
            await interaction.response.send_message("This feature is only available for paid guilds.", ephemeral=True)
            return

        action = select.values[0]
        
        if action in ["set_monthly", "set_yearly"]:
            voice_channels = [channel for channel in interaction.guild.voice_channels]
            if not voice_channels:
                await interaction.response.send_message("No voice channels found in this server.", ephemeral=True)
                return
            
            channel_select = VoiceChannelSelect(voice_channels)
            channel_select.callback = self.handle_channel_selection
            self.selected_channel = action
            
            view = View()
            view.add_item(channel_select)
            await interaction.response.send_message("Select a voice channel:", view=view, ephemeral=True)
        else:
            if action == "remove_monthly":
                success = await self.admin_service.remove_monthly_channel(guild_id)
                message = "Monthly channel removed successfully." if success else "Failed to remove monthly channel."
            else:
                success = await self.admin_service.remove_yearly_channel(guild_id)
                message = "Yearly channel removed successfully." if success else "Failed to remove yearly channel."
            
            await interaction.response.send_message(message, ephemeral=True)

    async def handle_channel_selection(self, interaction: discord.Interaction):
        channel_id = int(interaction.data["values"][0])
        guild_id = interaction.guild_id
        
        if self.selected_channel == "set_monthly":
            success = await self.admin_service.set_monthly_channel(guild_id, channel_id)
            message = "Monthly channel set successfully." if success else "Failed to set monthly channel."
        else:
            success = await self.admin_service.set_yearly_channel(guild_id, channel_id)
            message = "Yearly channel set successfully." if success else "Failed to set yearly channel."
        
        await interaction.response.send_message(message, ephemeral=True)

async def setup(bot):
    """Add the admin command to the bot."""
    @bot.tree.command(
        name="admin",
        description="Set up server settings and sync commands"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin(interaction: discord.Interaction):
        """Set up server settings and sync commands."""
        try:
            view = ServerSettingsView(interaction.guild)
            await interaction.response.send_message(
                "Let's set up your server! Follow the steps below:",
                view=view,
                ephemeral=True
            )
            await view.start_selection(interaction)
        except Exception as e:
            logger.error(f"Error in admin command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )

async def check_subscription_status(guild_id: int) -> bool:
    """Check if a guild has a paid subscription."""
    # Implement subscription check logic
    return False  # Default to free tier 