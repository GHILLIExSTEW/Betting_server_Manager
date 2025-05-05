# betting-bot/commands/load_logos.py

import discord
from discord import app_commands, Interaction, Attachment # Import specific types
from discord.ext import commands # Import commands for Cog
import os
import logging
from typing import Optional
from PIL import Image # Keep Pillow import
import asyncio # For running blocking code in executor
from io import BytesIO # Need BytesIO import

logger = logging.getLogger(__name__)

# --- Configuration ---
# Get required IDs from environment variables for security
# Ensure these are set in your .env file
try:
    import os
    from dotenv import load_dotenv
    # Load .env from parent directory relative to this file
    # Adjust path if needed based on your execution context
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.debug(f"Loaded environment variables from: {dotenv_path}")
    else:
        logger.warning(f".env file not found at {dotenv_path}, environment variables may be missing.")

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

# Copy the sport category mapping from image_generator.py (or import if centralized)
# Ensure keys match the league_name parameter format (e.g., upper/lowercase)
SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
    "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
    "MLB": "BASEBALL",
    "NHL": "HOCKEY",
    "SOCCER": "SOCCER", # Assuming league_name passed as 'Soccer'
    "TENNIS": "TENNIS", # Assuming league_name passed as 'Tennis'
    "UFC/MMA": "MMA"    # Assuming league_name passed as 'UFC/MMA'
    # Add other leagues/sports as needed, ensure keys match how league_name is provided
}
# Default category if league not in map
DEFAULT_SPORT_CATEGORY = "OTHER"

def process_and_save_logo(
    logo_bytes: bytes,
    team_name: str,        # This is the name of the team OR the league being saved
    is_league: bool,
    league_name: Optional[str] = None # The name of the league the TEAM belongs to
    ) -> Optional[str]:
    """Processes and saves logo, returns relative save path or None on failure."""
    try:
        with Image.open(BytesIO(logo_bytes)) as img:
            # Validate format
            original_format = img.format
            if original_format not in ['PNG', 'JPEG', 'GIF', 'WEBP']:
                logger.warning(f"Invalid image format '{original_format}' for {team_name}.")
                return None

            # Standardize team/league name for filename to match image_generator
            safe_name = team_name.lower().replace(' ', '_')
            if not safe_name:
                logger.warning(f"Could not generate safe filename for '{team_name}'.")
                return None

            # Determine save directory based on the structure image_generator expects
            # Assumes 'static' is in the 'betting-bot' directory relative to main.py
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # betting-bot directory
            static_dir = os.path.join(base_dir, 'static')
            logos_base_dir = os.path.join(static_dir, 'logos')

            if is_league:
                # Save league logos to static/logos/leagues/<LEAGUE_NAME_UPPER>/
                # For a league logo, team_name IS the league name
                league_name_for_path = team_name.upper()
                target_dir = os.path.join(logos_base_dir, 'leagues', league_name_for_path)
                save_filename = f"{safe_name}.png" # League logo filename often matches league name

            else:
                # Save team logos to static/logos/teams/<SPORT_CATEGORY>/<LEAGUE_NAME_UPPER>/
                if not league_name:
                    # This case should be prevented by the command check, but added for safety
                    logger.error(f"Programming Error: League name is required to save team logo for '{team_name}'.")
                    return None

                # Determine sport category based on league_name
                # Use upper() for matching the map keys
                sport_category = SPORT_CATEGORY_MAP.get(league_name.upper(), DEFAULT_SPORT_CATEGORY)
                league_dir_name = league_name.upper() # League name part of the path is uppercase
                target_dir = os.path.join(logos_base_dir, 'teams', sport_category, league_dir_name)
                save_filename = f"{safe_name}.png" # Team logo filename is team name

            os.makedirs(target_dir, exist_ok=True)
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

            # Return relative path from the static directory
            relative_path = os.path.relpath(save_path, static_dir)
            # Use forward slashes for consistency (especially if paths are used in web contexts)
            return relative_path.replace(os.sep, '/')

    except Exception as e:
        logger.exception(f"Error processing/saving logo for {team_name}: {e}")
        return None

# --- Cog Definition ---
class LoadLogosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Define the command using decorators
    @app_commands.command(
        name="load_logos",
        description="Load team or league logos (Restricted User)."
    )
    @app_commands.describe(
        name="The name of the team or league.",
        logo_file="The logo image file (PNG, JPG, GIF, WEBP).",
        is_league="Is this a league logo? (Default: False, for team logo)",
        league_name="The LEAGUE name (e.g., NHL, NFL) this TEAM belongs to (Required for team logos)."
    )
    async def load_logos_command(
        self,
        interaction: Interaction,
        name: str,
        logo_file: Attachment,
        is_league: bool = False,
        league_name: Optional[str] = None # Made optional, but required if is_league is False
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

        # Validate league_name requirement for team logos
        if not is_league and not league_name:
            await interaction.response.send_message(
                "❌ The `league_name` parameter is required when adding a TEAM logo.",
                ephemeral=True
            )
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
            # Pass league_name which is required for team logos now in process_and_save_logo
            saved_path = await loop.run_in_executor(
                None, # Default executor
                process_and_save_logo, # Function to run
                logo_bytes, # Arguments for the function
                name, # Use 'name' parameter which is team or league name
                is_league,
                league_name # Pass the league name for path generation
            )

            if saved_path:
                await interaction.followup.send(
                    f"✅ Successfully loaded and processed {'league' if is_league else 'team'} logo for **{name}**.\nSaved relative to static dir: `{saved_path}`",
                    ephemeral=True
                )
                # Optional: Update database (e.g., teams or leagues table) with the logo path here
                # Example:
                # db_manager = self.bot.db_manager # Assuming db_manager is attached to bot
                # if is_league:
                #     await db_manager.execute("UPDATE leagues SET logo=%s WHERE name=%s", saved_path, name)
                # else:
                #     # Find the correct team ID first if needed, then update based on team_id and league_id
                #     await db_manager.execute("UPDATE teams SET logo=%s WHERE name=%s AND league_name=%s", saved_path, name, league_name)
            else:
                # Error message already logged by process_and_save_logo
                await interaction.followup.send(
                    f"❌ Failed to process or save the logo for **{name}**. Check logs for details.",
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
        # Check if response already sent
        if not interaction.response.is_done():
            await interaction.response.send_message("An internal error occurred with the logo command.", ephemeral=True)
        else:
            try: # Try followup, might fail if interaction expired
                await interaction.followup.send("An internal error occurred with the logo command.", ephemeral=True)
            except discord.NotFound:
                logger.warning("Could not send error followup for load_logos (interaction expired?).")
            except discord.HTTPException as http_err:
                 logger.error(f"Failed to send error followup for load_logos: {http_err}")


# The setup function for the extension
async def setup(bot: commands.Bot):
    if not TEST_GUILD_ID:
        logger.warning("LoadLogosCog not loaded because TEST_GUILD_ID is not set.")
        return
    # Ensure the cog is added only once if setup is called multiple times
    if not bot.get_cog('LoadLogosCog'):
        # Use discord.Object for guild ID
        await bot.add_cog(LoadLogosCog(bot), guilds=[discord.Object(id=TEST_GUILD_ID)])
        logger.info(f"LoadLogosCog loaded for guild {TEST_GUILD_ID}")
    else:
        logger.warning("LoadLogosCog already loaded.")
