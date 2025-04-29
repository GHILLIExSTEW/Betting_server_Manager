import discord
from discord import app_commands
import logging
from typing import Optional
import os
from datetime import datetime
import aiosqlite

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
            guild_logos_dir = f"bot/assets/logos/{interaction.guild.id}"
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
            async with aiosqlite.connect('bot/data/betting.db') as db:
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

class AdminView(discord.ui.View):
    def __init__(self, is_paid: bool = False):
        super().__init__(timeout=None)
        self.is_paid = is_paid

    @discord.ui.select(
        placeholder="Select an admin action",
        options=[
            discord.SelectOption(
                label="Configure Server Settings",
                value="configure_settings",
                description="Configure server settings and channels"
            ),
            discord.SelectOption(
                label="View Current Settings",
                value="view_settings",
                description="View current server configuration"
            )
        ]
    )
    async def select_action(self, interaction: discord.Interaction, select: discord.ui.Select):
        if select.values[0] == "configure_settings":
            view = ServerSettingsView(interaction.guild, self.is_paid)
            await interaction.response.send_message(
                "Starting server configuration...",
                ephemeral=True
            )
            await view.start_selection(interaction)
        elif select.values[0] == "view_settings":
            await self.handle_view_settings(interaction)

    async def handle_view_settings(self, interaction: discord.Interaction):
        """Handle viewing current server settings."""
        try:
            async with aiosqlite.connect('bot/data/betting.db') as db:
                async with db.execute(
                    "SELECT * FROM server_settings WHERE guild_id = ?",
                    (interaction.guild.id,)
                ) as cursor:
                    settings = await cursor.fetchone()
            
            if not settings:
                await interaction.response.send_message(
                    "No settings configured for this server.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="Server Settings",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # Add basic settings
            embed.add_field(
                name="Subscription Level",
                value="Premium" if settings[1] == 2 else "Free",
                inline=False
            )
            
            # Add channel settings
            channels = {
                "Embed Channel 1": settings[2],
                "Command Channel 1": settings[4],
                "Admin Channel": settings[6]
            }
            
            if settings[1] == 2:  # Premium features
                channels.update({
                    "Embed Channel 2": settings[3],
                    "Command Channel 2": settings[5],
                    "Voice Channel": settings[12],
                    "Yearly Channel": settings[13]
                })
            
            for name, channel_id in channels.items():
                if channel_id:
                    channel = interaction.guild.get_channel(int(channel_id))
                    embed.add_field(
                        name=name,
                        value=channel.mention if channel else "Not set",
                        inline=True
                    )
            
            # Add role settings
            roles = {
                "Admin Role": settings[7],
                "Authorized Role": settings[8]
            }
            
            if settings[1] == 2:  # Premium features
                roles["Member Role"] = settings[9]
            
            for name, role_id in roles.items():
                if role_id:
                    role = interaction.guild.get_role(int(role_id))
                    embed.add_field(
                        name=name,
                        value=role.mention if role else "Not set",
                        inline=True
                    )
            
            if settings[1] == 2:  # Premium features
                embed.add_field(
                    name="Daily Report Time",
                    value=settings[10] or "Not set",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error viewing settings: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to view settings. Check logs for details.",
                ephemeral=True
            )

async def setup(tree: app_commands.CommandTree):
    """Setup function for the admin command."""
    @tree.command(
        name="admin",
        description="Admin commands for system management"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin(interaction: discord.Interaction):
        """Admin command for system management."""
        try:
            # Check if guild is in test guild for special actions
            is_test_guild = interaction.guild.id == int(os.getenv('TEST_GUILD_ID'))
            
            # Check subscription status (you'll need to implement this)
            is_paid = await check_subscription_status(interaction.guild.id)
            
            view = AdminView(is_paid)
            await interaction.response.send_message(
                "Select an admin action:",
                view=view,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in admin command: {str(e)}")
            await interaction.response.send_message(
                "An error occurred while processing the admin command.",
                ephemeral=True
            )

async def check_subscription_status(guild_id: int) -> bool:
    """Check if a guild has a paid subscription."""
    # Implement subscription check logic
    return False  # Default to free tier 