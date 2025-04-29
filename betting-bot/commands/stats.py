# betting-bot/commands/stats.py

"""Stats command for viewing betting statistics."""

import discord
from discord import app_commands, Interaction, SelectOption, File
from discord.ext import commands # Import commands for Cog
from discord.ui import View, Select
import logging
import os
from io import BytesIO # Needed for sending PIL image
from typing import Optional # Add Optional type import

# Use relative imports
try:
    # Import necessary services and utils
    # Services will be accessed via self.bot.<service_name>
    # from ..services.analytics_service import AnalyticsService # Not needed if accessed via bot
    from ..utils.stats_image_generator import StatsImageGenerator
    # Import db_manager only for type hint if needed by View
    # from ..data.db_manager import DatabaseManager
except ImportError:
    # Fallback imports
    from services.analytics_service import AnalyticsService
    from utils.stats_image_generator import StatsImageGenerator
    # from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# --- UI Components for Stats Command ---

# Optional: Define ChannelSelect here if needed by StatsView for sending image
class ChannelSelect(Select):
    def __init__(self, channels: list, parent_view):
        self.parent_view = parent_view # Store reference to parent StatsView
        options = [
            SelectOption(
                label=f"#{channel.name}",
                value=str(channel.id),
                description=f"ID: {channel.id}"
            )[:100] # Ensure description length limit
            for channel in channels[:25] # Limit options
        ]
        super().__init__(
            placeholder="Select a channel to send stats image to...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        try:
            # Immediately acknowledge
            await interaction.response.defer(ephemeral=True, thinking=True)

            channel_id = int(self.values[0])
            channel = interaction.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                 await interaction.followup.send("❌ Invalid channel selected.", ephemeral=True)
                 return

            # Get the stats data and context from the parent view
            stats_data = self.parent_view.stats_data
            is_server = self.parent_view.is_server
            selected_user_id = self.parent_view.selected_user_id

            if not stats_data:
                 await interaction.followup.send("❌ Stats data not found. Please select a capper/server first.", ephemeral=True)
                 return

            # Generate the stats image
            image_generator = StatsImageGenerator() # Assumes StatsImageGenerator doesn't need bot/db
            # generate_stats_image needs to be async or run in executor if it's CPU bound
            # For now, assume it returns a BytesIO object or path
            img_buffer: Optional[BytesIO] = await image_generator.generate_stats_image(
                stats_data=stats_data,
                is_server=is_server,
                guild=interaction.guild, # Pass guild object for name/icon
                user_id=selected_user_id, # Pass user_id for capper stats title
                bot=self.parent_view.bot # Pass bot if needed to fetch user names
            )

            if img_buffer:
                # Send the image to the selected channel
                img_buffer.seek(0) # Reset buffer position
                file = File(img_buffer, filename="stats.png")
                await channel.send(f"📊 Statistics requested by {interaction.user.mention}:", file=file)
                await interaction.followup.send(
                    f"✅ Statistics image sent to {channel.mention}",
                    ephemeral=True
                )
            else:
                 # Handle image generation failure
                 await interaction.followup.send(
                      "❌ Failed to generate statistics image.", ephemeral=True
                 )

            # Disable the select after use
            self.disabled = True
            # Need to edit the *original* message associated with StatsView, not this followup
            # This requires storing the original message reference in StatsView
            # await self.parent_view.update_message() # Example call

        except Exception as e:
            logger.exception(f"Error sending stats to channel: {e}")
            await interaction.followup.send(
                "❌ Failed to send statistics image. Check logs for details.",
                ephemeral=True
            )
        finally:
            # Re-enable the select? Or maybe just remove the view
            # This part depends on desired UX
             pass

class StatsView(View):
    def __init__(self, bot: commands.Bot, db_manager, interaction: Interaction):
        super().__init__(timeout=300) # 5 minute timeout
        self.bot = bot
        self.db = db_manager # Use the shared db_manager
        self.analytics_service = bot.analytics_service # Access via bot
        self.original_interaction = interaction # Store original interaction
        self.stats_data = None
        self.is_server = False
        self.selected_user_id = None
        # Placeholder for the select component - will be added by populate_cappers
        self.capper_select: Optional[Select] = None
        self.channel_select: Optional[ChannelSelect] = None # To hold the channel select later

    async def update_message(self, interaction: Optional[Interaction] = None, content: Optional[str] = None):
         """Helper to edit the original interaction message."""
         target_interaction = interaction or self.original_interaction
         if target_interaction and not target_interaction.response.is_done():
             # This should not happen if called after initial response/deferral
             logger.warning("Attempted to edit message before initial response.")
             return
         try:
             # Default content if none provided
             message_content = content or self.message_content or "Processing..."
             await target_interaction.edit_original_response(content=message_content, view=self)
         except discord.NotFound:
              logger.warning("Original interaction message for StatsView not found (timed out or deleted).")
         except Exception as e:
              logger.error(f"Failed to edit original StatsView message: {e}")

    async def populate_cappers(self):
        """Populate the select menu with cappers from the guild."""
        try:
            # Use self.db (shared DatabaseManager)
            cappers = await self.db.fetch_all(
                """
                SELECT user_id -- Add display_name from cappers table if stored there
                FROM cappers
                WHERE guild_id = $1
                -- ORDER BY display_name -- Order if display_name available
                """,
                (self.original_interaction.guild_id,)
            )

            options = []
            # Add server option first
            options.append(
                SelectOption(
                    label="📊 Server Stats",
                    value="server",
                    description="View overall server statistics"
                )
            )

            # Add cappers
            fetched_users = 0
            for capper in cappers:
                 if fetched_users >= 24: break # Limit options in Select menu (25 total max)
                 user = self.original_interaction.guild.get_member(capper['user_id']) # Try cache first
                 if not user: # Fetch if not in cache
                      try: user = await self.original_interaction.guild.fetch_member(capper['user_id'])
                      except discord.NotFound: continue # Skip if member left
                      except discord.Forbidden: continue # Skip if cannot fetch
                      except Exception as e:
                           logger.warning(f"Error fetching member {capper['user_id']}: {e}")
                           continue
                 if user:
                      options.append(
                           SelectOption(
                                label=user.display_name[:100], # Limit label length
                                value=str(capper['user_id']),
                                description=f"View {user.display_name}'s stats"[:100] # Limit desc length
                           )
                      )
                      fetched_users += 1


            if len(options) <= 1: # Only server option means no cappers found/fetched
                await self.original_interaction.response.send_message(
                    "No authorized cappers found in this server to display stats for.",
                    ephemeral=True
                )
                self.stop() # Stop the view if no options
                return

            # Create and add the select menu
            self.capper_select = Select(placeholder="Select a Capper or 'Server Stats'", options=options)
            self.capper_select.callback = self.capper_select_callback # Assign callback
            self.add_item(self.capper_select)

        except Exception as e:
            logger.exception(f"Error populating cappers for guild {self.original_interaction.guild_id}: {e}")
            # Try to send error message
            if not self.original_interaction.response.is_done():
                 await self.original_interaction.response.send_message("❌ Error fetching cappers.", ephemeral=True)
            else:
                 await self.original_interaction.followup.send("❌ Error fetching cappers.", ephemeral=True)
            self.stop() # Stop view on error


    async def capper_select_callback(self, interaction: Interaction):
        """Callback for when a capper/server is selected."""
        try:
             # Acknowledge interaction quickly
            await interaction.response.defer(ephemeral=True, thinking=True) # Thinking state

            self.clear_items() # Clear old selects/buttons
            selection = interaction.data['values'][0]

            if selection == "server":
                self.stats_data = await self.analytics_service.get_guild_stats(interaction.guild_id)
                self.is_server = True
                self.selected_user_id = None
                stats_title = f"📊 Server Stats for {interaction.guild.name}"
            else:
                self.selected_user_id = int(selection)
                self.stats_data = await self.analytics_service.get_user_stats(interaction.guild_id, self.selected_user_id)
                self.is_server = False
                # Try to get user display name for title
                user = interaction.guild.get_member(self.selected_user_id) or await interaction.guild.fetch_member(self.selected_user_id)
                stats_title = f"📊 Stats for {user.display_name}" if user else f"Stats for User ID {self.selected_user_id}"


            if not self.stats_data:
                 await interaction.followup.send("❌ Could not retrieve statistics data.", ephemeral=True)
                 self.stop()
                 return

            # Generate the stats image
            # Ensure StatsImageGenerator is async or run in executor
            image_generator = StatsImageGenerator()
            img_buffer: Optional[BytesIO] = await image_generator.generate_stats_image(
                 stats_data=self.stats_data,
                 is_server=self.is_server,
                 guild=interaction.guild,
                 user_id=self.selected_user_id,
                 bot=self.bot # Pass bot if needed by generator
            )

            if img_buffer:
                img_buffer.seek(0)
                file = File(img_buffer, filename="stats.png")
                # Add channel selection
                valid_channels = [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.user).send_messages]
                if valid_channels:
                     self.channel_select = ChannelSelect(valid_channels, self)
                     self.add_item(self.channel_select)
                     await interaction.followup.send(
                          content=f"{stats_title}\nSelect a channel to send this image to:",
                          file=file,
                          view=self,
                          ephemeral=True
                     )
                else:
                     # No channels to send to, just show image
                     await interaction.followup.send(
                          content=stats_title,
                          file=file,
                          view=None, # No further actions needed
                          ephemeral=True
                     )

            else:
                 await interaction.followup.send("❌ Failed to generate statistics image.", ephemeral=True)
                 self.stop()


        except Exception as e:
            logger.exception(f"Error in stats selection callback: {e}")
            await interaction.followup.send(
                "❌ An error occurred while generating statistics. Please try again later.",
                ephemeral=True
            )
            self.stop()


# --- Cog Definition ---
class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Services accessed via self.bot assuming they are attached in main.py
        # Example: self.analytics_service = bot.analytics_service
        # Example: self.db_manager = bot.db_manager

    @app_commands.command(name="stats", description="View betting statistics for cappers or the server.")
    async def stats_command(self, interaction: Interaction):
        """Displays betting statistics via an interactive view."""
        logger.info(f"Stats command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
             # Access db_manager attached to bot instance
            if not hasattr(self.bot, 'db_manager'):
                 logger.error("db_manager not found on bot instance.")
                 await interaction.response.send_message("❌ Bot is not properly configured (DB Error).", ephemeral=True)
                 return

            view = StatsView(self.bot, self.bot.db_manager, interaction)
            await view.populate_cappers() # Fetch cappers and populate select

            # Only send initial message if populate_cappers didn't already respond (e.g., with an error)
            if not interaction.response.is_done():
                 if view.children: # Check if select menu was added successfully
                      await interaction.response.send_message(
                           "Select a capper or 'Server Stats' to view statistics:",
                           view=view,
                           ephemeral=True
                      )
                 # else: # populate_cappers already sent an error message or stopped view
                 #    pass

        except Exception as e:
            logger.exception(f"Error initiating stats command for {interaction.user}: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while starting the stats command.", ephemeral=True)
            # Cannot use followup if initial response wasn't sent

# The setup function for the extension
async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
    logger.info("StatsCog loaded")
