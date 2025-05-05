# /home/container/betting-bot/utils/image_generator.py

import os
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
# Removed incorrect import: from utils.league_dictionaries import league_colors, league_logos
from utils.bet_utils import format_odds_with_sign
from config import Config
from data.models.bet import Bet, BetLeg
from typing import List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO) # Basic config, ensure your main setup runs first
logger = logging.getLogger(__name__)

# Constants
ASSET_DIR = Config.ASSET_DIR
DEFAULT_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'GothamMedium.ttf')
DEFAULT_BOLD_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'GothamBold.ttf')
LOGO_DIR = os.path.join(ASSET_DIR, 'logos')
DEFAULT_TEAM_LOGO = os.path.join(LOGO_DIR, 'default_logo.png')
DEFAULT_INDICATOR_COLOR = (114, 137, 218) # Default color (Discord blurple) since league colors are not used

# Ensure default fonts exist
if not os.path.exists(DEFAULT_FONT_PATH):
    logger.error(f"Default font not found at {DEFAULT_FONT_PATH}")
if not os.path.exists(DEFAULT_BOLD_FONT_PATH):
    logger.error(f"Default bold font not found at {DEFAULT_BOLD_FONT_PATH}")

# Load default fonts
try:
    font_m_18 = ImageFont.truetype(DEFAULT_FONT_PATH, 18)
    font_m_24 = ImageFont.truetype(DEFAULT_FONT_PATH, 24)
    font_b_18 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 18)
    font_b_24 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 24)
    font_b_36 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 36)
except IOError as e:
    logger.exception(f"Error loading fonts: {e}")
    # Handle font loading errors gracefully

class BetSlipGenerator:
    def __init__(self, width=800, leg_height=120, header_height=100, footer_height=80, padding=20, logo_size=60):
        self.width = width
        self.leg_height = leg_height
        self.header_height = header_height
        self.footer_height = footer_height
        self.padding = padding
        self.logo_size = logo_size
        self.font_m_18 = font_m_18
        self.font_m_24 = font_m_24
        self.font_b_18 = font_b_18
        self.font_b_24 = font_b_24
        self.font_b_36 = font_b_36
        self.logo_dir = LOGO_DIR
        self.default_logo = DEFAULT_TEAM_LOGO

    def _load_team_logo(self, league_name: str, team_name: str) -> Image.Image:
        """Loads a team logo, falling back to default if not found."""
        try:
            # Construct path: ASSET_DIR/logos/LEAGUE_NAME/Team_Name.png
            logo_filename = f"{team_name.replace(' ', '_')}.png"
            logo_path = os.path.join(self.logo_dir, league_name.upper(), logo_filename)

            if not os.path.exists(logo_path):
                # Fallback: try finding logo directly in logo_dir if league folder doesn't exist or logo isn't there
                logo_path_fallback = os.path.join(self.logo_dir, logo_filename)
                if os.path.exists(logo_path_fallback):
                     logo_path = logo_path_fallback
                     logger.debug(f"Found team logo for {team_name} directly in logo dir: {logo_path}")
                else:
                     # Use default logo if specific one not found
                     default_logo_path = self.default_logo
                     logger.warning(f"Team logo not found for {team_name} in league {league_name}. Using default. Checked: {logo_path} and {logo_path_fallback}")
                     logo_path = default_logo_path # Use default path

            # Check if the final logo_path exists before trying to open
            if not os.path.exists(logo_path):
                 logger.error(f"Final logo path does not exist: {logo_path}. Even default logo might be missing.")
                 # Return a small transparent image if even default logo is missing
                 return Image.new('RGBA', (self.logo_size, self.logo_size), (0, 0, 0, 0))

            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((self.logo_size, self.logo_size), Image.Resampling.LANCZOS)
            return logo

        except FileNotFoundError: # Should be caught by the os.path.exists check now, but keep for safety
            logger.warning(f"FileNotFoundError for logo path: {logo_path}. Returning transparent image.")
            return Image.new('RGBA', (self.logo_size, self.logo_size), (0, 0, 0, 0))
        except Exception as e:
            logger.exception(f"Error loading logo for {team_name} ({league_name}): {e}")
            # Return a transparent image on any other error
            return Image.new('RGBA', (self.logo_size, self.logo_size), (0, 0, 0, 0))


    def _draw_leg(self, draw: ImageDraw.ImageDraw, y_offset: int, leg: BetLeg, leg_number: int):
        """Draws a single bet leg."""
        leg_top = y_offset
        leg_bottom = leg_top + self.leg_height

        # Background for the leg
        draw.rectangle([0, leg_top, self.width, leg_bottom], fill=(35, 39, 42)) # Dark grey background

        # Default color indicator line (removed league_color dependency)
        draw.line([0, leg_top, self.width, leg_top], fill=DEFAULT_INDICATOR_COLOR, width=4)

        # Leg Number
        leg_num_text = f"#{leg_number}"
        draw.text((self.padding, leg_top + self.padding // 2), leg_num_text, fill=(200, 200, 200), font=self.font_b_18)

        # Team Info (if applicable)
        logo_area_width = self.padding + 50 # Reserve space for leg num roughly
        text_start_x = logo_area_width # Default start for text

        if leg.team_name:
            # Use league_name from the leg for finding the logo directory
            team_logo = self._load_team_logo(leg.league_name or "unknown_league", leg.team_name)
            logo_y = leg_top + (self.leg_height - self.logo_size) // 2
            # Paste the logo using alpha compositing to handle transparency
            temp_image = Image.new('RGBA', self.image.size, (0, 0, 0, 0))
            temp_image.paste(team_logo, (logo_area_width, logo_y), team_logo)
            self.image = Image.alpha_composite(self.image.convert("RGBA"), temp_image).convert("RGB")
            draw = ImageDraw.Draw(self.image) # Recreate draw object after pasting

            # Team Name and Bet Type Text start after logo
            text_start_x = logo_area_width + self.logo_size + self.padding
            draw.text((text_start_x, leg_top + self.padding), leg.team_name, fill=(255, 255, 255), font=self.font_b_24)
            draw.text((text_start_x, leg_top + self.padding + 30), f"{leg.bet_type}: {leg.line}", fill=(200, 200, 200), font=self.font_m_18)
        else:
            # Handle player props or other non-team bets - text starts closer to left
            draw.text((text_start_x, leg_top + self.padding), f"{leg.bet_type}: {leg.line}", fill=(255, 255, 255), font=self.font_b_24)


        # Odds
        odds_text = format_odds_with_sign(leg.odds)
        # Use textbbox to get width and height for centering
        try:
            bbox = draw.textbbox((0, 0), odds_text, font=self.font_b_24)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError: # Fallback for older PIL versions
             tw, th = draw.textsize(odds_text, font=self.font_b_24)

        odds_x = self.width - self.padding - tw
        odds_y = leg_top + (self.leg_height - th) // 2
        draw.text((odds_x, odds_y), odds_text, fill=(255, 255, 255), font=self.font_b_24)

        # Separator line
        # No need for leg_number > 0 check as it's drawn relative to leg_top
        draw.line([self.padding, leg_bottom -1, self.width - self.padding, leg_bottom-1], fill=(60, 60, 60), width=1)


    def create_bet_slip(self, bet: Bet) -> Optional[BytesIO]:
        """Generates the bet slip image."""
        if not bet or not bet.legs:
            logger.error("Attempted to generate bet slip with no bet data or no legs.")
            return None

        num_legs = len(bet.legs)
        total_height = self.header_height + (num_legs * self.leg_height) + self.footer_height
        # Start with RGB, convert to RGBA only when pasting logos, then back to RGB
        self.image = Image.new('RGB', (self.width, total_height), (44, 47, 51)) # Discord grey background
        draw = ImageDraw.Draw(self.image)

        # --- Header ---
        header_bottom = self.header_height
        # Use default color for header top border (removed league_color dependency)
        header_color = DEFAULT_INDICATOR_COLOR
        draw.rectangle([0, 0, self.width, header_bottom], fill=(35, 39, 42)) # Darker grey header
        draw.line([0, 0, self.width, 0], fill=header_color, width=5) # Top border

        # Header Title (Bet Type) - Uses Multi-Team Parlay Bet title per user context
        is_multi_team = num_legs > 1 and all(leg.team_name is not None for leg in bet.legs)
        if is_multi_team:
            title = "Multi-Team Parlay Bet"
        elif num_legs == 1:
             title = "Straight Bet"
        else: # Parlay with props or only props
            title = "Parlay Bet"


        # Use textbbox for centering title
        try:
            bbox = draw.textbbox((0, 0), title, font=self.font_b_36)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError: # Fallback for older PIL versions
             tw, th = draw.textsize(title, font=self.font_b_36)

        title_x = (self.width - tw) // 2
        title_y = (self.header_height - th) // 2
        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=self.font_b_36)

        # --- Legs ---
        current_y = self.header_height
        for i, leg in enumerate(bet.legs):
            # Pass draw object that might be recreated if logos are pasted
            self._draw_leg(draw, current_y, leg, i + 1)
            # Important: Re-assign draw object in case self.image was changed by alpha_composite
            draw = ImageDraw.Draw(self.image)
            current_y += self.leg_height

        # --- Footer ---
        footer_top = current_y
        draw.rectangle([0, footer_top, self.width, footer_top + self.footer_height], fill=(35, 39, 42)) # Darker grey footer
        draw.line([0, footer_top, self.width, footer_top], fill=(60,60,60), width=1) # Separator line

        # Stake, Odds, Payout
        stake_text = f"Stake: {bet.stake:.2f} Units"
        odds_text = f"Odds: {format_odds_with_sign(bet.total_odds)}"
        payout_text = f"To Win: {bet.potential_payout:.2f} Units"

        draw.text((self.padding, footer_top + self.padding), stake_text, fill=(200, 200, 200), font=self.font_m_18)

        try: # Use textbbox for centering odds
            bbox = draw.textbbox((0, 0), odds_text, font=self.font_m_18)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(odds_text, font=self.font_m_18)
        draw.text(((self.width - tw) // 2, footer_top + self.padding), odds_text, fill=(200, 200, 200), font=self.font_m_18)

        try: # Use textbbox for right-aligning payout
            bbox = draw.textbbox((0, 0), payout_text, font=self.font_b_18)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(payout_text, font=self.font_b_18)
        draw.text((self.width - self.padding - tw, footer_top + self.padding), payout_text, fill=(100, 255, 100), font=self.font_b_18) # Green payout

        # Optional: Capper Name
        if bet.capper_name:
            capper_text = f"Capper: {bet.capper_name}"
            draw.text((self.padding, footer_top + self.padding + 30), capper_text, fill=(180, 180, 180), font=self.font_m_18)


        # --- Save to BytesIO ---
        img_byte_arr = BytesIO()
        try:
            self.image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            logger.info(f"Successfully generated bet slip image for Bet ID {bet.bet_id if bet.bet_id else 'N/A'}")
            return img_byte_arr
        except Exception as e:
            logger.exception(f"Error saving image to BytesIO: {e}")
            return None

# Example Usage (for testing - requires running from project root or adjusting paths)
# (Keep the example usage block as is, but it will now test the modified code)
# ... [Rest of the __main__ block for testing] ...
if __name__ == '__main__':
    # Ensure the script is run from the project root or adjust paths accordingly
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    print(f"Current working directory: {os.getcwd()}")
    print(f"Asset directory: {ASSET_DIR}")
    print(f"Default font path: {DEFAULT_FONT_PATH}")
    print(f"Logo directory: {LOGO_DIR}")


    # Sample Data
    legs_data = [
        {'league_name': 'NFL', 'team_name': 'Kansas City Chiefs', 'bet_type': 'Spread', 'line': '-7', 'odds': -110},
        {'league_name': 'NBA', 'team_name': 'Los Angeles Lakers', 'bet_type': 'Moneyline', 'line': None, 'odds': 150},
        {'league_name': 'MLB', 'team_name': 'New York Yankees', 'bet_type': 'Total', 'line': 'O 8.5', 'odds': -105}
    ]
    bet_legs = [BetLeg(**data) for data in legs_data]

    sample_bet = Bet(
        bet_id=12345,
        user_id=98765,
        guild_id=11223,
        message_id=44556,
        channel_id=77889,
        stake=1.5,
        total_odds=750, # Example combined odds
        potential_payout=11.25, # Example payout (stake * decimal odds)
        status='pending',
        result=None,
        created_at=None, # Let DB handle default
        legs=bet_legs,
        capper_name="Test Capper"
    )

    generator = BetSlipGenerator()
    image_bytes = generator.create_bet_slip(sample_bet)

    if image_bytes:
        with open("test_bet_slip.png", "wb") as f:
            f.write(image_bytes.getvalue())
        print("Test bet slip generated: test_bet_slip.png")
    else:
        print("Failed to generate test bet slip.")

    # Test straight bet
    straight_leg = [BetLeg(**{'league_name': 'NHL', 'team_name': 'Boston Bruins', 'bet_type': 'Puck Line', 'line': '-1.5', 'odds': 120})]
    straight_bet = Bet(stake=2.0, total_odds=120, potential_payout=2.4, legs=straight_leg, capper_name="Straight Shooter")
    image_bytes_straight = generator.create_bet_slip(straight_bet)
    if image_bytes_straight:
        with open("test_straight_bet_slip.png", "wb") as f:
            f.write(image_bytes_straight.getvalue())
        print("Test straight bet slip generated: test_straight_bet_slip.png")

     # Test player prop (non-team)
    prop_leg = [BetLeg(**{'league_name': 'NBA', 'team_name': None, 'bet_type': 'Player Points', 'line': 'LeBron James O 28.5', 'odds': -115})]
    prop_bet = Bet(stake=1.0, total_odds=-115, potential_payout=0.87, legs=prop_leg) #Payout calculation needs refinement for odds
    image_bytes_prop = generator.create_bet_slip(prop_bet)
    if image_bytes_prop:
        with open("test_prop_bet_slip.png", "wb") as f:
            f.write(image_bytes_prop.getvalue())
        print("Test prop bet slip generated: test_prop_bet_slip.png")

    # Test parlay with prop
    parlay_with_prop_legs = [
        BetLeg(**{'league_name': 'NFL', 'team_name': 'Buffalo Bills', 'bet_type': 'Moneyline', 'line': None, 'odds': -200}),
        BetLeg(**{'league_name': 'NBA', 'team_name': None, 'bet_type': 'Player Assists', 'line': 'Nikola Jokic O 9.5', 'odds': 100})
    ]
    parlay_prop_bet = Bet(stake=0.5, total_odds=200, potential_payout=1.0, legs=parlay_with_prop_legs) # Payout calc needs refinement
    image_bytes_parlay_prop = generator.create_bet_slip(parlay_prop_bet)
    if image_bytes_parlay_prop:
        with open("test_parlay_prop_slip.png", "wb") as f:
            f.write(image_bytes_parlay_prop.getvalue())
        print("Test parlay with prop slip generated: test_parlay_prop_slip.png")
