# betting-bot/commands/load_logos.py

import discord
from discord import app_commands, Interaction, Attachment # Import specific types
from discord.ext import commands # Import commands for Cog
import os
import logging
from typing import Optional
from PIL import Image # Keep Pillow import
import asyncio # For running blocking code in executor

logger = logging.getLogger(__name__)

# --- Configuration ---
# Get required IDs from environment variables for security
# Ensure these are set in your .env file
try:
    # Ensure TEST_GUILD_ID is loaded correctly in main.py and accessible if needed here
    # Or load directly:
    import os
    from dotenv import load_dotenv
    # Load .env from parent directory relative to this file
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    TEST_GUILD_ID_STR = os.getenv('TEST_GUILD_ID')
    AUTHORIZED_USER_ID_STR = os.getenv('AUTHORIZED_LOAD_LOGO_USER_ID') # Use a specific env var

    if not TEST_GUILD_ID_STR or not AUTHORIZED_USER_ID_STR:
        logger.error("TEST_GUILD_ID or AUTHORIZED_LOAD_LOGO_USER_ID not set in environment variables!")
        TEST_GUILD_ID = None # Disable command if IDs not set
        AUTHORIZED_USER_ID = None
    else:
        TEST_GUILD_ID = int(TEST_GUILD_ID_STR)
        AUTHORIZED_USER_ID = int(AUTHORIZED_USER_ID_STR)
except ValueError:
    logger.error("Invalid format for TEST_GUILD_ID or AUTHORIZED_LOAD_LOGO_USER_ID in environment variables.")
    TEST_GUILD_ID = None
    AUTHORIZED_USER_ID = None
except Exception as e:
     logger.error(f"Error loading environment variables for load_logos: {e}")
     TEST_GUILD_ID = None
     AUTHORIZED_USER_ID = None

# --- Helper Function for Image Processing (to run in executor) ---
def process_and_save_logo(
    logo_bytes: bytes,
    team_name: str,
    is_league: bool,
    guild_id: Optional[int] = None # Added guild_id for capper logos
    ) -> Optional[str]:
    """Processes and saves logo, returns relative save path or None on failure."""
    try:
        with Image.open(BytesIO(logo_bytes)) as img:
            # Validate format
            original_format = img.format
            if original_format not in ['PNG', 'JPEG', 'GIF', 'WEBP']:
                 logger.warning(f"Invalid image format '{original_format}' for {team_name}.")
                 return None

            # Standardize team name for filename
            safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '_')).rstrip().lower().replace(' ', '_')
            if not safe_team_name:
                 logger.warning(f"Could not generate safe filename for '{team_name}'.")
                 return None

            # Determine save directory
            # Assumes 'assets' is at the same level as 'commands', 'services'
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if is_league:
                target_dir = os.path.join(base_dir, 'assets', 'leagues')
            # For team logos (not cappers), maybe a general 'teams' folder?
            # elif guild_id is None: # General team logo
            #     target_dir = os.path.join(base_dir, 'assets', 'teams') # Example
            else: # Capper logo (linked to guild/user previously) - adjust path as needed
                target_dir = os.path.join(base_dir, 'assets', 'logos', str(guild_id) if guild_id else 'unknown_guild')

            os.makedirs(target_dir, exist_ok=True)

            # Save as PNG for consistency, optimize
            save_filename = f"{safe_team_name}.png"
            save_path = os.path.join(target_dir, save_filename)

            # Convert to RGBA for PNG transparency support
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # Resize if needed (maintain aspect ratio)
            max_size = (200, 200) # Example max size
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save optimized image
            img.save(save_path, 'PNG', optimize=True)
            logger.info(f"Processed and saved logo to {save_path}")

            # Return relative path from base_dir for storage in DB? Or just confirm success?
            relative_path = os.path.relpath(save_path, base_dir)
            return relative_path

    except Exception as e:
        logger.exception(f"Error processing/saving logo for {team_name}: {e}")
        return None

# --- Cog Definition ---
class LoadLogosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Define the command using decorators
    # Use the 'guilds' parameter to restrict it to the test guild
    @app_commands.command(
        name="load_logos",
        description="Load team or league logos (Restricted User).",
        # Only register in the specified test guild
        guilds=[discord.Object(id=TEST_GUILD_ID)] if TEST_GUILD_ID else []
    )
    @app_commands.describe(
        team_name="The name of the team or league.",
        logo_file="The logo image file (PNG, JPG, GIF, WEBP).",
        is_league="Is this a league logo? (Default: False, for team logo)"
    )
    async def load_logos_command(
        self,
        interaction: Interaction,
        team_name: str,
        logo_file: Attachment,
        is_league: bool = False
    ):
        """Loads, processes, and saves a logo file."""

        # --- Authorization Check ---
        if not AUTHORIZED_USER_ID or interaction.user.id != AUTHORIZED_USER_ID:
            logger.warning(f"Unauthorized attempt to use load_logos by {interaction.user} ({interaction.user.id})")
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.",
                ephemeral=True
            )
            return

        if not TEST_GUILD_ID:
             await interaction.response.send_message("❌ Command disabled: TEST_GUILD_ID not configured.", ephemeral=True)
             return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            # Validate file type via content_type
            if logo_file.content_type is None or not logo_file.content_type.startswith('image/'):
                await interaction.followup.send(
                    f"❌ Invalid file type ({logo_file.content_type}). Please upload a PNG, JPG, GIF, or WEBP file.",
                    ephemeral=True
                )
                return
            # Optional: Check filename extension as well
            allowed_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
            if not logo_file.filename.lower().endswith(allowed_extensions):
                 await interaction.followup.send(
                     f"❌ Invalid file extension. Please use: {', '.join(allowed_extensions)}",
                     ephemeral=True
                 )
                 return

            # Read file bytes
            logo_bytes = await logo_file.read()

            # Run blocking Pillow code in an executor thread
            loop = asyncio.get_running_loop()
            saved_path = await loop.run_in_executor(
                None, # Default executor
                process_and_save_logo, # Function to run
                logo_bytes, # Arguments for the function
                team_name,
                is_league,
                interaction.guild_id # Pass guild_id for potential capper logo path
            )

            if saved_path:
                await interaction.followup.send(
                    f"✅ Successfully loaded and processed {'league' if is_league else 'team'} logo for **{team_name}**.\nSaved to: `{saved_path}`",
                    ephemeral=True
                )
                # TODO: Potentially update database (e.g., teams or leagues table) with the logo path here
                # await self.bot.db_manager.execute("UPDATE ... SET logo_path = $1 WHERE ...", saved_path, ...)
            else:
                # Error message already logged by process_and_save_logo
                await interaction.followup.send(
                    f"❌ Failed to process or save the logo for **{team_name}**. Check logs for details.",
                    ephemeral=True
                )

        except Exception as e:
            logger.exception(f"Error in load_logos command: {e}")
            await interaction.followup.send(
                "❌ An unexpected error occurred while loading the logo.",
                ephemeral=True
            )

    # Optional: Cog specific error handler
    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
         # Handle specific errors like CheckFailure if more checks are added
         logger.error(f"Error in LoadLogosCog command: {error}", exc_info=True)
         if not interaction.response.is_done():
              await interaction.response.send_message("An internal error occurred with the logo command.", ephemeral=True)
         else:
             try: # Try followup, might fail if interaction expired
                 await interaction.followup.send("An internal error occurred with the logo command.", ephemeral=True)
             except discord.NotFound:
                  logger.warning("Could not send error followup for load_logos (interaction expired?).")


# The setup function for the extension
async def setup(bot: commands.Bot):
    if not TEST_GUILD_ID:
         logger.warning("LoadLogosCog not loaded because TEST_GUILD_ID is not set.")
         return
    await bot.add_cog(LoadLogosCog(bot), guilds=[discord.Object(id=TEST_GUILD_ID)]) # Register with specific guild
    logger.info(f"LoadLogosCog loaded for guild {TEST_GUILD_ID}")
