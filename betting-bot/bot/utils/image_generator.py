from PIL import Image, ImageDraw, ImageFont
import os
from typing import Optional
from datetime import datetime

class BetSlipGenerator:
    def __init__(self):
        self.width = 800
        self.height = 600
        self.padding = 20
        self.logo_size = (100, 100)
        self.league_logo_size = (60, 60)
        
        # Load fonts
        self.font_path = os.path.join(os.path.dirname(__file__), 'fonts')
        self.title_font = ImageFont.truetype(os.path.join(self.font_path, 'Roboto-Bold.ttf'), 24)
        self.subtitle_font = ImageFont.truetype(os.path.join(self.font_path, 'Roboto-Regular.ttf'), 18)
        self.body_font = ImageFont.truetype(os.path.join(self.font_path, 'Roboto-Regular.ttf'), 16)
        self.footer_font = ImageFont.truetype(os.path.join(self.font_path, 'Roboto-Light.ttf'), 14)

    def _load_logo(self, team_name: str) -> Optional[Image.Image]:
        """Load team logo from assets directory."""
        logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logos', f'{team_name.lower()}.png')
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            return logo.resize(self.logo_size, Image.Resampling.LANCZOS)
        return None

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        """Load league logo from assets directory."""
        logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'leagues', f'{league.lower()}.png')
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            return logo.resize(self.league_logo_size, Image.Resampling.LANCZOS)
        return None

    def generate_bet_slip(
        self,
        home_team: str,
        away_team: str,
        league: str,
        game_time: datetime,
        line: str,
        odds: str,
        units: int,
        bet_id: str
    ) -> Image.Image:
        """Generate a bet slip image."""
        # Create blank image
        image = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(image)

        # Load logos
        home_logo = self._load_logo(home_team)
        away_logo = self._load_logo(away_team)
        league_logo = self._load_league_logo(league)

        # Draw logos
        if home_logo:
            image.paste(home_logo, (self.padding, self.padding), home_logo)
        if away_logo:
            image.paste(away_logo, (self.width - self.padding - self.logo_size[0], self.padding), away_logo)
        if league_logo:
            league_x = (self.width - self.league_logo_size[0]) // 2
            image.paste(league_logo, (league_x, self.padding), league_logo)

        # Draw game time
        game_time_str = game_time.strftime('%I:%M %p %Z')
        time_width = draw.textlength(game_time_str, font=self.subtitle_font)
        time_x = (self.width - time_width) // 2
        draw.text((time_x, self.padding + self.logo_size[1] + 10), 
                 game_time_str, font=self.subtitle_font, fill='black')

        # Draw separator
        separator_y = self.padding + self.logo_size[1] + 40
        draw.line([(self.padding, separator_y), (self.width - self.padding, separator_y)], 
                 fill='gray', width=2)

        # Draw bet details
        details_y = separator_y + 20
        draw.text((self.padding, details_y), f"Line: {line}", font=self.body_font, fill='black')
        draw.text((self.padding, details_y + 30), f"Odds: {odds}", font=self.body_font, fill='black')
        draw.text((self.padding, details_y + 60), f"Units: {units}", font=self.body_font, fill='black')

        # Draw bottom separator
        bottom_separator_y = self.height - 100
        draw.line([(self.padding, bottom_separator_y), (self.width - self.padding, bottom_separator_y)], 
                 fill='gray', width=2)

        # Draw footer
        footer_y = bottom_separator_y + 20
        draw.text((self.padding, footer_y), f"Bet ID: {bet_id}", 
                 font=self.footer_font, fill='black')
        
        # Draw instructions
        instructions = "✅ Win | ❌ Loss"
        instructions_width = draw.textlength(instructions, font=self.footer_font)
        instructions_x = (self.width - instructions_width) // 2
        draw.text((instructions_x, footer_y), instructions, 
                 font=self.footer_font, fill='black')

        return image 