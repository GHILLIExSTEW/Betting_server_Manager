# betting-bot/utils/image_generator.py

import logging
import os
import time
import io
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import traceback
import requests

from PIL import Image, ImageDraw, ImageFont
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
        fonts['emoji_font_24'] = ImageFont.truetype(emoji_font_path, 24)
        
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
        self.db_manager = DatabaseManager()
        self.padding = 20
        self.LEAGUE_TEAM_BASE_DIR = os.path.join(BASE_DIR, "static", "logos", "teams")
        self.LEAGUE_LOGO_BASE_DIR = os.path.join(BASE_DIR, "static", "logos", "leagues")
        self.DEFAULT_LOGO_PATH = os.path.join(BASE_DIR, "static", "logos", "default_logo.png")
        self.LOCK_ICON_PATH = os.path.join(BASE_DIR, "static", "logos", "lock_icon.png")
        
        self._logo_cache = {}
        self._lock_icon_cache = None
        self._last_cache_cleanup = time.time()
        self._cache_expiry = 300  # 5 minutes
        self._max_cache_size = 100
        
        self.background = None
        self.team_logos = {}
        
        # Load fonts last
        logger.info("Loading fonts into BetSlipGenerator instance...")
        # Make the global FONTS dict available as self.fonts
        self.fonts = FONTS
        
        # Individual font assignments for direct access
        self.font_m_18 = FONTS['font_m_18']
        self.font_m_24 = FONTS['font_m_24']
        self.font_b_18 = FONTS['font_b_18']
        self.font_b_24 = FONTS['font_b_24']
        self.font_b_36 = FONTS['font_b_36']
        self.font_b_28 = FONTS['font_b_28']
        self.emoji_font_24 = FONTS['emoji_font_24']
        logger.info("Fonts loaded successfully into BetSlipGenerator instance")

    def _draw_header(self, draw: ImageDraw.Draw, league_logo: Image.Image, league: str):
        """Draw the header section of the bet slip."""
        # Draw league logo
        if league_logo:
            logo_size = (100, 100)
            league_logo = league_logo.resize(logo_size, Image.Resampling.LANCZOS)
            draw.bitmap((self.padding, self.padding), league_logo)
        
        # Draw league name
        draw.text(
            (self.padding + 120, self.padding + 40),
            league.upper(),
            font=self.fonts['font_b_24'],
            fill='black'
        )

    def _draw_teams_section(self, draw: ImageDraw.Draw, home_team: str, away_team: str, home_logo: Image.Image, away_logo: Image.Image):
        """Draw the teams section of the bet slip."""
        y = 150
        
        # Draw team logos
        if home_logo and away_logo:
            logo_size = (80, 80)
            home_logo = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
            away_logo = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
            
            # Draw home team
            draw.bitmap((self.padding, y), home_logo)
            draw.text(
                (self.padding + 100, y + 30),
                home_team,
                font=self.fonts['font_b_18'],
                fill='black'
            )
            
            # Draw away team
            draw.bitmap((self.padding, y + 100), away_logo)
            draw.text(
                (self.padding + 100, y + 130),
                away_team,
                font=self.fonts['font_b_18'],
                fill='black'
            )

    def _draw_straight_details(self, draw: ImageDraw.Draw, line: Optional[str], odds: float, units: float, bet_id: str, timestamp: datetime):
        """Draw straight bet details section."""
        y = 400
        
        # Draw line
        if line:
            draw.text(
                (self.padding, y),
                line,
                font=self.fonts['font_m_24'],
                fill='black'
            )
            y += 30
        
        # Draw odds
        odds_txt = self._format_odds_with_sign(odds)
        draw.text(
            (self.padding, y + 20),
            odds_txt,
            font=self.fonts['font_b_24'],
            fill='black'
        )
        y += 30
        
        # Draw units
        units_txt = f"To Win {units:.2f} Units"
        draw.text(
            (self.padding, y + 50),
            units_txt,
            font=self.fonts['font_m_18'],
            fill='black'
        )
        
        # Draw bet ID and timestamp
        draw.text(
            (self.padding, y + 90),
            f"Bet ID: {bet_id}",
            font=self.fonts['font_m_18'],
            fill='gray'
        )
        draw.text(
            (self.padding, y + 120),
            f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            font=self.fonts['font_m_18'],
            fill='gray'
        )

    def _draw_parlay_details(self, draw: ImageDraw.Draw, legs: List[Dict], odds: float, units: float, bet_id: str, timestamp: datetime, is_same_game: bool):
        """Draw parlay bet details section."""
        y = 400
        
        # Draw each leg
        for i, leg in enumerate(legs, 1):
            leg_text = f"Leg {i}: {leg.get('team', 'N/A')} {leg.get('line', 'N/A')}"
            draw.text(
                (self.padding, y),
                leg_text,
                font=self.fonts['font_m_18'],
                fill='black'
            )
            y += 30
        
        # Draw total odds and units
        draw.text(
            (self.padding, y + 20),
            f"Total Odds: {odds:+d}",
            font=self.fonts['font_b_24'],
            fill='black'
        )
        draw.text(
            (self.padding, y + 50),
            f"Units: {units}",
            font=self.fonts['font_b_24'],
            fill='black'
        )
        
        # Draw bet ID and timestamp
        draw.text(
            (self.padding, y + 90),
            f"Bet ID: {bet_id}",
            font=self.fonts['font_m_18'],
            fill='gray'
        )
        draw.text(
            (self.padding, y + 120),
            f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            font=self.fonts['font_m_18'],
            fill='gray'
        )
        
        if is_same_game:
            draw.text(
                (self.padding, y + 150),
                "Same Game Parlay",
                font=self.fonts['font_b_18'],
                fill='blue'
            )

    def _draw_footer(self, draw: ImageDraw.Draw):
        """Draw the footer section of the bet slip."""
        # Draw footer text
        footer_text = "Good luck with your bet!"
        draw.text(
            (self.padding, 1000),
            footer_text,
            font=self.fonts['font_m_18'],
            fill='gray'
        )

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Load a team logo from the static directory."""
        try:
            # Get the sport from the league
            sport = get_sport_category_for_path(league.upper())
            if not sport:
                logger.error(f"Could not determine sport for league: {league}")
                return None

            # Ensure team directory exists
            team_dir = self._ensure_team_dir_exists(league)
            if not team_dir:
                return None

            # Load the team logo
            # Normalize team name for filename consistency
            normalized_team_name = normalize_team_name(team_name)
            logo_path = os.path.join(team_dir, f"{normalized_team_name}.png")

            if os.path.exists(logo_path):
                return Image.open(logo_path)
            else:
                logger.warning(f"Team logo not found: {logo_path}")
                # Attempt to load default logo
                if os.path.exists(self.DEFAULT_LOGO_PATH):
                    return Image.open(self.DEFAULT_LOGO_PATH)
                return None
        except Exception as e:
            logger.error(f"Error in _load_team_logo for {team_name} ({league}): {str(e)}")
            logger.error(traceback.format_exc())
            # Attempt to load default logo on error
            try:
                if os.path.exists(self.DEFAULT_LOGO_PATH):
                    return Image.open(self.DEFAULT_LOGO_PATH)
            except Exception as def_e:
                logger.error(f"Error loading default logo: {def_e}")
            return None

    def _ensure_team_dir_exists(self, league: str) -> Optional[str]:
        """Ensure the team directory exists and return its path."""
        try:
            sport = get_sport_category_for_path(league.upper())
            if not sport:
                logger.error(f"Could not determine sport for league: {league}")
                return None

            # Use LEAGUE_TEAM_BASE_DIR instead of static_dir
            team_dir = os.path.join(self.LEAGUE_TEAM_BASE_DIR, sport, league.upper())
            os.makedirs(team_dir, exist_ok=True)
            return team_dir
        except Exception as e:
            logger.error(f"Error ensuring team directory exists for {league}: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def _load_lock_icon(self) -> Optional[Image.Image]:
        if self._lock_icon_cache is None:
            try:
                path = self.LOCK_ICON_PATH
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    with Image.open(abs_path) as lock_img:
                        self._lock_icon_cache = lock_img.convert("RGBA").resize(
                            (30, 30), Image.Resampling.LANCZOS
                        ).copy()
                else:
                    logger.warning("Lock icon not found: %s", abs_path)
            except Exception as e:
                logger.error("Err loading lock icon: %s", e)
        return self._lock_icon_cache

    async def get_guild_background(self) -> Optional[Image.Image]:
        """Fetch the guild background image from the DB or return None if not set."""
        if not self.guild_id:
            return None
        try:
            settings = await self.db_manager.fetch_one(
                "SELECT guild_background FROM guild_settings WHERE guild_id = %s",
                (self.guild_id,)
            )
            guild_bg_url = settings.get("guild_background") if settings else None
            if guild_bg_url:
                response = requests.get(guild_bg_url, timeout=5)
                if response.status_code == 200:
                    return Image.open(io.BytesIO(response.content)).convert("RGBA")
        except Exception as e:
            logger.error(f"Error loading guild background: {e}")
        return None

    def generate_bet_slip(
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
        is_same_game: bool = False,
        background_img: Optional[Image.Image] = None
    ) -> Optional[Image.Image]:
        """Generate a bet slip image."""
        try:
            logger.info(f"Generating bet slip - Home: '{home_team}', Away: '{away_team}', League: '{league}', Type: {bet_type}")
            
            background_color = "#23232a"  # Default fallback color
            width, height = 600, 400
            if background_img:
                background_img = background_img.resize((width, height), Image.Resampling.LANCZOS)
                img = background_img.copy()
            else:
                img = Image.new('RGBA', (width, height), background_color)
            draw = ImageDraw.Draw(img)
            
            # Load fonts
            logger.info("Loading fonts...")
            self._load_fonts()
            logger.info("Fonts loaded successfully")
            
            # Load league logo
            logger.info(f"Loading league logo for: '{league}'")
            league_logo = self._load_league_logo(league)
            if not league_logo:
                logger.error(f"Failed to load league logo for {league}")
                return None
            logger.info(f"Successfully loaded league logo for: '{league}'")
            
            # Load team logos
            logger.info(f"Loading team logos - Home: '{home_team}', Away: '{away_team}', League: '{league}'")
            home_logo = self._load_team_logo(home_team, league)
            away_logo = self._load_team_logo(away_team, league)
            if not home_logo or not away_logo:
                logger.error("Failed to load team logos")
                return None
            logger.info(f"Successfully loaded home team logo for: '{home_team}'")
            logger.info(f"Successfully loaded away team logo for: '{away_team}'")
            
            # Draw header
            self._draw_header(draw, league_logo, league)
            
            # Draw teams section
            self._draw_teams_section(draw, home_team, away_team, home_logo, away_logo)
            
            # Draw bet details
            if bet_type == "parlay" and parlay_legs:
                self._draw_parlay_details(draw, parlay_legs, odds, units, bet_id, timestamp, is_same_game)
            else:
                self._draw_straight_details(draw, line, odds, units, bet_id, timestamp)
            
            # Draw footer
            self._draw_footer(draw)
            
            logger.info(f"Bet slip generated OK: {bet_id}")
            return img
            
        except Exception as e:
            logger.error(f"Error generating bet slip: {str(e)}")
            return None
            
    def _load_fonts(self):
        """Load fonts with proper fallbacks."""
        # Implementation of _load_fonts method
        pass

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        """Load a league logo with caching."""
        if not league:
            return None
            
        try:
            cache_key = f"league_{league}"
            now = time.time()
            
            # Check cache first
            if cache_key in self._logo_cache:
                logo, ts = self._logo_cache[cache_key]
                if now - ts <= self._cache_expiry:
                    return logo
                else:
                    del self._logo_cache[cache_key]
            
            # Get the league directory
            sport = get_sport_category_for_path(league.upper())
            fname = f"{league.lower().replace(' ', '_')}.png"
            logo_dir = os.path.join(self.LEAGUE_LOGO_BASE_DIR, sport, league.upper())
            logo_path = os.path.join(logo_dir, fname)
            os.makedirs(logo_dir, exist_ok=True)
            
            # Log the attempt
            absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info(
                "Loading league logo - League: '%s', Sport: '%s', Path: '%s', Exists: %s",
                league, sport, absolute_logo_path, file_exists
            )
            
            # Try to load the logo
            logo = None
            if file_exists:
                try:
                    logo = Image.open(absolute_logo_path).convert("RGBA")
                except Exception as e:
                    logger.error("Error loading league logo %s: %s", absolute_logo_path, e)
            
            # Cache the logo if we have one
            if logo:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    # Remove oldest entry if cache is full
                    oldest_key = min(self._logo_cache, key=lambda k: self._logo_cache[k][1])
                    del self._logo_cache[oldest_key]
                self._logo_cache[cache_key] = (logo.copy(), now)
                return logo
                
            logger.warning(
                "No logo found for league %s (path: %s)",
                league, absolute_logo_path
            )
            return None
            
        except Exception as e:
            logger.error(
                "Error in _load_league_logo for %s: %s",
                league, e, exc_info=True
            )
            return None

    def _cleanup_cache(self):
        now = time.time()
        if now - self._last_cache_cleanup > 300:
            expired = [
                k for k, (_, ts) in self._logo_cache.items()
                if now - ts > self._cache_expiry
            ]
            for k in expired:
                self._logo_cache.pop(k, None)
            self._last_cache_cleanup = now

    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team name to match logo file naming convention."""
        # Common team name mappings
        team_mappings = {
            # NHL Teams
            "Oilers": "edmonton_oilers",
            "Flames": "calgary_flames",
            "Canucks": "vancouver_canucks",
            "Maple Leafs": "toronto_maple_leafs",
            "Senators": "ottawa_senators",
            "Canadiens": "montreal_canadiens",
            "Bruins": "boston_bruins",
            "Sabres": "buffalo_sabres",
            "Rangers": "new_york_rangers",
            "Islanders": "new_york_islanders",
            "Devils": "new_jersey_devils",
            "Flyers": "philadelphia_flyers",
            "Penguins": "pittsburgh_penguins",
            "Capitals": "washington_capitals",
            "Hurricanes": "carolina_hurricanes",
            "Panthers": "florida_panthers",
            "Lightning": "tampa_bay_lightning",
            "Red Wings": "detroit_red_wings",
            "Blackhawks": "chicago_blackhawks",
            "Blues": "st_louis_blues",
            "Wild": "minnesota_wild",
            "Jets": "winnipeg_jets",
            "Avalanche": "colorado_avalanche",
            "Stars": "dallas_stars",
            "Predators": "nashville_predators",
            "Coyotes": "arizona_coyotes",
            "Golden Knights": "vegas_golden_knights",
            "Kraken": "seattle_kraken",
            "Sharks": "san_jose_sharks",
            "Kings": "los_angeles_kings",
            "Ducks": "anaheim_ducks",
            
            # NFL Teams
            "49ers": "san_francisco_49ers",
            "Bears": "chicago_bears",
            "Bengals": "cincinnati_bengals",
            "Bills": "buffalo_bills",
            "Broncos": "denver_broncos",
            "Browns": "cleveland_browns",
            "Buccaneers": "tampa_bay_buccaneers",
            "Cardinals": "arizona_cardinals",
            "Chargers": "los_angeles_chargers",
            "Chiefs": "kansas_city_chiefs",
            "Colts": "indianapolis_colts",
            "Cowboys": "dallas_cowboys",
            "Dolphins": "miami_dolphins",
            "Eagles": "philadelphia_eagles",
            "Falcons": "atlanta_falcons",
            "Giants": "new_york_giants",
            "Jaguars": "jacksonville_jaguars",
            "Jets": "new_york_jets",
            "Lions": "detroit_lions",
            "Packers": "green_bay_packers",
            "Panthers": "carolina_panthers",
            "Patriots": "new_england_patriots",
            "Raiders": "las_vegas_raiders",
            "Rams": "los_angeles_rams",
            "Ravens": "baltimore_ravens",
            "Saints": "new_orleans_saints",
            "Seahawks": "seattle_seahawks",
            "Steelers": "pittsburgh_steelers",
            "Texans": "houston_texans",
            "Titans": "tennessee_titans",
            "Vikings": "minnesota_vikings",
            "Commanders": "washington_commanders"
        }
        
        # First check if we have a direct mapping
        if team_name in team_mappings:
            return team_mappings[team_name]
        
        # If no direct mapping, try to normalize the name
        normalized = team_name.lower().replace(" ", "_")
        logger.info("Normalized team name from '%s' to '%s'", team_name, normalized)
        return normalized

    def _format_odds_with_sign(self, odds: float) -> str:
        """Format odds with appropriate sign."""
        if odds > 0:
            return f"+{odds:.0f}"
        return f"{odds:.0f}"
