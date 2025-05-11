# betting-bot/utils/image_generator.py

import logging
import os
import time
import io
from datetime import datetime
from typing import Optional, List, Dict, Any

from PIL import Image, ImageDraw, ImageFont
from config.asset_paths import (
    ASSETS_DIR,
    FONT_DIR,
    LOGO_DIR,
    TEAMS_SUBDIR,
    LEAGUES_SUBDIR,
    get_sport_category_for_path
)
from config.team_mappings import normalize_team_name

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


def get_sport_category_for_path(league_name: str) -> str:
    """Gets the sport category string for use in paths."""
    return SPORT_CATEGORY_MAP.get(
        str(league_name).upper(), DEFAULT_FALLBACK_SPORT_CATEGORY
    )


def _determine_asset_paths():
    """Determine asset paths dynamically."""
    assets_dir_default = "betting-bot/static/"
    font_dir_name = 'fonts'
    logo_dir_name = 'logos'
    teams_subdir_name = 'teams'
    leagues_subdir_name = 'leagues'

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        potential_assets_dir = os.path.join(parent_dir, 'assets')
        potential_static_dir = os.path.join(parent_dir, 'static')
    except NameError:
        script_dir = os.getcwd()
        parent_dir = os.path.dirname(script_dir)
        potential_assets_dir = os.path.join(parent_dir, 'betting-bot', 'assets')
        potential_static_dir = os.path.join(parent_dir, 'betting-bot', 'static')

    final_assets_dir = None
    if os.path.isdir(potential_static_dir):
        final_assets_dir = potential_static_dir
    elif os.path.isdir(potential_assets_dir):
        final_assets_dir = potential_assets_dir
    elif os.path.isdir(assets_dir_default):
        final_assets_dir = assets_dir_default
    else:
        final_assets_dir = os.path.join(os.getcwd(), 'static')
        logger.warning(
            "Could not find 'assets' or 'static'. Assuming path: %s",
            final_assets_dir
        )

    logger.info("Path determination targeting base: %s", final_assets_dir)

    paths = {
        "ASSETS_DIR": final_assets_dir,
        "DEFAULT_FONT_PATH": os.path.join(
            final_assets_dir, font_dir_name, 'Roboto-Regular.ttf'
        ),
        "DEFAULT_BOLD_FONT_PATH": os.path.join(
            final_assets_dir, font_dir_name, 'Roboto-Bold.ttf'
        ),
        "DEFAULT_EMOJI_FONT_PATH_NOTO": os.path.join(
            final_assets_dir, font_dir_name, 'NotoEmoji-Regular.ttf'
        ),
        "DEFAULT_EMOJI_FONT_PATH_SEGOE": os.path.join(
            final_assets_dir, font_dir_name, 'SegoeUIEmoji.ttf'
        ),
        "LEAGUE_TEAM_BASE_DIR": os.path.join(
            final_assets_dir, logo_dir_name, teams_subdir_name
        ),
        "LEAGUE_LOGO_BASE_DIR": os.path.join(
            final_assets_dir, logo_dir_name, leagues_subdir_name
        ),
        "DEFAULT_LOCK_ICON_PATH": os.path.join(
            final_assets_dir, "lock_icon.png"
        ),
        "DEFAULT_TEAM_LOGO_PATH": os.path.join(
            final_assets_dir, logo_dir_name, 'default_logo.png'
        ),
    }
    return paths


_PATHS = _determine_asset_paths()

try:
    _font_path = _PATHS["DEFAULT_FONT_PATH"]
    if not os.path.exists(_font_path):
        logger.warning("Default font '%s' not found. Falling back.", _font_path)
        _linux_fallbacks = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
        ]
        _font_path = next((p for p in _linux_fallbacks if os.path.exists(p)), 'arial.ttf')
    logger.info("Using regular font: %s", _font_path)

    _bold_font_path = _PATHS["DEFAULT_BOLD_FONT_PATH"]
    if not os.path.exists(_bold_font_path):
        logger.warning("Default bold font '%s' not found. Falling back.", _bold_font_path)
        _bold_font_path = _font_path
    logger.info("Using bold font: %s", _bold_font_path)

    _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"]
    if not os.path.exists(_emoji_font_path):
        _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_SEGOE"]
    if not os.path.exists(_emoji_font_path):
        logger.warning("Default Noto/Segoe emoji fonts not found. Falling back.")
        _linux_emoji_fallbacks = [
            '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
            '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf'
        ]
        _emoji_font_path = next((p for p in _linux_emoji_fallbacks if os.path.exists(p)), _font_path)
    logger.info("Using emoji font: %s", _emoji_font_path)

    font_m_18 = ImageFont.truetype(_font_path, 18)
    font_m_24 = ImageFont.truetype(_font_path, 24)
    font_b_18 = ImageFont.truetype(_bold_font_path, 18)
    font_b_24 = ImageFont.truetype(_bold_font_path, 24)
    font_b_36 = ImageFont.truetype(_bold_font_path, 36)
    try:
        font_b_28 = ImageFont.truetype(_bold_font_path, 28)
    except IOError:
        font_b_28 = font_b_24
        logger.warning("Using size 24 bold as 28 fallback.")
    try:
        emoji_font_24 = ImageFont.truetype(_emoji_font_path, 24)
    except IOError:
        emoji_font_24 = font_m_24
        logger.warning("Using regular font as emoji fallback.")
    logger.info("Fonts loaded globally.")
except Exception as e:
    logger.critical("CRITICAL: Error loading fonts: %s", e, exc_info=True)
    font_m_18 = font_m_24 = font_b_18 = font_b_24 = font_b_36 = font_b_28 = emoji_font_24 = ImageFont.load_default()


class BetSlipGenerator:
    def __init__(self):
        """Initialize the bet slip generator with required assets."""
        self._load_fonts()
        self._load_background()
        self._load_team_logos()
        self._load_league_logos()
        
    def _load_fonts(self):
        """Load required fonts."""
        try:
            self.title_font = ImageFont.truetype(os.path.join(FONT_DIR, "Roboto-Bold.ttf"), 36)
            self.subtitle_font = ImageFont.truetype(os.path.join(FONT_DIR, "Roboto-Regular.ttf"), 24)
            self.text_font = ImageFont.truetype(os.path.join(FONT_DIR, "Roboto-Regular.ttf"), 20)
            self.small_font = ImageFont.truetype(os.path.join(FONT_DIR, "Roboto-Regular.ttf"), 16)
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")
            raise
            
    def _load_background(self):
        """Load the background image."""
        try:
            self.background = Image.open(os.path.join(ASSETS_DIR, "background.png"))
        except Exception as e:
            logger.error(f"Error loading background: {e}")
            raise
            
    def _load_team_logos(self):
        """Load team logos."""
        self.team_logos = {}
        try:
            for sport_category in os.listdir(TEAMS_SUBDIR):
                sport_path = os.path.join(TEAMS_SUBDIR, sport_category)
                if os.path.isdir(sport_path):
                    for team_file in os.listdir(sport_path):
                        if team_file.endswith('.png'):
                            team_name = os.path.splitext(team_file)[0]
                            self.team_logos[team_name] = Image.open(os.path.join(sport_path, team_file))
        except Exception as e:
            logger.error(f"Error loading team logos: {e}")
            raise
            
    def _load_league_logo(self, league: str) -> Image.Image:
        """Load a league logo."""
        try:
            sport_category = get_sport_category_for_path(league)
            if not sport_category:
                logger.warning(f"No sport category found for league: {league}")
                return None
                
            logo_path = os.path.join(LEAGUES_SUBDIR, sport_category, f"{league.lower()}.png")
            if os.path.exists(logo_path):
                return Image.open(logo_path)
            else:
                logger.warning(f"League logo not found: {logo_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading league logo for {league}: {e}")
            return None
            
    def _get_team_logo(self, team_name: str) -> Image.Image:
        """Get a team logo by name."""
        normalized_name = normalize_team_name(team_name)
        if normalized_name in self.team_logos:
            return self.team_logos[normalized_name]
        logger.warning(f"Team logo not found for: {team_name} (normalized: {normalized_name})")
        return None

    def _format_odds_with_sign(self, odds: Optional[Any]) -> str:
        if odds is None:
            return "N/A"
        try:
            odds_num = int(float(odds))
            return f"+{odds_num}" if odds_num > 0 else str(odds_num)
        except (ValueError, TypeError):
            logger.warning("Invalid odds format: %s", odds)
            return "N/A"

    def _ensure_team_dir_exists(self, league: str) -> str:
        league_upper = league.upper()
        if league_upper.startswith("NCAA"):
            sport = get_sport_category_for_path(league_upper)
            if sport == DEFAULT_FALLBACK_SPORT_CATEGORY:
                sport = "UNKNOWN_NCAA_SPORT"
            team_dir = os.path.join(self.LEAGUE_TEAM_BASE_DIR, "NCAA", sport)
        else:
            sport = get_sport_category_for_path(league_upper)
            team_dir = os.path.join(self.LEAGUE_TEAM_BASE_DIR, sport, league_upper)
        os.makedirs(team_dir, exist_ok=True)
        return team_dir

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

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        if not team_name or not league:
            return None
        try:
            cache_key = f"team_{team_name}_{league}"
            now = time.time()
            if cache_key in self._logo_cache:
                logo, ts = self._logo_cache[cache_key]
                if now - ts <= self._cache_expiry:
                    return logo
                else:
                    del self._logo_cache[cache_key]
            team_dir = self._ensure_team_dir_exists(league)
            normalized_name = self._normalize_team_name(team_name)
            logo_path = os.path.join(team_dir, f"{normalized_name}.png")

            # --- START REFINED LOGGING ---
            absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info(
                "Team logo details - Team: '%s', Normalized: '%s', League: '%s', Path: '%s', Exists: %s",
                team_name, normalized_name, league, absolute_logo_path, file_exists
            )
            # --- END REFINED LOGGING ---

            logo = None
            if file_exists:
                try:
                    logo = Image.open(absolute_logo_path).convert("RGBA")
                except Exception as e:
                    logger.error("Err loading %s: %s", absolute_logo_path, e)
            if logo is None:
                default_path = _PATHS["DEFAULT_TEAM_LOGO_PATH"]
                abs_default = os.path.abspath(default_path)
                if os.path.exists(abs_default):
                    try:
                        logo = Image.open(abs_default).convert("RGBA")
                        logger.warning(
                            "Using default logo for %s (path: %s)",
                            team_name, absolute_logo_path
                        )
                    except Exception as e:
                        logger.error("Err loading default %s: %s", abs_default, e)
                else:
                    logger.warning("Default team logo not found: %s", abs_default)
            if logo:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    self._logo_cache.pop(
                        min(self._logo_cache, key=lambda k: self._logo_cache[k][1]), None
                    )
                self._logo_cache[cache_key] = (logo.copy(), now)
                return logo
            logger.warning(
                "Final: No logo loaded for %s (%s) path: %s",
                team_name, league, absolute_logo_path
            )
            return None
        except Exception as e:
            logger.error(
                "Err _load_team_logo %s (%s): %s",
                team_name, league, e, exc_info=True
            )
            return None

    def _load_lock_icon(self) -> Optional[Image.Image]:
        if self._lock_icon_cache is None:
            try:
                path = _PATHS["DEFAULT_LOCK_ICON_PATH"]
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

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        if not league:
            return None
        try:
            cache_key = f"league_{league}"
            now = time.time()
            if cache_key in self._logo_cache:
                logo, ts = self._logo_cache[cache_key]
                if now - ts <= self._cache_expiry:
                    return logo
                else:
                    del self._logo_cache[cache_key]
            sport = get_sport_category_for_path(league.upper())
            fname = f"{league.lower().replace(' ', '_')}.png"
            logo_dir = os.path.join(self.LEAGUE_LOGO_BASE_DIR, sport, league.upper())
            logo_path = os.path.join(logo_dir, fname)
            os.makedirs(logo_dir, exist_ok=True)

            # --- START REFINED LOGGING ---
            absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info(
                "League logo details - League: '%s', Sport: '%s', Path: '%s', Exists: %s",
                league, sport, absolute_logo_path, file_exists
            )
            # --- END REFINED LOGGING ---

            logo = None
            if file_exists:
                try:
                    with Image.open(absolute_logo_path) as img_file:
                        logo = img_file.convert('RGBA')
                except Exception as e:
                    logger.error("Err loading %s: %s", absolute_logo_path, e)
            if logo:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size:
                    self._logo_cache.pop(
                        min(self._logo_cache, key=lambda k: self._logo_cache[k][1]), None
                    )
                self._logo_cache[cache_key] = (logo.copy(), now)
                return logo
            logger.warning(
                "No logo found for league %s (path: %s)",
                league, absolute_logo_path
            )
            return None
        except Exception as e:
            logger.error("Err _load_league_logo %s: %s", league, e, exc_info=True)
            return None

    def generate_bet_slip(
        self, home_team: str, away_team: str, league: Optional[str], line: str,
        odds: float, units: float, bet_id: str, timestamp: datetime,
        bet_type: str = "straight",
        parlay_legs: Optional[List[Dict[str, Any]]] = None,
        is_same_game: bool = False
    ) -> Optional[Image.Image]:
        eff_league = league or "UNKNOWN"
        logger.info("Generating bet slip - Home: '%s', Away: '%s', League: '%s', Type: %s", 
                   home_team, away_team, eff_league, bet_type)
        try:
            width = 800; header_h = 100; footer_h = 80; leg_h = 180
            num_legs = len(parlay_legs) if parlay_legs else 1
            content_h = num_legs * leg_h if bet_type == "parlay" and parlay_legs else 400
            parlay_tot_h = 120 if bet_type == "parlay" else 0
            height = header_h + content_h + parlay_tot_h + footer_h
            img = Image.new('RGBA', (width, height), (40, 40, 40, 255))
            draw = ImageDraw.Draw(img)

            h_y = 30
            if bet_type == 'parlay':
                title = (
                    f"{eff_league.upper()} - "
                    f"{'Same Game Parlay' if is_same_game else 'Multi-Team Parlay Bet'}"
                )
            else:
                title = f"{eff_league.upper()} - Straight Bet"

            logger.info("Loading league logo for: '%s'", eff_league)
            lg_logo = self._load_league_logo(eff_league)
            if lg_logo:
                logger.info("Successfully loaded league logo for: '%s'", eff_league)
                r = min(60 / lg_logo.height, 1.0)
                nw, nh = int(lg_logo.width * r), int(lg_logo.height * r)
                lg_disp = lg_logo.resize((nw, nh), Image.Resampling.LANCZOS)
                lx, ly = (width - nw) // 2, h_y - 10
                if img.mode != 'RGBA': img = img.convert("RGBA")
                tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
                tmp.paste(lg_disp, (lx, ly), lg_disp)
                img = Image.alpha_composite(img, tmp)
                draw = ImageDraw.Draw(img)
                h_y += nh + 5
            else:
                logger.warning("Failed to load league logo for: '%s'", eff_league)
                h_y += 10

            bbox = draw.textbbox((0, 0), title, self.font_b_36)
            draw.text(((width - (bbox[2] - bbox[0])) / 2, h_y), title, 'white', self.font_b_36)

            c_start_y = header_h + 10
            if bet_type == "straight":
                logo_y, l_sz = c_start_y + 40, (120, 120)
                logger.info("Loading team logos - Home: '%s', Away: '%s', League: '%s'", 
                           home_team, away_team, eff_league)
                h_logo = self._load_team_logo(home_team, eff_league)
                a_logo = self._load_team_logo(away_team, eff_league)
                if h_logo:
                    logger.info("Successfully loaded home team logo for: '%s'", home_team)
                    h_disp = h_logo.resize(l_sz, Image.Resampling.LANCZOS)
                    if img.mode != 'RGBA': img = img.convert("RGBA")
                    tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    tmp.paste(h_disp, (width // 4 - l_sz[0] // 2, logo_y), h_disp)
                    img = Image.alpha_composite(img, tmp); draw = ImageDraw.Draw(img)
                else:
                    logger.warning("Failed to load home team logo for: '%s'", home_team)
                draw.text((width // 4, logo_y + l_sz[1] + 20), home_team, 'white', self.font_b_24, 'mm')
                if a_logo:
                    logger.info("Successfully loaded away team logo for: '%s'", away_team)
                    a_disp = a_logo.resize(l_sz, Image.Resampling.LANCZOS)
                    if img.mode != 'RGBA': img = img.convert("RGBA")
                    tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    tmp.paste(a_disp, (3 * width // 4 - l_sz[0] // 2, logo_y), a_disp)
                    img = Image.alpha_composite(img, tmp); draw = ImageDraw.Draw(img)
                else:
                    logger.warning("Failed to load away team logo for: '%s'", away_team)
                draw.text((3 * width // 4, logo_y + l_sz[1] + 20), away_team, 'white', self.font_b_24, 'mm')

                det_y = logo_y + l_sz[1] + 80
                bet_txt = f"{home_team}: {line}"
                draw.text((width // 2, det_y), bet_txt, 'white', self.font_m_24, 'mm')
                sep_y = det_y + 40; draw.line([(20, sep_y), (width - 20, sep_y)], 'white', 2)
                odds_y = sep_y + 30
                odds_txt = self._format_odds_with_sign(odds)
                draw.text((width // 2, odds_y), odds_txt, 'white', self.font_b_24, 'mm')
                units_y = odds_y + 50
                units_txt = f"To Win {units:.2f} Units"
                bbox = draw.textbbox((0, 0), units_txt, self.font_b_24); u_w = bbox[2] - bbox[0]
                lock = self._load_lock_icon()
                if lock:
                    sp = 20; t_w = u_w + 2 * lock.width + 2 * sp; sx = (width - t_w) // 2
                    if img.mode != 'RGBA': img = img.convert('RGBA')
                    tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    tmp.paste(lock, (sx, int(units_y - lock.height / 2)), lock)
                    img = Image.alpha_composite(img, tmp); draw = ImageDraw.Draw(img)
                    tx = sx + lock.width + sp
                    draw.text((tx + u_w / 2, units_y), units_txt, (255, 215, 0), self.font_b_24, "mm")
                    tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    tmp.paste(lock, (int(tx + u_w + sp), int(units_y - lock.height / 2)), lock)
                    img = Image.alpha_composite(img, tmp); draw = ImageDraw.Draw(img)
                else:
                    draw.text((width // 2, units_y), units_txt, (255, 215, 0), self.font_b_24, 'mm')
            elif bet_type == "parlay" and parlay_legs:
                curr_y = c_start_y
                for i, leg in enumerate(parlay_legs):
                    if i > 0: draw.line([(40, curr_y), (width - 40, curr_y)], (100, 100, 100), 1); curr_y += 20
                    leg_lg = leg.get('league', eff_league)
                    next_y = self._draw_parlay_leg_internal(img, draw, leg, leg_lg, width, curr_y, is_same_game, leg_h)
                    draw = ImageDraw.Draw(img); curr_y = next_y
                tot_y = curr_y; draw.line([(40, tot_y), (width - 40, tot_y)], 'white', 2); tot_y += 30
                tot_odds_txt = f"Total Odds: {self._format_odds_with_sign(odds)}"
                draw.text((width // 2, tot_y), tot_odds_txt, 'white', self.font_b_28, 'mm'); tot_y += 40
                units_txt = f"Stake: {units:.2f} Units"
                bbox = draw.textbbox((0, 0), units_txt, self.font_b_24); u_w = bbox[2] - bbox[0]
                lock = self._load_lock_icon()
                if lock:
                    sp = 15; t_w = u_w + 2 * lock.width + 2 * sp; sx = (width - t_w) // 2
                    if img.mode != 'RGBA': img = img.convert("RGBA")
                    tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    tmp.paste(lock, (sx, int(tot_y - lock.height / 2)), lock)
                    img = Image.alpha_composite(img, tmp); draw = ImageDraw.Draw(img)
                    tx = sx + lock.width + sp
                    draw.text((tx + u_w / 2, tot_y), units_txt, (255, 215, 0), self.font_b_24, 'mm')
                    tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    tmp.paste(lock, (int(tx + u_w + sp), int(tot_y - lock.height / 2)), lock)
                    img = Image.alpha_composite(img, tmp); draw = ImageDraw.Draw(img)
                else:
                    draw.text((width // 2, tot_y), f"🔒 {units_txt} 🔒", (255, 215, 0), self.emoji_font_24, 'mm')
            else:
                draw.text((width // 2, height // 2), "Invalid Bet Data", 'red', self.font_b_36, 'mm')

            f_y = height - footer_h // 2; id_txt = f"Bet #{bet_id}"; ts_txt = timestamp.strftime('%Y-%m-%d %H:%M UTC')
            draw.text((self.padding, f_y), id_txt, (150, 150, 150), self.font_m_18, 'lm')
            draw.text((width - self.padding, f_y), ts_txt, (150, 150, 150), self.font_m_18, 'rm')
            logger.info("Bet slip generated OK: %s", bet_id)
            return img.convert("RGB")
        except Exception as e:
            logger.exception("Error generating bet slip %s: %s", bet_id, e)
            err_img = Image.new('RGB', (800, 200), (40, 40, 40)); draw = ImageDraw.Draw(err_img)
            font = self.font_m_24
            draw.text((400, 100), "Error Generating Slip", 'red', font, "mm"); return err_img

    def _draw_parlay_leg_internal(
        self, image: Image.Image, draw: ImageDraw.Draw, leg: Dict[str, Any], league: Optional[str],
        width: int, start_y: int, is_same_game: bool, leg_height: int
    ) -> int:
        leg_home = leg.get('home_team', leg.get('team', 'Unk')); leg_away = leg.get('opponent', 'Unk')
        leg_line = leg.get('line', 'N/A'); leg_odds = leg.get('odds', 0); leg_lg = leg.get('league', league or 'UNK')
        logo_y = start_y + 10; l_sz = (50, 50); txt_x = 40
        team_show = leg.get('team', leg_home)
        if team_show != 'Unknown':
            team_logo = self._load_team_logo(team_show, leg_lg)
            if team_logo:
                lx = 40; disp = team_logo.resize(l_sz, Image.Resampling.LANCZOS)
                if image.mode != 'RGBA': image = image.convert("RGBA")
                tmp = Image.new('RGBA', image.size, (0, 0, 0, 0)); tmp.paste(disp, (lx, logo_y), disp)
                image = Image.alpha_composite(image, tmp); draw = ImageDraw.Draw(image); txt_x = lx + l_sz[0] + 15
        draw.text((txt_x, logo_y + 5), leg_line, 'white', self.font_m_24)
        h = leg.get('home_team', leg_home); a = leg.get('opponent', leg_away); parts = []
        if h != 'Unknown': parts.append(h)
        if a != 'Unknown' and a != h: parts.append(f"vs {a}")
        matchup = " ".join(parts) if parts else team_show
        draw.text((txt_x, logo_y + 40), f"{leg_lg} - {matchup}", (180, 180, 180), self.font_m_18)
        odds_txt = self._format_odds_with_sign(leg_odds)
        bbox = draw.textbbox((0, 0), odds_txt, self.font_b_28)
        tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]; odds_y = start_y + (leg_height / 2) - (th / 2)
        draw.text((width - 40 - tw, int(odds_y)), odds_txt, 'white', self.font_b_28)
        return start_y + leg_height
