# /home/container/betting-bot/utils/image_generator.py

import os
import logging
from io import BytesIO # Needed to return image bytes
from PIL import Image, ImageDraw, ImageFont
from config import Config # Needed to find asset paths
from typing import Optional, List # Keep standard typing imports

logger = logging.getLogger(__name__)

# --- Constants ---
# Get asset directory from Config and build paths
try:
    ASSET_DIR = Config.ASSET_DIR
    if not ASSET_DIR or not os.path.isdir(ASSET_DIR):
         raise ValueError(f"ASSET_DIR '{ASSET_DIR}' from Config is not a valid directory.")

    DEFAULT_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'GothamMedium.ttf')
    DEFAULT_BOLD_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'GothamBold.ttf')
    LOGO_DIR = os.path.join(ASSET_DIR, 'logos')
    DEFAULT_TEAM_LOGO_PATH = os.path.join(LOGO_DIR, 'default_logo.png')

    # Check if default logo exists ONCE at startup
    if not os.path.exists(DEFAULT_TEAM_LOGO_PATH):
         logger.warning(f"Default team logo defined but not found at: {DEFAULT_TEAM_LOGO_PATH}")
         # Set path to None if default doesn't exist? Or let _load_team_logo handle it?
         # Let _load_team_logo handle it, log warning here.

except (AttributeError, ValueError, TypeError) as e:
    logger.critical(f"Failed to initialize paths from Config object: {e}. Ensure Config has valid ASSET_DIR.")
    raise # Cannot proceed without asset paths

DEFAULT_INDICATOR_COLOR = (114, 137, 218) # Default color

# --- Font Loading ---
# Validate paths and load fonts globally once
try:
    if not os.path.exists(DEFAULT_FONT_PATH):
        raise FileNotFoundError(f"Default font not found at {DEFAULT_FONT_PATH}")
    if not os.path.exists(DEFAULT_BOLD_FONT_PATH):
        raise FileNotFoundError(f"Default bold font not found at {DEFAULT_BOLD_FONT_PATH}")

    font_m_18 = ImageFont.truetype(DEFAULT_FONT_PATH, 18)
    font_m_24 = ImageFont.truetype(DEFAULT_FONT_PATH, 24)
    font_b_18 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 18)
    font_b_24 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 24)
    font_b_36 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 36)
    logger.info("Successfully loaded fonts for image_generator.")
except (IOError, FileNotFoundError, TypeError) as e:
    logger.critical(f"CRITICAL: Error loading required fonts: {e}")
    raise

class BetSlipGenerator:
    def __init__(self, width=800, leg_height=120, header_height=100, footer_height=80, padding=20, logo_size=60):
        self.width = width
        self.leg_height = leg_height
        self.header_height = header_height
        self.footer_height = footer_height
        self.padding = padding
        self.logo_size = logo_size
        # Assign globally loaded fonts
        self.font_m_18 = font_m_18
        self.font_m_24 = font_m_24
        self.font_b_18 = font_b_18
        self.font_b_24 = font_b_24
        self.font_b_36 = font_b_36
        # Use constants derived from Config
        self.logo_dir = LOGO_DIR
        self.default_logo_path = DEFAULT_TEAM_LOGO_PATH
        self.image = None

    def _format_odds_with_sign(self, odds: Optional[int]) -> str:
        if odds is None: return "N/A"
        if odds > 0: return f"+{odds}"
        return str(odds)

    def _load_team_logo(self, league_name: Optional[str], team_name: str) -> Optional[Image.Image]:
        """Finds and loads team logo based on league/name, falling back to default."""
        if not team_name:
             logger.warning("Load logo called with empty team name.")
             return None

        try:
            # Sanitize team name for filename
            s_team_name = team_name.replace(' ', '_').replace('/', '_')
            team_filename = f"{s_team_name}.png"

            # 1. Check league-specific folder
            final_path_to_load = None
            if league_name:
                league_folder = str(league_name).upper()
                league_specific_path = os.path.join(self.logo_dir, league_folder, team_filename)
                if os.path.exists(league_specific_path):
                    final_path_to_load = league_specific_path
                    logger.debug(f"Found logo in league folder: {final_path_to_load}")

            # 2. Check base logo folder (if not found in league folder)
            if not final_path_to_load:
                base_path = os.path.join(self.logo_dir, team_filename)
                if os.path.exists(base_path):
                    final_path_to_load = base_path
                    logger.debug(f"Found logo in base folder: {final_path_to_load}")

            # 3. Use default logo (if still not found)
            if not final_path_to_load:
                if os.path.exists(self.default_logo_path):
                    final_path_to_load = self.default_logo_path
                    logger.debug(f"Using default logo for team '{team_name}'.")
                else:
                    # This case should ideally not happen if startup checks are done
                    logger.error(f"Team logo for '{team_name}' not found, AND default logo missing: {self.default_logo_path}")
                    return None # Cannot load anything

            # Load the determined image path
            with Image.open(final_path_to_load) as logo:
                logo = logo.convert("RGBA")
                logo.thumbnail((self.logo_size, self.logo_size), Image.Resampling.LANCZOS)
                return logo.copy()

        except Exception as e:
            logger.exception(f"Error loading logo for team '{team_name}' (league '{league_name}'): {e}")
            return None

    def _draw_leg(self, draw: ImageDraw.ImageDraw, y_offset: int, leg, leg_number: int):
        """Draws a single leg. Assumes 'leg' object has needed attributes."""
        leg_top = y_offset
        leg_bottom = leg_top + self.leg_height
        draw.rectangle([0, leg_top, self.width, leg_bottom], fill=(35, 39, 42))
        draw.line([0, leg_top, self.width, leg_top], fill=DEFAULT_INDICATOR_COLOR, width=4)

        draw.text((self.padding, leg_top + self.padding // 2), f"#{leg_number}", fill=(200, 200, 200), font=self.font_b_18)

        logo_area_start_x = self.padding + 40
        text_start_x = logo_area_start_x

        # Get data from leg object
        leg_team_name = getattr(leg, 'team_name', None)
        leg_league_name = getattr(leg, 'league_name', None) # Needed to find logo
        leg_bet_type = getattr(leg, 'bet_type', 'N/A')
        leg_line = getattr(leg, 'line', '')
        leg_odds = getattr(leg, 'odds', None)

        if leg_team_name:
            # Find and load the logo dynamically using league and team name
            team_logo = self._load_team_logo(leg_league_name, leg_team_name)

            if team_logo:
                try:
                    logo_y = leg_top + (self.leg_height - team_logo.height) // 2
                    temp_image = Image.new('RGBA', self.image.size, (0, 0, 0, 0))
                    temp_image.paste(team_logo, (logo_area_start_x, logo_y), team_logo)
                    if self.image.mode != 'RGBA': self.image = self.image.convert("RGBA")
                    self.image = Image.alpha_composite(self.image, temp_image)
                    draw = ImageDraw.Draw(self.image) # Recreate draw object
                    text_start_x = logo_area_start_x + team_logo.width + self.padding
                except Exception as e:
                    logger.exception(f"Error pasting logo for leg {leg_number}, team {leg_team_name}: {e}")
            #else: logger.debug(f"No logo loaded/found for leg {leg_number}, team {leg_team_name}.")

            draw.text((text_start_x, leg_top + self.padding), str(leg_team_name), fill=(255, 255, 255), font=self.font_b_24)
            bet_line_text = f"{leg_bet_type}: {leg_line}".strip()
            draw.text((text_start_x, leg_top + self.padding + 30), bet_line_text, fill=(200, 200, 200), font=self.font_m_18)

        else: # Handle props/non-team bets
            bet_line_text = f"{leg_bet_type}: {leg_line}".strip()
            draw.text((text_start_x, leg_top + self.padding), bet_line_text, fill=(255, 255, 255), font=self.font_b_24)

        # Draw Odds
        odds_text = self._format_odds_with_sign(leg_odds)
        try:
            bbox = draw.textbbox((0, 0), odds_text, font=self.font_b_24)
            tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
        except AttributeError: tw, th = draw.textsize(odds_text, font=self.font_b_24)
        odds_x = self.width - self.padding - tw
        odds_y = leg_top + (self.leg_height - th) // 2
        draw.text((odds_x, odds_y), odds_text, fill=(255, 255, 255), font=self.font_b_24)

        draw.line([self.padding, leg_bottom -1, self.width - self.padding, leg_bottom-1], fill=(60, 60, 60), width=1)
        return draw

    def create_bet_slip(self, bet) -> Optional[BytesIO]: # Return BytesIO again
        """Generates the bet slip image. Assumes 'bet' has needed attributes. Returns BytesIO object."""
        bet_legs = getattr(bet, 'legs', [])
        bet_stake = getattr(bet, 'stake', 0.0)
        bet_total_odds = getattr(bet, 'total_odds', None)
        bet_potential_payout = getattr(bet, 'potential_payout', 0.0)
        bet_capper_name = getattr(bet, 'capper_name', None)
        bet_id = getattr(bet, 'bet_id', None)

        if not bet_legs:
            logger.error("Bet object missing 'legs' attribute or legs list is empty.")
            return None

        num_legs = len(bet_legs)
        total_height = self.header_height + (num_legs * self.leg_height) + self.footer_height
        try:
            self.image = Image.new('RGBA', (self.width, total_height), (44, 47, 51, 255))
            draw = ImageDraw.Draw(self.image)
        except Exception as e:
            logger.exception(f"Failed to create base image with PIL: {e}")
            return None

        # --- Header ---
        header_bottom = self.header_height
        header_color = DEFAULT_INDICATOR_COLOR
        draw.rectangle([0, 0, self.width, header_bottom], fill=(35, 39, 42, 255))
        draw.line([0, 0, self.width, 0], fill=header_color + (255,), width=5)

        all_legs_have_team = all(getattr(leg, 'team_name', None) for leg in bet_legs)
        is_multi_team = num_legs > 1 and all_legs_have_team
        if is_multi_team: title = "Multi-Team Parlay Bet"
        elif num_legs == 1: title = "Straight Bet"
        else: title = "Parlay Bet"

        try:
            bbox = draw.textbbox((0, 0), title, font=self.font_b_36)
            tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
        except AttributeError: tw, th = draw.textsize(title, font=self.font_b_36)
        title_x = (self.width - tw) // 2
        title_y = (self.header_height - th) // 2
        draw.text((title_x, title_y), title, fill=(255, 255, 255, 255), font=self.font_b_36)

        # --- Legs ---
        current_y = self.header_height
        try:
            for i, leg in enumerate(bet_legs):
                # Pass leg object containing league_name and team_name
                draw = self._draw_leg(draw, current_y, leg, i + 1)
                current_y += self.leg_height
        except Exception as e:
            logger.exception(f"Error occurred while drawing leg #{i+1 if 'i' in locals() else 'unknown'}: {e}")
            return None

        # --- Footer ---
        footer_top = current_y
        draw.rectangle([0, footer_top, self.width, footer_top + self.footer_height], fill=(35, 39, 42, 255))
        draw.line([0, footer_top, self.width, footer_top], fill=(60, 60, 60, 255), width=1)

        stake_text = f"Stake: {bet_stake:.2f} Units"
        odds_text = f"Odds: {self._format_odds_with_sign(bet_total_odds)}"
        payout_text = f"To Win: {bet_potential_payout:.2f} Units"

        draw.text((self.padding, footer_top + self.padding), stake_text, fill=(200, 200, 200, 255), font=self.font_m_18)
        try:
            bbox = draw.textbbox((0, 0), odds_text, font=self.font_m_18)
            tw = bbox[2] - bbox[0]
        except AttributeError: tw, _ = draw.textsize(odds_text, font=self.font_m_18)
        draw.text(((self.width - tw) // 2, footer_top + self.padding), odds_text, fill=(200, 200, 200, 255), font=self.font_m_18)
        try:
            bbox = draw.textbbox((0, 0), payout_text, font=self.font_b_18)
            tw = bbox[2] - bbox[0]
        except AttributeError: tw, _ = draw.textsize(payout_text, font=self.font_b_18)
        draw.text((self.width - self.padding - tw, footer_top + self.padding), payout_text, fill=(100, 255, 100, 255), font=self.font_b_18)

        if bet_capper_name:
            capper_text = f"Capper: {bet_capper_name}"
            draw.text((self.padding, footer_top + self.padding + 25), capper_text, fill=(180, 180, 180, 255), font=self.font_m_18)

        # --- Save to BytesIO --- ### RETURN BytesIO ###
        img_byte_arr = BytesIO()
        try:
            final_image = self.image.convert("RGB") # Convert final image to RGB
            final_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0) # Reset stream position
            logger.info(f"Successfully generated bet slip image bytes for Bet ID {bet_id if bet_id else 'N/A'}")
            return img_byte_arr # Return the BytesIO object
        except Exception as e:
            logger.exception(f"Error saving image to BytesIO: {e}")
            return None # Return None if saving fails


# --- Example Usage Block ---
# (This block remains for testing the script directly)
if __name__ == '__main__':
    # Define constants for testing if not globally available
    if 'ASSET_DIR' not in globals():
        print("Defining constants for testing purposes ONLY.")
        _test_script_dir = os.path.dirname(__file__)
        ASSET_DIR = os.path.abspath(os.path.join(_test_script_dir, '..', 'assets'))
        if not os.path.exists(ASSET_DIR): ASSET_DIR = '.'
        print(f"Using ASSET_DIR (for testing): {ASSET_DIR}")
        DEFAULT_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'GothamMedium.ttf')
        DEFAULT_BOLD_FONT_PATH = os.path.join(ASSET_DIR, 'fonts', 'GothamBold.ttf')
        LOGO_DIR = os.path.join(ASSET_DIR, 'logos')
        DEFAULT_TEAM_LOGO_PATH = os.path.join(LOGO_DIR, 'default_logo.png')
        # Redo font loading
        try:
            if not os.path.exists(DEFAULT_FONT_PATH): raise FileNotFoundError(f"[Test] Font missing: {DEFAULT_FONT_PATH}")
            if not os.path.exists(DEFAULT_BOLD_FONT_PATH): raise FileNotFoundError(f"[Test] Font missing: {DEFAULT_BOLD_FONT_PATH}")
            font_m_18 = ImageFont.truetype(DEFAULT_FONT_PATH, 18); font_m_24 = ImageFont.truetype(DEFAULT_FONT_PATH, 24)
            font_b_18 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 18); font_b_24 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 24)
            font_b_36 = ImageFont.truetype(DEFAULT_BOLD_FONT_PATH, 36)
            logger.info("[Test] Successfully loaded fonts within __main__.")
        except Exception as e: logger.critical(f"[Test] CRITICAL: Error loading fonts in __main__: {e}"); exit(1)

    from collections import namedtuple
    MockBetLeg = namedtuple("MockBetLeg", ["league_name", "team_name", "bet_type", "line", "odds"]) # No logo path needed here
    MockBet = namedtuple("MockBet", ["bet_id", "stake", "total_odds", "potential_payout", "capper_name", "legs"])

    # Setup CWD
    project_root_for_test = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if os.path.exists(os.path.join(project_root_for_test, 'config.py')): os.chdir(project_root_for_test)
    elif not os.path.exists('config.py'): print("ERROR: Cannot determine project root for testing."); exit(1)
    print(f"Test CWD: {os.getcwd()}")

    # Test Execution
    generator = BetSlipGenerator()
    print("Generating example slips (using mock data)...")

    # Example 1: Multi-Team Parlay
    multi_legs = [
        MockBetLeg(league_name='NFL', team_name='Kansas City Chiefs', bet_type='Spread', line='-7', odds=-110),
        MockBetLeg(league_name='NBA', team_name='Los Angeles Lakers', bet_type='Moneyline', line=None, odds=150)
    ]
    multi_bet = MockBet(bet_id=1, stake=1.0, total_odds=250, potential_payout=2.50, capper_name="Tester", legs=multi_legs)
    img_bytes = generator.create_bet_slip(multi_bet) # Get BytesIO object
    if img_bytes:
        try:
            with open("test_multi_team_slip.png", "wb") as f: f.write(img_bytes.getvalue()) # Save BytesIO content
            print(" - test_multi_team_slip.png generated.")
        except Exception as e: print(f" - FAILED to save multi-team slip: {e}")
    else: print(" - FAILED to generate multi-team slip (generator returned None).")

    # (Repeat similar save logic for other test cases, using BytesIO)
    # Example 2: Straight Bet
    straight_legs = [MockBetLeg(league_name='NHL', team_name='Boston Bruins', bet_type='Puck Line', line='-1.5', odds=120)]
    straight_bet = MockBet(bet_id=2, stake=2.0, total_odds=120, potential_payout=2.4, legs=straight_legs, capper_name=None)
    img_bytes_straight = generator.create_bet_slip(straight_bet)
    if img_bytes_straight:
        try:
            with open("test_straight_bet_slip.png", "wb") as f: f.write(img_bytes_straight.getvalue())
            print(" - test_straight_bet_slip.png generated.")
        except Exception as e: print(f" - FAILED to save straight bet slip: {e}")
    else: print(" - FAILED to generate straight bet slip.")

    # Example 3: Parlay with Prop
    prop_legs = [
        MockBetLeg(league_name='MLB', team_name='New York Yankees', bet_type='Total', line='O 8.5', odds=-105),
        MockBetLeg(league_name='NFL', team_name=None, bet_type='Player Rushing Yards', line='C. McCaffrey O 75.5', odds=-115) # Prop leg
    ]
    prop_bet = MockBet(bet_id=3, stake=0.5, total_odds=255, potential_payout=1.28, legs=prop_legs, capper_name="PropMaster")
    img_bytes_prop = generator.create_bet_slip(prop_bet)
    if img_bytes_prop:
         try:
            with open("test_parlay_prop_slip.png", "wb") as f: f.write(img_bytes_prop.getvalue())
            print(" - test_parlay_prop_slip.png generated.")
         except Exception as e: print(f" - FAILED to save parlay prop slip: {e}")
    else: print(" - FAILED to generate parlay prop slip.")

    # Example 4: Missing Logo (Fallback to Default)
    missing_logo_legs = [MockBetLeg(league_name='FAKE_LEAGUE', team_name='Team With No Logo', bet_type='Moneyline', line='', odds=500)]
    missing_logo_bet = MockBet(bet_id=4, stake=1.0, total_odds=500, potential_payout=5.00, legs=missing_logo_legs, capper_name="Tester")
    img_bytes_missing = generator.create_bet_slip(missing_logo_bet)
    if img_bytes_missing:
        try:
            with open("test_missing_logo_slip.png", "wb") as f: f.write(img_bytes_missing.getvalue())
            print(" - test_missing_logo_slip.png generated (should use default logo).")
        except Exception as e: print(f" - FAILED to save missing logo slip: {e}")
    else: print(" - FAILED to generate missing logo slip.")


    print("Testing complete.")
