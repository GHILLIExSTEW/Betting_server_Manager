# betting-bot/commands/admin.py

"""Admin commands for server setup and management."""

import discord
from discord import app_commands, Interaction, SelectOption, TextChannel, Role, VoiceChannel
from discord.ext import commands # Import commands for Cog
from discord.ui import View, Select, Modal, TextInput
import logging
import os
from typing import Optional, List
import requests
from PIL import Image
from io import BytesIO

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
        # Filter out channels that have already been selected for this type
        if setting_key == 'embed_channel_id' and hasattr(self, 'view') and hasattr(self.view, 'embed_channels'):
            channels = [ch for ch in channels if str(ch.id) not in self.view.embed_channels]
        elif setting_key == 'command_channel_id' and hasattr(self, 'view') and hasattr(self.view, 'command_channels'):
            channels = [ch for ch in channels if str(ch.id) not in self.view.command_channels]

        options = [
            discord.SelectOption(
                label=f"#{channel.name}", # Add # prefix
                value=str(channel.id),
                description=f"ID: {channel.id}"
            ) for channel in channels[:max_options] # Limit options
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

        # For embed channels, track the selection
        if self.setting_key == 'embed_channel_id':
            if selected_value in self.view.embed_channels:
                await interaction.response.send_message("This channel has already been selected as an embed channel.", ephemeral=True)
                return
            self.view.embed_channels.append(selected_value)
            # Store as a list in settings
            if 'embed_channel_id' not in self.view.settings:
                self.view.settings['embed_channel_id'] = []
            self.view.settings['embed_channel_id'].append(selected_value)
        # For command channels, track the selection
        elif self.setting_key == 'command_channel_id':
            if selected_value in self.view.command_channels:
                await interaction.response.send_message("This channel has already been selected as a command channel.", ephemeral=True)
                return
            self.view.command_channels.append(selected_value)
            # Store as a list in settings
            if 'command_channel_id' not in self.view.settings:
                self.view.settings['command_channel_id'] = []
            self.view.settings['command_channel_id'].append(selected_value)
        else:
            # For other channels (like admin channel), store as single value
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
            ) for role in roles[:max_options] # Limit options
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
        view = GuildSettingsView(
            bot=self.bot,
            guild=interaction.guild,
            admin_service=self.bot.admin_service,
            original_interaction=interaction,
            subscription_level='free'
        )
        await view.start_selection()
        self.stop()

class SkipButton(discord.ui.Button):
    """Button to skip the current setup step."""
    def __init__(self):
        super().__init__(
            label="Skip",
            style=discord.ButtonStyle.secondary,
            custom_id="skip_step"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle skip button click."""
        if not hasattr(self.view, 'process_next_selection'):
            await interaction.response.send_message("Error: Cannot process skip action.", ephemeral=True)
            return

        # Defer the interaction to prevent timeout
        await interaction.response.defer()
        
        # Store the message for editing
        self.view.message = interaction.message
        
        # Move to next step
        self.view.current_step += 1
        await self.view.process_next_selection(interaction)

class GuildSettingsView(discord.ui.View):
    """View for guild settings setup"""
    
    SETUP_STEPS = [
        {
            'name': 'Embed Channel',
            'select': ChannelSelect,
            'options': lambda guild: [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels],
            'setting_key': 'embed_channel_id',
            'max_count': 2,  # Maximum number of embed channels allowed for premium
            'free_count': 1  # Maximum number of embed channels for free tier
        },
        {
            'name': 'Command Channel',
            'select': ChannelSelect,
            'options': lambda guild: [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels],
            'setting_key': 'command_channel_id',
            'max_count': 2,  # Maximum number of command channels allowed for premium
            'free_count': 1  # Maximum number of command channels for free tier
        },
        {
            'name': 'Admin Channel',
            'select': ChannelSelect,
            'options': lambda guild: [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels],
            'setting_key': 'admin_channel_id',
            'max_count': 1,  # Only one admin channel allowed
            'free_count': 1
        },
        {
            'name': 'Admin Role',
            'select': RoleSelect,
            'options': lambda guild: [discord.SelectOption(label=role.name, value=str(role.id)) for role in guild.roles],
            'setting_key': 'admin_role_id',
            'max_count': 1,  # Only one admin role allowed
            'free_count': 1
        },
        {
            'name': 'Authorized Role',
            'select': RoleSelect,
            'options': lambda guild: [discord.SelectOption(label=role.name, value=str(role.id)) for role in guild.roles],
            'setting_key': 'authorized_role_id',
            'max_count': 1,  # Only one authorized role allowed
            'free_count': 1
        },
        {
            'name': 'Member Role',
            'select': RoleSelect,
            'options': lambda guild: [discord.SelectOption(label=role.name, value=str(role.id)) for role in guild.roles],
            'setting_key': 'member_role_id',
            'max_count': 1,  # Only one member role allowed
            'free_count': 1
        },
        {
            'name': 'Bot Avatar URL',
            'select': None,  # This will be handled by message input
            'setting_key': 'bot_image_mask',
            'is_premium_only': True
        },
        {
            'name': 'Guild Background URL',
            'select': None,  # This will be handled by message input
            'setting_key': 'guild_background',
            'is_premium_only': True
        },
        {
            'name': 'Default Parlay Image',
            'select': None,  # This will be handled by message input
            'setting_key': 'default_parlay_image',
            'is_premium_only': True
        }
        # Note: User avatars are stored per user in the cappers table's image_path column
        # and are only available for premium guild members with the authorized role
    ]

    def __init__(self, bot, guild, admin_service, original_interaction, subscription_level='free'):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = guild
        self.admin_service = admin_service
        self.original_interaction = original_interaction
        self.current_step = 0
        self.settings = {}
        self.subscription_level = subscription_level
        self.embed_channels = []  # Track selected embed channels
        self.command_channels = []  # Track selected command channels
        self.waiting_for_url = False  # Track if we're waiting for a URL input
        
        # Create necessary directories for this guild
        self._create_guild_directories()

    def _create_guild_directories(self):
        """Create necessary directories for the guild."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            guild_dirs = [
                os.path.join(base_dir, 'static', 'logos', str(self.guild.id)),  # For guild logos and assets
                os.path.join(base_dir, 'data', 'guilds', str(self.guild.id))     # For guild-specific data
            ]
            
            for dir_path in guild_dirs:
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
        except Exception as e:
            logger.error(f"Error creating guild directories: {e}")

    async def start_selection(self):
        """Start the selection process"""
        try:
            await self.process_next_selection(self.original_interaction, initial=True)
        except Exception as e:
            logger.error(f"Error in start_selection: {str(e)}")
            if not self.original_interaction.response.is_done():
                await self.original_interaction.followup.send("An error occurred during setup. Please try again.", ephemeral=True)
            else:
                await self.original_interaction.followup.send("An error occurred during setup. Please try again.", ephemeral=True)

    async def process_next_selection(self, interaction: discord.Interaction, initial: bool = False):
        """Process the next selection step"""
        try:
            if self.current_step >= len(self.SETUP_STEPS):
                await self.finalize_setup(interaction)
                return

            step = self.SETUP_STEPS[self.current_step]
            
            # Skip premium-only steps for free tier
            if step.get('is_premium_only', False) and self.subscription_level != 'premium':
                self.current_step += 1
                await self.process_next_selection(interaction)
                return

            # Handle URL input steps
            if step['select'] is None:
                self.waiting_for_url = True
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"Please upload an image for {step['name'].lower()} or type 'skip' to skip this step:",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"Please upload an image for {step['name'].lower()} or type 'skip' to skip this step:",
                        ephemeral=True
                    )
                return

            # For selection steps, defer the interaction
            if not interaction.response.is_done():
                await interaction.response.defer()

            select_class = step['select']
            
            # Get the appropriate items based on the step type
            if select_class == ChannelSelect:
                items = interaction.guild.text_channels
            else:  # RoleSelect
                items = interaction.guild.roles

            if not items:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"No {step['name'].lower()} found. Please create one and try again.", ephemeral=True)
                else:
                    await interaction.followup.send(f"No {step['name'].lower()} found. Please create one and try again.", ephemeral=True)
                return

            # Create a new view that inherits from the current view
            view = GuildSettingsView(self.bot, interaction.guild, self.admin_service, self.original_interaction, self.subscription_level)
            view.current_step = self.current_step
            view.settings = self.settings.copy()
            view.message = self.message

            # Create the selection dropdown
            select = select_class(
                placeholder=f"Select {step['name']}",
                options=step['options'](interaction.guild),
                min_values=1,
                max_values=1
            )
            view.add_item(select)

            # Add skip button
            skip_button = SkipButton()
            view.add_item(skip_button)

            # Send the message
            if initial:
                await interaction.response.send_message(f"Please select a {step['name'].lower()}:", view=view, ephemeral=True)
            else:
                if self.message:
                    try:
                        await self.message.edit(content=f"Please select a {step['name'].lower()}:", view=view)
                    except discord.NotFound:
                        await interaction.followup.send(f"Please select a {step['name'].lower()}:", view=view, ephemeral=True)
                else:
                    await interaction.followup.send(f"Please select a {step['name'].lower()}:", view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in process_next_selection: {str(e)}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred during setup. Please try again.", ephemeral=True)
            else:
                await interaction.followup.send("An error occurred during setup. Please try again.", ephemeral=True)

    async def handle_url_input(self, message: discord.Message):
        """Handle file uploads or URL input from user"""
        if not self.waiting_for_url:
            return

        step = self.SETUP_STEPS[self.current_step]
        setting_key = step['setting_key']

        # Check for file attachments first
        if message.attachments:
            attachment = message.attachments[0]  # Get the first attachment
            if not attachment.content_type.startswith('image/'):
                await message.channel.send(f"❌ Please upload an image file for {step['name']}.")
                return

            try:
                # Download the attachment
                response = requests.get(attachment.url, timeout=10, stream=True)
                response.raise_for_status()
                image_data = BytesIO(response.content)
                
                with Image.open(image_data) as img:
                    if img.format not in ['PNG', 'JPEG', 'JPG', 'GIF', 'WEBP']:
                        await message.channel.send(f"❌ Invalid image format for {step['name']}. Use PNG, JPG, GIF, or WEBP.")
                        return
                    
                    # Save as PNG for consistency
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    guild_dir = os.path.join(base_dir, 'static', 'logos', str(self.guild.id))
                    os.makedirs(guild_dir, exist_ok=True)
                    save_path = os.path.join(guild_dir, f"{setting_key}.png")
                    img.save(save_path, 'PNG')
                    # Store relative path from betting-bot root
                    relative_path = os.path.join('static', 'logos', str(self.guild.id), f"{setting_key}.png")
                    self.settings[setting_key] = relative_path
                    
            except Exception as e:
                logger.error(f"Failed to process uploaded image for {setting_key}: {e}")
                await message.channel.send(f"❌ Failed to process the uploaded image for {step['name']}.")
                return
        else:
            # Handle URL input as before
            content = message.content.strip()
            if content.lower() == 'skip':
                self.settings[setting_key] = None
            else:
                try:
                    response = requests.get(content, timeout=10, stream=True)
                    response.raise_for_status()
                    content_type = response.headers.get('content-type', '').lower()
                    if not content_type.startswith('image/'):
                        await message.channel.send(f"❌ URL does not point to a valid image type for {step['name']}.")
                        return
                    image_data = BytesIO(response.content)
                    with Image.open(image_data) as img:
                        if img.format not in ['PNG', 'JPEG', 'JPG', 'GIF', 'WEBP']:
                            await message.channel.send(f"❌ Invalid image format for {step['name']}. Use PNG, JPG, GIF, or WEBP.")
                            return
                        # Save as PNG for consistency
                        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        guild_dir = os.path.join(base_dir, 'static', 'logos', str(self.guild.id))
                        os.makedirs(guild_dir, exist_ok=True)
                        save_path = os.path.join(guild_dir, f"{setting_key}.png")
                        img.save(save_path, 'PNG')
                        # Store relative path from betting-bot root
                        relative_path = os.path.join('static', 'logos', str(self.guild.id), f"{setting_key}.png")
                        self.settings[setting_key] = relative_path
                except Exception as e:
                    logger.error(f"Failed to download/save image for {setting_key}: {e}")
                    await message.channel.send(f"❌ Failed to download or save the image for {step['name']}.")
                    return

        self.waiting_for_url = False
        self.current_step += 1

        # Check if there are more URL steps
        while self.current_step < len(self.SETUP_STEPS):
            next_step = self.SETUP_STEPS[self.current_step]
            if next_step.get('is_premium_only', False) and next_step['select'] is None:
                await message.channel.send(
                    f"Please upload an image for {next_step['name'].lower()} or type 'skip' to skip this step:"
                )
                self.waiting_for_url = True
                return
            self.current_step += 1

        # If we've gone through all steps, finalize
        await self.finalize_setup(message)

    async def finalize_setup(self, interaction_or_message):
        """Saves the collected settings to the database."""
        try:
            # Ensure assets/logos/guild_id exists
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            guild_logos_dir = os.path.join(base_dir, 'assets', 'logos', str(self.guild.id))
            os.makedirs(guild_logos_dir, exist_ok=True)

            # Convert selected IDs from string to int before saving
            final_settings = {}
            for k, v in self.settings.items():
                if v and v != "none":
                    if k in ['embed_channel_id', 'command_channel_id', 'admin_channel_id', 'admin_role_id', 'authorized_role_id', 'member_role_id']:
                        final_settings[k] = int(v)
                    else:
                        final_settings[k] = v

            await self.admin_service.setup_guild(self.guild.id, final_settings)
            
            if isinstance(interaction_or_message, discord.Interaction):
                await interaction_or_message.edit_original_response(
                    content="✅ Guild setup completed successfully!",
                    view=None
                )
            else:
                await interaction_or_message.channel.send(
                    "✅ Guild setup completed successfully!"
                )
        except Exception as e:
            logger.exception(f"Error saving guild settings: {e}")
            if isinstance(interaction_or_message, discord.Interaction):
                await interaction_or_message.edit_original_response(
                    content="❌ An error occurred while saving settings.",
                    view=None
                )
            else:
                await interaction_or_message.channel.send(
                    "❌ An error occurred while saving settings."
                )
        finally:
            self.stop()

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
    def __init__(self, bot: commands.Bot, admin_service):
        self.bot = bot
        self.admin_service = admin_service
        self.active_views = {}  # Track active views by user ID

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle URL input messages"""
        if message.author.bot:
            return

        # Check if this user has an active view waiting for URL input
        if message.author.id in self.active_views:
            view = self.active_views[message.author.id]
            if view.waiting_for_url:
                try:
                    await view.handle_url_input(message)
                    # If we're done with all URL inputs, remove the view
                    if not view.waiting_for_url:
                        del self.active_views[message.author.id]
                except Exception as e:
                    logger.error(f"Error handling URL input: {str(e)}")
                    await message.channel.send("An error occurred while processing your input. Please try again.")
                    del self.active_views[message.author.id]

    @app_commands.command(name="setup", description="Run the interactive server setup.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: Interaction):
        """Starts the interactive server setup process."""
        logger.info(f"Setup command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            await interaction.response.defer(ephemeral=True)
            existing_settings = await self.bot.db_manager.fetch_one(
                "SELECT * FROM guild_settings WHERE guild_id = %s",
                interaction.guild_id
            )
            if existing_settings:
                view = discord.ui.View(timeout=300)
                # Use instance methods for callbacks, passing context
                async def update_images_callback(inner_interaction: discord.Interaction):
                    await self.update_images_callback(inner_interaction, existing_settings)
                async def full_setup_callback(inner_interaction: discord.Interaction):
                    await self.full_setup_callback(inner_interaction)
                update_images_btn = discord.ui.Button(label="Update Images", style=discord.ButtonStyle.primary)
                update_images_btn.callback = update_images_callback
                view.add_item(update_images_btn)
                full_setup_btn = discord.ui.Button(label="Full Setup", style=discord.ButtonStyle.secondary)
                full_setup_btn.callback = full_setup_callback
                view.add_item(full_setup_btn)
                await interaction.followup.send(
                    "Server is already set up. Would you like to update images or run full setup?",
                    view=view,
                    ephemeral=True
                )
                return

            # Get subscription level from database
            subscription_level = await self.bot.admin_service.get_guild_subscription_level(interaction.guild_id)
            
            if subscription_level == 'free':
                modal = SubscriptionModal()
                await interaction.followup.send_modal(modal)
                view = SubscriptionView(self.bot, interaction)
                await interaction.followup.send(
                    "Choose your subscription option:",
                    view=view,
                    ephemeral=True
                )
            else:
                view = GuildSettingsView(
                    self.bot, 
                    interaction.guild, 
                    self.admin_service, 
                    interaction, 
                    subscription_level='premium'
                )
                await interaction.followup.send(
                    "Starting server setup...",
                    view=view,
                    ephemeral=True
                )
                await view.start_selection()
        except Exception as e:
            logger.exception(f"Error initiating setup command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while starting the setup.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
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

    async def update_images_callback(self, interaction: discord.Interaction, existing_settings=None):
        """Handle update images button click"""
        try:
            # Create a new view for image URL requests
            view = GuildSettingsView(
                bot=self.bot,
                guild=interaction.guild,
                admin_service=self.admin_service,
                original_interaction=interaction,
                subscription_level='premium'
            )
            if existing_settings:
                view.settings = dict(existing_settings)
            
            # Find the first image URL step
            for i, step in enumerate(view.SETUP_STEPS):
                if step.get('is_premium_only', False) and step['select'] is None:
                    view.current_step = i
                    break
            
            # Send initial message asking for URL
            await interaction.response.send_message(
                f"Please upload an image for {view.SETUP_STEPS[view.current_step]['name'].lower()} or type 'skip' to skip this step:",
                ephemeral=True
            )
            view.waiting_for_url = True
            
            # Store the view for this user
            self.active_views[interaction.user.id] = view
            
        except Exception as e:
            logger.error(f"Error in update images callback: {str(e)}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred while updating images. Please try again.", ephemeral=True)
            else:
                await interaction.followup.send("An error occurred while updating images. Please try again.", ephemeral=True)

    async def full_setup_callback(self, interaction: discord.Interaction):
        """Handle full setup button click"""
        try:
            await interaction.response.defer()
            view = GuildSettingsView(
                bot=self.bot,
                guild=interaction.guild,
                admin_service=self.admin_service,
                original_interaction=interaction,
                subscription_level='premium'
            )
            await interaction.followup.send(
                "Starting full server setup...",
                view=view,
                ephemeral=True
            )
            await view.start_selection()
        except Exception as e:
            logger.error(f"Error in full setup callback: {str(e)}")
            if not interaction.response.is_done():
                await interaction.followup.send("An error occurred during setup. Please try again.", ephemeral=True)
            else:
                await interaction.followup.send("An error occurred during setup. Please try again.", ephemeral=True)


# The setup function for the extension
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot, bot.admin_service))
    logger.info("AdminCog loaded")
