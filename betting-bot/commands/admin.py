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


class GuildSettingsView(discord.ui.View):
    """View to guide through guild setup steps."""
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction):
        super().__init__(timeout=300) # 5 minute timeout
        self.bot = bot
        self.original_interaction = interaction
        self.guild = interaction.guild
        self.settings = {} # Store selected settings here
        self.current_step = 0
        # Filter channels/roles accessible by the bot and sort roles
        self.text_channels = sorted([c for c in self.guild.text_channels if c.permissions_for(self.guild.me).view_channel], key=lambda c: c.position)
        self.roles = sorted([r for r in self.guild.roles if r.id != self.guild.id and not r.is_default()], key=lambda r: r.position, reverse=True)

        # Define the steps for setup
        self.steps = [
            ("Select Embed Channel 1", "embed_channel_1", self.text_channels, ChannelSelect),
            ("Select Embed Channel 2", "embed_channel_2", self.text_channels, ChannelSelect),
            ("Select Command Channel 1", "command_channel_1", self.text_channels, ChannelSelect),
            ("Select Command Channel 2", "command_channel_2", self.text_channels, ChannelSelect),
            ("Select Admin Channel", "admin_channel_1", self.text_channels, ChannelSelect),
            ("Select Admin Role", "admin_role", self.roles, RoleSelect),
            ("Select Authorized Role (Capper Role)", "authorized_role", self.roles, RoleSelect),
            ("Select Member Role", "member_role", self.roles, RoleSelect),
            ("Set Daily Report Time (HH:MM)", "daily_report_time", None, None),  # This will need a custom input
            ("Set Bot Name Mask", "bot_name_mask", None, None),  # This will need a custom input
            ("Set Bot Image Mask", "bot_image_mask", None, None),  # This will need a custom input
            ("Set Guild Default Image", "guild_default_image", None, None),  # This will need a custom input
            ("Set Default Parlay Thumbnail", "default_parlay_thumbnail", None, None)  # This will need a custom input
        ]

    async def start_selection(self):
        """Sends the initial message and starts the selection process."""
        # Send the first step message
        await self.process_next_selection(self.original_interaction, initial=True)

    async def process_next_selection(self, interaction: discord.Interaction, initial: bool = False):
        """Moves to the next selection step or saves settings."""
        if not initial:
            # Store the selected value
            if isinstance(interaction.data, dict) and 'values' in interaction.data:
                selected_value = interaction.data['values'][0]
                current_step_name, current_step_key, _, _ = self.steps[self.current_step]
                self.settings[current_step_key] = selected_value
                logger.info(f"Selected {current_step_name}: {selected_value}")

        # Move to next step
        self.current_step += 1

        if self.current_step < len(self.steps):
            # Show next step
            step_name, step_key, options, view_class = self.steps[self.current_step]
            
            if view_class is None:
                # Handle text input steps
                modal = TextInputModal(step_name, step_key)
                await interaction.response.send_modal(modal)
            else:
                # Handle select menu steps
                view = view_class(options, self.process_next_selection)
                await interaction.edit_original_response(
                    content=f"Please select the {step_name}:",
                    view=view
                )
        else:
            # All steps complete, save settings
            await interaction.edit_original_response(
                content="Saving guild settings...",
                view=None
            )

            try:
                # Ensure assets/logos/guild_id exists
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                guild_logos_dir = os.path.join(base_dir, 'assets', 'logos', str(interaction.guild.id))
                os.makedirs(guild_logos_dir, exist_ok=True)
                logger.info(f"Ensured guild logos directory exists: {guild_logos_dir}")

                # Save settings using admin service (accessed via bot)
                if not hasattr(self.bot, 'admin_service'):
                    raise AdminServiceError("Admin service not found on bot instance.")

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
                    view=None # Remove view
                )
            except AdminServiceError as ase:
                logger.error(f"AdminServiceError saving guild settings for guild {interaction.guild_id}: {ase}")
                await interaction.edit_original_response(content=f"❌ Error saving settings: {ase}", view=None)
            except discord.HTTPException as hte:
                logger.error(f"Discord API error during final setup message edit for guild {interaction.guild_id}: {hte}")
            except Exception as e:
                logger.exception(f"Error saving guild settings for guild {interaction.guild_id}: {e}")
                await interaction.edit_original_response(content="❌ An unexpected error occurred while saving settings.", view=None)
            finally:
                self.stop() # Stop the view

    async def on_timeout(self) -> None:
        logger.warning(f"GuildSettingsView timed out for guild {self.guild.id}")
        self.clear_items()
        try:
            # Try editing the original message, might fail if already gone
            await self.original_interaction.edit_original_response(content="Guild setup timed out.", view=None)
        except discord.NotFound:
            pass # Ignore if message is gone
        except Exception as e:
            logger.error(f"Error editing message on GuildSettingsView timeout: {e}")


class VoiceChannelSelect(Select):
    """Select menu for choosing voice channels."""
    def __init__(self, channels: List[VoiceChannel], placeholder: str = "Select a voice channel...", max_options=25):
        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"ID: {channel.id}"
            )[:100] for channel in channels[:max_options] # Limit options and description length
        ]
        if not options:
             options.append(discord.SelectOption(label="No Voice Channels Found", value="none", emoji="❌"))

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            disabled=not options or options[0].value == "none"
        )

    async def callback(self, interaction: discord.Interaction):
        # This callback should be handled by the parent view (AdminActionView)
        # It stores the result on the view and lets the view process it.
        if not hasattr(self.view, 'selected_channel_id'):
             logger.error("Parent view missing 'selected_channel_id' attribute.")
             await interaction.response.send_message("Internal view error.", ephemeral=True)
             return

        selected_value = self.values[0]
        if selected_value == "none":
             await interaction.response.defer()
             return

        self.view.selected_channel_id = int(selected_value)
        logger.debug(f"Voice channel selected: {selected_value}")
        await interaction.response.defer()

        # Call the processing method on the parent view
        if hasattr(self.view, 'process_voice_channel_selection'):
             await self.view.process_voice_channel_selection(interaction)
        else:
             logger.error("Parent view missing 'process_voice_channel_selection' method.")
             await interaction.followup.send("Error processing voice channel selection.", ephemeral=True)


class AdminActionView(View):
    """View for handling various admin actions like setting voice channels."""
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.original_interaction = interaction
        # Access services via self.bot
        self.admin_service: AdminService = bot.admin_service
        self.selected_action: Optional[str] = None
        self.selected_channel_id: Optional[int] = None

    @discord.ui.select(
        placeholder="Select an admin action...",
        options=[
            discord.SelectOption(label="Set Monthly Channel", value="set_monthly", description="Set voice channel for monthly stats"),
            discord.SelectOption(label="Set Yearly Channel", value="set_yearly", description="Set voice channel for yearly stats"),
            discord.SelectOption(label="Remove Monthly Channel", value="remove_monthly", description="Disable monthly stats voice channel"),
            discord.SelectOption(label="Remove Yearly Channel", value="remove_yearly", description="Disable yearly stats voice channel")
        ], custom_id="admin_action_select" # Add custom_id for potential persistence
    )
    async def select_action_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        # Permissions check again within the callback for safety
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions.", ephemeral=True)
            return

        guild_id = interaction.guild_id
        action = select.values[0]
        self.selected_action = action # Store selected action

        # Payment check
        is_paid = False
        try:
            is_paid = await self.admin_service.is_guild_paid(guild_id)
        except Exception as e:
            logger.error(f"Failed to check payment status for guild {guild_id}: {e}")
            await interaction.response.send_message("Error checking server status. Cannot proceed.", ephemeral=True)
            return

        if not is_paid and action in ["set_monthly", "set_yearly"]:
            await interaction.response.send_message("This feature requires an active subscription.", ephemeral=True)
            return

        # --- Handle Actions ---
        if action in ["set_monthly", "set_yearly"]:
            # Fetch accessible voice channels
            voice_channels = sorted([vc for vc in interaction.guild.voice_channels if vc.permissions_for(interaction.guild.me).connect], key=lambda vc: vc.position)
            if not voice_channels:
                await interaction.response.send_message("No voice channels found where I have permission to connect.", ephemeral=True)
                return

            # Update view with VoiceChannelSelect
            self.clear_items() # Clear the action select
            self.add_item(VoiceChannelSelect(voice_channels, placeholder=f"Select channel for {action.replace('_', ' ').title()}"))
            await interaction.response.edit_message(content="Please select the voice channel:", view=self)
            # The VoiceChannelSelect callback will call process_voice_channel_selection

        elif action == "remove_monthly":
            await interaction.response.defer() # Defer while performing action
            success = await self.admin_service.remove_monthly_channel(guild_id)
            message = "✅ Monthly channel removed successfully." if success else "❌ Failed to remove monthly channel (maybe not set?)."
            await interaction.followup.send(message, ephemeral=True)
            self.stop() # Stop view after action

        elif action == "remove_yearly":
            await interaction.response.defer()
            success = await self.admin_service.remove_yearly_channel(guild_id)
            message = "✅ Yearly channel removed successfully." if success else "❌ Failed to remove yearly channel (maybe not set?)."
            await interaction.followup.send(message, ephemeral=True)
            self.stop() # Stop view after action

        else: # Should not happen
            await interaction.response.send_message("Unknown action selected.", ephemeral=True)

    async def process_voice_channel_selection(self, interaction: discord.Interaction):
        """Called by VoiceChannelSelect callback to finalize setting the channel."""
        if not self.selected_action or self.selected_channel_id is None:
            logger.error("Action or channel ID missing during voice channel processing.")
            await interaction.followup.send("Internal error processing selection.", ephemeral=True)
            self.stop()
            return

        guild_id = interaction.guild_id
        success = False
        action_desc = ""

        try:
            if self.selected_action == "set_monthly":
                action_desc = "monthly"
                success = await self.admin_service.set_monthly_channel(guild_id, self.selected_channel_id)
            elif self.selected_action == "set_yearly":
                action_desc = "yearly"
                success = await self.admin_service.set_yearly_channel(guild_id, self.selected_channel_id)

            message = f"✅ {action_desc.title()} channel set successfully." if success else f"❌ Failed to set {action_desc} channel."
            await interaction.followup.send(message, ephemeral=True)

            # Optional: Trigger immediate update of the channel name via VoiceService
            if success and hasattr(self.bot, 'voice_service'):
                 # Call the method to update just this guild, needs implementation in VoiceService
                 # await self.bot.voice_service.update_specific_guild_channels(guild_id)
                 logger.info(f"Triggering voice channel update for guild {guild_id} after setting {action_desc} channel.")

        except Exception as e:
             logger.exception(f"Error finalizing voice channel setting for guild {guild_id}: {e}")
             await interaction.followup.send(f"❌ An error occurred while setting the {action_desc} channel.", ephemeral=True)
        finally:
            self.stop() # Stop the view

    async def on_timeout(self) -> None:
         logger.warning(f"AdminActionView timed out for interaction {self.original_interaction.id}")
         self.clear_items()
         try:
              await self.original_interaction.edit_original_response(content="Admin action timed out.", view=None)
         except discord.NotFound:
              pass
         except Exception as e:
              logger.error(f"Error editing message on AdminActionView timeout: {e}")


class TextInputModal(discord.ui.Modal):
    """Modal for text input settings."""
    def __init__(self, title: str, setting_key: str):
        super().__init__(title=title)
        self.setting_key = setting_key
        self.input = discord.ui.TextInput(
            label=title,
            placeholder="Enter value...",
            required=True
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        if not hasattr(self.view, 'settings'):
            logger.error("Parent view or settings dictionary not found in TextInputModal.")
            await interaction.response.send_message("Error processing input.", ephemeral=True)
            return

        self.view.settings[self.setting_key] = self.input.value
        await interaction.response.defer()
        
        if hasattr(self.view, 'process_next_selection'):
            await self.view.process_next_selection(interaction)
        else:
            logger.error("process_next_selection method not found in parent view.")
            await interaction.followup.send("Error proceeding to next step.", ephemeral=True)


# --- Cog Definition ---
class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Services are accessed via self.bot

    @app_commands.command(name="setup", description="Run the interactive server setup.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: Interaction):
        """Starts the interactive server setup process."""
        logger.info(f"Setup command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            # Access services via self.bot
            if not hasattr(self.bot, 'admin_service') or not hasattr(self.bot, 'db_manager'):
                 logger.error("Required services (AdminService, DatabaseManager) not found on bot instance.")
                 await interaction.response.send_message("Bot is not properly configured. Setup cannot start.", ephemeral=True)
                 return

            # Defer the initial response before starting the view
            await interaction.response.defer(ephemeral=True, thinking=True)

            view = GuildSettingsView(self.bot, interaction)
            # Send placeholder message, view will edit it
            await interaction.followup.send("Starting server setup...", view=view, ephemeral=True)
            await view.start_selection()

        except Exception as e:
            logger.exception(f"Error initiating setup command for {interaction.user}: {e}")
            # Ensure followup is used if deferred
            await interaction.followup.send("❌ An error occurred while starting the setup.", ephemeral=True)


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
