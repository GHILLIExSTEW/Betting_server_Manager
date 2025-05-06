# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime 
from typing import Optional, List, Dict, Any 
import time 

logger = logging.getLogger(__name__)

# --- Sport Category Mapping (Defined Globally) ---
SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
    "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
    "MLB": "BASEBALL", "NCAAB_BASEBALL": "BASEBALL", # Added for consistency if used
    "NHL": "HOCKEY",
    "MLS": "SOCCER", "EPL": "SOCCER", "LA LIGA": "SOCCER", "SERIE A": "SOCCER", "BUNDESLIGA": "SOCCER", "LIGUE 1": "SOCCER",
    "TENNIS": "TENNIS",
    "UFC": "MMA", "MMA": "MMA",
    "DARTS": "DARTS"
    # Add other leagues/sports as needed
}
DEFAULT_FALLBACK_SPORT_CATEGORY = "OTHER_SPORTS" # For leagues not in map

# Helper function to get sport category for path construction
def get_sport_category_for_path(league_name: str) -> str:
    """Gets the sport category string for use in paths, using the global map."""
    return SPORT_CATEGORY_MAP.get(str(league_name).upper(), DEFAULT_FALLBACK_SPORT_CATEGORY)

# --- Default Font/Asset Path Logic (Global Scope Helper) ---
def _determine_asset_paths():
    assets_dir_default = "betting-bot/static/" 
    font_dir_name = 'fonts'
    logo_dir_name = 'logos'
    teams_subdir_name = 'teams'
    leagues_subdir_name = 'leagues'

    script_dir = os.path.dirname(__file__) 
    parent_dir = os.path.dirname(script_dir) 
    potential_assets_dir = os.path.join(parent_dir, 'assets') 
    potential_static_dir = os.path.join(parent_dir, 'static') 

    final_assets_dir = None
    # Runtime check for directory existence (simulation here assumes 'assets' is primary if available)
    # For the purpose of generating paths, we'll assume 'assets' is the target if it's intended.
    # The actual check 'os.path.isdir' happens when the bot runs.
    # Based on logs: "/home/container/betting-bot/assets" is used.
    final_assets_dir = potential_assets_dir # Assuming 'assets' will be the one found or intended
    logger.info(f"Path determination logic targeting base: {final_assets_dir}")


    paths = {
        "ASSETS_DIR": final_assets_dir,
        "DEFAULT_FONT_PATH": os.path.join(final_assets_dir, font_dir_name, 'Roboto-Regular.ttf'),
        "DEFAULT_BOLD_FONT_PATH": os.path.join(final_assets_dir, font_dir_name, 'Roboto-Bold.ttf'),
        "DEFAULT_EMOJI_FONT_PATH_NOTO": os.path.join(final_assets_dir, font_dir_name, 'NotoEmoji-Regular.ttf'),
        "DEFAULT_EMOJI_FONT_PATH_SEGOE": os.path.join(final_assets_dir, font_dir_name, 'SegoeUIEmoji.ttf'),
        "LEAGUE_TEAM_BASE_DIR": os.path.join(final_assets_dir, logo_dir_name, teams_subdir_name),
        "LEAGUE_LOGO_BASE_DIR": os.path.join(final_assets_dir, logo_dir_name, leagues_subdir_name),
        "DEFAULT_LOCK_ICON_PATH": os.path.join(final_assets_dir, "lock_icon.png"),
        "DEFAULT_TEAM_LOGO_PATH": os.path.join(final_assets_dir, logo_dir_name, 'default_logo.png')
    }
    return paths

_PATHS = _determine_asset_paths()

# --- Font Loading (Global Scope) --- (Assumed correct from previous steps)
try:
    _font_path = _PATHS["DEFAULT_FONT_PATH"]
    if not os.path.exists(_font_path): # This check is runtime; here we assume paths are constructed correctly
        _font_path = 'arial.ttf' # Fallback for non-runtime
    _bold_font_path = _PATHS["DEFAULT_BOLD_FONT_PATH"]
    if not os.path.exists(_bold_font_path):
        _bold_font_path = _font_path
    _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"] # Defaulting to Noto
    if not os.path.exists(_emoji_font_path):
        _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_SEGOE"]
        if not os.path.exists(_emoji_font_path):
            _emoji_font_path = _font_path

    font_m_18 = ImageFont.truetype(_font_path, 18)
    font_m_24 = ImageFont.truetype(_font_path, 24)
    font_b_18 = ImageFont.truetype(_bold_font_path, 18)
    font_b_24 = ImageFont.truetype(_bold_font_path, 24)
    font_b_36 = ImageFont.truetype(_bold_font_path, 36)
    emoji_font_24 = ImageFont.truetype(_emoji_font_path, 24)
    logger.info("Successfully loaded fonts globally for image_generator (simulated).")
except Exception as e:
    logger.critical(f"CRITICAL: Error loading required fonts: {e}", exc_info=True)
    font_m_18 = font_m_24 = font_b_18 = font_b_24 = font_b_36 = emoji_font_24 = ImageFont.load_default()


class BetSlipGenerator:
    def __init__(self, font_path: Optional[str] = None, emoji_font_path: Optional[str] = None, assets_dir: str = "betting-bot/static/"): # assets_dir default might be overridden by _PATHS
        # Use paths from _determine_asset_paths
        self.assets_dir = _PATHS["ASSETS_DIR"] # Use determined assets_dir
        self.font_path = font_path or _PATHS["DEFAULT_FONT_PATH"]
        self.bold_font_path = _PATHS["DEFAULT_BOLD_FONT_PATH"]
        self.emoji_font_path = emoji_font_path or _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"]
        
        self.league_team_base_dir = _PATHS["LEAGUE_TEAM_BASE_DIR"]
        self.league_logo_base_dir = _PATHS["LEAGUE_LOGO_BASE_DIR"]
        
        os.makedirs(self.league_team_base_dir, exist_ok=True)
        os.makedirs(self.league_logo_base_dir, exist_ok=True)
        
        self._logo_cache = {}
        self._font_cache = {}
        self._lock_icon_cache = None
        self._max_cache_size = 100
        self._cache_expiry = 3600
        self._last_cache_cleanup = time.time()
        
        self.width = 800
        self.leg_height = 120
        self.header_height = 100
        self.footer_height = 80
        self.padding = 20
        self.logo_size = 60
        self.image = None
        
        self.font_m_18 = font_m_18
        self.font_m_24 = font_m_24
        self.font_b_18 = font_b_18
        self.font_b_24 = font_b_24
        self.font_b_36 = font_b_36
        # Assuming font_b_28 is needed as per previous code in generate_bet_slip
        try:
            self.font_b_28 = ImageFont.truetype(self.bold_font_path, 28)
        except:
            self.font_b_28 = font_b_24 # Fallback
        self.emoji_font_24 = emoji_font_24
        
        logger.info(f"BetSlipGenerator initialized with determined assets_dir: {self.assets_dir}")

    def _get_default_font(self) -> str:
        return _PATHS["DEFAULT_FONT_PATH"]

    def _get_default_bold_font(self) -> str:
        return _PATHS["DEFAULT_BOLD_FONT_PATH"]

    def _get_default_emoji_font(self) -> str:
        return _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"]

    def _format_odds_with_sign(self, odds: Optional[Any]) -> str:
        if odds is None: return "N/A"
        try:
            odds_num = int(float(odds)) 
            if odds_num > 0: return f"+{odds_num}"
            return str(odds_num)
        except (ValueError, TypeError):
            logger.warning(f"Could not format odds, invalid value: {odds}")
            return "N/A"

    def _ensure_team_dir_exists(self, league: str) -> str:
        """Ensure team logo directory exists and return path.
        Handles standard leagues like NHL and special structures for NCAA.
        Example NHL: league="NHL" -> {assets_dir}/logos/teams/HOCKEY/NHL/
        Example NCAAF: league="NCAAF" -> {assets_dir}/logos/teams/NCAA/FOOTBALL/
        """
        league_upper = league.upper() # e.g. "NHL", "NCAAF"
        
        # Path structure: {assets_dir}/logos/teams/...
        # self.league_team_base_dir already points to .../logos/teams/

        if league_upper.startswith("NCAA"):
            # For NCAA leagues like "NCAAF", "NCAAB"
            # SPORT_CATEGORY_MAP gives the specific sport (e.g., "FOOTBALL" for "NCAAF")
            specific_sport_for_ncaa = get_sport_category_for_path(league_upper)
            if specific_sport_for_ncaa == DEFAULT_FALLBACK_SPORT_CATEGORY: # If "NCAAF" isn't in map or maps to default
                logger.warning(f"NCAA league '{league_upper}' not found in SPORT_CATEGORY_MAP for specific sport, using 'UNKNOWN_NCAA_SPORT'.")
                specific_sport_for_ncaa = "UNKNOWN_NCAA_SPORT"
            # Path: .../logos/teams/NCAA/{SpecificSportLikeFootball}/
            team_dir = os.path.join(self.league_team_base_dir, "NCAA", specific_sport_for_ncaa)
        else:
            # For standard leagues like "NHL", "NBA"
            sport_category = get_sport_category_for_path(league_upper) # Main category e.g. "HOCKEY"
            # Path: .../logos/teams/{SportCategoryFromMap}/{LeagueCodeUppercase}/
            team_dir = os.path.join(self.league_team_base_dir, sport_category, league_upper)
            
        os.makedirs(team_dir, exist_ok=True)
        return team_dir

    # _get_sport_category method removed from class, uses global get_sport_category_for_path helper

    def _cleanup_cache(self):
        current_time = time.time()
        if current_time - self._last_cache_cleanup > 300:
            expired_keys = [k for k, (_, ts) in self._logo_cache.items() if current_time - ts > self._cache_expiry]
            for key in expired_keys:
                try: del self._logo_cache[key]
                except KeyError: pass
            self._last_cache_cleanup = current_time

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        try:
            cache_key = f"team_{team_name}_{league}"
            current_time = time.time()
            
            if cache_key in self._logo_cache:
                logo, timestamp = self._logo_cache[cache_key]
                if current_time - timestamp <= self._cache_expiry:
                    return logo
                else:
                    del self._logo_cache[cache_key]

            # league_team_dir now correctly uses uppercase league for non-NCAA, 
            # and NCAA/SPORT for NCAA thanks to the updated _ensure_team_dir_exists
            league_team_dir = self._ensure_team_dir_exists(league) # league is e.g. "NHL", "NCAAF"
            
            team_name_map = { # This map is very limited, direct naming is preferred
                "oilers": "edmonton_oilers",
                "bruins": "boston_bruins",
                "bengals": "cincinnati_bengals",
                "steelers": "pittsburgh_steelers",
                "lakers": "los_angeles_lakers",
                "celtics": "boston_celtics"
            }
            
            logo_filename_base = team_name_map.get(team_name.lower(), team_name.lower().replace(" ", "_"))
            logo_filename = f"{logo_filename_base}.png"
            logo_path = os.path.join(league_team_dir, logo_filename)
            logger.info(f"Attempting to load team logo from: {logo_path}") # Added log
            
            if os.path.exists(logo_path):
                try:
                    logo = Image.open(logo_path).convert("RGBA")
                    logo = logo.resize((100, 100), Image.Resampling.LANCZOS)
                    
                    self._cleanup_cache()
                    if len(self._logo_cache) >= self._max_cache_size:
                        oldest_key = min(self._logo_cache.items(), key=lambda x: x[1][1])[0]
                        del self._logo_cache[oldest_key]
                    
                    self._logo_cache[cache_key] = (logo, current_time)
                    return logo
                except Exception as e:
                    logger.error(f"Error loading logo from {logo_path}: {str(e)}")
            
            default_logo_path = _PATHS["DEFAULT_TEAM_LOGO_PATH"]
            if os.path.exists(default_logo_path):
                try:
                    default_logo = Image.open(default_logo_path).convert("RGBA")
                    default_logo = default_logo.resize((100, 100), Image.Resampling.LANCZOS)
                    logger.warning(f"Using default logo for team {team_name} (logo not found at {logo_path})")
                    return default_logo
                except Exception as e:
                    logger.error(f"Error loading default logo from {default_logo_path}: {str(e)}")
            
            logger.warning(f"No logo found for team '{team_name}' in league '{league}' (path: {logo_path}) and no default logo available.")
            return None
            
        except Exception as e:
            logger.error(f"Error in _load_team_logo for team {team_name}, league {league}: {str(e)}", exc_info=True)
            return None

    def _load_lock_icon(self) -> Optional[Image.Image]:
        if self._lock_icon_cache is None:
            try:
                lock_icon_path = _PATHS["DEFAULT_LOCK_ICON_PATH"]
                if os.path.exists(lock_icon_path):
                    with Image.open(lock_icon_path) as lock:
                        lock = lock.convert("RGBA")
                        lock = lock.resize((30, 30), Image.Resampling.LANCZOS)  
                        self._lock_icon_cache = lock.copy()
                else:
                    logger.warning(f"Lock icon not found at {lock_icon_path}")
            except Exception as e:
                logger.error(f"Error loading lock icon: {str(e)}")
        return self._lock_icon_cache

    def _load_league_logo(self, league: str) -> Optional[Image.Image]: # league is e.g. "NHL", "NCAAF"
        try:
            if not league:
                return None

            cache_key = f"league_{league}"
            current_time = time.time()

            if cache_key in self._logo_cache:
                logo, timestamp = self._logo_cache[cache_key]
                if current_time - timestamp <= self._cache_expiry:
                    return logo
                else:
                    del self._logo_cache[cache_key]
            
            # Path: {assets_dir}/logos/leagues/{SPORT_CATEGORY_FROM_MAP}/{league_code_lowercase}.png
            sport_category = get_sport_category_for_path(league.upper()) 
            logo_filename = f"{league.lower().replace(' ', '_')}.png"
            logo_path = os.path.join(self.league_logo_base_dir, sport_category, logo_filename)
            logger.info(f"Attempting to load league logo from: {logo_path}") # Added log

            # Ensure sport category directory under leagues exists
            os.makedirs(os.path.dirname(logo_path), exist_ok=True)

            if os.path.exists(logo_path):
                try:
                    with Image.open(logo_path) as img:
                        logo = img.convert('RGBA')
                        # Update cache
                        self._cleanup_cache()
                        if len(self._logo_cache) >= self._max_cache_size:
                            oldest_key = min(self._logo_cache.items(), key=lambda x: x[1][1])[0]
                            del self._logo_cache[oldest_key]
                        self._logo_cache[cache_key] = (logo.copy(), current_time) # Cache a copy
                        return logo
                except Exception as e:
                    logger.error(f"Error loading league logo from {logo_path}: {str(e)}")
            
            logger.warning(f"No logo found for league {league} (path: {logo_path})")
            return None
            
        except Exception as e:
            logger.error(f"Error in _load_league_logo for league {league}: {str(e)}", exc_info=True)
            return None

    def generate_bet_slip(
        self,
        home_team: str, away_team: str, league: Optional[str], line: str, odds: float,
        units: float, bet_id: str, timestamp: datetime, bet_type: str = "straight",
        parlay_legs: Optional[List[Dict[str, Any]]] = None, is_same_game: bool = False
    ) -> Optional[Image.Image]:
        """Generate a bet slip image for straight or parlay bets."""
        # Ensure league is provided for logo loading, default if None
        effective_league = league or "UNKNOWN_LEAGUE"
        logger.info(f"Generating bet slip - Type: {bet_type}, League: {effective_league}, BetID: {bet_id}")
        
        try:
            width = 800
            header_h = 100 
            footer_h = 80
            leg_draw_height = 180 
            num_legs = len(parlay_legs) if parlay_legs else 1
            parlay_extra_height = (num_legs - 1) * leg_draw_height if bet_type == "parlay" and parlay_legs else 0
            parlay_total_section_height = 120 if bet_type == "parlay" else 0
            base_content_height = 400 
            height = header_h + (base_content_height if bet_type == 'straight' else parlay_extra_height + leg_draw_height) + parlay_total_section_height + footer_h

            image = Image.new('RGBA', (width, height), (40, 40, 40, 255))
            draw = ImageDraw.Draw(image)

            header_y = 30 
            header_text_base = f"{effective_league.upper()} - {'Straight Bet' if bet_type == 'straight' else 'Multi-Team Parlay Bet' if bet_type == 'parlay' and not is_same_game else 'Same Game Parlay' if bet_type == 'parlay' and is_same_game else 'Bet'}"
            header_text = header_text_base.strip(" - ")
            
            league_logo_img = self._load_league_logo(effective_league)
            if league_logo_img:
                # Resize league logo for header
                max_league_logo_h = 60
                ratio = max_league_logo_h / league_logo_img.height
                new_w = int(league_logo_img.width * ratio)
                league_logo_disp = league_logo_img.resize((new_w, max_league_logo_h), Image.Resampling.LANCZOS)

                logo_x = (width - league_logo_disp.width) // 2
                logo_y = header_y - 10 
                if image.mode != 'RGBA': image = image.convert("RGBA")
                temp_layer = Image.new('RGBA', image.size, (0,0,0,0))
                temp_layer.paste(league_logo_disp, (logo_x, logo_y), league_logo_disp)
                image = Image.alpha_composite(image, temp_layer)
                draw = ImageDraw.Draw(image) 
                header_y += league_logo_disp.height + 5 
            else:
                header_y += 10 # Adjust if no logo to center text a bit

            bbox = draw.textbbox((0, 0), header_text, font=self.font_b_36)
            tw = bbox[2] - bbox[0]
            draw.text(((width - tw) / 2, header_y), header_text, fill='white', font=self.font_b_36)

            if bet_type == "straight":
                logo_y_start = header_h + 60
                logo_size = (120, 120) 

                home_logo = self._load_team_logo(home_team, effective_league)
                away_logo = self._load_team_logo(away_team, effective_league)

                if home_logo:
                    home_logo_disp = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    temp_layer_home = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_layer_home.paste(home_logo_disp, (width // 4 - logo_size[0] // 2, logo_y_start), home_logo_disp) # Corrected variable name
                    image = Image.alpha_composite(image, temp_layer_home)
                    draw = ImageDraw.Draw(image) 
                draw.text((width // 4, logo_y_start + logo_size[1] + 20), home_team, fill='white', font=self.font_b_24, anchor='mm')

                if away_logo:
                    away_logo_disp = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    temp_layer_away = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_layer_away.paste(away_logo_disp, (3 * width // 4 - logo_size[0] // 2, logo_y_start), away_logo_disp) # Corrected variable name
                    image = Image.alpha_composite(image, temp_layer_away)
                    draw = ImageDraw.Draw(image)
                draw.text((3 * width // 4, logo_y_start + logo_size[1] + 20), away_team, fill='white', font=self.font_b_24, anchor='mm')

                details_y = logo_y_start + logo_size[1] + 80
                bet_text = f"{home_team}: {line}" 
                draw.text((width // 2, details_y), bet_text, fill='white', font=self.font_m_24, anchor='mm') 

                separator_y = details_y + 40
                draw.line([(20, separator_y), (width - 20, separator_y)], fill='white', width=2)

                odds_y = separator_y + 30
                odds_text_display = self._format_odds_with_sign(odds) # Use original odds
                draw.text((width // 2, odds_y), odds_text_display, fill='white', font=self.font_b_24, anchor='mm')

                units_y = odds_y + 50  
                units_text = f"To Win {units:.2f} Units"
                units_bbox = draw.textbbox((0, 0), units_text, font=self.font_b_24)
                units_width = units_bbox[2] - units_bbox[0]
                
                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 20  
                    text_total_width = units_width + 2 * lock_icon.width + 2 * lock_spacing
                    start_x = (width - text_total_width) // 2
                    
                    if image.mode != 'RGBA': image = image.convert('RGBA')
                    temp_lock_l = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_lock_l.paste(lock_icon, (start_x, units_y - lock_icon.height // 2), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_l)
                    
                    draw = ImageDraw.Draw(image)
                    text_x = start_x + lock_icon.width + lock_spacing
                    draw.text((text_x + units_width / 2, units_y), units_text, fill=(255, 215, 0), font=self.font_b_24, anchor="mm") # Centered text
                    
                    temp_lock_r = Image.new('RGBA', image.size, (0,0,0,0))
                    temp_lock_r.paste(lock_icon, (text_x + units_width + lock_spacing, units_y - lock_icon.height // 2), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_r)
                    draw = ImageDraw.Draw(image)
                else:
                    draw.text((width // 2, units_y), units_text, fill=(255, 215, 0), font=self.font_b_24, anchor='mm')

            elif bet_type == "parlay" and parlay_legs:
                current_y_parlay = header_h + 10 # Renamed variable
                for i, leg_data in enumerate(parlay_legs):
                    if i > 0:
                        separator_y = current_y_parlay 
                        draw.line([(40, separator_y), (width - 40, separator_y)], fill=(100, 100, 100), width=1)
                        current_y_parlay += 20

                    # Use the leg's own league if available, else default to main parlay league
                    leg_effective_league = leg_data.get('league', effective_league)
                    current_y_parlay = self._draw_parlay_leg_internal(
                        image=image, draw=draw, leg=leg_data, league=leg_effective_league, 
                        width=width, start_y=current_y_parlay,
                        is_same_game=is_same_game, leg_height=leg_draw_height 
                    )
                    draw = ImageDraw.Draw(image) 

                total_y = current_y_parlay + 20
                draw.line([(40, total_y), (width - 40, total_y)], fill='white', width=2)
                total_y += 30

                total_odds_text = f"Total Odds: {self._format_odds_with_sign(odds)}" # Use overall parlay odds
                draw.text((width // 2, total_y), total_odds_text, fill='white', font=self.font_b_28, anchor='mm') 
                total_y += 40

                # Parlay units here refers to the stake on the whole parlay.
                units_text = f"Stake: {units:.2f} Units" 
                units_bbox = draw.textbbox((0, 0), units_text, font=self.font_b_24)
                units_width = units_bbox[2] - units_bbox[0]
                lock_icon = self._load_lock_icon()

                if lock_icon:
                    lock_spacing = 15
                    lock_x_left = (width - (units_width + 2 * lock_icon.width + 2 * lock_spacing)) // 2
                    if image.mode != 'RGBA': image = image.convert("RGBA")
                    
                    temp_lock_l_parlay = Image.new('RGBA', image.size, (0,0,0,0)) # Unique name
                    temp_lock_l_parlay.paste(lock_icon, (lock_x_left, total_y - lock_icon.height // 2), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_l_parlay)
                    
                    draw = ImageDraw.Draw(image) # Recreate draw after paste
                    text_x_parlay = lock_x_left + lock_icon.width + lock_spacing # For text positioning
                    draw.text((text_x_parlay + units_width / 2, total_y), units_text, fill=(255, 215, 0), font=self.font_b_24, anchor='mm') # Centered text

                    temp_lock_r_parlay = Image.new('RGBA', image.size, (0,0,0,0)) # Unique name
                    lock_x_right = text_x_parlay + units_width + lock_spacing
                    temp_lock_r_parlay.paste(lock_icon, (lock_x_right, total_y - lock_icon.height // 2), lock_icon)
                    image = Image.alpha_composite(image, temp_lock_r_parlay)
                    draw = ImageDraw.Draw(image) # Recreate draw after paste
                else: 
                    draw.text((width // 2, total_y), f"🔒 {units_text} 🔒", # Fallback with unicode emoji
                              fill=(255, 215, 0), font=self.emoji_font_24, anchor='mm')


            else: 
                 header_font_fallback = self.font_b_36 # Use an available font
                 draw.text((width // 2, height // 2), "Invalid Bet Data", fill='red', font=header_font_fallback, anchor='mm')

            footer_y_pos = height - footer_h // 2 # Adjusted for vertical centering
            bet_id_text = f"Bet #{bet_id}"
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC')
            
            bet_id_bbox = draw.textbbox((0, 0), bet_id_text, font=self.font_m_18)
            ts_bbox = draw.textbbox((0, 0), timestamp_text, font=self.font_m_18)
            
            draw.text((self.padding, footer_y_pos), bet_id_text, fill=(150, 150, 150), font=self.font_m_18, anchor='lm')
            draw.text((width - self.padding, footer_y_pos), timestamp_text, fill=(150, 150, 150), font=self.font_m_18, anchor='rm')

            logger.info(f"Bet slip PIL image generated successfully for Bet ID: {bet_id}")
            return image.convert("RGB") 

        except Exception as e:
            logger.exception(f"Error generating bet slip image for Bet ID {bet_id}: {str(e)}")
            # Fallback error image generation
            error_img_width = 800
            error_img_height = 200
            error_img = Image.new('RGB', (error_img_width, error_img_height), (40, 40, 40))
            draw_error = ImageDraw.Draw(error_img)
            try:
                error_font = self.font_m_24 # Use an existing loaded font
            except AttributeError: # Fallback if fonts not loaded
                error_font = ImageFont.load_default()
            draw_error.text((error_img_width/2, error_img_height/2), "Error Generating Bet Slip", fill="red", font=error_font, anchor="mm")
            return error_img

    def _draw_parlay_leg_internal(
        self, image: Image.Image, draw: ImageDraw.Draw, leg: Dict[str, Any], league: Optional[str],
        width: int, start_y: int, is_same_game: bool, leg_height: int
    ) -> int:
        leg_home = leg.get('home_team', leg.get('team', 'Unknown'))
        leg_away = leg.get('opponent', 'Unknown')
        leg_line = leg.get('line', 'N/A')
        leg_odds = leg.get('odds', 0)
        # Use the leg's specific league if provided, otherwise the parlay's main league
        leg_league_display = leg.get('league', league or 'UNKNOWN') 

        current_y = start_y
        logo_y = current_y + 10
        logo_disp_size = (50, 50) 
        text_start_x = 40

        # Team logo for the leg (usually the team bet on, or home team for totals)
        # The 'team' field in leg_details should be the team involved in the bet for that leg.
        team_bet_on_for_logo = leg.get('team', leg_home) # Prioritize 'team' if explicitly set for the leg
        
        # For SGPs, always try to draw a logo if a team is identified.
        # For multi-team parlays, logos per leg can make it busy, but let's try.
        draw_logos = True # Simpler: always try if team_bet_on_for_logo is known

        if draw_logos and team_bet_on_for_logo != 'Unknown':
            # Pass the leg's specific league to _load_team_logo
            team_logo = self._load_team_logo(team_bet_on_for_logo, leg_league_display) 
            if team_logo:
                logo_x = 40
                team_logo_disp = team_logo.resize(logo_disp_size, Image.Resampling.LANCZOS)
                if image.mode != 'RGBA': image = image.convert("RGBA")
                temp_layer = Image.new('RGBA', image.size, (0,0,0,0))
                temp_layer.paste(team_logo_disp, (logo_x, logo_y), team_logo_disp)
                image = Image.alpha_composite(image, temp_layer)
                draw = ImageDraw.Draw(image) 
                text_start_x = logo_x + logo_disp_size[0] + 15
            else: 
                logger.debug(f"Parlay leg logo not found for {team_bet_on_for_logo} in league {leg_league_display}")

        draw.text((text_start_x, logo_y + 5), leg_line, fill='white', font=self.font_m_24) 
        
        matchup_text_parts = []
        if leg_home != 'Unknown': matchup_text_parts.append(leg_home)
        if leg_away != 'Unknown' and leg_away != leg_home : matchup_text_parts.append(f"vs {leg_away}")
        matchup_display = " ".join(matchup_text_parts) if matchup_text_parts else team_bet_on_for_logo # Fallback to team name if no good matchup
        
        # Include player name if it's a player prop (assuming line contains player info)
        # For clarity, if leg['bet_type'] == 'player_prop', the line itself usually has the player.
        # So, leg_league_display + matchup_display should be fine.
        draw.text((text_start_x, logo_y + 40), f"{leg_league_display} - {matchup_display}", fill=(180, 180, 180), font=self.font_m_18)

        leg_odds_text = self._format_odds_with_sign(leg_odds) # Leg's specific odds
        
        # Vertically center odds in the allocated leg height
        # Using leg_height provided as param
        bbox_leg_odds = draw.textbbox((0,0), leg_odds_text, font=self.font_b_28) # Using font_b_28
        tw_leg_odds = bbox_leg_odds[2]-bbox_leg_odds[0]
        th_leg_odds = bbox_leg_odds[3]-bbox_leg_odds[1]
        
        # Calculate Y to center within the available leg_height block starting at `start_y`
        odds_y_centered = start_y + (leg_height / 2) - (th_leg_odds / 2)
        
        draw.text((width - 40 - tw_leg_odds, odds_y_centered), leg_odds_text, fill='white', font=self.font_b_28)

        return start_y + leg_height
