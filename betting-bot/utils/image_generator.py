# betting-bot/utils/image_generator.py

"""Generates bet slip images for straight and parlay bets."""

import logging
from typing import List, Dict, Union, Optional
from datetime import datetime
from pathlib import Path
import io
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class BetSlipGenerator:
    def __init__(self):
        """Initialize the BetSlipGenerator with paths and default settings."""
        self.assets_dir = Path("/home/container/betting-bot/assets")
        self.logo_dir = self.assets_dir / "logos"
        self.font_dir = self.assets_dir / "fonts"
        
        # Ensure directories exist
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.logo_dir.mkdir(parents=True, exist_ok=True)
        self.font_dir.mkdir(parents=True, exist_ok=True)

        # Default font paths (adjust based on your server setup)
        self.default_font_path = self.font_dir / "Arial.ttf"
        self.bold_font_path = self.font_dir / "Arial_Bold.ttf"

        # Default image dimensions and colors
        self.width = 512
        self.height = 256
        self.background_color = (30, 30, 30)  # Dark gray background
        self.text_color = (255, 255, 255)  # White text
        self.accent_color = (255, 215, 0)  # Yellow for odds and units

    def _load_font(self, font_path: Path, size: int) -> ImageFont.ImageFont:
        """Load a font with the specified size, falling back to default if necessary."""
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception as e:
            logger.warning(f"Failed to load font {font_path}: {e}. Using default font.")
            return ImageFont.load_default()

    def _load_logo(self, team_name: str) -> Optional[Image.Image]:
        """Load a team logo image based on the team name."""
        logo_path = self.logo_dir / f"{team_name}.png"
        try:
            logo = Image.open(logo_path).convert("RGBA")
            # Resize logo to fit (e.g., 80x80 pixels)
            logo = logo.resize((80, 80), Image.Resampling.LANCZOS)
            return logo
        except Exception as e:
            logger.warning(f"Failed to load logo for team {team_name}: {e}")
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
        bet_type: str,
        parlay_legs: Optional[List[Dict[str, Union[str, float]]]] = None,
        is_same_game: bool = False
    ) -> Image.Image:
        """Generate a bet slip image for straight or parlay bets."""
        logger.debug(f"Generating bet slip for bet_id: {bet_id}, type: {bet_type}, league: {league}")

        try:
            # Create a new image with a dark background
            image = Image.new("RGBA", (self.width, self.height), self.background_color)
            draw = ImageDraw.Draw(image)

            # Load fonts
            header_font = self._load_font(self.bold_font_path, 24)
            main_font = self._load_font(self.default_font_path, 20)
            sub_font = self._load_font(self.default_font_path, 16)

            # Header: League and Bet Type (e.g., "NHL - Straight Bet")
            header_text = f"{league.upper()} - {bet_type.capitalize()} Bet"
            header_bbox = draw.textbbox((0, 0), header_text, font=header_font)
            header_width = header_bbox[2] - header_bbox[0]
            draw.text(
                ((self.width - header_width) // 2, 10),
                header_text,
                fill=self.text_color,
                font=header_font
            )

            # Load team logos
            home_logo = self._load_logo(home_team)
            away_logo = self._load_logo(away_team)

            # Positions for logos
            logo_y = 50
            if home_logo:
                image.paste(home_logo, (self.width // 4 - 40, logo_y), home_logo)
            if away_logo:
                image.paste(away_logo, (3 * self.width // 4 - 40, logo_y), away_logo)

            # Team names below logos
            team_y = logo_y + (90 if home_logo or away_logo else 0)
            home_text = home_team
            away_text = away_team
            home_bbox = draw.textbbox((0, 0), home_text, font=main_font)
            away_bbox = draw.textbbox((0, 0), away_text, font=main_font)
            home_width = home_bbox[2] - home_bbox[0]
            away_width = away_bbox[2] - away_bbox[0]
            draw.text(
                ((self.width // 4 - home_width // 2), team_y),
                home_text,
                fill=self.text_color,
                font=main_font
            )
            draw.text(
                ((3 * self.width // 4 - away_width // 2), team_y),
                away_text,
                fill=self.text_color,
                font=main_font
            )

            # Bet details (Line, Odds, Units)
            if bet_type.lower() == "straight":
                bet_line = f"{home_team}: {line} @ {odds:+.0f}"
                to_win = units * (abs(odds) / 100 if odds < 0 else 100 / odds)
                bet_units = f"To Win {to_win:.2f} Units"
            else:
                bet_line = f"{len(parlay_legs)} Leg Parlay @ {odds:+.0f}"
                to_win = units * (abs(odds) / 100 if odds < 0 else 100 / odds)
                bet_units = f"To Win {to_win:.2f} Units"

            line_bbox = draw.textbbox((0, 0), bet_line, font=main_font)
            units_bbox = draw.textbbox((0, 0), bet_units, font=main_font)
            line_width = line_bbox[2] - line_bbox[0]
            units_width = units_bbox[2] - units_bbox[0]

            line_y = team_y + 40
            draw.text(
                ((self.width - line_width) // 2, line_y),
                bet_line,
                fill=self.text_color,
                font=main_font
            )
            draw.text(
                ((self.width - units_width) // 2, line_y + 30),
                bet_units,
                fill=self.accent_color,
                font=main_font
            )

            # Draw a horizontal line separator
            draw.line(
                [(50, line_y + 60), (self.width - 50, line_y + 60)],
                fill=self.accent_color,
                width=2
            )

            # Bet ID and Timestamp
            bet_id_text = f"Bet #{bet_id[:8]}..."
            timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M")
            id_bbox = draw.textbbox((0, 0), bet_id_text, font=sub_font)
            time_bbox = draw.textbbox((0, 0), timestamp_text, font=sub_font)
            id_width = id_bbox[2] - id_bbox[0]
            time_width = time_bbox[2] - time_bbox[0]

            footer_y = line_y + 80
            draw.text(
                (20, footer_y),
                bet_id_text,
                fill=self.text_color,
                font=sub_font
            )
            draw.text(
                (self.width - time_width - 20, footer_y),
                timestamp_text,
                fill=self.text_color,
                font=sub_font
            )

            logger.debug(f"Bet slip image generated successfully for bet_id: {bet_id}")
            return image

        except Exception as e:
            logger.error(f"Failed to generate graphical bet slip for bet_id {bet_id}: {e}", exc_info=True)
            # Fallback to text-based image
            return self._generate_text_fallback(
                home_team, away_team, league, line, odds, units, bet_id, timestamp, bet_type, parlay_legs
            )

    def _generate_text_fallback(
        self,
        home_team: str,
        away_team: str,
        league: str,
        line: str,
        odds: float,
        units: float,
        bet_id: str,
        timestamp: datetime,
        bet_type: str,
        parlay_legs: Optional[List[Dict[str, Union[str, float]]]] = None
    ) -> Image.Image:
        """Generate a text-based bet slip as a fallback."""
        image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        font = self._load_font(self.default_font_path, 16)

        text_lines = [
            f"{league.upper()} {bet_type.capitalize()} Bet Slip",
            "",
            f"{away_team} @ {home_team}",
            f"Line: {line} @ {odds:+.0f} ({units:.1f} units)",
            "",
            f"Bet ID {bet_id}",
            f"Placed: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        ]

        y_position = 10
        for line in text_lines:
            draw.text((10, y_position), line, fill=(255, 255, 255), font=font)
            y_position += 20

        logger.debug(f"Fallback text-based bet slip generated for bet_id: {bet_id}")
        return image
