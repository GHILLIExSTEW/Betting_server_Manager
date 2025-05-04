# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class BetSlipGenerator:
    def __init__(self, font_path: Optional[str] = None, emoji_font_path: Optional[str] = None, assets_dir: str = "betting-bot/static/"):
        self.font_path = font_path or self._get_default_font()
        self.bold_font_path = self._get_default_bold_font()
        self.emoji_font_path = emoji_font_path or self._get_default_emoji_font()
        self.assets_dir = assets_dir
        self.league_team_base_dir = os.path.join(self.assets_dir, "logos/teams")
        self.league_logo_base_dir = os.path.join(self.assets_dir, "logos/leagues")
        self._ensure_font_exists()
        self._ensure_bold_font_exists()
        self._ensure_emoji_font_exists()

    def _get_default_font(self) -> str:
        """Get the default font path for regular text."""
        custom_font_path = "betting-bot/static/fonts/Roboto-Regular.ttf"
        if os.path.exists(custom_font_path):
            logger.debug(f"Using regular font at {custom_font_path}")
            return custom_font_path
        if os.name == 'nt':  # Windows
            return 'C:\\Windows\\Fonts\\arial.ttf'
        else:  # Linux/Mac
            return '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

    def _get_default_bold_font(self) -> str:
        """Get the default bold font path for emphasized text."""
        custom_bold_font_path = "betting-bot/static/fonts/Roboto-Bold.ttf"
        if os.path.exists(custom_bold_font_path):
            logger.debug(f"Using bold font at {custom_bold_font_path}")
            return custom_bold_font_path
        logger.debug("Bold font not found, falling back to regular font")
        return self._get_default_font()

    def _get_default_emoji_font(self) -> str:
        """Get the default font path for emojis."""
        custom_emoji_font_path = "betting-bot/static/fonts/NotoEmoji-Regular.ttf"
        if os.path.exists(custom_emoji_font_path):
            logger.debug(f"Using emoji font at {custom_emoji_font_path}")
            return custom_emoji_font_path
        custom_emoji_font_path = "betting-bot/static/fonts/SegoeUIEmoji.ttf"
        if os.path.exists(custom_emoji_font_path):
            logger.debug(f"Using emoji font at {custom_emoji_font_path}")
            return custom_emoji_font_path
        if os.name == 'nt':
            return 'C:\\Windows\\Fonts\\seguiemj.ttf'
        else:
            return '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf'

    def _ensure_font_exists(self) -> None:
        """Ensure the regular font file exists."""
        if not os.path.exists(self.font_path):
            logger.warning(f"Font file not found at {self.font_path}")
            for font in ['Arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']:
                if os.path.exists(font):
                    self.font_path = font
                    logger.debug(f"Falling back to regular font at {self.font_path}")
                    break
            else:
                raise FileNotFoundError(
                    "Could not find a suitable font file. Please place 'Roboto-Regular.ttf' in betting-bot/static/fonts/"
                )

    def _ensure_bold_font_exists(self) -> None:
        """Ensure the bold font file exists."""
        if not os.path.exists(self.bold_font_path):
            logger.warning(f"Bold font file not found at {self.bold_font_path}. Falling back to regular font.")
            self.bold_font_path = self.font_path

    def _ensure_emoji_font_exists(self) -> None:
        """Ensure the emoji font file exists."""
        if not os.path.exists(self.emoji_font_path):
            logger.warning(f"Emoji font file not found at {self.emoji_font_path}")
            for font in ['seguiemj.ttf', 'SegoeUIEmoji.ttf', 'NotoEmoji-Regular.ttf']:
                if os.path.exists(font):
                    self.emoji_font_path = font
                    logger.debug(f"Falling back to emoji font at {self.emoji_font_path}")
                    break
            else:
                logger.error("Could not find a suitable emoji font file. Falling back to text-based lock symbol.")
                self.emoji_font_path = self.font_path

    def _ensure_team_dir_exists(self, league: str) -> str:
        """Ensure the team logos directory exists for the given league."""
        sport_category = {
            "NBA": "BASKETBALL",
            "NFL": "FOOTBALL",
            "MLB": "BASEBALL",
            "NHL": "HOCKEY",
            "NCAAB": "BASKETBALL",
            "NCAAF": "FOOTBALL",
            "Soccer": "SOCCER",
            "Tennis": "TENNIS",
            "UFC/MMA": "MMA"
        }.get(league, "OTHER")
        league_team_dir = os.path.join(self.league_team_base_dir, sport_category, league.upper())
        if not os.path.exists(league_team_dir):
            logger.warning(f"Team logos directory not found at {league_team_dir}")
            os.makedirs(league_team_dir, exist_ok=True)
        return league_team_dir

    def _ensure_league_dir_exists(self, league: str) -> str:
        """Ensure the league logos directory exists for the given league."""
        sport_category = {
            "NBA": "BASKETBALL",
            "NFL": "FOOTBALL",
            "MLB": "BASEBALL",
            "NHL": "HOCKEY",
            "NCAAB": "BASKETBALL",
            "NCAAF": "FOOTBALL",
            "Soccer": "SOCCER",
            "Tennis": "TENNIS",
            "UFC/MMA": "MMA"
        }.get(league, "OTHER")
        league_logo_dir = os.path.join(self.league_logo_base_dir, sport_category, league.upper())
        if not os.path.exists(league_logo_dir):
            logger.warning(f"League logos directory not found at {league_logo_dir}")
            os.makedirs(league_logo_dir, exist_ok=True)
        return league_logo_dir

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        """Load the league logo image based on league name."""
        try:
            league_logo_dir = self._ensure_league_dir_exists(league)
            logo_filename = league.lower() + ".png"
            logo_path = os.path.join(league_logo_dir, logo_filename)
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA")
                logo = logo.resize((30, 30), Image.Resampling.LANCZOS)
                return logo
            else:
                logger.warning(f"League logo not found for {league} at {logo_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading league logo for {league}: {str(e)}")
            return None

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        """Load the team logo image based on team name and league."""
        try:
            league_team_dir = self._ensure_team_dir_exists(league)
            team_name_map = {
                "oilers": "edmonton_oilers",
                "bruins": "boston_bruins",
                "bengals": "cincinnati_bengals",
                "steelers": "pittsburgh_steelers"
            }
            logo_filename = team_name_map.get(team_name.lower(), team_name.lower().replace(" ", "_")) + ".png"
            logo_path = os.path.join(league_team_dir, logo_filename)
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA")
                logo = logo.resize((100, 100), Image.Resampling.LANCZOS)
                return logo
            else:
                logger.warning(f"Logo not found for team {team_name} at {logo_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading logo for team {team_name}: {str(e)}")
            return None

    def _load_lock_icon(self) -> Optional[Image.Image]:
        """Load the lock icon image."""
        try:
            lock_path = os.path.join(self.assets_dir, "lock_icon.png")
            if os.path.exists(lock_path):
                lock = Image.open(lock_path).convert("RGBA")
                lock = lock.resize((20, 20), Image.Resampling.LANCZOS)
                return lock
            else:
                logger.warning(f"Lock icon not found at {lock_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading lock icon: {str(e)}")
            return None

    def generate_bet_slip(
        self,
        home_team: str,
        away_team: str,
        league: str,
        line: str,
        odds: float,
        units: float,
        bet_id: str,
        timestamp: datetime,
        bet_type: str = "straight",
        parlay_legs: Optional[List[Dict[str, Any]]] = None,
        is_same_game: bool = False
    ) -> Image.Image:
        """Generate a bet slip image for straight or parlay bets."""
        try:
            # Set dimensions
            width = 800
            height = 450  # Reduced height for straight bets
            image = Image.new('RGB', (width, height), (40, 40, 40))
            draw = ImageDraw.Draw(image)

            # Load fonts
            try:
                header_font = ImageFont.truetype(self.font_path, 32)  # Larger font for header
                team_font = ImageFont.truetype(self.font_path, 24)  # Larger font for team names
                details_font = ImageFont.truetype(self.font_path, 28)  # For bet details
                small_font = ImageFont.truetype(self.font_path, 18)  # For bet ID and timestamp
            except Exception as e:
                logger.error(f"Failed to load fonts: {e}. Using default font.")
                header_font = team_font = details_font = small_font = ImageFont.load_default()

            # Draw header
            header_y = 40
            header_text = f"{league} - {'Straight Bet' if bet_type == 'straight' else 'Parlay'}"
            draw.text((width // 2, header_y), header_text, fill='white', font=header_font, anchor='mm')

            if bet_type == "straight":
                # Load and draw team logos
                logo_y = header_y + 60
                logo_size = (120, 120)  # Larger logos

                # Draw home team logo and name
                home_logo = self._load_team_logo(home_team, league)
                if home_logo:
                    home_logo = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    image.paste(home_logo, (width // 4 - logo_size[0] // 2, logo_y), home_logo)
                draw.text((width // 4, logo_y + logo_size[1] + 20), home_team, fill='white', font=team_font, anchor='mm')

                # Draw away team logo and name
                away_logo = self._load_team_logo(away_team, league)
                if away_logo:
                    away_logo = away_logo.resize(logo_size, Image.Resampling.LANCZOS)
                    image.paste(away_logo, (3 * width // 4 - logo_size[0] // 2, logo_y), away_logo)
                draw.text((3 * width // 4, logo_y + logo_size[1] + 20), away_team, fill='white', font=team_font, anchor='mm')

                # Draw bet details
                details_y = logo_y + logo_size[1] + 80
                bet_text = f"{home_team}: {line}"
                draw.text((width // 2, details_y), bet_text, fill='white', font=details_font, anchor='mm')

                # Draw separator line
                separator_y = details_y + 40
                draw.line([(20, separator_y), (width - 20, separator_y)], fill='white', width=2)

                # Draw odds below separator
                odds_y = separator_y + 30
                odds_text = f"{odds:+.0f}"
                draw.text((width // 2, odds_y), odds_text, fill='white', font=details_font, anchor='mm')

                # Draw units with lock symbols
                units_y = odds_y + 40
                units_text = f"To Win {units:.2f} Units"
                units_bbox = draw.textbbox((0, 0), units_text, font=details_font)
                units_width = units_bbox[2] - units_bbox[0]
                
                # Load and place lock icons
                lock_icon = self._load_lock_icon()
                if lock_icon:
                    lock_spacing = 15
                    lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
                    image.paste(lock_icon, (lock_x_left, units_y - lock_icon.height // 2), lock_icon)
                    lock_x_right = lock_x_left + units_width + lock_icon.width + 2 * lock_spacing
                    image.paste(lock_icon, (lock_x_right, units_y - lock_icon.height // 2), lock_icon)
                    
                    # Draw units text
                    draw.text(
                        (width // 2, units_y),
                        units_text,
                        fill=(255, 215, 0),  # Gold color
                        font=details_font,
                        anchor='mm'
                    )
                else:
                    # Fallback to emoji locks
                    draw.text(
                        (width // 2, units_y),
                        f"🔒 {units_text} 🔒",
                        fill=(255, 215, 0),
                        font=details_font,
                        anchor='mm'
                    )

                # Draw footer (bet ID and timestamp)
                footer_y = height - 30
                draw.text((20, footer_y), f"Bet #{bet_id}", fill=(150, 150, 150), font=small_font, anchor='lm')
                timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M')
                draw.text((width - 20, footer_y), timestamp_text, fill=(150, 150, 150), font=small_font, anchor='rm')

            else:
                # Handle parlay bets (existing parlay code)
                # ... existing parlay code ...
                pass

            return image

        except Exception as e:
            logger.error(f"Error generating bet slip: {str(e)}")
            raise

    def _draw_leg(
        self,
        image: Image.Image,
        draw: ImageDraw.Draw,
        leg: Dict[str, Any],
        league: str,
        width: int,
        start_y: int,
        team_font: ImageFont.FreeTypeFont,
        odds_font: ImageFont.FreeTypeFont,
        units_font: ImageFont.FreeTypeFont,
        emoji_font: ImageFont.FreeTypeFont,
        draw_logos: bool = True
    ) -> int:
        """Draw a single leg of a bet (used for both straight and parlay bets)."""
        # Handle both straight bet and parlay leg formats
        home_team = leg.get('home_team', leg.get('team', 'Unknown'))
        away_team = leg.get('away_team', leg.get('opponent', 'Unknown'))
        line = leg.get('line', 'ML')
        odds = float(leg.get('odds', 0))
        units = float(leg.get('units', 1.00))

        current_y = start_y
        if draw_logos:
            # Load and draw team logos with larger size
            home_logo = self._load_team_logo(home_team, league)
            away_logo = self._load_team_logo(away_team, league)
            logo_y = current_y
            
            # Save logos for future use if they don't exist
            if home_logo:
                self._save_team_logo(home_logo, home_team, league)
                image.paste(home_logo, (width // 4 - 75, logo_y), home_logo)
            if away_logo:
                self._save_team_logo(away_logo, away_team, league)
                image.paste(away_logo, (3 * width // 4 - 75, logo_y), away_logo)
            
            # Team names below logos
            team_y = logo_y + 150
            draw.text((width // 4, team_y), home_team, fill='white', font=team_font, anchor='mm')
            draw.text((3 * width // 4, team_y), away_team, fill='white', font=team_font, anchor='mm')
            current_y = team_y + 80  # Increased spacing after team names

        # Bet details with line
        details_y = current_y
        line_text = f"{home_team} vs {away_team}: {line}"
        draw.text((width // 2, details_y), line_text, fill='white', font=team_font, anchor='mm')
        
        # Draw odds below line with increased spacing
        odds_y = details_y + 60  # Increased spacing after line
        odds_text = f"{odds:+.0f}"
        draw.text((width // 2, odds_y), odds_text, fill='white', font=odds_font, anchor='mm')

        # Draw units with lock symbols and increased spacing
        units_y = odds_y + 60  # Increased spacing after odds
        units_label = "Unit" if units == 1.0 else "Units"
        units_text = f"To Win {units:.2f} {units_label}"
        units_bbox = draw.textbbox((0, 0), units_text, font=units_font)
        units_width = units_bbox[2] - units_bbox[0]
        lock_icon = self._load_lock_icon()
        lock_spacing = 15

        if lock_icon:
            lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
            image.paste(lock_icon, (lock_x_left, units_y - lock_icon.height // 2), lock_icon)
            lock_x_right = lock_x_left + units_width + lock_icon.width + 2 * lock_spacing
            image.paste(lock_icon, (lock_x_right, units_y - lock_icon.height // 2), lock_icon)
            draw.text(
                (lock_x_left + lock_icon.width + lock_spacing + units_width // 2, units_y),
                units_text,
                fill=(255, 215, 0),
                font=units_font,
                anchor='mm'
            )
        else:
            try:
                draw.text(
                    (width // 2, units_y),
                    f"🔒 {units_text} 🔒",
                    fill=(255, 215, 0),
                    font=emoji_font,
                    anchor='mm'
                )
            except Exception as e:
                logger.error(f"Failed to render emoji with emoji font: {str(e)}. Falling back to text-based lock symbol.")
                draw.text(
                    (width // 2, units_y),
                    f"[L] {units_text} [L]",
                    fill=(255, 215, 0),
                    font=units_font,
                    anchor='mm'
                )
        
        return units_y + 60  # Increased spacing after units

    def _save_team_logo(self, logo: Image.Image, team_name: str, league: str) -> None:
        """Save team logo for future use."""
        try:
            league_team_dir = self._ensure_team_dir_exists(league)
            team_name_map = {
                "oilers": "edmonton_oilers",
                "bruins": "boston_bruins",
                "bengals": "cincinnati_bengals",
                "steelers": "pittsburgh_steelers"
            }
            safe_team_name = team_name_map.get(team_name.lower(), team_name.lower().replace(" ", "_"))
            logo_path = os.path.join(league_team_dir, f"{safe_team_name}.png")
            
            if not os.path.exists(logo_path):
                logger.info(f"Saving team logo for {team_name} at {logo_path}")
                logo.save(logo_path, "PNG")
        except Exception as e:
            logger.error(f"Error saving logo for team {team_name}: {str(e)}")

    def save_bet_slip(self, image: Image.Image, output_path: str) -> None:
        """Save the bet slip image to a file."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path)
        except Exception as e:
            logger.error(f"Error saving bet slip: {str(e)}")
            raise
