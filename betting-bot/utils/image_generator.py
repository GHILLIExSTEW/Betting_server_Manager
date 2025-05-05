# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime # Included based on user file upload
from typing import Optional, List, Dict, Any # Included based on user file upload
import time # Included based on user file upload
# NOTE: No io.BytesIO or config imported based on user file upload

logger = logging.getLogger(__name__)

# --- Sport Category Mapping (Defined Globally) ---
SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
    "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
    "MLB": "BASEBALL", "NCAAB_BASEBALL": "BASEBALL",
    "NHL": "HOCKEY",
    "MLS": "SOCCER", "EPL": "SOCCER", "LA LIGA": "SOCCER", "SERIE A": "SOCCER", "BUNDESLIGA": "SOCCER", "LIGUE 1": "SOCCER",
    "TENNIS": "TENNIS",
    "UFC": "MMA", "MMA": "MMA",
    "DARTS": "DARTS"
    # Add other leagues/sports as needed
}

# --- Default Font/Asset Path Logic (Global Scope Helper) ---
# This function helps determine paths ONCE before font loading.
# It prevents needing self.assets_dir before it's set in __init__.
def _determine_asset_paths():
    assets_dir_default = "betting-bot/static/" # Default from user's file __init__
    font_dir_name = 'fonts'
    logo_dir_name = 'logos'
    teams_subdir_name = 'teams'
    leagues_subdir_name = 'leagues'

    # Try finding assets relative to this file's parent dir (betting-bot/)
    script_dir = os.path.dirname(__file__) # utils/
    parent_dir = os.path.dirname(script_dir) # betting-bot/
    potential_assets_dir = os.path.join(parent_dir, 'assets') # Check for 'assets' first
    potential_static_dir = os.path.join(parent_dir, 'static') # Check for 'static' second

    final_assets_dir = None
    if os.path.isdir(potential_assets_dir):
        final_assets_dir = potential_assets_dir
        logger.info(f"Determined assets directory: {final_assets_dir}")
    elif os.path.isdir(potential_static_dir):
         final_assets_dir = potential_static_dir
         logger.info(f"Determined assets directory: {final_assets_dir} (using 'static')")
    else:
        logger.warning(f"Assets/Static directory not found relative to script. Trying default '{assets_dir_default}'. This might fail if CWD isn't betting-bot root.")
        final_assets_dir = assets_dir_default # Fallback to original default

    # Construct full paths
    paths = {
        "ASSETS_DIR": final_assets_dir,
        "DEFAULT_FONT_PATH": os.path.join(final_assets_dir, font_dir_name, 'Roboto-Regular.ttf'),
        "DEFAULT_BOLD_FONT_PATH": os.path.join(final_assets_dir, font_dir_name, 'Roboto-Bold.ttf'),
        "DEFAULT_EMOJI_FONT_PATH_NOTO": os.path.join(final_assets_dir, font_dir_name, 'NotoEmoji-Regular.ttf'),
        "DEFAULT_EMOJI_FONT_PATH_SEGOE": os.path.join(final_assets_dir, font_dir_name, 'SegoeUIEmoji.ttf'),
        "LEAGUE_TEAM_BASE_DIR": os.path.join(final_assets_dir, logo_dir_name, teams_subdir_name),
        "LEAGUE_LOGO_BASE_DIR": os.path.join(final_assets_dir, logo_dir_name, leagues_subdir_name),
        "DEFAULT_LOCK_ICON_PATH": os.path.join(final_assets_dir, "lock_icon.png"),
        # Assuming default logo is directly in logos/, not logos/teams/
        "DEFAULT_TEAM_LOGO_PATH": os.path.join(final_assets_dir, logo_dir_name, 'default_logo.png')
    }
    return paths

# Determine paths ONCE when module is loaded
_PATHS = _determine_asset_paths()

# --- Font Loading (Global Scope) ---
# Load fonts using paths determined above
try:
    # Determine best available default font
    _font_path = _PATHS["DEFAULT_FONT_PATH"]
    if not os.path.exists(_font_path):
        logger.warning(f"Default font '{_font_path}' not found. Falling back.")
        if os.name == 'nt': _font_path = 'C:\\Windows\\Fonts\\arial.ttf'
        else:
             _found = False
             for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']:
                 if os.path.exists(p): _font_path = p; _found=True; break
             if not _found: _font_path = 'arial.ttf' # Final guess
        logger.info(f"Using regular font: {_font_path}")

    # Determine best available bold font
    _bold_font_path = _PATHS["DEFAULT_BOLD_FONT_PATH"]
    if not os.path.exists(_bold_font_path):
        logger.warning(f"Default bold font '{_bold_font_path}' not found. Using regular font.")
        _bold_font_path = _font_path
    logger.info(f"Using bold font: {_bold_font_path}")

    # Determine best available emoji font
    _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"]
    if not os.path.exists(_emoji_font_path):
         _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_SEGOE"]
         if not os.path.exists(_emoji_font_path):
              logger.warning(f"Default emoji fonts not found. Falling back.")
              if os.name == 'nt': _emoji_font_path = 'C:\\Windows\\Fonts\\seguiemj.ttf'
              else:
                  _found = False
                  for p in ['/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf']:
                       if os.path.exists(p): _emoji_font_path = p; _found=True; break
                  if not _found: _emoji_font_path = _font_path # Fallback to regular
    logger.info(f"Using emoji font: {_emoji_font_path}")


    # Load fonts globally
    font_m_18 = ImageFont.truetype(_font_path, 18)
    font_m_24 = ImageFont.truetype(_font_path, 24)
    font_b_18 = ImageFont.truetype(_bold_font_path, 18)
    font_b_24 = ImageFont.truetype(_bold_font_path, 24)
    font_b_36 = ImageFont.truetype(_bold_font_path, 36)
    emoji_font_24 = ImageFont.truetype(_emoji_font_path, 24) if os.path.exists(_emoji_font_path) else font_m_24 # Fallback if emoji font failed final check

    logger.info("Successfully loaded fonts globally for image_generator.")
except Exception as e:
    logger.critical(f"CRITICAL: Error loading required fonts: {e}", exc_info=True)
    # Set fonts to default PIL font to allow continuation, but log critical error
    font_m_18 = font_m_24 = font_b_18 = font_b_24 = font_b_36 = emoji_font_24 = ImageFont.load_default()
    # Optional: raise e # Re-raise if fonts are absolutely essential

class BetSlipGenerator:
    # __init__ now primarily sets dimensions and references global resources
    def __init__(self, width=800, leg_height=120, header_height=100, footer_height=80, padding=20, logo_size=60):
        self.width = width
        self.leg_height = leg_height # Used for Y calculations
        self.header_height = header_height # Used for Y calculations
        self.footer_height = footer_height # Used for Y calculations
        self.padding = padding
        self.logo_size = logo_size # Used by _load_team_logo for thumbnailing
        self.image = None # Instance variable for the image being built

        # Use globally loaded fonts
        self.font_m_18 = font_m_18
        self.font_m_24 = font_m_24
        self.font_b_18 = font_b_18
        self.font_b_24 = font_b_24
        self.font_b_36 = font_b_36
        self.emoji_font_24 = emoji_font_24 # Use specific emoji font

        # Use globally determined paths
        self.assets_dir = _PATHS["ASSETS_DIR"]
        self.league_team_base_dir = _PATHS["LEAGUE_TEAM_BASE_DIR"]
        self.league_logo_base_dir = _PATHS["LEAGUE_LOGO_BASE_DIR"]
        self.default_logo_path = _PATHS["DEFAULT_TEAM_LOGO_PATH"]
        self.lock_icon_path = _PATHS["DEFAULT_LOCK_ICON_PATH"]

        # Initialize caches (same as user file)
        self._logo_cache = {}
        self._font_cache = {} # Font cache less critical now fonts are global
        self._lock_icon_cache = None
        self._max_cache_size = 100
        self._cache_expiry = 3600
        self._last_cache_cleanup = time.time()
        logger.info(f"BetSlipGenerator Initialized. Assets Dir: {self.assets_dir}, Team Logo Base: {self.league_team_base_dir}")

    # Removed _get_default_*, _ensure_* methods as logic is now global

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
        """Ensure the team logos directory exists for the given league."""
        # References global SPORT_CATEGORY_MAP
        sport_category = SPORT_CATEGORY_MAP.get(league.upper(), league.upper() if league else "OTHER")
        # Uses self.league_team_base_dir (which is based on global _PATHS)
        league_team_dir = os.path.join(self.league_team_base_dir, sport_category, league.upper() if league else "UNKNOWN")

        if not os.path.isdir(league_team_dir):
            logger.info(f"Team logos directory not found at {league_team_dir}, creating it.")
            try:
                os.makedirs(league_team_dir, exist_ok=True)
            except OSError as e:
                 logger.error(f"Failed to create directory {league_team_dir}: {e}")
                 logger.warning(f"Falling back to base team logo directory: {self.league_team_base_dir}")
                 os.makedirs(self.league_team_base_dir, exist_ok=True) # Ensure base exists
                 return self.league_team_base_dir
        return league_team_dir

    # _ensure_league_dir_exists is removed (was source of SyntaxError and unused)

    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        if current_time - self._last_cache_cleanup > 300:
            expired_keys = [k for k, (_, ts) in self._logo_cache.items() if current_time - ts > self._cache_expiry]
            for key in expired_keys:
                try: del self._logo_cache[key]
                except KeyError: pass
            self._last_cache_cleanup = current_time

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Load the team logo image based on team name and league with caching."""
        # Using refined logic from previous step
        if not team_name or not league:
            logger.warning(f"Load logo called with missing team name ('{team_name}') or league ('{league}')")
            return None

        cache_key = f"{team_name}_{league}".lower()
        current_time = time.time()

        if cache_key in self._logo_cache:
            logo, timestamp = self._logo_cache[cache_key]
            if current_time - timestamp <= self._cache_expiry:
                logger.debug(f"Cache HIT for logo: {cache_key}")
                return logo.copy() # Return copy from cache
            else: del self._logo_cache[cache_key]

        logger.debug(f"Cache MISS for logo: {cache_key}")
        try:
            league_team_dir = self._ensure_team_dir_exists(league)
            # Using the same simple map and formatting logic from user file
            team_name_map = {"oilers": "edmonton_oilers", "bruins": "boston_bruins", "bengals": "cincinnati_bengals", "steelers": "pittsburgh_steelers"}
            safe_team_name = team_name_map.get(team_name.lower(), team_name.lower().replace(" ", "_"))
            logo_filename = f"{safe_team_name}.png"
            logo_path = os.path.join(league_team_dir, logo_filename)
            logger.debug(f"Attempting to load logo from path: {logo_path}")

            final_path_to_load = None
            if os.path.exists(logo_path):
                final_path_to_load = logo_path
            # Add fallback to base LOGO_DIR (not LEAGUE_TEAM_BASE_DIR) based on user file structure?
            # User file didn't show this fallback, let's stick closer to that logic first.
            # If specific path fails, try default logo path.
            elif os.path.exists(self.default_logo_path):
                final_path_to_load = self.default_logo_path
                logger.warning(f"Logo not found for '{team_name}' at {logo_path}. Using default.")
            else:
                logger.error(f"Logo for '{team_name}' not found at {logo_path} AND default logo missing: {self.default_logo_path}")
                return None

            with Image.open(final_path_to_load) as logo:
                logo = logo.convert("RGBA")
                # Resize using self.logo_size from __init__
                logo.thumbnail((self.logo_size, self.logo_size), Image.Resampling.LANCZOS)
                # Cache update
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    try: oldest_key = min(self._logo_cache.items(), key=lambda item: item[1][1])[0]; del self._logo_cache[oldest_key]
                    except ValueError: pass
                logo_copy = logo.copy() # Cache a copy
                self._logo_cache[cache_key] = (logo_copy, current_time)
                return logo_copy # Return the copy

        except Exception as e:
            logger.error(f"Error loading logo for team '{team_name}' ({league}): {str(e)}", exc_info=True)
            return None

    # _load_font removed - using globally loaded fonts

    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Load the lock icon image with caching."""
        if self._lock_icon_cache is None:
            try:
                if os.path.exists(self.lock_icon_path):
                     with Image.open(self.lock_icon_path) as lock:
                        lock = lock.convert("RGBA")
                        lock = lock.resize((20, 20), Image.Resampling.LANCZOS) # Size from user file
                        self._lock_icon_cache = lock.copy()
                else: logger.warning(f"Lock icon not found at {self.lock_icon_path}")
            except Exception as e: logger.error(f"Error loading lock icon: {str(e)}")
        return self._lock_icon_cache


    def generate_bet_slip(
        self,
        home_team: str, away_team: str, league: Optional[str], line: str, odds: float,
        units: float, bet_id: str, timestamp: datetime, bet_type: str = "straight",
        parlay_legs: Optional[List[Dict[str, Any]]] = None, is_same_game: bool = False
    ) -> Optional[Image.Image]: # Return PIL Image or None
        """Generate a bet slip image for straight or parlay bets."""
        # Using drawing logic based on user's uploaded file structure
        logger.info(f"Generating bet slip - Type: {bet_type}, League: {league}, BetID: {bet_id}")
        try:
            width = 800
            header_h = 80 # Use values from __init__ or defaults if preferred
            footer_h = 60
            # Height calculation from user file was complex, use simpler approach
            # Base height + space per leg for parlays
            leg_draw_height = 150 # Approx height needed per parlay leg display
            num_legs = len(parlay_legs) if parlay_legs else 1
            parlay_extra_height = (num_legs -1) * leg_draw_height if bet_type == "parlay" and parlay_legs else 0
            parlay_total_section_height = 120 if bet_type == "parlay" else 0 # Space for total odds/stake
            base_content_height = 310 # Approx height for straight bet content (logos, bet, odds, units)
            height = header_h + (base_content_height if bet_type=='straight' else parlay_extra_height + leg_draw_height) + parlay_total_section_height + footer_h

            image = Image.new('RGB', (width, height), (40, 40, 40)) # Dark background from user file
            draw = ImageDraw.Draw(image)

            # --- Header --- (From user file)
            header_y = 40
            header_text = f"{league.upper() if league else ''} - {'Straight Bet' if bet_type == 'straight' else 'Parlay'}"
            header_text = header_text.strip(" - ")
            bbox = draw.textbbox((0, 0), header_text, font=self.font_b_36) # Use bold header font
            tw = bbox[2] - bbox[0]
            draw.text(((width - tw) / 2, header_y), header_text, fill='white', font=self.font_b_36)

            # --- Content ---
            if bet_type == "straight":
                # --- Straight Bet Drawing (based on user file) ---
                logo_y = header_h + 60 # Adjusted Y start
                logo_size = (120, 120) # Size from user file

                effective_league = league or 'NHL' # Default from user file
                home_logo = self._load_team_logo(home_team, effective_league)
                away_logo = self._load_team_logo(away_team, effective_league)

                # Draw Home Team Logo & Name
                if home_logo:
                    home_logo_disp = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    # Need RGBA conversion for pasting with transparency
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    temp_layer_home = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_layer_home.paste(home_logo_disp, (width // 4 - logo_size[0] // 2, logo_y), home_logo_disp)
                    image = Image.alpha_composite(image, temp_layer_home)
                    draw = ImageDraw.Draw(image) # Recreate draw object
                draw.text((width // 4, logo_y + logo_size[1] + 20), home_team, fill='white', font=self.font_b_24, anchor='mm')

                # Draw Away Team Logo & Name
                if away_logo:
                    away_logo_disp = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    temp_layer_away = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_layer_away.paste(away_logo_disp, (3 * width // 4 - logo_size[0] // 2, logo_y), away_logo_disp)
                    image = Image.alpha_composite(image, temp_layer_away)
                    draw = ImageDraw.Draw(image)
                draw.text((3 * width // 4, logo_y + logo_size[1] + 20), away_team, fill='white', font=self.font_b_24, anchor='mm')

                # Draw Bet details
                details_y = logo_y + logo_size[1] + 80
                bet_text = f"{home_team}: {line}" # User file had this structure
                draw.text((width // 2, details_y), bet_text, fill='white', font=self.font_m_24, anchor='mm') # User file used details_font (28) here? Let's try 24 regular.

                # Draw separator line
                separator_y = details_y + 40
                draw.line([(20, separator_y), (width - 20, separator_y)], fill='white', width=2)

                # Draw odds
                odds_y = separator_y + 30
                odds_text = self._format_odds_with_sign(int(odds))
                draw.text((width // 2, odds_y), odds_text, fill='white', font=self.font_b_24, anchor='mm') # User file used details_font(28), try bold 24

                # Draw units
                units_y = odds_y + 40
                units_text = f"To Win {units:.2f} Units"
                units_bbox = draw.textbbox((0, 0), units_text, font=self.font_b_24) # Bold 24 for units
                units_width = units_bbox[2] - units_bbox[0]
                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 15
                    lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    temp_lock_l = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_lock_l.paste(lock_icon, (lock_x_left, units_y - lock_icon.height // 2), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_l)
                    temp_lock_r = Image.new('RGBA', image.size, (0,0,0,0))
                    lock_x_right = lock_x_left + units_width + lock_icon.width + 2 * lock_spacing
                    temp_lock_r.paste(lock_icon, (lock_x_right, units_y - lock_icon.height // 2), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_r)
                    draw = ImageDraw.Draw(image) # Recreate draw object
                    draw.text((lock_x_left + lock_icon.width + lock_spacing + units_width // 2, units_y),
                              units_text, fill=(255, 215, 0), font=self.font_b_24, anchor='mm')
                else: # Fallback
                    draw.text((width // 2, units_y), f"白 {units_text} 白",
                              fill=(255, 215, 0), font=self.emoji_font_24, anchor='mm')


            elif bet_type == "parlay" and parlay_legs:
                # --- Parlay Drawing (based on user file's generate method) ---
                current_y = header_h + 10
                for i, leg in enumerate(parlay_legs):
                    if i > 0:
                        separator_y = current_y # Separator before the leg
                        draw.line([(40, separator_y), (width - 40, separator_y)], fill=(100, 100, 100), width=1)
                        current_y += 20

                    # Use internal helper to draw each leg (extracted from user file generate method)
                    # This helper needs access to fonts etc.
                    current_y = self._draw_parlay_leg_internal(
                        image=image, draw=draw, leg=leg, league=league, width=width, start_y=current_y,
                        is_same_game=is_same_game, leg_height=leg_draw_height # Pass allocated height
                    )
                    # Need to update image/draw object if _draw_parlay_leg_internal modified it
                    draw = ImageDraw.Draw(image)

                # Draw total parlay odds and units
                total_y = current_y + 20
                draw.line([(40, total_y), (width - 40, total_y)], fill='white', width=2)
                total_y += 30

                total_odds_text = f"Total Odds: {self._format_odds_with_sign(int(odds))}"
                draw.text((width // 2, total_y), total_odds_text, fill='white', font=self.font_b_28, anchor='mm') # Using bold 28
                total_y += 40

                units_text = f"Total Units: {units:.2f}" # Assuming units is stake
                units_bbox = draw.textbbox((0, 0), units_text, font=self.font_b_24) # Using bold 24
                units_width = units_bbox[2] - units_bbox[0]
                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 15
                    lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    temp_lock_l = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_lock_l.paste(lock_icon, (lock_x_left, total_y - lock_icon.height // 2), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_l)
                    temp_lock_r = Image.new('RGBA', image.size, (0,0,0,0))
                    lock_x_right = lock_x_left + units_width + lock_icon.width + 2 * lock_spacing
                    temp_lock_r.paste(lock_icon, (lock_x_right, total_y - lock_icon.height // 2), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_r)
                    draw = ImageDraw.Draw(image) # Recreate draw object
                    draw.text((lock_x_left + lock_icon.width + lock_spacing + units_width // 2, total_y),
                              units_text, fill=(255, 215, 0), font=self.font_b_24, anchor='mm')
                else: # Fallback
                    draw.text((width // 2, total_y), f"白 {units_text} 白",
                              fill=(255, 215, 0), font=self.emoji_font_24, anchor='mm')

            else: # Invalid type or legs
                 draw.text((width // 2, height // 2), "Invalid Bet Data", fill='red', font=header_font, anchor='mm')

            # --- Footer ---
            footer_y = height - 30
            draw.text((20, footer_y), f"Bet #{bet_id}", fill=(150, 150, 150), font=self.font_m_18, anchor='lm')
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC')
            ts_bbox = draw.textbbox((0,0), timestamp_text, font=self.font_m_18)
            ts_width = ts_bbox[2] - ts_bbox[0]
            draw.text((width - 20 - ts_width, footer_y), timestamp_text, fill=(150, 150, 150), font=self.font_m_18)

            logger.info(f"Bet slip PIL image generated successfully for Bet ID: {bet_id}")
            return image.convert("RGB") # Convert back to RGB before returning

        except Exception as e:
            logger.exception(f"Error generating bet slip image for Bet ID {bet_id}: {str(e)}")
            # Create error image
            error_img = Image.new('RGB', (width, 200), (40, 40, 40))
            draw = ImageDraw.Draw(error_img)
            font = self.font_m_24 # Use loaded font
            draw.text((width/2, 100), "Error Generating Bet Slip", fill="red", font=font, anchor="mm")
            return error_img

    # Helper specifically for drawing parlay legs based on user file logic
    def _draw_parlay_leg_internal(
        self, image: Image.Image, draw: ImageDraw.Draw, leg: Dict[str, Any], league: Optional[str],
        width: int, start_y: int, is_same_game: bool, leg_height: int
    ) -> int:
        """Internal helper to draw one parlay leg. Returns the new Y position."""
        # Get leg details
        leg_home = leg.get('home_team', leg.get('team', 'Unknown'))
        leg_away = leg.get('opponent', 'Unknown')
        leg_line = leg.get('line', 'N/A')
        leg_odds = leg.get('odds', 0)
        leg_league = leg.get('league', league or 'UNKNOWN')

        current_y = start_y
        logo_y = current_y + 10
        logo_disp_size = (50, 50) # Smaller logos in user file's parlay logic
        text_start_x = 40

        # Determine team to show logo for (user file logic wasn't clear, use leg_home)
        team_bet_on = leg_home
        # Only draw logos for same-game parlays according to user file logic?
        # Let's assume we always try to draw if team_bet_on exists.
        # draw_logos = True # Override based on assumption
        # User file had `draw_logos=True` only if `is_same_game`? Let's follow that.
        draw_logos = is_same_game

        if draw_logos and team_bet_on != 'Unknown':
            team_logo = self._load_team_logo(team_bet_on, leg_league)
            if team_logo:
                logo_x = 40
                team_logo_disp = team_logo.resize(logo_disp_size, Image.Resampling.LANCZOS)
                if image.mode != 'RGBA': image = image.convert("RGBA")
                temp_layer = Image.new('RGBA', image.size, (0,0,0,0))
                temp_layer.paste(team_logo_disp, (logo_x, logo_y), team_logo_disp)
                image = Image.alpha_composite(image, temp_layer)
                draw = ImageDraw.Draw(image) # Update draw object
                text_start_x = logo_x + logo_disp_size[0] + 15
            else: logger.debug(f"Parlay leg logo not found for {team_bet_on}")

        # Draw Line description
        draw.text((text_start_x, logo_y + 5), leg_line, fill='white', font=self.font_m_24) # User file used details_font(28) or team_font(24)? Try 24.
        # Draw League/Matchup
        matchup_text = f"{leg_home} vs {leg_away}" if leg_home != 'Unknown' and leg_away != 'Unknown' else leg_home
        draw.text((text_start_x, logo_y + 40), f"{leg_league} - {matchup_text}", fill=(180, 180, 180), font=self.font_m_18)

        # Draw Leg Odds (Right Aligned)
        leg_odds_text = self._format_odds_with_sign(int(leg_odds))
        # Vertically center odds in the allocated leg height
        leg_center_y = start_y + (leg_height / 2)
        bbox = draw.textbbox((0,0), leg_odds_text, font=self.font_b_28) # Bold 28 for odds? User file unclear.
        tw = bbox[2]-bbox[0]; th = bbox[3]-bbox[1]
        draw.text((width - 40 - tw, leg_center_y - (th/2)), leg_odds_text, fill='white', font=self.font_b_28)

        return start_y + leg_height # Return Y position for start of next leg


# --- Example Usage Block ---
if __name__ == '__main__':
    # Ensure logger is configured for testing
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = logging.getLogger(__name__) # Re-get logger for __main__ scope
    logger.info("Testing BetSlipGenerator directly...")

    # --- Define Test Constants ---
    # Define constants for testing scope, assuming standard structure
    try:
        _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # betting-bot/
        ASSET_DIR = os.path.join(_base_dir, 'assets') # Assume assets/ folder
        if not os.path.isdir(ASSET_DIR): ASSET_DIR = os.path.join(_base_dir, 'static') # Fallback static/
        if not os.path.isdir(ASSET_DIR): ASSET_DIR = '.' # Final fallback CWD
        logger.info(f"[Test] Using ASSET_DIR: {ASSET_DIR}")

        # Re-assign global paths for test scope based on ASSET_DIR found
        # These globals are used by the generator instance created below
        DEFAULT_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'Roboto-Regular.ttf')
        DEFAULT_BOLD_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'Roboto-Bold.ttf')
        DEFAULT_EMOJI_FONT_PATH_NOTO = os.path.join(ASSET_DIR, 'fonts', 'NotoEmoji-Regular.ttf')
        DEFAULT_EMOJI_FONT_PATH_SEGOE = os.path.join(ASSET_DIR, 'fonts', 'SegoeUIEmoji.ttf')
        LOGO_DIR = os.path.join(ASSET_DIR, 'logos')
        DEFAULT_TEAM_LOGO_PATH = os.path.join(LOGO_DIR, 'default_logo.png')

        # Re-load fonts based on determined paths for testing
        _font_path = DEFAULT_FONT_PATH
        if not os.path.exists(_font_path): _font_path = 'arial.ttf' # Basic fallback
        _bold_font_path = DEFAULT_BOLD_FONT_PATH
        if not os.path.exists(_bold_font_path): _bold_font_path = _font_path
        _emoji_font_path = DEFAULT_EMOJI_FONT_PATH_NOTO
        if not os.path.exists(_emoji_font_path): _emoji_font_path = DEFAULT_EMOJI_FONT_PATH_SEGOE
        if not os.path.exists(_emoji_font_path): _emoji_font_path = _font_path

        font_m_18 = ImageFont.truetype(_font_path, 18); font_m_24 = ImageFont.truetype(_font_path, 24)
        font_b_18 = ImageFont.truetype(_bold_font_path, 18); font_b_24 = ImageFont.truetype(_bold_font_path, 24)
        font_b_36 = ImageFont.truetype(_bold_font_path, 36); font_b_28 = ImageFont.truetype(_bold_font_path, 28) # Added missing font size
        emoji_font_24 = ImageFont.truetype(_emoji_font_path, 24) if os.path.exists(_emoji_font_path) else font_m_24
        logger.info("[Test] Fonts loaded for __main__.")

    except Exception as e:
        logger.critical(f"[Test] CRITICAL: Error setting up constants/fonts in __main__: {e}", exc_info=True)
        exit(1)


    from collections import namedtuple # Keep for mock data
    MockBetLeg = namedtuple("MockBetLeg", ["league_name", "team_name", "bet_type", "line", "odds", "opponent"])
    MockBet = namedtuple("MockBet", ["bet_id", "stake", "total_odds", "potential_payout", "capper_name", "legs"])

    # Test Execution
    generator = BetSlipGenerator() # Uses globally loaded fonts/paths
    print("Generating example slips (using mock data)...")

    # --- Test Straight Bet ---
    # Create mock 'bet' object that has 'legs' attribute
    straight_legs_data = [
        MockBetLeg(league_name='NHL', team_name='Boston Bruins', bet_type='Moneyline', line='Boston Bruins ML', odds=-150, opponent='Florida Panthers')
    ]
    straight_bet_obj = MockBet(
        bet_id='ST123', stake=1.5, total_odds=-150, potential_payout=1.0, # Payout calc needed?
        capper_name="Test Capper", legs=straight_legs_data
    )
    pil_image_straight = generator.create_bet_slip(straight_bet_obj) # Pass the object
    if pil_image_straight:
        try:
            pil_image_straight.save("test_straight_slip_generated.png")
            print(" - test_straight_slip_generated.png saved.")
        except Exception as e: print(f" - FAILED to save straight slip: {e}")
    else: print(" - FAILED to generate straight slip.")

    # --- Test Parlay Bet ---
    parlay_legs_data = [
        MockBetLeg(league_name='NFL', team_name='Kansas City Chiefs', bet_type='Spread', line='KC Chiefs -7.5', odds=-110, opponent='Denver Broncos'),
        MockBetLeg(league_name='NBA', team_name='Los Angeles Lakers', bet_type='Moneyline', line='LAL ML', odds=150, opponent='Golden State Warriors'),
    ]
    parlay_bet_obj = MockBet(
        bet_id='PA456', stake=1.0, total_odds=250, potential_payout=2.50,
        capper_name="Tester", legs=parlay_legs_data
    )
    pil_image_parlay = generator.create_bet_slip(parlay_bet_obj) # Pass the object
    if pil_image_parlay:
        try:
            pil_image_parlay.save("test_parlay_slip_generated.png")
            print(" - test_parlay_slip_generated.png saved.")
        except Exception as e: print(f" - FAILED to save parlay slip: {e}")
    else: print(" - FAILED to generate parlay slip.")

    print("Testing complete.")
