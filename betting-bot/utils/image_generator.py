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
        logger.info(f"Assets directory set to: {self.assets_dir}")

        self.font_path = font_path or self._get_default_font(self.assets_dir)
        self.bold_font_path = self._get_default_bold_font(self.assets_dir)
        self.emoji_font_path = emoji_font_path or self._get_default_emoji_font(self.assets_dir)
        self.emoji_font_loaded = False # Flag to track if emoji font loaded successfully

        # Base directory for logos within the static folder
        self.logos_base_dir = os.path.join(self.assets_dir, "logos")
        self.league_team_base_dir = os.path.join(self.logos_base_dir, "teams")
        self.league_logo_base_dir = os.path.join(self.logos_base_dir, "leagues")

        self._ensure_font_exists()
        self._ensure_bold_font_exists()
        self._ensure_emoji_font_exists() # This will set self.emoji_font_loaded

        # Initialize caches
        self._logo_cache = {}
        self._font_cache = {}
        self._lock_icon_cache = None
        self._max_cache_size = 100
        self._cache_expiry = 3600
        self._last_cache_cleanup = time.time()
        self._ensure_base_dirs_exist() # Ensure directories are created on init

    def _ensure_base_dirs_exist(self):
        """Ensure base directories for static assets and logos exist."""
        try:
            os.makedirs(self.assets_dir, exist_ok=True)
            os.makedirs(self.logos_base_dir, exist_ok=True)
            os.makedirs(self.league_team_base_dir, exist_ok=True)
            os.makedirs(self.league_logo_base_dir, exist_ok=True)
            logger.debug(f"Ensured base directories exist: {self.assets_dir}, {self.logos_base_dir}")
        except OSError as e:
            logger.error(f"Could not create static/asset directories: {e}")

    # --- Font loading methods (_get_default_font, _get_default_bold_font, _get_default_emoji_font) ---
    def _get_default_font(self, assets_dir: str) -> str:
        custom_font_path = os.path.join(assets_dir, "fonts", "Roboto-Regular.ttf")
        if os.path.exists(custom_font_path): logger.debug(f"Using regular font at {custom_font_path}"); return custom_font_path
        logger.warning(f"Custom font {custom_font_path} not found.")
        if os.name == 'nt': fallback = 'C:\\Windows\\Fonts\\arial.ttf'; \
            if os.path.exists(fallback): return fallback
        else: fallbacks = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf']; \
            for fb in fallbacks:
                if os.path.exists(fb): return fb
        logger.error("Could not find a suitable default regular font."); return "arial.ttf"

    def _get_default_bold_font(self, assets_dir: str) -> str:
        custom_bold_font_path = os.path.join(assets_dir, "fonts", "Roboto-Bold.ttf")
        if os.path.exists(custom_bold_font_path): logger.debug(f"Using bold font at {custom_bold_font_path}"); return custom_bold_font_path
        logger.warning(f"Custom bold font {custom_bold_font_path} not found, falling back to regular font.")
        return self._get_default_font(assets_dir)

    def _get_default_emoji_font(self, assets_dir: str) -> str:
        custom_emoji_font_paths = [os.path.join(assets_dir, "fonts", "NotoEmoji-Regular.ttf"), os.path.join(assets_dir, "fonts", "SegoeUIEmoji.ttf")]
        for path in custom_emoji_font_paths:
            if os.path.exists(path): logger.debug(f"Using custom emoji font at {path}"); return path
        logger.warning(f"Custom emoji fonts not found in {os.path.join(assets_dir, 'fonts')}.")
        if os.name == 'nt': fallback = 'C:\\Windows\\Fonts\\seguiemj.ttf'; \
            if os.path.exists(fallback): return fallback
        else: fallbacks = ['/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf', '/System/Library/Fonts/Apple Color Emoji.ttc']; \
            for fb in fallbacks:
                if os.path.exists(fb): return fb
        logger.error("Could not find a suitable default emoji font. Emojis may not render correctly.")
        return self._get_default_font(assets_dir)

    # --- Font existence checks (_ensure_font_exists, _ensure_bold_font_exists, _ensure_emoji_font_exists) ---
    def _ensure_font_exists(self) -> None:
        try: ImageFont.truetype(self.font_path, 10); logger.debug(f"Regular font confirmed at {self.font_path}")
        except IOError:
            logger.error(f"Font file not found or invalid: {self.font_path}");
            try: ImageFont.load_default(); logger.warning("Falling back to Pillow's default font."); self.font_path = "PillowDefault"
            except Exception as e: logger.critical(f"Pillow default font failed: {e}"); raise FileNotFoundError(f"Font not found: {self.font_path}")
        except Exception as e: logger.critical(f"Error loading font {self.font_path}: {e}"); raise

    def _ensure_bold_font_exists(self) -> None:
        try: ImageFont.truetype(self.bold_font_path, 10); logger.debug(f"Bold font confirmed at {self.bold_font_path}")
        except IOError: logger.warning(f"Bold font not found: {self.bold_font_path}. Falling back."); self.bold_font_path = self.font_path
        except Exception as e: logger.error(f"Error loading bold font {self.bold_font_path}. Falling back."); self.bold_font_path = self.font_path

    def _ensure_emoji_font_exists(self) -> None:
        try: ImageFont.truetype(self.emoji_font_path, 10); logger.info(f"Emoji font confirmed at {self.emoji_font_path}"); self.emoji_font_loaded = True
        except (IOError, OSError) as e: logger.warning(f"Emoji font not found/invalid: {self.emoji_font_path}. Error: {e}."); self.emoji_font_loaded = False; self.emoji_font_path = self.font_path
        except Exception as e: logger.error(f"Error loading emoji font {self.emoji_font_path}: {e}"); self.emoji_font_loaded = False; self.emoji_font_path = self.font_path

    # --- Cache cleanup method (_cleanup_cache) ---
    def _cleanup_cache(self):
        current_time = time.time()
        if current_time - self._last_cache_cleanup > 300:
            expired_keys = [key for key, (_, timestamp) in self._logo_cache.items() if current_time - timestamp > self._cache_expiry]
            for key in expired_keys:
                if key in self._logo_cache: del self._logo_cache[key]
            if expired_keys: logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries.")
            self._last_cache_cleanup = current_time

    # --- Logo loading method (_load_team_logo) - Adjusted for user's path ---
    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Load team logo from static/logos/teams/{league_lower}/{team_lower_underscore}.png"""
        if not team_name or not league: logger.warning("Load logo: Empty team or league name."); return None
        try:
            cache_key = f"team_{league.lower()}_{team_name.lower()}"
            current_time = time.time()
            if cache_key in self._logo_cache:
                logo, timestamp = self._logo_cache[cache_key]
                if current_time - timestamp <= self._cache_expiry: logger.debug(f"Cache hit: {cache_key}"); return logo.copy()
                else: del self._logo_cache[cache_key] # Expired

            # --- Path construction based on user's structure ---
            league_dir_name = league.lower()
            normalized_team_name = team_name.lower().replace(' ', '_')
            logo_filename = f"{normalized_team_name}.png"
            # Path: static/logos/teams/{league_lower}/{team_lower_underscore}.png
            logo_path = os.path.join(self.league_team_base_dir, league_dir_name, logo_filename)
            # --- End Path construction ---

            abs_logo_path = os.path.abspath(logo_path)
            logger.debug(f"Attempting to load logo from path: {abs_logo_path}")

            if os.path.exists(abs_logo_path):
                try:
                    logo = Image.open(abs_logo_path).convert("RGBA")
                    self._cleanup_cache()
                    if len(self._logo_cache) >= self._max_cache_size:
                        try: oldest_key = next(iter(self._logo_cache)); del self._logo_cache[oldest_key]; logger.debug(f"Cache evicted: {oldest_key}")
                        except StopIteration: pass
                    self._logo_cache[cache_key] = (logo, current_time)
                    logger.debug(f"Loaded and cached logo: {cache_key} from {abs_logo_path}")
                    return logo.copy()
                except Exception as img_err: logger.error(f"Error opening/processing logo {abs_logo_path}: {img_err}"); return None
            else: logger.warning(f"Logo not found: {abs_logo_path}"); return None
        except Exception as e: logger.exception(f"Error loading logo team '{team_name}' league '{league}': {e}"); return None

    # --- Font loading method (_load_font) ---
    def _load_font(self, size: int, is_bold: bool = False) -> ImageFont.FreeTypeFont:
        font_type = 'bold' if is_bold else 'regular'; cache_key = f"font_{font_type}_{size}"
        if cache_key not in self._font_cache:
            try:
                font_path_to_use = self.bold_font_path if is_bold else self.font_path
                if font_path_to_use == "PillowDefault": self._font_cache[cache_key] = ImageFont.load_default(); logger.warning(f"Using Pillow default font: {font_type} size {size}")
                else: self._font_cache[cache_key] = ImageFont.truetype(font_path_to_use, size, encoding="unic")
            except Exception as e: logger.error(f"Failed loading font {font_type} size {size}: {e}. Using default."); self._font_cache[cache_key] = ImageFont.load_default()
        return self._font_cache[cache_key]

    # --- Lock icon loading method (_load_lock_icon) - Adjusted path ---
    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Load the lock icon image from static/lock_icon.png"""
        if self._lock_icon_cache is None:
            try:
                # --- Path construction corrected ---
                # Look directly in static directory (self.assets_dir)
                lock_path = os.path.join(self.assets_dir, "lock_icon.png")
                # --- End Path construction ---
                abs_lock_path = os.path.abspath(lock_path)
                logger.debug(f"Attempting to load lock icon from: {abs_lock_path}")
                if os.path.exists(abs_lock_path):
                    lock = Image.open(abs_lock_path).convert("RGBA")
                    lock = lock.resize((20, 20), Image.Resampling.LANCZOS)
                    self._lock_icon_cache = lock
                    logger.info(f"Successfully loaded lock icon from {abs_lock_path}")
                else:
                    logger.warning(f"Lock icon not found at expected path: {abs_lock_path}")
                    return None # Explicitly return None if not found
            except Exception as e:
                logger.error(f"Error loading lock icon: {str(e)}")
                return None # Return None on error
        # Return a copy if the icon was loaded successfully
        return self._lock_icon_cache.copy() if self._lock_icon_cache else None

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
        is_same_game: bool = False
    ) -> Image.Image:
        try:
            # --- Dimensions and Setup ---
            width = 800; base_height = 450; leg_height_with_logos = 220; leg_height_no_logos = 100
            details_height = 150; footer_height = 50; header_height = 80; separator_height = 20; totals_height = 80
            height = header_height
            if bet_type == "straight": height += 150 + details_height + footer_height; height = max(base_height, height)
            elif bet_type == "parlay" and parlay_legs:
                num_legs = len(parlay_legs); first_leg_draw_logos = is_same_game
                for i in range(num_legs):
                    if i > 0: height += separator_height
                    height += leg_height_with_logos if (i == 0 and first_leg_draw_logos) else leg_height_no_logos
                height += separator_height + totals_height + footer_height; height = max(base_height, height)
            else: height = base_height
            image = Image.new('RGB', (width, height), (40, 40, 40)); draw = ImageDraw.Draw(image)

            # --- Fonts ---
            try:
                header_font=self._load_font(32,is_bold=True); team_font=self._load_font(28); details_font=self._load_font(24)
                odds_font=self._load_font(28,is_bold=True); units_font=self._load_font(24); small_font=self._load_font(18)
                fallback_font = details_font # Default fallback
                if self.emoji_font_loaded:
                    try: fallback_font = ImageFont.truetype(self.emoji_font_path, 24)
                    except Exception as e: logger.error(f"Failed emoji font instance: {e}"); self.emoji_font_loaded = False
            except Exception as e: logger.error(f"Font loading failed: {e}. Using Pillow default."); header_font=team_font=details_font=odds_font=units_font=small_font=fallback_font = ImageFont.load_default()

            # --- Header ---
            header_y = 40
            if bet_type == "parlay" and not is_same_game: header_text_type = "Multi-Team Parlay Bet"
            elif bet_type == "parlay" and is_same_game: header_text_type = "Same-Game Parlay"
            else: header_text_type = "Straight Bet"
            header_text = f"{league} - {header_text_type}" if league else header_text_type
            draw.text((width // 2, header_y), header_text, fill='white', font=header_font, anchor='mm')
            current_y = header_y + 60

            # --- Draw Content (Straight or Parlay) ---
            lock_icon = self._load_lock_icon() # Load lock icon once

            if bet_type == "straight":
                logo_size=(100, 100); current_league=league or 'NHL'
                home_logo=self._load_team_logo(home_team, current_league); away_logo=self._load_team_logo(away_team, current_league)
                home_x=width//4; away_x=3*width//4
                if home_logo: image.paste(home_logo, (home_x - logo_size[0] // 2, current_y), home_logo)
                draw.text((home_x, current_y + logo_size[1] + 15), home_team, fill='white', font=team_font, anchor='mm')
                if away_logo: image.paste(away_logo, (away_x - logo_size[0] // 2, current_y), away_logo)
                draw.text((away_x, current_y + logo_size[1] + 15), away_team, fill='white', font=team_font, anchor='mm')
                current_y += logo_size[1] + 40
                bet_text = f"{home_team}: {line}"; draw.text((width // 2, current_y), bet_text, fill='white', font=details_font, anchor='mm'); current_y += 40
                draw.line([(40, current_y), (width - 40, current_y)], fill=(80, 80, 80), width=2); current_y += 30
                odds_text = f"{odds:+.0f}" if odds else "N/A"; draw.text((width // 2, current_y), odds_text, fill='white', font=odds_font, anchor='mm'); current_y += 40
                units_text=f"To Win {units:.2f} Units"
                try: units_bbox=draw.textbbox((0,0), units_text, font=units_font); units_width=units_bbox[2]-units_bbox[0]
                except AttributeError: units_width,_=draw.textsize(units_text, font=units_font)
                if lock_icon:
                    lock_spacing=10; text_height=units_font.getmetrics()[0] if hasattr(units_font,'getmetrics') else 20; lock_y_offset=(text_height-lock_icon.height)//2; base_lock_y=current_y-(text_height//2)
                    lock_x_left=(width-units_width-2*lock_icon.width-2*lock_spacing)//2; image.paste(lock_icon,(lock_x_left,base_lock_y+lock_y_offset),lock_icon)
                    text_x=lock_x_left+lock_icon.width+lock_spacing; draw.text((text_x,current_y),units_text,fill=(255,215,0),font=units_font,anchor='lm')
                    lock_x_right=text_x+units_width+lock_spacing; image.paste(lock_icon,(lock_x_right,base_lock_y+lock_y_offset),lock_icon)
                elif self.emoji_font_loaded: draw.text((width // 2, current_y), f"🔒 {units_text} 🔒", fill=(255,215,0), font=fallback_font, anchor='mm')
                else: draw.text((width // 2, current_y), f"[L] {units_text} [L]", fill=(255,215,0), font=details_font, anchor='mm')
                current_y += 40
            elif bet_type == "parlay" and parlay_legs:
                draw_first_leg_logos = is_same_game
                for i, leg in enumerate(parlay_legs):
                    if i > 0: draw.line([(40, current_y - 10), (width - 40, current_y - 10)], fill=(80, 80, 80), width=1); current_y += 10
                    current_y = self._draw_leg(image=image, draw=draw, leg=leg, league=leg.get('league', league or 'NHL'), width=width, start_y=current_y, team_font=team_font, details_font=details_font, odds_font=odds_font, emoji_font=fallback_font, draw_logos=(i == 0 and draw_first_leg_logos)); current_y += 10
                current_y += 10; draw.line([(20, current_y), (width - 20, current_y)], fill='white', width=2); current_y += 30
                total_odds_display = odds; total_units_display = sum(float(leg.get('units', 0)) for leg in parlay_legs) if all('units' in leg for leg in parlay_legs) else units
                odds_text = f"Total Odds: {total_odds_display:+.0f}" if total_odds_display else "Total Odds: N/A"; draw.text((width // 2, current_y), odds_text, fill='white', font=odds_font, anchor='mm'); current_y += 40
                units_text = f"Total Units: {total_units_display:.2f}"
                try: units_bbox = draw.textbbox((0, 0), units_text, font=units_font); units_width = units_bbox[2] - units_bbox[0]
                except AttributeError: units_width, _ = draw.textsize(units_text, font=units_font)
                if lock_icon:
                    lock_spacing=10; text_height=units_font.getmetrics()[0] if hasattr(units_font,'getmetrics') else 20; lock_y_offset=(text_height-lock_icon.height)//2; base_lock_y=current_y-(text_height//2)
                    lock_x_left=(width-units_width-2*lock_icon.width-2*lock_spacing)//2; image.paste(lock_icon,(lock_x_left,base_lock_y+lock_y_offset),lock_icon)
                    text_x=lock_x_left+lock_icon.width+lock_spacing; draw.text((text_x,current_y),units_text,fill=(255,215,0),font=units_font,anchor='lm')
                    lock_x_right=text_x+units_width+lock_spacing; image.paste(lock_icon,(lock_x_right,base_lock_y+lock_y_offset),lock_icon)
                elif self.emoji_font_loaded: draw.text((width // 2, current_y), f"🔒 {units_text} 🔒", fill=(255,215,0), font=fallback_font, anchor='mm')
                else: draw.text((width // 2, current_y), f"[L] {units_text} [L]", fill=(255,215,0), font=details_font, anchor='mm')
                current_y += 40

            # --- Footer ---
            footer_y = height - 30
            draw.text((20, footer_y), f"Bet #{bet_id}", fill=(150, 150, 150), font=small_font, anchor='lm')
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC')
            draw.text((width - 20, footer_y), timestamp_text, fill=(150, 150, 150), font=small_font, anchor='rm')

            return image
        except Exception as e:
            logger.exception(f"Error generating bet slip: {str(e)}")
            error_img = Image.new('RGB', (800, 100), (40, 40, 40))
            error_draw = ImageDraw.Draw(error_img)
            error_font = self._load_font(20) if self._font_cache else ImageFont.load_default()
            error_draw.text((10, 10), f"Error generating bet slip image. Check logs.", fill='red', font=error_font)
            return error_img

    # --- Method to draw a single parlay leg ---
    def _draw_leg(
        self, image: Image.Image, draw: ImageDraw.Draw, leg: Dict[str, Any], league: str, width: int, start_y: int,
        team_font: ImageFont.FreeTypeFont, details_font: ImageFont.FreeTypeFont, odds_font: ImageFont.FreeTypeFont,
        emoji_font: ImageFont.FreeTypeFont, draw_logos: bool = True
    ) -> int:
        """Draw a single leg of a parlay bet."""
        home_team=leg.get('home_team',leg.get('team','Unknown')); away_team=leg.get('away_team',leg.get('opponent','Unknown'))
        line=leg.get('line','ML'); current_y = start_y; logo_size=(80, 80)
        if draw_logos:
            home_logo=self._load_team_logo(home_team,league); away_logo=self._load_team_logo(away_team,league)
            logo_y_padding=15; home_x=width*0.3; away_x=width*0.7
            if home_logo: image.paste(home_logo,(int(home_x-logo_size[0]//2),current_y+logo_y_padding),home_logo)
            if away_logo: image.paste(away_logo,(int(away_x-logo_size[0]//2),current_y+logo_y_padding),away_logo)
            team_y=current_y+logo_size[1]+logo_y_padding+15
            draw.text((home_x,team_y),home_team,fill='white',font=team_font,anchor='mm')
            draw.text((away_x,team_y),away_team,fill='white',font=team_font,anchor='mm'); current_y = team_y + 40
        else: current_y += 20
        details_y = current_y; line_text = f"{home_team} vs {away_team}: {line}"; max_line_width = width - 80
        try: line_bbox=draw.textbbox((0,0),line_text,font=details_font); line_width=line_bbox[2]-line_bbox[0]
        except AttributeError: line_width,_=draw.textsize(line_text,font=details_font)
        if line_width > max_line_width: approx_chars=int(len(line_text)*(max_line_width/line_width))-3; line_text=line_text[:max(10,approx_chars)]+"..."
        draw.text((width//2,details_y),line_text,fill='white',font=details_font,anchor='mm'); current_y = details_y + 35
        return current_y

    # --- _calculate_parlay_odds, _save_team_logo, save_bet_slip ---
    def _calculate_parlay_odds(self, legs: List[Dict[str, Any]]) -> float:
        try:
            total_decimal_odds = 1.0
            for leg in legs:
                leg_odds = float(leg.get('odds', 0));
                if leg_odds == 0: continue
                if leg_odds > 0: decimal_leg = (leg_odds / 100) + 1
                else: decimal_leg = (100 / abs(leg_odds)) + 1
                total_decimal_odds *= decimal_leg
            if total_decimal_odds == 1.0: return 0.0
            if total_decimal_odds >= 2.0: final_american_odds = (total_decimal_odds - 1) * 100
            else: final_american_odds = -100 / (total_decimal_odds - 1)
            return final_american_odds
        except Exception as e: logger.error(f"Error calculating parlay odds: {e}"); return 0.0

    def _save_team_logo(self, logo: Image.Image, team_name: str, league: str) -> None:
        logger.debug(f"Placeholder: Saving handled by load_logos command.")
        pass

    def save_bet_slip(self, image: Image.Image, output_path: str) -> None:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path, "PNG", optimize=True)
            logger.info(f"Bet slip image saved to {output_path}")
        except Exception as e: logger.error(f"Error saving bet slip to {output_path}: {e}"); raise
