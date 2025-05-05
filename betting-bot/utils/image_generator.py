# betting-bot/utils/image_generator.py
# PEP 8 Compliant

"""Generates bet slip images using PIL."""

import logging
import os
import time
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

# Attempt to import league dictionaries - handle potential errors
try:
    from .league_dictionaries import (
        nhl, nfl, nba, mlb, ncaaf, ncaab, soccer
    )
    # Combine relevant dictionaries for easy lookup
    LEAGUE_NAME_LOOKUP = {
        'NHL': nhl.TEAM_FULL_NAMES,
        'NFL': nfl.TEAM_FULL_NAMES,
        'NBA': nba.TEAM_FULL_NAMES,
        'MLB': mlb.TEAM_FULL_NAMES,
        'NCAAF': ncaaf.TEAM_FULL_NAMES,
        'NCAAB': ncaab.TEAM_FULL_NAMES,
        'SOCCER': soccer.TEAM_FULL_NAMES, # Assuming 'SOCCER' is the key used
        # Add other leagues here as needed
    }
    logger.info("Successfully imported league dictionaries.")
except ImportError:
    logger.warning(
        "Could not import league dictionaries. "
        "Team name normalization for logos will be basic."
    )
    LEAGUE_NAME_LOOKUP = {}
except AttributeError as e:
    logger.warning(
        f"Attribute error importing league dictionaries "
        f"(likely missing TEAM_FULL_NAMES): {e}. "
        "Team name normalization will be basic."
    )
    LEAGUE_NAME_LOOKUP = {}


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

    _MAX_CACHE_SIZE = 100
    _CACHE_EXPIRY = 3600

    def __init__(
        self,
        font_path: Optional[str] = None,
        emoji_font_path: Optional[str] = None,
    ):
        """Initializes the BetSlipGenerator."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.assets_dir = os.path.join(project_root, 'static')
        logger.info(f"Assets directory set to: {self.assets_dir}")

        self.font_path = font_path or self._get_default_font(self.assets_dir)
        self.bold_font_path = self._get_default_bold_font(self.assets_dir)
        self.emoji_font_path = emoji_font_path or self._get_default_emoji_font(
            self.assets_dir
        )
        self.emoji_font_loaded = False

        self.logos_base_dir = os.path.join(self.assets_dir, "logos")
        self.league_team_base_dir = os.path.join(self.logos_base_dir, "teams")
        self.league_logo_base_dir = os.path.join(self.logos_base_dir, "leagues")

        self._ensure_base_dirs_exist()
        self._ensure_font_exists()
        self._ensure_bold_font_exists()
        self._ensure_emoji_font_exists()

        self._logo_cache: Dict[str, tuple[Image.Image, float]] = {}
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self._lock_icon_cache: Optional[Image.Image] = None
        self._last_cache_cleanup: float = time.time()

    # --- Directory and Font Helper Methods ---
    def _ensure_base_dirs_exist(self):
        """Ensure base directories for static assets and logos exist."""
        dirs_to_create = [
            self.assets_dir, self.logos_base_dir,
            self.league_team_base_dir, self.league_logo_base_dir,
        ]
        for directory in dirs_to_create:
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as e:
                logger.error(f"Could not create directory {directory}: {e}")
        logger.debug(f"Ensured base directories exist: {self.assets_dir}")

    def _get_default_font(self, assets_dir: str) -> str:
        """Finds a suitable default regular font file."""
        custom = os.path.join(assets_dir, "fonts", "Roboto-Regular.ttf")
        if os.path.exists(custom): return custom
        logger.warning(f"Custom font not found: {custom}.")
        if os.name == 'nt': sys_f = 'C:\\Windows\\Fonts\\arial.ttf'
        else: sys_f = next((f for f in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf'] if os.path.exists(f)), None)
        if sys_f and os.path.exists(sys_f): logger.info(f"Using system font: {sys_f}"); return sys_f
        logger.error("No default regular font found."); return "arial.ttf"

    def _get_default_bold_font(self, assets_dir: str) -> str:
        """Finds a suitable default bold font file."""
        custom = os.path.join(assets_dir, "fonts", "Roboto-Bold.ttf")
        if os.path.exists(custom): return custom
        logger.warning(f"Custom bold font not found: {custom}.")
        reg = self._get_default_font(assets_dir)
        if "arial.ttf" in reg.lower() and os.name == 'nt':
             bold_fb = 'C:\\Windows\\Fonts\\arialbd.ttf'
             if os.path.exists(bold_fb): return bold_fb
        logger.warning("Falling back to regular font for bold."); return reg

    def _get_default_emoji_font(self, assets_dir: str) -> str:
        """Finds a suitable default emoji font file."""
        customs = [os.path.join(assets_dir, "fonts", f) for f in ["NotoEmoji-Regular.ttf", "SegoeUIEmoji.ttf"]]
        for custom in customs:
            if os.path.exists(custom): return custom
        logger.warning("Custom emoji fonts not found.")
        if os.name == 'nt': sys_f = 'C:\\Windows\\Fonts\\seguiemj.ttf'
        else: sys_f = next((f for f in ['/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf', '/System/Library/Fonts/Apple Color Emoji.ttc'] if os.path.exists(f)), None)
        if sys_f and os.path.exists(sys_f): logger.info(f"Using system emoji font: {sys_f}"); return sys_f
        logger.error("No default emoji font found. Falling back."); return self._get_default_font(assets_dir)

    def _ensure_font_exists(self) -> None:
        """Logs confirmation or error for the regular font."""
        try: ImageFont.truetype(self.font_path, 10); logger.debug(f"Regular font confirmed: {self.font_path}")
        except IOError:
            logger.error(f"Font file failed: {self.font_path}. Trying Pillow default.")
            try: ImageFont.load_default(); logger.warning("Using Pillow default font."); self.font_path = "PillowDefault"
            except Exception as e: logger.critical(f"Pillow font failed: {e}"); raise FileNotFoundError(f"Font missing: {self.font_path}")
        except Exception as e: logger.critical(f"Font error {self.font_path}: {e}"); raise

    def _ensure_bold_font_exists(self) -> None:
        """Logs confirmation or error for the bold font."""
        try: ImageFont.truetype(self.bold_font_path, 10); logger.debug(f"Bold font confirmed: {self.bold_font_path}")
        except IOError: logger.warning(f"Bold font failed: {self.bold_font_path}. Using regular."); self.bold_font_path = self.font_path
        except Exception as e: logger.error(f"Bold font error {self.bold_font_path}: {e}. Using regular."); self.bold_font_path = self.font_path

    def _ensure_emoji_font_exists(self) -> None:
        """Logs confirmation or error for the emoji font."""
        try: ImageFont.truetype(self.emoji_font_path, 10); logger.info(f"Emoji font confirmed: {self.emoji_font_path}"); self.emoji_font_loaded = True
        except (IOError, OSError) as e: logger.warning(f"Emoji font failed: {self.emoji_font_path}. {e}"); self.emoji_font_loaded = False; self.emoji_font_path = self.font_path
        except Exception as e: logger.error(f"Emoji font error {self.emoji_font_path}: {e}"); self.emoji_font_loaded = False; self.emoji_font_path = self.font_path

    def _cleanup_cache(self):
        """Removes expired items from the logo cache."""
        now = time.time()
        if now - self._last_cache_cleanup > 300:
            expired = [k for k, (_, ts) in self._logo_cache.items() if now - ts > self._CACHE_EXPIRY]
            for key in expired:
                if key in self._logo_cache: del self._logo_cache[key]
            if expired: logger.debug(f"Cleaned {len(expired)} cache entries.")
            self._last_cache_cleanup = now

    def _get_sport_category(self, league_name: str) -> str:
        """Determines the sport category for path construction."""
        sport_map = {
            "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
            "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
            "MLB": "BASEBALL", "NHL": "HOCKEY",
            "SOCCER": "SOCCER", "TENNIS": "TENNIS", "UFC/MMA": "MMA",
        }
        return sport_map.get(league_name.upper(), "OTHER")

    def _get_canonical_team_name(self, team_input: str, league: str) -> str:
        """
        Uses league dictionaries to find the full, canonical team name.

        Args:
            team_input: The potentially abbreviated team name.
            league: The league identifier (e.g., NHL, NBA).

        Returns:
            The canonical full team name or the original input if not found.
        """
        league_upper = league.upper()
        if not LEAGUE_NAME_LOOKUP or league_upper not in LEAGUE_NAME_LOOKUP:
            logger.warning(f"No dictionary lookup found for league: {league_upper}")
            return team_input # Return original input if no dictionary

        lookup_dict = LEAGUE_NAME_LOOKUP[league_upper]
        # Check lowercase input against dictionary keys
        canonical_name = lookup_dict.get(team_input.lower())

        if canonical_name:
            logger.debug(f"Normalized '{team_input}' to '{canonical_name}' for league {league_upper}")
            return canonical_name
        else:
            logger.warning(f"Could not find canonical name for '{team_input}' in league {league_upper}. Using input.")
            return team_input # Return original input if not found

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """
        Loads a team logo using the definitive path and dictionary lookup:
        static/logos/teams/{SPORT_CATEGORY}/{LEAGUE_UPPERCASE}/{full_team_name_lower_underscore}.png
        """
        if not team_name or not league:
            logger.warning("Load logo: Empty team or league name.")
            return None

        try:
            # --- Get Full Name using Dictionary ---
            full_team_name = self._get_canonical_team_name(team_name, league)
            # --- End Dictionary Lookup ---

            cache_key = f"team_{league.lower()}_{full_team_name.lower()}" # Use full name for cache
            now = time.time()

            if cache_key in self._logo_cache:
                logo, timestamp = self._logo_cache[cache_key]
                if now - timestamp <= self._CACHE_EXPIRY:
                    logger.debug(f"Cache hit: {cache_key}")
                    return logo.copy()
                else: del self._logo_cache[cache_key]

            # --- Path Construction using definitive structure ---
            sport_category = self._get_sport_category(league)
            league_dir_name = league.upper() # Uppercase league directory
            # Normalize the *full name* for the filename
            normalized_filename_base = full_team_name.lower().replace(' ', '_')
            logo_filename = f"{normalized_filename_base}.png"

            logo_path = os.path.join(
                self.league_team_base_dir, sport_category, league_dir_name, logo_filename
            )
            # --- End Path Construction ---

            abs_logo_path = os.path.abspath(logo_path)
            logger.debug(f"Attempting logo load: {abs_logo_path}")

            if os.path.exists(abs_logo_path):
                try:
                    logo = Image.open(abs_logo_path).convert("RGBA")
                    self._cleanup_cache()
                    if len(self._logo_cache) >= self._MAX_CACHE_SIZE:
                        try: oldest_key = next(iter(self._logo_cache)); del self._logo_cache[oldest_key]; logger.debug(f"Cache evicted: {oldest_key}")
                        except StopIteration: pass
                    self._logo_cache[cache_key] = (logo, now)
                    logger.debug(f"Loaded/cached logo: {cache_key}")
                    return logo.copy()
                except Exception as img_err: logger.error(f"Error opening {abs_logo_path}: {img_err}"); return None
            else: logger.warning(f"Logo not found: {abs_logo_path}"); return None
        except Exception as e: logger.exception(f"Error loading logo {team_name}/{league}: {e}"); return None

    def _load_font(
        self, size: int, is_bold: bool = False
    ) -> ImageFont.FreeTypeFont:
        """Loads a font from cache or file, handling fallbacks."""
        font_type = 'bold' if is_bold else 'regular'
        cache_key = f"font_{font_type}_{size}"
        if cache_key not in self._font_cache:
            try:
                path = self.bold_font_path if is_bold else self.font_path
                if path == "PillowDefault": font = ImageFont.load_default(); logger.warning(f"Using Pillow default: {font_type} {size}")
                else: font = ImageFont.truetype(path, size, encoding="unic")
                self._font_cache[cache_key] = font
            except Exception as e: logger.error(f"Font load failed {path} ({size}): {e}. Using default."); self._font_cache[cache_key] = ImageFont.load_default()
        return self._font_cache[cache_key]

    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Loads the lock icon from static/lock_icon.png."""
        if self._lock_icon_cache is None:
            try:
                lock_path = os.path.join(self.assets_dir, "lock_icon.png")
                abs_path = os.path.abspath(lock_path)
                logger.debug(f"Attempting lock icon load: {abs_path}")
                if os.path.exists(abs_path):
                    img = Image.open(abs_path).convert("RGBA")
                    self._lock_icon_cache = img.resize((20, 20), Image.Resampling.LANCZOS)
                    logger.info(f"Loaded lock icon: {abs_path}")
                else: logger.warning(f"Lock icon NOT FOUND: {abs_path}"); return None
            except Exception as e: logger.error(f"Error loading lock icon: {e}"); return None
        return self._lock_icon_cache.copy() if self._lock_icon_cache else None

    # --- Main Generation Method ---
    def generate_bet_slip(
        self, home_team: str, away_team: str, league: Optional[str], line: str,
        odds: float, units: float, bet_id: str, timestamp: datetime,
        bet_type: str = "straight", parlay_legs: Optional[List[Dict[str, Any]]] = None,
        is_same_game: bool = False,
    ) -> Image.Image:
        """Generates the bet slip image."""
        try:
            # --- Dimensions ---
            width=800; base_h=450; leg_h_logos=220; leg_h_no_logos=100
            details_h=150; footer_h=50; header_h=80; sep_h=20; totals_h=80
            height=header_h
            if bet_type == "straight": height += 150 + details_h + footer_h; height = max(base_h, height)
            elif bet_type == "parlay" and parlay_legs:
                num_legs = len(parlay_legs); first_leg_logos = is_same_game
                for i in range(num_legs):
                    if i > 0: height += sep_h
                    height += leg_h_logos if (i == 0 and first_leg_logos) else leg_h_no_logos
                height += sep_h + totals_h + footer_h; height = max(base_h, height)
            else: height = base_h
            image = Image.new('RGB', (width, height), (40, 40, 40)); draw = ImageDraw.Draw(image)

            # --- Fonts ---
            try:
                hdr_f=self._load_font(32,True); team_f=self._load_font(28); det_f=self._load_font(24)
                odds_f=self._load_font(28,True); units_f=self._load_font(24); small_f=self._load_font(18)
                emoji_f_inst = ImageFont.truetype(self.emoji_font_path, 24) if self.emoji_font_loaded else None
            except Exception as e: logger.error(f"Font load failed: {e}. Using Pillow default."); hdr_f=team_f=det_f=odds_f=units_f=small_f=emoji_f_inst = ImageFont.load_default()
            fallback_font = emoji_f_inst if self.emoji_font_loaded else det_f # Use details if emoji fails

            # --- Header ---
            hdr_y = 40
            if bet_type == "parlay" and not is_same_game: bt_type_txt = "Multi-Team Parlay Bet"
            elif bet_type == "parlay" and is_same_game: bt_type_txt = "Same-Game Parlay"
            else: bt_type_txt = "Straight Bet"
            hdr_txt = f"{league} - {bt_type_txt}" if league else bt_type_txt
            draw.text((width//2, hdr_y), hdr_txt, fill='white', font=hdr_f, anchor='mm')
            curr_y = hdr_y + 60

            # --- Draw Content ---
            lock_icon = self._load_lock_icon()
            if bet_type == "straight":
                curr_y = self._draw_straight_bet_details(
                    image, draw, home_team, away_team, league, line, odds, units,
                    curr_y, width, lock_icon, team_f, det_f, odds_f, units_f, fallback_font
                )
            elif bet_type == "parlay" and parlay_legs:
                curr_y = self._draw_parlay_details(
                    image, draw, parlay_legs, league, odds, units, width, curr_y,
                    is_same_game, lock_icon, team_f, det_f, odds_f, units_f, fallback_font
                )

            # --- Footer ---
            footer_y = height - 30
            draw.text((20, footer_y), f"Bet #{bet_id}", fill=(150,150,150), font=small_f, anchor='lm')
            ts_utc = timestamp.astimezone(timezone.utc)
            ts_txt = ts_utc.strftime('%Y-%m-%d %H:%M UTC')
            draw.text((width-20, footer_y), ts_txt, fill=(150,150,150), font=small_f, anchor='rm')

            return image
        except Exception as e:
            logger.exception(f"Error generating bet slip: {e}")
            err_img = Image.new('RGB', (800, 100), (40, 40, 40)); err_draw = ImageDraw.Draw(err_img)
            try: err_font = self._load_font(20)
            except Exception: err_font = ImageFont.load_default()
            err_draw.text((10, 10), "Error generating slip. Check logs.", fill='red', font=err_font)
            return err_img

    # --- Drawing Helper Methods ---
    def _draw_straight_bet_details(
        self, image, draw, home_team, away_team, league, line, odds, units,
        current_y, width, lock_icon, team_font, details_font, odds_font,
        units_font, fallback_font
    ) -> int:
        """Draws the specific details for a straight bet."""
        logo_size=(100, 100); current_league=league or 'NHL'
        home_logo=self._load_team_logo(home_team, current_league); away_logo=self._load_team_logo(away_team, current_league)
        home_x=width//4; away_x=3*width//4
        if home_logo: image.paste(home_logo,(home_x - logo_size[0]//2, current_y), home_logo)
        draw.text((home_x, current_y + logo_size[1] + 15), home_team, fill='white', font=team_font, anchor='mm')
        if away_logo: image.paste(away_logo,(away_x - logo_size[0]//2, current_y), away_logo)
        draw.text((away_x, current_y + logo_size[1] + 15), away_team, fill='white', font=team_font, anchor='mm')
        current_y += logo_size[1] + 40
        bet_text = f"{self._get_canonical_team_name(home_team, current_league)}: {line}" # Use full name
        draw.text((width // 2, current_y), bet_text, fill='white', font=details_font, anchor='mm'); current_y += 40
        draw.line([(40, current_y), (width - 40, current_y)], fill=(80, 80, 80), width=2); current_y += 30
        odds_text = f"{odds:+.0f}" if odds is not None else "N/A"; draw.text((width // 2, current_y), odds_text, fill='white', font=odds_font, anchor='mm'); current_y += 40
        units_text=f"To Win {units:.2f} Units"
        self._draw_units_section(draw, image, units_text, current_y, width, lock_icon, units_font, fallback_font, details_font)
        current_y += 40
        return current_y

    def _draw_parlay_details(
        self, image, draw, parlay_legs, league, odds, units, width,
        current_y, is_same_game, lock_icon, team_font, details_font,
        odds_font, units_font, fallback_font
    ) -> int:
        """Draws the specific details for a parlay bet."""
        draw_first_logos = is_same_game
        for i, leg in enumerate(parlay_legs):
            if i > 0: draw.line([(40, current_y - 10), (width - 40, current_y - 10)], fill=(80,80,80), width=1); current_y += 10
            current_y = self._draw_leg(image, draw, leg, leg.get('league', league or 'NHL'), width, current_y, team_font, details_font, odds_font, fallback_font, (i == 0 and draw_first_logos)); current_y += 10
        current_y += 10; draw.line([(20, current_y), (width - 20, current_y)], fill='white', width=2); current_y += 30
        total_odds = odds; total_units = sum(float(l.get('units', 0)) for l in parlay_legs) if all('units' in l for l in parlay_legs) else units
        odds_txt = f"Total Odds: {total_odds:+.0f}" if total_odds is not None else "N/A"; draw.text((width//2, current_y), odds_txt, fill='white', font=odds_font, anchor='mm'); current_y += 40
        units_txt = f"Total Units: {total_units:.2f}"
        self._draw_units_section(draw, image, units_txt, current_y, width, lock_icon, units_font, fallback_font, details_font)
        current_y += 40
        return current_y

    def _draw_units_section(
        self, draw, image, units_text, current_y, width, lock_icon,
        units_font, emoji_fallback_font, details_font
    ):
        """Helper to draw the units text with lock icon or fallbacks."""
        try: units_bbox=draw.textbbox((0,0), units_text, font=units_font); units_width=units_bbox[2]-units_bbox[0]
        except AttributeError: units_width,_=draw.textsize(units_text, font=units_font)

        if lock_icon:
            lock_space=10; txt_h=units_font.getmetrics()[0] if hasattr(units_font,'getmetrics') else 20; lock_y_off=(txt_h-lock_icon.height)//2; base_y=current_y-(txt_h//2)
            lock_x_l=(width-units_width-2*lock_icon.width-2*lock_space)//2; image.paste(lock_icon,(lock_x_l,base_y+lock_y_off),lock_icon)
            txt_x=lock_x_l+lock_icon.width+lock_space; draw.text((txt_x,current_y),units_text,fill=(255,215,0),font=units_font,anchor='lm')
            lock_x_r=txt_x+units_width+lock_space; image.paste(lock_icon,(lock_x_r,base_y+lock_y_off),lock_icon)
        elif self.emoji_font_loaded: draw.text((width//2,current_y), f"🔒 {units_text} 🔒", fill=(255,215,0), font=emoji_fallback_font, anchor='mm')
        else: draw.text((width//2,current_y), f"[L] {units_text} [L]", fill=(255,215,0), font=details_font, anchor='mm')

    def _draw_leg(
        self, image: Image.Image, draw: ImageDraw.Draw, leg: Dict[str, Any],
        league: str, width: int, start_y: int, team_font: ImageFont.FreeTypeFont,
        details_font: ImageFont.FreeTypeFont, odds_font: ImageFont.FreeTypeFont,
        emoji_font: ImageFont.FreeTypeFont, draw_logos: bool = True
    ) -> int:
        """Draws a single leg of a parlay bet."""
        # Use dictionary lookup for full names
        home_team_full = self._get_canonical_team_name(leg.get('home_team', leg.get('team', 'Unknown')), league)
        away_team_full = self._get_canonical_team_name(leg.get('away_team', leg.get('opponent', 'Unknown')), league)
        line=leg.get('line','ML'); current_y = start_y; logo_size=(80, 80)

        if draw_logos:
            # Load logos using the potentially partial names passed in leg dict
            home_logo = self._load_team_logo(leg.get('home_team', leg.get('team', '')), league)
            away_logo = self._load_team_logo(leg.get('away_team', leg.get('opponent', '')), league)
            logo_y_pad=15; home_x=width*0.3; away_x=width*0.7
            if home_logo: image.paste(home_logo,(int(home_x-logo_size[0]//2),current_y+logo_y_pad),home_logo)
            if away_logo: image.paste(away_logo,(int(away_x-logo_size[0]//2),current_y+logo_y_pad),away_logo)
            team_y=current_y+logo_size[1]+logo_y_pad+15
            # Display full names
            draw.text((home_x,team_y),home_team_full,fill='white',font=team_font,anchor='mm')
            draw.text((away_x,team_y),away_team_full,fill='white',font=team_font,anchor='mm'); current_y = team_y + 40
        else: current_y += 20

        details_y = current_y;
        # Use full names in line text
        line_text = f"{home_team_full} vs {away_team_full}: {line}"; max_line_width = width - 80
        try: line_bbox=draw.textbbox((0,0),line_text,font=details_font); line_width=line_bbox[2]-line_bbox[0]
        except AttributeError: line_width,_=draw.textsize(line_text,font=details_font)
        if line_width > max_line_width: approx_chars=int(len(line_text)*(max_line_width/line_width))-3; line_text=line_text[:max(10,approx_chars)]+"..."
        draw.text((width//2,details_y),line_text,fill='white',font=details_font,anchor='mm'); current_y = details_y + 35
        return current_y

    # --- _calculate_parlay_odds ---
    def _calculate_parlay_odds(self, legs: List[Dict[str, Any]]) -> float:
        """Calculates parlay odds from individual American leg odds."""
        try:
            total_decimal = 1.0
            for leg in legs:
                odds = float(leg.get('odds', 0));
                if odds == 0: continue
                if odds > 0: decimal = (odds / 100) + 1
                else: decimal = (100 / abs(odds)) + 1
                total_decimal *= decimal
            if total_decimal <= 1.0: return 0.0
            if total_decimal >= 2.0: american_odds = (total_decimal - 1) * 100
            else: american_odds = -100 / (total_decimal - 1)
            return american_odds
        except Exception as e: logger.error(f"Error calculating parlay odds: {e}"); return 0.0

    def save_bet_slip(self, image: Image.Image, output_path: str) -> None:
        """Saves the generated image to a file."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path, "PNG", optimize=True)
            logger.info(f"Bet slip saved: {output_path}")
        except Exception as e: logger.error(f"Error saving slip: {e}"); raise
