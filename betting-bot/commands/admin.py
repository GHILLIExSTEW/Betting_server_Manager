# betting-bot/commands/admin.py

"""Admin commands for server setup and management."""

import discord
from discord import app_commands, Interaction, SelectOption, TextChannel, Role, VoiceChannel
from discord.ext import commands # Import commands for Cog
from discord.ui import View, Select, Modal, TextInput
import logging
import os
from typing import Optional, List

# Use relative imports (assuming commands/ is sibling to services/, utils/)
try:
    # Services will be accessed via self.bot.<service_name>
    from ..services.admin_service import AdminService # Explicitly import AdminService type hint if needed
    from ..utils.errors import AdminServiceError
except ImportError:
    # Fallbacks
    from services.admin_service import AdminService
    from utils.errors import AdminServiceError


logger = logging.getLogger(__name__)

# --- UI Components ---

class ChannelSelect(discord.ui.Select):
    """Select menu for choosing text channels."""
    def __init__(self, channels: List[TextChannel], placeholder: str, setting_key: str, max_options=25):
        options = [
            discord.SelectOption(
                label=f"#{channel.name}", # Add # prefix
                value=str(channel.id),
                description=f"ID: {channel.id}"
            )[:100] for channel in channels[:max_options] # Limit options and description length
        ]
        if not options: # Handle case with no channels
             options.append(discord.SelectOption(label="No Text Channels Found", value="none", emoji="❌"))

        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1,
            disabled=not options or options[0].value == "none" # Disable if no channels
        )
        self.setting_key = setting_key

    async def callback(self, interaction: discord.Interaction):
        # Ensure the view attribute exists and has settings
        if not hasattr(self.view, 'settings'):
            logger.error("Parent view or settings dictionary not found in ChannelSelect.")
            await interaction.response.send_message("Error processing selection.", ephemeral=True)
            return

        selected_value = self.values[0]
        if selected_value == "none":
             await interaction.response.defer() # Acknowledge but do nothing else
             return

        self.view.settings[self.setting_key] = selected_value
        await interaction.response.defer()

        # Ensure the view attribute exists and has the method
        if hasattr(self.view, 'process_next_selection'):
            await self.view.process_next_selection(interaction)
        else:
            logger.error("process_next_selection method not found in parent view.")
            # Use followup because response was deferred
            await interaction.followup.send("Error proceeding to next step.", ephemeral=True)


class RoleSelect(discord.ui.Select):
    """Select menu for choosing roles."""
    def __init__(self, roles: List[Role], placeholder: str, setting_key: str, max_options=25):
        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                description=f"ID: {role.id}"
            )[:100] for role in roles[:max_options] # Limit options and description length
        ]
        if not options: # Handle case with no roles
             options.append(discord.SelectOption(label="No Roles Found (Except @everyone)", value="none", emoji="❌"))

        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1,
            disabled=not options or options[0].value == "none" # Disable if no roles
        )
        self.setting_key = setting_key

    async def callback(self, interaction: discord.Interaction):
        # Ensure the view attribute exists and has settings
        if not hasattr(self.view, 'settings'):
            logger.error("Parent view or settings dictionary not found in RoleSelect.")
            await interaction.response.send_message("Error processing selection.", ephemeral=True)
            return

        selected_value = self.values[0]
        if selected_value == "none":
             await interaction.response.defer() # Acknowledge but do nothing else
             return

        self.view.settings[self.setting_key] = selected_value
        await interaction.response.defer()

        # Ensure the view attribute exists and has the method
        if hasattr(self.view, 'process_next_selection'):
            await self.view.process_next_selection(interaction)
        else:
            logger.error("process_next_selection method not found in parent view.")
            # Use followup because response was deferred
            await interaction.followup.send("Error proceeding to next step.", ephemeral=True)


class SubscriptionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Free Tier Information")
        self.add_item(discord.ui.TextInput(
            label="Free Tier Details",
            style=discord.TextStyle.paragraph,
            placeholder="Please enjoy our free tier service as long as you like, however your server is limited to 4 active bets at a time, and all premium services will be locked out. For only $19.99 a month, your server can have access to two embed channels, two command channels, an admin channel, unit tracking monthly and yearly, bot avatar masks, custom user avatar masks, a daily report, and custom guild background image for your bet slips. Subscribe today to unlock the full power of the Bet Embed Generator!",
            required=True,
            default="Please enjoy our free tier service as long as you like, however your server is limited to 4 active bets at a time, and all premium services will be locked out. For only $19.99 a month, your server can have access to two embed channels, two command channels, an admin channel, unit tracking monthly and yearly, bot avatar masks, custom user avatar masks, a daily report, and custom guild background image for your bet slips. Subscribe today to unlock the full power of the Bet Embed Generator!"
        ))

class SubscriptionView(discord.ui.View):
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.original_interaction = interaction

    @discord.ui.button(label="Subscribe", style=discord.ButtonStyle.green)
    async def subscribe(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TODO: Implement subscription page redirect
        await interaction.response.send_message("Redirecting to subscription page...", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Continue with Free Tier", style=discord.ButtonStyle.grey)
    async def continue_free(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        view = GuildSettingsView(self.bot, interaction, is_paid=False)
        await view.start_selection()
        self.stop()

class GuildSettingsView(discord.ui.View):
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction, is_paid: bool = False, is_image_setup: bool = False):
        super().__init__(timeout=300)
        self.bot = bot
        self.original_interaction = interaction
        self.guild = interaction.guild
        self.settings = {}
        self.current_step = 0
        self.is_paid = is_paid
        self.is_image_setup = is_image_setup
        
        # Filter channels/roles accessible by the bot and sort them
        self.text_channels = sorted(
            [c for c in self.guild.text_channels if c.permissions_for(self.guild.me).view_channel],
            key=lambda c: c.position
        )
        self.voice_channels = sorted(
            [c for c in self.guild.voice_channels if c.permissions_for(self.guild.me).view_channel],
            key=lambda c: c.position
        )
        self.roles = sorted(
            [r for r in self.guild.roles if r.id != self.guild.id and not r.is_default()],
            key=lambda r: r.position,
            reverse=True
        )

        # Define steps based on tier and setup type
        if is_image_setup:
            self.steps = [
                ("Set Guild Background Image URL", "guild_background", None, None),
                ("Set Default Image URL", "guild_default_image", None, None),
                ("Set Default Parlay Image URL", "default_parlay_thumbnail", None, None)
            ]
        else:
            self.steps = []
            # Free tier steps
            self.steps.extend([
                ("Select Embed Channel", "embed_channel_1", self.text_channels, ChannelSelect),
                ("Select Command Channel", "command_channel_1", self.text_channels, ChannelSelect),
                ("Select Admin Channel", "admin_channel_1", self.text_channels, ChannelSelect),
                ("Select Admin Role", "admin_role", self.roles, RoleSelect),
                ("Select Authorized Role (Capper Role)", "authorized_role", self.roles, RoleSelect),
                ("Select Member Role", "member_role", self.roles, RoleSelect)
            ])
            
            # Paid tier additional steps
            if is_paid:
                self.steps.extend([
                    ("Select Second Embed Channel", "embed_channel_2", self.text_channels, ChannelSelect),
                    ("Select Second Command Channel", "command_channel_2", self.text_channels, ChannelSelect),
                    ("Select Voice Channel for Monthly Updates", "voice_channel_id", self.voice_channels, VoiceChannelSelect),
                    ("Select Voice Channel for Yearly Updates", "yearly_channel_id", self.voice_channels, VoiceChannelSelect),
                    ("Set Minimum Unit Value", "min_units", None, None),
                    ("Set Maximum Unit Value", "max_units", None, None),
                    ("Set Daily Report Time (HH:MM)", "daily_report_time", None, None),
                    ("Set Bot Name Mask", "bot_name_mask", None, None),
                    ("Set Bot Image Mask", "bot_image_mask", None, None),
                    ("Set Guild Background Image URL", "guild_background", None, None),
                    ("Set Default Image URL", "guild_default_image", None, None),
                    ("Set Default Parlay Image URL", "default_parlay_thumbnail", None, None)
                ])

    async def start_selection(self):
        """Sends the initial message and starts the selection process."""
        await self.process_next_selection(self.original_interaction, initial=True)

    async def process_next_selection(self, interaction: discord.Interaction, initial: bool = False):
        """Processes the next selection step or saves settings."""
        if self.current_step >= len(self.steps):
            await self.save_settings(interaction)
            return

        step_title, setting_key, options, select_class = self.steps[self.current_step]
        self.clear_items()

        if select_class:
            if not options:
                await interaction.edit_original_response(
                    content="❌ No available options found. Please ensure the bot has proper permissions.",
                    view=None
                )
                self.stop()
                return

            select = select_class(self, options)
            self.add_item(select)
            self.add_item(CancelButton(self))

            content = f"**Step {self.current_step + 1}**: {step_title}"
            if initial:
                await interaction.edit_original_response(content=content, view=self)
            else:
                await interaction.response.edit_message(content=content, view=self)
        else:
            # Handle text input for non-select options
            modal = TextInputModal(step_title, setting_key)
            await interaction.response.send_modal(modal)
            self.current_step += 1

    async def save_settings(self, interaction: discord.Interaction):
        """Saves the collected settings to the database."""
        try:
            # Ensure assets/logos/guild_id exists
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            guild_logos_dir = os.path.join(base_dir, 'assets', 'logos', str(interaction.guild.id))
            os.makedirs(guild_logos_dir, exist_ok=True)

            # Convert selected IDs from string to int before saving
            final_settings = {}
            for k, v in self.settings.items():
                if v and v != "none":
                    if k in ['embed_channel_1', 'embed_channel_2', 'command_channel_1', 'command_channel_2',
                           'admin_channel_1', 'admin_role', 'authorized_role', 'member_role',
                           'voice_channel_id', 'yearly_channel_id']:
                        final_settings[k] = int(v)
                    else:
                        final_settings[k] = v

            await self.bot.admin_service.setup_guild(interaction.guild_id, final_settings)
            await interaction.edit_original_response(
                content="✅ Guild setup completed successfully!",
                view=None
            )
        except Exception as e:
            logger.exception(f"Error saving guild settings: {e}")
            await interaction.edit_original_response(
                content="❌ An error occurred while saving settings.",
                view=None
            )
        finally:
            self.stop()

class TextInputModal(discord.ui.Modal):
    def __init__(self, title: str, setting_key: str):
        super().__init__(title=title)
        self.setting_key = setting_key
        self.add_item(discord.ui.TextInput(
            label=title,
            placeholder=f"Enter {title.lower()}",
            required=True
        ))

    async def on_submit(self, interaction: discord.Interaction):
        value = self.children[0].value
        view = self.view
        view.settings[self.setting_key] = value
        await view.process_next_selection(interaction)

class VoiceChannelSelect(discord.ui.Select):
    def __init__(self, parent_view: GuildSettingsView, channels: List[discord.VoiceChannel]):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"Channel ID: {channel.id}"
            )
            for channel in channels[:25]
        ]
        super().__init__(
            placeholder="Select voice channel...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.settings[self.custom_id] = self.values[0]
        self.disabled = True
        await interaction.response.defer()
        self.parent_view.current_step += 1
        await self.parent_view.process_next_selection(interaction)


# --- Cog Definition ---
class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Run the interactive server setup.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: Interaction):
        """Starts the interactive server setup process."""
        logger.info(f"Setup command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            # Check if guild is already set up
            existing_settings = await self.bot.db_manager.fetch_one(
                "SELECT * FROM guild_settings WHERE guild_id = %s",
                interaction.guild_id
            )

            if existing_settings:
                # Ask if they want to update images
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Update Images", style=discord.ButtonStyle.primary))
                view.add_item(discord.ui.Button(label="Full Setup", style=discord.ButtonStyle.secondary))
                
                await interaction.response.send_message(
                    "Server is already set up. Would you like to update images or run full setup?",
                    view=view,
                    ephemeral=True
                )
                return

            # Check if guild has paid subscription
            is_paid = await self.bot.admin_service.check_guild_subscription(interaction.guild_id)
            
            if not is_paid:
                # Show subscription modal
                modal = SubscriptionModal()
                await interaction.response.send_modal(modal)
                
                # After modal is closed, show subscription view
                view = SubscriptionView(self.bot, interaction)
                await interaction.followup.send(
                    "Choose your subscription option:",
                    view=view,
                    ephemeral=True
                )
            else:
                # Start paid setup
                view = GuildSettingsView(self.bot, interaction, is_paid=True)
                await interaction.response.send_message(
                    "Starting server setup...",
                    view=view,
                    ephemeral=True
                )
                await view.start_selection()

        except Exception as e:
            logger.exception(f"Error initiating setup command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while starting the setup.",
                ephemeral=True
            )

    @app_commands.command(name="setchannel", description="Set or remove voice channels for stat tracking.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setchannel_command(self, interaction: Interaction):
        """Allows admins to set or remove stat tracking voice channels."""
        logger.info(f"SetChannel command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            # Access services via self.bot
            if not hasattr(self.bot, 'admin_service') or not hasattr(self.bot, 'db_manager'):
                 logger.error("Required services (AdminService, DatabaseManager) not found on bot instance.")
                 await interaction.response.send_message("Bot is not properly configured.", ephemeral=True)
                 return

            view = AdminActionView(self.bot, interaction)
            await interaction.response.send_message("Select the channel action you want to perform:", view=view, ephemeral=True)

        except Exception as e:
            logger.exception(f"Error initiating setchannel command for {interaction.user}: {e}")
            if not interaction.response.is_done():
                 await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            # Cannot easily followup here if initial response failed

    # Cog specific error handler
    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
         if isinstance(error, app_commands.MissingPermissions):
              await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
         else:
              logger.error(f"Error in AdminCog command: {error}", exc_info=True)
              if not interaction.response.is_done():
                   await interaction.response.send_message("An internal error occurred with the admin command.", ephemeral=True)
              else:
                   # May not be possible to followup reliably
                   pass


# The setup function for the extension
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
    logger.info("AdminCog loaded")
