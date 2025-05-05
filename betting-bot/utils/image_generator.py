# betting-bot/utils/image_generator.py

"""Generates bet slip images using PIL."""

import logging
import os
import time
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class BetSlipGenerator:
    """
    Handles the creation of bet slip images with team logos and details.

    Attributes:
        assets_dir (str): Path to the static assets directory.
        font_path (str): Path to the regular font file.
        bold_font_path (str): Path to the bold font file.
        emoji_font_path (str): Path to the emoji font file.
        emoji_font_loaded (bool): Flag indicating if the emoji font loaded.
        logos_base_dir (str): Base path for all logos.
        league_team_base_dir (str): Base path for team logos.
        league_logo_base_dir (str): Base path for league logos.
    """

    # Max items and expiry for the logo cache
    _MAX_CACHE_SIZE = 100
    _CACHE_EXPIRY = 3600  # 1 hour in seconds

    def __init__(
        self,
        font_path: Optional[str] = None,
        emoji_font_path: Optional[str] = None,
    ):
        """
        Initializes the BetSlipGenerator.

        Args:
            font_path: Optional path to the regular font file.
            emoji_font_path: Optional path to the emoji font file.
        """
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.assets_dir = os.path.join(project_root, 'static')
        logger.info(f"Assets directory set to: {self.assets_dir}")

        # --- Font Setup ---
        self.font_path = font_path or self._get_default_font(self.assets_dir)
        self.bold_font_path = self._get_default_bold_font(self.assets_dir)
        self.emoji_font_path = emoji_font_path or self._get_default_emoji_font(
            self.assets_dir
        )
        self.emoji_font_loaded = False

        # --- Path Setup ---
        self.logos_base_dir = os.path.join(self.assets_dir, "logos")
        self.league_team_base_dir = os.path.join(self.logos_base_dir, "teams")
        self.league_logo_base_dir = os.path.join(self.logos_base_dir, "leagues")

        # --- Initialization ---
        self._ensure_base_dirs_exist()
        self._ensure_font_exists()
        self._ensure_bold_font_exists()
        self._ensure_emoji_font_exists()  # Sets self.emoji_font_loaded

        # --- Caches ---
        self._logo_cache: Dict[str, tuple[Image.Image, float]] = {}
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self._lock_icon_cache: Optional[Image.Image] = None
        self._last_cache_cleanup: float = time.time()

    def _ensure_base_dirs_exist(self):
        """Ensure base directories for static assets and logos exist."""
        dirs_to_create = [
            self.assets_dir,
            self.logos_base_dir,
            self.league_team_base_dir,
            self.league_logo_base_dir,
        ]
        for directory in dirs_to_create:
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as e:
                logger.error(f"Could not create directory {directory}: {e}")
        logger.debug(f"Ensured base directories exist: {self.assets_dir}")

    def _get_default_font(self, assets_dir: str) -> str:
        """Finds a suitable default regular font file."""
        custom_font = os.path.join(assets_dir, "fonts", "Roboto-Regular.ttf")
        if os.path.exists(custom_font):
            logger.debug(f"Using regular font: {custom_font}")
            return custom_font

        logger.warning(f"Custom font not found: {custom_font}.")
        if os.name == 'nt':
            sys_font = 'C:\\Windows\\Fonts\\arial.ttf'
            if os.path.exists(sys_font):
                logger.info(f"Using system fallback font: {sys_font}")
                return sys_font
        else:
            sys_fonts = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/System/Library/Fonts/Supplemental/Arial.ttf',
            ]
            for sys_font in sys_fonts:
                if os.path.exists(sys_font):
                    logger.info(f"Using system fallback font: {sys_font}")
                    return sys_font

        logger.error("Could not find a suitable default regular font.")
        return "arial.ttf" # Let Pillow try to find Arial

    def _get_default_bold_font(self, assets_dir: str) -> str:
        """Finds a suitable default bold font file."""
        custom_font = os.path.join(assets_dir, "fonts", "Roboto-Bold.ttf")
        if os.path.exists(custom_font):
            logger.debug(f"Using bold font: {custom_font}")
            return custom_font
        logger.warning(f"Custom bold font not found: {custom_font}.")
        # Assuming Arial Bold exists if Arial exists (less reliable)
        regular_font = self._get_default_font(assets_dir)
        if "arial.ttf" in regular_font.lower():
            if os.name == 'nt':
                 bold_fallback = 'C:\\Windows\\Fonts\\arialbd.ttf'
                 if os.path.exists(bold_fallback): return bold_fallback
            # Add other OS bold fallbacks if needed
        logger.warning("Falling back to regular font for bold.")
        return regular_font

    def _get_default_emoji_font(self, assets_dir: str) -> str:
        """Finds a suitable default emoji font file."""
        custom_fonts = [
            os.path.join(assets_dir, "fonts", "NotoEmoji-Regular.ttf"),
            os.path.join(assets_dir, "fonts", "SegoeUIEmoji.ttf"),
        ]
        for custom_font in custom_fonts:
            if os.path.exists(custom_font):
                logger.debug(f"Using custom emoji font: {custom_font}")
                return custom_font
        logger.warning(f"Custom emoji fonts not found in fonts directory.")
        if os.name == 'nt':
            sys_font = 'C:\\Windows\\Fonts\\seguiemj.ttf'
            if os.path.exists(sys_font):
                logger.info(f"Using system fallback emoji font: {sys_font}")
                return sys_font
        else:
            sys_fonts = [
                '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
                '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf',
                '/System/Library/Fonts/Apple Color Emoji.ttc',
            ]
            for sys_font in sys_fonts:
                if os.path.exists(sys_font):
                    logger.info(f"Using system fallback emoji font: {sys_font}")
                    return sys_font
        logger.error("Could not find suitable emoji font. Falling back.")
        return self._get_default_font(assets_dir) # Fallback to regular

    def _ensure_font_exists(self) -> None:
        """Logs confirmation or error for the regular font."""
        try:
            ImageFont.truetype(self.font_path, 10)
            logger.debug(f"Regular font confirmed: {self.font_path}")
        except IOError:
            logger.error(f"Regular font failed: {self.font_path}. Trying Pillow default.")
            try:
                ImageFont.load_default()
                logger.warning("Using Pillow's default font.")
                self.font_path = "PillowDefault" # Mark as fallback
            except Exception as e:
                logger.critical(f"Pillow default font failed: {e}")
                raise FileNotFoundError(f"Font missing: {self.font_path}")
        except Exception as e:
            logger.critical(f"Unexpected font error {self.font_path}: {e}")
            raise

    def _ensure_bold_font_exists(self) -> None:
        """Logs confirmation or error for the bold font."""
        try:
            ImageFont.truetype(self.bold_font_path, 10)
            logger.debug(f"Bold font confirmed: {self.bold_font_path}")
        except IOError:
            logger.warning(f"Bold font failed: {self.bold_font_path}. Using regular.")
            self.bold_font_path = self.font_path
        except Exception as e:
            logger.error(f"Bold font error {self.bold_font_path}: {e}. Using regular.")
            self.bold_font_path = self.font_path

    def _ensure_emoji_font_exists(self) -> None:
        """Logs confirmation or error for the emoji font."""
        try:
            ImageFont.truetype(self.emoji_font_path, 10)
            logger.info(f"Emoji font confirmed: {self.emoji_font_path}")
            self.emoji_font_loaded = True
        except (IOError, OSError) as e:
            logger.warning(f"Emoji font failed: {self.emoji_font_path}. {e}")
            self.emoji_font_loaded = False
            self.emoji_font_path = self.font_path # Use regular as fallback path
        except Exception as e:
            logger.error(f"Emoji font error {self.emoji_font_path}: {e}")
            self.emoji_font_loaded = False
            self.emoji_font_path = self.font_path

    def _cleanup_cache(self):
        """Removes expired items from the logo cache."""
        now = time.time()
        if now - self._last_cache_cleanup > 300: # Cleanup every 5 mins
            expired = [
                k for k, (_, ts) in self._logo_cache.items()
                if now - ts > self._CACHE_EXPIRY
            ]
            for key in expired:
                if key in self._logo_cache:
                    del self._logo_cache[key]
            if expired:
                logger.debug(f"Cleaned {len(expired)} expired cache entries.")
            self._last_cache_cleanup = now

    def _get_sport_category(self, league: str) -> str:
        """Determines the sport category for path construction."""
        # Ensure consistency with load_logos.py SPORT_CATEGORY_MAP
        sport_map = {
            "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
            "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
            "MLB": "BASEBALL", "NHL": "HOCKEY",
            "SOCCER": "SOCCER", "TENNIS": "TENNIS", "UFC/MMA": "MMA"
        }
        return sport_map.get(league.upper(), "OTHER")

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Loads a team logo from the cache or file system."""
        if not team_name or not league:
            logger.warning("Load logo called with empty team or league.")
            return None

        try:
            cache_key = f"team_{league.lower()}_{team_name.lower()}"
            now = time.time()

            # Check cache
            if cache_key in self._logo_cache:
                logo, timestamp = self._logo_cache[cache_key]
                if now - timestamp <= self._CACHE_EXPIRY:
                    logger.debug(f"Cache hit for logo: {cache_key}")
                    return logo.copy() # Return a copy
                else:
                    del self._logo_cache[cache_key] # Expired

            # Construct path based on user's specified structure
            league_dir_name = league.lower()
            normalized_team_name = team_name.lower().replace(' ', '_')
            logo_filename = f"{normalized_team_name}.png"
            # Path: static/logos/teams/{league_lower}/{team_lower_underscore}.png
            logo_path = os.path.join(
                self.league_team_base_dir, league_dir_name, logo_filename
            )
            abs_logo_path = os.path.abspath(logo_path)
            logger.debug(f"Attempting to load logo: {abs_logo_path}")

            if os.path.exists(abs_logo_path):
                try:
                    logo = Image.open(abs_logo_path).convert("RGBA")
                    # Cache management
                    self._cleanup_cache()
                    if len(self._logo_cache) >= self._MAX_CACHE_SIZE:
                        try:
                            oldest_key = next(iter(self._logo_cache))
                            del self._logo_cache[oldest_key]
                            logger.debug(f"Cache full. Evicted: {oldest_key}")
                        except StopIteration: pass # Cache empty
                    self._logo_cache[cache_key] = (logo, now)
                    logger.debug(f"Loaded and cached logo: {cache_key}")
                    return logo.copy()
                except Exception as img_err:
                    logger.error(f"Error opening logo file {abs_logo_path}: {img_err}")
                    return None
            else:
                logger.warning(f"Logo not found: {abs_logo_path}")
                return None
        except Exception as e:
            logger.exception(f"Error loading logo {team_name}/{league}: {e}")
            return None

    def _load_font(
        self, size: int, is_bold: bool = False
    ) -> ImageFont.FreeTypeFont:
        """Loads a font from cache or file, handling fallbacks."""
        font_type = 'bold' if is_bold else 'regular'
        cache_key = f"font_{font_type}_{size}"
        if cache_key not in self._font_cache:
            try:
                path = self.bold_font_path if is_bold else self.font_path
                if path == "PillowDefault":
                    font = ImageFont.load_default()
                    logger.warning(f"Using Pillow default font: {font_type} {size}")
                else:
                    font = ImageFont.truetype(path, size, encoding="unic")
                self._font_cache[cache_key] = font
            except Exception as e:
                logger.error(f"Failed loading font {path} ({size}): {e}. Using default.")
                self._font_cache[cache_key] = ImageFont.load_default()
        return self._font_cache[cache_key]

    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Loads the lock icon from static/lock_icon.png."""
        if self._lock_icon_cache is None:
            try:
                # Path corrected to look directly in static dir
                lock_path = os.path.join(self.assets_dir, "lock_icon.png")
                abs_lock_path = os.path.abspath(lock_path)
                logger.debug(f"Attempting lock icon load: {abs_lock_path}")
                if os.path.exists(abs_lock_path):
                    img = Image.open(abs_lock_path).convert("RGBA")
                    # Resize consistently
                    self._lock_icon_cache = img.resize(
                        (20, 20), Image.Resampling.LANCZOS
                    )
                    logger.info(f"Loaded lock icon: {abs_lock_path}")
                else:
                    logger.warning(f"Lock icon not found: {abs_lock_path}")
                    return None
            except Exception as e:
                logger.error(f"Error loading lock icon: {e}")
                return None
        # Return a copy if loaded
        return self._lock_icon_cache.copy() if self._lock_icon_cache else None

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
        is_same_game: bool = False,
    ) -> Image.Image:
        """
        Generates the bet slip image.

        Args:
            home_team: Name of the home team.
            away_team: Name of the away team.
            league: League name (e.g., NHL, NBA).
            line: Betting line description (e.g., ML, -7.5).
            odds: American odds for the bet.
            units: Units wagered.
            bet_id: Unique identifier for the bet.
            timestamp: Time the bet was placed.
            bet_type: 'straight' or 'parlay'.
            parlay_legs: List of leg dictionaries for parlays.
            is_same_game: Flag for same-game parlays.

        Returns:
            A PIL Image object representing the bet slip.
        """
        try:
            # --- Dimensions and Setup ---
            width = 800
            base_height = 450
            leg_height_with_logos = 220
            leg_height_no_logos = 100
            details_height = 150
            footer_height = 50
            header_height = 80
            separator_height = 20
            totals_height = 80

            # Calculate height dynamically
            height = header_height
            if bet_type == "straight":
                height += 150 + details_height # Logo section + details
                height += footer_height
                height = max(base_height, height)
            elif bet_type == "parlay" and parlay_legs:
                num_legs = len(parlay_legs)
                first_leg_draw_logos = is_same_game
                for i in range(num_legs):
                    if i > 0:
                        height += separator_height
                    height += leg_height_with_logos if (i == 0 and first_leg_draw_logos) else leg_height_no_logos
                height += separator_height + totals_height + footer_height
                height = max(base_height, height)
            else:
                height = base_height

            image = Image.new('RGB', (width, height), (40, 40, 40))
            draw = ImageDraw.Draw(image)

            # --- Fonts ---
            # Load fonts safely using the helper method
            header_font = self._load_font(32, is_bold=True)
            team_font = self._load_font(28)
            details_font = self._load_font(24)
            odds_font = self._load_font(28, is_bold=True)
            units_font = self._load_font(24)
            small_font = self._load_font(18)
            # Load emoji font instance only if flag is true
            emoji_font_instance = None
            if self.emoji_font_loaded:
                try:
                    emoji_font_instance = ImageFont.truetype(
                        self.emoji_font_path, 24
                    )
                except Exception as e:
                    logger.error(f"Failed emoji font instance: {e}")
                    self.emoji_font_loaded = False
            fallback_font = emoji_font_instance if self.emoji_font_loaded else details_font

            # --- Header ---
            header_y = 40
            # Use specific title for Multi-Team Parlay based on your preference
            if bet_type == "parlay" and not is_same_game:
                header_text_type = "Multi-Team Parlay Bet"
            elif bet_type == "parlay" and is_same_game:
                header_text_type = "Same-Game Parlay"
            else:
                header_text_type = "Straight Bet"
            header_text = f"{league} - {header_text_type}" if league else header_text_type
            draw.text(
                (width // 2, header_y), header_text, fill='white',
                font=header_font, anchor='mm'
            )
            current_y = header_y + 60

            # --- Draw Content (Straight or Parlay) ---
            lock_icon = self._load_lock_icon() # Load lock icon once

            if bet_type == "straight":
                current_y = self._draw_straight_bet_details(
                    image, draw, home_team, away_team, league, line, odds, units,
                    current_y, width, lock_icon, team_font, details_font,
                    odds_font, units_font, fallback_font
                )
            elif bet_type == "parlay" and parlay_legs:
                current_y = self._draw_parlay_details(
                    image, draw, parlay_legs, league, odds, units, width,
                    current_y, is_same_game, lock_icon, team_font,
                    details_font, odds_font, units_font, fallback_font
                )

            # --- Footer ---
            footer_y = height - 30
            draw.text(
                (20, footer_y), f"Bet #{bet_id}", fill=(150, 150, 150),
                font=small_font, anchor='lm'
            )
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC')
            draw.text(
                (width - 20, footer_y), timestamp_text, fill=(150, 150, 150),
                font=small_font, anchor='rm'
            )

            return image
        except Exception as e:
            logger.exception(f"Error generating bet slip: {str(e)}")
            # Create a fallback error image
            error_img = Image.new('RGB', (800, 100), (40, 40, 40))
            error_draw = ImageDraw.Draw(error_img)
            try:
                # Use a font known to exist or Pillow's default
                error_font = self._load_font(20)
            except Exception:
                 error_font = ImageFont.load_default()
            error_draw.text(
                (10, 10), "Error generating bet slip image. Check logs.",
                fill='red', font=error_font
            )
            return error_img

    def _draw_straight_bet_details(
        self, image, draw, home_team, away_team, league, line, odds, units,
        current_y, width, lock_icon, team_font, details_font, odds_font,
        units_font, fallback_font
    ) -> int:
        """Draws the specific details for a straight bet."""
        logo_size = (100, 100)
        current_league = league or 'NHL' # Use default if None
        home_logo = self._load_team_logo(home_team, current_league)
        away_logo = self._load_team_logo(away_team, current_league)
        home_x = width // 4
        away_x = 3 * width // 4

        # Draw logos and names
        if home_logo:
            image.paste(
                home_logo, (home_x - logo_size[0] // 2, current_y), home_logo
            )
        draw.text(
            (home_x, current_y + logo_size[1] + 15), home_team,
            fill='white', font=team_font, anchor='mm'
        )
        if away_logo:
            image.paste(
                away_logo, (away_x - logo_size[0] // 2, current_y), away_logo
            )
        draw.text(
            (away_x, current_y + logo_size[1] + 15), away_team,
            fill='white', font=team_font, anchor='mm'
        )
        current_y += logo_size[1] + 40

        # Draw bet line, separator, odds
        bet_text = f"{home_team}: {line}"
        draw.text(
            (width // 2, current_y), bet_text, fill='white',
            font=details_font, anchor='mm'
        )
        current_y += 40
        draw.line(
            [(40, current_y), (width - 40, current_y)],
            fill=(80, 80, 80), width=2
        )
        current_y += 30
        odds_text = f"{odds:+.0f}" if odds is not None else "N/A"
        draw.text(
            (width // 2, current_y), odds_text, fill='white',
            font=odds_font, anchor='mm'
        )
        current_y += 40

        # Draw units with lock/fallback
        units_text = f"To Win {units:.2f} Units"
        self._draw_units_section(
            draw, image, units_text, current_y, width, lock_icon,
            units_font, fallback_font, details_font
        )
        current_y += 40
        return current_y

    def _draw_parlay_details(
        self, image, draw, parlay_legs, league, odds, units, width,
        current_y, is_same_game, lock_icon, team_font, details_font,
        odds_font, units_font, fallback_font
    ) -> int:
        """Draws the specific details for a parlay bet."""
        draw_first_leg_logos = is_same_game
        for i, leg in enumerate(parlay_legs):
            if i > 0:
                draw.line(
                    [(40, current_y - 10), (width - 40, current_y - 10)],
                    fill=(80, 80, 80), width=1
                )
                current_y += 10
            current_y = self._draw_leg(
                image=image, draw=draw, leg=leg,
                league=leg.get('league', league or 'NHL'), # Use leg league or default
                width=width, start_y=current_y,
                team_font=team_font, details_font=details_font,
                odds_font=odds_font, emoji_font=fallback_font, # Pass correct fallback
                draw_logos=(i == 0 and draw_first_leg_logos)
            )
            current_y += 10 # Padding after leg

        # Separator before totals
        current_y += 10
        draw.line(
            [(20, current_y), (width - 20, current_y)], fill='white', width=2
        )
        current_y += 30

        # Total odds and units
        total_odds_display = odds
        total_units_display = sum(
            float(leg.get('units', 0)) for leg in parlay_legs
        ) if all('units' in leg for leg in parlay_legs) else units

        odds_text = (
            f"Total Odds: {total_odds_display:+.0f}"
            if total_odds_display is not None else "Total Odds: N/A"
        )
        draw.text(
            (width // 2, current_y), odds_text, fill='white',
            font=odds_font, anchor='mm'
        )
        current_y += 40

        units_text = f"Total Units: {total_units_display:.2f}"
        self._draw_units_section(
            draw, image, units_text, current_y, width, lock_icon,
            units_font, fallback_font, details_font
        )
        current_y += 40
        return current_y

    def _draw_units_section(
        self, draw, image, units_text, current_y, width, lock_icon,
        units_font, emoji_fallback_font, details_font
    ):
        """Helper to draw the units text with lock icon or fallbacks."""
        try:
            # Use textbbox if available for better width calculation
            units_bbox = draw.textbbox((0, 0), units_text, font=units_font)
            units_width = units_bbox[2] - units_bbox[0]
        except AttributeError:
            # Fallback for older Pillow versions
            units_width, _ = draw.textsize(units_text, font=units_font)

        if lock_icon:
            lock_spacing = 10
            try:
                # Attempt to get font metrics for vertical alignment
                text_ascent, text_descent = units_font.getmetrics()
                text_height = text_ascent + text_descent
            except AttributeError:
                text_height = 20 # Estimate if getmetrics not available
            lock_y_offset = (text_height - lock_icon.height) // 2
            base_lock_y = current_y - (text_height // 2) # Center text line first

            lock_x_left = (
                (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
            )
            image.paste(
                lock_icon, (lock_x_left, base_lock_y + lock_y_offset), lock_icon
            )
            text_x = lock_x_left + lock_icon.width + lock_spacing
            draw.text(
                (text_x, current_y), units_text, fill=(255, 215, 0),
                font=units_font, anchor='lm'
            ) # Gold color, left-middle anchor
            lock_x_right = text_x + units_width + lock_spacing
            image.paste(
                lock_icon, (lock_x_right, base_lock_y + lock_y_offset), lock_icon
            )
        elif self.emoji_font_loaded:
            # Use emoji only if the specific emoji font was loaded
            draw.text(
                (width // 2, current_y), f"🔒 {units_text} 🔒",
                fill=(255, 215, 0), font=emoji_fallback_font, anchor='mm'
            )
        else:
            # Final fallback if no icon file and no specific emoji font
            draw.text(
                (width // 2, current_y), f"[L] {units_text} [L]",
                fill=(255, 215, 0), font=details_font, anchor='mm'
            )

    # --- Method to draw a single parlay leg ---
    def _draw_leg(
        self, image: Image.Image, draw: ImageDraw.Draw, leg: Dict[str, Any],
        league: str, width: int, start_y: int, team_font: ImageFont.FreeTypeFont,
        details_font: ImageFont.FreeTypeFont, odds_font: ImageFont.FreeTypeFont,
        emoji_font: ImageFont.FreeTypeFont, draw_logos: bool = True
    ) -> int:
        """Draws a single leg of a parlay bet."""
        home_team = leg.get('home_team', leg.get('team', 'Unknown'))
        away_team = leg.get('away_team', leg.get('opponent', 'Unknown'))
        line = leg.get('line', 'ML')
        current_y = start_y
        logo_size = (80, 80)

        if draw_logos:
            home_logo = self._load_team_logo(home_team, league)
            away_logo = self._load_team_logo(away_team, league)
            logo_y_pad = 15
            home_x = width * 0.3
            away_x = width * 0.7
            if home_logo:
                image.paste(
                    home_logo,
                    (int(home_x - logo_size[0] // 2), current_y + logo_y_pad),
                    home_logo
                )
            if away_logo:
                image.paste(
                    away_logo,
                    (int(away_x - logo_size[0] // 2), current_y + logo_y_pad),
                    away_logo
                )
            team_y = current_y + logo_size[1] + logo_y_pad + 15
            draw.text(
                (home_x, team_y), home_team, fill='white',
                font=team_font, anchor='mm'
            )
            draw.text(
                (away_x, team_y), away_team, fill='white',
                font=team_font, anchor='mm'
            )
            current_y = team_y + 40
        else:
            current_y += 20 # Space if no logos

        # Bet Details (Line)
        details_y = current_y
        line_text = f"{home_team} vs {away_team}: {line}"
        max_line_width = width - 80 # Padding
        try:
            line_bbox = draw.textbbox((0, 0), line_text, font=details_font)
            line_width = line_bbox[2] - line_bbox[0]
        except AttributeError:
            line_width, _ = draw.textsize(line_text, font=details_font)

        if line_width > max_line_width:
            # Truncate text if it's too long
            ratio = max_line_width / line_width if line_width > 0 else 1
            cutoff = int(len(line_text) * ratio) - 3
            line_text = line_text[:max(10, cutoff)] + "..." # Show at least some

        draw.text(
            (width // 2, details_y), line_text, fill='white',
            font=details_font, anchor='mm'
        )
        current_y = details_y + 35 # Space after line

        # Individual leg odds are usually omitted visually in parlays
        # Add back here if desired, using odds_font

        return current_y

    # --- _calculate_parlay_odds ---
    def _calculate_parlay_odds(self, legs: List[Dict[str, Any]]) -> float:
        """Calculates parlay odds from individual American leg odds."""
        # Note: Real bookmaker parlay odds might differ slightly.
        try:
            total_decimal = 1.0
            for leg in legs:
                odds = float(leg.get('odds', 0))
                if odds == 0: continue
                if odds > 0:
                    decimal = (odds / 100) + 1
                else:
                    decimal = (100 / abs(odds)) + 1
                total_decimal *= decimal

            if total_decimal <= 1.0: return 0.0 # Error or no valid legs
            if total_decimal >= 2.0:
                american_odds = (total_decimal - 1) * 100
            else:
                american_odds = -100 / (total_decimal - 1)
            return american_odds
        except Exception as e:
            logger.error(f"Error calculating parlay odds: {e}")
            return 0.0

    def save_bet_slip(self, image: Image.Image, output_path: str) -> None:
        """Saves the generated image to a file."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path, "PNG", optimize=True)
            logger.info(f"Bet slip saved: {output_path}")
        except Exception as e:
            logger.error(f"Error saving bet slip to {output_path}: {e}")
            raise
