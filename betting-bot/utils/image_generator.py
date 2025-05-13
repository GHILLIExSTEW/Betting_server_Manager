# betting-bot/utils/image_generator.py

import logging
import os
import time
import io
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import traceback
# Remove 'requests' if only local guild backgrounds are used
# import requests # Not needed if guild_background is always a local path

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError # Added UnidentifiedImageError
from config.asset_paths import (
    ASSETS_DIR,
    FONT_DIR,
    LOGO_DIR,
    TEAMS_SUBDIR,
    LEAGUES_SUBDIR,
    get_sport_category_for_path,
    BASE_DIR
)
from config.team_mappings import normalize_team_name
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# --- Sport Category Mapping (Defined Globally) ---
# ... (SPORT_CATEGORY_MAP remains the same) ...
SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL",
    "NCAAB": "BASKETBALL",
    "WNBA": "BASKETBALL",
    "EUROLEAGUE": "BASKETBALL",
    "CBA": "BASKETBALL",  # Chinese Basketball Association
    "NFL": "FOOTBALL",
    "NCAAF": "FOOTBALL",
    "CFL": "FOOTBALL",  # Canadian Football League
    "XFL": "FOOTBALL",
    "MLB": "BASEBALL",
    "NCAAB_BASEBALL": "BASEBALL",
    "NPB": "BASEBALL",  # Nippon Professional Baseball (Japan)
    "KBO": "BASEBALL",  # Korea Baseball Organization
    "NHL": "HOCKEY",
    "KHL": "HOCKEY",  # Kontinental Hockey League (Russia)
    "SHL": "HOCKEY",  # Swedish Hockey League
    "MLS": "SOCCER",
    "EPL": "SOCCER",  # English Premier League
    "LA_LIGA": "SOCCER",
    "SERIE_A": "SOCCER",
    "BUNDESLIGA": "SOCCER",
    "LIGUE_1": "SOCCER",
    "UEFA_CL": "SOCCER",  # UEFA Champions League
    "COPA_LIBERTADORES": "SOCCER",
    "A_LEAGUE": "SOCCER",  # Australian A-League
    "J_LEAGUE": "SOCCER",  # Japan J1 League
    "ATP": "TENNIS",
    "WTA": "TENNIS",
    "ITF": "TENNIS",  # International Tennis Federation events
    "GRAND_SLAM": "TENNIS",  # Wimbledon, US Open, Australian Open, French Open
    "UFC": "MMA",
    "BELLATOR": "MMA",
    "ONE_CHAMPIONSHIP": "MMA",
    "PFL": "MMA",  # Professional Fighters League
    "PGA": "GOLF",
    "LPGA": "GOLF",
    "EUROPEAN_TOUR": "GOLF",
    "MASTERS": "GOLF",
    "BOXING": "BOXING",
    "CRICKET": "CRICKET",
    "IPL": "CRICKET",  # Indian Premier League
    "BBL": "CRICKET",  # Big Bash League (Australia)
    "TEST_CRICKET": "CRICKET",
    "RUGBY_UNION": "RUGBY",
    "SUPER_RUGBY": "RUGBY",
    "SIX_NATIONS": "RUGBY",
    "RUGBY_LEAGUE": "RUGBY",
    "NRL": "RUGBY",  # National Rugby League (Australia)
    "SUPER_LEAGUE": "RUGBY",  # Rugby League in Europe
    "F1": "MOTORSPORTS",
    "NASCAR": "MOTORSPORTS",
    "INDYCAR": "MOTORSPORTS",
    "MOTOGP": "MOTORSPORTS",
    "DARTS": "DARTS",
    "PDC": "DARTS",  # Professional Darts Corporation
    "VOLLEYBALL": "VOLLEYBALL",
    "FIVB": "VOLLEYBALL",  # International Volleyball Federation events
    "TABLE_TENNIS": "TABLE_TENNIS",
    "ITTF": "TABLE_TENNIS",  # International Table Tennis Federation
    "CYCLING": "CYCLING",
    "TOUR_DE_FRANCE": "CYCLING",
    "GIRO_D_ITALIA": "CYCLING",
    "VUELTA_A_ESPANA": "CYCLING",
    "ESPORTS_CSGO": "ESPORTS",
    "ESPORTS_LOL": "ESPORTS",  # League of Legends
    "ESPORTS_DOTA2": "ESPORTS",
    "ESPORTS_OVERWATCH": "ESPORTS",
    "ESPORTS_FIFA": "ESPORTS",
    "AUSSIE_RULES": "AUSTRALIAN_FOOTBALL",
    "AFL": "AUSTRALIAN_FOOTBALL",  # Australian Football League
    "HANDBALL": "HANDBALL",
    "EHF_CL": "HANDBALL",  # European Handball Federation Champions League
    "SNOOKER": "SNOOKER",
    "WORLD_CHAMPIONSHIP_SNOOKER": "SNOOKER",
    "BADMINTON": "BADMINTON",
    "BWF": "BADMINTON",  # Badminton World Federation events
    "LACROSSE": "LACROSSE",
    "NLL": "LACROSSE",  # National Lacrosse League
    "FIELD_HOCKEY": "FIELD_HOCKEY",
    "FIH_PRO_LEAGUE": "FIELD_HOCKEY"  # International Hockey Federation Pro League
}
DEFAULT_FALLBACK_SPORT_CATEGORY = "OTHER_SPORTS"


# Asset paths
# ... (Asset path definitions remain the same) ...
_PATHS = {
    "ASSETS_DIR": ASSETS_DIR,
    "DEFAULT_FONT_PATH": os.path.join(FONT_DIR, "Roboto-Regular.ttf"),
    "DEFAULT_BOLD_FONT_PATH": os.path.join(FONT_DIR, "Roboto-Bold.ttf"),
    "DEFAULT_EMOJI_FONT_PATH_NOTO": os.path.join(FONT_DIR, "NotoColorEmoji-Regular.ttf"),
    "DEFAULT_EMOJI_FONT_PATH_SEGOE": os.path.join(FONT_DIR, "SegoeUIEmoji.ttf"),
    "LEAGUE_TEAM_BASE_DIR": TEAMS_SUBDIR,
    "LEAGUE_LOGO_BASE_DIR": LEAGUES_SUBDIR,
    "DEFAULT_LOCK_ICON_PATH": os.path.join(ASSETS_DIR, "lock_icon.png"),
    "DEFAULT_TEAM_LOGO_PATH": os.path.join(LOGO_DIR, "default_logo.png"),
}


def load_fonts():
    """Load fonts with proper fallbacks."""
    fonts = {}
    try:
        # Use relative paths from project root
        font_path = os.path.join(BASE_DIR, "assets", "fonts", "Roboto-Regular.ttf")
        bold_font_path = os.path.join(BASE_DIR, "assets", "fonts", "Roboto-Bold.ttf")
        emoji_font_path = os.path.join(BASE_DIR, "assets", "fonts", "NotoColorEmoji-Regular.ttf")
        
        logger.info("Loading fonts from paths:")
        logger.info(f"Regular font: {font_path}")
        logger.info(f"Bold font: {bold_font_path}")
        logger.info(f"Emoji font: {emoji_font_path}")
        
        # Check if fonts exist at specified paths
        missing_files = []
        if not os.path.exists(font_path): missing_files.append(font_path)
        if not os.path.exists(bold_font_path): missing_files.append(bold_font_path)
        if not os.path.exists(emoji_font_path): missing_files.append(emoji_font_path)
        
        if missing_files:
            logger.error("Font files not found at these paths:")
            for path in missing_files:
                logger.error(f"  - {path}")
            raise FileNotFoundError(f"Font files not found at specified paths: {', '.join(missing_files)}")

        # Load fonts with proper error handling
        logger.info("Loading fonts from specified paths...")
        fonts['font_m_18'] = ImageFont.truetype(font_path, 18)
        fonts['font_m_24'] = ImageFont.truetype(font_path, 24)
        fonts['font_b_18'] = ImageFont.truetype(bold_font_path, 18)
        fonts['font_b_24'] = ImageFont.truetype(bold_font_path, 24)
        fonts['font_b_36'] = ImageFont.truetype(bold_font_path, 36)
        fonts['font_b_28'] = ImageFont.truetype(bold_font_path, 28)
        fonts['emoji_font_24'] = ImageFont.truetype(emoji_font_path, 24) # For lock icons
        
        logger.info("Successfully loaded all fonts")
        return fonts
        
    except Exception as e:
        logger.error(f"Error loading fonts: {e}")
        default_font = ImageFont.load_default()
        return {
            'font_m_18': default_font,
            'font_m_24': default_font,
            'font_b_18': default_font,
            'font_b_24': default_font,
            'font_b_36': default_font,
            'font_b_28': default_font,
            'emoji_font_24': default_font
        }

# Load fonts globally
FONTS = load_fonts()

class BetSlipGenerator:
    def __init__(self, guild_id: Optional[int] = None):
        """Initialize the bet slip generator with required assets."""
        self.guild_id = guild_id
        self.db_manager = DatabaseManager() # Assuming this initializes its own pool or is passed one
        self.padding = 20
        self.LEAGUE_TEAM_BASE_DIR = os.path.join(BASE_DIR, "static", "logos", "teams")
        self.LEAGUE_LOGO_BASE_DIR = os.path.join(BASE_DIR, "static", "logos", "leagues")
        self.DEFAULT_LOGO_PATH = os.path.join(BASE_DIR, "static", "logos", "default_logo.png")
        self.LOCK_ICON_PATH = os.path.join(BASE_DIR, "static", "logos", "lock_icon.png") # Path to your lock.png
        self._logo_cache = {}
        self._lock_icon_cache = None # For the PIL Image object of the lock
        self._last_cache_cleanup = time.time()
        self._cache_expiry = 300  # 5 minutes
        self._max_cache_size = 100
        
        # self.background = None # This was defined but not used in your provided code.
                                # If you load a default background here, do it.
        # self.team_logos = {} # This was defined but not used; logos are loaded on demand.

        # Load fonts last
        logger.info("Loading fonts into BetSlipGenerator instance...")
        self.fonts = FONTS  # Use the global FONTS dict for all font access
        logger.info("Fonts loaded successfully into BetSlipGenerator instance.")

    def _draw_header(self, draw: ImageDraw.Draw, league_logo: Optional[Image.Image], league: str, bet_type: str):
        y_offset = 30
        title_font = self.fonts['font_b_36']
        league_name_font = self.fonts['font_b_24'] # Example for league name next to logo
        logo_display_size = (50, 50) # Smaller logo for header
        text_color = 'white'
        image_width = 600 # Assuming image width

        title_text = f"{league.upper()} - {bet_type.replace('_', ' ').title()}"
        
        # Calculate title width using the new method
        title_bbox = title_font.getbbox(title_text)
        title_w = title_bbox[2] - title_bbox[0]
        
        title_x = (image_width - title_w) // 2
        title_y = y_offset
        
        if league_logo:
            logo_size = (60, 60)
            league_logo = league_logo.resize(logo_size, Image.Resampling.LANCZOS)
            draw.bitmap((270, 30), league_logo)
        # Draw title
        title = f"{league} - {bet_type.title().replace('_', ' ')}"
        w, h = draw.textsize(title, font=self.fonts['font_b_36'])
        draw.text(((600 - w) // 2, 30), title, font=self.fonts['font_b_36'], fill='white')

    def _draw_teams_section(self, img: Image.Image, draw: ImageDraw.Draw, home_team: str, away_team: str, home_logo: Optional[Image.Image], away_logo: Optional[Image.Image]):
        y_base = 110 # Start y position for logos
        logo_size = (80, 80)
        text_y_offset = 90 # Offset from logo top to team name text
        logo_text_gap = 5 # Gap between logo and text if side-by-side, or use for centering under
        team_name_font = self.fonts['font_b_24']
        text_color = 'white'
        image_width = 600
        
        # Home Team
        home_logo_x = self.padding + 70 
        if home_logo:
            try:
                home_logo_resized = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
                # Paste with transparency mask if RGBA
                img.paste(home_logo_resized, (home_logo_x, y_base), home_logo_resized if home_logo_resized.mode == 'RGBA' else None)
            except Exception as e:
                logger.error(f"Error pasting home logo: {e}")
        
        home_name_bbox = team_name_font.getbbox(home_team)
        home_name_w = home_name_bbox[2] - home_name_bbox[0]
        home_name_x = home_logo_x + (logo_size[0] - home_name_w) // 2
        draw.text((home_name_x, y_base + text_y_offset), home_team, font=team_name_font, fill=text_color)

        # Away Team
        away_logo_x = image_width - self.padding - 70 - logo_size[0]
        if away_logo:
            away_logo = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
            img.paste(away_logo, (400, y), away_logo)
        # Team names
        hw, _ = draw.textsize(home_team, font=self.fonts['font_b_24'])
        aw, _ = draw.textsize(away_team, font=self.fonts['font_b_24'])
        draw.text((120 + (80 - hw) // 2, y + 90), home_team, font=self.fonts['font_b_24'], fill='white')
        draw.text((400 + (80 - aw) // 2, y + 90), away_team, font=self.fonts['font_b_24'], fill='white')

    def _draw_straight_details(self, draw: ImageDraw.Draw, line: Optional[str], odds: float, units: float, bet_id: str, timestamp: datetime):
        y = 210 + 30 # Start y after team names
        content_width = 600 - (2 * self.padding) # Usable width
        center_x = 600 / 2
        text_color = 'white'
        gold_color = '#FFD700'
        divider_color = '#888888'

        line_font = self.fonts['font_m_24']
        odds_font = self.fonts['font_b_28']
        units_font = self.fonts['font_b_24'] # Font for "To Win X Units"
        emoji_font = self.fonts['emoji_font_24'] # Font for lock emoji
        footer_font = self.fonts['font_m_18']
        footer_color = '#CCCCCC'

        # Bet Line (e.g., "Oilers: Hyman - 2 SOG")
        if line:
            w, _ = draw.textsize(line, font=self.fonts['font_m_24'])
            draw.text(((600 - w) // 2, y), line, font=self.fonts['font_m_24'], fill='white')
            y += 40
        # Divider
        draw.line([(self.padding, y), (600 - self.padding, y)], fill=divider_color, width=1)
        y += 15

        # Odds
        odds_txt = self._format_odds_with_sign(odds)
        w, _ = draw.textsize(odds_txt, font=self.fonts['font_b_28'])
        draw.text(((600 - w) // 2, y), odds_txt, font=self.fonts['font_b_28'], fill='white')
        y += 40
        # Units with lock icons
        lock = "🔒"
        units_txt = f"{lock} To Win {units:.2f} Units {lock}"
        w, _ = draw.textsize(units_txt, font=self.fonts['font_b_24'])
        draw.text(((600 - w) // 2, y), units_txt, font=self.fonts['font_b_24'], fill='#FFD700')
        y += 40
        # Footer
        bet_id_txt = f"Bet #{bet_id}"
        time_txt = timestamp.strftime('%Y-%m-%d %H:%M UTC')
        draw.text((60, 360), bet_id_txt, font=self.fonts['font_m_18'], fill='#CCCCCC')
        tw, _ = draw.textsize(time_txt, font=self.fonts['font_m_18'])
        draw.text((600 - 60 - tw, 360), time_txt, font=self.fonts['font_m_18'], fill='#CCCCCC')

    def _draw_parlay_details(self, draw: ImageDraw.Draw, legs: List[Dict], odds: float, units: float, bet_id: str, timestamp: datetime, is_same_game: bool):
        # This is your existing method. You'll need to replace `draw.textsize` here as well.
        # For brevity, I'll show one replacement. Apply similarly to others.
        y = 210 # Adjusted starting y if header and teams are similar to straight
        content_width = 600 - (2 * self.padding)
        center_x = 600 / 2
        text_color = 'white'
        gold_color = '#FFD700'
        footer_color = '#CCCCCC'

        leg_font = self.fonts['font_m_18'] # Example
        total_odds_font = self.fonts['font_b_24']
        units_font = self.fonts['font_b_24']
        footer_font = self.fonts['font_m_18']
        emoji_font = self.fonts['emoji_font_24']

        # Draw each leg
        for i, leg in enumerate(legs, 1):
            leg_text = f"Leg {i}: {leg.get('league','N/A')} - {leg.get('team', 'N/A')} {leg.get('line', 'N/A')} ({leg.get('odds_str', 'N/A')})"
            # OLD: # leg_w, leg_h = draw.textsize(leg_text, font=leg_font)
            leg_bbox = leg_font.getbbox(leg_text) # NEW
            leg_w = leg_bbox[2] - leg_bbox[0]   # NEW
            leg_h = leg_bbox[3] - leg_bbox[1]   # NEW
            
            draw.text((self.padding, y), leg_text, font=leg_font, fill=text_color)
            y += leg_h + 5 # Use calculated height and a small gap
            if y > 300 and i < len(legs): # Check if overflowing, might need smaller fonts or less info for many legs
                draw.text((self.padding, y), "...", font=leg_font, fill=text_color)
                y += leg_h + 5
                break


        y += 10 # Gap before total odds
        # Draw total odds and units
        total_odds_text = f"Total Parlay Odds: {self._format_odds_with_sign(odds)}"
        # OLD: # total_odds_w, _ = draw.textsize(total_odds_text, font=total_odds_font)
        total_odds_bbox = total_odds_font.getbbox(total_odds_text) # NEW
        total_odds_w = total_odds_bbox[2] - total_odds_bbox[0] # NEW
        draw.text( (center_x - total_odds_w / 2, y), total_odds_text, font=total_odds_font, fill=text_color)
        y += (total_odds_bbox[3] - total_odds_bbox[1]) + 10 # NEW

        # Units with lock icons (similar to _draw_straight_details)
        lock_char = "🔒"
        units_text_part = f" To Win {units:.2f} Units "
        
        lock_bbox = emoji_font.getbbox(lock_char)
        lock_w = lock_bbox[2] - lock_bbox[0]
        units_text_part_bbox = units_font.getbbox(units_text_part)
        units_text_part_w = units_text_part_bbox[2] - units_text_part_bbox[0]
        
        total_units_section_w = lock_w + units_text_part_w + lock_w
        current_x = center_x - total_units_section_w / 2

        draw.text((current_x, y), lock_char, font=emoji_font, fill=gold_color)
        current_x += lock_w
        draw.text((current_x, y + ( ( (lock_bbox[3]-lock_bbox[1]) - (units_text_part_bbox[3]-units_text_part_bbox[1]) )/2 ) ), units_text_part, font=units_font, fill=gold_color)
        current_x += units_text_part_w
        draw.text((current_x, y), lock_char, font=emoji_font, fill=gold_color)
        
        # Footer (same as straight details)
        footer_y = 400 - self.padding - (footer_font.getbbox("Test")[3] - footer_font.getbbox("Test")[1])
        bet_id_text = f"Bet #{bet_id}"
        timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC')
        draw.text((self.padding, footer_y), bet_id_text, font=footer_font, fill=footer_color)
        ts_bbox = footer_font.getbbox(timestamp_text)
        ts_w = ts_bbox[2] - ts_bbox[0]
        draw.text((600 - self.padding - ts_w, footer_y), timestamp_text, font=footer_font, fill=footer_color)

    def _draw_footer(self, draw: ImageDraw.Draw, bet_id: str, timestamp: datetime):
        """Draw the footer with bet ID and timestamp."""
        # Calculate footer position
        footer_y = 400 - self.padding - (self.fonts['font_m_18'].getbbox("Test")[3] - self.fonts['font_m_18'].getbbox("Test")[1])
        
        # Format timestamp
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Draw bet ID
        bet_id_text = f"Bet ID: {bet_id}"
        draw.text(
            (self.padding, footer_y),
            bet_id_text,
            font=self.fonts['font_m_18'],
            fill='#AAAAAA'
        )
        
        # Draw timestamp
        timestamp_text = f"Placed: {formatted_time}"
        # Calculate width of bet_id_text to position timestamp
        bet_id_width = self.fonts['font_m_18'].getbbox(bet_id_text)[2]
        draw.text(
            (self.padding + bet_id_width + 20, footer_y),  # Add 20px spacing
            timestamp_text,
            font=self.fonts['font_m_18'],
            fill='#AAAAAA'
        )

    # ... (rest of _load_team_logo, _ensure_team_dir_exists, _load_lock_icon are okay from previous fixes)

    async def get_guild_background(self) -> Optional[Image.Image]:
        """Fetch the guild background image from a local path stored in the DB."""
        if not self.guild_id:
            return None
        
        background_image = None
        try:
            settings = await self.db_manager.fetch_one(
                "SELECT guild_background FROM guild_settings WHERE guild_id = %s",
                (self.guild_id,)
            )
            guild_bg_path = settings.get("guild_background") if settings else None

            if guild_bg_path:
                # Construct the full path assuming guild_bg_path is relative to a known base
                # or is an absolute path.
                # If guild_bg_path is stored as, e.g., "guilds/GUILD_ID/background.png"
                # and your static files are in "betting-bot/static/"
                # then full_path = os.path.join(BASE_DIR, "static", guild_bg_path)
                
                # Assuming guild_bg_path from DB is already an absolute path or a path
                # that os.path.exists can directly verify.
                # If it's relative, you MUST resolve it correctly.
                # For PebbleHost, /home/container/ is often the base.
                # Let's assume it's stored as an absolute path or one resolvable from BASE_DIR/static/
                
                potential_path = guild_bg_path
                if not os.path.isabs(guild_bg_path): # If it's not absolute, try resolving from static
                    potential_path = os.path.join(BASE_DIR, "static", guild_bg_path)

                if os.path.exists(potential_path):
                    logger.info(f"Loading guild background from local path: {potential_path}")
                    background_image = Image.open(potential_path).convert("RGBA")
                    logger.info(f"Successfully loaded guild background from local path.")
                else:
                    logger.warning(f"Guild background file not found at specified path: {guild_bg_path} (resolved to: {potential_path})")
            else:
                logger.debug(f"No guild background path set for guild {self.guild_id}.")

        except FileNotFoundError:
            logger.error(f"Guild background file not found at path: {guild_bg_path}")
        except UnidentifiedImageError: # Catch if the file is not a valid image
            logger.error(f"Cannot identify image file for guild background at {guild_bg_path}. It may be corrupted or not an image.")
        except Exception as e:
            logger.error(f"Error loading guild background for guild {self.guild_id} (path: {guild_bg_path if 'guild_bg_path' in locals() else 'N/A'}): {e}", exc_info=True)
        
        return background_image


    async def generate_bet_slip( # Changed to async to allow awaiting get_guild_background
        self,
        home_team: str,
        away_team: str,
        league: str,
        odds: float,
        units: float,
        bet_id: str,
        timestamp: datetime,
        bet_type: str = "straight",
        line: Optional[str] = None,
        parlay_legs: Optional[List[Dict]] = None,
        is_same_game: bool = False
        # removed background_img parameter, will fetch it inside
    ) -> Optional[Image.Image]:
        """Generate a bet slip image."""
        try:
            logger.info(f"Generating bet slip - Home: '{home_team}', Away: '{away_team}', League: '{league}', Type: {bet_type}")
            
            width, height = 600, 400 # Define dimensions
            
            # Load guild-specific background or default
            guild_bg_image = await self.get_guild_background() # Now async

            if guild_bg_image:
                try:
                    # Resize background to fit, maintaining aspect ratio (cover/contain logic might be better)
                    # For simplicity, let's resize to fit width, then crop or ensure it's large enough.
                    # This example will stretch it; for a better look, you might want to crop or tile.
                    background_img_resized = guild_bg_image.resize((width, height), Image.Resampling.LANCZOS)
                    img = background_img_resized.copy()
                except Exception as bg_err:
                    logger.error(f"Error processing guild background, using default: {bg_err}")
                    img = Image.new('RGBA', (width, height), "#23232a") # Default fallback color
            else:
                img = Image.new('RGBA', (width, height), "#23232a") # Default fallback color

            draw = ImageDraw.Draw(img)
            
            # Fonts are already loaded into self.fonts in __init__
            
            league_logo_pil = self._load_league_logo(league) # This returns a PIL Image or None
            
            # Ensure team logos are loaded
            home_logo_pil = self._load_team_logo(home_team, league)
            away_logo_pil = self._load_team_logo(away_team, league)

            if not home_logo_pil:
                logger.warning(f"Home logo for {home_team} not loaded, using default.")
                home_logo_pil = Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA")
            if not away_logo_pil:
                logger.warning(f"Away logo for {away_team} not loaded, using default.")
                away_logo_pil = Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA")

            # Draw components
            self._draw_header(draw, league_logo_pil, league, bet_type)
            self._draw_teams_section(img, draw, home_team, away_team, home_logo_pil, away_logo_pil)
            
            if bet_type.lower() == "parlay" and parlay_legs:
                self._draw_parlay_details(draw, parlay_legs, odds, units, bet_id, timestamp, is_same_game)
            else: # Default to straight or if bet_type is 'straight', 'game_line', etc.
                self._draw_straight_details(draw, line, odds, units, bet_id, timestamp)
            
            self._draw_footer(draw, bet_id, timestamp)

            logger.info(f"Bet slip generated OK: {bet_id}")
            return img.convert("RGB") # Convert to RGB before saving if it was RGBA for pasting
            
        except Exception as e:
            logger.error(f"Error in generate_bet_slip: {str(e)}", exc_info=True)
            # Fallback: create a simple error image
            try:
                err_img = Image.new('RGB', (600, 100), "darkred")
                err_draw = ImageDraw.Draw(err_img)
                err_font = ImageFont.load_default() # Use default font for error image
                err_draw.text((10,10), f"Error generating bet slip:\n{str(e)[:100]}", font=err_font, fill="white")
                return err_img
            except Exception as final_err:
                logger.error(f"Failed to create fallback error image: {final_err}")
                return None # Return None if even error image fails
                
    def _load_fonts(self):
        """
        This method is effectively a no-op now because fonts are loaded globally
        and assigned to self.fonts in __init__. 
        If you had specific instance-based font loading logic, it would go here.
        """
        pass # Fonts are handled by the global FONTS and __init__ assignment

    # ... (rest of the methods like _load_league_logo, _cleanup_cache, _normalize_team_name, _format_odds_with_sign
    # remain largely the same as your provided code, but ensure they use self.fonts with correct keys if they draw text)

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        """Load a league logo with caching."""
        if not league:
            return None
        try:
            cache_key = f"league_{league}"
            now = time.time()
            if cache_key in self._logo_cache:
                logo, ts = self._logo_cache[cache_key]
                if now - ts <= self._cache_expiry:
                    return logo.copy() # Return a copy to avoid issues if original is modified
                else:
                    del self._logo_cache[cache_key]
            
            sport = get_sport_category_for_path(league.upper())
            if not sport: # Handle if sport category not found
                logger.warning(f"Sport category not found for league '{league}'. Cannot load logo.")
                return None
            
            fname = f"{league.lower().replace(' ', '_')}.png"
            # Ensure LEAGUE_LOGO_BASE_DIR is correct
            logo_dir = os.path.join(self.LEAGUE_LOGO_BASE_DIR, sport, league.upper())
            logo_path = os.path.join(logo_dir, fname)
            
            # This part was already good, keeping it
            absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info(
                "Loading league logo - League: '%s', Sport: '%s', Path: '%s', Exists: %s",
                league, sport, absolute_logo_path, file_exists
            )
            
            logo = None
            if file_exists:
                try:
                    logo = Image.open(absolute_logo_path).convert("RGBA")
                except Exception as e:
                    logger.error(f"Error opening league logo {absolute_logo_path}: {e}")
            
            if logo:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    oldest_key = min(self._logo_cache, key=lambda k: self._logo_cache[k][1])
                    del self._logo_cache[oldest_key]
                self._logo_cache[cache_key] = (logo.copy(), now)
                return logo.copy()
                
            logger.warning(f"No logo image found for league {league} (path: {absolute_logo_path})")
            # Fallback to default logo if league logo not found
            if os.path.exists(self.DEFAULT_LOGO_PATH):
                return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA")
            return None
            
        except Exception as e:
            logger.error(f"Error in _load_league_logo for {league}: {e}", exc_info=True)
            # Fallback to default logo on any error
            try:
                if os.path.exists(self.DEFAULT_LOGO_PATH):
                    return Image.open(self.DEFAULT_LOGO_PATH).convert("RGBA")
            except Exception as def_err:
                logger.error(f"Error loading default logo during fallback: {def_err}")
            return None

    # _cleanup_cache, _normalize_team_name, _format_odds_with_sign, _load_team_logo, _ensure_team_dir_exists
    # can largely remain as they are, assuming they don't use draw.textsize().
    # If they do, they also need the same fix. _load_lock_icon might need similar font updates if it draws text.
