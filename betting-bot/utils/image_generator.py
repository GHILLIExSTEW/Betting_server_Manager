# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class BetSlipGenerator:
    def __init__(self, font_path: Optional[str] = None, emoji_font_path: Optional[str] = None, assets_dir: str = "betting-bot/static/"):
        self.font_path = font_path or self._get_default_font()
        self.bold_font_path = self._get_default_bold_font()
        self.emoji_font_path = emoji_font_path or self._get_default_emoji_font()
        self.assets_dir = assets_dir
        self.league_team_dir = os.path.join(self.assets_dir, "logos/teams/HOCKEY/NHL")
        self.league_logo_dir = os.path.join(self.assets_dir, "logos/leagues/HOCKEY/NHL")
        self._ensure_font_exists()
        self._ensure_bold_font_exists()
        self._ensure_emoji_font_exists()
        self._ensure_team_dir_exists()
        self._ensure_league_dir_exists()

    def _get_default_font(self) -> str:
        """Get the default font path for regular text."""
        custom_font_path = "betting-bot/static/fonts/Roboto-Regular.ttf"
        if os.path.exists(custom_font_path):
            return custom_font_path
        if os.name == 'nt':  # Windows
            return 'C:\\Windows\\Fonts\\arial.ttf'
        else:  # Linux/Mac
            return '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

    def _get_default_bold_font(self) -> str:
        """Get the default bold font path for emphasized text."""
        custom_bold_font_path = "betting-bot/static/fonts/Roboto-Bold.ttf"
        if os.path.exists(custom_bold_font_path):
            return custom_bold_font_path
        return self._get_default_font()

    def _get_default_emoji_font(self) -> str:
        """Get the default font path for emojis."""
        custom_emoji_font_path = "betting-bot/static/fonts/NotoColorEmoji-Regular.ttf"
        if os.path.exists(custom_emoji_font_path):
            return custom_emoji_font_path
        if os.name == 'nt':  # Windows
            return 'C:\\Windows\\Fonts\\seguiemj.ttf'
        else:  # Linux/Mac (try common paths)
            return '/usr/share/fonts/truetype/noto/NotoColorEmoji-Regular.ttf'

    def _ensure_font_exists(self) -> None:
        """Ensure the regular font file exists."""
        if not os.path.exists(self.font_path):
            logger.warning(f"Font file not found at {self.font_path}")
            for font in ['Arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']:
                if os.path.exists(font):
                    self.font_path = font
                    break
            else:
                raise FileNotFoundError("Could not find a suitable font file. Please place 'Roboto-Regular.ttf' in betting-bot/static/fonts/")

    def _ensure_bold_font_exists(self) -> None:
        """Ensure the bold font file exists."""
        if not os.path.exists(self.bold_font_path):
            logger.warning(f"Bold font file not found at {self.bold_font_path}. Falling back to regular font.")
            self.bold_font_path = self.font_path

    def _ensure_emoji_font_exists(self) -> None:
        """Ensure the emoji font file exists."""
        if not os.path.exists(self.emoji_font_path):
            logger.warning(f"Emoji font file not found at {self.emoji_font_path}")
            for font in ['seguiemj.ttf', 'NotoColorEmoji-Regular.ttf']:
                if os.path.exists(font):
                    self.emoji_font_path = font
                    break
            else:
                raise FileNotFoundError("Could not find a suitable emoji font file. Please place 'NotoColorEmoji-Regular.ttf' in betting-bot/static/fonts/")

    def _ensure_team_dir_exists(self) -> None:
        """Ensure the team logos directory exists."""
        if not os.path.exists(self.league_team_dir):
            logger.warning(f"Team logos directory not found at {self.league_team_dir}")
            os.makedirs(self.league_team_dir, exist_ok=True)

    def _ensure_league_dir_exists(self) -> None:
        """Ensure the league logos directory exists."""
        if not os.path.exists(self.league_logo_dir):
            logger.warning(f"League logos directory not found at {self.league_logo_dir}")
            os.makedirs(self.league_logo_dir, exist_ok=True)

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        """Load the league logo image based on league name."""
        try:
            logo_filename = league.lower() + ".png"  # e.g., "nhl.png"
            logo_path = os.path.join(self.league_logo_dir, logo_filename)
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA")
                logo = logo.resize((30, 30), Image.Resampling.LANCZOS)  # Small size for the header
                return logo
            else:
                logger.warning(f"League logo not found for {league} at {logo_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading league logo for {league}: {str(e)}")
            return None

    def _load_team_logo(self, team_name: str) -> Optional[Image.Image]:
        """Load the team logo image based on team name."""
        try:
            # Map short team names to full filenames
            team_name_map = {
                "oilers": "edmonton_oilers",
                "bruins": "boston_bruins"
            }
            logo_filename = team_name_map.get(team_name.lower(), team_name.lower().replace(" ", "_")) + ".png"
            logo_path = os.path.join(self.league_team_dir, logo_filename)
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
        timestamp: datetime
    ) -> Image.Image:
        """Generate a bet slip image matching the provided style."""
        try:
            # Image dimensions
            width, height = 600, 400
            image = Image.new('RGB', (width, height), (40, 40, 40))  # Dark gray background
            draw = ImageDraw.Draw(image)

            # Load fonts
            header_font = ImageFont.truetype(self.font_path, 24)
            team_font = ImageFont.truetype(self.font_path, 18)
            odds_font = ImageFont.truetype(self.font_path, 30)
            small_font = ImageFont.truetype(self.font_path, 14)
            units_font = ImageFont.truetype(self.bold_font_path, 14)  # Use bold font for units text
            emoji_font = ImageFont.truetype(self.emoji_font_path, 14)  # Use emoji font for emoji rendering

            # Rounded rectangle background
            padding = 10
            corner_radius = 20
            draw.rounded_rectangle(
                [(padding, padding), (width - padding, height - padding)],
                radius=corner_radius,
                fill=(40, 40, 40),
                outline=None
            )

            # League logo and header
            league_logo = self._load_league_logo(league)
            header_text = f"{league.upper()} - Straight Bet"
            header_y = 50
            if league_logo:
                # Center the logo above the header text
                logo_x = (width - league_logo.width) // 2
                image.paste(league_logo, (logo_x, 20), league_logo)
                header_y = 60  # Adjust header position to be below the logo
            draw.text((width // 2, header_y), header_text, fill='white', font=header_font, anchor='mm')

            # Load and draw team logos
            home_logo = self._load_team_logo(home_team)
            away_logo = self._load_team_logo(away_team)
            logo_y = 90
            if home_logo:
                image.paste(home_logo, (width // 4 - 50, logo_y), home_logo)
            if away_logo:
                image.paste(away_logo, (3 * width // 4 - 50, logo_y), away_logo)

            # Team names below logos
            team_y = logo_y + 120
            draw.text((width // 4, team_y), home_team, fill='white', font=team_font, anchor='mm')
            draw.text((3 * width // 4, team_y), away_team, fill='white', font=team_font, anchor='mm')

            # Bet details
            details_y = team_y + 50
            line_text = f"{home_team}: {line}"
            draw.text((width // 2, details_y), line_text, fill='white', font=team_font, anchor='mm')
            odds_y = details_y + 40
            odds_text = f"{odds:+.0f}"  # Ensure no decimal places, show sign (e.g., "-110")
            draw.text((width // 2, odds_y), odds_text, fill='white', font=odds_font, anchor='mm')
            units_y = odds_y + 40
            units_text = f"To Win {units:.2f} Unit"
            units_bbox = draw.textbbox((0, 0), units_text, font=units_font)
            units_width = units_bbox[2] - units_bbox[0]
            lock_icon = self._load_lock_icon()
            lock_spacing = 10
            if lock_icon:
                # Draw lock icon on the left
                lock_x_left = (width - units_width - 2 * lock_icon.width - 2 * lock_spacing) // 2
                image.paste(lock_icon, (lock_x_left, units_y - lock_icon.height // 2), lock_icon)
                # Draw lock icon on the right
                lock_x_right = lock_x_left + units_width + lock_icon.width + 2 * lock_spacing
                image.paste(lock_icon, (lock_x_right, units_y - lock_icon.height // 2), lock_icon)
                # Adjust text position to be between locks
                draw.text((lock_x_left + lock_icon.width + lock_spacing + units_width // 2, units_y), units_text, fill=(255, 215, 0), font=units_font, anchor='mm')
            else:
                # Fallback to emoji, using the emoji font
                draw.text((width // 2, units_y), f"🔒 {units_text} 🔒", fill=(255, 215, 0), font=emoji_font, anchor='mm')

            # Separator line before footer
            separator_y = height - 50
            draw.line([(padding + 20, separator_y), (width - padding - 20, separator_y)], fill='white', width=1)

            # Footer: Bet ID and Timestamp
            footer_y = height - 30
            draw.text((padding + 10, footer_y), f"Bet #{bet_id}", fill=(150, 150, 150), font=small_font, anchor='lm')
            timestamp_text = timestamp.strftime('%Y-%m-%d %H:%M')
            draw.text((width - padding - 10, footer_y), timestamp_text, fill=(150, 150, 150), font=small_font, anchor='rm')

            return image

        except Exception as e:
            logger.error(f"Error generating bet slip: {str(e)}")
            raise

    def save_bet_slip(self, image: Image.Image, output_path: str) -> None:
        """Save the bet slip image to a file."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path)
        except Exception as e:
            logger.error(f"Error saving bet slip: {str(e)}")
            raise
