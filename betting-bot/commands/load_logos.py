# betting-bot/commands/load_logos.py

import asyncio
import logging
import os
from io import BytesIO
from typing import Optional

import discord
from discord import Attachment, Interaction, app_commands
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image

logger = logging.getLogger(__name__)

# --- Configuration ---
try:
    dotenv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'
    )
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.debug(f"Loaded environment variables from: {dotenv_path}")
    else:
        logger.warning(f".env file not found: {dotenv_path}")

    TEST_GUILD_ID_STR = os.getenv('TEST_GUILD_ID')
    AUTH_USER_ID_STR = os.getenv('AUTHORIZED_LOAD_LOGO_USER_ID')

    if not TEST_GUILD_ID_STR or not AUTH_USER_ID_STR:
        logger.error("TEST_GUILD_ID or AUTH_USER_ID not set.")
        TEST_GUILD_ID = None
        AUTHORIZED_USER_ID = None
    else:
        TEST_GUILD_ID = int(TEST_GUILD_ID_STR)
        AUTHORIZED_USER_ID = int(AUTH_USER_ID_STR)
except ValueError:
    logger.error("Invalid format for TEST_GUILD_ID or AUTH_USER_ID.")
    TEST_GUILD_ID = None
    AUTHORIZED_USER_ID = None
except Exception as e:
    logger.error(f"Error loading env vars for load_logos: {e}")
    TEST_GUILD_ID = None
    AUTHORIZED_USER_ID = None

# --- Sport Category Mapping ---
# (Should be consistent with utils/image_generator.py)
SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
    "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
    "MLB": "BASEBALL", "NHL": "HOCKEY",
    "SOCCER": "SOCCER", "TENNIS": "TENNIS", "UFC/MMA": "MMA",
    # Add mappings for all leagues used, matching the keys to league_name
}
DEFAULT_SPORT_CATEGORY = "OTHER"


# --- Helper Function for Image Processing ---

def get_sport_category(league_name: str) -> str:
    """Helper to get sport category consistently."""
    return SPORT_CATEGORY_MAP.get(league_name.upper(), DEFAULT_SPORT_CATEGORY)


def process_and_save_logo(
    logo_bytes: bytes,
    name_to_save: str,
    is_league: bool,
    league_name_for_path: Optional[str] = None,
) -> Optional[str]:
    """
    Processes/saves logo to specified structure, returns relative path.

    Args:
        logo_bytes: Raw bytes of the image file.
        name_to_save: The name of the team or league to save.
        is_league: Boolean indicating if it's a league logo.
        league_name_for_path: League name (e.g., NBA, NHL) for context.

    Returns:
        Relative path from static dir if successful, else None.
    """
    try:
        with Image.open(BytesIO(logo_bytes)) as img:
            # Validate format
            allowed_formats = ['PNG', 'JPEG', 'GIF', 'WEBP']
            if img.format not in allowed_formats:
                logger.warning(f"Invalid format '{img.format}' for {name_to_save}.")
                return None

            # Base filename part (lowercase, underscore)
            safe_filename_base = name_to_save.lower().replace(' ', '_')
            if not safe_filename_base:
                logger.warning(f"Could not generate filename for '{name_to_save}'.")
                return None

            # Determine save directory based on definitive structure
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            static_dir = os.path.join(base_dir, 'static')
            logos_base_dir = os.path.join(static_dir, 'logos')

            if is_league:
                # Saving a League Logo
                # Path: static/logos/leagues/{SPORT_CATEGORY}/{LEAGUE_UPPERCASE}/{league_lower}.png
                league_name_upper = name_to_save.upper()
                league_name_lower = name_to_save.lower()
                sport_category = get_sport_category(league_name_upper)
                target_dir = os.path.join(
                    logos_base_dir, 'leagues', sport_category, league_name_upper
                )
                save_filename = f"{league_name_lower}.png"
            else:
                # Saving a Team Logo
                # Path: static/logos/teams/{SPORT_CATEGORY}/{LEAGUE_UPPERCASE}/{team_lower_underscore}.png
                if not league_name_for_path:
                    logger.error(f"League name required for team logo '{name_to_save}'.")
                    return None
                league_name_upper = league_name_for_path.upper()
                sport_category = get_sport_category(league_name_upper)
                target_dir = os.path.join(
                    logos_base_dir, 'teams', sport_category, league_name_upper
                )
                save_filename = f"{safe_filename_base}.png"

            os.makedirs(target_dir, exist_ok=True)
            save_path = os.path.join(target_dir, save_filename)

            # Process image (convert to RGBA, resize, optimize)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            max_size = (200, 200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(save_path, 'PNG', optimize=True)

            logger.info(f"Processed and saved logo to {save_path}")
            # Return path relative to static directory
            relative_path = os.path.relpath(save_path, static_dir)
            return relative_path.replace(os.sep, '/') # Use forward slashes

    except Exception as e:
        logger.exception(f"Error processing/saving logo for {name_to_save}: {e}")
        return None

# --- Cog Definition ---
class LoadLogosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="load_logos",
        description="Load team or league logos (Restricted User)."
    )
    @app_commands.describe(
        name="The name of the team or league (e.g., Lakers, NBA).",
        logo_file="The logo image file (PNG, JPG, GIF, WEBP).",
        is_league="Is this a league logo? (Default: False = team logo)",
        league_name="League code (e.g., NBA, NHL) team belongs to (Required for teams)."
    )
    async def load_logos_command(
        self,
        interaction: Interaction,
        name: str,
        logo_file: Attachment,
        is_league: bool = False,
        league_name: Optional[str] = None,
    ):
        """Loads, processes, and saves a logo file."""
        # Authorization Check
        if not AUTHORIZED_USER_ID or interaction.user.id != AUTHORIZED_USER_ID:
            msg = "❌ Unauthorized."
            await interaction.response.send_message(msg, ephemeral=True)
            return
        if not TEST_GUILD_ID:
            msg = "❌ Cmd disabled."
            await interaction.response.send_message(msg, ephemeral=True)
            return
        if not is_league and not league_name:
            msg = "❌ `league_name` (e.g., NBA, NHL) is required for TEAM logos."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            # Validate file type
            ct = logo_file.content_type
            if not ct or not ct.startswith('image/'):
                msg = f"❌ Invalid file type ({ct}). Upload PNG, JPG, GIF, WEBP."
                await interaction.followup.send(msg, ephemeral=True)
                return
            ext = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
            if not logo_file.filename.lower().endswith(ext):
                msg = f"❌ Invalid file extension. Use: {', '.join(ext)}."
                await interaction.followup.send(msg, ephemeral=True)
                return

            logo_bytes = await logo_file.read()

            # Run processing in executor
            loop = asyncio.get_running_loop()
            saved_path = await loop.run_in_executor(
                None, process_and_save_logo, logo_bytes, name, is_league, league_name
            )

            if saved_path:
                msg = (
                    f"✅ Logo for **{name}** processed.\n"
                    f"Saved relative path: `{saved_path}`"
                )
                await interaction.followup.send(msg, ephemeral=True)
            else:
                msg = f"❌ Failed to process logo for **{name}**. See logs."
                await interaction.followup.send(msg, ephemeral=True)

        except Exception as e:
            logger.exception(f"Error in load_logos command: {e}")
            await interaction.followup.send("❌ Error loading logo.", ephemeral=True)

    async def cog_app_command_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        """Handles errors for commands in this cog."""
        logger.error(f"Error in LoadLogosCog command: {error}", exc_info=True)
        if isinstance(error, app_commands.CheckFailure):
            pass # Authorization already handled basically
        err_msg = "Internal error in logo command."
        if not interaction.response.is_done():
            await interaction.response.send_message(err_msg, ephemeral=True)
        else:
            try:
                await interaction.followup.send(err_msg, ephemeral=True)
            except (discord.NotFound, discord.HTTPException) as http_err:
                logger.error(f"Failed error followup for load_logos: {http_err}")

# The setup function for the extension
async def setup(bot: commands.Bot):
    if not TEST_GUILD_ID:
        logger.warning("LoadLogosCog not loaded: TEST_GUILD_ID missing.")
        return
    if not bot.get_cog('LoadLogosCog'):
        # Use discord.Object for guild ID
        await bot.add_cog(LoadLogosCog(bot), guilds=[discord.Object(id=TEST_GUILD_ID)])
        logger.info(f"LoadLogosCog loaded for guild {TEST_GUILD_ID}")
    else:
        logger.warning("LoadLogosCog already loaded.")
