# betting-bot/commands/parlay_betting.py

"""Parlay betting workflow for placing multi-leg bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel, File, Embed
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union, Any 
from datetime import datetime, timezone
import io
import uuid 
import os
import json 
from discord.ext import commands

# Import directly from utils
from utils.errors import BetServiceError, ValidationError, GameNotFoundError
from utils.image_generator import BetSlipGenerator

logger = logging.getLogger(__name__)

# --- UI Component Classes ---
class LeagueSelect(Select):
    def __init__(self, parent_view, leagues: List[str]):
        self.parent_view = parent_view
        options = [SelectOption(label=league, value=league) for league in leagues[:24]]
        options.append(SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select League for this Leg...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.current_leg_construction_details['league'] = self.values[0]
        logger.debug(f"League selected for current leg: {self.values[0]} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class LineTypeSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="Game Line", value="game_line", description="Moneyline or game over/under"),
            SelectOption(label="Player Prop", value="player_prop", description="Bet on player performance")
        ]
        super().__init__(placeholder="Select Line Type for this Leg...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.current_leg_construction_details['line_type'] = self.values[0]
        logger.debug(f"Line Type selected for current leg: {self.values[0]} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class GameSelect(Select):
    def __init__(self, parent_view, games: List[Dict]):
        self.parent_view = parent_view
        options = []
        for game in games[:24]: 
            home = game.get('home_team_name', 'Unknown Home')
            away = game.get('away_team_name', 'Unknown Away')
            start_dt_obj = game.get('start_time')
            time_str = "Time N/A"
            if isinstance(start_dt_obj, str): 
                try:
                    start_dt_obj = datetime.fromisoformat(start_dt_obj.replace('Z', '+00:00'))
                except ValueError:
                    start_dt_obj = None 
            
            if isinstance(start_dt_obj, datetime):
                time_str = start_dt_obj.strftime('%m/%d %H:%M %Z')
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id') 
            if game_api_id is None:
                logger.warning(f"Game missing 'id': {game}")
                continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id)))
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(placeholder="Select Game for this Leg (or Other)...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        selected_game_id = self.values[0]
        self.parent_view.current_leg_construction_details['game_id'] = selected_game_id 
        if selected_game_id != "Other":
            game = next((g for g in self.parent_view.games if str(g.get('id')) == selected_game_id), None)
            if game:
                self.parent_view.current_leg_construction_details['home_team_name'] = game.get('home_team_name', 'Unknown')
                self.parent_view.current_leg_construction_details['away_team_name'] = game.get('away_team_name', 'Unknown')
            else:
                logger.warning(f"Could not find full details for selected game ID {selected_game_id}")
        logger.debug(f"Game selected for current leg: {selected_game_id} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class HomePlayerSelect(Select): # Copied from straight_betting, might need context adjustments for parlay
    def __init__(self, parent_view, players: List[str], team_name: str):
        self.parent_view = parent_view
        self.team_name = team_name
        options = [SelectOption(label=player, value=f"home_{player}") for player in players[:24]]
        if not options:
            options.append(SelectOption(label="No Players Available", value="none", emoji="❌"))
        super().__init__(placeholder=f"{team_name} Players...", options=options, min_values=0, max_values=1)

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.current_leg_construction_details['player'] = self.values[0].replace("home_", "")
            for item in self.parent_view.children:
                if isinstance(item, AwayPlayerSelect):
                    item.disabled = True
        else:
            if not self.parent_view.current_leg_construction_details.get('player'):
                 self.parent_view.current_leg_construction_details['player'] = None
        logger.debug(f"Home player selected for leg: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        if self.parent_view.current_leg_construction_details.get('player'): # Only advance if player selected from this menu
            await self.parent_view.go_next(interaction)

class AwayPlayerSelect(Select): # Copied from straight_betting
    def __init__(self, parent_view, players: List[str], team_name: str):
        self.parent_view = parent_view
        self.team_name = team_name
        options = [SelectOption(label=player, value=f"away_{player}") for player in players[:24]]
        if not options:
            options.append(SelectOption(label="No Players Available", value="none", emoji="❌"))
        super().__init__(placeholder=f"{team_name} Players...", options=options, min_values=0, max_values=1)

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.current_leg_construction_details['player'] = self.values[0].replace("away_", "")
            for item in self.parent_view.children:
                if isinstance(item, HomePlayerSelect):
                    item.disabled = True
        else:
             if not self.parent_view.current_leg_construction_details.get('player'):
                 self.parent_view.current_leg_construction_details['player'] = None
        logger.debug(f"Away player selected for leg: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        if self.parent_view.current_leg_construction_details.get('player'):
            await self.parent_view.go_next(interaction)

class ManualEntryButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Manual Entry for Leg",
            custom_id=f"parlay_manual_entry_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Manual Entry button clicked by user {interaction.user.id} for parlay leg.")
        self.parent_view.current_leg_construction_details['game_id'] = "Other" 
        self.disabled = True
        for item in self.parent_view.children:
            if isinstance(item, CancelButton) or isinstance(item, GameSelect): # Disable other relevant items
                item.disabled = True
        
        line_type = self.parent_view.current_leg_construction_details.get('line_type', 'game_line')
        leg_number = len(self.parent_view.bet_details.get('legs', [])) + 1
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True, leg_number=leg_number)
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully for parlay leg.")
            await self.parent_view.edit_message_for_current_leg(
                interaction, 
                content="Manual entry form opened for leg. Please fill in the details.",
                view=self.parent_view 
            )
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal for parlay leg: {e}")
            try:
                await self.parent_view.edit_message_for_current_leg(
                    interaction,
                    content="❌ Failed to open manual entry form. Please restart the parlay.",
                    view=None
                )
            except discord.HTTPException as e2: logger.error(f"Failed to edit message after modal error: {e2}")
            self.parent_view.stop()


class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.red,
            label="Cancel Parlay",
            custom_id=f"parlay_cancel_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Cancel Parlay button clicked by user {interaction.user.id}")
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True 

        bet_serial = self.parent_view.bet_details.get('bet_serial')
        if bet_serial:
            try:
                if hasattr(self.parent_view.bot, 'bet_service'):
                     await self.parent_view.bot.bet_service.delete_bet(bet_serial)
                     logger.info(f"Parlay bet {bet_serial} cancelled and deleted by user {interaction.user.id}.")
                     await interaction.response.edit_message(content=f"Parlay `{bet_serial}` cancelled and records deleted.", view=None)
                else:
                     logger.error("BetService not found on bot instance during parlay cancellation.")
                     await interaction.response.edit_message(content="Cancellation failed (Internal Error).", view=None)
            except Exception as e:
                logger.error(f"Failed to delete parlay bet {bet_serial}: {e}")
                await interaction.response.edit_message(content=f"Parlay `{bet_serial}` cancellation failed. Contact admin.", view=None)
        else:
             await interaction.response.edit_message(content="Parlay workflow cancelled.", view=None)
        self.parent_view.stop()

class BetDetailsModal(Modal): # For individual leg details
    def __init__(self, line_type: str, is_manual: bool = False, leg_number: int = 1):
        title = f"Leg {leg_number}: Enter Details"
        super().__init__(title=title[:45]) 
        self.line_type = line_type
        self.is_manual = is_manual
        self.leg_number = leg_number

        self.team = TextInput(label="Team Involved in this Leg", required=True, max_length=100, placeholder="Enter team name for this leg")
        self.add_item(self.team)
        
        if self.is_manual: # Only add opponent if manual, game select provides it
             self.opponent = TextInput(label="Opponent for this Leg", required=True, max_length=100, placeholder="Enter opponent name")
             self.add_item(self.opponent)

        if line_type == "player_prop":
            self.player_line = TextInput(label="Player - Line (Leg)", required=True, max_length=100, placeholder="E.g., Player Name - Points Over X.X")
            self.add_item(self.player_line)
        else: 
            self.line = TextInput(label="Line (Leg)", required=True, max_length=100, placeholder="E.g., Moneyline, Spread -X.X")
            self.add_item(self.line)

        self.odds = TextInput(label="Odds for this Leg", required=True, max_length=10, placeholder="American odds (e.g., -110)")
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"Parlay Leg Modal submitted: line_type={self.line_type}, is_manual={self.is_manual}, leg_number={self.leg_number} by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True, thinking=True) 

        try:
            team_value = self.team.value.strip()
            opponent_value = self.opponent.value.strip() if hasattr(self, 'opponent') else self.view.current_leg_construction_details.get('away_team_name', 'N/A')
            line_value = self.player_line.value.strip() if self.line_type == "player_prop" else self.line.value.strip()
            odds_str_value = self.odds.value.strip()

            if not team_value or (self.is_manual and not opponent_value) or not line_value or not odds_str_value:
                await interaction.followup.send("❌ All fields are required for the leg. Please try again.", ephemeral=True)
                return

            try:
                odds_val_str = odds_str_value.replace('+', '')
                if not odds_val_str: raise ValueError("Odds cannot be empty.")
                odds_float = float(odds_val_str)
                if -100 < odds_float < 100 and odds_float != 0:
                     raise ValueError("Odds cannot be between -99 and +99 (excluding 0).")
            except ValueError as ve:
                logger.warning(f"Invalid odds entered for parlay leg: {odds_str_value} - Error: {ve}")
                await interaction.followup.send(f"❌ Invalid odds for leg: '{odds_str_value}'. {ve}", ephemeral=True)
                return

            if not self.is_manual: # Game was selected
                selected_home = self.view.current_leg_construction_details.get('home_team_name')
                selected_away = self.view.current_leg_construction_details.get('away_team_name')
                # If team entered in modal doesn't match selected game, prioritize selected game context
                if selected_home and team_value.lower() not in [selected_home.lower(), selected_away.lower()]:
                    logger.warning(f"Team '{team_value}' entered in modal does not match selected game teams ({selected_home} vs {selected_away}). Using selected game context.")
                    # Decide which team to assign based on some logic, or require user to be clearer
                    # For now, let's assume 'team' input was specific if a game was selected
                if team_value.lower() == selected_home.lower():
                    opponent_value = selected_away
                elif team_value.lower() == selected_away.lower():
                    opponent_value = selected_home
                else: # Team entered is not one of the game teams
                    pass # Keep modal input, game_id might be primary key

            leg_details_to_add = {
                'game_id': self.view.current_leg_construction_details.get('game_id') if self.view.current_leg_construction_details.get('game_id') != 'Other' else None,
                'team': team_value,
                'opponent': opponent_value,
                'line': line_value,
                'odds': odds_float, 
                'odds_str': odds_str_value, 
                'bet_type': self.line_type,
                'league': self.view.current_leg_construction_details.get('league', 'NHL') 
            }
            await self.view.add_leg(interaction, leg_details_to_add) 
        except Exception as e:
            logger.exception(f"Error in Parlay Leg Modal on_submit: {e}")
            await interaction.followup.send("❌ Failed to process leg details. Please restart parlay.", ephemeral=True)
            if hasattr(self, 'view') and self.view: self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in Parlay Leg Modal: {error}", exc_info=True)
         try:
            if not interaction.response.is_done():
                 await interaction.response.send_message('❌ Modal error.', ephemeral=True)
            else:
                 await interaction.followup.send('❌ Modal error.', ephemeral=True)
         except discord.HTTPException: pass
         if hasattr(self, 'view') and self.view: self.view.stop()


class UnitsSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="0.5 Units", value="0.5"),
            SelectOption(label="1 Unit", value="1.0"),
            SelectOption(label="1.5 Units", value="1.5"),
            SelectOption(label="2 Units", value="2.0"),
            SelectOption(label="2.5 Units", value="2.5"),
            SelectOption(label="3 Units", value="3.0")
        ]
        super().__init__(placeholder="Select Total Units for Parlay...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        units_str_val = self.values[0]
        self.parent_view.bet_details['units_str'] = units_str_val 
        logger.debug(f"Total units selected for parlay: {units_str_val} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        # Generate bet slip preview
        try:
            if self.parent_view.bet_slip_generator is None:
                self.parent_view.bet_slip_generator = await self.parent_view.bot.get_bet_slip_generator(self.parent_view.original_interaction.guild_id)
            
            legs = self.parent_view.bet_details.get('legs', [])
            if not legs:
                logger.error("No legs found in parlay bet details")
                return
                
            league = legs[0].get('league', 'UNKNOWN_LEAGUE')
            game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
            is_sgp = len(game_ids) == 1 and len(legs) > 1
            
            bet_slip = self.parent_view.bet_slip_generator.generate_bet_slip(
                home_team=legs[0].get('team', 'N/A'),
                away_team=legs[0].get('opponent', 'N/A'),
                league=league,
                line="Parlay",
                odds=float(self.parent_view.bet_details.get('total_odds', 0)),
                units=float(units_str_val),
                bet_id=str(self.parent_view.bet_details.get('bet_serial', '')),
                timestamp=datetime.now(timezone.utc),
                bet_type="parlay",
                parlay_legs=legs,
                is_same_game=is_sgp
            )
            
            if bet_slip:
                buffer = io.BytesIO()
                bet_slip.save(buffer, format="PNG")
                buffer.seek(0)
                await self.parent_view.message.edit(attachments=[discord.File(buffer, filename="parlay_slip.png")])
                logger.debug("Parlay bet slip preview generated and attached")
        except Exception as e:
            logger.exception(f"Error generating parlay bet slip preview: {e}")
            # Continue with the workflow even if image generation fails
        await self.parent_view.go_next(interaction)


class AddLegButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Add Another Leg",
            custom_id=f"parlay_add_leg_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Add Leg button clicked by user {interaction.user.id}")
        self.parent_view.current_step = 0  # Reset step to 0 to start leg selection from league (go_next increments to 1)
        self.parent_view.current_leg_construction_details = {} # Clear details for the new leg
        # Keep existing 'legs' list and 'bet_serial' if already created
        
        # Defer before editing and calling go_next
        await interaction.response.defer() 
        await self.parent_view.edit_message_for_current_leg(
            interaction, 
            content="Starting next leg...", 
            view=None # Temporarily remove view while processing
        )
        await self.parent_view.go_next(interaction)

class FinalizeButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.blurple,
            label="Finalize Parlay",
            custom_id=f"parlay_finalize_{parent_view.original_interaction.id}",
            disabled=len(parent_view.bet_details.get('legs', [])) < 1 # Allow finalizing with 1 leg (becomes straight) or more
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Finalize Parlay button clicked by user {interaction.user.id}")
        
        legs_data = self.parent_view.bet_details.get('legs', [])
        if not legs_data:
            await interaction.response.send_message("❌ Cannot finalize an empty parlay. Please add at least one leg.", ephemeral=True)
            return

        total_odds = self.parent_view._calculate_parlay_odds(legs_data)
        self.parent_view.bet_details['total_odds'] = total_odds 
        self.parent_view.bet_details['total_odds_str'] = self.parent_view._format_odds_with_sign(total_odds) 

        for item in self.parent_view.children: 
            if isinstance(item, Button): item.disabled = True
        
        # Defer before editing and proceeding
        await interaction.response.defer()
        await self.parent_view.edit_message_for_current_leg(
            interaction, 
            content=f"Finalizing parlay... Calculated Total Odds: {self.parent_view.bet_details['total_odds_str']}. Select total units.", 
            view=self.parent_view
        )
        
        self.parent_view.current_step = 5 # Advance to Units selection step
        await self.parent_view.go_next(interaction)


class LegDecisionView(View):
    def __init__(self, parent_view: 'ParlayBetWorkflowView'): 
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.add_item(AddLegButton(self.parent_view))
        # FinalizeButton is re-added here and its disabled state is re-evaluated
        finalize_button = FinalizeButton(self.parent_view)
        finalize_button.disabled = len(self.parent_view.bet_details.get('legs', [])) < 1 # Min 1 leg to finalize
        self.add_item(finalize_button) 
        self.add_item(CancelButton(self.parent_view))

class ChannelSelect(Select):
    def __init__(self, parent_view, channels: List[TextChannel]):
        self.parent_view = parent_view
        options = [
            SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"Channel ID: {channel.id}"
            )
            for channel in channels
        ]
        super().__init__(
            placeholder="Select channel to post bet...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        channel_id = int(self.values[0])
        self.parent_view.bet_details["channel_id"] = channel_id
        logger.debug(f"Channel selected: {channel_id} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class ConfirmButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Confirm & Post Parlay",
            custom_id=f"parlay_confirm_bet_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Confirm Parlay button clicked by user {interaction.user.id}")
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        await interaction.response.edit_message(view=self.parent_view) 
        await self.parent_view.submit_bet(interaction)

# --- Main Workflow View ---
class ParlayBetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot): 
        super().__init__(timeout=1800) 
        self.original_interaction = interaction
        self.bot = bot 
        self.current_step = 0
        self.bet_details: Dict[str, Any] = {'legs': [], 'bet_type': 'parlay'}
        self.current_leg_construction_details: Dict[str, Any] = {} 
        self.games: List[Dict] = [] 
        self.message: Optional[Union[discord.WebhookMessage, discord.InteractionMessage]] = None 
        self.is_processing = False 
        self.latest_interaction = interaction 
        self.bet_slip_generator = None  # Will be initialized when needed
        self.preview_image_bytes: Optional[io.BytesIO] = None 

    async def get_bet_slip_generator(self) -> BetSlipGenerator:
        """Get the BetSlipGenerator for the current guild."""
        if self.bet_slip_generator is None:
            self.bet_slip_generator = await self.bot.get_bet_slip_generator(self.original_interaction.guild_id)
        return self.bet_slip_generator

    def _format_odds_with_sign(self, odds: Optional[float]) -> str:
        if odds is None: return "N/A"
        try:
            odds_num = int(float(odds)) 
            if odds_num > 0: return f"+{odds_num}"
            return str(odds_num)
        except (ValueError, TypeError):
            logger.warning(f"Could not format odds for display: {odds}")
            return "N/A"

    def _calculate_parlay_odds(self, legs: List[Dict[str, Any]]) -> float:
        if not legs: return 0.0
        total_decimal_odds = 1.0
        try:
            for leg in legs:
                odds = float(leg.get('odds', 0)) 
                if odds == 0: continue 
                decimal_leg = (odds / 100.0) + 1.0 if odds > 0 else (100.0 / abs(odds)) + 1.0
                total_decimal_odds *= decimal_leg
            if total_decimal_odds <= 1.0: return 0.0
            return round((total_decimal_odds - 1.0) * 100.0 if total_decimal_odds >= 2.0 else -100.0 / (total_decimal_odds - 1.0))
        except (ValueError, TypeError, KeyError) as e:
             logger.error(f"Error calculating parlay odds from legs: {legs}. Error: {e}")
             return 0.0

    async def add_leg(self, interaction: Interaction, leg_details: Dict[str, Any]):
        if 'legs' not in self.bet_details: self.bet_details['legs'] = []
        required_keys = ['team', 'opponent', 'line', 'odds', 'odds_str', 'bet_type', 'league']
        if not all(key in leg_details for key in required_keys):
             logger.error(f"Attempted to add invalid leg to parlay: {leg_details}")
             # Use the interaction from the modal submit for the followup
             await interaction.followup.send("❌ Internal error: Leg details were incomplete. Please restart.", ephemeral=True)
             self.stop()
             return
        self.bet_details['legs'].append(leg_details)
        self.current_leg_construction_details = {} 
        leg_count = len(self.bet_details['legs'])
        logger.info(f"Leg {leg_count} added to parlay by user {interaction.user.id}. Details: {leg_details}")
        
        summary_lines = [f"**Parlay Legs ({leg_count}):**"]
        for i, leg in enumerate(self.bet_details['legs']):
            summary_lines.append(f"{i+1}. {leg['league']}: {leg['line']} ({leg.get('team','N/A')} vs {leg.get('opponent','N/A')}) @ {leg['odds_str']}")
        summary_text = "\n".join(summary_lines)

        decision_view = LegDecisionView(self)
        # Edit the message associated with the *original* interaction that started the view,
        # or the latest message updated by the view. The interaction here is from the modal.
        await self.edit_message_for_current_leg(interaction, content=f"{summary_text}\n\nAdd another leg or finalize?", view=decision_view)
        self.current_step = 4 # Ready for decision (Add/Finalize) or next step in go_next after this
                               # Setting to 4 means next go_next call (if from finalize) will be step 5 (Units)

    async def start_flow(self):
        logger.debug(f"Starting parlay bet workflow for user {self.original_interaction.user} (ID: {self.original_interaction.user.id})")
        try:
            if not self.original_interaction.response.is_done():
                 await self.original_interaction.response.send_message("Starting parlay bet placement...", view=self, ephemeral=True)
                 self.message = await self.original_interaction.original_response()
            else:
                 if not self.message:
                      self.message = await self.original_interaction.followup.send("Starting parlay bet placement...", view=self, ephemeral=True)
            await self.go_next(self.original_interaction)
        except discord.HTTPException as e:
            logger.error(f"Failed to send initial message/start flow for parlay workflow: {e}")
            try: await self.original_interaction.followup.send("❌ Failed to start parlay workflow.", ephemeral=True)
            except: pass
            self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this parlay placement.", ephemeral=True)
            return False
        self.latest_interaction = interaction 
        return True
    
    async def edit_message_for_current_leg(self, interaction_to_edit_from: Interaction, content: Optional[str] = None, view: Optional[View] = None, embed: Optional[discord.Embed] = None, file: Optional[File] = None):
        log_info = f"Editing main parlay message: content={content is not None}, view={view is not None}"
        logger.debug(log_info)
        attachments = [file] if file else []
        try:
            # The `interaction_to_edit_from` is the one from the component (button/select) or modal.
            # We want to edit the message that these components are/were attached to, which is `self.message`.
            if self.message:
                await self.message.edit(content=content, embed=embed, view=view, attachments=attachments)
            else: # Fallback to editing the original interaction if self.message isn't set
                logger.warning("self.message not set in ParlayBetWorkflowView, attempting to edit original_interaction.")
                await self.original_interaction.edit_original_response(content=content, embed=embed, view=view, attachments=attachments)

        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Failed to edit main parlay workflow message: {e}. Interaction type: {interaction_to_edit_from.type if interaction_to_edit_from else 'N/A'}")
            # If self.message.edit fails, the interaction_to_edit_from might be the modal's ack,
            # so a followup on it might not be what we want for the main view message.
            # It's better to try and ensure self.message is always the target.
            # If interaction_to_edit_from *is* the interaction for the view message, then followup can be attempted.
            if interaction_to_edit_from and interaction_to_edit_from.message and interaction_to_edit_from.message.id == (self.message.id if self.message else None):
                try:
                    await interaction_to_edit_from.followup.send(content if content else "Updating display...", ephemeral=True, view=view, files=attachments if attachments else None)
                    if view : self.message = await interaction_to_edit_from.original_response() # Try to re-capture
                except discord.HTTPException as fe:
                    logger.error(f"Failed to send followup after message edit error: {fe}")
            else:
                logger.error(f"Cannot reliably update user after message edit error. Main message: {self.message.id if self.message else 'None'}")

        except Exception as e:
            logger.exception(f"Unexpected error editing main parlay workflow message: {e}")


    async def go_next(self, interaction: Interaction):
        if self.is_processing:
            logger.debug(f"Skipping go_next; already processing step {self.current_step}")
            if not interaction.response.is_done():
                try: await interaction.response.defer()
                except: pass
            return
        self.is_processing = True

        if not interaction.response.is_done(): # Safety defer
            try: await interaction.response.defer()
            except discord.HTTPException as e:
                logger.warning(f"Defer in go_next failed for {interaction.id}: {e}")
        
        try:
            logger.debug(f"Processing go_next: current_step={self.current_step} for user {interaction.user.id}")
            self.clear_items()
            self.current_step += 1
            step_content = f"**Step {self.current_step}**"
            file_to_send = None
            logger.debug(f"Entering step {self.current_step}")

            leg_count = len(self.bet_details.get('legs', []))
            step_content = f"**Parlay Leg {leg_count + 1} - Step {self.current_step}**"
            if self.current_step > 5 : # After unit selection
                 step_content = f"**Finalizing Parlay - Step {self.current_step}**"

            if self.current_step == 1: 
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                self.add_item(LeagueSelect(self, allowed_leagues))
                self.add_item(CancelButton(self))
                step_content += ": Select League for this Leg"
                await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
            elif self.current_step == 2: 
                self.add_item(LineTypeSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Line Type for this Leg"
                await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
            elif self.current_step == 3: 
                league = self.current_leg_construction_details.get('league')
                if not league:
                    logger.error("No league selected for current parlay leg.")
                    await self.edit_message_for_current_leg(interaction, content="❌ No league for leg. Restart.", view=None); self.stop(); return
                self.games = [] 
                if league != "Other" and hasattr(self.bot, 'game_service'):
                    try:
                        logger.debug(f"Fetching scheduled games for parlay leg: {league}, guild: {interaction.guild_id}")
                        # CORRECTED CALL
                        self.games = await self.bot.game_service.get_league_games(
                            guild_id=interaction.guild_id, league=league, status='scheduled', limit=25
                        )
                        logger.debug(f"Fetched {len(self.games)} games for {league} leg.")
                    except Exception as e:
                        logger.exception(f"Error fetching games for parlay leg (league {league}): {e}")
                if self.games: 
                    self.add_item(GameSelect(self, self.games))
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content += f": Select Game for {league} Leg (or Enter Manually)"
                    await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
                else: 
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content = f"No games for {league} leg. Enter details manually." if league != "Other" else "Enter game details manually."
                    await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
            elif self.current_step == 4: # Modal trigger for leg details
                line_type = self.current_leg_construction_details.get('line_type')
                game_id = self.current_leg_construction_details.get('game_id') 
                is_manual = game_id == "Other"
                leg_number = leg_count + 1
                # (Player select logic can be added here if needed, similar to straight_betting)
                modal = BetDetailsModal(line_type=line_type, is_manual=is_manual, leg_number=leg_number)
                modal.view = self
                try: 
                    await interaction.response.send_modal(modal) # This interaction is from previous component
                except discord.HTTPException as e:
                    logger.error(f"Failed to send Parlay BetDetailsModal: {e}")
                    await self.original_interaction.followup.send("❌ Failed to open details form.", ephemeral=True); self.stop()
                self.is_processing = False 
                return 
            # Step 5 (LegDecisionView) is handled by add_leg method
            elif self.current_step == 6:
                # Get all writable text channels
                channels = [
                    channel for channel in interaction.guild.text_channels
                    if channel.permissions_for(interaction.guild.me).send_messages
                ]
                
                if not channels:
                    await self.edit_message_for_current_leg(interaction, content="❌ No writable channels found.", view=None)
                    self.stop()
                    self.is_processing = False
                    return
                
                self.add_item(ChannelSelect(self, channels))
                self.add_item(CancelButton(self))
                step_content += ": Select Channel"
                await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
                self.is_processing = False
                return
            elif self.current_step == 7:  # Units Selection (after Finalize)
                self.add_item(UnitsSelect(self))
                self.add_item(CancelButton(self))
                step_content = f"**Finalize Parlay**: Select Total Units (Overall Odds: {self.bet_details.get('total_odds_str', 'N/A')})"
                await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
            elif self.current_step == 8:  # Confirmation
                if not all(k in self.bet_details for k in ['bet_serial', 'channel_id']):
                    await self.edit_message_for_current_leg(interaction, content="❌ Details incomplete.", view=None)
                    self.stop()
                    return

                # Generate final parlay slip image
                try:
                    file_to_send = None
                    if self.preview_image_bytes:
                        self.preview_image_bytes.seek(0)
                        file_to_send = File(
                            self.preview_image_bytes,
                            filename="parlay_slip.png"
                        )
                except Exception as e:
                    logger.exception(f"Failed to generate final parlay slip image: {e}")
                    await self.edit_message_for_current_leg(interaction, content="❌ Failed to generate parlay slip.", view=None)
                    self.stop()
                    return

                self.add_item(ConfirmButton(self))
                self.add_item(CancelButton(self))
                confirmation_text = "**Confirm Your Parlay**\n\n"
                for i, leg in enumerate(self.bet_details.get('legs', []), 1):
                    confirmation_text += f"**Leg {i}**:\n"
                    confirmation_text += f"League: {leg.get('league', 'N/A')}\n"
                    confirmation_text += f"Game: {leg.get('away_team_name', 'N/A')} @ {leg.get('home_team_name', 'N/A')}\n"
                    if leg.get('player'):
                        confirmation_text += f"Player: {leg.get('player', 'N/A')}\n"
                    confirmation_text += f"Line: {leg.get('line', 'N/A')}\n"
                    confirmation_text += f"Odds: {leg.get('odds', 'N/A')}\n\n"
                confirmation_text += f"Total Odds: {self.bet_details.get('total_odds', 'N/A')}\n"
                confirmation_text += f"Units: {self.bet_details.get('units_str', 'N/A')}\n"
                confirmation_text += f"Channel: <#{self.bet_details.get('channel_id', 'N/A')}>\n\n"
                confirmation_text += "Click Confirm to place your parlay."
                await self.edit_message_for_current_leg(interaction, content=confirmation_text, view=self, file=file_to_send)
                self.is_processing = False
                return
            else: 
                logger.error(f"ParlayBetWorkflowView unexpected step: {self.current_step}")
                await self.edit_message_for_current_leg(interaction, content="❌ Invalid step.", view=None); self.stop()
        except Exception as e:
            logger.exception(f"Error in parlay workflow step {self.current_step}: {e}")
            await self.edit_message_for_current_leg(interaction or self.latest_interaction, content="❌ Unexpected error.", view=None)
            self.stop()
        finally:
            self.is_processing = False

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        bet_serial = details.get('bet_serial')
        if not bet_serial:
             logger.error("Attempted to submit parlay without bet_serial.")
             await self.edit_message_for_current_leg(interaction, content="❌ Bet ID missing.", view=None); self.stop(); return
        logger.info(f"Submitting parlay {bet_serial} by user {interaction.user.id}")
        await self.edit_message_for_current_leg(interaction, content="Processing & posting parlay...", view=None, file=None)
        try:
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None
            if not post_channel or not isinstance(post_channel, TextChannel):
                raise ValueError(f"Invalid channel <#{post_channel_id}>.")

            units = float(details.get('units_str', 1.0))
            total_odds = float(details.get('total_odds', 0.0))
            bet_details_json = json.dumps({'legs': details.get('legs', [])}) 

            update_query = """
                UPDATE bets SET units = %s, odds = %s, channel_id = %s, confirmed = 1, bet_details = %s, legs = %s
                WHERE bet_serial = %s 
            """ # Removed AND confirmed = 0 to allow updates if somehow confirmed earlier
            rowcount, _ = await self.bot.db_manager.execute(
                update_query, units, total_odds, post_channel_id, bet_details_json, len(details.get('legs',[])), bet_serial
            )
            if rowcount is None or rowcount == 0:
                 logger.warning(f"Parlay {bet_serial} update for confirmation affected 0 rows. It might have been already fully updated or an issue occurred.")
                 # Check if it's already in the desired state
                 check_bet = await self.bot.db_manager.fetch_one("SELECT * FROM bets WHERE bet_serial = %s", (bet_serial,))
                 if not (check_bet and check_bet['confirmed'] == 1 and check_bet['channel_id'] == post_channel_id):
                     raise BetServiceError("Failed to confirm parlay in DB or already confirmed with different data.")
            
            final_image_bytes = self.preview_image_bytes
            if not final_image_bytes: # Regenerate
                 legs = details.get('legs', [])
                 league = legs[0].get('league', 'UNKNOWN_LEAGUE') if legs else 'UNKNOWN_LEAGUE'
                 game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
                 is_sgp = len(game_ids) == 1 and len(legs) > 1
                 bet_slip_image = await self.get_bet_slip_generator().generate_bet_slip(
                     home_team=legs[0].get('team', 'N/A') if legs else 'N/A', away_team=legs[0].get('opponent', 'N/A') if legs else 'N/A',
                     league=league, line="Parlay", odds=total_odds, units=units, bet_id=str(bet_serial),
                     timestamp=datetime.now(timezone.utc), bet_type="parlay", parlay_legs=legs, is_same_game=is_sgp
                 )
                 final_image_bytes = io.BytesIO(); bet_slip_image.save(final_image_bytes, format='PNG')
            
            final_image_bytes.seek(0)
            discord_file = File(final_image_bytes, filename=f"parlay_slip_{bet_serial}.png")
            
            role_mention = ""; display_name = interaction.user.display_name; avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            # (Code to fetch settings, capper info would be here)
            
            webhook = None
            try:
                webhooks = await post_channel.webhooks()
                webhook = next((wh for wh in webhooks if wh.user and wh.user.id == self.bot.user.id), None)
                if not webhook: webhook = await post_channel.create_webhook(name=f"{self.bot.user.name} Parlays"[:100])
            except Exception as e: logger.error(f"Webhook setup failed: {e}"); raise ValueError("Webhook setup failed.")
            
            sent_message = await webhook.send(file=discord_file, username=display_name[:80], avatar_url=avatar_url, wait=True, content=role_mention)
            
            if sent_message and hasattr(self.bot.bet_service, 'pending_reactions'):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial, 'user_id': interaction.user.id, 'guild_id': interaction.guild_id,
                    'channel_id': post_channel_id, 'legs': details.get('legs'), 'bet_type': 'parlay'
                }
            await self.edit_message_for_current_leg(interaction, content=f"✅ Parlay placed! (ID: `{bet_serial}`). Posted to {post_channel.mention}.", view=None)
        except Exception as e:
            logger.exception(f"Error submitting parlay {bet_serial}: {e}")
            await self.edit_message_for_current_leg(interaction, content=f"❌ Error placing parlay: {e}", view=None)
        finally:
            if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None
            self.stop()

# async def setup(bot: commands.Bot): 
#     logger.info("ParlayBetWorkflow components loaded.")
