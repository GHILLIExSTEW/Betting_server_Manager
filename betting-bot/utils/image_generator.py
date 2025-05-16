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
    get_sport_category_for_path,
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
        fonts_fallback = {key: default_font for key in ['font_m_18', 'font_m_24', 'font_b_18', 'font_b_24', 'font_b_28', 'font_b_36']}
        fonts_fallback['emoji_font_24'] = default_font 
        return fonts_fallback

FONTS = load_fonts()

class BetSlipGenerator:
    def __init__(self, guild_id: Optional[int] = None):
        self.guild_id = guild_id
        self.db_manager = DatabaseManager()
        self.padding = 20
        self.LEAGUE_TEAM_BASE_DIR = os.path.join(BASE_DIR, "static", "logos", "teams")
        self.LEAGUE_LOGO_BASE_DIR = os.path.join(BASE_DIR, "static", "logos", "leagues")
        self.DEFAULT_LOGO_PATH = os.path.join(BASE_DIR, "static", "logos", "default_logo.png")
        self.LOCK_ICON_PATH = "/home/container/betting-bot/static/lock_icon.png"
        
        self._logo_cache: Dict[str, tuple[Image.Image, float]] = {}
        self._lock_icon_cache: Optional[Image.Image] = None
        self._last_cache_cleanup = time.time()
        self._cache_expiry = 300
        self._max_cache_size = 100
        
        logger.info("Initializing BetSlipGenerator instance...")
        self.fonts = FONTS
        if any(font == ImageFont.load_default() for key, font in self.fonts.items() if key != 'emoji_font_24'):
            logger.warning("BetSlipGenerator: One or more regular/bold custom fonts failed to load; using default system fonts for them.")
        else:
            logger.info("BetSlipGenerator: Regular/bold custom fonts loaded successfully.")
        
        if self.fonts['emoji_font_24'] == ImageFont.load_default():
            logger.warning("BetSlipGenerator: NotoColorEmoji font failed to load; emoji rendering will be basic or fail.")
        else:
            logger.info("BetSlipGenerator: NotoColorEmoji font loaded successfully.")

        try:
            if os.path.exists(self.LOCK_ICON_PATH):
                self._lock_icon_cache = Image.open(self.LOCK_ICON_PATH).convert("RGBA")
                logger.info(f"Successfully loaded lock icon from {self.LOCK_ICON_PATH}")
            else:
                logger.warning(f"Lock icon image not found at {self.LOCK_ICON_PATH}. Will fallback to emoji.")
        except Exception as e:
            logger.error(f"Error loading lock icon from {self.LOCK_ICON_PATH}: {e}. Will fallback to emoji.")
            self._lock_icon_cache = None

    def _get_text_dimensions(self, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height

    def _draw_header(self, img: Image.Image, draw: ImageDraw.Draw, image_width: int, league_logo: Optional[Image.Image], league: str, bet_type_str: str):
        y_offset = 25
        title_font = self.fonts['font_b_36']
        logo_display_size = (45, 45)
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
                title_x_with_logo = logo_x + logo_display_size[0] + 15
                total_width_with_logo = logo_display_size[0] + 15 + title_w
                if total_width_with_logo < image_width - 2 * self.padding:
                    start_block_x = (image_width - total_width_with_logo) // 2
                    logo_x = start_block_x
                    title_x = logo_x + logo_display_size[0] + 15
                else:
                    title_x = title_x_with_logo
                img.paste(league_logo_resized, (int(logo_x), int(logo_y)), league_logo_resized)
            except Exception as e:
                logger.error(f"Error drawing league logo in header: {e}", exc_info=True)
                title_x = title_x_no_logo
        else:
            title_x = title_x_no_logo
        draw.text((title_x, y_offset), title_text, font=title_font, fill=text_color, anchor="lt")

    def _draw_teams_section(self, img: Image.Image, draw: ImageDraw.Draw, image_width: int, home_team: str, away_team: str, home_logo: Optional[Image.Image], away_logo: Optional[Image.Image]):
        y_base = 85
        logo_size = (120, 120)
        text_y_offset = logo_size[1] + 8
        team_name_font = self.fonts['font_b_24']
        text_color = 'white'
        
        section_width = image_width // 2 - self.padding * 1.5
        home_section_center_x = self.padding + section_width // 2
        away_section_center_x = image_width - self.padding - section_width // 2

        if home_logo:
            try:
                home_logo_resized = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
                home_logo_x = home_section_center_x - logo_size[0] // 2
                if home_logo_resized.mode == 'RGBA':
                    img.paste(home_logo_resized, (int(home_logo_x), int(y_base)), home_logo_resized)
                else:
                    img.paste(home_logo_resized, (int(home_logo_x), int(y_base)))
            except Exception as e:
                logger.error(f"Error pasting home logo: {e}", exc_info=True)
        
        home_name_w, _ = self._get_text_dimensions(home_team, team_name_font)
        home_name_x = home_section_center_x - home_name_w // 2
        draw.text((home_name_x, y_base + text_y_offset), home_team, font=team_name_font, fill=text_color, anchor="lt")

        if away_logo:
            try:
                away_logo_resized = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
                away_logo_x = away_section_center_x - logo_size[0] // 2
                if away_logo_resized.mode == 'RGBA':
                    img.paste(away_logo_resized, (int(away_logo_x), int(y_base)), away_logo_resized)
                else:
                    img.paste(away_logo_resized, (int(away_logo_x), int(y_base)))
            except Exception as e:
                logger.error(f"Error pasting away logo: {e}", exc_info=True)
        
        away_name_w, _ = self._get_text_dimensions(away_team, team_name_font)
        away_name_x = away_section_center_x - away_name_w // 2
        draw.text((away_name_x, y_base + text_y_offset), away_team, font=team_name_font, fill=text_color, anchor="lt")

    def _draw_lock_element(self, img: Image.Image, draw: ImageDraw.Draw, x: int, y: int, size: tuple[int, int], emoji_font: ImageFont.FreeTypeFont, color: str, draw_it: bool = True) -> tuple[int, int, bool]:
        lock_icon_size_for_draw = size
        if self._lock_icon_cache:
            if draw_it:
                try:
                    lock_img_resized = self._lock_icon_cache.resize(lock_icon_size_for_draw, Image.Resampling.LANCZOS)
                    img.paste(lock_img_resized, (int(x), int(y)), lock_img_resized)
                    return lock_icon_size_for_draw[0], lock_icon_size_for_draw[1], True
                except Exception as e:
                    logger.warning(f"Failed to draw cached lock image: {e}. Falling back to emoji if possible.")
            else:
                return lock_icon_size_for_draw[0], lock_icon_size_for_draw[1], True
        
        if self.fonts['emoji_font_24'] != ImageFont.load_default():
            lock_char = "🔒"
            emoji_w, emoji_h = self._get_text_dimensions(lock_char, emoji_font)
            if draw_it:
                emoji_draw_y = y + (lock_icon_size_for_draw[1] - emoji_h) // 2
                draw.text((x, emoji_draw_y), lock_char, font=emoji_font, fill=color, anchor="lt")
            return emoji_w, emoji_h, True

        if draw_it:
            logger.warning("Lock icon image and emoji font both unavailable. No lock element drawn.")
        return 0, 0, False

    def _draw_straight_details(self, draw: ImageDraw.Draw, image_width: int, image_height: int, line: Optional[str], odds: float, units: float, bet_id: str, timestamp: datetime, img: Image.Image):
        y = 100 + 70 + 10 + 24 + 30
        center_x = image_width / 2
        text_color = 'white'; gold_color = '#FFD700'; divider_color = '#606060'

        line_font = self.fonts['font_m_24']; odds_font = self.fonts['font_b_28']
        units_font = self.fonts['font_b_24']; emoji_font = self.fonts['emoji_font_24']
        
        if line:
            line_w, line_h = self._get_text_dimensions(line, line_font)
            y += 10  # Extra space after team names, before line
            draw.text((center_x, y), line, font=line_font, fill=text_color, anchor="mt")
            y += line_h + 24  # More space after line, before separator

        draw.line([(self.padding + 20, y), (image_width - self.padding - 20, y)], fill=divider_color, width=2); y += 18  # More space after separator

        odds_text = self._format_odds_with_sign(odds)
        odds_w, odds_h = self._get_text_dimensions(odds_text, odds_font)
        draw.text((center_x, y), odds_text, font=odds_font, fill=text_color, anchor="mt"); y += odds_h + 12
        
        units_str_display = "Unit" if units == 1.0 else "Units"
        units_display_text = f" To Win {units:.2f} {units_str_display} "
        units_text_part_w, units_text_part_h = self._get_text_dimensions(units_display_text, units_font)

        lock_element_size = (units_text_part_h, units_text_part_h)
        
        dim_lock_w, dim_lock_h, can_draw_lock = self._draw_lock_element(img, draw, 0, 0, lock_element_size, emoji_font, gold_color, draw_it=False)
        
        if can_draw_lock:
            total_units_section_w = dim_lock_w + units_text_part_w + dim_lock_w
        else:
            total_units_section_w = units_text_part_w

        current_x = center_x - total_units_section_w / 2
        lock_drawn_y = y
        
        actual_lock1_w, actual_lock1_h, lock1_drawn = self._draw_lock_element(img, draw, current_x, lock_drawn_y, lock_element_size, emoji_font, gold_color, draw_it=True)
        if lock1_drawn:
            current_x += actual_lock1_w

        text_draw_y = lock_drawn_y + (actual_lock1_h - units_text_part_h) / 2 if lock1_drawn and actual_lock1_h > 0 else lock_drawn_y
        draw.text((current_x, text_draw_y), units_display_text, font=units_font, fill=gold_color, anchor="lt")
        current_x += units_text_part_w
        
        if can_draw_lock:
            self._draw_lock_element(img, draw, current_x, lock_drawn_y, lock_element_size, emoji_font, gold_color, draw_it=True)

        y += units_text_part_h + 30  # Add extra space after units before footer
        return y

    def _draw_parlay_details(self, draw: ImageDraw.Draw, image_width: int, image_height: int, legs: List[Dict], odds: float, units: float, bet_id: str, timestamp: datetime, is_same_game: bool, img: Image.Image, team_logos: List[Optional[Image.Image]]):
        y = 85
        center_x = image_width / 2
        text_color = 'white'; gold_color = '#FFD700'; divider_color = '#606060'
        leg_font = self.fonts['font_m_24']; odds_font = self.fonts['font_b_28']
        units_font = self.fonts['font_b_24']; emoji_font = self.fonts['emoji_font_24']
        team_name_font = self.fonts['font_b_24']
        logo_size = (50, 50)
        logo_spacing = 10

        for i, (leg_data, logo) in enumerate(zip(legs, team_logos)):
            leg_text = f"Leg {i+1}: {leg_data.get('team', 'N/A')} {leg_data.get('line', 'N/A')} ({leg_data.get('league', 'N/A')})"
            leg_w, leg_h = self._get_text_dimensions(leg_text, leg_font)
            
            # Draw team logo
            if logo:
                try:
                    logo_resized = logo.resize(logo_size, Image.Resampling.LANCZOS)
                    logo_x = self.padding
                    logo_y = y + (leg_h - logo_size[1]) // 2
                    if logo_resized.mode == 'RGBA':
                        img.paste(logo_resized, (int(logo_x), int(logo_y)), logo_resized)
                    else:
                        img.paste(logo_resized, (int(logo_x), int(logo_y)))
                except Exception as e:
                    logger.error(f"Error drawing team logo for parlay leg {i+1}: {e}")

            # Draw leg text
            text_x = self.padding + logo_size[0] + logo_spacing
            draw.text((text_x, y), leg_text, font=leg_font, fill=text_color, anchor="lt")
            y += leg_h + 12

            # Draw separator line
            draw.line([(self.padding + 20, y), (image_width - self.padding - 20, y)], fill=divider_color, width=2)
            y += 12

        # Draw total odds
        odds_text = self._format_odds_with_sign(odds)
        odds_w, odds_h = self._get_text_dimensions(odds_text, odds_font)
        draw.text((center_x, y), odds_text, font=odds_font, fill=text_color, anchor="mt")
        y += odds_h + 12

        # Draw units
        units_str_display = "Unit" if units == 1.0 else "Units"
        units_display_text = f" To Win {units:.2f} {units_str_display} "
        units_text_part_w, units_text_part_h = self._get_text_dimensions(units_display_text, units_font)

        lock_element_size = (units_text_part_h, units_text_part_h)
        dim_lock_w, dim_lock_h, can_draw_lock = self._draw_lock_element(img, draw, 0, 0, lock_element_size, emoji_font, gold_color, draw_it=False)
        
        if can_draw_lock:
            total_units_section_w = dim_lock_w + units_text_part_w + dim_lock_w
        else:
            total_units_section_w = units_text_part_w
            
        current_x = center_x - total_units_section_w / 2
        lock_drawn_y = y

        actual_lock1_w, actual_lock1_h, lock1_drawn = self._draw_lock_element(img, draw, current_x, lock_drawn_y, lock_element_size, emoji_font, gold_color, draw_it=True)
        if lock1_drawn:
            current_x += actual_lock1_w
        
        text_draw_y = lock_drawn_y + (actual_lock1_h - units_text_part_h) / 2 if lock1_drawn and actual_lock1_h > 0 else lock_drawn_y
        draw.text((current_x, text_draw_y), units_display_text, font=units_font, fill=gold_color, anchor="lt")
        current_x += units_text_part_w
        
        if can_draw_lock:
            self._draw_lock_element(img, draw, current_x, lock_drawn_y, lock_element_size, emoji_font, gold_color, draw_it=True)

        return y + units_text_part_h + 20  # Return final y for footer

    def _draw_footer(self, draw: ImageDraw.Draw, image_width: int, image_height: int, bet_id: str, timestamp: datetime):
        footer_font = self.fonts['font_m_18']; footer_color = '#CCCCCC'
        _, footer_text_h = self._get_text_dimensions("Test", footer_font)
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
        parlay_legs: Optional[List[Dict]] = None, is_same_game: bool = False,
        team_logo_paths: Optional[List[str]] = None
    ) -> Optional[Image.Image]:
        try:
            logger.info(f"Generating bet slip - Home:'{home_team}', Away:'{away_team}', League:'{league}', Type:{bet_type}")
            width = 600
            # Dynamic height for parlays
            if bet_type.lower() == "parlay" and parlay_legs:
                num_legs = len(parlay_legs)
                height = 200 + num_legs * 80 + 100  # Base height + 80 per leg + extra for odds/units/footer
            else:
                height = 400  # Fixed height for straight bets
            
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
                    
                    if ratio_w > ratio_h:
                        new_w = width
                        new_h = int(bg_h * ratio_w)
                        resized_bg = guild_bg_image_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        crop_y = (new_h - height) // 2
                        final_bg_to_paste = resized_bg.crop((0, crop_y, width, crop_y + height))
                    else:
                        new_h = height
                        new_w = int(bg_w * ratio_h)
                        resized_bg = guild_bg_image_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        crop_x = (new_w - width) // 2
                        final_bg_to_paste = resized_bg.crop((crop_x, 0, crop_x + width, height))

                    img.paste(final_bg_to_paste, (0,0), final_bg_to_paste)
                    logger.info("Applied guild background with 50% transparency.")
                except Exception as bg_err:
                    logger.error(f"Error processing guild background: {bg_err}", exc_info=True)
            
            draw = ImageDraw.Draw(img)
            
            league_logo_pil = None if bet_type.lower() == "parlay" else self._load_league_logo(league)
            home_logo_pil = None
            away_logo_pil = None
            team_logos = []

            if bet_type.lower() == "parlay" and parlay_legs and team_logo_paths:
                for logo_path in team_logo_paths:
                    try:
                        logo = Image.open(logo_path).convert("RGBA")
                        team_logos.append(logo)
                    except Exception as e:
                        logger.warning(f"Failed to load team logo at {logo_path}: {e}")
                        default_logo = Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
                        team_logos.append(default_logo)
            else:
                home_logo_pil = self._load_team_logo(home_team, league)
                away_logo_pil = self._load_team_logo(away_team, league)
            
            default_pil_logo = None
            if os.path.exists(self.DEFAULT_LOGO_PATH):
                try: default_pil_logo = Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA")
                except Exception as e: logger.error(f"Failed to load default logo: {e}")
            
            if not league_logo_pil and default_pil_logo and bet_type.lower() != "parlay":
                league_logo_pil = default_pil_logo.copy()
            if not home_logo_pil and default_pil_logo:
                home_logo_pil = default_pil_logo.copy()
            if not away_logo_pil and default_pil_logo:
                away_logo_pil = default_pil_logo.copy()

            self._draw_header(img, draw, width, league_logo_pil, league, bet_type)
            
            if bet_type.lower() == "parlay" and parlay_legs:
                y_end = self._draw_parlay_details(draw, width, height, parlay_legs, odds, units, bet_id, timestamp, is_same_game, img, team_logos)
                # Adjust footer to sit below all content
                self._draw_footer(draw, width, y_end + self.padding, bet_id, timestamp)
            else:
                self._draw_teams_section(img, draw, width, home_team, away_team, home_logo_pil, away_logo_pil)
                y_end = self._draw_straight_details(draw, width, height, line, odds, units, bet_id, timestamp, img)
                self._draw_footer(draw, width, y_end + self.padding, bet_id, timestamp)

            logger.info(f"Bet slip generated OK for bet ID: {bet_id}")
            return img.convert("RGB")
            
        except Exception as e:
            logger.error(f"Error in generate_bet_slip: {str(e)}", exc_info=True)
            try:
                err_img = Image.new('RGB', (600,100), "darkred")
                err_draw = ImageDraw.Draw(err_img)
                err_draw.text((10,10), f"Error creating slip:\n{str(e)[:100]}", font=ImageFont.load_default(), fill="white")
                return err_img
            except Exception as final_err:
                logger.error(f"Fallback image failed: {final_err}")
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
                logger.warning(f"Sport category not found for league '{league}'. Attempting to use default logo.")
                return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            
            fname = f"{league.lower().replace(' ', '_')}.png"
            logo_dir = os.path.join(self.LEAGUE_LOGO_BASE_DIR, sport, league.upper())
            logo_path = os.path.join(logo_dir, fname); absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info("Loading league logo - League:'%s', Resolved Sport Category: '%s', Path:'%s', Exists:%s", league, sport, absolute_logo_path, file_exists)
            
            logo = None
            if file_exists:
                try: logo = Image.open(absolute_logo_path).convert("RGBA")
                except Exception as e: logger.error(f"Error opening league logo {absolute_logo_path}: {e}")
            
            if logo:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    oldest_key = min(self._logo_cache, key=lambda k: self._logo_cache[k][1])
                    del self._logo_cache[oldest_key]
                self._logo_cache[cache_key] = (logo.copy(), now)
                return logo.copy()
                
            logger.warning(f"No logo found for league {league} (path: {absolute_logo_path}). Attempting to use default logo.")
            return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
        except Exception as e:
            logger.error(f"Error in _load_league_logo for {league}: {e}", exc_info=True)
            try: return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            except Exception as def_err: logger.error(f"Error loading default logo during fallback: {def_err}")
            return None

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        try:
            sport = get_sport_category_for_path(league.upper())
            if not sport:
                logger.error(f"No sport category determined for league: {league} (when loading team: {team_name})")
                return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            
            team_dir = self._ensure_team_dir_exists(league)
            if not team_dir:
                return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            
            normalized_team_name = normalize_team_name(team_name)
            logo_path = os.path.join(team_dir, f"{normalized_team_name}.png")
            absolute_logo_path = os.path.abspath(logo_path)
            logger.info(f"Attempting to load team logo: Team='{team_name}', Normalized='{normalized_team_name}', League='{league}', Sport='{sport}', Path='{absolute_logo_path}'")

            if os.path.exists(absolute_logo_path):
                return Image.open(absolute_logo_path).convert("RGBA")
            else:
                logger.warning(f"Team logo not found: {absolute_logo_path}. Using default logo.")
                return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
        except Exception as e:
            logger.error(f"Error in _load_team_logo for {team_name} (league {league}): {e}", exc_info=True)
            try:
                return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA") if os.path.exists(self.DEFAULT_LOGO_PATH) else None
            except Exception as def_err:
                logger.error(f"Error loading default team logo during fallback: {def_err}")
            return None

    def _ensure_team_dir_exists(self, league: str) -> Optional[str]:
        try:
            sport = get_sport_category_for_path(league.upper())
            if not sport:
                logger.error(f"No sport category for league: {league} in _ensure_team_dir_exists")
                return None
            team_dir = os.path.join(self.LEAGUE_TEAM_BASE_DIR, sport, league.upper())
            os.makedirs(team_dir, exist_ok=True)
            return team_dir
        except Exception as e:
            logger.error(f"Error ensuring team directory for league {league} (sport: {sport}): {e}", exc_info=True)
            return None
    
    def _normalize_team_name(self, team_name: str) -> str:
        return normalize_team_name(team_name)

    def _format_odds_with_sign(self, odds: float) -> str:
        return f"+{int(odds)}" if odds > 0 else str(int(odds))
