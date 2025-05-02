# betting-bot/utils/image_generator.py

"""Generates bet slip images for the betting bot."""

import logging
from datetime import datetime
from typing import List, Dict, Union
from PIL import Image, ImageDraw, ImageFont
import io

logger = logging.getLogger(__name__)

class BetSlipGenerator:
    def __init__(self):
        """Initialize the BetSlipGenerator with default settings."""
        self.background_color = (255, 255, 255)  # White background
        self.text_color = (0, 0, 0)  # Black text
        self.width = 600
        self.height = 400
        try:
            # Use a default font; adjust path if using a custom font
            self.font = ImageFont.load_default()
        except Exception as e:
            logger.error(f"Failed to load default font: {e}")
            raise ValueError("Could not load font for bet slip generation")

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
        parlay_legs: List[Dict[str, Union[str, float]]] = None,
        is_same_game: bool = False
    ) -> Image.Image:
        """
        Generate a bet slip image with the provided details.

        Args:
            home_team (str): Name of the home team.
            away_team (str): Name of the away team.
            league (str): League of the bet (e.g., NHL, NBA).
            line (str): Betting line (e.g., ML, O/U 5.5).
            odds (float): Odds for the bet (e.g., -110, +200).
            units (float): Units wagered.
            bet_id (str): Unique identifier for the bet.
            timestamp (datetime): Timestamp of the bet.
            bet_type (str): Type of bet ('straight' or 'parlay').
            parlay_legs (List[Dict]): List of legs for parlay bets, each with home_team, away_team, line, odds, units.
            is_same_game (bool): Whether all parlay legs are from the same game.

        Returns:
            Image.Image: Generated bet slip image.

        Raises:
            ValueError: If image generation fails.
        """
        logger.debug(f"Generating bet slip for bet_id: {bet_id}, type: {bet_type}, league: {league}")
        try:
            # Create a blank image
            image = Image.new('RGB', (self.width, self.height), self.background_color)
            draw = ImageDraw.Draw(image)

            # Define text positions
            y_position = 20
            line_spacing = 30
            x_margin = 20

            # Draw title
            title = f"{league} {bet_type.capitalize()} Bet Slip"
            draw.text((x_margin, y_position), title, fill=self.text_color, font=self.font)
            y_position += line_spacing * 2

            # Draw teams or game info
            if bet_type == "parlay" and parlay_legs and not is_same_game:
                # For multi-game parlays, list each leg
                draw.text((x_margin, y_position), "Parlay Legs:", fill=self.text_color, font=self.font)
                y_position += line_spacing
                for leg in parlay_legs:
                    leg_text = (f"{leg.get('home_team', 'Unknown')} vs {leg.get('away_team', 'Unknown')}: "
                               f"{leg.get('line', 'N/A')} @ {leg.get('odds', 0.0)} ({leg.get('units', 0.0)} units)")
                    draw.text((x_margin + 20, y_position), leg_text, fill=self.text_color, font=self.font)
                    y_position += line_spacing
            else:
                # For straight bets or same-game parlays, show one game
                game_text = f"{away_team} @ {home_team}"
                draw.text((x_margin, y_position), game_text, fill=self.text_color, font=self.font)
                y_position += line_spacing
                if bet_type == "parlay" and parlay_legs:
                    draw.text((x_margin, y_position), "Parlay Legs:", fill=self.text_color, font=self.font)
                    y_position += line_spacing
                    for leg in parlay_legs:
                        leg_text = f"{leg.get('line', 'N/A')} @ {leg.get('odds', 0.0)} ({leg.get('units', 0.0)} units)"
                        draw.text((x_margin + 20, y_position), leg_text, fill=self.text_color, font=self.font)
                        y_position += line_spacing
                else:
                    bet_text = f"Line: {line} @ {odds} ({units} units)"
                    draw.text((x_margin, y_position), bet_text, fill=self.text_color, font=self.font)
                    y_position += line_spacing * 2

            # Draw bet ID and timestamp
            draw.text((x_margin, y_position), f"Bet ID: {bet_id}", fill=self.text_color, font=self.font)
            y_position += line_spacing
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            draw.text((x_margin, y_position), f"Placed: {timestamp_str}", fill=self.text_color, font=self.font)

            logger.debug(f"Bet slip image generated successfully for bet_id: {bet_id}")
            return image

        except Exception as e:
            logger.error(f"Failed to generate bet slip image for bet_id {bet_id}: {e}", exc_info=True)
            raise ValueError(f"Could not generate bet slip image: {str(e)}")
