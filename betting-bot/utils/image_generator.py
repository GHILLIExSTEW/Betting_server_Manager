# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import time
import io # Make sure io is imported

logger = logging.getLogger(__name__)

# --- Sport Category Mapping (Defined Globally) ---
SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
    "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
    "MLB": "BASEBALL", "NCAAB_BASEBALL": "BASEBALL", # Added for consistency if used
    "NHL": "HOCKEY",
    "MLS": "SOCCER", "EPL": "SOCCER", "LA LIGA": "SOCCER", "SERIE A": "SOCCER", "BUNDESLIGA": "SOCCER", "LIGUE 1": "SOCCER",
    "TENNIS": "TENNIS",
    "UFC": "MMA", "MMA": "MMA",
    "DARTS": "DARTS"
    # Add other leagues/sports as needed
}
DEFAULT_FALLBACK_SPORT_CATEGORY = "OTHER_SPORTS" # For leagues not in map

# Helper function to get sport category for path construction
def get_sport_category_for_path(league_name: str) -> str:
    """Gets the sport category string for use in paths, using the global map."""
    return SPORT_CATEGORY_MAP.get(str(league_name).upper(), DEFAULT_FALLBACK_SPORT_CATEGORY)

# --- Default Font/Asset Path Logic (Global Scope Helper) ---
def _determine_asset_paths():
    assets_dir_default = "betting-bot/static/"
    font_dir_name = 'fonts'
    logo_dir_name = 'logos'
    teams_subdir_name = 'teams'
    leagues_subdir_name = 'leagues'

    script_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(script_dir)
    potential_assets_dir = os.path.join(parent_dir, 'assets')
    potential_static_dir = os.path.join(parent_dir, 'static')

    final_assets_dir = None
    # Check for 'assets' first, then 'static'
    if os.path.isdir(potential_assets_dir):
        final_assets_dir = potential_assets_dir
    elif os.path.isdir(potential_static_dir):
        final_assets_dir = potential_static_dir
    else:
        # If neither is found relative to script, try using the default path
        # This assumes the script might be run from the betting-bot root directory
        if os.path.isdir(assets_dir_default):
             final_assets_dir = assets_dir_default
        else:
             # Last resort, use current working directory + assets (might be incorrect)
             final_assets_dir = os.path.join(os.getcwd(), 'assets')
             logger.warning(f"Could not find 'assets' or 'static' relative to script or default path. Assuming assets path: {final_assets_dir}")

    logger.info(f"Path determination logic targeting base: {final_assets_dir}")

    paths = {
        "ASSETS_DIR": final_assets_dir,
        "DEFAULT_FONT_PATH": os.path.join(final_assets_dir, font_dir_name, 'Roboto-Regular.ttf'),
        "DEFAULT_BOLD_FONT_PATH": os.path.join(final_assets_dir, font_dir_name, 'Roboto-Bold.ttf'),
        "DEFAULT_EMOJI_FONT_PATH_NOTO": os.path.join(final_assets_dir, font_dir_name, 'NotoEmoji-Regular.ttf'),
        "DEFAULT_EMOJI_FONT_PATH_SEGOE": os.path.join(final_assets_dir, font_dir_name, 'SegoeUIEmoji.ttf'),
        "LEAGUE_TEAM_BASE_DIR": os.path.join(final_assets_dir, logo_dir_name, teams_subdir_name),
        "LEAGUE_LOGO_BASE_DIR": os.path.join(final_assets_dir, logo_dir_name, leagues_subdir_name),
        "DEFAULT_LOCK_ICON_PATH": os.path.join(final_assets_dir, "lock_icon.png"),
        "DEFAULT_TEAM_LOGO_PATH": os.path.join(final_assets_dir, logo_dir_name, 'default_logo.png')
    }
    return paths

_PATHS = _determine_asset_paths()

# --- Font Loading (Global Scope) ---
# Load fonts using paths determined above, with fallbacks
try:
    # Determine best available default font
    _font_path = _PATHS["DEFAULT_FONT_PATH"]
    if not os.path.exists(_font_path):
        logger.warning(f"Default font '{_font_path}' not found. Falling back.")
        if os.name == 'nt': _font_path = 'C:\\Windows\\Fonts\\arial.ttf' # Windows fallback
        else: # Linux/MacOS fallbacks
            _found = False
            for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']:
                if os.path.exists(p): _font_path = p; _found=True; break
            if not _found: _font_path = 'arial.ttf' # Final guess if others not found
    logger.info(f"Using regular font: {_font_path}")

    # Determine best available bold font
    _bold_font_path = _PATHS["DEFAULT_BOLD_FONT_PATH"]
    if not os.path.exists(_bold_font_path):
        logger.warning(f"Default bold font '{_bold_font_path}' not found. Trying bold variant of regular font or falling back.")
        # Attempt to find a bold variant automatically (may not work reliably)
        _bold_font_path_try = _font_path.replace("Regular", "Bold").replace(".ttf", "-Bold.ttf") # Simple replacement logic
        # More robust check for common bold suffixes
        if not os.path.exists(_bold_font_path_try):
             _bold_font_path_try = _font_path.replace(".ttf", "bd.ttf") # Another common pattern
        if not os.path.exists(_bold_font_path_try):
             _bold_font_path_try = _font_path.replace(".ttf", "-Bold.otf") # Check .otf too
        # Add more patterns if needed

        if os.path.exists(_bold_font_path_try):
            _bold_font_path = _bold_font_path_try
        else: # Fallback to regular font if bold variant not found easily
             _bold_font_path = _font_path
             logger.info("Using regular font as bold fallback.")
    logger.info(f"Using bold font: {_bold_font_path}")


    # Determine best available emoji font
    _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"]
    if not os.path.exists(_emoji_font_path):
        _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_SEGOE"]
        if not os.path.exists(_emoji_font_path):
            logger.warning(f"Default Noto/Segoe emoji fonts not found. Falling back.")
            if os.name == 'nt': _emoji_font_path = 'C:\\Windows\\Fonts\\seguiemj.ttf' # Windows Emoji font
            else: # Linux/MacOS fallbacks
                _found = False
                # Common paths for Noto Color Emoji
                for p in ['/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf']:
                     if os.path.exists(p): _emoji_font_path = p; _found=True; break
                if not _found: _emoji_font_path = _font_path # Fallback to regular if no emoji font found
    logger.info(f"Using emoji font: {_emoji_font_path}")


    # Load fonts globally using the determined paths
    font_m_18 = ImageFont.truetype(_font_path, 18)
    font_m_24 = ImageFont.truetype(_font_path, 24)
    font_b_18 = ImageFont.truetype(_bold_font_path, 18)
    font_b_24 = ImageFont.truetype(_bold_font_path, 24)
    font_b_36 = ImageFont.truetype(_bold_font_path, 36)
    # Ensure font_b_28 exists or falls back gracefully
    try:
        font_b_28 = ImageFont.truetype(_bold_font_path, 28)
    except IOError:
        logger.warning("Could not load bold font at size 28, using size 24 as fallback.")
        font_b_28 = font_b_24
    # Load emoji font, fallback to regular if path is invalid
    try:
        emoji_font_24 = ImageFont.truetype(_emoji_font_path, 24)
    except IOError:
        logger.warning(f"Could not load emoji font '{_emoji_font_path}', falling back to regular font for emojis.")
        emoji_font_24 = font_m_24 # Fallback to regular size 24

    logger.info("Successfully loaded fonts globally for image_generator.")
except Exception as e:
    logger.critical(f"CRITICAL: Error loading required fonts: {e}", exc_info=True)
    # Set fonts to default PIL font to allow continuation, but log critical error
    font_m_18 = font_m_24 = font_b_18 = font_b_24 = font_b_36 = font_b_28 = emoji_font_24 = ImageFont.load_default()


class BetSlipGenerator:
    def __init__(self, font_path: Optional[str] = None, emoji_font_path: Optional[str] = None, assets_dir: Optional[str] = None):
        # Use determined paths from global scope
        self.assets_dir = assets_dir or _PATHS["ASSETS_DIR"]
        self.font_path = font_path or _PATHS["DEFAULT_FONT_PATH"] # Use determined default
        self.bold_font_path = _PATHS["DEFAULT_BOLD_FONT_PATH"] # Use determined default
        self.emoji_font_path = emoji_font_path or _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"] # Use determined default

        self.league_team_base_dir = _PATHS["LEAGUE_TEAM_BASE_DIR"]
        self.league_logo_base_dir = _PATHS["LEAGUE_LOGO_BASE_DIR"]

        # Ensure base directories exist
        os.makedirs(self.league_team_base_dir, exist_ok=True)
        os.makedirs(self.league_logo_base_dir, exist_ok=True)

        # Initialize caches
        self._logo_cache = {}
        self._font_cache = {}
        self._lock_icon_cache = None
        self._max_cache_size = 100
        self._cache_expiry = 3600 # 1 hour
        self._last_cache_cleanup = time.time()

        # Set dimensions
        self.width = 800
        self.leg_height = 120
        self.header_height = 100
        self.footer_height = 80
        self.padding = 20
        self.logo_size = 60
        self.image = None

        # Use globally loaded fonts
        self.font_m_18 = font_m_18
        self.font_m_24 = font_m_24
        self.font_b_18 = font_b_18
        self.font_b_24 = font_b_24
        self.font_b_28 = font_b_28 # Use globally loaded/fallback font
        self.font_b_36 = font_b_36
        self.emoji_font_24 = emoji_font_24

        logger.info(f"BetSlipGenerator initialized with determined assets_dir: {self.assets_dir}")

    # Removed redundant _get_default font methods, using globals

    def _format_odds_with_sign(self, odds: Optional[Any]) -> str:
        """Formats odds, adding a '+' for positive values. Handles None/non-numeric."""
        if odds is None: return "N/A"
        try:
            odds_num = int(float(odds)) # Attempt conversion
            if odds_num > 0: return f"+{odds_num}"
            return str(odds_num)
        except (ValueError, TypeError):
            logger.warning(f"Could not format odds, invalid value: {odds}")
            return "N/A"

    def _ensure_team_dir_exists(self, league: str) -> str:
        """Ensure team logo directory exists and return path.
        Handles standard leagues like NHL and special structures for NCAA.
        Example NHL: league="NHL" -> {assets_dir}/logos/teams/HOCKEY/NHL/
        Example NCAAF: league="NCAAF" -> {assets_dir}/logos/teams/NCAA/FOOTBALL/
        """
        league_upper = league.upper() # e.g. "NHL", "NCAAF"

        # self.league_team_base_dir is already determined using _PATHS
        # Path structure: {base_dir}/logos/teams/...

        if league_upper.startswith("NCAA"):
            specific_sport_for_ncaa = get_sport_category_for_path(league_upper)
            if specific_sport_for_ncaa == DEFAULT_FALLBACK_SPORT_CATEGORY:
                logger.warning(f"NCAA league '{league_upper}' not mapped, using 'UNKNOWN_NCAA_SPORT'.")
                specific_sport_for_ncaa = "UNKNOWN_NCAA_SPORT"
            # Path: .../logos/teams/NCAA/{SpecificSport}/
            team_dir = os.path.join(self.league_team_base_dir, "NCAA", specific_sport_for_ncaa)
        else:
            sport_category = get_sport_category_for_path(league_upper)
            # Path: .../logos/teams/{SportCategory}/{LeagueCodeUppercase}/
            team_dir = os.path.join(self.league_team_base_dir, sport_category, league_upper)

        os.makedirs(team_dir, exist_ok=True)
        return team_dir

    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        if current_time - self._last_cache_cleanup > 300: # Check every 5 minutes
            expired_keys = [k for k, (_, ts) in self._logo_cache.items() if current_time - ts > self._cache_expiry]
            if expired_keys:
                 for key in expired_keys:
                     try: del self._logo_cache[key]
                     except KeyError: pass
                 logger.debug(f"Cache cleanup removed {len(expired_keys)} expired logo entries.")
            self._last_cache_cleanup = current_time

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Load the team logo image based on team name and league with caching."""
        if not team_name or not league:
             logger.warning("Attempted to load team logo with missing team_name or league.")
             return None
        try:
            cache_key = f"team_{team_name}_{league}"
            current_time = time.time()

            # Check cache first
            if cache_key in self._logo_cache:
                logo, timestamp = self._logo_cache[cache_key]
                if current_time - timestamp <= self._cache_expiry:
                    # logger.debug(f"Cache hit for team logo: {cache_key}")
                    return logo
                else:
                    # logger.debug(f"Cache expired for team logo: {cache_key}")
                    del self._logo_cache[cache_key]

            # Determine directory and filename
            league_team_dir = self._ensure_team_dir_exists(league)
            # Normalize team name for filename: lowercase, space to underscore
            logo_filename_base = team_name.lower().replace(" ", "_")
            logo_filename = f"{logo_filename_base}.png" # Assume PNG
            logo_path = os.path.join(league_team_dir, logo_filename)

            # --- START REFINED LOGGING ---
            absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info(f"Attempting to load team logo: Path='{absolute_logo_path}', Exists={file_exists}")
            # --- END REFINED LOGGING ---

            logo_to_cache = None
            if file_exists: # Use the checked variable
                try:
                    # Use the absolute path for opening the file
                    loaded_logo = Image.open(absolute_logo_path).convert("RGBA")
                    # loaded_logo = loaded_logo.resize((100, 100), Image.Resampling.LANCZOS) # Resize if needed later
                    logo_to_cache = loaded_logo # Cache the loaded logo
                except Exception as e:
                    logger.error(f"Error loading logo from existing path {absolute_logo_path}: {str(e)}")
                    # Fall through to default logo logic

            # If file didn't exist or failed to load, try default
            if logo_to_cache is None:
                default_logo_path = _PATHS["DEFAULT_TEAM_LOGO_PATH"]
                abs_default_logo_path = os.path.abspath(default_logo_path)
                if os.path.exists(abs_default_logo_path):
                    try:
                        default_logo = Image.open(abs_default_logo_path).convert("RGBA")
                        # default_logo = default_logo.resize((100, 100), Image.Resampling.LANCZOS) # Resize if needed later
                        logger.warning(f"Using default logo for team {team_name} (logo not found or failed to load at {absolute_logo_path})")
                        logo_to_cache = default_logo # Use default logo
                    except Exception as e:
                        logger.error(f"Error loading default logo from {abs_default_logo_path}: {str(e)}")
                else:
                     logger.warning(f"Default team logo not found at {abs_default_logo_path}")

            # Update cache if a logo (specific or default) was successfully loaded
            if logo_to_cache:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    # Simple LRU-like eviction
                    try: # Ensure cache isn't empty before using min
                         if self._logo_cache:
                             oldest_key = min(self._logo_cache.items(), key=lambda item: item[1][1])[0]
                             del self._logo_cache[oldest_key]
                             logger.debug(f"Cache full, evicted oldest entry: {oldest_key}")
                         else:
                             logger.warning("Cache full, but no entries to evict.")
                    except Exception as evict_err:
                         logger.error(f"Error evicting from logo cache: {evict_err}")

                self._logo_cache[cache_key] = (logo_to_cache, current_time)
                return logo_to_cache
            else:
                 # Log final failure if neither specific nor default logo worked
                 logger.warning(f"Final result: No logo loaded for team '{team_name}' in league '{league}' (path checked: {absolute_logo_path})")
                 return None

        except Exception as e:
            logger.error(f"Unexpected error in _load_team_logo for team {team_name}, league {league}: {str(e)}", exc_info=True)
            return None

    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Load the lock icon image with caching."""
        if self._lock_icon_cache is None:
            try:
                lock_icon_path = _PATHS["DEFAULT_LOCK_ICON_PATH"]
                abs_lock_icon_path = os.path.abspath(lock_icon_path)
                if os.path.exists(abs_lock_icon_path):
                    with Image.open(abs_lock_icon_path) as lock:
                        lock = lock.convert("RGBA")
                        lock = lock.resize((30, 30), Image.Resampling.LANCZOS)
                        self._lock_icon_cache = lock.copy() # Cache the processed icon
                else:
                    logger.warning(f"Lock icon not found at {abs_lock_icon_path}")
            except Exception as e:
                logger.error(f"Error loading lock icon: {str(e)}")
        return self._lock_icon_cache

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        """Load the league logo image with caching."""
        if not league:
             logger.warning("Attempted to load league logo with empty league name.")
             return None
        try:
            cache_key = f"league_{league}"
            current_time = time.time()

            # Check cache first
            if cache_key in self._logo_cache:
                logo, timestamp = self._logo_cache[cache_key]
                if current_time - timestamp <= self._cache_expiry:
                    # logger.debug(f"Cache hit for league logo: {cache_key}")
                    return logo
                else:
                    # logger.debug(f"Cache expired for league logo: {cache_key}")
                    del self._logo_cache[cache_key]

            # Determine directory and filename
            sport_category = get_sport_category_for_path(league.upper())
            logo_filename = f"{league.lower().replace(' ', '_')}.png" # Assume PNG
            logo_dir = os.path.join(self.league_logo_base_dir, sport_category)
            logo_path = os.path.join(logo_dir, logo_filename)

            # Ensure directory exists
            os.makedirs(logo_dir, exist_ok=True)

            # --- START REFINED LOGGING ---
            absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info(f"Attempting to load league logo: Path='{absolute_logo_path}', Exists={file_exists}")
            # --- END REFINED LOGGING ---

            logo_to_cache = None
            if file_exists: # Use the checked variable
                try:
                    # Use absolute path for opening
                    with Image.open(absolute_logo_path) as img:
                        loaded_logo = img.convert('RGBA')
                        logo_to_cache = loaded_logo # Cache the loaded logo
                except Exception as e:
                    logger.error(f"Error loading league logo from existing path {absolute_logo_path}: {str(e)}")
                    # Fall through to warning

            # Update cache if a logo was successfully loaded
            if logo_to_cache:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    try: # Ensure cache isn't empty before using min
                        if self._logo_cache:
                            oldest_key = min(self._logo_cache.items(), key=lambda item: item[1][1])[0]
                            del self._logo_cache[oldest_key]
                            logger.debug(f"Cache full, evicted oldest entry: {oldest_key}")
                        else:
                            logger.warning("Cache full, but no entries to evict.")
                    except Exception as evict_err:
                         logger.error(f"Error evicting from logo cache: {evict_err}")
                self._logo_cache[cache_key] = (logo_to_cache.copy(), current_time) # Cache a copy
                return logo_to_cache
            else:
                logger.warning(f"No logo found for league {league} (path checked: {absolute_logo_path})")
                return None

        except Exception as e:
            logger.error(f"Unexpected error in _load_league_logo for league {league}: {str(e)}", exc_info=True)
            return None

    def generate_bet_slip(
        self,
        home_team: str, away_team: str, league: Optional[str], line: str, odds: float,
        units: float, bet_id: str, timestamp: datetime, bet_type: str = "straight",
        parlay_legs: Optional[List[Dict[str, Any]]] = None, is_same_game: bool = False
    ) -> Optional[Image.Image]:
        """Generate a bet slip image for straight or parlay bets."""
        # Ensure league is provided for logo loading, default if None
        effective_league = league or "UNKNOWN_LEAGUE"
        logger.info(f"Generating bet slip - Type: {bet_type}, League: {effective_league}, BetID: {bet_id}")

        try:
            width = 800
            header_h = 100
            footer_h = 80
            leg_draw_height = 180 # Height allocated per leg in parlay section
            num_legs = len(parlay_legs) if parlay_legs else 1
            # Calculate dynamic height based on bet type
            if bet_type == "parlay" and parlay_legs:
                content_height = num_legs * leg_draw_height # Height for all legs
                parlay_total_section_height = 120 # Extra space for total odds/stake
            else: # Straight bet
                content_height = 400 # Fixed height for straight bet content
                parlay_total_section_height = 0

            height = header_h + content_height + parlay_total_section_height + footer_h

            image = Image.new('RGBA', (width, height), (40, 40, 40, 255))
            draw = ImageDraw.Draw(image)

            # --- Header ---
            header_y = 30 # Initial Y position for header content
            # Title logic based on user preference and bet type
            if bet_type == 'parlay':
                header_text_base = f"{effective_league.upper()} - {'Same Game Parlay' if is_same_game else 'Multi-Team Parlay Bet'}"
            else: # straight or other
                header_text_base = f"{effective_league.upper()} - Straight Bet"

            header_text = header_text_base.strip(" - ")

            # Draw League Logo if available
            league_logo_img = self._load_league_logo(effective_league)
            if league_logo_img:
                max_league_logo_h = 60
                ratio = min(max_league_logo_h / league_logo_img.height, 1.0) # Avoid upscaling
                new_w = int(league_logo_img.width * ratio)
                new_h = int(league_logo_img.height * ratio)
                league_logo_disp = league_logo_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                logo_x = (width - league_logo_disp.width) // 2
                logo_y = header_y - 10 # Position logo slightly above text baseline
                if image.mode != 'RGBA': image = image.convert("RGBA")
                temp_layer = Image.new('RGBA', image.size, (0,0,0,0))
                temp_layer.paste(league_logo_disp, (logo_x, logo_y), league_logo_disp)
                image = Image.alpha_composite(image, temp_layer)
                draw = ImageDraw.Draw(image) # Recreate draw object after image modification
                header_y += league_logo_disp.height + 5 # Move text baseline down
            else:
                header_y += 10 # Add padding if no logo

            # Draw Header Text
            bbox = draw.textbbox((0, 0), header_text, font=self.font_b_36)
            tw = bbox[2] - bbox[0]
            draw.text(((width - tw) / 2, header_y), header_text, fill='white', font=self.font_b_36)

            # --- Content Section ---
            content_start_y = header_h + 10 # Start content below header

            if bet_type == "straight":
                logo_y_start = content_start_y + 40 # Y position for team logos
                logo_size = (120, 120) # Target size for team logos

                # Load team logos
                home_logo = self._load_team_logo(home_team, effective_league)
                away_logo = self._load_team_logo(away_team, effective_league)

                # Draw Home Team Logo and Name
                if home_logo:
                    home_logo_disp = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    temp_layer_home = Image.new('RGBA', image.size, (0,0,0,0))
                    # Center logo in the left quarter
                    temp_layer_home.paste(home_logo_disp, (width // 4 - logo_size[0] // 2, logo_y_start), home_logo_disp)
                    image = Image.alpha_composite(image, temp_layer_home)
                    draw = ImageDraw.Draw(image)
                draw.text((width // 4, logo_y_start + logo_size[1] + 20), home_team, fill='white', font=self.font_b_24, anchor='mm')

                # Draw Away Team Logo and Name
                if away_logo:
                    away_logo_disp = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    temp_layer_away = Image.new('RGBA', image.size, (0,0,0,0))
                    # Center logo in the right quarter
                    temp_layer_away.paste(away_logo_disp, (3 * width // 4 - logo_size[0] // 2, logo_y_start), away_logo_disp)
                    image = Image.alpha_composite(image, temp_layer_away)
                    draw = ImageDraw.Draw(image)
                draw.text((3 * width // 4, logo_y_start + logo_size[1] + 20), away_team, fill='white', font=self.font_b_24, anchor='mm')

                # Draw Bet Details (Line, Odds, Units)
                details_y = logo_y_start + logo_size[1] + 80 # Start drawing details below names
                bet_text = f"{home_team}: {line}" # Example, adjust based on actual line format
                draw.text((width // 2, details_y), bet_text, fill='white', font=self.font_m_24, anchor='mm')

                separator_y = details_y + 40
                draw.line([(20, separator_y), (width - 20, separator_y)], fill='white', width=2)

                odds_y = separator_y + 30
                odds_text_display = self._format_odds_with_sign(odds)
                draw.text((width // 2, odds_y), odds_text_display, fill='white', font=self.font_b_24, anchor='mm')

                units_y = odds_y + 50
                units_text = f"To Win {units:.2f} Units" # 'units' here means payout for straight bets
                units_bbox = draw.textbbox((0, 0), units_text, font=self.font_b_24)
                units_width = units_bbox[2] - units_bbox[0]

                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 20
                    text_total_width = units_width + 2 * lock_icon.width + 2 * lock_spacing
                    start_x = (width - text_total_width) // 2

                    if image.mode != 'RGBA': image = image.convert('RGBA')
                    temp_lock_l = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_lock_l.paste(lock_icon, (start_x, int(units_y - lock_icon.height / 2)), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_l)
                    draw = ImageDraw.Draw(image) # Recreate draw object

                    text_x = start_x + lock_icon.width + lock_spacing
                    draw.text((text_x + units_width / 2, units_y), units_text, fill=(255, 215, 0), font=self.font_b_24, anchor="mm") # Center text

                    temp_lock_r = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_lock_r.paste(lock_icon, (int(text_x + units_width + lock_spacing), int(units_y - lock_icon.height / 2)), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_r)
                    draw = ImageDraw.Draw(image) # Recreate draw object
                else:
                    # Fallback text if lock icon fails to load
                    draw.text((width // 2, units_y), units_text, fill=(255, 215, 0), font=self.font_b_24, anchor='mm')

            elif bet_type == "parlay" and parlay_legs:
                current_y_parlay = content_start_y
                for i, leg_data in enumerate(parlay_legs):
                    if i > 0:
                        separator_y = current_y_parlay
                        draw.line([(40, separator_y), (width - 40, separator_y)], fill=(100, 100, 100), width=1)
                        current_y_parlay += 20 # Space after separator

                    leg_effective_league = leg_data.get('league', effective_league)
                    # Draw the leg, returns the y-coord for the start of the *next* leg
                    next_leg_start_y = self._draw_parlay_leg_internal(
                        image=image, draw=draw, leg=leg_data, league=leg_effective_league,
                        width=width, start_y=current_y_parlay,
                        is_same_game=is_same_game, leg_height=leg_draw_height # Pass allocated height
                    )
                    # Update the main image and draw object IF the helper modified them
                    draw = ImageDraw.Draw(image) # Recreate draw object to be safe
                    current_y_parlay = next_leg_start_y # Move cursor down

                # Draw Total Odds and Stake below the legs
                total_y = current_y_parlay # Start right after the last leg's allocated space
                draw.line([(40, total_y), (width - 40, total_y)], fill='white', width=2)
                total_y += 30

                total_odds_text = f"Total Odds: {self._format_odds_with_sign(odds)}" # Use overall parlay odds
                draw.text((width // 2, total_y), total_odds_text, fill='white', font=self.font_b_28, anchor='mm')
                total_y += 40

                units_text = f"Stake: {units:.2f} Units" # 'units' for parlay is the stake amount
                units_bbox = draw.textbbox((0, 0), units_text, font=self.font_b_24)
                units_width = units_bbox[2] - units_bbox[0]
                lock_icon = self._load_lock_icon()

                if lock_icon:
                    lock_spacing = 15
                    text_total_width = units_width + 2 * lock_icon.width + 2 * lock_spacing
                    lock_x_left = (width - text_total_width) // 2
                    if image.mode != 'RGBA': image = image.convert("RGBA")

                    temp_lock_l_parlay = Image.new('RGBA', image.size, (0,0,0,0)) # Unique name
                    temp_lock_l_parlay.paste(lock_icon, (lock_x_left, int(total_y - lock_icon.height / 2)), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_l_parlay)
                    draw = ImageDraw.Draw(image)

                    text_x_parlay = lock_x_left + lock_icon.width + lock_spacing
                    draw.text((text_x_parlay + units_width / 2, total_y), units_text, fill=(255, 215, 0), font=self.font_b_24, anchor='mm') # Center text

                    temp_lock_r_parlay = Image.new('RGBA', image.size, (0,0,0,0)) # Unique name
                    lock_x_right = text_x_parlay + units_width + lock_spacing
                    temp_lock_r_parlay.paste(lock_icon, (lock_x_right, int(total_y - lock_icon.height / 2)), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_r_parlay)
                    draw = ImageDraw.Draw(image)
                else:
                    # Fallback if lock icon fails
                    draw.text((width // 2, total_y), f"🔒 {units_text} 🔒",
                              fill=(255, 215, 0), font=self.emoji_font_24, anchor='mm')
            else:
                 # Handle unexpected bet_type or missing parlay_legs if needed
                 header_font_fallback = self.font_b_36
                 draw.text((width // 2, height // 2), "Invalid Bet Data", fill='red', font=header_font_fallback, anchor='mm')

            # --- Footer ---
            footer_y_pos = height - footer_h // 2 # Center vertically in footer area
            bet_id_text = f"Bet #{bet_id}"
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC')

            draw.text((self.padding, footer_y_pos), bet_id_text, fill=(150, 150, 150), font=self.font_m_18, anchor='lm')
            draw.text((width - self.padding, footer_y_pos), timestamp_text, fill=(150, 150, 150), font=self.font_m_18, anchor='rm')

            logger.info(f"Bet slip PIL image generated successfully for Bet ID: {bet_id}")
            return image.convert("RGB") # Convert to RGB before returning

        except Exception as e:
            logger.exception(f"Error generating bet slip image for Bet ID {bet_id}: {str(e)}")
            # Fallback error image generation
            error_img_width = 800
            error_img_height = 200
            error_img = Image.new('RGB', (error_img_width, error_img_height), (40, 40, 40))
            draw_error = ImageDraw.Draw(error_img)
            try:
                error_font = self.font_m_24 # Use loaded font
            except AttributeError: # Fallback if fonts not loaded globally
                error_font = ImageFont.load_default()
            draw_error.text((error_img_width/2, error_img_height/2), "Error Generating Bet Slip", fill="red", font=error_font, anchor="mm")
            return error_img

    def _draw_parlay_leg_internal(
        self, image: Image.Image, draw: ImageDraw.Draw, leg: Dict[str, Any], league: Optional[str],
        width: int, start_y: int, is_same_game: bool, leg_height: int
    ) -> int:
        """Internal helper to draw one parlay leg. Returns the new Y position."""
        # Get leg details
        leg_home = leg.get('home_team', leg.get('team', 'Unknown')) # Team involved
        leg_away = leg.get('opponent', 'Unknown') # Opponent if applicable
        leg_line = leg.get('line', 'N/A') # The specific bet line (e.g., "Moneyline", "Over 5.5")
        leg_odds = leg.get('odds', 0) # Odds for this leg
        leg_league = leg.get('league', league or 'UNKNOWN') # League for this leg

        logo_y = start_y + 10 # Position logo near the top
        logo_disp_size = (50, 50) # Smaller logo for legs
        text_start_x = 40 # Default X start for text

        # Determine which team's logo to show
        team_to_show_logo = leg.get('team', leg_home) # Prioritize 'team' if explicitly set in leg details

        # Attempt to load and draw the logo
        if team_to_show_logo != 'Unknown':
            team_logo = self._load_team_logo(team_to_show_logo, leg_league)
            if team_logo:
                logo_x = 40
                team_logo_disp = team_logo.resize(logo_disp_size, Image.Resampling.LANCZOS)
                if image.mode != 'RGBA': image = image.convert("RGBA")
                temp_layer = Image.new('RGBA', image.size, (0,0,0,0))
                temp_layer.paste(team_logo_disp, (logo_x, logo_y), team_logo_disp)
                image = Image.alpha_composite(image, temp_layer)
                draw = ImageDraw.Draw(image) # Recreate Draw object
                text_start_x = logo_x + logo_disp_size[0] + 15 # Indent text
            else:
                logger.debug(f"Parlay leg logo not found for {team_to_show_logo} in {leg_league}")

        # Draw Leg Line (e.g., "Over 5.5 Goals")
        draw.text((text_start_x, logo_y + 5), leg_line, fill='white', font=self.font_m_24)

        # Draw Matchup/Context (e.g., "NHL - Edmonton Oilers vs Boston Bruins")
        matchup_text_parts = []
        # Use specific home/away if available in leg data, otherwise use the derived ones
        actual_home = leg.get('home_team', leg_home)
        actual_away = leg.get('opponent', leg_away)
        if actual_home != 'Unknown': matchup_text_parts.append(actual_home)
        if actual_away != 'Unknown' and actual_away != actual_home: matchup_text_parts.append(f"vs {actual_away}")
        # If player prop, 'line' usually contains the player info, so matchup is less critical
        matchup_display = " ".join(matchup_text_parts) if matchup_text_parts else team_to_show_logo # Fallback to team name if no good matchup

        draw.text((text_start_x, logo_y + 40), f"{leg_league} - {matchup_display}", fill=(180, 180, 180), font=self.font_m_18)

        # Draw Leg Odds
        leg_odds_text = self._format_odds_with_sign(leg_odds)
        bbox_leg_odds = draw.textbbox((0,0), leg_odds_text, font=self.font_b_28)
        tw_leg_odds = bbox_leg_odds[2]-bbox_leg_odds[0]
        th_leg_odds = bbox_leg_odds[3]-bbox_leg_odds[1]

        # Calculate Y to center odds within the leg_height block
        odds_y_centered = start_y + (leg_height / 2) - (th_leg_odds / 2)

        # Position odds on the right side
        draw.text((width - 40 - tw_leg_odds, int(odds_y_centered)), leg_odds_text, fill='white', font=self.font_b_28)

        # Return the y-coordinate where the next leg should start
        return start_y + leg_height # Each leg takes up the full allocated height
