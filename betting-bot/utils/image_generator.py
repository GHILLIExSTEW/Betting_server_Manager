# betting-bot/utils/image_generator.py

import logging
import os
import time
import io
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import traceback

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from config.asset_paths import (
    # ASSETS_DIR, # Not directly used in this version, paths constructed from BASE_DIR
    # FONT_DIR,   # Not directly used in this version
    # LOGO_DIR,   # Not directly used in this version
    # TEAMS_SUBDIR, # Not directly used in this version
    # LEAGUES_SUBDIR, # Not directly used in this version
    get_sport_category_for_path, # Keep if used by other parts of your project
    BASE_DIR
)
from config.team_mappings import normalize_team_name
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL", "NCAAB": "BASKETBALL", "WNBA": "BASKETBALL", "EUROLEAGUE": "BASKETBALL", "CBA": "BASKETBALL",
    "NFL": "FOOTBALL", "NCAAF": "FOOTBALL", "CFL": "FOOTBALL", "XFL": "FOOTBALL",
    "MLB": "BASEBALL", "NCAAB_BASEBALL": "BASEBALL", "NPB": "BASEBALL", "KBO": "BASEBALL",
    "NHL": "HOCKEY", "KHL": "HOCKEY", "SHL": "HOCKEY",
    "MLS": "SOCCER", "EPL": "SOCCER", "LA_LIGA": "SOCCER", "SERIE_A": "SOCCER", "BUNDESLIGA": "SOCCER",
    "LIGUE_1": "SOCCER", "UEFA_CL": "SOCCER", "COPA_LIBERTADORES": "SOCCER", "A_LEAGUE": "SOCCER", "J_LEAGUE": "SOCCER",
    "ATP": "TENNIS", "WTA": "TENNIS", "ITF": "TENNIS", "GRAND_SLAM": "TENNIS",
    "UFC": "MMA", "BELLATOR": "MMA", "ONE_CHAMPIONSHIP": "MMA", "PFL": "MMA",
    "PGA": "GOLF", "LPGA": "GOLF", "EUROPEAN_TOUR": "GOLF", "MASTERS": "GOLF",
    "BOXING": "BOXING", "CRICKET": "CRICKET", "IPL": "CRICKET", "BBL": "CRICKET", "TEST_CRICKET": "CRICKET",
    "RUGBY_UNION": "RUGBY", "SUPER_RUGBY": "RUGBY", "SIX_NATIONS": "RUGBY",
    "RUGBY_LEAGUE": "RUGBY", "NRL": "RUGBY", "SUPER_LEAGUE": "RUGBY",
    "F1": "MOTORSPORTS", "NASCAR": "MOTORSPORTS", "INDYCAR": "MOTORSPORTS", "MOTOGP": "MOTORSPORTS",
    "DARTS": "DARTS", "PDC": "DARTS", "VOLLEYBALL": "VOLLEYBALL", "FIVB": "VOLLEYBALL",
    "TABLE_TENNIS": "TABLE_TENNIS", "ITTF": "TABLE_TENNIS", "CYCLING": "CYCLING",
    "TOUR_DE_FRANCE": "CYCLING", "GIRO_D_ITALIA": "CYCLING", "VUELTA_A_ESPANA": "CYCLING",
    "ESPORTS_CSGO": "ESPORTS", "ESPORTS_LOL": "ESPORTS", "ESPORTS_DOTA2": "ESPORTS",
    "ESPORTS_OVERWATCH": "ESPORTS", "ESPORTS_FIFA": "ESPORTS",
    "AUSSIE_RULES": "AUSTRALIAN_FOOTBALL", "AFL": "AUSTRALIAN_FOOTBALL",
    "HANDBALL": "HANDBALL", "EHF_CL": "HANDBALL", "SNOOKER": "SNOOKER",
    "WORLD_CHAMPIONSHIP_SNOOKER": "SNOOKER", "BADMINTON": "BADMINTON", "BWF": "BADMINTON",
    "LACROSSE": "LACROSSE", "NLL": "LACROSSE", "FIELD_HOCKEY": "FIELD_HOCKEY", "FIH_PRO_LEAGUE": "FIELD_HOCKEY"
}
DEFAULT_FALLBACK_SPORT_CATEGORY = "OTHER_SPORTS"

def load_fonts():
    fonts = {}
    try:
        font_dir = os.path.join(BASE_DIR, "assets", "fonts")
        font_path = os.path.join(font_dir, "Roboto-Regular.ttf")
        bold_font_path = os.path.join(font_dir, "Roboto-Bold.ttf")
        emoji_font_path = os.path.join(font_dir, "NotoColorEmoji-Regular.ttf")
        
        missing_files = []
        for p, name in [(font_path, "Regular"), (bold_font_path, "Bold"), (emoji_font_path, "Emoji")]:
            if not os.path.exists(p):
                missing_files.append(f"{name} font at {p}")
        
        if missing_files:
            logger.error("Font files not found: %s", "; ".join(missing_files))
            raise FileNotFoundError(f"Font files not found: {', '.join(missing_files)}")

        fonts['font_m_18'] = ImageFont.truetype(font_path, 18)
        fonts['font_m_24'] = ImageFont.truetype(font_path, 24)
        fonts['font_b_18'] = ImageFont.truetype(bold_font_path, 18)
        fonts['font_b_24'] = ImageFont.truetype(bold_font_path, 24)
        fonts['font_b_28'] = ImageFont.truetype(bold_font_path, 28)
        fonts['font_b_36'] = ImageFont.truetype(bold_font_path, 36)
        fonts['emoji_font_24'] = ImageFont.truetype(emoji_font_path, 24)
        logger.info("Custom fonts loaded successfully for global FONTS.")
        return fonts
        
    except Exception as e:
        logger.error(f"Critical error loading custom fonts: {e}. Falling back to default system fonts.", exc_info=True)
        default_font = ImageFont.load_default()
        return {key: default_font for key in ['font_m_18', 'font_m_24', 'font_b_18', 'font_b_24', 'font_b_28', 'font_b_36', 'emoji_font_24']}

FONTS = load_fonts()

class BetSlipGenerator:
    def __init__(self, guild_id: Optional[int] = None):
        self.guild_id = guild_id
        self.db_manager = DatabaseManager() 
        self.padding = 20
        self.LEAGUE_TEAM_BASE_DIR = os.path.join(BASE_DIR, "static", "logos", "teams")
        self.LEAGUE_LOGO_BASE_DIR = os.path.join(BASE_DIR, "static", "logos", "leagues")
        self.DEFAULT_LOGO_PATH = os.path.join(BASE_DIR, "static", "logos", "default_logo.png")
        # self.LOCK_ICON_PATH = os.path.join(BASE_DIR, "static", "logos", "lock_icon.png") # Path for image lock if needed
        self._logo_cache: Dict[str, tuple[Image.Image, float]] = {}
        # self._lock_icon_cache: Optional[Image.Image] = None # If using image for lock
        self._last_cache_cleanup = time.time()
        self._cache_expiry = 300  # 5 minutes
        self._max_cache_size = 100
        
        logger.info("Initializing BetSlipGenerator instance...")
        self.fonts = FONTS # Use globally loaded fonts
        if any(font == ImageFont.load_default() for font in self.fonts.values()):
            logger.warning("BetSlipGenerator: One or more custom fonts failed to load; using default system fonts.")
        else:
            logger.info("BetSlipGenerator: Custom fonts loaded successfully.")

    def _get_text_dimensions(self, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height

    def _draw_header(self, draw: ImageDraw.Draw, image_width: int, league_logo: Optional[Image.Image], league: str, bet_type_str: str):
        y_offset = 25 # Slightly higher
        title_font = self.fonts['font_b_36']
        logo_display_size = (45, 45) # Adjusted logo size
        text_color = 'white'

        bet_type_display = bet_type_str.replace('_', ' ').title()
        if "Game Line" in bet_type_display: bet_type_display = "Game Line" 
        elif "Player Prop" in bet_type_display: bet_type_display = "Player Prop"

        title_text = f"{league.upper()} - {bet_type_display}"
        title_w, title_h = self._get_text_dimensions(title_text, title_font)
        
        logo_x = self.padding
        title_x_no_logo = (image_width - title_w) // 2

        if league_logo:
            try:
                league_logo_resized = league_logo.resize(logo_display_size, Image.Resampling.LANCZOS)
                logo_y = y_offset + (title_h - logo_display_size[1]) // 2
                
                # Position title next to logo
                title_x_with_logo = logo_x + logo_display_size[0] + 15
                
                # If title with logo goes too far, center the whole block (logo + title)
                total_width_with_logo = logo_display_size[0] + 15 + title_w
                if total_width_with_logo < image_width - 2 * self.padding:
                    start_block_x = (image_width - total_width_with_logo) // 2
                    logo_x = start_block_x
                    title_x = logo_x + logo_display_size[0] + 15
                else: # Fallback if too wide, just place logo left and title next
                     title_x = title_x_with_logo


                if hasattr(draw, 'im'):
                    if league_logo_resized.mode == 'RGBA':
                        draw.im.paste(league_logo_resized, (logo_x, logo_y), league_logo_resized)
                    else:
                        draw.im.paste(league_logo_resized, (logo_x, logo_y))
                else: draw.bitmap((logo_x, logo_y), league_logo_resized)
            except Exception as e: 
                logger.error(f"Error drawing league logo in header: {e}", exc_info=True)
                title_x = title_x_no_logo # Center title if logo fails
        else:
            title_x = title_x_no_logo

        draw.text((title_x, y_offset), title_text, font=title_font, fill=text_color, anchor="lt")


    def _draw_teams_section(self, img: Image.Image, draw: ImageDraw.Draw, image_width: int, home_team: str, away_team: str, home_logo: Optional[Image.Image], away_logo: Optional[Image.Image]):
        y_base = 85 # Start y position for logos
        logo_size = (70, 70) # Slightly smaller
        text_y_offset = logo_size[1] + 8 
        team_name_font = self.fonts['font_b_24']
        text_color = 'white'
        
        section_width = image_width // 2 - self.padding * 1.5 # Adjusted for spacing
        home_section_center_x = self.padding + section_width // 2 
        away_section_center_x = image_width - self.padding - section_width // 2

        if home_logo:
            try:
                home_logo_resized = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
                home_logo_x = home_section_center_x - logo_size[0] // 2
                if home_logo_resized.mode == 'RGBA': img.paste(home_logo_resized, (home_logo_x, y_base), home_logo_resized)
                else: img.paste(home_logo_resized, (home_logo_x, y_base))
            except Exception as e: logger.error(f"Error pasting home logo: {e}", exc_info=True)
        
        home_name_w, _ = self._get_text_dimensions(home_team, team_name_font)
        home_name_x = home_section_center_x - home_name_w // 2
        draw.text((home_name_x, y_base + text_y_offset), home_team, font=team_name_font, fill=text_color, anchor="lt")

        if away_logo:
            try:
                away_logo_resized = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
                away_logo_x = away_section_center_x - logo_size[0] // 2
                if away_logo_resized.mode == 'RGBA': img.paste(away_logo_resized, (away_logo_x, y_base), away_logo_resized)
                else: img.paste(away_logo_resized, (away_logo_x, y_base))
            except Exception as e: logger.error(f"Error pasting away logo: {e}", exc_info=True)

        away_name_w, _ = self._get_text_dimensions(away_team, team_name_font)
        away_name_x = away_section_center_x - away_name_w // 2
        draw.text((away_name_x, y_base + text_y_offset), away_team, font=team_name_font, fill=text_color, anchor="lt")


    def _draw_straight_details(self, draw: ImageDraw.Draw, image_width: int, image_height: int, line: Optional[str], odds: float, units: float, bet_id: str, timestamp: datetime):
        y = 100 + 70 + 10 + 24 + 30 # Start after team section
        center_x = image_width / 2
        text_color = 'white'; gold_color = '#FFD700'; divider_color = '#606060' # Darker grey

        line_font = self.fonts['font_m_24']; odds_font = self.fonts['font_b_28']
        units_font = self.fonts['font_b_24']; emoji_font = self.fonts['emoji_font_24']
        
        if line:
            line_w, line_h = self._get_text_dimensions(line, line_font)
            draw.text((center_x, y), line, font=line_font, fill=text_color, anchor="mt")
            y += line_h + 12 

        draw.line([(self.padding + 20, y), (image_width - self.padding - 20, y)], fill=divider_color, width=2); y += 12

        odds_text = self._format_odds_with_sign(odds)
        odds_w, odds_h = self._get_text_dimensions(odds_text, odds_font)
        draw.text((center_x, y), odds_text, font=odds_font, fill=text_color, anchor="mt"); y += odds_h + 12
        
        lock_char = "🔒"; units_text_part = f" To Win {units:.2f} Units "
        lock_w, lock_h = self._get_text_dimensions(lock_char, emoji_font)
        units_text_part_w, units_text_part_h = self._get_text_dimensions(units_text_part, units_font)
        total_units_section_w = lock_w + units_text_part_w + lock_w
        current_x = center_x - total_units_section_w / 2
        
        # Try to align text middle with emoji middle by adjusting text_y
        emoji_center_y_offset = lock_h / 2
        text_center_y_offset = units_text_part_h / 2
        text_y_for_emoji_align = y + emoji_center_y_offset - text_center_y_offset

        draw.text((current_x, y), lock_char, font=emoji_font, fill=gold_color, anchor="lt")
        current_x += lock_w
        draw.text((current_x, text_y_for_emoji_align), units_text_part, font=units_font, fill=gold_color, anchor="lt")
        current_x += units_text_part_w
        draw.text((current_x, y), lock_char, font=emoji_font, fill=gold_color, anchor="lt")
        
    def _draw_parlay_details(self, draw: ImageDraw.Draw, image_width: int, image_height: int, legs: List[Dict], odds: float, units: float, bet_id: str, timestamp: datetime, is_same_game: bool):
        y = 100 + 70 + 10 + 24 + 20; center_x = image_width / 2
        text_color = 'white'; gold_color = '#FFD700'; footer_color = '#CCCCCC'; divider_color = '#606060'
        leg_font = self.fonts['font_m_18']; total_odds_font = self.fonts['font_b_24']
        units_font = self.fonts['font_b_24']; emoji_font = self.fonts['emoji_font_24']
        max_leg_y = image_height - 120 # Reserve space

        for i, leg_data in enumerate(legs):
            leg_text = f"Leg {i+1}: {leg_data.get('league','N/A')} - {leg_data.get('team', 'N/A')} {leg_data.get('line', 'N/A')} ({leg_data.get('odds_str', 'N/A')})"
            _leg_w, leg_h = self._get_text_dimensions(leg_text, leg_font)
            if y + leg_h > max_leg_y and i < len(legs) -1 :
                draw.text((self.padding, y), "...", font=leg_font, fill=text_color, anchor="lt"); y += leg_h + 5; break 
            draw.text((self.padding, y), leg_text, font=leg_font, fill=text_color, anchor="lt"); y += leg_h + 5
        
        y += 10 
        draw.line([(self.padding + 20, y), (image_width - self.padding - 20, y)], fill=divider_color, width=2); y += 12
        total_odds_text = f"Total Parlay Odds: {self._format_odds_with_sign(odds)}"
        total_odds_w, total_odds_h = self._get_text_dimensions(total_odds_text, total_odds_font)
        draw.text( (center_x, y), total_odds_text, font=total_odds_font, fill=text_color, anchor="mt"); y += total_odds_h + 12

        lock_char = "🔒"; units_text_part = f" To Win {units:.2f} Units "
        lock_w, lock_h = self._get_text_dimensions(lock_char, emoji_font)
        units_text_part_w, units_text_part_h = self._get_text_dimensions(units_text_part, units_font)
        total_units_section_w = lock_w + units_text_part_w + lock_w
        current_x = center_x - total_units_section_w / 2
        text_y_adj = y + (lock_h - units_text_part_h) // 2
        draw.text((current_x, y), lock_char, font=emoji_font, fill=gold_color, anchor="lt")
        current_x += lock_w
        draw.text((current_x, text_y_adj), units_text_part, font=units_font, fill=gold_color, anchor="lt")
        current_x += units_text_part_w
        draw.text((current_x, y), lock_char, font=emoji_font, fill=gold_color, anchor="lt")
        
    def _draw_footer(self, draw: ImageDraw.Draw, image_width: int, image_height: int, bet_id: str, timestamp: datetime):
        footer_font = self.fonts['font_m_18']; footer_color = '#CCCCCC'
        _ , footer_text_h = self._get_text_dimensions("Test", footer_font)
        footer_y = image_height - self.padding - footer_text_h 

        bet_id_text = f"Bet #{bet_id}"
        timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC')
        draw.text((self.padding, footer_y), bet_id_text, font=footer_font, fill=footer_color, anchor="ls")
        ts_w, _ = self._get_text_dimensions(timestamp_text, footer_font)
        draw.text((image_width - self.padding, footer_y), timestamp_text, font=footer_font, fill=footer_color, anchor="rs")

    async def get_guild_background(self) -> Optional[Image.Image]:
        if not self.guild_id: return None
        background_image = None; guild_bg_path_from_db = None; effective_path = None
        try:
            settings = await self.db_manager.fetch_one("SELECT guild_background FROM guild_settings WHERE guild_id = %s",(self.guild_id,))
            guild_bg_path_from_db = settings.get("guild_background") if settings else None
            if guild_bg_path_from_db:
                normalized_db_path = guild_bg_path_from_db.replace('\\', '/')
                if os.path.isabs(normalized_db_path): effective_path = normalized_db_path
                else:
                    # Path from DB should be relative to BASE_DIR/static/
                    # e.g. DB: "guilds/123/bg.png" -> /home/container/betting-bot/static/guilds/123/bg.png
                    # e.g. DB: "static/guilds/123/bg.png" -> /home/container/betting-bot/static/guilds/123/bg.png (if static is part of path)
                    if normalized_db_path.lower().startswith('static/'):
                        effective_path = os.path.join(BASE_DIR, normalized_db_path)
                    else:
                        effective_path = os.path.join(BASE_DIR, "static", normalized_db_path)
                
                if os.path.exists(effective_path):
                    logger.info(f"Loading guild background from local path: {effective_path}")
                    background_image = Image.open(effective_path).convert("RGBA")
                    logger.info(f"Successfully loaded guild background from local path.")
                else: logger.warning(f"Guild background file NOT FOUND. DB path:'{guild_bg_path_from_db}', Resolved to:'{effective_path}'.")
            else: logger.debug(f"No guild background path for guild {self.guild_id}.")
        except Exception as e: logger.error(f"Error loading guild background (path:{guild_bg_path_from_db or 'N/A'}): {e}", exc_info=True)
        return background_image

    async def generate_bet_slip(
        self, home_team: str, away_team: str, league: str, odds: float, units: float, 
        bet_id: str, timestamp: datetime, bet_type: str = "straight", line: Optional[str] = None, 
        parlay_legs: Optional[List[Dict]] = None, is_same_game: bool = False
    ) -> Optional[Image.Image]:
        try:
            logger.info(f"Generating bet slip - Home:'{home_team}', Away:'{away_team}', League:'{league}', Type:{bet_type}")
            width, height = 600, 400
            
            guild_bg_image_pil = await self.get_guild_background()
            img = Image.new('RGBA', (width, height), "#23232a") 

            if guild_bg_image_pil:
                try:
                    guild_bg_image_pil = guild_bg_image_pil.convert("RGBA")
                    alpha_channel = guild_bg_image_pil.getchannel('A')
                    semi_transparent_alpha = alpha_channel.point(lambda p: int(p * 0.5))
                    guild_bg_image_pil.putalpha(semi_transparent_alpha)
                    
                    bg_w, bg_h = guild_bg_image_pil.size
                    ratio_w = width / bg_w
                    ratio_h = height / bg_h
                    
                    if ratio_w > ratio_h: # Fit by width, crop height
                        new_w = width
                        new_h = int(bg_h * ratio_w)
                        resized_bg = guild_bg_image_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        crop_y = (new_h - height) // 2
                        final_bg_to_paste = resized_bg.crop((0, crop_y, width, crop_y + height))
                    else: # Fit by height, crop width
                        new_h = height
                        new_w = int(bg_w * ratio_h)
                        resized_bg = guild_bg_image_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        crop_x = (new_w - width) // 2
                        final_bg_to_paste = resized_bg.crop((crop_x, 0, crop_x + width, height))

                    img.paste(final_bg_to_paste, (0,0), final_bg_to_paste)
                    logger.info("Applied guild background with 50% transparency.")
                except Exception as bg_err: logger.error(f"Error processing guild background: {bg_err}", exc_info=True)
            
            draw = ImageDraw.Draw(img)
            
            league_logo_pil = self._load_league_logo(league)
            home_logo_pil = self._load_team_logo(home_team, league)
            away_logo_pil = self._load_team_logo(away_team, league)
            
            default_pil_logo = None
            if os.path.exists(self.DEFAULT_LOGO_PATH):
                try: default_pil_logo = Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA")
                except Exception as e: logger.error(f"Failed to load default logo: {e}")
            
            if not league_logo_pil and default_pil_logo: league_logo_pil = default_pil_logo.copy()
            if not home_logo_pil and default_pil_logo: home_logo_pil = default_pil_logo.copy()
            if not away_logo_pil and default_pil_logo: away_logo_pil = default_pil_logo.copy()

            self._draw_header(draw, width, league_logo_pil, league, bet_type)
            self._draw_teams_section(img, draw, width, home_team, away_team, home_logo_pil, away_logo_pil)
            
            if bet_type.lower() == "parlay" and parlay_legs:
                self._draw_parlay_details(draw, width, height, parlay_legs, odds, units, bet_id, timestamp, is_same_game)
            else:
                self._draw_straight_details(draw, width, height, line, odds, units, bet_id, timestamp)
            
            self._draw_footer(draw, width, height, bet_id, timestamp)

            logger.info(f"Bet slip generated OK for bet ID: {bet_id}")
            return img.convert("RGB")
            
        except Exception as e:
            logger.error(f"Error in generate_bet_slip: {str(e)}", exc_info=True)
            try:
                err_img = Image.new('RGB', (600,100), "darkred"); err_draw = ImageDraw.Draw(err_img)
                err_draw.text((10,10), f"Error creating slip:\n{str(e)[:100]}", font=ImageFont.load_default(), fill="white")
                return err_img
            except Exception as final_err: logger.error(f"Fallback image failed: {final_err}")
            return None
                
    def _load_fonts(self): pass 

    def _cleanup_cache(self):
        now = time.time()
        if now - self._last_cache_cleanup > 300:
            expired_keys = [k for k, (_, ts) in self._logo_cache.items() if now - ts > self._cache_expiry]
            for k in expired_keys: self._logo_cache.pop(k, None)
            self._last_cache_cleanup = now
            logger.debug(f"Logo cache cleaned. Removed {len(expired_keys)} expired items.")

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        if not league: return None
        try:
            cache_key = f"league_{league}"; now = time.time()
            if cache_key in self._logo_cache:
                logo, ts = self._logo_cache[cache_key]
                if now - ts <= self._cache_expiry: return logo.copy()
                else: del self._logo_cache[cache_key]
            
            sport = get_sport_category_for_path(league.upper())
            if not sport: 
                logger.warning(f"Sport category not for league '{league}'. Default logo."); 
                return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            
            fname = f"{league.lower().replace(' ', '_')}.png"; 
            logo_dir = os.path.join(self.LEAGUE_LOGO_BASE_DIR, sport, league.upper())
            logo_path = os.path.join(logo_dir, fname); absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info("Loading league logo - League:'%s',Path:'%s',Exists:%s", league, absolute_logo_path, file_exists)
            
            logo = None
            if file_exists:
                try: logo = Image.open(absolute_logo_path).convert("RGBA")
                except Exception as e: logger.error(f"Error opening league logo {absolute_logo_path}: {e}")
            
            if logo:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    oldest_key = min(self._logo_cache, key=lambda k: self._logo_cache[k][1]); del self._logo_cache[oldest_key]
                self._logo_cache[cache_key] = (logo.copy(), now); return logo.copy()
                
            logger.warning(f"No logo for league {league} (path: {absolute_logo_path}). Defaulting."); 
            return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
        except Exception as e:
            logger.error(f"Error in _load_league_logo for {league}: {e}", exc_info=True)
            try: return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            except Exception as def_err: logger.error(f"Error loading default logo: {def_err}")
            return None

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        try:
            sport = get_sport_category_for_path(league.upper())
            if not sport: logger.error(f"No sport for league: {league} (team: {team_name})"); return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            team_dir = self._ensure_team_dir_exists(league)
            if not team_dir: return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            
            normalized_team_name = normalize_team_name(team_name)
            logo_path = os.path.join(team_dir, f"{normalized_team_name}.png"); absolute_logo_path = os.path.abspath(logo_path)
            logger.info(f"Attempting to load team logo: {absolute_logo_path}")

            if os.path.exists(absolute_logo_path): return Image.open(absolute_logo_path).convert("RGBA")
            else: logger.warning(f"Team logo not found: {absolute_logo_path}. Using default."); return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
        except Exception as e:
            logger.error(f"Error in _load_team_logo for {team_name} ({league}): {e}", exc_info=True)
            try: return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            except Exception as def_err: logger.error(f"Error loading default team logo: {def_err}")
            return None

    def _ensure_team_dir_exists(self, league: str) -> Optional[str]:
        try:
            sport = get_sport_category_for_path(league.upper())
            if not sport: logger.error(f"No sport for league: {league}"); return None
            team_dir = os.path.join(self.LEAGUE_TEAM_BASE_DIR, sport, league.upper())
            os.makedirs(team_dir, exist_ok=True); return team_dir
        except Exception as e: logger.error(f"Error ensuring team directory for {league}: {e}", exc_info=True); return None
    
    def _normalize_team_name(self, team_name: str) -> str: return normalize_team_name(team_name) # DEPRECATED - Use global
    def _format_odds_with_sign(self, odds: float) -> str: return f"+{int(odds)}" if odds > 0 else str(int(odds))
