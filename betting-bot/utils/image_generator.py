# /home/container/betting-bot/utils/image_generator.py

import os
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from config import Config
# Removed incorrect import: from data.models.bet import Bet, BetLeg
from typing import List, Optional # Keep standard typing imports

# Setup logging
# Consider if basicConfig is needed or if logging is configured globally in main.py
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
# Ensure Config object provides these attributes
try:
    ASSET_DIR = Config.ASSET_DIR
    # Default paths constructed using ASSET_DIR
    DEFAULT_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'GothamMedium.ttf')
    DEFAULT_BOLD_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'GothamBold.ttf')
    LOGO_DIR = os.path.join(ASSET_DIR, 'logos')
    DEFAULT_TEAM_LOGO_PATH = os.path.join(LOGO_DIR, 'default_logo.png')
except AttributeError as e:
    logger.critical(f"Failed to get critical paths from Config object: {e}. Ensure Config has ASSET_DIR.")
    raise # Cannot proceed without asset paths
except TypeError as e:
     logger.critical(f"Config.ASSET_DIR is likely None or invalid type: {e}")
     raise # Cannot proceed without asset paths


DEFAULT_INDICATOR_COLOR = (114, 137, 218) # Default color (Discord blurple)

# --- Font Loading ---
# Validate paths and load fonts globally once to avoid reloading per instance
try:
    if not os.path.exists(DEFAULT_FONT_PATH):
        raise FileNotFoundError(f"Default font not found at {DEFAULT_FONT_PATH}")
    if not os.path.exists(DEFAULT_BOLD_FONT_PATH):
        raise FileNotFoundError(f"Default bold font not found at {DEFAULT_BOLD_FONT_PATH}")

    # Load fonts (consider adding more sizes if needed)
    font_m_18 = ImageFont.truetype(DEFAULT_FONT_PATH, 18)
    font_m_24 = ImageFont.truetype(DEFAULT_FONT_PATH, 24)
    font_b_18 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 18)
    font_b_24 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 24)
    font_b_36 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 36)
    logger.info("Successfully loaded fonts.")
except (IOError, FileNotFoundError, TypeError) as e:
    logger.critical(f"CRITICAL: Error loading required fonts: {e}")
    # Optional: Implement fallback to a system font if possible, otherwise raise
    raise # Re-raise the exception; the generator likely can't function without fonts

class BetSlipGenerator:
    def __init__(self, width=800, leg_height=120, header_height=100, footer_height=80, padding=20, logo_size=60):
        self.width = width
        self.leg_height = leg_height
        self.header_height = header_height
        self.footer_height = footer_height
        self.padding = padding
        self.logo_size = logo_size
        # Assign globally loaded fonts to the instance
        self.font_m_18 = font_m_18
        self.font_m_24 = font_m_24
        self.font_b_18 = font_b_18
        self.font_b_24 = font_b_24
        self.font_b_36 = font_b_36
        # Use constant paths defined outside __init__
        self.logo_dir = LOGO_DIR
        self.default_logo_path = DEFAULT_TEAM_LOGO_PATH
        self.image = None # Instance variable to hold the current image being built

    def _format_odds_with_sign(self, odds: Optional[int]) -> str:
        """Formats odds, adding a '+' for positive values. Handles None."""
        if odds is None:
            return "N/A"
        if odds > 0:
            return f"+{odds}"
        else:
            return str(odds)

    def _load_team_logo(self, league_name: Optional[str], team_name: str) -> Optional[Image.Image]:
        """Loads a team logo image, falling back to default. Returns None on error or if default missing."""
        if not team_name:
             logger.warning("Attempted to load logo with empty team name.")
             return None
        try:
            league_folder = str(league_name).upper() if league_name else "unknown_league"
            team_filename = f"{team_name.replace(' ', '_').replace('/', '_')}.png" # Basic sanitization

            logo_path = os.path.join(self.logo_dir, league_folder, team_filename)
            logo_path_fallback = os.path.join(self.logo_dir, team_filename)

            final_path_to_load = None
            if os.path.exists(logo_path):
                final_path_to_load = logo_path
            elif os.path.exists(logo_path_fallback):
                 final_path_to_load = logo_path_fallback
                 logger.debug(f"Found team logo '{team_name}' directly in logo dir: {final_path_to_load}")
            elif os.path.exists(self.default_logo_path):
                 final_path_to_load = self.default_logo_path
                 logger.warning(f"Team logo '{team_name}' (league '{league_folder}') not found. Using default. Checked: {logo_path}, {logo_path_fallback}")
            else:
                 logger.error(f"Team logo '{team_name}' (league '{league_folder}') not found, AND default logo missing: {self.default_logo_path}")
                 return None # Cannot load anything

            # Load the determined image path
            with Image.open(final_path_to_load) as logo:
                logo = logo.convert("RGBA")
                logo.thumbnail((self.logo_size, self.logo_size), Image.Resampling.LANCZOS)
                # Return a copy, as the original might be closed by 'with' statement sooner than expected depending on usage
                return logo.copy()

        except FileNotFoundError:
            logger.error(f"FileNotFoundError encountered for path: {final_path_to_load or logo_path}. Check file existence and permissions.")
            return None
        except Exception as e:
            logger.exception(f"Error loading logo for team '{team_name}' (league '{league_name}'): {e}")
            return None

    def _draw_leg(self, draw: ImageDraw.ImageDraw, y_offset: int, leg, leg_number: int): # Removed ': BetLeg' hint
        """Draws a single bet leg. Modifies self.image if logo is pasted."""
        # Assume 'leg' object has attributes: team_name, league_name, bet_type, line, odds
        leg_top = y_offset
        leg_bottom = leg_top + self.leg_height

        draw.rectangle([0, leg_top, self.width, leg_bottom], fill=(35, 39, 42))
        draw.line([0, leg_top, self.width, leg_top], fill=DEFAULT_INDICATOR_COLOR, width=4)

        leg_num_text = f"#{leg_number}"
        draw.text((self.padding, leg_top + self.padding // 2), leg_num_text, fill=(200, 200, 200), font=self.font_b_18)

        logo_area_start_x = self.padding + 40
        text_start_x = logo_area_start_x

        # Safely get attributes from leg object
        leg_team_name = getattr(leg, 'team_name', None)
        leg_league_name = getattr(leg, 'league_name', None)
        leg_bet_type = getattr(leg, 'bet_type', 'N/A')
        leg_line = getattr(leg, 'line', '')
        leg_odds = getattr(leg, 'odds', None)

        if leg_team_name:
            team_logo = self._load_team_logo(leg_league_name, leg_team_name)

            if team_logo:
                try:
                    logo_y = leg_top + (self.leg_height - team_logo.height) // 2
                    temp_image = Image.new('RGBA', self.image.size, (0, 0, 0, 0))
                    temp_image.paste(team_logo, (logo_area_start_x, logo_y), team_logo)
                    # Ensure self.image is RGBA before compositing
                    if self.image.mode != 'RGBA':
                        self.image = self.image.convert("RGBA")
                    self.image = Image.alpha_composite(self.image, temp_image) # Keep as RGBA for now
                    draw = ImageDraw.Draw(self.image) # Recreate draw object on the new image
                    text_start_x = logo_area_start_x + team_logo.width + self.padding
                except Exception as e:
                    logger.exception(f"Error pasting logo for leg {leg_number}, team {leg_team_name}: {e}")
                    # Keep text_start_x closer if pasting fails
            else:
                logger.warning(f"Could not display logo for leg {leg_number}, team {leg_team_name}.")

            draw.text((text_start_x, leg_top + self.padding), leg_team_name, fill=(255, 255, 255), font=self.font_b_24)
            bet_line_text = f"{leg_bet_type}: {leg_line}".strip()
            draw.text((text_start_x, leg_top + self.padding + 30), bet_line_text, fill=(200, 200, 200), font=self.font_m_18)

        else: # Handle props/non-team bets
            bet_line_text = f"{leg_bet_type}: {leg_line}".strip()
            draw.text((text_start_x, leg_top + self.padding), bet_line_text, fill=(255, 255, 255), font=self.font_b_24)

        odds_text = self._format_odds_with_sign(leg_odds)
        try:
            bbox = draw.textbbox((0, 0), odds_text, font=self.font_b_24)
            tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(odds_text, font=self.font_b_24)

        odds_x = self.width - self.padding - tw
        odds_y = leg_top + (self.leg_height - th) // 2
        draw.text((odds_x, odds_y), odds_text, fill=(255, 255, 255), font=self.font_b_24)

        draw.line([self.padding, leg_bottom -1, self.width - self.padding, leg_bottom-1], fill=(60, 60, 60), width=1)
        return draw # Return potentially updated draw object

    def create_bet_slip(self, bet) -> Optional[BytesIO]: # Removed ': Bet' hint
        """Generates the bet slip image. Assumes 'bet' has needed attributes."""
        # Safely access attributes from the 'bet' object
        bet_legs = getattr(bet, 'legs', [])
        bet_stake = getattr(bet, 'stake', 0.0)
        bet_total_odds = getattr(bet, 'total_odds', None)
        bet_potential_payout = getattr(bet, 'potential_payout', 0.0)
        bet_capper_name = getattr(bet, 'capper_name', None)
        bet_id = getattr(bet, 'bet_id', None) # For logging

        if not bet_legs:
            logger.error("Attempted to generate bet slip with no legs found in bet object.")
            return None

        num_legs = len(bet_legs)
        total_height = self.header_height + (num_legs * self.leg_height) + self.footer_height
        # Initialize image as RGBA to simplify compositing in _draw_leg
        self.image = Image.new('RGBA', (self.width, total_height), (44, 47, 51, 255))
        draw = ImageDraw.Draw(self.image)

        # --- Header ---
        header_bottom = self.header_height
        header_color = DEFAULT_INDICATOR_COLOR
        # Draw header rectangle (using RGBA color for consistency)
        draw.rectangle([0, 0, self.width, header_bottom], fill=(35, 39, 42, 255))
        draw.line([0, 0, self.width, 0], fill=header_color + (255,), width=5) # Add alpha to color tuple

        # Determine Title (Uses Multi-Team Parlay Bet title per user context)
        # Check if all legs have a non-None, non-empty team_name attribute
        all_legs_have_team = all(getattr(leg, 'team_name', None) for leg in bet_legs)
        is_multi_team = num_legs > 1 and all_legs_have_team

        if is_multi_team:
            title = "Multi-Team Parlay Bet"
        elif num_legs == 1:
             title = "Straight Bet"
        else:
            title = "Parlay Bet"

        # Center title
        try:
            bbox = draw.textbbox((0, 0), title, font=self.font_b_36)
            tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(title, font=self.font_b_36)
        title_x = (self.width - tw) // 2
        title_y = (self.header_height - th) // 2
        draw.text((title_x, title_y), title, fill=(255, 255, 255, 255), font=self.font_b_36)

        # --- Legs ---
        current_y = self.header_height
        for i, leg in enumerate(bet_legs):
            draw = self._draw_leg(draw, current_y, leg, i + 1)
            current_y += self.leg_height

        # --- Footer ---
        footer_top = current_y
        draw.rectangle([0, footer_top, self.width, footer_top + self.footer_height], fill=(35, 39, 42, 255))
        draw.line([0, footer_top, self.width, footer_top], fill=(60, 60, 60, 255), width=1)

        # Footer Text using safely accessed attributes
        stake_text = f"Stake: {bet_stake:.2f} Units"
        odds_text = f"Odds: {self._format_odds_with_sign(bet_total_odds)}"
        payout_text = f"To Win: {bet_potential_payout:.2f} Units"

        # Draw footer texts with alignment
        draw.text((self.padding, footer_top + self.padding), stake_text, fill=(200, 200, 200, 255), font=self.font_m_18)
        try:
            bbox = draw.textbbox((0, 0), odds_text, font=self.font_m_18)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(odds_text, font=self.font_m_18)
        draw.text(((self.width - tw) // 2, footer_top + self.padding), odds_text, fill=(200, 200, 200, 255), font=self.font_m_18)
        try:
            bbox = draw.textbbox((0, 0), payout_text, font=self.font_b_18)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(payout_text, font=self.font_b_18)
        draw.text((self.width - self.padding - tw, footer_top + self.padding), payout_text, fill=(100, 255, 100, 255), font=self.font_b_18)

        if bet_capper_name:
            capper_text = f"Capper: {bet_capper_name}"
            draw.text((self.padding, footer_top + self.padding + 25), capper_text, fill=(180, 180, 180, 255), font=self.font_m_18)

        # --- Save to BytesIO ---
        img_byte_arr = BytesIO()
        try:
            # Convert final image to RGB before saving (PNG supports transparency, but RGB is often smaller)
            final_image = self.image.convert("RGB")
            final_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            logger.info(f"Successfully generated bet slip image for Bet ID {bet_id if bet_id else 'N/A'}")
            return img_byte_arr
        except Exception as e:
            logger.exception(f"Error saving image to BytesIO: {e}")
            return None

# --- Example Usage Block ---
# (Keep the example block, but define simple placeholder classes for testing if needed)
if __name__ == '__main__':
    # Simple placeholder classes/structs for testing if Bet/BetLeg aren't available globally
    # This allows the __main__ block to run independently for testing the generator
    from collections import namedtuple
    MockBetLeg = namedtuple("MockBetLeg", ["league_name", "team_name", "bet_type", "line", "odds"])
    MockBet = namedtuple("MockBet", ["bet_id", "stake", "total_odds", "potential_payout", "capper_name", "legs"])


    # Setup CWD for asset loading (same logic as before)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.basename(project_root) == 'betting-bot' and os.path.exists(os.path.join(project_root, 'config.py')):
        os.chdir(project_root)
    else:
        potential_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if os.path.exists(os.path.join(potential_root, 'config.py')):
             os.chdir(potential_root)
        else:
             if not os.path.exists('config.py'):
                 print("ERROR: Cannot determine project root for testing. config.py not found.")
                 exit(1)
    print(f"Current working directory for test: {os.getcwd()}")
    # Path verification (same logic as before)
    if not os.path.exists(ASSET_DIR): print(f"ERROR: ASSET_DIR not found at {ASSET_DIR}"); exit(1)
    # ... (other path checks)

    # Sample Data using Mock objects
    legs_data = [
        MockBetLeg(league_name='NFL', team_name='Kansas City Chiefs', bet_type='Spread', line='-7', odds=-110),
        MockBetLeg(league_name='NBA', team_name='Los Angeles Lakers', bet_type='Moneyline', line=None, odds=150),
        MockBetLeg(league_name='MLB', team_name='New York Yankees', bet_type='Total', line='O 8.5', odds=-105),
        MockBetLeg(league_name='FAKE', team_name='Missing Logo Team', bet_type='Moneyline', line=None, odds=200),
        MockBetLeg(league_name='NFL', team_name=None, bet_type='Player Touchdowns', line='Patrick Mahomes O 0.5', odds=300)
    ]

    sample_bet = MockBet(
        bet_id=12345,
        stake=1.5,
        total_odds=1500,
        potential_payout=22.50,
        capper_name="Test Capper",
        legs=legs_data
    )

    generator = BetSlipGenerator()
    print("Generating complex parlay slip (using mock objects)...")
    image_bytes = generator.create_bet_slip(sample_bet)

    if image_bytes:
        with open("test_bet_slip.png", "wb") as f: f.write(image_bytes.getvalue())
        print("Test bet slip generated: test_bet_slip.png")
    else: print("Failed to generate test bet slip.")

    # Test straight bet
    print("Generating straight bet slip...")
    straight_leg_data = [MockBetLeg(league_name='NHL', team_name='Boston Bruins', bet_type='Puck Line', line='-1.5', odds=120)]
    straight_bet = MockBet(bet_id=None, stake=2.0, total_odds=120, potential_payout=2.4, legs=straight_leg_data, capper_name="Straight Shooter")
    image_bytes_straight = generator.create_bet_slip(straight_bet)
    if image_bytes_straight:
        with open("test_straight_bet_slip.png", "wb") as f: f.write(image_bytes_straight.getvalue())
        print("Test straight bet slip generated: test_straight_bet_slip.png")
    else: print("Failed to generate straight bet slip.")

     # Test multi-team parlay
    print("Generating multi-team parlay slip...")
    multi_team_legs_data = [
        MockBetLeg(league_name='NFL', team_name='Buffalo Bills', bet_type='Moneyline', line=None, odds=-200),
        MockBetLeg(league_name='NBA', team_name='Denver Nuggets', bet_type='Spread', line='+5.5', odds=-110)
    ]
    multi_team_bet = MockBet(bet_id=678, stake=1.0, total_odds=172, potential_payout=1.72, legs=multi_team_legs_data, capper_name=None)
    image_bytes_multi = generator.create_bet_slip(multi_team_bet)
    if image_bytes_multi:
        with open("test_multi_team_slip.png", "wb") as f: f.write(image_bytes_multi.getvalue())
        print("Test multi-team parlay slip generated: test_multi_team_slip.png")
    else: print("Failed to generate multi-team parlay slip.")

    print("Testing complete.")
