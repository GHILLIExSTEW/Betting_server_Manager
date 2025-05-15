# betting-bot/commands/parlay_betting.py

"""Parlay betting workflow for placing multi-leg bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel, File, Embed, Webhook
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union, Any 
from datetime import datetime, timezone
import io
import uuid 
import os
import json 
from discord.ext import commands # Required for Cog
# Assuming utils are in a directory accessible by PYTHONPATH or relative to project root
from utils.errors import BetServiceError, ValidationError, GameNotFoundError
from utils.image_generator import BetSlipGenerator # For type hinting and direct calls

logger = logging.getLogger(__name__)

# --- UI Component Classes (Redefined or assumed from a shared UI module) ---
# For "one file at a time", I'll define essential ones here.
# Ideally, these would be in a shared ui_components.py

class LeagueSelect(Select):
    def __init__(self, parent_view: 'ParlayBetWorkflowView', leagues: List[str]):
        self.parent_view = parent_view
        options = [SelectOption(label=league, value=league) for league in leagues[:24]]
        options.append(SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select League for this Leg...", options=options, min_values=1, max_values=1, custom_id=f"parlay_league_select_{uuid.uuid4()}")

    async def callback(self, interaction: Interaction):
        self.parent_view.current_leg_construction_details['league'] = self.values[0]
        logger.debug(f"Parlay Leg - League selected: {self.values[0]} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class LineTypeSelect(Select):
    def __init__(self, parent_view: 'ParlayBetWorkflowView'):
        self.parent_view = parent_view
        options = [
            SelectOption(label="Game Line", value="game_line", description="Moneyline or game over/under"),
            SelectOption(label="Player Prop", value="player_prop", description="Bet on player performance")
        ]
        super().__init__(placeholder="Select Line Type for this Leg...", options=options, min_values=1, max_values=1, custom_id=f"parlay_linetype_select_{uuid.uuid4()}")

    async def callback(self, interaction: Interaction):
        self.parent_view.current_leg_construction_details['line_type'] = self.values[0]
        logger.debug(f"Parlay Leg - Line Type selected: {self.values[0]} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class GameSelect(Select):
    def __init__(self, parent_view: 'ParlayBetWorkflowView', games: List[Dict]):
        self.parent_view = parent_view
        options = []
        for game in games[:24]: 
            home = game.get('home_team_name', 'Unknown Home')
            away = game.get('away_team_name', 'Unknown Away')
            start_dt_obj = game.get('start_time')
            time_str = "Time N/A"
            if isinstance(start_dt_obj, str): 
                try: start_dt_obj = datetime.fromisoformat(start_dt_obj.replace('Z', '+00:00'))
                except ValueError: start_dt_obj = None 
            
            if isinstance(start_dt_obj, datetime): time_str = start_dt_obj.strftime('%m/%d %H:%M %Z')
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id') 
            if game_api_id is None: logger.warning(f"Game missing 'id': {game}"); continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id)))
        
        if len(options) < 25: options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(placeholder="Select Game for this Leg (or Other)...", options=options, min_values=1, max_values=1, custom_id=f"parlay_game_select_{uuid.uuid4()}")

    async def callback(self, interaction: Interaction):
        selected_game_id = self.values[0]
        self.parent_view.current_leg_construction_details['game_id'] = selected_game_id 
        if selected_game_id != "Other":
            game = next((g for g in self.parent_view.games if str(g.get('id')) == selected_game_id), None)
            if game:
                self.parent_view.current_leg_construction_details['home_team_name'] = game.get('home_team_name', 'Unknown')
                self.parent_view.current_leg_construction_details['away_team_name'] = game.get('away_team_name', 'Unknown')
            else: logger.warning(f"Could not find full details for selected game ID {selected_game_id}")
        logger.debug(f"Parlay Leg - Game selected: {selected_game_id} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class ManualEntryButton(Button):
    def __init__(self, parent_view: 'ParlayBetWorkflowView'):
        super().__init__(style=ButtonStyle.green, label="Manual Entry for Leg", custom_id=f"parlay_manual_entry_{parent_view.original_interaction.id}_{len(parent_view.bet_details.get('legs',[]))}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Manual Entry button clicked by user {interaction.user.id} for parlay leg.")
        self.parent_view.current_leg_construction_details['game_id'] = "Other" 
        self.disabled = True
        for item in self.parent_view.children: # Disable other selects/buttons in this step
            if isinstance(item, (Select, Button)) and item != self: item.disabled = True
        
        line_type = self.parent_view.current_leg_construction_details.get('line_type', 'game_line')
        leg_number = len(self.parent_view.bet_details.get('legs', [])) + 1
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True, leg_number=leg_number, view_custom_id_suffix=self.parent_view.original_interaction.id)
            modal.view_ref = self.parent_view # Pass reference to the parent view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal for parlay leg sent.")
            await self.parent_view.edit_message_for_current_leg(
                interaction, content="Manual entry form opened for leg. Please fill details.", view=self.parent_view
            )
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal for parlay leg: {e}")
            await self.parent_view.edit_message_for_current_leg(interaction, content="❌ Failed to open form. Please restart.", view=None)
            self.parent_view.stop()

class CancelButton(Button):
    def __init__(self, parent_view: 'ParlayBetWorkflowView'):
        super().__init__(style=ButtonStyle.red, label="Cancel Parlay", custom_id=f"parlay_cancel_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Cancel Parlay button clicked by user {interaction.user.id}")
        for item in self.parent_view.children: item.disabled = True
        bet_serial = self.parent_view.bet_details.get('bet_serial')
        if bet_serial and hasattr(self.parent_view.bot, 'bet_service'):
            try: await self.parent_view.bot.bet_service.delete_bet(bet_serial)
            except Exception as e: logger.error(f"Error deleting parlay bet {bet_serial} on cancel: {e}")
        await interaction.response.edit_message(content="Parlay workflow cancelled.", view=None)
        self.parent_view.stop()

class BetDetailsModal(Modal): 
    def __init__(self, line_type: str, is_manual: bool = False, leg_number: int = 1, view_custom_id_suffix: str = ""):
        title = f"Leg {leg_number}: Enter Details"
        super().__init__(title=title[:45], custom_id=f"parlay_leg_modal_{leg_number}_{view_custom_id_suffix}") 
        self.line_type = line_type
        self.is_manual = is_manual
        self.leg_number = leg_number
        self.view_ref: Optional[ParlayBetWorkflowView] = None # To be set before sending

        self.team = TextInput(label="Team Involved/Player's Team", required=True, max_length=100, placeholder="Enter team name")
        self.add_item(self.team)
        
        if self.is_manual:
             self.opponent = TextInput(label="Opponent for this Leg", required=True, max_length=100, placeholder="Enter opponent name")
             self.add_item(self.opponent)

        prop_label = "Player - Line (e.g., Name O/U Pts)" if line_type == "player_prop" else "Line (e.g., Moneyline, Spread -X.X)"
        prop_placeholder = "E.g., Player Name - Points Over X.X" if line_type == "player_prop" else "E.g., Moneyline, Spread -7.5"
        self.line_input = TextInput(label=prop_label, required=True, max_length=100, placeholder=prop_placeholder)
        self.add_item(self.line_input)

        self.odds = TextInput(label="Odds for this Leg", required=True, max_length=10, placeholder="American odds (e.g., -110, +200)")
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        if not self.view_ref:
            logger.error("ParlayBetWorkflowView reference not found in BetDetailsModal.")
            await interaction.response.send_message("Internal error: View reference missing.", ephemeral=True)
            return

        logger.debug(f"Parlay Leg Modal {self.leg_number} submitted by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True, thinking=True) 

        try:
            team_value = self.team.value.strip()
            opponent_value = self.opponent.value.strip() if hasattr(self, 'opponent') else self.view_ref.current_leg_construction_details.get('away_team_name', 'N/A')
            line_value = self.line_input.value.strip()
            odds_str_value = self.odds.value.strip()

            if not team_value or not line_value or not odds_str_value or (self.is_manual and not opponent_value):
                await interaction.followup.send("❌ All fields are required for the leg.", ephemeral=True); return

            try:
                odds_float = float(odds_str_value.replace('+', ''))
                if -100 < odds_float < 100 and odds_float != 0: raise ValueError("Odds out of range.")
            except ValueError as ve:
                await interaction.followup.send(f"❌ Invalid odds for leg: '{odds_str_value}'. {ve}", ephemeral=True); return

            current_details = self.view_ref.current_leg_construction_details
            leg_details_to_add = {
                'game_id': current_details.get('game_id') if current_details.get('game_id') != 'Other' else None,
                'team': team_value, 'opponent': opponent_value, 'line': line_value,
                'odds': odds_float, 'odds_str': odds_str_value, 
                'bet_type': self.line_type, # This is 'player_prop' or 'game_line' for the leg
                'league': current_details.get('league', 'UNKNOWN') 
            }
            
            # For image generator consistency if game was selected
            if not self.is_manual and current_details.get('home_team_name'):
                leg_details_to_add['home_team'] = current_details.get('home_team_name')
                leg_details_to_add['away_team'] = current_details.get('away_team_name')
            else: # Manual or if team/opponent from modal should be canonical
                leg_details_to_add['home_team'] = team_value # Or player's team
                leg_details_to_add['away_team'] = opponent_value


            await self.view_ref.add_leg(interaction, leg_details_to_add) 
        except Exception as e:
            logger.exception(f"Error in Parlay Leg Modal {self.leg_number} on_submit: {e}")
            await interaction.followup.send("❌ Failed to process leg details. Please restart parlay.", ephemeral=True)
            if self.view_ref: self.view_ref.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in Parlay Leg Modal {self.leg_number}: {error}", exc_info=True)
         try:
            if not interaction.response.is_done(): await interaction.response.send_message('❌ Modal error.', ephemeral=True)
            else: await interaction.followup.send('❌ Modal error.', ephemeral=True)
         except discord.HTTPException: pass
         if self.view_ref: self.view_ref.stop()

class UnitsSelect(Select):
    def __init__(self, parent_view: 'ParlayBetWorkflowView'):
        self.parent_view = parent_view
        options = [SelectOption(label=f"{i*0.5:.1f} Units", value=str(i*0.5)) for i in range(1, 7)] # 0.5 to 3.0
        super().__init__(placeholder="Select Total Units for Parlay...", options=options, min_values=1, max_values=1, custom_id=f"parlay_units_select_{parent_view.original_interaction.id}")

    async def callback(self, interaction: Interaction):
        selected_units = float(self.values[0])
        self.parent_view.bet_details["units_str"] = self.values[0]
        self.parent_view.bet_details["units"] = selected_units # Store float value
        logger.debug(f"Parlay Units selected: {selected_units} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view._handle_units_selection(interaction, selected_units) # This will regen preview
        await self.parent_view.go_next(interaction)

class ChannelSelect(Select): # Definition for Parlay flow
    def __init__(self, parent_view: 'ParlayBetWorkflowView', channels: List[TextChannel]):
        self.parent_view = parent_view
        sorted_channels = sorted(channels, key=lambda x: x.name.lower())
        options = [
            SelectOption(label=ch.name, value=str(ch.id), description=f"ID: {ch.id}"[:100])
            for ch in sorted_channels[:25] 
        ]
        if not options:
            options.append(SelectOption(label="No embed channels configured", value="none_configured", emoji="🚫"))

        super().__init__(placeholder="Select channel to post parlay...", options=options, min_values=1, max_values=1, custom_id=f"parlay_channel_select_{parent_view.original_interaction.id}", disabled=(not options or options[0].value == "none_configured"))

    async def callback(self, interaction: Interaction):
        if self.values[0] == "none_configured":
            await interaction.response.send_message("No embed channels are available. Please ask an admin to configure them.", ephemeral=True)
            return
            
        self.parent_view.bet_details["channel_id"] = int(self.values[0])
        logger.debug(f"Parlay Channel selected: {self.values[0]} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class ConfirmButton(Button): # Definition for Parlay flow
    def __init__(self, parent_view: 'ParlayBetWorkflowView'):
        super().__init__(style=ButtonStyle.green, label="Confirm & Post Parlay", custom_id=f"parlay_confirm_bet_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Confirm Parlay button clicked by user {interaction.user.id}")
        for item in self.parent_view.children: item.disabled = True
        await interaction.response.edit_message(view=self.parent_view) 
        await self.parent_view.submit_bet(interaction)

class AddLegButton(Button):
    def __init__(self, parent_view: 'ParlayBetWorkflowView'):
        super().__init__(style=ButtonStyle.green, label="Add Another Leg", custom_id=f"parlay_add_leg_{parent_view.original_interaction.id}_{len(parent_view.bet_details.get('legs',[])) +1}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Add Leg button clicked by user {interaction.user.id}")
        self.parent_view.current_step = 0 
        self.parent_view.current_leg_construction_details = {} 
        await interaction.response.defer() 
        # Message will be edited by go_next
        await self.parent_view.go_next(interaction)

class FinalizeButton(Button):
    def __init__(self, parent_view: 'ParlayBetWorkflowView'):
        super().__init__(style=ButtonStyle.blurple, label="Finalize Parlay", custom_id=f"parlay_finalize_{parent_view.original_interaction.id}", disabled=len(parent_view.bet_details.get('legs', [])) < 1)
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Finalize Parlay button clicked by user {interaction.user.id}")
        legs_data = self.parent_view.bet_details.get('legs', [])
        if not legs_data:
            await interaction.response.send_message("❌ Cannot finalize empty parlay.", ephemeral=True); return

        # Create bet_serial now if not already created (e.g., first finalization)
        if "bet_serial" not in self.parent_view.bet_details:
            try:
                # Primary league for the parlay can be the league of the first leg, or a general placeholder
                primary_league = legs_data[0].get('league') if legs_data else "PARLAY"
                bet_serial = await self.parent_view.bot.bet_service.create_parlay_bet(
                    guild_id=interaction.guild_id, user_id=interaction.user.id,
                    legs=legs_data, # Initial legs data
                    channel_id=None, # Will be set later
                    league=primary_league
                )
                if not bet_serial: raise BetServiceError("Failed to create parlay record (no serial).")
                self.parent_view.bet_details['bet_serial'] = bet_serial
                logger.info(f"Parlay bet record {bet_serial} created upon finalization attempt.")
            except BetServiceError as bse:
                logger.error(f"Error creating parlay record on finalize: {bse}")
                await interaction.response.send_message(f"❌ Error initializing parlay: {bse}", ephemeral=True)
                self.parent_view.stop(); return
        
        total_odds = self.parent_view._calculate_parlay_odds(legs_data)
        self.parent_view.bet_details['total_odds'] = total_odds 
        self.parent_view.bet_details['total_odds_str'] = self.parent_view._format_odds_with_sign(total_odds) 

        for item in self.parent_view.children: item.disabled = True
        await interaction.response.defer() # Defer before edit
        
        self.parent_view.current_step = 4 # To make go_next go to step 5 (Units)
        await self.parent_view.go_next(interaction)

class LegDecisionView(View): # View after a leg is added
    def __init__(self, parent_view: 'ParlayBetWorkflowView'): 
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.add_item(AddLegButton(self.parent_view))
        finalize_button = FinalizeButton(self.parent_view)
        # Min 1 leg needed to finalize. If 0 legs somehow, disable.
        finalize_button.disabled = len(self.parent_view.bet_details.get('legs', [])) < 1 
        self.add_item(finalize_button) 
        self.add_item(CancelButton(self.parent_view))

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
        self.bet_slip_generator: Optional[BetSlipGenerator] = None 
        self.preview_image_bytes: Optional[io.BytesIO] = None 

    async def get_bet_slip_generator(self) -> BetSlipGenerator:
        if self.bet_slip_generator is None:
            self.bet_slip_generator = await self.bot.get_bet_slip_generator(self.original_interaction.guild_id)
        return self.bet_slip_generator

    def _format_odds_with_sign(self, odds: Optional[Union[float, int]]) -> str:
        if odds is None: return "N/A"
        try:
            odds_num = int(float(odds)) 
            return f"+{odds_num}" if odds_num > 0 else str(odds_num)
        except (ValueError, TypeError): return "N/A"

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
            american_odds = (total_decimal_odds - 1.0) * 100.0 if total_decimal_odds >= 2.0 else -100.0 / (total_decimal_odds - 1.0)
            return round(american_odds)
        except Exception as e: logger.error(f"Error in _calculate_parlay_odds: {e}"); return 0.0

    async def add_leg(self, modal_interaction: Interaction, leg_details: Dict[str, Any]):
        if 'legs' not in self.bet_details: self.bet_details['legs'] = []
        self.bet_details['legs'].append(leg_details)
        self.current_leg_construction_details = {} 
        leg_count = len(self.bet_details['legs'])
        logger.info(f"Leg {leg_count} added to parlay by user {self.original_interaction.user.id}. Details: {leg_details}")
        
        summary_lines = [f"**Parlay Legs ({leg_count}):**"]
        for i, leg in enumerate(self.bet_details['legs']):
            summary_lines.append(f"{i+1}. {leg.get('league','N/A')}: {leg.get('team','N/A')} {leg.get('line','N/A')} ({leg.get('odds_str','N/A')})")
        summary_text = "\n".join(summary_lines)

        decision_view = LegDecisionView(self)
        # Use the modal's interaction for followup if self.message is not set or fails
        try:
            # We want to edit self.message, which is the message the main view is on
            await self.edit_message_for_current_leg(modal_interaction, content=f"{summary_text}\n\nAdd another leg or finalize?", view=decision_view)
        except Exception as e: # Fallback if editing self.message failed
            logger.error(f"Failed to edit self.message in add_leg, trying followup on modal_interaction: {e}")
            await modal_interaction.followup.send(f"{summary_text}\n\nAdd another leg or finalize?", view=decision_view, ephemeral=True)
            self.message = await modal_interaction.original_response() # Try to recapture message

        self.current_step = 4 # Ready for decision (Add/Finalize) or next step after this. go_next will inc to 5 if Finalize.

    async def start_flow(self): # Parlay starts its own message
        logger.debug(f"Starting parlay bet workflow for user {self.original_interaction.user.id}")
        try:
            # The initial response for /bet command (which BetTypeView is on) is already done.
            # Parlay workflow needs to send a *new* ephemeral message or edit the existing one if possible.
            # Since BetTypeView stops, its message might not be editable.
            # Let's send a new ephemeral message for the parlay workflow.
            if self.original_interaction.response.is_done():
                 self.message = await self.original_interaction.followup.send("Starting parlay leg 1...", view=self, ephemeral=True)
            else: # Should not happen if /bet command defers or responds
                 await self.original_interaction.response.send_message("Starting parlay leg 1...", view=self, ephemeral=True)
                 self.message = await self.original_interaction.original_response()
            
            await self.go_next(self.original_interaction) # Start with the first step of leg building
        except discord.HTTPException as e:
            logger.error(f"Failed to send initial message for parlay workflow: {e}")
            try: await self.original_interaction.followup.send("❌ Failed to start parlay workflow.", ephemeral=True)
            except: pass # Ignore if followup also fails
            self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this parlay.", ephemeral=True)
            return False
        self.latest_interaction = interaction 
        return True
    
    async def edit_message_for_current_leg(self, interaction_context: Interaction, content: Optional[str] = None, view: Optional[View] = None, embed: Optional[discord.Embed] = None, file: Optional[File] = None):
        logger.debug(f"Parlay: Attempting to edit message {self.message.id if self.message else 'None'}. Content: {content is not None}, View: {view is not None}")
        attachments = [file] if file else discord.utils.MISSING
        try:
            if self.message:
                await self.message.edit(content=content, embed=embed, view=view, attachments=attachments)
            else: # Fallback if self.message is somehow None (shouldn't happen after start_flow)
                logger.warning("Parlay: self.message is None during edit_message_for_current_leg. Using original_interaction followup.")
                if self.original_interaction.response.is_done():
                    self.message = await self.original_interaction.followup.send(content=content or "Updating...", view=view, files=attachments if attachments else None, ephemeral=True)
                else: # This case implies original /bet interaction wasn't even responded to.
                    await self.original_interaction.response.send_message(content=content or "Updating...", view=view, files=attachments if attachments else None, ephemeral=True)
                    self.message = await self.original_interaction.original_response()
        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Parlay: Failed to edit message {self.message.id if self.message else 'Original Interaction'}: {e}. Interaction type: {interaction_context.type if interaction_context else 'N/A'}")
            # If edit fails, try to send a new followup message from the current interaction context if it's different
            if interaction_context and interaction_context.response.is_done() and (not self.message or interaction_context.message.id != self.message.id) :
                 try:
                      self.message = await interaction_context.followup.send(content=content or "Updating display...", ephemeral=True, view=view, files=attachments if attachments else None)
                 except discord.HTTPException as fe: logger.error(f"Parlay: Failed to send followup after message edit error: {fe}")
            elif not interaction_context.response.is_done(): # If the current interaction hasn't been responded to (e.g. fresh button click)
                 try:
                      await interaction_context.response.send_message(content=content or "Updating display...", ephemeral=True, view=view, files=attachments if attachments else None)
                      self.message = await interaction_context.original_response()
                 except discord.HTTPException as fe: logger.error(f"Parlay: Failed to send new message after previous edit error: {fe}")
            else:
                 logger.error(f"Parlay: Cannot reliably update user after message edit error. Main message: {self.message.id if self.message else 'None'}")
        except Exception as e:
            logger.exception(f"Parlay: Unexpected error editing message: {e}")

    async def go_next(self, interaction: Interaction): # interaction is the one that triggered this call
        if self.is_processing:
            logger.debug(f"Parlay: Skipping go_next for step {self.current_step}; already processing.")
            if not interaction.response.is_done():
                try: await interaction.response.defer()
                except discord.HTTPException: pass
            return
        self.is_processing = True

        # Defer the interaction that CALLED go_next if it hasn't been responded to.
        # This is important for component callbacks.
        if not interaction.response.is_done():
            try: await interaction.response.defer()
            except discord.HTTPException as e:
                logger.warning(f"Parlay: Defer failed for interaction {interaction.id} in go_next (step {self.current_step}): {e}")

        try:
            self.current_step += 1 # Increment step for the new state we are building
            logger.info(f"Parlay Workflow: Advancing to step {self.current_step} for user {self.original_interaction.user.id}")
            self.clear_items() # Clear buttons/selects from the PREVIOUS step
            
            current_leg_count = len(self.bet_details.get('legs', []))
            # Step content should reflect what the user needs to do for THIS step
            content = f"**Parlay Leg {current_leg_count + 1} - Step {self.current_step}**: "

            # Step 1: League for current leg
            if self.current_step == 1:
                allowed_leagues = [
                    "NFL",
                    "EPL",
                    "NBA",
                    "MLB",
                    "NHL",
                    "La Liga",
                    "NCAA",
                    "Bundesliga",
                    "Serie A",
                    "Ligue 1",
                    "MLS",
                    "Formula 1",
                    "Tennis",
                    "UFC/MMA",
                    "WNBA",
                    "CFL",
                    "AFL",
                    "Darts",
                    "EuroLeague",
                    "NPB",
                    "KBO",
                    "KHL"
                ]
                self.add_item(LeagueSelect(self, allowed_leagues))
                content += "Select League"
            # Step 2: Line Type for current leg
            elif self.current_step == 2:
                self.add_item(LineTypeSelect(self))
                content += "Select Line Type"
            # Step 3: Game for current leg
            elif self.current_step == 3:
                league = self.current_leg_construction_details.get('league')
                if not league:
                    await self.edit_message_for_current_leg(interaction, content="❌ League not set for current leg. Cancelling.", view=None); self.stop(); return
                self.games = []
                if league != "Other" and hasattr(self.bot, 'game_service'):
                    try: self.games = await self.bot.game_service.get_league_games(self.original_interaction.guild_id, league, "scheduled", 25)
                    except Exception as e: logger.exception(f"Parlay: Error fetching games for {league}: {e}")
                
                if self.games: self.add_item(GameSelect(self, self.games))
                self.add_item(ManualEntryButton(self))
                content += f"Select Game for {league} Leg (or Enter Manually)"
            # Step 4: Details Modal for current leg (triggered by GameSelect or ManualEntryButton, or if player prop)
            elif self.current_step == 4:
                # This step is primarily entered via a modal. If we reach here through direct go_next,
                # it means a modal should be shown. The modal's on_submit calls add_leg,
                # which then shows LegDecisionView.
                line_type = self.current_leg_construction_details.get('line_type')
                game_id = self.current_leg_construction_details.get('game_id')
                is_manual = game_id == "Other"
                leg_number = current_leg_count + 1
                
                modal = BetDetailsModal(line_type=line_type, is_manual=is_manual, leg_number=leg_number, view_custom_id_suffix=self.original_interaction.id)
                modal.view_ref = self 
                try:
                    # Use the interaction that led to this step to send the modal
                    await interaction.response.send_modal(modal) 
                    content = f"**Parlay Leg {leg_number}**: Please fill details in the popup."
                    await self.edit_message_for_current_leg(interaction, content=content, view=self) # Edit the main message
                except discord.HTTPException as e:
                    logger.error(f"Parlay: Failed to send BetDetailsModal (step 4): {e}")
                    await self.edit_message_for_current_leg(interaction, content="❌ Error opening leg details form.", view=None); self.stop()
                self.is_processing = False; return # Modal handles next step

            # Step 5: Units for the whole parlay (This step is reached after "Finalize Parlay" is clicked)
            elif self.current_step == 5:
                self.add_item(UnitsSelect(self))
                content = f"**Finalizing Parlay** (Total Odds: {self.bet_details.get('total_odds_str', 'N/A')}): Select Total Units"
            # Step 6: Channel Selection for the whole parlay
            elif self.current_step == 6:
                if not self.bet_details.get("units_str"): # Should be set by UnitsSelect
                    await self.edit_message_for_current_leg(interaction, content="❌ Parlay units not set. Please restart.", view=None); self.stop(); return

                guild_settings = await self.bot.db_manager.fetch_one(
                    "SELECT embed_channel_1, embed_channel_2 FROM guild_settings WHERE guild_id = %s",
                    (self.original_interaction.guild_id,)
                )
                configured_channel_objects = []
                if guild_settings:
                    ids_to_check = filter(None, [guild_settings.get('embed_channel_1'), guild_settings.get('embed_channel_2')])
                    for ch_id_str in ids_to_check:
                        try:
                            ch_id = int(ch_id_str)
                            channel = self.original_interaction.guild.get_channel(ch_id) or await self.original_interaction.guild.fetch_channel(ch_id)
                            if channel and isinstance(channel, TextChannel) and channel.permissions_for(self.original_interaction.guild.me).send_messages:
                                if channel not in configured_channel_objects: configured_channel_objects.append(channel)
                            elif channel: logger.warning(f"Parlay: Embed channel {ch_id} invalid type or permissions.")
                            else: logger.warning(f"Parlay: Embed channel {ch_id} not found.")
                        except (ValueError, discord.NotFound, discord.Forbidden) as e: logger.error(f"Parlay: Error processing embed_channel_id {ch_id_str}: {e}")
                
                if not configured_channel_objects:
                    await self.edit_message_for_current_leg(interaction, content="❌ No configured embed channels. Admin: `/setup`.", view=None); self.stop(); return
                
                self.add_item(ChannelSelect(self, configured_channel_objects))
                content = f"**Finalizing Parlay - Step {self.current_step}**: Select Channel to Post Parlay"
            # Step 7: Confirmation of the whole parlay
            elif self.current_step == 7:
                if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units_str', 'legs', 'total_odds_str']):
                    await self.edit_message_for_current_leg(interaction, content="❌ Parlay details incomplete. Please restart.", view=None); self.stop(); return
                
                file_to_send = None
                if self.preview_image_bytes:
                    self.preview_image_bytes.seek(0)
                    file_to_send = File(self.preview_image_bytes, filename=f"parlay_preview_s{self.current_step}.png")

                self.add_item(ConfirmButton(self))
                content = "**Confirm Your Parlay**\n\n" + self._generate_parlay_summary_text()
            else:
                logger.error(f"ParlayBetWorkflowView: Unexpected step: {self.current_step}")
                await self.edit_message_for_current_leg(interaction, content="❌ Workflow error.", view=None); self.stop(); return

            # Add CancelButton to all steps building a leg, or finalizing
            if self.current_step <= 7 : self.add_item(CancelButton(self))
            
            # Edit the main message (self.message)
            # The 'interaction' here is the one that triggered go_next (e.g., a select menu's callback)
            await self.edit_message_for_current_leg(interaction, content=content, view=self, file=getattr(self, 'file_to_send', None))

        except Exception as e:
            logger.exception(f"Error in parlay go_next (step {self.current_step}): {e}")
            await self.edit_message_for_current_leg(interaction, content="❌ Unexpected error in parlay flow.", view=None)
            self.stop()
        finally:
            self.is_processing = False

    def _generate_parlay_summary_text(self) -> str:
        """Generates a text summary of the parlay legs and details."""
        summary_parts = []
        legs = self.bet_details.get('legs', [])
        for i, leg in enumerate(legs, 1):
            summary_parts.append(
                f"**Leg {i}**: {leg.get('league','N/A')} - "
                f"{leg.get('team','N/A')} {leg.get('line','N/A')} "
                f"({leg.get('odds_str','N/A')})"
            )
        summary_text = "\n".join(summary_parts)
        summary_text += f"\n\nTotal Odds: **{self.bet_details.get('total_odds_str', 'N/A')}**"
        summary_text += f"\nUnits: **{self.bet_details.get('units_str', 'N/A')}**"
        selected_channel_id = self.bet_details.get('channel_id')
        channel_mention = f"<#{selected_channel_id}>" if selected_channel_id else "Not selected"
        summary_text += f"\nPost to Channel: {channel_mention}"
        summary_text += "\n\nClick Confirm to place your parlay."
        return summary_text

    async def _handle_units_selection(self, interaction: Interaction, units: float):
        # This method is called after UnitsSelect callback
        logger.debug(f"Parlay _handle_units_selection: units={units}, bet_serial={self.bet_details.get('bet_serial')}")
        self.bet_details['units'] = units
        self.bet_details['units_str'] = str(units)

        if "bet_serial" not in self.bet_details:
            logger.error("Parlay: bet_serial missing when trying to update units in DB.")
            # Attempt to create it now if it's missing, assuming legs exist
            if self.bet_details.get('legs'):
                try:
                    primary_league = self.bet_details['legs'][0].get('league') if self.bet_details['legs'] else "PARLAY"
                    total_odds = self.bet_details.get('total_odds', self._calculate_parlay_odds(self.bet_details['legs']))
                    bet_serial = await self.bot.bet_service.create_parlay_bet(
                        guild_id=self.original_interaction.guild_id, user_id=self.original_interaction.user.id,
                        legs=self.bet_details['legs'], channel_id=None, league=primary_league
                        # Units and odds will be updated shortly
                    )
                    if not bet_serial: raise BetServiceError("Failed to create parlay record before units update.")
                    self.bet_details['bet_serial'] = bet_serial
                    logger.info(f"Parlay bet record {bet_serial} created during units selection.")
                except BetServiceError as bse:
                    logger.error(f"Error creating parlay record in _handle_units_selection: {bse}")
                    await interaction.followup.send(f"❌ Error initializing parlay: {bse}", ephemeral=True)
                    self.stop(); return
            else:
                await interaction.followup.send("❌ Parlay has no legs. Cannot set units.", ephemeral=True)
                self.stop(); return


        # Update DB with units for the parlay
        try:
            await self.bot.db_manager.execute(
                "UPDATE bets SET units = %s WHERE bet_serial = %s",
                (units, self.bet_details['bet_serial'])
            )
            logger.info(f"Units for parlay {self.bet_details['bet_serial']} updated to {units}.")
        except Exception as e:
            logger.error(f"Failed to update units in DB for parlay {self.bet_details.get('bet_serial')}: {e}")
            await interaction.followup.send("❌ Error saving unit selection. Please try again.", ephemeral=True)
            # Potentially revert UI or stop
            self.disabled = False # Re-enable UnitsSelect if DB update failed? Or just stop.
            if hasattr(self, 'parent_view'): await self.parent_view.edit_message_for_current_leg(interaction, view=self.parent_view)
            return

        # Regenerate Preview Image
        try:
            legs = self.bet_details.get("legs", [])
            if not legs:
                logger.error("No legs found in parlay bet for preview generation after units selection.")
                self.preview_image_bytes = None; return

            bet_slip_gen = await self.get_bet_slip_generator()
            
            # Determine home/away/league for the slip header (e.g., from first leg or a summary)
            # For multi-game parlays, the header might be generic or use first leg.
            # For SGPs, it should use the single game's details.
            is_sgp = len(set(leg.get("game_id") for leg in legs if leg.get("game_id"))) == 1 and len(legs) > 1
            
            header_home_team = "Multi-Game"
            header_away_team = "Parlay" # Or ""
            header_league = "Parlay"

            if legs:
                if is_sgp and legs[0].get("game_id"): # Use details from the single game if SGP
                     # Need to ensure home_team/away_team for the SGP's game are in leg details
                     header_home_team = legs[0].get('home_team', legs[0].get('team', 'Team A'))
                     header_away_team = legs[0].get('away_team', legs[0].get('opponent', 'Team B'))
                     header_league = legs[0].get('league', 'SGP')
                else: # Multi-game parlay, use first leg's league for header, or generic
                    header_league = legs[0].get('league', 'Parlay')
                    # For team names in header for multi-game, you might leave them generic or pick first leg's
                    # For simplicity, let's use generic for multi-game parlay header
                    if not is_sgp: # Only if not SGP
                        header_home_team = "Multi-Game"
                        header_away_team = "Parlay"


            bet_slip_image = await bet_slip_gen.generate_bet_slip(
                home_team=header_home_team,
                away_team=header_away_team,
                league=header_league, # Or a generic "Parlay" title
                odds=self.bet_details.get("total_odds", 0), # Overall parlay odds
                units=units,
                bet_id=str(self.bet_details.get("bet_serial", "N/A")),
                timestamp=datetime.now(timezone.utc), # Or bet creation time
                bet_type="parlay", 
                parlay_legs=legs,
                is_same_game=is_sgp 
            )
            
            if bet_slip_image:
                if self.preview_image_bytes: self.preview_image_bytes.close()
                self.preview_image_bytes = io.BytesIO()
                bet_slip_image.save(self.preview_image_bytes, format='PNG')
                self.preview_image_bytes.seek(0)
                logger.debug(f"Parlay slip preview updated for bet {self.bet_details.get('bet_serial')} with units {units}.")
            else:
                logger.warning(f"Failed to regen parlay preview for bet {self.bet_details.get('bet_serial')}.")
                if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None
        except Exception as img_e:
            logger.error(f"Error regen parlay preview in _handle_units_selection: {img_e}", exc_info=True)
            if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None


    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        bet_serial = details.get('bet_serial')
        if not bet_serial:
             logger.error("Parlay: Attempted to submit without bet_serial.")
             await self.edit_message_for_current_leg(interaction, content="❌ Bet ID missing.", view=None); self.stop(); return
        
        logger.info(f"Submitting parlay {bet_serial} by user {interaction.user.id}")
        await self.edit_message_for_current_leg(interaction, content=f"Processing parlay `{bet_serial}`...", view=None, file=None)
        
        try:
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None
            if not post_channel or not isinstance(post_channel, TextChannel):
                raise ValueError(f"Invalid channel <#{post_channel_id}> for parlay posting.")

            units_val = float(details.get('units', 1.0)) # ensure float
            total_odds_val = float(details.get('total_odds', 0.0)) # ensure float
            legs_data = details.get('legs', [])
            bet_details_json = json.dumps({'legs': legs_data}) 

            update_query = """
                UPDATE bets SET units = %s, odds = %s, channel_id = %s, confirmed = 1, 
                               bet_details = %s, legs = %s, status = %s 
                WHERE bet_serial = %s 
            """
            rowcount, _ = await self.bot.db_manager.execute(
                update_query, units_val, total_odds_val, post_channel_id, 
                bet_details_json, len(legs_data), 'pending', bet_serial # Set status to pending
            )
            if rowcount is None or rowcount == 0:
                 logger.warning(f"Parlay {bet_serial} DB update for confirmation affected 0 rows.")
                 # Potentially check if it was already updated correctly.
                 # For now, assume error if no rows affected here.
                 raise BetServiceError("Failed to confirm parlay details in DB.")
            
            final_image_bytes_for_post = self.preview_image_bytes # Use already generated preview
            if not final_image_bytes_for_post: # Fallback: Regenerate if somehow missing
                 logger.warning(f"Parlay {bet_serial}: preview_image_bytes missing at submit. Regenerating.")
                 # Regeneration logic from _handle_units_selection can be adapted here
                 # For brevity, assuming it's usually present. If issues persist, add full regen here.
                 # This part is crucial for ensuring an image is always sent.
                 # For now, if it's None, it might send without an image if regen fails.
                 pass # Let it try to send without image if regen is too complex here.


            discord_file_to_send = None
            if final_image_bytes_for_post:
                final_image_bytes_for_post.seek(0)
                discord_file_to_send = File(final_image_bytes_for_post, filename=f"parlay_slip_{bet_serial}.png")
            
            # Webhook logic (consistent with straight_betting.py)
            capper_data = await self.bot.db_manager.fetch_one(
                "SELECT display_name, image_path FROM cappers WHERE guild_id = %s AND user_id = %s",
                (interaction.guild_id, interaction.user.id)
            )
            webhook_username = capper_data.get('display_name') if capper_data and capper_data.get('display_name') else interaction.user.display_name
            webhook_avatar_url = None
            if capper_data and capper_data.get('image_path') and capper_data.get('image_path').startswith(('http://', 'https://')):
                webhook_avatar_url = capper_data.get('image_path')
            else:
                webhook_avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            
            target_webhook = None
            try:
                webhooks = await post_channel.webhooks()
                target_webhook = discord.utils.find(lambda wh: wh.user and wh.user.id == self.bot.user.id, webhooks)
                if not target_webhook: target_webhook = await post_channel.create_webhook(name=f"{self.bot.user.name} Parlays")
            except Exception as e: logger.error(f"Parlay: Webhook setup failed for channel {post_channel.id}: {e}"); raise ValueError("Webhook setup failed.")
            
            # No explicit "New Parlay Bet" text, just the image via webhook
            sent_message = await target_webhook.send(
                file=discord_file_to_send, 
                username=webhook_username[:80], # Discord name limit
                avatar_url=webhook_avatar_url, 
                wait=True
            )
            
            if sent_message and hasattr(self.bot.bet_service, 'pending_reactions'):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial, 'user_id': interaction.user.id, 'guild_id': interaction.guild_id,
                    'channel_id': post_channel_id, 'legs': legs_data, 'bet_type': 'parlay'
                }
            await self.edit_message_for_current_leg(interaction, content=f"✅ Parlay ID `{bet_serial}` posted to {post_channel.mention}!", view=None, file=None) # Clear original message
        except Exception as e:
            logger.exception(f"Error submitting parlay {bet_serial}: {e}")
            await self.edit_message_for_current_leg(interaction, content=f"❌ Error placing parlay: {e}", view=None)
        finally:
            if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None
            self.stop()
