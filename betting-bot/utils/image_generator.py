import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class BetSlipGenerator:
    def __init__(self, font_path: Optional[str] = None):
        self.font_path = font_path or self._get_default_font()
        self._ensure_font_exists()

    def _get_default_font(self) -> str:
        """Get the default font path based on the operating system."""
        if os.name == 'nt':  # Windows
            return 'C:\\Windows\\Fonts\\arial.ttf'
        else:  # Linux/Mac
            return '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

    def _ensure_font_exists(self) -> None:
        """Ensure the font file exists."""
        if not os.path.exists(self.font_path):
            logger.warning(f"Font file not found at {self.font_path}")
            # Try to find an alternative font
            for font in ['Arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']:
                if os.path.exists(font):
                    self.font_path = font
                    break
            else:
                raise FileNotFoundError(f"Could not find a suitable font file")

    def generate_bet_slip(
        self,
        home_team: str,
        away_team: str,
        league: str,
        game_time: datetime,
        line: str,
        odds: float,
        units: int,
        bet_id: str
    ) -> Image.Image:
        """Generate a bet slip image."""
        try:
            # Create a new image with a white background
            width, height = 800, 600
            image = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(image)

            # Load fonts
            title_font = ImageFont.truetype(self.font_path, 36)
            header_font = ImageFont.truetype(self.font_path, 24)
            text_font = ImageFont.truetype(self.font_path, 18)

            # Draw title
            draw.text((width//2, 50), "BET SLIP", fill='black', font=title_font, anchor='mm')

            # Draw bet ID
            draw.text((width-50, 50), f"#{bet_id}", fill='black', font=header_font, anchor='rm')

            # Draw game information
            y_offset = 120
            draw.text((50, y_offset), f"League: {league}", fill='black', font=text_font)
            y_offset += 30
            draw.text((50, y_offset), f"Game: {away_team} @ {home_team}", fill='black', font=text_font)
            y_offset += 30
            draw.text((50, y_offset), f"Time: {game_time.strftime('%Y-%m-%d %H:%M %Z')}", fill='black', font=text_font)
            y_offset += 30

            # Draw bet details
            draw.text((50, y_offset), f"Line: {line}", fill='black', font=text_font)
            y_offset += 30
            draw.text((50, y_offset), f"Odds: {odds:+d}", fill='black', font=text_font)
            y_offset += 30
            draw.text((50, y_offset), f"Units: {units}", fill='black', font=text_font)
            y_offset += 30

            # Draw timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            draw.text((width//2, height-50), f"Generated: {timestamp}", fill='black', font=text_font, anchor='mm')

            # Draw border
            draw.rectangle([(10, 10), (width-10, height-10)], outline='black', width=2)

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