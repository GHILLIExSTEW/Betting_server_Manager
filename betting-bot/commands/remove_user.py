# betting-bot/commands/remove_user.py

import discord
from discord import app_commands, Interaction, SelectOption
from discord.ext import commands # Import commands for Cog
from discord.ui import View, Select
import logging
from typing import List

# import aiosqlite # Remove direct driver import

logger = logging.getLogger(__name__)

# --- UI Components ---

class RemoveUserSelect(Select):
    # Corrected __init__ to accept db_manager if needed directly, or access via parent_view.db
    # Assuming users list is passed in directly now
    def __init__(self, users: list, parent_view):
        self.parent_view = parent_view # Store parent view reference
        options = [
            SelectOption(
                label=user['display_name'][:100] if user.get('display_name') else f"User ID: {user['user_id']}",
                value=str(user['user_id']), # Ensure value is string
                description=f"Remove {user.get('display_name', user['user_id'])}"[:100]
            ) for user in users[:25] # Limit options
        ]
        super().__init__(
            placeholder="Select a user to remove...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        # Access db_manager via parent view's stored instance
        db_manager = self.parent_view.db
        if not db_manager:
             logger.error("Database manager not found in RemoveUserView.")
             await interaction.response.send_message("❌ Internal configuration error.", ephemeral=True)
             return

        try:
            # Defer response as DB operations follow
            await interaction.response.defer(ephemeral=True)

            user_id_to_remove = int(self.values[0])

            # Optional: Fetch user info before deleting for confirmation message
            # User info was already fetched to populate the select, maybe store it?
            # For now, just proceed with deletion.

            # Delete the user using shared db_manager
            # Ensure this query targets the correct table ('users' or maybe 'cappers'?)
            # Original code deleted from 'users', let's assume that's correct.
            delete_status = await db_manager.execute(
                """
                DELETE FROM users
                WHERE user_id = $1 AND guild_id = $2
                """, # Assumes 'users' table has user_id and guild_id
                user_id_to_remove, interaction.guild_id
            )

            if delete_status and 'DELETE 1' in delete_status:
                logger.info(f"User {user_id_to_remove} removed from users table for guild {interaction.guild_id} by {interaction.user}")
                await interaction.followup.send(
                    f"✅ Successfully removed user ID `{user_id_to_remove}`.",
                    ephemeral=True
                )
            elif delete_status and 'DELETE 0' in delete_status:
                 logger.warning(f"Attempted to remove user {user_id_to_remove} for guild {interaction.guild_id}, but they were not found in the users table.")
                 await interaction.followup.send("❌ User not found in the database.", ephemeral=True)
            else:
                 logger.error(f"Failed to remove user {user_id_to_remove} for guild {interaction.guild_id}. Status: {delete_status}")
                 await interaction.followup.send("❌ Failed to remove user from database.", ephemeral=True)

            # Disable the select after use
            self.disabled = True
            await interaction.edit_original_response(view=self.parent_view) # Update original message

        except Exception as e:
            logger.exception(f"Error removing user: {e}")
            await interaction.followup.send(
                "❌ An error occurred while removing the user.",
                ephemeral=True
            )


class RemoveUserView(View):
    def __init__(self, bot: commands.Bot, db_manager, interaction: Interaction):
        super().__init__(timeout=300) # 5 minute timeout
        self.bot = bot
        self.db = db_manager # Store shared db_manager
        self.original_interaction = interaction
        self.select_menu: Optional[RemoveUserSelect] = None

    async def populate_users(self):
        """Fetches users and adds the select menu."""
        try:
            # Use self.db (shared DatabaseManager)
            # Fetch users from the correct table ('users' or 'cappers'?)
            # Let's assume 'users' table with user_id, guild_id, display_name
            users = await self.db.fetch_all(
                """
                SELECT user_id, display_name
                FROM users -- Or 'cappers' table? Clarify target table
                WHERE guild_id = $1
                ORDER BY display_name -- Or username
                """,
                self.original_interaction.guild_id
            )

            if not users:
                 # Check if response already sent before sending another
                if not self.original_interaction.response.is_done():
                    await self.original_interaction.response.send_message(
                        "❌ No registered users found in this server to remove.", # Adjust message based on table used
                        ephemeral=True
                    )
                else:
                    # This case is less likely if populate is called right after command start
                    await self.original_interaction.followup.send(
                         "❌ No registered users found in this server to remove.", ephemeral=True
                    )
                self.stop() # Stop the view if no users
                return

            # Add select menu
            self.select_menu = RemoveUserSelect(users, self)
            self.add_item(self.select_menu)

            # Send the message with the view
            if not self.original_interaction.response.is_done():
                 await self.original_interaction.response.send_message(
                      "Select a user to remove from the system:",
                      view=self,
                      ephemeral=True
                 )
            else:
                 # If initial response was deferred, edit it
                 await self.original_interaction.edit_original_response(
                      content="Select a user to remove from the system:", view=self
                 )

        except Exception as e:
            logger.exception(f"Error populating users for removal: {e}")
            error_message = "❌ An error occurred while fetching users."
            if not self.original_interaction.response.is_done():
                 await self.original_interaction.response.send_message(error_message, ephemeral=True)
            else:
                 await self.original_interaction.followup.send(error_message, ephemeral=True)
            self.stop()

    async def on_timeout(self) -> None:
         logger.info(f"RemoveUserView timed out for interaction {self.original_interaction.id}")
         if self.select_menu: self.select_menu.disabled = True
         try:
              await self.original_interaction.edit_original_response(content="Timed out waiting for user selection.", view=self)
         except discord.NotFound:
              pass # Ignore if original message deleted
         except Exception as e:
              logger.error(f"Error editing message on RemoveUserView timeout: {e}")


# --- Cog Definition ---
class RemoveUserCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Access db_manager via self.bot assuming it's attached in main.py
        self.db_manager = bot.db_manager

    @app_commands.command(name="remove_user", description="Remove a registered user from the system (Admin only).")
    @app_commands.checks.has_permissions(administrator=True) # Ensure only admins can run
    async def remove_user_command(self, interaction: Interaction):
        """Starts the interactive process to remove a user."""
        logger.info(f"Remove User command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            # Access db_manager attached to bot instance
            if not hasattr(self.bot, 'db_manager'):
                 logger.error("db_manager not found on bot instance.")
                 await interaction.response.send_message("❌ Bot is not properly configured (DB Error).", ephemeral=True)
                 return

            # Create the view and populate it
            view = RemoveUserView(self.bot, self.bot.db_manager, interaction)
            await view.populate_users()
            # The view now handles sending the response/message

        except Exception as e:
            logger.exception(f"Error initiating remove_user command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred starting the remove user command.", ephemeral=True)
            # else: # Cannot easily followup if populate_users failed before sending initial response

    # Optional: Cog specific error handler
    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
         if isinstance(error, app_commands.MissingPermissions):
              await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
         else:
              logger.error(f"Error in RemoveUserCog command: {error}", exc_info=True)
              if not interaction.response.is_done():
                   await interaction.response.send_message("An internal error occurred.", ephemeral=True)
              else:
                  # May not be possible to followup reliably if error was early
                  pass


# The setup function for the extension
async def setup(bot: commands.Bot):
    await bot.add_cog(RemoveUserCog(bot))
    logger.info("RemoveUserCog loaded")
