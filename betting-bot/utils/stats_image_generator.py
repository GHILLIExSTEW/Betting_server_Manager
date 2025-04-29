import logging
from typing import Dict, List
from PIL import Image, ImageDraw, ImageFont
import os

logger = logging.getLogger(__name__)

class StatsImageGenerator:
    def __init__(self):
        self.font_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts', 'arial.ttf')
        self.background_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'stats_bg.png')
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(self.font_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.background_path), exist_ok=True)

    def generate_capper_stats_image(self, stats: Dict, username: str) -> Image.Image:
        """Generate an image with capper statistics."""
        try:
            # Create a new image with a white background
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)

            # Load font
            try:
                font = ImageFont.truetype(self.font_path, 24)
                title_font = ImageFont.truetype(self.font_path, 32)
            except IOError:
                font = ImageFont.load_default()
                title_font = ImageFont.load_default()

            # Draw title
            draw.text((400, 50), f"{username}'s Stats", fill='black', font=title_font, anchor="mm")

            # Draw stats
            y = 150
            stats_text = [
                f"Total Bets: {stats.get('total_bets', 0)}",
                f"Won Bets: {stats.get('won_bets', 0)}",
                f"Lost Bets: {stats.get('lost_bets', 0)}",
                f"Win Percentage: {stats.get('win_percentage', 0):.1f}%",
                f"Total Units: {stats.get('total_units', 0)}",
                f"Net Units: {stats.get('net_units', 0)}"
            ]

            for text in stats_text:
                draw.text((400, y), text, fill='black', font=font, anchor="mm")
                y += 50

            return img
        except Exception as e:
            logger.error(f"Error generating capper stats image: {str(e)}")
            raise

    def generate_guild_stats_image(self, stats: Dict) -> Image.Image:
        """Generate an image with guild statistics."""
        try:
            # Create a new image with a white background
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)

            # Load font
            try:
                font = ImageFont.truetype(self.font_path, 24)
                title_font = ImageFont.truetype(self.font_path, 32)
            except IOError:
                font = ImageFont.load_default()
                title_font = ImageFont.load_default()

            # Draw title
            draw.text((400, 50), "Guild Stats", fill='black', font=title_font, anchor="mm")

            # Draw stats
            y = 150
            stats_text = [
                f"Total Bets: {stats.get('total_bets', 0)}",
                f"Total Cappers: {stats.get('total_cappers', 0)}",
                f"Total Units Wagered: {stats.get('total_units', 0)}",
                f"Net Units: {stats.get('net_units', 0)}"
            ]

            for text in stats_text:
                draw.text((400, y), text, fill='black', font=font, anchor="mm")
                y += 50

            return img
        except Exception as e:
            logger.error(f"Error generating guild stats image: {str(e)}")
            raise

    def generate_top_cappers_image(self, cappers: List[Dict]) -> Image.Image:
        """Generate an image with top cappers."""
        try:
            # Create a new image with a white background
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)

            # Load font
            try:
                font = ImageFont.truetype(self.font_path, 24)
                title_font = ImageFont.truetype(self.font_path, 32)
            except IOError:
                font = ImageFont.load_default()
                title_font = ImageFont.load_default()

            # Draw title
            draw.text((400, 50), "Top Cappers", fill='black', font=title_font, anchor="mm")

            # Draw cappers
            y = 150
            for capper in cappers:
                text = f"User ID: {capper['user_id']} - Net Units: {capper['net_units']}"
                draw.text((400, y), text, fill='black', font=font, anchor="mm")
                y += 50

            return img
        except Exception as e:
            logger.error(f"Error generating top cappers image: {str(e)}")
            raise 