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

# Import directly from utils
from utils.image_generator import get_sport_category_for_path

logger = logging.getLogger(__name__)

# --- Configuration ---
try:
    # Adjusted path to be relative to this file's location within the package
    # betting-bot/commands/load_logos.py -> betting-bot/.env
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.debug(f"Loaded environment variables from: {dotenv_path}")
    else:
        logger.warning(f".env file not found at: {dotenv_path}. Relying on pre-set env vars.")

    TEST_GUILD_ID_STR = os.getenv('TEST_GUILD_ID')
    AUTHORIZED_USER_ID_STR = os.getenv('AUTHORIZED_LOAD_LOGO_USER_ID')

    if not TEST_GUILD_ID_STR: # AUTH_USER_ID can be optional if check is elsewhere
        logger.warning("TEST_GUILD_ID not set. load_logos command may be restricted or fail.")
        TEST_GUILD_ID = None
    else:
        TEST_GUILD_ID = int(TEST_GUILD_ID_STR)
    
    if not AUTHORIZED_USER_ID_STR:
        logger.warning("AUTHORIZED_LOAD_LOGO_USER_ID not set. Command authorization will rely on permissions only.")
        AUTHORIZED_USER_ID = None
    else:
        AUTHORIZED_USER_ID = int(AUTHORIZED_USER_ID_STR)

except ValueError:
    logger.error("Invalid format for TEST_GUILD_ID or AUTH_USER_ID in .env.")
    TEST_GUILD_ID = None
    AUTHORIZED_USER_ID = None
except Exception as e:
    logger.error(f"Error loading env vars for load_logos: {e}")
    TEST_GUILD_ID = None
    AUTHORIZED_USER_ID = None


# --- Helper Function for Image Processing ---
# get_sport_category_for_path is now imported from image_generator

def process_and_save_logo(
    logo_bytes: bytes,
    name_to_save: str, # For team: team name. For league: league code (e.g., "NHL", "NCAAF")
    is_league: bool,
    league_code_for_path: Optional[str] = None, # The league code, e.g., "NHL", "NCAAF", "NBA"
) -> Optional[str]:
    try:
        with Image.open(BytesIO(logo_bytes)) as img:
            allowed_formats = ['PNG', 'JPEG', 'GIF', 'WEBP']
            if img.format not in allowed_formats:
                logger.warning(f"Invalid format '{img.format}' for {name_to_save}.")
                return None

            safe_filename_base = name_to_save.lower().replace(' ', '_')
            if not safe_filename_base:
                logger.warning(f"Could not generate filename for '{name_to_save}'.")
                return None

            # Determine root for 'assets' or 'static' based on image_generator's preference
            # This assumes load_logos.py runs in an environment where this relative path makes sense
            # or that image_generator's _PATHS["ASSETS_DIR"] is somehow accessible globally (it's not by default)
            # For consistency, we'll reconstruct a similar logic to find 'betting-bot/assets' or 'betting-bot/static'
            
            current_script_commands_dir = os.path.dirname(os.path.abspath(__file__)) # .../betting-bot/commands
            betting_bot_dir = os.path.dirname(current_script_commands_dir) # .../betting-bot
            
            potential_assets_dir = os.path.join(betting_bot_dir, 'assets')
            potential_static_dir = os.path.join(betting_bot_dir, 'static')

            final_save_root = potential_static_dir
            logos_base_dir = os.path.join(final_save_root, 'logos')

            if is_league:
                # Saving a League Logo
                # Path: {final_save_root}/logos/leagues/{SPORT_CATEGORY_FROM_MAP}/{league_code_lower}.png
                # name_to_save is the league code, e.g., "NHL", "NCAAF"
                league_code_lower = name_to_save.lower().replace(' ', '_')
                sport_category = get_sport_category_for_path(name_to_save.upper())
                
                target_dir = os.path.join(logos_base_dir, 'leagues', sport_category)
                save_filename = f"{league_code_lower}.png"
            else:
                # Saving a Team Logo
                if not league_code_for_path:
                    logger.error(f"league_code_for_path (e.g., NHL, NCAAF) required for team logo '{name_to_save}'.")
                    return None
                
                league_code_upper = league_code_for_path.upper()

                if league_code_upper.startswith("NCAA"):
                    specific_sport_for_ncaa = get_sport_category_for_path(league_code_upper)
                    if specific_sport_for_ncaa == "OTHER_SPORTS": # Default fallback from helper
                         logger.warning(f"NCAA league '{league_code_upper}' not in SPORT_CATEGORY_MAP, using 'UNKNOWN_NCAA_SPORT'.")
                         specific_sport_for_ncaa = "UNKNOWN_NCAA_SPORT"
                    # Path: {final_save_root}/logos/teams/NCAA/{SpecificSportLikeFootball}/
                    target_dir = os.path.join(logos_base_dir, 'teams', "NCAA", specific_sport_for_ncaa)
                else:
                    # Standard leagues
                    sport_category = get_sport_category_for_path(league_code_upper)
                    # Path: {final_save_root}/logos/teams/{SportCategoryFromMap}/{LeagueCodeUppercase}/
                    target_dir = os.path.join(logos_base_dir, 'teams', sport_category, league_code_upper)
                
                # team name (name_to_save) becomes the filename base
                save_filename = f"{safe_filename_base}.png" 

            os.makedirs(target_dir, exist_ok=True)
            save_path = os.path.join(target_dir, save_filename)

            if img.mode != 'RGBA': img = img.convert('RGBA')
            max_size = (200, 200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(save_path, 'PNG', optimize=True)

            logger.info(f"Processed and saved logo to {save_path}")
            # Relative path from `final_save_root` (e.g., assets/)
            relative_path = os.path.relpath(save_path, final_save_root)
            return relative_path.replace(os.sep, '/') 

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
        name="Team name (e.g., Edmonton Oilers) or League Code (e.g., NHL).",
        logo_file="The logo image file (PNG, JPG, GIF, WEBP).",
        is_league="Is this a league logo? (Default: False = team logo)",
        league_code="League code (e.g., NHL, NCAAF) team belongs to. Required for team logos."
    )
    async def load_logos_command(
        self,
        interaction: Interaction,
        name: str,
        logo_file: Attachment,
        is_league: bool = False,
        league_code: Optional[str] = None, 
    ):
        if AUTHORIZED_USER_ID and interaction.user.id != AUTHORIZED_USER_ID : # Check if AUTH_USER_ID is set before comparing
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            return
        # Ensure guild check uses TEST_GUILD_ID if it's set
        if TEST_GUILD_ID and interaction.guild_id != TEST_GUILD_ID:
            await interaction.response.send_message("❌ This command can only be used in the configured test guild.", ephemeral=True)
            return


        if not is_league and not league_code:
            await interaction.response.send_message("❌ `league_code` (e.g., NHL, NCAAF) is required for TEAM logos.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            ct = logo_file.content_type
            if not ct or not ct.startswith('image/'):
                await interaction.followup.send(f"❌ Invalid file type ({ct}). Upload PNG, JPG, GIF, WEBP.", ephemeral=True)
                return
            ext = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
            if not logo_file.filename.lower().endswith(ext):
                await interaction.followup.send(f"❌ Invalid file extension. Use: {', '.join(ext)}.", ephemeral=True)
                return

            logo_bytes = await logo_file.read()
            loop = asyncio.get_running_loop()
            
            # Pass the league_code to be used for path construction for team logos
            # If it's a league logo, name IS the league_code
            league_code_for_path_arg = league_code if not is_league else name

            saved_path = await loop.run_in_executor(
                None, process_and_save_logo, logo_bytes, name, is_league, league_code_for_path_arg
            )

            if saved_path:
                msg = (
                    f"✅ Logo for **{name}** (Context: {'League' if is_league else f'Team in {league_code_for_path_arg}'}) processed.\n"
                    f"Attempted save path relative to assets/static: `{saved_path}`\n"
                    f"Please verify the file exists at the expected absolute path on the server."
                )
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Failed to process logo for **{name}**. Check logs.", ephemeral=True)

        except Exception as e:
            logger.exception(f"Error in load_logos command: {e}")
            await interaction.followup.send("❌ Error loading logo.", ephemeral=True)

    async def cog_app_command_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        logger.error(f"Error in LoadLogosCog command: {error}", exc_info=True)
        if isinstance(error, app_commands.CheckFailure):
             pass 
        err_msg = "Internal error in logo command."
        if not interaction.response.is_done():
            await interaction.response.send_message(err_msg, ephemeral=True)
        else:
            try: await interaction.followup.send(err_msg, ephemeral=True)
            except: pass

async def setup(bot: commands.Bot):
    if not TEST_GUILD_ID:
        logger.warning("LoadLogosCog not loaded: TEST_GUILD_ID missing or invalid in .env.")
        return
    
    # Register the cog as a guild command for Cookin' Books
    guild = discord.Object(id=TEST_GUILD_ID)
    await bot.add_cog(LoadLogosCog(bot), guilds=[guild])
    logger.info(f"LoadLogosCog loaded as guild command for guild {TEST_GUILD_ID}")
