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

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.errors import AdminServiceError

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
    def __init__(self, guild: discord.Guild, is_paid: bool = False):
        super().__init__(timeout=None)
        self.guild = guild
        self.is_paid = is_paid
        self.settings = {}
        self.current_step = 0
        self.text_channels = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
        self.roles = [r for r in guild.roles if r.id != guild.id]
        
        # Define selection steps
        self.steps = [
            # Free tier steps
            ("Select Embed Channel 1", "embed_channel_1", self.text_channels, ChannelSelect),
            ("Select Command Channel 1", "command_channel_1", self.text_channels, ChannelSelect),
            ("Select Admin Channel", "admin_channel_1", self.text_channels, ChannelSelect),
            ("Select Admin Role", "admin_role", self.roles, RoleSelect),
            ("Select Authorized Role", "authorized_role", self.roles, RoleSelect),
        ]
        
        # Add paid tier steps
        if is_paid:
            self.steps.extend([
                ("Select Embed Channel 2", "embed_channel_2", self.text_channels, ChannelSelect),
                ("Select Command Channel 2", "command_channel_2", self.text_channels, ChannelSelect),
                ("Select Voice Channel", "voice_channel_id", self.text_channels, ChannelSelect),
                ("Select Yearly Channel", "yearly_channel_id", self.text_channels, ChannelSelect),
                ("Select Member Role", "member_role", self.roles, RoleSelect),
            ])

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
            # All selections complete, show time input for paid users
            if self.is_paid:
                await self.show_time_input(interaction)
            else:
                await self.save_settings(interaction)

    async def show_time_input(self, interaction: discord.Interaction):
        self.clear_items()
        self.time_input = discord.ui.TextInput(
            label="Daily Report Time",
            placeholder="Enter time in HH:MM format",
            required=True
        )
        self.add_item(self.time_input)
        await interaction.followup.send(
            "**Set Daily Report Time**",
            view=self,
            ephemeral=True
        )
        # After time input, show URL inputs for paid users
        await self.show_url_inputs(interaction)

    async def show_url_inputs(self, interaction: discord.Interaction):
        self.clear_items()
        self.bot_name_mask = discord.ui.TextInput(
            label="Bot Name Mask",
            placeholder="Enter bot name mask",
            required=True
        )
        self.bot_image_mask = discord.ui.TextInput(
            label="Bot Image Mask",
            placeholder="Enter bot image mask URL",
            required=True
        )
        self.guild_default_image = discord.ui.TextInput(
            label="Guild Default Image",
            placeholder="Enter default image URL",
            required=True
        )
        self.default_parlay_thumbnail = discord.ui.TextInput(
            label="Default Parlay Thumbnail",
            placeholder="Enter parlay thumbnail URL",
            required=True
        )
        
        self.add_item(self.bot_name_mask)
        self.add_item(self.bot_image_mask)
        self.add_item(self.guild_default_image)
        self.add_item(self.default_parlay_thumbnail)
        
        await interaction.followup.send(
            "**Set Bot and Image Settings**",
            view=self,
            ephemeral=True
        )

    async def save_settings(self, interaction: discord.Interaction):
        try:
            # Create guild directory for logos
            guild_logos_dir = f"betting-bot/assets/logos/{interaction.guild.id}"
            os.makedirs(guild_logos_dir, exist_ok=True)
            logger.info(f"Created guild logos directory: {guild_logos_dir}")

            # Validate time format for paid users
            if self.is_paid and hasattr(self, 'time_input'):
                try:
                    datetime.strptime(self.time_input.value, '%H:%M')
                except ValueError:
                    await interaction.followup.send(
                        "❌ Invalid time format. Use HH:MM.",
                        ephemeral=True
                    )
                    return

            # Validate URLs for paid users
            if self.is_paid:
                urls = [
                    self.bot_image_mask.value,
                    self.guild_default_image.value,
                    self.default_parlay_thumbnail.value
                ]
                for url in urls:
                    if not url.startswith(('http://', 'https://')):
                        await interaction.followup.send(
                            "❌ Invalid URL format. URLs must start with http:// or https://",
                            ephemeral=True
                        )
                        return

            # Save settings to database
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                # Check if guild exists in settings
                async with db.execute(
                    "SELECT guild_id FROM server_settings WHERE guild_id = ?",
                    (interaction.guild.id,)
                ) as cursor:
                    exists = await cursor.fetchone()
                
                if exists:
                    # Update existing settings
                    query = """
                        UPDATE server_settings SET
                        commands_registered = ?,
                        embed_channel_1 = ?,
                        command_channel_1 = ?,
                        admin_channel_1 = ?,
                        admin_role = ?,
                        authorized_role = ?
                    """
                    params = [
                        2 if self.is_paid else 1,
                        self.settings.get('embed_channel_1'),
                        self.settings.get('command_channel_1'),
                        self.settings.get('admin_channel_1'),
                        self.settings.get('admin_role'),
                        self.settings.get('authorized_role')
                    ]
                    
                    if self.is_paid:
                        query += """,
                            embed_channel_2 = ?,
                            command_channel_2 = ?,
                            member_role = ?,
                            daily_report_time = ?,
                            voice_channel_id = ?,
                            yearly_channel_id = ?,
                            bot_name_mask = ?,
                            bot_image_mask = ?,
                            guild_default_image = ?,
                            default_parlay_thumbnail = ?
                        """
                        params.extend([
                            self.settings.get('embed_channel_2'),
                            self.settings.get('command_channel_2'),
                            self.settings.get('member_role'),
                            self.time_input.value,
                            self.settings.get('voice_channel_id'),
                            self.settings.get('yearly_channel_id'),
                            self.bot_name_mask.value,
                            self.bot_image_mask.value,
                            self.guild_default_image.value,
                            self.default_parlay_thumbnail.value
                        ])
                    
                    query += " WHERE guild_id = ?"
                    params.append(interaction.guild.id)
                else:
                    # Insert new settings
                    query = """
                        INSERT INTO server_settings (
                            guild_id, commands_registered,
                            embed_channel_1, command_channel_1,
                            admin_channel_1, admin_role, authorized_role
                    """
                    params = [
                        interaction.guild.id,
                        2 if self.is_paid else 1,
                        self.settings.get('embed_channel_1'),
                        self.settings.get('command_channel_1'),
                        self.settings.get('admin_channel_1'),
                        self.settings.get('admin_role'),
                        self.settings.get('authorized_role')
                    ]
                    
                    if self.is_paid:
                        query += """,
                            embed_channel_2, command_channel_2,
                            member_role, daily_report_time,
                            voice_channel_id, yearly_channel_id,
                            bot_name_mask, bot_image_mask,
                            guild_default_image, default_parlay_thumbnail
                        """
                        params.extend([
                            self.settings.get('embed_channel_2'),
                            self.settings.get('command_channel_2'),
                            self.settings.get('member_role'),
                            self.time_input.value,
                            self.settings.get('voice_channel_id'),
                            self.settings.get('yearly_channel_id'),
                            self.bot_name_mask.value,
                            self.bot_image_mask.value,
                            self.guild_default_image.value,
                            self.default_parlay_thumbnail.value
                        ])
                    
                    query += ") VALUES (" + ",".join(["?"] * len(params)) + ")"
                
                await db.execute(query, params)
                await db.commit()

            await interaction.followup.send(
                "✅ Server settings updated successfully!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            await interaction.followup.send(
                "❌ Failed to save settings. Check logs for details.",
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
    def __init__(self, admin_service: AdminService):
        super().__init__()
        self.admin_service = admin_service
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

async def setup(bot: commands.Bot):
    admin_service = AdminService()
    
    @bot.tree.command(name="admin", description="Admin commands for server management")
    @app_commands.default_permissions(administrator=True)
    async def admin(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return
            
        view = AdminView(admin_service)
        await interaction.response.send_message("Select an action:", view=view, ephemeral=True)

async def check_subscription_status(guild_id: int) -> bool:
    """Check if a guild has a paid subscription."""
    # Implement subscription check logic
    return False  # Default to free tier 