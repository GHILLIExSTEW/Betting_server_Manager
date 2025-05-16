# betting-bot/utils/modals.py
import discord
from discord.ui import Modal, TextInput
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

# Import your project's configurations and utilities
# Adjust these paths if your config/utils structure is different
# relative to the 'betting-bot' root when this module is imported.
from config.leagues import LEAGUE_CONFIG
from utils.errors import BetServiceError # Example, if used directly in modal

# For type hinting the parent view reference without circular imports
if TYPE_CHECKING:
    from commands.straight_betting import StraightBetWorkflowView
    from commands.parlay_betting import ParlayBetWorkflowView # Example
    # Add other view types if modals reference them specifically
    # from commands.setid import ImageUploadView # Example for CapperImageURLModal's parent

logger = logging.getLogger(__name__)

class StraightBetDetailsModal(Modal):
    def __init__(self, line_type: str, selected_league_key: str, bet_details_from_view: Dict[str, Any], is_manual: bool = False):
        self.league_config = LEAGUE_CONFIG.get(selected_league_key, LEAGUE_CONFIG.get("OTHER", {}))
        super().__init__(title=f"Enter Bet Details for {self.league_config.get('name', 'Bet')}")

        self.line_type = line_type
        self.is_manual = is_manual
        self.selected_league_key = selected_league_key
        # This reference will be set by the calling view
        self.view_ref: Optional['StraightBetWorkflowView'] = None 

        participant_label = self.league_config.get('participant_label', "Team/Player")
        team_placeholder_text = self.league_config.get('team_placeholder', "Enter name (e.g., Team A or Player X)")
        
        team_field_label = participant_label
        if line_type == "player_prop" and "Player" not in participant_label:
            team_field_label = f"Player's Team (if applicable, or N/A)"
        elif line_type == "game_line" and "Team" not in participant_label:
            team_field_label = f"{participant_label} (Main Participant)"

        self.team_or_participant = TextInput(
            label=team_field_label,
            required=True, max_length=100,
            placeholder=team_placeholder_text,
            default=bet_details_from_view.get('team', '')
        )
        self.add_item(self.team_or_participant)

        if self.is_manual:
            opponent_label = "Opponent"
            if self.league_config.get('sport_type') == "Individual Player" or self.league_config.get('sport_type') == "Racing":
                opponent_label = f"Opponent {participant_label} (if H2H, or N/A)"
            opponent_placeholder_text = f"e.g., Opponent for {team_placeholder_text.split('e.g., ')[-1]}" \
                if 'e.g., ' in team_placeholder_text and self.league_config.get('sport_type') == "Team Sport" \
                else "Enter opponent name or N/A"
            self.opponent = TextInput(
                label=opponent_label,
                required=not (self.league_config.get('sport_type') in ["Individual Player", "Racing"]),
                max_length=100,
                placeholder=opponent_placeholder_text,
                default=bet_details_from_view.get('opponent', '')
            )
            self.add_item(self.opponent)

        line_label = "Line Details"
        line_placeholder_text = ""
        if line_type == "player_prop":
            line_label = f"{participant_label} Prop Details"
            line_placeholder_text = self.league_config.get('line_placeholder_player', "e.g., Player X - Points Over 20.5")
        else: # game_line
            line_label = "Game Line / Match Outcome"
            line_placeholder_text = self.league_config.get('line_placeholder_game', "e.g., Moneyline, Spread -7.5")
            if self.league_config.get('sport_type') == "Racing":
                line_label = "Race Bet Type"
            elif self.league_config.get('sport_type') == "Individual Player":
                line_label = "Match Bet Type"

        self.line_description = TextInput(
            label=line_label,
            required=True, max_length=100,
            placeholder=line_placeholder_text
        )
        self.add_item(self.line_description)

        self.odds = TextInput(
            label="Odds",
            required=True, max_length=10,
            placeholder="e.g., -110 or +200"
        )
        self.add_item(self.odds)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.view_ref:
            logger.error("Parent View (self.view_ref) not set in StraightBetDetailsModal.")
            await interaction.response.send_message("Internal error: Modal cannot communicate with parent view.", ephemeral=True)
            return

        logger.debug(f"StraightBetDetailsModal submitted by user {interaction.user.id} for league {self.selected_league_key}")
        # Defer the interaction if it hasn't been responded to yet.
        # Modals usually handle their own initial response.
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)
        else: # If already deferred (e.g. by a button that opened this modal), use followup for thinking
            await interaction.followup.send("Processing details...", ephemeral=True, thinking=True)


        try:
            team_input = self.team_or_participant.value.strip()
            opponent_input = "N/A"
            if self.is_manual and hasattr(self, 'opponent'):
                opponent_input = self.opponent.value.strip()
            elif not self.is_manual :
                selected_game_home = self.view_ref.bet_details.get("home_team_name", "")
                selected_game_away = self.view_ref.bet_details.get("away_team_name", "")
                if team_input.lower() == selected_game_home.lower():
                    opponent_input = selected_game_away
                elif team_input.lower() == selected_game_away.lower():
                    opponent_input = selected_game_home
                else:
                    if self.line_type != "player_prop":
                         opponent_input = selected_game_away if team_input != selected_game_away else selected_game_home
            
            line_value = self.line_description.value.strip()
            odds_str = self.odds.value.strip()

            if not team_input or not line_value or not odds_str:
                await interaction.followup.send("❌ All details are required in the modal.", ephemeral=True)
                return
            try:
                odds_val = float(odds_str.replace("+", ""))
            except ValueError:
                await interaction.followup.send(f"❌ Invalid odds format: '{odds_str}'. Use numbers e.g., -110 or 200.", ephemeral=True)
                return

            self.view_ref.bet_details.update({
                "line": line_value,
                "odds_str": odds_str,
                "odds": odds_val,
                "team": team_input,
                "opponent": opponent_input,
                "selected_league_key": self.selected_league_key
            })

            if self.is_manual or self.line_type == "player_prop":
                self.view_ref.home_team = team_input
                self.view_ref.away_team = opponent_input
            else:
                self.view_ref.home_team = self.view_ref.bet_details.get("home_team_name", team_input)
                self.view_ref.away_team = self.view_ref.bet_details.get("away_team_name", opponent_input)

            self.view_ref.league = self.league_config.get("name", self.selected_league_key)
            self.view_ref.line = line_value
            self.view_ref.odds = odds_val
            
            if "bet_serial" not in self.view_ref.bet_details:
                game_id_for_db = self.view_ref.bet_details.get("game_id")
                if game_id_for_db == "Other": game_id_for_db = None

                bet_serial = await self.view_ref.bot.bet_service.create_straight_bet(
                    guild_id=interaction.guild_id, user_id=interaction.user.id,
                    game_id=game_id_for_db,
                    bet_type=self.view_ref.bet_details.get("line_type", "game_line"),
                    team=team_input, opponent=opponent_input, line=line_value,
                    units=1.0, odds=odds_val, channel_id=None,
                    league=self.view_ref.league
                )
                if not bet_serial: raise BetServiceError("Failed to create bet record.")
                self.view_ref.bet_details["bet_serial"] = bet_serial
                self.view_ref.bet_id = str(bet_serial)
            else:
                self.view_ref.bet_id = str(self.view_ref.bet_details['bet_serial'])

            current_units = float(self.view_ref.bet_details.get("units", 1.0))
            bet_slip_generator = await self.view_ref.get_bet_slip_generator()
            
            display_home = self.view_ref.home_team
            display_away = self.view_ref.away_team
            if self.league_config.get('sport_type') in ["Individual Player", "Racing", "Fighting"] and not self.is_manual:
                display_home = self.view_ref.bet_details.get("home_team_name", team_input)
                display_away = self.view_ref.bet_details.get("away_team_name", "N/A")

            bet_slip_image = await bet_slip_generator.generate_bet_slip(
                home_team=display_home, away_team=display_away,
                league=self.view_ref.league, line=line_value, odds=odds_val, units=current_units,
                bet_id=self.view_ref.bet_id, timestamp=datetime.now(timezone.utc),
                bet_type=self.view_ref.bet_details.get("line_type", "straight")
            )
            if bet_slip_image:
                self.view_ref.preview_image_bytes = io.BytesIO()
                bet_slip_image.save(self.view_ref.preview_image_bytes, format='PNG')
                self.view_ref.preview_image_bytes.seek(0)
            else: self.view_ref.preview_image_bytes = None

            # The parent view (self.view_ref) will handle editing the message.
            # We just need to signal it to proceed.
            self.view_ref.current_step = 4 
            await self.view_ref.go_next(interaction) 

        except Exception as e:
            logger.exception(f"Error in StraightBetDetailsModal on_submit: {e}")
            try:
                # Ensure followup is used if interaction was already responded to (e.g. deferred)
                await interaction.followup.send("❌ Error processing details from modal. Please try again.", ephemeral=True)
            except discord.HTTPException: pass 
            if hasattr(self, "view_ref") and self.view_ref: self.view_ref.stop()
            
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.error(f"Error in StraightBetDetailsModal: {error}", exc_info=True)
        response_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try:
            await response_method('❌ Modal error. Please try again.', ephemeral=True)
        except discord.HTTPException: pass
        if hasattr(self, "view_ref") and self.view_ref: self.view_ref.stop()


# Add other modal classes here (ParlayLegDetailsModal, ParlayTotalOddsModal, etc.)
# For example:
# class ParlayLegDetailsModal(Modal): ...
# class ParlayTotalOddsModal(Modal): ...
# class CapperProfileModal(Modal): ...
# class CapperImageURLModal(Modal): ...
# class SubscriptionInfoModal(Modal): ...
