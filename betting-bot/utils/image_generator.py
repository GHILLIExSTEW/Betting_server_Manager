# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime # Included as requested by user previously
from typing import Optional, List, Dict, Any # Included as requested by user previously
import time # Included as requested by user previously
# NOTE: io.BytesIO is NOT imported in the uploaded file version.
# NOTE: config is NOT imported in the uploaded file version.

logger = logging.getLogger(__name__)

# --- Sport Category Mapping (Defined ONCE Globally) ---
# Moved from _ensure_league_dir_exists to module level
SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
    "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
    "MLB": "BASEBALL", "NCAAB_BASEBALL": "BASEBALL", # Assuming college baseball league name
    "NHL": "HOCKEY",
    "MLS": "SOCCER", "EPL": "SOCCER", "LA LIGA": "SOCCER", "SERIE A": "SOCCER", "BUNDESLIGA": "SOCCER", "LIGUE 1": "SOCCER",
    "TENNIS": "TENNIS",
    "UFC": "MMA", "MMA": "MMA",
    "DARTS": "DARTS"
    # Add other leagues/sports as needed
}

class BetSlipGenerator:
    # Using the __init__ from your uploaded file
    def __init__(self, font_path: Optional[str] = None, emoji_font_path: Optional[str] = None, assets_dir: str = "betting-bot/static/"):
        self.font_path = font_path or self._get_default_font()
        self.bold_font_path = self._get_default_bold_font()
        self.emoji_font_path = emoji_font_path or self._get_default_emoji_font()
        self.assets_dir = assets_dir # NOTE: Assumes assets are in betting-bot/static/ per your file
        self.league_team_base_dir = os.path.join(self.assets_dir, "logos/teams")
        self.league_logo_base_dir = os.path.join(self.assets_dir, "logos/leagues")
        self._ensure_font_exists()
        self._ensure_bold_font_exists()
        self._ensure_emoji_font_exists()

        # Initialize caches
        self._logo_cache = {}
        self._font_cache = {}
        self._lock_icon_cache = None
        self._max_cache_size = 100  # Maximum number of items in logo cache
        self._cache_expiry = 3600  # Cache expiry time in seconds
        self._last_cache_cleanup = time.time()
        logger.info(f"BetSlipGenerator Initialized. Assets Dir: {self.assets_dir}, Team Logo Base: {self.league_team_base_dir}")


    def _get_default_font(self) -> str:
        """Get the default font path for regular text."""
        # Uses path relative to assumed location or system paths
        custom_font_path = os.path.join(self.assets_dir, 'fonts', 'Roboto-Regular.ttf') # Relative to assets_dir
        if os.path.exists(custom_font_path):
            logger.debug(f"Using regular font at {custom_font_path}")
            return custom_font_path
        logger.warning(f"Default font '{custom_font_path}' not found. Falling back.")
        if os.name == 'nt': return 'C:\\Windows\\Fonts\\arial.ttf'
        for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']:
            if os.path.exists(p): return p
        return 'arial.ttf'

    def _get_default_bold_font(self) -> str:
        """Get the default bold font path for emphasized text."""
        custom_bold_font_path = os.path.join(self.assets_dir, 'fonts', 'Roboto-Bold.ttf') # Relative to assets_dir
        if os.path.exists(custom_bold_font_path):
            logger.debug(f"Using bold font at {custom_bold_font_path}")
            return custom_bold_font_path
        logger.warning(f"Default bold font '{custom_bold_font_path}' not found. Falling back to regular font.")
        # Fallback logic here relies on self.font_path being set first in __init__
        # It might be better to call _get_default_font() again if needed.
        # For now, keeping logic close to uploaded file:
        return self._get_default_font() # Fallback to regular font path determination


    def _get_default_emoji_font(self) -> str:
        """Get the default font path for emojis."""
        # Uses path relative to assumed location or system paths
        custom_emoji_font_path = os.path.join(self.assets_dir, 'fonts', 'NotoEmoji-Regular.ttf') # Relative to assets_dir
        if os.path.exists(custom_emoji_font_path):
            logger.debug(f"Using emoji font at {custom_emoji_font_path}")
            return custom_emoji_font_path
        custom_emoji_font_path_alt = os.path.join(self.assets_dir, 'fonts', 'SegoeUIEmoji.ttf') # Relative to assets_dir
        if os.path.exists(custom_emoji_font_path_alt):
            logger.debug(f"Using emoji font at {custom_emoji_font_path_alt}")
            return custom_emoji_font_path_alt
        logger.warning(f"Default emoji fonts not found in '{os.path.join(self.assets_dir, 'fonts')}'. Falling back.")
        if os.name == 'nt': return 'C:\\Windows\\Fonts\\seguiemj.ttf'
        for p in ['/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf']:
             if os.path.exists(p): return p
        return self.font_path # Fallback to regular font path (might not render emojis well)

    def _ensure_font_exists(self) -> None:
        """Ensure the regular font file exists."""
        if not os.path.exists(self.font_path):
            logger.error(f"Regular font file check failed at resolved path: {self.font_path}")
            # Consider raising error if font is critical and no fallback worked
            # raise FileNotFoundError(f"Could not find a suitable regular font file. Checked: {self.font_path}")
        else:
             logger.debug(f"Regular font confirmed at: {self.font_path}")


    def _ensure_bold_font_exists(self) -> None:
        """Ensure the bold font file exists."""
        # If bold path is same as regular (fallback), existence was already checked
        if self.bold_font_path != self.font_path and not os.path.exists(self.bold_font_path):
             logger.warning(f"Bold font file check failed at resolved path: {self.bold_font_path}. Will use regular: {self.font_path}")
             self.bold_font_path = self.font_path # Ensure fallback if explicit check fails
        else:
            logger.debug(f"Bold font confirmed at: {self.bold_font_path}")


    def _ensure_emoji_font_exists(self) -> None:
        """Ensure the emoji font file exists."""
        # If emoji path is same as regular (fallback), existence was already checked
        if self.emoji_font_path != self.font_path and not os.path.exists(self.emoji_font_path):
            logger.warning(f"Emoji font file check failed at resolved path: {self.emoji_font_path}. Will use regular: {self.font_path}")
            self.emoji_font_path = self.font_path # Ensure fallback if explicit check fails
        else:
             logger.debug(f"Emoji font confirmed at: {self.emoji_font_path}")


    def _ensure_team_dir_exists(self, league: str) -> str:
        """Ensure the team logos directory exists for the given league."""
        # References global SPORT_CATEGORY_MAP
        sport_category = SPORT_CATEGORY_MAP.get(league.upper(), league.upper() if league else "OTHER")
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

    # CORRECTED: Removed erroneous line, references global map
    def _ensure_league_dir_exists(self, league: str) -> str:
        """Ensure the league logos directory exists for the given league."""
        # References global SPORT_CATEGORY_MAP
        sport_category = SPORT_CATEGORY_MAP.get(league.upper(), league.upper() if league else "OTHER")
        league_logo_dir = os.path.join(self.league_logo_base_dir, sport_category, league.upper() if league else "UNKNOWN")
        if not os.path.isdir(league_logo_dir):
            logger.info(f"League logos directory not found at {league_logo_dir}, creating it.")
            try:
                os.makedirs(league_logo_dir, exist_ok=True)
            except OSError as e:
                 logger.error(f"Failed to create directory {league_logo_dir}: {e}")
                 logger.warning(f"Falling back to base league logo directory: {self.league_logo_base_dir}")
                 os.makedirs(self.league_logo_base_dir, exist_ok=True) # Ensure base exists
                 return self.league_logo_base_dir
        return league_logo_dir


    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        if current_time - self._last_cache_cleanup > 300:  # Clean up every 5 minutes
            expired_keys = [key for key, (_, timestamp) in self._logo_cache.items() if current_time - timestamp > self._cache_expiry]
            for key in expired_keys:
                try: del self._logo_cache[key]
                except KeyError: pass # Ignore if already removed
            self._last_cache_cleanup = current_time


    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Load the team logo image based on team name and league with caching."""
        # Using the implementation from your uploaded file, assuming it's mostly correct
        # but adding logging
        if not team_name or not league:
            logger.warning(f"Attempting to load logo with missing team name ('{team_name}') or league ('{league}')")
            return None

        cache_key = f"{team_name}_{league}".lower() # Use lowercase for consistency
        current_time = time.time()

        # Check cache
        if cache_key in self._logo_cache:
            logo, timestamp = self._logo_cache[cache_key]
            if current_time - timestamp <= self._cache_expiry:
                logger.debug(f"Cache HIT for logo: {cache_key}")
                return logo
            else:
                logger.debug(f"Cache EXPIRED for logo: {cache_key}")
                del self._logo_cache[cache_key]
        else:
             logger.debug(f"Cache MISS for logo: {cache_key}")

        try:
            league_team_dir = self._ensure_team_dir_exists(league)
            team_name_map = { # This map needs to be maintained based on your filenames
                "oilers": "edmonton_oilers",
                "bruins": "boston_bruins",
                "bengals": "cincinnati_bengals",
                "steelers": "pittsburgh_steelers"
            }
            # Using the formatting from your file version
            logo_filename = team_name_map.get(team_name.lower(), team_name.lower().replace(" ", "_")) + ".png"
            logo_path = os.path.join(league_team_dir, logo_filename)
            logger.debug(f"Checking logo path: {logo_path}")

            if os.path.exists(logo_path):
                logger.info(f"Logo FOUND for team '{team_name}' at {logo_path}")
                with Image.open(logo_path) as logo:
                    logo = logo.convert("RGBA")
                    # Resizing to 100x100 as per your file's logic, not self.logo_size
                    logo = logo.resize((100, 100), Image.Resampling.LANCZOS)

                    # Update cache
                    self._cleanup_cache()
                    if len(self._logo_cache) >= self._max_cache_size:
                        try: # Safely remove oldest
                            oldest_key = min(self._logo_cache.items(), key=lambda item: item[1][1])[0]
                            del self._logo_cache[oldest_key]
                        except ValueError: pass # Ignore if cache empty
                    self._logo_cache[cache_key] = (logo.copy(), current_time)
                    return logo.copy()
            else:
                logger.warning(f"Logo NOT FOUND for team '{team_name}' ({league}) at expected path: {logo_path}")
                # Fallback to default logo? Your original code didn't explicitly do this here.
                # Let's add the default fallback based on previous discussions
                if os.path.exists(self.default_logo_path):
                    logger.warning(f"Using default logo: {self.default_logo_path}")
                    with Image.open(self.default_logo_path) as logo:
                         logo = logo.convert("RGBA")
                         logo.thumbnail((100, 100), Image.Resampling.LANCZOS) # Resize default too
                         # Don't cache the default logo under the specific team key
                         return logo.copy()
                else:
                     logger.error(f"Default logo also not found at {self.default_logo_path}")
                     return None # Cannot load anything
        except Exception as e:
            logger.error(f"Error loading logo for team '{team_name}' ({league}): {str(e)}", exc_info=True)
            return None

    def _load_font(self, size: int, is_bold: bool = False) -> ImageFont.FreeTypeFont:
        """Load font with caching."""
        font_path_key = self.bold_font_path if is_bold else self.font_path
        cache_key = f"{font_path_key}_{size}"
        if cache_key not in self._font_cache:
            try:
                self._font_cache[cache_key] = ImageFont.truetype(font_path_key, size)
            except Exception as e:
                logger.error(f"Failed to load font '{font_path_key}' size {size}: {e}. Using default font.")
                self._font_cache[cache_key] = ImageFont.load_default()
        return self._font_cache[cache_key]

    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Load the lock icon image with caching."""
        if self._lock_icon_cache is None:
            try:
                lock_path = os.path.join(self.assets_dir, "lock_icon.png")
                if os.path.exists(lock_path):
                     with Image.open(lock_path) as lock:
                        lock = lock.convert("RGBA")
                        lock = lock.resize((20, 20), Image.Resampling.LANCZOS) # Resize from your code
                        self._lock_icon_cache = lock.copy()
                else:
                    logger.warning(f"Lock icon not found at {lock_path}")
                    return None # Explicitly return None if not found
            except Exception as e:
                logger.error(f"Error loading lock icon: {str(e)}")
                return None
        return self._lock_icon_cache


    def generate_bet_slip(
        self,
        home_team: str,
        away_team: str,
        league: Optional[str],
        line: str,
        odds: float,
        units: float,
        bet_id: str,
        timestamp: datetime,
        bet_type: str = "straight",
        parlay_legs: Optional[List[Dict[str, Any]]] = None,
        is_same_game: bool = False
    ) -> Optional[Image.Image]: # Return PIL Image or None
        """Generate a bet slip image for straight or parlay bets."""
        # Using the implementation structure from your uploaded file
        logger.info(f"Generating bet slip - Type: {bet_type}, League: {league}, BetID: {bet_id}")
        try:
            width = 800
            base_height = 450 # For straight bets
            leg_draw_height = 150 # Height allocated per leg in parlay drawing section below (adjust as needed)
            header_h = 80
            footer_h = 60

            if bet_type == "parlay" and parlay_legs:
                 # Adjust calculation based on how _draw_leg impacts height
                 # A fixed leg height calculation might be simpler:
                 num_legs = len(parlay_legs)
                 # Height = Header + (Legs * Leg Draw Height) + Total Odds/Units Section + Footer
                 height = header_h + (num_legs * leg_draw_height) + 120 + footer_h # Example calculation
            else:
                height = base_height

            image = Image.new('RGB', (width, height), (40, 40, 40))
            draw = ImageDraw.Draw(image)

            # Load fonts using cached method
            header_font = self._load_font(32)
            team_font = self._load_font(24)
            details_font = self._load_font(28)
            small_font = self._load_font(18)
            # Odds/Units fonts based on user file code (details_font or specific)
            odds_font = details_font # Or self._load_font(28, is_bold=True)? User code uses details_font
            units_font = details_font # Or self._load_font(24, is_bold=True)? User code uses details_font
            emoji_font = ImageFont.truetype(self.emoji_font_path, 24) if os.path.exists(self.emoji_font_path) else details_font

            # Draw header (using logic from user file)
            header_y = 40
            header_text = f"{league.upper() if league else ''} - {'Straight Bet' if bet_type == 'straight' else 'Parlay'}"
            header_text = header_text.strip(" - ")
            # Center text
            bbox = draw.textbbox((0, 0), header_text, font=header_font)
            tw = bbox[2] - bbox[0]
            draw.text(((width - tw) / 2, header_y), header_text, fill='white', font=header_font)


            if bet_type == "straight":
                # --- Straight Bet Drawing (based on user file) ---
                logo_y = header_y + 60
                logo_size = (120, 120) # Size used in user file

                # Draw home team logo and name
                effective_league = league or 'NHL' # User file defaulted to NHL
                home_logo = self._load_team_logo(home_team, effective_league)
                if home_logo:
                    home_logo_disp = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    image.paste(home_logo_disp, (width // 4 - logo_size[0] // 2, logo_y), home_logo_disp)
                draw.text((width // 4, logo_y + logo_size[1] + 20), home_team, fill='white', font=team_font, anchor='mm')

                # Draw away team logo and name
                away_logo = self._load_team_logo(away_team, effective_league)
                if away_logo:
                    away_logo_disp = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    image.paste(away_logo_disp, (3 * width // 4 - logo_size[0] // 2, logo_y), away_logo_disp)
                draw.text((3 * width // 4, logo_y + logo_size[1] + 20), away_team, fill='white', font=team_font, anchor='mm')

                # Draw bet details (using 'line' argument as the primary bet text)
                details_y = logo_y + logo_size[1] + 80
                bet_text = f"{home_team}: {line}" # This line seems specific, maybe just use `line`?
                # Let's use just the line argument passed in, as it's more general
                bet_text = line
                draw.text((width // 2, details_y), bet_text, fill='white', font=details_font, anchor='mm')

                # Draw separator line
                separator_y = details_y + 40
                draw.line([(20, separator_y), (width - 20, separator_y)], fill='white', width=2) # White separator in user file

                # Draw odds below separator
                odds_y = separator_y + 30
                odds_text = self._format_odds_with_sign(int(odds)) # Format requires int
                draw.text((width // 2, odds_y), odds_text, fill='white', font=details_font, anchor='mm') # Using details_font per user file

                # Draw units with lock symbols
                units_y = odds_y + 40
                units_text = f"To Win {units:.2f} Units" # Assuming units is payout
                units_bbox = draw.textbbox((0, 0), units_text, font=details_font)
                units_width = units_bbox[2] - units_bbox[0]

                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 15
                    lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
                    image.paste(lock_icon, (lock_x_left, units_y - lock_icon.height // 2), lock_icon)
                    lock_x_right = lock_x_left + units_width + lock_icon.width + 2 * lock_spacing
                    image.paste(lock_icon, (lock_x_right, units_y - lock_icon.height // 2), lock_icon)
                    # Draw text between locks
                    draw.text((lock_x_left + lock_icon.width + lock_spacing + units_width // 2, units_y),
                              units_text, fill=(255, 215, 0), font=details_font, anchor='mm')
                else: # Fallback from user file
                    draw.text((width // 2, units_y), f"白 {units_text} 白",
                              fill=(255, 215, 0), font=emoji_font, anchor='mm')

            else: # Parlay logic from user file
                current_y = header_y + 60
                for i, leg in enumerate(parlay_legs):
                    if i > 0:
                        separator_y = current_y - 20 # Adjust Y based on drawing
                        draw.line([(20, separator_y), (width - 20, separator_y)], fill='white', width=1)
                        current_y += 20 # Space after separator

                    # Use _draw_parlay_leg helper (extracted from user file's generate_bet_slip)
                    current_y = self._draw_parlay_leg(
                        image=image, draw=draw, leg=leg, league=league, width=width, start_y=current_y,
                        team_font=team_font, odds_font=odds_font, units_font=units_font, emoji_font=emoji_font,
                        is_same_game=is_same_game
                    ) # _draw_parlay_leg returns the new Y position

                # Draw total parlay odds and units (using logic from user file)
                total_y = current_y + 40 # Space before totals
                draw.line([(20, total_y), (width - 20, total_y)], fill='white', width=2)
                total_y += 30

                # Calculate total odds - User file had a _calculate method, but also passed total odds in 'odds' arg
                # Let's trust the 'odds' arg passed for the total parlay odds
                total_odds_text = f"Total Odds: {self._format_odds_with_sign(int(odds))}"
                draw.text((width // 2, total_y), total_odds_text, fill='white', font=odds_font, anchor='mm')
                total_y += 40

                # Draw total units - User file assumed 'units' arg was total stake for parlay
                units_text = f"Total Units: {units:.2f}" # Displaying as 'Total Units' per user file
                units_bbox = draw.textbbox((0, 0), units_text, font=units_font)
                units_width = units_bbox[2] - units_bbox[0]
                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 15
                    lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
                    image.paste(lock_icon, (lock_x_left, total_y - lock_icon.height // 2), lock_icon)
                    lock_x_right = lock_x_left + units_width + lock_icon.width + 2 * lock_spacing
                    image.paste(lock_icon, (lock_x_right, total_y - lock_icon.height // 2), lock_icon)
                    draw.text((lock_x_left + lock_icon.width + lock_spacing + units_width // 2, total_y),
                              units_text, fill=(255, 215, 0), font=units_font, anchor='mm')
                else:
                    draw.text((width // 2, total_y), f"白 {units_text} 白",
                              fill=(255, 215, 0), font=emoji_font, anchor='mm')


            # Draw footer (common)
            footer_y = height - 30
            draw.text((20, footer_y), f"Bet #{bet_id}", fill=(150, 150, 150), font=small_font, anchor='lm')
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC') # Use UTC format
            # Right align timestamp
            ts_bbox = draw.textbbox((0,0), timestamp_text, font=small_font)
            ts_width = ts_bbox[2] - ts_bbox[0]
            draw.text((width - 20 - ts_width, footer_y), timestamp_text, fill=(150, 150, 150), font=small_font)

            logger.info(f"Bet slip PIL image generated successfully for Bet ID: {bet_id}")
            return image # Return the PIL Image object

        except Exception as e:
            logger.error(f"Error generating bet slip image for Bet ID {bet_id}: {str(e)}", exc_info=True)
            # Create a simple error image
            error_img = Image.new('RGB', (width, 200), (40, 40, 40))
            draw = ImageDraw.Draw(error_img)
            font = self._load_font(24) # Use cached font
            draw.text((width/2, 100), "Error Generating Bet Slip", fill="red", font=font, anchor="mm")
            return error_img # Return error image

    # Extracted parlay leg drawing logic from user's file
    def _draw_parlay_leg(
        self,
        image: Image.Image, # Pass image to paste onto
        draw: ImageDraw.Draw,
        leg: Dict[str, Any],
        league: Optional[str], # Overall league context
        width: int,
        start_y: int,
        team_font: ImageFont.FreeTypeFont,
        odds_font: ImageFont.FreeTypeFont,
        units_font: ImageFont.FreeTypeFont, # Note: units not drawn per leg in user file
        emoji_font: ImageFont.FreeTypeFont, # Note: lock icon not drawn per leg in user file
        draw_logos: bool = True, # Controlled by caller, user file implies true for parlays
        is_same_game: bool = False # Passed from caller
    ) -> int:
        """Draw a single leg of a parlay bet. Returns the Y position after drawing."""
        # Get leg details safely
        leg_home = leg.get('home_team', leg.get('team', 'Unknown'))
        leg_away = leg.get('opponent', 'Unknown')
        leg_line = leg.get('line', 'N/A')
        leg_odds = leg.get('odds', 0)
        leg_league = leg.get('league', league or 'UNKNOWN') # Use leg's league or fallback

        current_y = start_y
        logo_y = current_y + 10
        logo_disp_size = (50, 50) # Smaller size from user file's parlay logic
        text_start_x = 40 # Default start

        # Determine which team to show logo for based on bet line?
        # User file logic seems inconsistent here. Let's try loading home team logo.
        team_bet_on = leg_home
        if draw_logos: # Only draw if requested
            team_logo = self._load_team_logo(team_bet_on, leg_league)
            if team_logo:
                logo_x = 40
                team_logo_disp = team_logo.resize(logo_disp_size, Image.Resampling.LANCZOS)
                # Need alpha_composite if pasting RGBA onto RGB
                if image.mode != 'RGBA': image = image.convert("RGBA")
                temp_layer = Image.new('RGBA', image.size, (0,0,0,0))
                temp_layer.paste(team_logo_disp, (logo_x, logo_y), team_logo_disp)
                image = Image.alpha_composite(image, temp_layer)
                # Crucially, update the draw object if the image object was replaced
                draw = ImageDraw.Draw(image)
                text_start_x = logo_x + logo_disp_size[0] + 15
            else:
                 logger.debug(f"Parlay leg logo not found for {team_bet_on}")


        # Draw Line description
        draw.text((text_start_x, logo_y + 5), leg_line, fill='white', font=details_font) # User file used details_font size
        # Draw League/Matchup below line
        matchup_text = f"{leg_home} vs {leg_away}" if leg_home != 'Unknown' and leg_away != 'Unknown' else leg_home
        draw.text((text_start_x, logo_y + 40), f"{leg_league} - {matchup_text}", fill=(180, 180, 180), font=small_font)

        # Draw Leg Odds (Right Aligned)
        leg_odds_text = self._format_odds_with_sign(int(leg_odds))
        # Vertical centering within the allocated leg height
        leg_center_y = start_y + (leg_draw_height / 2) # Use the allocated height parameter
        bbox = draw.textbbox((0,0), leg_odds_text, font=odds_font)
        tw = bbox[2]-bbox[0]; th = bbox[3]-bbox[1]
        draw.text((width - 40 - tw, leg_center_y - (th/2)), leg_odds_text, fill='white', font=odds_font)

        # Return Y position for the start of the *next* leg
        return start_y + leg_draw_height # Move down by allocated height


    # Removed _save_team_logo - this class shouldn't save files unless intended as primary function
    # Removed save_bet_slip - returns PIL Image object

# --- Example Usage Block ---
if __name__ == '__main__':
    # This block only runs when the script is executed directly
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__) # Re-get logger for __main__ scope
    logger.info("Testing BetSlipGenerator directly...")

    # Define constants and fonts for testing scope
    try:
        _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # IMPORTANT: Adjust this if your asset folder is named differently or elsewhere
        ASSET_DIR = os.path.join(_base_dir, 'assets') # Assuming assets/ not betting-bot/static/
        if not os.path.isdir(ASSET_DIR): ASSET_DIR = os.path.join(_base_dir, 'static') # Fallback to static
        if not os.path.isdir(ASSET_DIR): ASSET_DIR = '.' # Final fallback
        logger.info(f"[Test] Using ASSET_DIR: {ASSET_DIR}")

        DEFAULT_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'Roboto-Regular.ttf')
        DEFAULT_BOLD_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'Roboto-Bold.ttf')
        DEFAULT_EMOJI_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'NotoEmoji-Regular.ttf') # Add emoji path def
        LOGO_DIR = os.path.join(ASSET_DIR, 'logos')
        DEFAULT_TEAM_LOGO_PATH = os.path.join(LOGO_DIR, 'default_logo.png')

        # Load fonts within __main__ scope for testing
        if not os.path.exists(DEFAULT_FONT_PATH): raise FileNotFoundError(f"[Test] Font missing: {DEFAULT_FONT_PATH}")
        if not os.path.exists(DEFAULT_BOLD_FONT_PATH): raise FileNotFoundError(f"[Test] Font missing: {DEFAULT_BOLD_FONT_PATH}")
        # Emoji font existence check happens within generator's __init__/helpers

        font_m_18 = ImageFont.truetype(DEFAULT_FONT_PATH, 18); font_m_24 = ImageFont.truetype(DEFAULT_FONT_PATH, 24)
        font_b_18 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 18); font_b_24 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 24)
        font_b_36 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 36)
        logger.info("[Test] Fonts loaded for __main__.")
    except Exception as e:
        logger.critical(f"[Test] CRITICAL: Error setting up constants/fonts in __main__: {e}")
        exit(1)

    from collections import namedtuple # Keep for mock data
    # Define mock structures matching expected attributes
    MockBetLeg = namedtuple("MockBetLeg", ["league_name", "team_name", "bet_type", "line", "odds", "opponent"])
    MockBet = namedtuple("MockBet", ["bet_id", "stake", "total_odds", "potential_payout", "capper_name", "legs"])

    # --- Test Execution ---
    # Pass the explicitly found asset dir to the generator for testing
    generator = BetSlipGenerator(assets_dir=ASSET_DIR)
    print("Generating example slips (using mock data)...")

    # Example 1: Straight Bet
    pil_image_straight = generator.generate_bet_slip(
        home_team="Boston Bruins", away_team="Florida Panthers", league="NHL",
        line="Boston Bruins ML", odds=-150, units=1.0, # Assume units = stake for straight
        bet_id="ST123", timestamp=datetime.now(timezone.utc), bet_type="straight"
    )
    if pil_image_straight:
        try:
            pil_image_straight.save("test_straight_slip_generated.png")
            print(" - test_straight_slip_generated.png saved.")
        except Exception as e: print(f" - FAILED to save straight slip: {e}")
    else: print(" - FAILED to generate straight slip.")

    # Example 2: Multi-Team Parlay
    parlay_legs_data = [
        # Use the MockBetLeg structure
        MockBetLeg(league_name='NFL', team_name='Kansas City Chiefs', bet_type='Spread', line='KC Chiefs -7.5', odds=-110, opponent='Denver Broncos'),
        MockBetLeg(league_name='NBA', team_name='Los Angeles Lakers', bet_type='Moneyline', line='LAL ML', odds=150, opponent='Golden State Warriors'),
    ]
    # For parlays, 'odds' is total parlay odds, 'units' is stake
    pil_image_parlay = generator.generate_bet_slip(
        home_team=parlay_legs_data[0].team_name, # Use first leg for top display
        away_team=parlay_legs_data[0].opponent,
        league=None, # League displayed per leg
        line="2-Leg Parlay", odds=250, units=1.0, # Total odds, total stake
        bet_id="PA456", timestamp=datetime.now(timezone.utc),
        bet_type="parlay", parlay_legs=parlay_legs_data, is_same_game=False
    )
    if pil_image_parlay:
        try:
            pil_image_parlay.save("test_parlay_slip_generated.png")
            print(" - test_parlay_slip_generated.png saved.")
        except Exception as e: print(f" - FAILED to save parlay slip: {e}")
    else: print(" - FAILED to generate parlay slip.")

    print("Testing complete.")
