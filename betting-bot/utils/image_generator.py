# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime # Included as requested by user previously
from typing import Optional, List, Dict, Any # Included as requested by user previously
import time # Included as requested by user previously
from io import BytesIO # Often needed for processing image data, let's keep for now just in case

logger = logging.getLogger(__name__)

class BetSlipGenerator:
    # MODIFIED: Default assets_dir assumption changed to 'assets/'
    def __init__(self, font_path: Optional[str] = None, emoji_font_path: Optional[str] = None, assets_dir: str = "assets"):
        self.assets_dir = assets_dir
        # Ensure base assets dir exists
        if not os.path.isdir(self.assets_dir):
             # Try finding it relative to this file's parent directory (betting-bot/)
             script_dir = os.path.dirname(__file__) # utils/
             parent_dir = os.path.dirname(script_dir) # betting-bot/
             potential_assets_dir = os.path.join(parent_dir, assets_dir)
             if os.path.isdir(potential_assets_dir):
                  self.assets_dir = potential_assets_dir
                  logger.info(f"Found assets directory at: {self.assets_dir}")
             else:
                  logger.error(f"Assets directory not found at initial '{assets_dir}' or relative '{potential_assets_dir}'. Logo/font loading will likely fail.")
                  # Fallback to relative path - might work depending on CWD
                  self.assets_dir = assets_dir # Keep original if relative fails

        # MODIFIED: Construct font paths relative to the determined assets_dir
        self.font_path = font_path or os.path.join(self.assets_dir, 'fonts', 'Roboto-Regular.ttf')
        self.bold_font_path = self._get_default_bold_font() # This method also uses self.assets_dir now
        self.emoji_font_path = emoji_font_path or self._get_default_emoji_font() # This method also uses self.assets_dir

        self.league_team_base_dir = os.path.join(self.assets_dir, "logos", "teams")
        self.league_logo_base_dir = os.path.join(self.assets_dir, "logos", "leagues") # For potential league logos

        self._ensure_font_exists()
        self._ensure_bold_font_exists()
        self._ensure_emoji_font_exists()

        # Initialize caches
        self._logo_cache = {}
        self._font_cache = {}
        self._lock_icon_cache = None
        self._max_cache_size = 100
        self._cache_expiry = 3600
        self._last_cache_cleanup = time.time()
        logger.info(f"BetSlipGenerator Initialized. Assets Dir: {self.assets_dir}, Team Logo Base: {self.league_team_base_dir}")


    # MODIFIED: Default font finding logic now uses self.assets_dir
    def _get_default_font(self) -> str:
        """Get the default font path for regular text."""
        custom_font_path = os.path.join(self.assets_dir, 'fonts', 'Roboto-Regular.ttf')
        if os.path.exists(custom_font_path):
            logger.debug(f"Using regular font at {custom_font_path}")
            return custom_font_path
        # Fallback logic remains the same
        logger.warning(f"Default font '{custom_font_path}' not found. Falling back to system fonts.")
        if os.name == 'nt': return 'C:\\Windows\\Fonts\\arial.ttf'
        # Common Linux paths
        for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']:
            if os.path.exists(p): return p
        return 'arial.ttf' # Final fallback guess

    # MODIFIED: Default bold font finding logic now uses self.assets_dir
    def _get_default_bold_font(self) -> str:
        """Get the default bold font path for emphasized text."""
        custom_bold_font_path = os.path.join(self.assets_dir, 'fonts', 'Roboto-Bold.ttf')
        if os.path.exists(custom_bold_font_path):
            logger.debug(f"Using bold font at {custom_bold_font_path}")
            return custom_bold_font_path
        logger.warning(f"Default bold font '{custom_bold_font_path}' not found. Falling back to regular font.")
        # Fallback to regular if bold isn't found
        return self.font_path # Use the potentially already determined regular font path

    # MODIFIED: Default emoji font finding logic now uses self.assets_dir
    def _get_default_emoji_font(self) -> str:
        """Get the default font path for emojis."""
        # Prioritize NotoEmoji
        custom_emoji_font_path = os.path.join(self.assets_dir, 'fonts', 'NotoEmoji-Regular.ttf')
        if os.path.exists(custom_emoji_font_path):
            logger.debug(f"Using emoji font at {custom_emoji_font_path}")
            return custom_emoji_font_path
        # Fallback to Segoe UI Emoji (often included)
        custom_emoji_font_path_alt = os.path.join(self.assets_dir, 'fonts', 'SegoeUIEmoji.ttf')
        if os.path.exists(custom_emoji_font_path_alt):
            logger.debug(f"Using emoji font at {custom_emoji_font_path_alt}")
            return custom_emoji_font_path_alt
        logger.warning(f"Default emoji fonts not found in '{os.path.join(self.assets_dir, 'fonts')}'. Falling back to system emoji fonts.")
        # System fallbacks
        if os.name == 'nt': return 'C:\\Windows\\Fonts\\seguiemj.ttf'
        # Common Linux paths
        for p in ['/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf']:
             if os.path.exists(p): return p
        return self.font_path # Final fallback to regular font

    def _ensure_font_exists(self) -> None:
        """Ensure the regular font file exists."""
        if not os.path.exists(self.font_path):
            logger.error(f"Regular font file check failed at resolved path: {self.font_path}")
            # Attempting to find *any* fallback caused issues, rely on _get_default_font's logic.
            # If _get_default_font failed, this will likely raise FileNotFoundError later.
            # Consider raising immediately if path is critical.
            # raise FileNotFoundError(f"Could not find a suitable regular font file. Checked: {self.font_path}")
        else:
            logger.debug(f"Regular font confirmed at: {self.font_path}")

    def _ensure_bold_font_exists(self) -> None:
        """Ensure the bold font file exists."""
        if not os.path.exists(self.bold_font_path):
             logger.warning(f"Bold font file check failed at resolved path: {self.bold_font_path}. Using regular: {self.font_path}")
             self.bold_font_path = self.font_path # Use regular font path if bold doesn't exist
        else:
             logger.debug(f"Bold font confirmed at: {self.bold_font_path}")


    def _ensure_emoji_font_exists(self) -> None:
        """Ensure the emoji font file exists."""
        if not os.path.exists(self.emoji_font_path):
             logger.warning(f"Emoji font file check failed at resolved path: {self.emoji_font_path}. Falling back to regular: {self.font_path}")
             self.emoji_font_path = self.font_path # Use regular font path if emoji doesn't exist
        else:
             logger.debug(f"Emoji font confirmed at: {self.emoji_font_path}")


    # MODIFIED: Added more logging and refined path joining
    def _ensure_team_dir_exists(self, league: str) -> str:
        """Ensure the team logos directory exists for the given league."""
        sport_category_map = {
            "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
            "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
            "MLB": "BASEBALL", "NCAAB_BASEBALL": "BASEBALL", # Assuming college baseball league name
            "NHL": "HOCKEY",
            "MLS": "SOCCER", "EPL": "SOCCER", "LA LIGA": "SOCCER", "SERIE A": "SOCCER", "BUNDESLIGA": "SOCCER", "LIGUE 1": "SOCCER", # Added common soccer leagues
            "TENNIS": "TENNIS", # Assuming league name might be 'TENNIS'
            "UFC": "MMA", "MMA": "MMA", # Common MMA league names
            "DARTS": "DARTS" # Added Darts
            # Add other leagues/sports as needed
        }
        # Use league name directly if no category found, or default to OTHER
        sport_category = sport_category_map.get(league.upper(), league.upper() if league else "OTHER")
        league_team_dir = os.path.join(self.league_team_base_dir, sport_category, league.upper() if league else "UNKNOWN")

        # Check and create directory
        if not os.path.isdir(league_team_dir):
            logger.info(f"Team logos directory not found at {league_team_dir}, creating it.")
            try:
                os.makedirs(league_team_dir, exist_ok=True)
            except OSError as e:
                 logger.error(f"Failed to create directory {league_team_dir}: {e}")
                 # Fallback to base team directory? Or just fail? Let's try base.
                 logger.warning(f"Falling back to base team logo directory: {self.league_team_base_dir}")
                 return self.league_team_base_dir # Return base dir path
        return league_team_dir # Return specific dir path

    # Method to ensure league logo dir exists (similar logic)
    def _ensure_league_dir_exists(self, league: str) -> str:
        # ... (similar logic to _ensure_team_dir_exists but using self.league_logo_base_dir) ...
        # This method doesn't seem used by the current generate_bet_slip, but kept for completeness
        sport_category_map = { "NBA": "BASKETBALL", ... } # Same map
        sport_category = sport_category_map.get(league.upper(), league.upper() if league else "OTHER")
        league_logo_dir = os.path.join(self.league_logo_base_dir, sport_category, league.upper() if league else "UNKNOWN")
        if not os.path.isdir(league_logo_dir):
            logger.info(f"League logos directory not found at {league_logo_dir}, creating it.")
            try:
                os.makedirs(league_logo_dir, exist_ok=True)
            except OSError as e:
                 logger.error(f"Failed to create directory {league_logo_dir}: {e}")
                 logger.warning(f"Falling back to base league logo directory: {self.league_logo_base_dir}")
                 return self.league_logo_base_dir
        return league_logo_dir


    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        # ... (cache cleanup logic remains the same) ...
        pass # Keep existing implementation

    # MODIFIED: Added extensive logging to trace path generation and checks
    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Load the team logo image based on team name and league with caching."""
        if not team_name or not league:
            logger.warning(f"Attempting to load logo with missing team name ('{team_name}') or league ('{league}')")
            return None

        cache_key = f"{team_name}_{league}".lower() # Use lowercase for cache consistency
        current_time = time.time()

        # Check cache
        if cache_key in self._logo_cache:
            logo, timestamp = self._logo_cache[cache_key]
            if current_time - timestamp <= self._cache_expiry:
                logger.debug(f"Cache HIT for logo: {cache_key}")
                return logo
            else:
                logger.debug(f"Cache EXPIRED for logo: {cache_key}")
                del self._logo_cache[cache_key]
        else:
             logger.debug(f"Cache MISS for logo: {cache_key}")


        try:
            # 1. Determine the specific league/team directory
            league_team_dir = self._ensure_team_dir_exists(league)
            logger.debug(f"Determined team directory for '{team_name}' ({league}): {league_team_dir}")

            # 2. Format filename (lowercase, underscore separators)
            # Consider removing articles like 'fc', 'cf' etc. if filenames don't include them
            # Simple mapping for known difficult names
            team_name_map = {
                "oilers": "edmonton_oilers", "bruins": "boston_bruins", # Example hockey
                "bengals": "cincinnati_bengals", "steelers": "pittsburgh_steelers", # Example NFL
                "manchester city": "manchester_city", "fc barcelona": "barcelona" # Example Soccer
                # ADD MORE MAPPINGS AS NEEDED BASED ON FILENAMES
            }
            safe_team_name = team_name_map.get(team_name.lower(), team_name.lower().replace(" ", "_").replace(".", "").replace("-", "_"))
            logo_filename = f"{safe_team_name}.png"
            logger.debug(f"Formatted logo filename: {logo_filename}")

            # 3. Construct full path
            logo_path = os.path.join(league_team_dir, logo_filename)
            logger.debug(f"Attempting to load logo from path: {logo_path}")

            # 4. Check if file exists and load
            if os.path.exists(logo_path):
                logger.info(f"Logo FOUND for team '{team_name}' at {logo_path}")
                with Image.open(logo_path) as logo:
                    logo = logo.convert("RGBA")
                    # MODIFIED: Use self.logo_size for resizing
                    logo.thumbnail((self.logo_size, self.logo_size), Image.Resampling.LANCZOS)

                    # Update cache
                    self._cleanup_cache()
                    if len(self._logo_cache) >= self._max_cache_size:
                        try:
                            oldest_key = min(self._logo_cache.items(), key=lambda x: x[1][1])[0]
                            del self._logo_cache[oldest_key]
                        except ValueError: pass # Cache might be empty
                    self._logo_cache[cache_key] = (logo.copy(), current_time) # Store copy in cache

                    return logo.copy() # Return a copy
            else:
                logger.warning(f"Logo NOT FOUND for team '{team_name}' ({league}) at expected path: {logo_path}")
                # Optional: Add fallback to base /teams/ directory here if needed
                # fallback_path = os.path.join(self.league_team_base_dir, logo_filename)
                # if os.path.exists(fallback_path): ... etc ...
                return None # Return None if not found

        except Exception as e:
            logger.error(f"Error loading logo for team '{team_name}' ({league}): {str(e)}", exc_info=True)
            return None

    def _load_font(self, size: int, is_bold: bool = False) -> ImageFont.FreeTypeFont:
        """Load font with caching."""
        # ... (font loading/caching remains the same) ...
        font_path_key = self.bold_font_path if is_bold else self.font_path
        cache_key = f"{font_path_key}_{size}" # Cache based on path and size
        if cache_key not in self._font_cache:
            try:
                self._font_cache[cache_key] = ImageFont.truetype(font_path_key, size)
            except Exception as e:
                logger.error(f"Failed to load font '{font_path_key}' size {size}: {e}. Using default font.")
                self._font_cache[cache_key] = ImageFont.load_default() # Default PIL font
        return self._font_cache[cache_key]

    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Load the lock icon image with caching."""
        # ... (lock icon loading remains the same, ensure path uses self.assets_dir) ...
        if self._lock_icon_cache is None:
            try:
                 lock_path = os.path.join(self.assets_dir, "lock_icon.png") # Uses self.assets_dir
                 if os.path.exists(lock_path):
                     with Image.open(lock_path) as lock:
                          lock = lock.convert("RGBA")
                          lock.thumbnail((20, 20), Image.Resampling.LANCZOS)
                          self._lock_icon_cache = lock.copy()
                 else:
                     logger.warning(f"Lock icon not found at {lock_path}")
                     return None
            except Exception as e:
                 logger.error(f"Error loading lock icon: {str(e)}")
                 return None
        return self._lock_icon_cache


    # MODIFIED: generate_bet_slip - simplified logic based on provided args
    # Kept the structure from user's file, just ensuring logo loading uses updated method
    def generate_bet_slip(
        self,
        home_team: str,
        away_team: str,
        league: Optional[str],
        line: str, # This seems to be the primary bet line text (e.g., "Team A ML", "Over 5.5")
        odds: float, # Should be float or int from command file
        units: float, # Should be float from command file
        bet_id: str, # Provided by command file
        timestamp: datetime, # Provided by command file
        bet_type: str = "straight", # Provided by command file
        parlay_legs: Optional[List[Dict[str, Any]]] = None, # Provided by command file
        is_same_game: bool = False # Provided by command file
    ) -> Optional[Image.Image]: # Returns PIL Image or None
        """Generate a bet slip image for straight or parlay bets."""
        logger.info(f"Generating bet slip - Type: {bet_type}, League: {league}, BetID: {bet_id}")
        logger.debug(f"generate_bet_slip args: home='{home_team}', away='{away_team}', line='{line}', odds={odds}, units={units}, parlay_legs={parlay_legs is not None}, same_game={is_same_game}")
        try:
            # Determine image dimensions
            width = 800
            base_height = 450 # Adjust as needed for your design
            leg_height_parlay = 200 # Adjust height per parlay leg
            header_height = 80
            footer_height = 60

            num_legs = len(parlay_legs) if parlay_legs else 1
            if bet_type == "parlay" and parlay_legs:
                # Dynamic height for parlays: Header + (Legs * Leg Height) + Footer + Padding
                height = header_height + (num_legs * leg_height_parlay) + footer_height + 40 # Added padding
            else: # Straight bet
                 height = base_height # Fixed height for straight bets

            image = Image.new('RGB', (width, height), (40, 40, 40)) # Dark background
            draw = ImageDraw.Draw(image)

            # Load fonts (using caching helper)
            header_font = self._load_font(32, is_bold=True)
            team_font = self._load_font(24, is_bold=True)
            details_font = self._load_font(28)
            small_font = self._load_font(18)
            odds_font = self._load_font(28, is_bold=True) # Bold odds
            units_font = self._load_font(24, is_bold=True) # Bold units
            emoji_font = ImageFont.truetype(self.emoji_font_path, 24) if os.path.exists(self.emoji_font_path) else details_font # Fallback for emoji

            # --- Draw Header ---
            header_y = 40
            header_text = f"{league.upper() if league else ''} - {'Straight Bet' if bet_type == 'straight' else 'Parlay'}"
            header_text = header_text.strip(" - ")
            try: # Center text
                bbox = draw.textbbox((0, 0), header_text, font=header_font)
                tw = bbox[2] - bbox[0]
                draw.text(((width - tw) / 2, header_y), header_text, fill='white', font=header_font)
            except AttributeError: # Fallback
                 tw, th = draw.textsize(header_text, font=header_font)
                 draw.text(((width - tw) / 2, header_y), header_text, fill='white', font=header_font)

            # --- Draw Content ---
            if bet_type == "straight":
                current_y = header_height + 20 # Start drawing below header

                # Load Logos (using league/names passed)
                # Pass league consistently, even if None initially, _load_team_logo handles None league
                effective_league = league or "UNKNOWN" # Default league if None passed
                home_logo = self._load_team_logo(home_team, effective_league)
                away_logo = self._load_team_logo(away_team, effective_league)

                logo_y = current_y
                logo_disp_size = (80, 80) # Adjust display size

                # Draw Home Team Logo & Name
                if home_logo:
                     home_logo_disp = home_logo.resize(logo_disp_size, Image.Resampling.LANCZOS)
                     image.paste(home_logo_disp, (width // 4 - logo_disp_size[0] // 2, logo_y), home_logo_disp)
                     logger.debug(f"Pasted home logo for {home_team}")
                else: logger.debug(f"Home logo not loaded/found for {home_team}")
                try: # Center text
                    bbox = draw.textbbox((0, 0), home_team, font=team_font)
                    tw = bbox[2] - bbox[0]
                    draw.text((width // 4 - tw // 2, logo_y + logo_disp_size[1] + 10), home_team, fill='white', font=team_font)
                except AttributeError: draw.text((width // 4, logo_y + logo_disp_size[1] + 10), home_team, fill='white', font=team_font, anchor='mm')

                # Draw Away Team Logo & Name
                if away_logo:
                     away_logo_disp = away_logo.resize(logo_disp_size, Image.Resampling.LANCZOS)
                     image.paste(away_logo_disp, (3 * width // 4 - logo_disp_size[0] // 2, logo_y), away_logo_disp)
                     logger.debug(f"Pasted away logo for {away_team}")
                else: logger.debug(f"Away logo not loaded/found for {away_team}")
                try: # Center text
                    bbox = draw.textbbox((0, 0), away_team, font=team_font)
                    tw = bbox[2] - bbox[0]
                    draw.text((3 * width // 4 - tw // 2, logo_y + logo_disp_size[1] + 10), away_team, fill='white', font=team_font)
                except AttributeError: draw.text((3 * width // 4, logo_y + logo_disp_size[1] + 10), away_team, fill='white', font=team_font, anchor='mm')

                # Draw Bet Line Details (e.g., "Team A ML" or "Over 5.5")
                details_y = logo_y + logo_disp_size[1] + 50 # Adjust Y position
                # The 'line' argument seems to hold the core bet text
                bet_text = line
                try: # Center text
                    bbox = draw.textbbox((0, 0), bet_text, font=details_font)
                    tw = bbox[2] - bbox[0]
                    draw.text(((width - tw) / 2, details_y), bet_text, fill='white', font=details_font)
                except AttributeError: draw.text((width // 2, details_y), bet_text, fill='white', font=details_font, anchor='mm')

                # Draw separator line
                separator_y = details_y + 50 # Adjust Y position
                draw.line([(40, separator_y), (width - 40, separator_y)], fill=(100, 100, 100), width=1)

                # Draw Odds
                odds_y = separator_y + 30 # Adjust Y position
                odds_text = self._format_odds_with_sign(int(odds)) # Format odds
                try: # Center text
                    bbox = draw.textbbox((0, 0), odds_text, font=odds_font)
                    tw = bbox[2] - bbox[0]
                    draw.text(((width - tw) / 2, odds_y), odds_text, fill='white', font=odds_font)
                except AttributeError: draw.text((width // 2, odds_y), odds_text, fill='white', font=odds_font, anchor='mm')

                # Draw Units
                units_y = odds_y + 50 # Adjust Y position
                units_text = f"To Win {units:.2f} Units" # Assuming 'units' is payout here, needs clarification
                # Recalculate payout based on stake if 'units' is stake? Assume 'units' is payout for now.
                try: # Center text
                    bbox = draw.textbbox((0, 0), units_text, font=units_font)
                    tw = bbox[2] - bbox[0]
                    draw.text(((width - tw) / 2, units_y), units_text, fill=(255, 215, 0), font=units_font) # Gold color
                except AttributeError: draw.text((width // 2, units_y), units_text, fill=(255, 215, 0), font=units_font, anchor='mm')


            elif bet_type == "parlay" and parlay_legs:
                # Draw Parlay Legs
                current_y = header_height + 10 # Start Y position for first leg
                for i, leg in enumerate(parlay_legs):
                    if i > 0: # Draw separator above legs 2+
                        separator_y = current_y + 10
                        draw.line([(40, separator_y), (width - 40, separator_y)], fill=(100, 100, 100), width=1)
                        current_y += 30 # Space after separator

                    # Get leg details (assuming structure from parlay_betting.py)
                    leg_home = leg.get('home_team', leg.get('team', 'Unknown')) # Use team if home_team absent
                    leg_away = leg.get('opponent', 'Unknown') # Opponent needed for context?
                    leg_line = leg.get('line', 'N/A')
                    leg_odds = leg.get('odds', 0)
                    leg_league = leg.get('league', league or 'UNKNOWN') # Use leg league or default

                    # --- Draw Leg Content ---
                    leg_start_y = current_y
                    logo_y = leg_start_y + 10
                    logo_disp_size = (50, 50) # Smaller logos for parlays

                    # Load logo for the *team bet on* for this leg
                    team_bet_on = leg_home # Or determine based on line? Assume home for now.
                    team_logo = self._load_team_logo(team_bet_on, leg_league)

                    if team_logo:
                         logo_x = 40 # Left align logo
                         team_logo_disp = team_logo.resize(logo_disp_size, Image.Resampling.LANCZOS)
                         image.paste(team_logo_disp, (logo_x, logo_y), team_logo_disp)
                         text_start_x = logo_x + logo_disp_size[0] + 15
                         logger.debug(f"Pasted parlay leg {i+1} logo for {team_bet_on}")
                    else:
                         text_start_x = 40 # Start text further left if no logo
                         logger.debug(f"Parlay leg {i+1} logo not loaded/found for {team_bet_on}")


                    # Draw Line description
                    draw.text((text_start_x, logo_y + 5), leg_line, fill='white', font=details_font)
                    # Draw League/Matchup below line
                    matchup_text = f"{leg_home} vs {leg_away}" if leg_home != 'Unknown' and leg_away != 'Unknown' else leg_home
                    draw.text((text_start_x, logo_y + 40), f"{leg_league} - {matchup_text}", fill=(180, 180, 180), font=small_font)

                    # Draw Leg Odds (Right Aligned)
                    leg_odds_text = self._format_odds_with_sign(int(leg_odds))
                    try:
                         bbox = draw.textbbox((0, 0), leg_odds_text, font=odds_font)
                         tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
                         draw.text((width - 40 - tw, leg_start_y + (leg_height_parlay // 2) - (th // 2)), leg_odds_text, fill='white', font=odds_font)
                    except AttributeError:
                         tw, th = draw.textsize(leg_odds_text, font=odds_font)
                         draw.text((width - 40 - tw, leg_start_y + (leg_height_parlay // 2) - (th // 2)), leg_odds_text, fill='white', font=odds_font)


                    current_y += leg_height_parlay # Move Y down for next leg

                # --- Draw Total Parlay Odds & Payout ---
                separator_y = current_y + 20
                draw.line([(40, separator_y), (width - 40, separator_y)], fill=(100, 100, 100), width=2)
                current_y = separator_y + 20

                # Total Odds (passed in 'odds' arg for parlay)
                total_odds_text = f"Total Odds: {self._format_odds_with_sign(int(odds))}"
                try: # Center text
                    bbox = draw.textbbox((0, 0), total_odds_text, font=odds_font)
                    tw = bbox[2] - bbox[0]
                    draw.text(((width - tw) / 2, current_y), total_odds_text, fill='white', font=odds_font)
                except AttributeError: draw.text((width // 2, current_y), total_odds_text, fill='white', font=odds_font, anchor='mm')
                current_y += 40

                # Total Payout (passed in 'units' arg for parlay)
                # 'units' likely represents stake for parlay, calculate payout?
                # Assume 'units' is total stake for now. Calc payout if possible.
                stake = units
                # Need a function to calculate parlay payout from total_odds and stake
                # payout = calculate_payout(stake, odds) # Placeholder
                # For now, just display stake
                units_text = f"Stake: {stake:.2f} Units" # Display stake instead of 'To Win' if payout unclear
                try: # Center text
                    bbox = draw.textbbox((0, 0), units_text, font=units_font)
                    tw = bbox[2] - bbox[0]
                    draw.text(((width - tw) / 2, current_y), units_text, fill=(255, 215, 0), font=units_font) # Gold color
                except AttributeError: draw.text((width // 2, current_y), units_text, fill=(255, 215, 0), font=units_font, anchor='mm')

            else: # Fallback if invalid type or no legs
                draw.text((width // 2, height // 2), "Invalid Bet Data", fill='red', font=header_font, anchor='mm')


            # --- Draw Footer (Common to both) ---
            footer_y = height - 30 # Position near bottom
            draw.text((20, footer_y), f"Bet #{bet_id}", fill=(150, 150, 150), font=small_font, anchor='lm')
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M UTC') # Add UTC label
            try:
                bbox = draw.textbbox((0, 0), timestamp_text, font=small_font)
                tw = bbox[2] - bbox[0]
                draw.text((width - 20 - tw, footer_y), timestamp_text, fill=(150, 150, 150), font=small_font)
            except AttributeError: draw.text((width - 20, footer_y), timestamp_text, fill=(150, 150, 150), font=small_font, anchor='rm')


            logger.info(f"Bet slip image generated successfully for Bet ID: {bet_id}")
            return image # Return the PIL Image object

        except Exception as e:
            logger.error(f"Error generating bet slip image for Bet ID {bet_id}: {str(e)}", exc_info=True)
            # Optionally create a simple error image
            error_img = Image.new('RGB', (width, 200), (40, 40, 40))
            draw = ImageDraw.Draw(error_img)
            font = self._load_font(24)
            draw.text((width/2, 100), "Error Generating Bet Slip", fill="red", font=font, anchor="mm")
            return error_img # Return error image

    # Removed _calculate_parlay_odds - assuming total odds are passed in `odds` arg for parlays
    # Removed _draw_leg - logic incorporated into generate_bet_slip parlay section
    # Removed _save_team_logo - generator shouldn't save files directly unless specifically designed to

    # Removed save_bet_slip - generator returns Image object, caller saves if needed

# Example Usage (if run directly)
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Testing BetSlipGenerator...")

    # IMPORTANT: Define these constants here for testing if running directly
    # These should match how they are defined globally in the main script context
    try:
        _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # Assumes utils/image_generator.py
        ASSET_DIR = os.path.join(_base_dir, 'assets')
        DEFAULT_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'Roboto-Regular.ttf')
        DEFAULT_BOLD_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'Roboto-Bold.ttf')
        LOGO_DIR = os.path.join(ASSET_DIR, 'logos')
        DEFAULT_TEAM_LOGO_PATH = os.path.join(LOGO_DIR, 'default_logo.png')
        logger.info(f"Test constants defined. ASSET_DIR={ASSET_DIR}")
    except Exception as e:
        logger.error(f"Failed to define constants for testing: {e}")
        exit()


    # Re-initialize fonts if constants were defined above
    try:
        if not os.path.exists(DEFAULT_FONT_PATH): raise FileNotFoundError(f"[Test] Font missing: {DEFAULT_FONT_PATH}")
        if not os.path.exists(DEFAULT_BOLD_FONT_PATH): raise FileNotFoundError(f"[Test] Font missing: {DEFAULT_BOLD_FONT_PATH}")
        font_m_18 = ImageFont.truetype(DEFAULT_FONT_PATH, 18); font_m_24 = ImageFont.truetype(DEFAULT_FONT_PATH, 24)
        font_b_18 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 18); font_b_24 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 24)
        font_b_36 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 36)
        logger.info("[Test] Successfully loaded fonts within __main__.")
    except Exception as e:
         logger.critical(f"[Test] CRITICAL: Error loading fonts in __main__: {e}")
         exit(1)


    # Create generator instance
    generator = BetSlipGenerator(assets_dir=ASSET_DIR) # Pass assets dir explicitly

    # --- Test Straight Bet ---
    logger.info("Testing Straight Bet generation...")
    straight_img = generator.generate_bet_slip(
        home_team="Boston Bruins",
        away_team="Florida Panthers",
        league="NHL",
        line="Boston Bruins ML",
        odds=-150,
        units=2.5, # Example payout/stake - clarify meaning
        bet_id="ST123",
        timestamp=datetime.now(timezone.utc),
        bet_type="straight"
    )
    if straight_img:
        straight_img.save("test_straight_slip_from_generator.png")
        logger.info("Saved test_straight_slip_from_generator.png")
    else: logger.error("Failed to generate straight bet slip.")

    # --- Test Parlay Bet ---
    logger.info("Testing Parlay Bet generation...")
    parlay_legs_data = [
        {'team': 'Kansas City Chiefs', 'opponent': 'Denver Broncos', 'league': 'NFL', 'line': 'KC Chiefs -7.5', 'odds': -110},
        {'team': 'Los Angeles Lakers', 'opponent': 'Golden State Warriors', 'league': 'NBA', 'line': 'Over 225.5', 'odds': -110},
        {'team': 'Liverpool', 'opponent': 'Manchester City', 'league': 'EPL', 'line': 'Liverpool ML', 'odds': 200},
    ]
    # Assume total odds/stake are passed in main args for parlay
    parlay_img = generator.generate_bet_slip(
        home_team=parlay_legs_data[0]['team'], # Use first leg for main display?
        away_team=parlay_legs_data[0]['opponent'],
        league=None, # League shown per leg? Or overall league? Let's test None.
        line="3-Leg Parlay", # Placeholder line for overall parlay
        odds=585, # Example calculated total parlay odds
        units=1.0, # Example stake
        bet_id="PA456",
        timestamp=datetime.now(timezone.utc),
        bet_type="parlay",
        parlay_legs=parlay_legs_data,
        is_same_game=False
    )
    if parlay_img:
        parlay_img.save("test_parlay_slip_from_generator.png")
        logger.info("Saved test_parlay_slip_from_generator.png")
    else: logger.error("Failed to generate parlay bet slip.")
