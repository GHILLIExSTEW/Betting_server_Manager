# betting-bot/commands/setid.py

import discord
from discord import app_commands, Interaction, Member
from discord.ext import commands # Import commands for Cog
from discord.ui import Modal, TextInput, View, Button, button # Corrected import for button decorator
import logging
import os
import requests # Keep requests for URL fetching
from io import BytesIO
from PIL import Image # Keep Pillow for image processing
from typing import Optional

# Use relative imports
try:
    # Import db_manager only for type hint if needed
    # from ..data.db_manager import DatabaseManager
    # Import errors if needed
    # from ..utils.errors import ...
    pass # No specific service needed directly here? DB access via bot.db_manager
except ImportError:
    # Fallback imports
    # from data.db_manager import DatabaseManager
    # from utils.errors import ...
    pass

logger = logging.getLogger(__name__)

# --- UI Components ---

class CapperModal(Modal, title="Capper Profile Setup"):
    # Corrected __init__ to not require guild_id/user_id if passed via interaction context
    def __init__(self, target_user: Member, db_manager):
        super().__init__(timeout=300) # Add timeout
        self.target_user = target_user
        self.db = db_manager # Store db_manager instance

    display_name = TextInput(
        label="Display Name",
        placeholder="Enter the capper's display name",
        required=True,
        max_length=32
    )

    banner_color = TextInput(
        label="Banner Color (Hex)",
        placeholder="#RRGGBB (e.g., #0096FF)",
        required=False,
        max_length=7,
        default="#0096FF" # Provide default
    )

    async def on_submit(self, interaction: Interaction):
        try:
            # Acknowledge interaction
            await interaction.response.defer(ephemeral=True, thinking=True)

            guild_id = interaction.guild_id
            user_id = self.target_user.id
            color_value = self.banner_color.value.strip()

            # Validate hex color
            if color_value:
                if not color_value.startswith('#'):
                    color_value = '#' + color_value
                if len(color_value) != 7:
                    # Try parsing to see if it's a valid hex
                    try: int(color_value[1:], 16)
                    except ValueError:
                         await interaction.followup.send(
                              "❌ Invalid hex color format. Please use #RRGGBB (e.g., #3498db).",
                              ephemeral=True
                         )
                         return
                # Store valid color or default
                final_color = color_value
            else:
                 final_color = "#0096FF" # Default if empty

            # Create the capper entry using shared db_manager
            # Assumes 'cappers' table exists with columns: guild_id, user_id, display_name, banner_color, updated_at
            # Using ON CONFLICT DO NOTHING for safety, though check beforehand is better
            insert_status = await self.db.execute(
                """
                INSERT INTO cappers (
                    guild_id, user_id, display_name, banner_color, updated_at
                    -- bet_won, bet_loss initialized to 0 by default in schema? If not, add here.
                ) VALUES ($1, $2, $3, $4, NOW() AT TIME ZONE 'UTC') -- Use PG function for timestamp
                ON CONFLICT (guild_id, user_id) DO NOTHING
                """,
                guild_id,
                user_id,
                self.display_name.value,
                final_color
            )

            # Check if insert happened (status might vary depending on db_manager.execute)
            # For now, assume success if no exception
            logger.info(f"Capper entry created/exists for {user_id} in guild {guild_id}.")

            # Follow up - ask for image
            image_view = ImageUploadView(guild_id=guild_id, user_id=user_id, db_manager=self.db)
            await interaction.followup.send(
                f"✅ Profile base for {self.target_user.mention} setup! Now, please provide a profile picture.",
                view=image_view,
                ephemeral=True
            )

        except Exception as e:
            logger.exception(f"Error in CapperModal submission: {e}")
            # Ensure followup is used if response was deferred
            await interaction.followup.send(
                "❌ An error occurred while setting up the profile.",
                ephemeral=True
            )

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in CapperModal: {error}", exc_info=True)
         # Use followup because original response was likely deferred
         await interaction.followup.send('❌ An error occurred with the profile setup modal.', ephemeral=True)


class ImageUploadView(View):
    def __init__(self, guild_id: int, user_id: int, db_manager):
        super().__init__(timeout=300) # 5 minute timeout for user to respond
        self.guild_id = guild_id
        self.user_id = user_id
        self.db = db_manager

    async def interaction_check(self, interaction: Interaction) -> bool:
         # Optional: Ensure only the admin who initiated setid can interact
         # Or ensure only the target user can upload their *own* image?
         # For now, allow admin interaction.
         # return interaction.user.guild_permissions.administrator # Example check
         return True # Allow interaction

    @button(label="Upload Image", style=discord.ButtonStyle.primary, custom_id="capper_upload_img")
    async def upload_image_button(self, interaction: Interaction, button: Button):
        # Prompt user to upload an image in the *next* message they send
        await interaction.response.send_message(
            "Please upload your profile image (PNG, JPG, GIF) in your next message in this channel.",
            ephemeral=True
        )
        # Need logic in on_message event handler to catch the upload, which is complex with ephemeral interactions.
        # A better approach might be needed here, perhaps a different flow or command.
        # For now, this button just gives instructions.

    @button(label="Provide URL", style=discord.ButtonStyle.secondary, custom_id="capper_provide_url")
    async def provide_url_button(self, interaction: Interaction, button: Button):
        # Show the URL Modal
        modal = ImageURLModal(guild_id=self.guild_id, user_id=self.user_id, db_manager=self.db)
        await interaction.response.send_modal(modal)

    async def on_timeout(self) -> None:
         logger.info(f"ImageUploadView timed out for user {self.user_id}")
         # Optionally update original message or disable view components
         # self.clear_items()
         # await self.message.edit(content="Image upload prompt timed out.", view=self) # Need message reference

class ImageURLModal(Modal, title="Enter Profile Image URL"):
    def __init__(self, guild_id: int, user_id: int, db_manager):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.user_id = user_id
        self.db = db_manager

    url = TextInput(
        label="Image URL",
        placeholder="https://example.com/image.png",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            image_url = self.url.value

            # --- Download and Process Image (Consider running in executor) ---
            try:
                 # Use a timeout for the request
                 response = requests.get(image_url, timeout=10, stream=True)
                 response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                 # Check content type (optional but recommended)
                 content_type = response.headers.get('content-type', '').lower()
                 if not content_type.startswith('image/'):
                      await interaction.followup.send("❌ URL does not point to a valid image type.", ephemeral=True)
                      return

                 # Read image data
                 image_data = BytesIO(response.content)
                 with Image.open(image_data) as img:
                      # Validate format
                      if img.format not in ['PNG', 'JPEG', 'GIF', 'WEBP']: # Allow WEBP?
                           await interaction.followup.send("❌ Invalid image format. Use PNG, JPG, GIF.", ephemeral=True)
                           return

                      # Define save path and ensure directory exists
                      # Save as PNG for consistency? Or keep original format? Let's use PNG.
                      filename = f"{self.user_id}.png"
                      # Use absolute path based on bot's root if possible, otherwise relative
                      # Assuming 'assets' is at the same level as 'commands', 'services' etc.
                      base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # Up two levels
                      save_dir = os.path.join(base_dir, 'assets', 'logos', str(self.guild_id))
                      os.makedirs(save_dir, exist_ok=True)
                      save_path = os.path.join(save_dir, filename)

                      # Save the image (potentially resizing/optimizing first)
                      img.save(save_path, 'PNG') # Save as PNG
                      logger.info(f"Saved capper logo to {save_path}")
                      db_path = os.path.relpath(save_path, base_dir) # Store relative path in DB

            except requests.exceptions.RequestException as req_err:
                 logger.error(f"Failed to download image from URL {image_url}: {req_err}")
                 await interaction.followup.send("❌ Failed to download image from URL. Check the link.", ephemeral=True)
                 return
            except IOError as img_err: # Catch Pillow errors
                 logger.error(f"Failed to process image from URL {image_url}: {img_err}")
                 await interaction.followup.send("❌ Could not process the image file from the URL.", ephemeral=True)
                 return
            except Exception as proc_err: # Catch other potential errors
                 logger.exception(f"Error processing image from {image_url}: {proc_err}")
                 await interaction.followup.send("❌ An error occurred while processing the image.", ephemeral=True)
                 return
            # --- End Image Processing ---


            # Update database using shared db_manager
            update_status = await self.db.execute(
                """
                UPDATE cappers
                SET image_path = $1, updated_at = NOW() AT TIME ZONE 'UTC'
                WHERE guild_id = $2 AND user_id = $3
                """,
                db_path, self.guild_id, self.user_id
            )

            if update_status and 'UPDATE 1' in update_status:
                await interaction.followup.send(
                    "✅ Profile picture updated successfully!",
                    ephemeral=True
                )
            else:
                 await interaction.followup.send(
                      "⚠️ Profile picture saved, but failed to update database record.",
                      ephemeral=True
                 )

        except Exception as e:
            logger.exception(f"Error processing image URL modal: {e}")
            # Check if response already sent before sending followup
            if not interaction.response.is_done():
                 await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            else:
                 await interaction.followup.send("❌ An error occurred processing the image URL.", ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in ImageURLModal: {error}", exc_info=True)
         if not interaction.response.is_done():
              await interaction.response.send_message('❌ An error occurred with the URL modal.', ephemeral=True)
         else:
              await interaction.followup.send('❌ An error occurred with the URL modal.', ephemeral=True)


# --- Cog Definition ---
class SetIDCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Access db_manager via self.bot assuming it's attached in main.py
        self.db_manager = bot.db_manager

    @app_commands.command(name="setid", description="Set up a user as an authorized capper.")
    @app_commands.describe(user="The user to designate as a capper.")
    @app_commands.checks.has_permissions(administrator=True) # Only admins can run this
    async def setid_command(self, interaction: Interaction, user: Member):
        """Sets up a capper profile, prompting for name, color, and image."""
        logger.info(f"SetID command initiated by {interaction.user} for {user} in guild {interaction.guild_id}")
        try:
            # Check if user is already a capper using shared db_manager
            existing_capper = await self.db_manager.fetch_one(
                """
                SELECT user_id
                FROM cappers
                WHERE guild_id = $1 AND user_id = $2
                """,
                interaction.guild_id, user.id
            )

            if existing_capper:
                await interaction.response.send_message(
                    f"❌ {user.mention} is already set up as a capper.",
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none() # Avoid pinging
                )
                return

            # Show profile setup modal (pass target user and db_manager)
            modal = CapperModal(target_user=user, db_manager=self.db_manager)
            await interaction.response.send_modal(modal)
            # The modal's on_submit will handle the DB interaction and image prompt

        except Exception as e:
            logger.exception(f"Error in setid command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while setting up the user.", ephemeral=True)
            # else: Cannot followup modals easily


# The setup function for the extension
async def setup(bot: commands.Bot):
    await bot.add_cog(SetIDCog(bot))
    logger.info("SetIDCog loaded")
