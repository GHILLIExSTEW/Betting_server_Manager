# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime, timezone # Added timezone import
from typing import Optional, List, Dict, Any
import time
from io import BytesIO # For saving image to memory

logger = logging.getLogger(__name__)

class BetSlipGenerator:
    def __init__(self, font_path: Optional[str] = None, emoji_font_path: Optional[str] = None):
        # Use os.path.join for better cross-platform compatibility
        # Assume the script runs from the project root or paths are adjusted accordingly
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Get betting-bot directory

        self.assets_dir = os.path.join(project_root, 'static') # Corrected path relative to project root
        self.font_path = font_path or self._get_default_font(self.assets_dir)
        self.bold_font_path = self._get_default_bold_font(self.assets_dir)
        self.emoji_font_path = emoji_font_path or self._get_default_emoji_font(self.assets_dir)

        # Base directory for logos within the static folder
        self.logos_base_dir = os.path.join(self.assets_dir, "logos")
        self.league_team_base_dir = os.path.join(self.logos_base_dir, "teams")
        self.league_logo_base_dir = os.path.join(self.logos_base_dir, "leagues")

        self._ensure_font_exists()
        self._ensure_bold_font_exists()
        self._ensure_emoji_font_exists()

        # Initialize caches
        self._logo_cache = {}
        self._font_cache = {}
        self._lock_icon_cache = None
        self._max_cache_size = 100  # Maximum number of items in logo cache
        self._cache_expiry = 3600  # Cache expiry time in seconds (1 hour)
        self._last_cache_cleanup = time.time()
        self._ensure_base_dirs_exist() # Ensure directories are created on init

    def _ensure_base_dirs_exist(self):
        """Ensure base directories for static assets and logos exist."""
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.logos_base_dir, exist_ok=True)
        os.makedirs(self.league_team_base_dir, exist_ok=True)
        os.makedirs(self.league_logo_base_dir, exist_ok=True)
        logger.debug(f"Ensured base directories exist: {self.assets_dir}, {self.logos_base_dir}")

    # --- Font loading methods (_get_default_font, _get_default_bold_font, _get_default_emoji_font) ---
    # (Keep these as they were in the previous correct version, including fallbacks)
    def _get_default_font(self, assets_dir: str) -> str:
        """Get the default font path for regular text."""
        custom_font_path = os.path.join(assets_dir, "fonts", "Roboto-Regular.ttf")
        if os.path.exists(custom_font_path):
            logger.debug(f"Using regular font at {custom_font_path}")
            return custom_font_path
        logger.warning(f"Custom font {custom_font_path} not found.")
        if os.name == 'nt':
            fallback = 'C:\\Windows\\Fonts\\arial.ttf'
            if os.path.exists(fallback): return fallback
        else:
            fallbacks = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/System/Library/Fonts/Supplemental/Arial.ttf'
            ]
            for fb in fallbacks:
                if os.path.exists(fb): return fb
        logger.error("Could not find a suitable default regular font.")
        return "arial.ttf"

    def _get_default_bold_font(self, assets_dir: str) -> str:
        """Get the default bold font path for emphasized text."""
        custom_bold_font_path = os.path.join(assets_dir, "fonts", "Roboto-Bold.ttf")
        if os.path.exists(custom_bold_font_path):
            logger.debug(f"Using bold font at {custom_bold_font_path}")
            return custom_bold_font_path
        logger.warning(f"Custom bold font {custom_bold_font_path} not found, falling back to regular font.")
        return self._get_default_font(assets_dir)

    def _get_default_emoji_font(self, assets_dir: str) -> str:
        """Get the default font path for emojis."""
        custom_emoji_font_paths = [
            os.path.join(assets_dir, "fonts", "NotoEmoji-Regular.ttf"),
            os.path.join(assets_dir, "fonts", "SegoeUIEmoji.ttf")
        ]
        for path in custom_emoji_font_paths:
            if os.path.exists(path):
                logger.debug(f"Using custom emoji font at {path}")
                return path
        logger.warning(f"Custom emoji fonts not found in {os.path.join(assets_dir, 'fonts')}.")
        if os.name == 'nt':
            fallback = 'C:\\Windows\\Fonts\\seguiemj.ttf'
            if os.path.exists(fallback): return fallback
        else:
            fallbacks = [
                '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
                '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf',
                '/System/Library/Fonts/Apple Color Emoji.ttc'
            ]
            for fb in fallbacks:
                if os.path.exists(fb): return fb
        logger.error("Could not find a suitable default emoji font. Emojis may not render correctly.")
        return self._get_default_font(assets_dir)

    # --- Font existence checks (_ensure_font_exists, _ensure_bold_font_exists, _ensure_emoji_font_exists) ---
    # (Keep these as they were in the previous correct version)
    def _ensure_font_exists(self) -> None:
        """Ensure the regular font file exists."""
        try:
            ImageFont.truetype(self.font_path, 10)
            logger.debug(f"Regular font confirmed at {self.font_path}")
        except IOError:
            logger.error(f"Font file not found or invalid at configured path: {self.font_path}")
            try:
                 ImageFont.load_default()
                 logger.warning("Falling back to Pillow's default font.")
                 self.font_path = "PillowDefault" # Indicate fallback
            except Exception as e:
                 logger.critical(f"Pillow default font also failed: {e}. Cannot generate images.")
                 raise FileNotFoundError(f"Font not found at {self.font_path} and Pillow default failed.")
        except Exception as e:
             logger.critical(f"Unexpected error loading font {self.font_path}: {e}")
             raise

    def _ensure_bold_font_exists(self) -> None:
        """Ensure the bold font file exists."""
        try:
            ImageFont.truetype(self.bold_font_path, 10)
            logger.debug(f"Bold font confirmed at {self.bold_font_path}")
        except IOError:
            logger.warning(f"Bold font file not found or invalid at {self.bold_font_path}. Falling back to regular font.")
            self.bold_font_path = self.font_path
        except Exception as e:
            logger.error(f"Unexpected error loading bold font {self.bold_font_path}. Falling back to regular.")
            self.bold_font_path = self.font_path

    def _ensure_emoji_font_exists(self) -> None:
        """Ensure the emoji font file exists."""
        try:
             ImageFont.truetype(self.emoji_font_path, 10)
             logger.debug(f"Emoji font confirmed at {self.emoji_font_path}")
        except IOError:
             logger.warning(f"Emoji font file not found or invalid at {self.emoji_font_path}. Emojis might render as tofu.")
        except Exception as e:
             logger.error(f"Unexpected error loading emoji font {self.emoji_font_path}. Emojis might render as tofu.")
             self.emoji_font_path = self.font_path # Fallback to regular

    # --- Helper to get sport category ---
    def _get_sport_category(self, league: str) -> str:
        """Helper to get sport category for path construction."""
        # Should match SPORT_CATEGORY_MAP in load_logos.py
        sport_category_map = {
            "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
            "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
            "MLB": "BASEBALL",
            "NHL": "HOCKEY",
            "SOCCER": "SOCCER",
            "TENNIS": "TENNIS",
            "UFC/MMA": "MMA"
            # Add others as needed
        }
        return sport_category_map.get(league.upper(), "OTHER")

    # --- Directory existence checks (_ensure_team_dir_exists, _ensure_league_dir_exists) ---
    # (Keep these as they were in the previous correct version)
    def _ensure_team_dir_exists(self, league: str) -> str:
        """Ensure the team logos directory exists for the given league and returns its path."""
        sport_category = self._get_sport_category(league)
        league_dir = os.path.join(self.league_team_base_dir, sport_category, league.upper())
        try:
            os.makedirs(league_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory {league_dir}: {e}")
        return league_dir

    def _ensure_league_dir_exists(self, league: str) -> str:
        """Ensure the league logos directory exists for the given league and returns its path."""
        league_dir = os.path.join(self.league_logo_base_dir, league.upper())
        try:
            os.makedirs(league_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory {league_dir}: {e}")
        return league_dir

    # --- Cache cleanup method (_cleanup_cache) ---
    # (Keep as it was in the previous correct version)
    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        if current_time - self._last_cache_cleanup > 300:
            expired_keys = [key for key, (_, timestamp) in self._logo_cache.items() if current_time - timestamp > self._cache_expiry]
            for key in expired_keys:
                if key in self._logo_cache: # Double check existence before deleting
                     del self._logo_cache[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired logo cache entries.")
            self._last_cache_cleanup = current_time


    # --- Logo loading method (_load_team_logo) ---
    # (Keep as it was in the previous correct version, uses standardized path)
    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Load the team logo image based on team name and league with caching."""
        if not team_name or not league:
             logger.warning("Attempted to load logo with empty team name or league.")
             return None

        try:
            # Use lowercase for cache key consistency
            cache_key = f"team_{league.lower()}_{team_name.lower()}"
            current_time = time.time()

            # Check cache first
            if cache_key in self._logo_cache:
                logo, timestamp = self._logo_cache[cache_key]
                if current_time - timestamp <= self._cache_expiry:
                    logger.debug(f"Cache hit for logo: {cache_key}")
                    return logo.copy() # Return a copy
                else:
                    del self._logo_cache[cache_key] # Expired

            # Construct the expected path based on static/logos/teams structure
            sport_category = self._get_sport_category(league)
            league_dir_path = os.path.join(self.league_team_base_dir, sport_category, league.upper())

            # Normalize team name for filename (matching load_logos.py's saving logic)
            normalized_name = team_name.lower().replace(' ', '_')
            logo_filename = f"{normalized_name}.png"
            logo_path = os.path.join(league_dir_path, logo_filename)

            logger.debug(f"Attempting to load logo from path: {logo_path}")

            if os.path.exists(logo_path):
                try:
                    logo = Image.open(logo_path).convert("RGBA")
                    # Assume logo is already appropriately sized by load_logos

                    # Update cache
                    self._cleanup_cache() # Clean up before potentially adding
                    if len(self._logo_cache) >= self._max_cache_size:
                        try:
                            # Simple FIFO eviction if cache full
                            oldest_key = next(iter(self._logo_cache))
                            del self._logo_cache[oldest_key]
                            logger.debug(f"Cache full. Evicted logo: {oldest_key}")
                        except StopIteration:
                            pass # Cache was empty, shouldn't happen if len > max_size

                    self._logo_cache[cache_key] = (logo, current_time)
                    logger.debug(f"Loaded and cached logo: {cache_key}")
                    return logo.copy() # Return a copy
                except Exception as img_err:
                    logger.error(f"Error opening or processing logo file {logo_path}: {img_err}")
                    return None
            else:
                logger.warning(f"Logo not found at expected path: {logo_path}")
                return None
        except Exception as e:
            logger.exception(f"Error loading logo for team '{team_name}' in league '{league}': {e}")
            return None

    # --- Font loading method (_load_font) ---
    # (Keep as it was in the previous correct version)
    def _load_font(self, size: int, is_bold: bool = False) -> ImageFont.FreeTypeFont:
        """Load font with caching."""
        font_type = 'bold' if is_bold else 'regular'
        cache_key = f"font_{font_type}_{size}"
        if cache_key not in self._font_cache:
            try:
                font_path_to_use = self.bold_font_path if is_bold else self.font_path
                if font_path_to_use == "PillowDefault":
                     self._font_cache[cache_key] = ImageFont.load_default()
                     logger.warning(f"Using Pillow default font for {font_type} size {size}")
                else:
                     self._font_cache[cache_key] = ImageFont.truetype(font_path_to_use, size)
            except Exception as e:
                logger.error(f"Failed to load font {font_type} size {size} from {font_path_to_use}: {e}. Using default font.")
                self._font_cache[cache_key] = ImageFont.load_default()
        return self._font_cache[cache_key]

    # --- Lock icon loading method (_load_lock_icon) ---
    # (Keep as it was in the previous correct version)
    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Load the lock icon image with caching."""
        if self._lock_icon_cache is None:
            try:
                lock_path = os.path.join(self.assets_dir, "images", "lock_icon.png")
                if os.path.exists(lock_path):
                    lock = Image.open(lock_path).convert("RGBA")
                    lock = lock.resize((20, 20), Image.Resampling.LANCZOS)
                    self._lock_icon_cache = lock
                else:
                    logger.warning(f"Lock icon not found at {lock_path}")
                    return None
            except Exception as e:
                logger.error(f"Error loading lock icon: {str(e)}")
                return None
        # Return a copy to prevent modification issues if the icon is pasted multiple times
        return self._lock_icon_cache.copy()


    # --- Main generation method (generate_bet_slip) ---
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
        is_same_game: bool = False # Used to decide on logo drawing for first leg
    ) -> Image.Image:
        """Generate a bet slip image for straight or parlay bets."""
        try:
            # --- Determine Image Dimensions ---
            width = 800
            base_height = 450
            leg_height_with_logos = 220 # Approx height if logos are drawn
            leg_height_no_logos = 100 # Approx height if no logos (just text)
            details_height = 150 # Space for line, odds, units in straight bet
            footer_height = 50
            header_height = 80
            separator_height = 20
            totals_height = 80 # Space for total odds/units in parlay

            height = header_height # Start with header

            if bet_type == "straight":
                height += 150 # Logo section
                height += details_height # Bet details section
                height += footer_height
                height = max(base_height, height) # Ensure min height
            elif bet_type == "parlay" and parlay_legs:
                num_legs = len(parlay_legs)
                # Draw logos only for the first leg IF it's a same-game parlay
                first_leg_draw_logos = is_same_game

                for i in range(num_legs):
                    if i > 0: height += separator_height
                    if i == 0 and first_leg_draw_logos:
                        height += leg_height_with_logos
                    else:
                         height += leg_height_no_logos
                height += separator_height # Separator before totals
                height += totals_height # Total Odds/Units
                height += footer_height # Footer
                height = max(base_height, height) # Ensure min height
            else: # Default case or error
                height = base_height

            image = Image.new('RGB', (width, height), (40, 40, 40)) # Dark background
            draw = ImageDraw.Draw(image)

            # --- Load Fonts ---
            try:
                header_font = self._load_font(32, is_bold=True)
                team_font = self._load_font(28) # Slightly larger team names
                details_font = self._load_font(24) # Font for line/details
                odds_font = self._load_font(28, is_bold=True) # Bold odds
                units_font = self._load_font(24) # Font for units text
                small_font = self._load_font(18)
                try:
                     emoji_font = ImageFont.truetype(self.emoji_font_path, 24)
                except (IOError, OSError): # Catch potential errors loading specific font
                     logger.warning(f"Cannot load emoji font {self.emoji_font_path}, using details font as fallback.")
                     emoji_font = details_font # Fallback
            except Exception as e:
                logger.error(f"Failed to load fonts: {e}. Using default fonts.")
                header_font = team_font = details_font = odds_font = units_font = small_font = emoji_font = ImageFont.load_default()

            # --- Draw Header ---
            header_y = 40
            # Use Multi-Team Parlay Bet title based on guideline
            if bet_type == "parlay" and not is_same_game:
                 header_text_type = "Multi-Team Parlay Bet"
            elif bet_type == "parlay" and is_same_game:
                 header_text_type = "Same-Game Parlay"
            else:
                 header_text_type = "Straight Bet"

            header_text = f"{league} - {header_text_type}" if league else header_text_type
            draw.text((width // 2, header_y), header_text, fill='white', font=header_font, anchor='mm')

            current_y = header_y + 60 # Start drawing content below header

            # --- Draw Straight Bet Details ---
            if bet_type == "straight":
                logo_size = (100, 100) # Standard logo size

                # Load logos
                # Provide a default league like 'NHL' if league is None, or handle gracefully
                current_league = league or 'NHL'
                home_logo = self._load_team_logo(home_team, current_league)
                away_logo = self._load_team_logo(away_team, current_league)

                # Draw home team logo and name
                home_x = width // 4
                if home_logo:
                    image.paste(home_logo, (home_x - logo_size[0] // 2, current_y), home_logo)
                draw.text((home_x, current_y + logo_size[1] + 15), home_team, fill='white', font=team_font, anchor='mm')

                # Draw away team logo and name
                away_x = 3 * width // 4
                if away_logo:
                    image.paste(away_logo, (away_x - logo_size[0] // 2, current_y), away_logo)
                draw.text((away_x, current_y + logo_size[1] + 15), away_team, fill='white', font=team_font, anchor='mm')

                current_y += logo_size[1] + 40 # Move below logos and names

                # Draw bet line
                bet_text = f"{home_team}: {line}" # Adjust formatting based on line type if needed
                draw.text((width // 2, current_y), bet_text, fill='white', font=details_font, anchor='mm')
                current_y += 40

                # Draw separator line
                draw.line([(40, current_y), (width - 40, current_y)], fill=(80, 80, 80), width=2)
                current_y += 30

                # Draw odds
                odds_text = f"{odds:+.0f}" if odds else "N/A"
                draw.text((width // 2, current_y), odds_text, fill='white', font=odds_font, anchor='mm') # Use bold odds font
                current_y += 40

                # Draw units with lock symbols
                units_text = f"To Win {units:.2f} Units"
                # Use textbbox for more accurate width calculation if available, otherwise getsize
                try:
                    units_bbox = draw.textbbox((0, 0), units_text, font=units_font)
                    units_width = units_bbox[2] - units_bbox[0]
                except AttributeError: # Fallback for older Pillow versions
                    units_width, _ = draw.textsize(units_text, font=units_font)


                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 10
                    # Try to align lock icon vertically with text
                    text_height = units_font.getmetrics()[0] if hasattr(units_font, 'getmetrics') else 20 # Approx height
                    lock_y_offset = (text_height - lock_icon.height) // 2
                    base_lock_y = current_y - (text_height // 2) # Center text vertically first

                    lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
                    image.paste(lock_icon, (lock_x_left, base_lock_y + lock_y_offset), lock_icon)

                    # Draw units text between locks
                    text_x = lock_x_left + lock_icon.width + lock_spacing
                    draw.text((text_x, current_y), units_text, fill=(255, 215, 0), font=units_font, anchor='lm') # Gold color, left-middle anchor

                    lock_x_right = text_x + units_width + lock_spacing
                    image.paste(lock_icon, (lock_x_right, base_lock_y + lock_y_offset), lock_icon)
                else:
                    # Fallback to emoji locks
                    draw.text(
                        (width // 2, current_y),
                        f"🔒 {units_text} 🔒", # Use actual lock emoji if font supports
                        fill=(255, 215, 0),
                        font=emoji_font, # Use specific emoji font
                        anchor='mm'
                    )
                current_y += 40

            # --- Draw Parlay Bet Details ---
            elif bet_type == "parlay" and parlay_legs:
                # Determine if logos should be drawn for the first leg
                draw_first_leg_logos = is_same_game

                # Draw each leg
                for i, leg in enumerate(parlay_legs):
                    # Separator line (light grey)
                    if i > 0:
                        draw.line([(40, current_y - 10), (width - 40, current_y - 10)], fill=(80, 80, 80), width=1)
                        current_y += 10

                    # Draw the leg details using _draw_leg
                    current_y = self._draw_leg(
                        image=image,
                        draw=draw,
                        leg=leg,
                        # Use leg's league, fallback to main league, fallback to 'NHL'
                        league=leg.get('league', league or 'NHL'),
                        width=width,
                        start_y=current_y,
                        team_font=team_font, # Pass fonts
                        details_font=details_font,
                        odds_font=odds_font, # Pass odds font
                        emoji_font=emoji_font,
                        # Draw logos ONLY for the first leg IF it's a same-game parlay
                        draw_logos=(i == 0 and draw_first_leg_logos)
                    )
                    current_y += 10 # Add padding after each leg

                # Draw separator before total odds/units
                current_y += 10
                draw.line([(20, current_y), (width - 20, current_y)], fill='white', width=2)
                current_y += 30

                # --- Total Odds and Units for Parlay ---
                # 'odds' passed to generate_bet_slip should be the final parlay odds
                total_odds_display = odds
                # Sum units from individual legs if they exist, otherwise use 'units' passed
                if all('units' in leg for leg in parlay_legs):
                     total_units_display = sum(float(leg.get('units', 0)) for leg in parlay_legs)
                else:
                     total_units_display = units # Use the single 'units' value passed

                # Draw total odds
                odds_text = f"Total Odds: {total_odds_display:+.0f}" if total_odds_display else "Total Odds: N/A"
                draw.text((width // 2, current_y), odds_text, fill='white', font=odds_font, anchor='mm') # Use bold odds font
                current_y += 40

                # Draw total units with lock symbols
                units_text = f"Total Units: {total_units_display:.2f}"
                try:
                    units_bbox = draw.textbbox((0, 0), units_text, font=units_font)
                    units_width = units_bbox[2] - units_bbox[0]
                except AttributeError:
                    units_width, _ = draw.textsize(units_text, font=units_font)

                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 10
                    text_height = units_font.getmetrics()[0] if hasattr(units_font, 'getmetrics') else 20
                    lock_y_offset = (text_height - lock_icon.height) // 2
                    base_lock_y = current_y - (text_height // 2)

                    lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
                    image.paste(lock_icon, (lock_x_left, base_lock_y + lock_y_offset), lock_icon)

                    text_x = lock_x_left + lock_icon.width + lock_spacing
                    draw.text((text_x, current_y), units_text, fill=(255, 215, 0), font=units_font, anchor='lm')

                    lock_x_right = text_x + units_width + lock_spacing
                    image.paste(lock_icon, (lock_x_right, base_lock_y + lock_y_offset), lock_icon)
                else:
                    draw.text(
                        (width // 2, current_y),
                        f"🔒 {units_text} 🔒",
                        fill=(255, 215, 0),
                        font=emoji_font,
                        anchor='mm'
                    )
                current_y += 40

            # --- Draw Footer ---
            # Ensure footer doesn't overlap content, place it relative to calculated height
            footer_y = height - 30
            draw.text((20, footer_y), f"Bet #{bet_id}", fill=(150, 150, 150), font=small_font, anchor='lm')
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC') # Add UTC
            draw.text((width - 20, footer_y), timestamp_text, fill=(150, 150, 150), font=small_font, anchor='rm')

            return image

        except Exception as e:
            logger.exception(f"Error generating bet slip: {str(e)}")
            # Create a simple error image as fallback
            error_img = Image.new('RGB', (800, 100), (40, 40, 40))
            error_draw = ImageDraw.Draw(error_img)
            error_font = self._load_font(20) if self._font_cache else ImageFont.load_default()
            error_draw.text((10, 10), f"Error generating bet slip image. Please check logs.", fill='red', font=error_font)
            return error_img

    # --- Method to draw a single parlay leg ---
    def _draw_leg(
        self,
        image: Image.Image,
        draw: ImageDraw.Draw,
        leg: Dict[str, Any],
        league: str,
        width: int,
        start_y: int,
        team_font: ImageFont.FreeTypeFont,
        details_font: ImageFont.FreeTypeFont,
        odds_font: ImageFont.FreeTypeFont, # Added odds font
        emoji_font: ImageFont.FreeTypeFont,
        draw_logos: bool = True # Control logo drawing per leg
    ) -> int:
        """Draw a single leg of a parlay bet."""
        home_team = leg.get('home_team', leg.get('team', 'Unknown'))
        away_team = leg.get('away_team', leg.get('opponent', 'Unknown'))
        line = leg.get('line', 'ML')
        # Individual leg odds might be present, use bold font if showing
        leg_odds = float(leg.get('odds', 0))

        current_y = start_y
        logo_size = (80, 80) # Smaller logos for legs
        content_start_x = 40
        content_end_x = width - 40
        content_width = content_end_x - content_start_x

        # --- Draw Logos (if enabled for this leg) ---
        if draw_logos:
            home_logo = self._load_team_logo(home_team, league)
            away_logo = self._load_team_logo(away_team, league)

            logo_y_padding = 15
            home_x = width * 0.3 # Position logos closer for leg view
            away_x = width * 0.7

            if home_logo:
                image.paste(home_logo, (int(home_x - logo_size[0] // 2), current_y + logo_y_padding), home_logo)
            if away_logo:
                image.paste(away_logo, (int(away_x - logo_size[0] // 2), current_y + logo_y_padding), away_logo)

            # Team names below logos
            team_y = current_y + logo_size[1] + logo_y_padding + 15
            draw.text((home_x, team_y), home_team, fill='white', font=team_font, anchor='mm')
            draw.text((away_x, team_y), away_team, fill='white', font=team_font, anchor='mm')
            current_y = team_y + 40 # Move Y position down significantly after logos/names
        else:
            # No logos, start drawing text lower
             current_y += 20

        # --- Draw Bet Details (Line) ---
        details_y = current_y
        line_text = f"{home_team} vs {away_team}: {line}"
        # Truncate line text if too long
        max_line_width = width - 80 # Leave some padding
        try:
             line_bbox = draw.textbbox((0,0), line_text, font=details_font)
             line_width = line_bbox[2] - line_bbox[0]
        except AttributeError:
             line_width, _ = draw.textsize(line_text, font=details_font)

        if line_width > max_line_width:
             # Simple truncation
             approx_chars = int(len(line_text) * (max_line_width / line_width)) - 3
             line_text = line_text[:max(10, approx_chars)] + "..." # Ensure at least some chars show

        draw.text((width // 2, details_y), line_text, fill='white', font=details_font, anchor='mm')
        current_y = details_y + 35 # Space after line text

        # --- Draw Individual Leg Odds (Optional) ---
        # Uncomment below if you want to show odds for each leg
        # if leg_odds:
        #     leg_odds_text = f"{leg_odds:+.0f}"
        #     draw.text((width // 2, current_y), leg_odds_text, fill=(200, 200, 200), font=odds_font, anchor='mm') # Lighter color for leg odds
        #     current_y += 35

        return current_y # Return the Y position after drawing this leg

    # --- Other Methods (_calculate_parlay_odds, _save_team_logo, save_bet_slip) ---
    def _calculate_parlay_odds(self, legs: List[Dict[str, Any]]) -> float:
        """Calculate the total odds for a parlay bet based on leg odds."""
        try:
            total_decimal_odds = 1.0
            for leg in legs:
                leg_odds = float(leg.get('odds', 0)) # Assumes 'odds' key holds American odds
                if leg_odds == 0: continue

                if leg_odds > 0:
                    decimal_leg = (leg_odds / 100) + 1
                else:
                    decimal_leg = (100 / abs(leg_odds)) + 1
                total_decimal_odds *= decimal_leg

            if total_decimal_odds == 1.0: return 0.0
            if total_decimal_odds >= 2.0:
                final_american_odds = (total_decimal_odds - 1) * 100
            else:
                final_american_odds = -100 / (total_decimal_odds - 1)

            return final_american_odds
        except Exception as e:
            logger.error(f"Error calculating parlay odds from legs: {str(e)}")
            return 0.0

    def _save_team_logo(self, logo: Image.Image, team_name: str, league: str) -> None:
        """Placeholder: Logic to save logos if needed (now handled by load_logos)."""
        logger.debug(f"Placeholder: _save_team_logo called for {team_name}, {league}. Saving handled by load_logos.")
        pass

    def save_bet_slip(self, image: Image.Image, output_path: str) -> None:
        """Save the bet slip image to a file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # Optimize PNG saving
            image.save(output_path, "PNG", optimize=True)
            logger.info(f"Bet slip image saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving bet slip image to {output_path}: {str(e)}")
            raise # Re-raise the exception
