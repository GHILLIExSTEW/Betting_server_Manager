# betting-bot/commands/parlay_betting.py

"""Parlay betting workflow for placing multi-leg bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel, File, Embed
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union, Any # Added Any
from datetime import datetime, timezone
import io
import uuid # For temporary bet ID for preview if needed
import os
import json # For bet_details in DB

# Use relative imports
try:
    from ..utils.errors import BetServiceError, ValidationError, GameNotFoundError # Adjusted path
    from ..utils.image_generator import BetSlipGenerator # Adjusted path
    from discord.ext import commands # For Cog base class if this were a Cog
except ImportError:
    # Fallback for running script directly or different structure
    from utils.errors import BetServiceError, ValidationError, GameNotFoundError
    from utils.image_generator import BetSlipGenerator
    from discord.ext import commands


logger = logging.getLogger(__name__)

# --- UI Component Classes ---
class LeagueSelect(Select):
    def __init__(self, parent_view, leagues: List[str]):
        self.parent_view = parent_view
        options = [SelectOption(label=league, value=league) for league in leagues[:24]]
        options.append(SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select League...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        # For parlay, league is per-leg, store it temporarily before adding to a leg
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
        super().__init__(placeholder="Select Line Type...", options=options, min_values=1, max_values=1)

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
            start_dt = game.get('start_time')
            time_str = start_dt.strftime('%m/%d %H:%M %Z') if isinstance(start_dt, datetime) else 'Time N/A'
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id') 
            if game_api_id is None:
                logger.warning(f"Game missing 'id': {game}")
                continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id)))
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(placeholder="Select Game (or Other)...", options=options, min_values=1, max_values=1)

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

class HomePlayerSelect(Select):
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
        logger.debug(f"Home player selected for current leg: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        if self.parent_view.current_leg_construction_details.get('player'):
            await self.parent_view.go_next(interaction)

class AwayPlayerSelect(Select):
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
        logger.debug(f"Away player selected for current leg: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        if self.parent_view.current_leg_construction_details.get('player'):
            await self.parent_view.go_next(interaction)

class ManualEntryButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Manual Entry",
            custom_id=f"parlay_manual_entry_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Manual Entry button clicked by user {interaction.user.id} for parlay leg.")
        self.parent_view.current_leg_construction_details['game_id'] = "Other" 
        self.disabled = True
        for item in self.parent_view.children:
            if isinstance(item, CancelButton): # Or other buttons in this step
                item.disabled = True
        
        line_type = self.parent_view.current_leg_construction_details.get('line_type', 'game_line')
        leg_number = len(self.parent_view.bet_details.get('legs', [])) + 1
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True, leg_number=leg_number)
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully for parlay leg.")
            # The interaction for the button has been responded to by sending the modal.
            # We might want to edit the original message that had the button.
            await self.parent_view.edit_message_for_current_leg(
                interaction, # Use the button's interaction if possible
                content="Manual entry form opened for leg. Please fill in the details.",
                view=self.parent_view # Keep the (disabled) view for context
            )
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal for parlay leg: {e}")
            try:
                await self.parent_view.edit_message_for_current_leg(
                    interaction,
                    content="❌ Failed to open manual entry form. Please restart the parlay.",
                    view=None
                )
            except discord.HTTPException as e2:
                logger.error(f"Failed to edit message after modal error: {e2}")
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
                     await interaction.response.edit_message(
                         content=f"Parlay `{bet_serial}` cancelled and records deleted.",
                         view=None 
                     )
                else:
                     logger.error("BetService not found on bot instance during parlay cancellation.")
                     await interaction.response.edit_message(content="Cancellation failed (Internal Error).", view=None)
            except Exception as e:
                logger.error(f"Failed to delete parlay bet {bet_serial}: {e}")
                await interaction.response.edit_message(
                    content=f"Parlay `{bet_serial}` cancellation failed. Please contact admin.",
                    view=None
                )
        else:
             await interaction.response.edit_message(content="Parlay workflow cancelled.", view=None)
        self.parent_view.stop()

class BetDetailsModal(Modal):
    def __init__(self, line_type: str, is_manual: bool = False, leg_number: int = 1):
        title = f"Leg {leg_number}: Enter Bet Details"
        super().__init__(title=title[:45]) 
        self.line_type = line_type
        self.is_manual = is_manual
        self.leg_number = leg_number

        self.team = TextInput(label="Team Involved", required=True, max_length=100, placeholder="Enter team name")
        self.add_item(self.team)
        
        if self.is_manual: # Only add opponent if manual, game select provides it otherwise
             self.opponent = TextInput(label="Opponent", required=True, max_length=100, placeholder="Enter opponent name")
             self.add_item(self.opponent)

        if line_type == "player_prop":
            self.player_line = TextInput(label="Player - Line", required=True, max_length=100, placeholder="E.g., LeBron James - Points Over 25.5")
            self.add_item(self.player_line)
        else: 
            self.line = TextInput(label="Line", required=True, max_length=100, placeholder="E.g., Moneyline, Spread -7.5, Total Over 6.5")
            self.add_item(self.line)

        self.odds = TextInput(label="Leg Odds", required=True, max_length=10, placeholder="American odds (e.g., -110, +200)")
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"Parlay BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual}, leg_number={self.leg_number} by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True, thinking=True) 

        try:
            team_value = self.team.value.strip()
            opponent_value = self.opponent.value.strip() if hasattr(self, 'opponent') else self.view.current_leg_construction_details.get('away_team_name', 'N/A')
            
            line_value = self.player_line.value.strip() if self.line_type == "player_prop" else self.line.value.strip()
            odds_str_value = self.odds.value.strip()

            if not team_value or (self.is_manual and not opponent_value) or not line_value or not odds_str_value:
                await interaction.followup.send("❌ All fields are required. Please fill them all.", ephemeral=True)
                return

            try:
                odds_val_str = odds_str_value.replace('+', '')
                if not odds_val_str: raise ValueError("Odds cannot be empty.")
                odds_float = float(odds_val_str)
                if -100 < odds_float < 100 and odds_float != 0:
                     raise ValueError("Odds cannot be between -99 and +99 (excluding 0).")
            except ValueError as ve:
                logger.warning(f"Invalid odds entered for parlay leg: {odds_str_value} - Error: {ve}")
                await interaction.followup.send(f"❌ Invalid odds format: '{odds_str_value}'. {ve}", ephemeral=True)
                return

            # If game was selected, ensure team/opponent match or use selected game data
            if not self.is_manual:
                if 'home_team_name' in self.view.current_leg_construction_details and team_value.lower() != self.view.current_leg_construction_details['home_team_name'].lower():
                    logger.warning(f"Team entered '{team_value}' differs from selected game '{self.view.current_leg_construction_details['home_team_name']}'. Using selected game's team.")
                    team_value = self.view.current_leg_construction_details['home_team_name']
                if 'away_team_name' in self.view.current_leg_construction_details:
                    opponent_value = self.view.current_leg_construction_details['away_team_name']


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
            # The add_leg method in the parent view will now handle the next step and message update

        except Exception as e:
            logger.exception(f"Error in Parlay BetDetailsModal on_submit: {e}")
            await interaction.followup.send("❌ Failed to process leg details. Please try again.", ephemeral=True)
            if hasattr(self, 'view') and self.view: self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in Parlay BetDetailsModal: {error}", exc_info=True)
         try:
            if not interaction.response.is_done():
                 await interaction.response.send_message('❌ An error occurred with the bet details modal.', ephemeral=True)
            else:
                 await interaction.followup.send('❌ An error occurred with the bet details modal.', ephemeral=True)
         except discord.HTTPException:
             logger.warning("Could not send error followup for Parlay BetDetailsModal.")
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
        self.parent_view.current_step = 0  
        self.parent_view.current_leg_construction_details = {} # Reset for new leg
        # Keep existing 'legs' and 'bet_serial'

        # Edit message before calling go_next, as go_next will then edit it again for the new step
        await interaction.response.edit_message(content="Starting next leg...", view=None) 
        await self.parent_view.go_next(interaction)

class FinalizeButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.blurple,
            label="Finalize Parlay",
            custom_id=f"parlay_finalize_{parent_view.original_interaction.id}",
            disabled=len(parent_view.bet_details.get('legs', [])) < 2 # Min 2 legs for a parlay
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Finalize Parlay button clicked by user {interaction.user.id}")
        
        total_odds = self.parent_view._calculate_parlay_odds(self.parent_view.bet_details.get('legs', []))
        self.parent_view.bet_details['total_odds'] = total_odds 
        self.parent_view.bet_details['total_odds_str'] = self.parent_view._format_odds_with_sign(total_odds) 

        for item in self.parent_view.children: # Disable buttons on current view
            if isinstance(item, Button): item.disabled = True
        
        # Defer the interaction before editing the message and proceeding
        await interaction.response.defer()
        await self.parent_view.edit_message_for_current_leg(
            interaction, 
            content="Finalizing parlay... Calculated Total Odds: " + self.parent_view.bet_details['total_odds_str'], 
            view=self.parent_view
        )
        
        self.parent_view.current_step = 5 # Advance to Units selection step
        await self.parent_view.go_next(interaction)


class LegDecisionView(View):
    def __init__(self, parent_view: 'ParlayBetWorkflowView'): # Forward reference
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.add_item(AddLegButton(self.parent_view))
        self.add_item(FinalizeButton(self)) 
        self.add_item(CancelButton(self.parent_view))

class ChannelSelect(Select):
    def __init__(self, parent_view, channels: List[TextChannel]):
        self.parent_view = parent_view
        options = [SelectOption(label=f"#{channel.name}", value=str(channel.id)) for channel in channels[:25]]
        if not options:
            options.append(SelectOption(label="No Writable Channels Found", value="none", emoji="❌"))
        super().__init__(
            placeholder="Select Channel to Post Parlay...",
            options=options,
            min_values=1,
            max_values=1,
            disabled=not options or options[0].value == "none"
        )

    async def callback(self, interaction: Interaction):
        selected_value = self.values[0]
        if selected_value == "none":
            await interaction.response.defer()
            return
        self.parent_view.bet_details['channel_id'] = int(selected_value)
        logger.debug(f"Channel selected for parlay: {selected_value} by user {interaction.user.id}")
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
        super().__init__(timeout=1800) # Increased timeout for multi-leg
        self.original_interaction = interaction
        self.bot = bot 
        self.current_step = 0
        self.bet_details: Dict[str, Any] = {'legs': [], 'bet_type': 'parlay'}
        self.current_leg_construction_details: Dict[str, Any] = {} # For building current leg
        self.games: List[Dict] = [] 
        self.message: Optional[Union[discord.WebhookMessage, discord.InteractionMessage]] = None 
        self.is_processing = False 
        self.latest_interaction = interaction 
        self.bet_slip_generator = BetSlipGenerator() 
        self.preview_image_bytes: Optional[io.BytesIO] = None 

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
             await interaction.followup.send("❌ Internal error: Leg details were incomplete. Please restart.", ephemeral=True)
             self.stop()
             return
        self.bet_details['legs'].append(leg_details)
        self.current_leg_construction_details = {} # Reset for next potential leg
        leg_count = len(self.bet_details['legs'])
        logger.info(f"Leg {leg_count} added to parlay by user {interaction.user.id}. Details: {leg_details}")
        
        # Update message to show leg decision view
        summary_lines = [f"**Parlay Legs ({leg_count}):**"]
        for i, leg in enumerate(self.bet_details['legs']):
            summary_lines.append(f"{i+1}. {leg['league']}: {leg['line']} ({leg.get('team','N/A')} vs {leg.get('opponent','N/A')}) @ {leg['odds_str']}")
        summary_text = "\n".join(summary_lines)

        decision_view = LegDecisionView(self)
        # Edit the message that the modal was submitted from
        await self.edit_message_for_current_leg(interaction, content=f"{summary_text}\n\nAdd another leg or finalize?", view=decision_view)
        self.current_step = 4 # Mark as leg added, waiting for decision (next step is 5 for finalize flow)


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
        """ Edits the message associated with the latest interaction of the main view. """
        # This is a bit tricky with modals, as the modal interaction is separate.
        # We want to edit the message that the *original buttons/selects* were on.
        log_info = f"Editing main parlay message: content={content is not None}, view={view is not None}"
        logger.debug(log_info)
        attachments = [file] if file else []
        try:
            if self.message: # If we have a stored message object for the view
                await self.message.edit(content=content, embed=embed, view=view, attachments=attachments)
            elif self.latest_interaction: # Fallback to latest interaction if message object not stored
                 await self.latest_interaction.edit_original_response(content=content, embed=embed, view=view, attachments=attachments)
            else: # Fallback to original interaction (might fail if too old)
                 await self.original_interaction.edit_original_response(content=content, embed=embed, view=view, attachments=attachments)

        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Failed to edit main parlay workflow message: {e}. This can happen if the original message was deleted or interaction timed out.")
            # If the original edit fails, try a followup on the interaction that triggered this edit (e.g., modal submit)
            if interaction_to_edit_from and interaction_to_edit_from.response.is_done():
                 try:
                     await interaction_to_edit_from.followup.send(content if content else "Updated.", ephemeral=True, view=view)
                     if view: self.message = await interaction_to_edit_from.original_response() # Try to get new message ref
                 except discord.HTTPException as fe:
                     logger.error(f"Failed to send followup after message edit error: {fe}")
        except Exception as e:
            logger.exception(f"Unexpected error editing main parlay workflow message: {e}")


    async def go_next(self, interaction: Interaction):
        if self.is_processing:
            logger.debug(f"Skipping parlay go_next; already processing step {self.current_step} for user {interaction.user.id}")
            return
        self.is_processing = True
        try:
            # Only increment step if not coming from "Add Leg" which resets step to 0 for go_next to make it 1
            # or if we are not in a state waiting for modal (step 4 for leg details)
            is_add_leg_callback = interaction.data and interaction.data.get('custom_id', '').startswith('parlay_add_leg_')
            if not is_add_leg_callback and self.current_step != 4: # Step 4 is modal input, modal submit handles next
                self.current_step += 1
            elif is_add_leg_callback : # Add leg resets step to 0, so go_next increments it to 1
                self.current_step +=1


            leg_count = len(self.bet_details.get('legs', []))
            step_content = f"**Parlay Leg {leg_count + 1} - Step {self.current_step}**"
            self.clear_items() 

            logger.debug(f"Entering parlay step {self.current_step} for leg {leg_count + 1}")

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
                    await self.edit_message_for_current_leg(interaction, content="❌ No league selected for this leg. Please restart.", view=None)
                    self.stop()
                    return
                self.games = [] 
                if league != "Other" and hasattr(self.bot, 'game_service'):
                    try:
                        logger.debug(f"Fetching scheduled games for parlay leg: {league}, guild: {interaction.guild_id}")
                        self.games = await self.bot.game_service.get_league_games(
                            guild_id=interaction.guild_id, league=league, status='scheduled', limit=25
                        )
                        logger.debug(f"Fetched {len(self.games)} upcoming games for {league} for parlay leg.")
                    except Exception as e:
                        logger.exception(f"Error fetching games for parlay leg (league {league}): {e}")
                if self.games: 
                    self.add_item(GameSelect(self, self.games))
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content += f": Select Game for {league} Leg (or Enter Manually)"
                    await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
                else: 
                    logger.warning(f"No games found for parlay leg (league {league}). Prompting manual entry.")
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content = f"No games found for {league} leg. Enter details manually." if league != "Other" else "Enter game details manually for this leg."
                    await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
            elif self.current_step == 4: # Modal trigger for leg details
                line_type = self.current_leg_construction_details.get('line_type')
                game_id = self.current_leg_construction_details.get('game_id') 
                is_manual = game_id == "Other"
                leg_number = leg_count + 1
                if line_type == "player_prop" and not is_manual and hasattr(self.bot, 'game_service'):
                     home_players, away_players = [], []
                     try:
                         players_data = await self.bot.game_service.get_game_players(game_id)
                         home_players = players_data.get('home_players', [])
                         away_players = players_data.get('away_players', [])
                     except Exception as e: logger.error(f"Failed to fetch players for game {game_id}: {e}")
                     home_team = self.current_leg_construction_details.get('home_team_name', 'Home')
                     away_team = self.current_leg_construction_details.get('away_team_name', 'Away')
                     if home_players or away_players:
                         self.add_item(HomePlayerSelect(self, home_players, home_team))
                         self.add_item(AwayPlayerSelect(self, away_players, away_team))
                         self.add_item(CancelButton(self))
                         step_content += f": Select Player for Leg {leg_number} Prop"
                         await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
                         self.current_step -= 1 
                         self.is_processing = False
                         return 
                modal = BetDetailsModal(line_type=line_type, is_manual=is_manual, leg_number=leg_number)
                modal.view = self
                try:
                    # The interaction here is the one that triggered go_next (e.g., game select)
                    # We need to send modal in response to *that* interaction.
                    await interaction.response.send_modal(modal)
                except discord.HTTPException as e:
                    logger.error(f"Failed to send Parlay BetDetailsModal: {e}")
                    # Try followup on the original interaction if modal send failed
                    await self.original_interaction.followup.send("❌ Failed to open bet details form. Please try again.", ephemeral=True)
                    self.stop()
                self.is_processing = False 
                return 
            # Step 5 is shown by add_leg (LegDecisionView)
            elif self.current_step == 6: # Units Selection (after Finalize clicked)
                self.add_item(UnitsSelect(self))
                self.add_item(CancelButton(self))
                step_content = f"**Finalize Parlay - Step {self.current_step}**: Select Total Units (Overall Odds: {self.bet_details.get('total_odds_str', 'N/A')})"
                await self.edit_message_for_current_leg(interaction, content=step_content, view=self)
            elif self.current_step == 7: # Channel Selection & Preview
                 if 'units_str' not in self.bet_details:
                      await self.edit_message_for_current_leg(interaction, content="❌ Units not set. Please restart.", view=None); self.stop(); return
                 if 'bet_serial' not in self.bet_details:
                      await self.edit_message_for_current_leg(interaction, content="❌ Bet not created. Please restart.", view=None); self.stop(); return
                 try:
                     bet_serial = self.bet_details['bet_serial']
                     legs = self.bet_details.get('legs', [])
                     if not legs: raise ValueError("No legs for parlay preview.")
                     league = legs[0].get('league', 'UNKNOWN_LEAGUE') # Primary league for header
                     game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
                     is_same_game = len(game_ids) == 1 and len(legs) > 1 # SGP if one game_id and multiple legs
                     
                     bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                         home_team=legs[0].get('team', 'N/A'), away_team=legs[0].get('opponent', 'N/A'), 
                         league=league, line="Parlay", odds=self.bet_details.get('total_odds', 0.0), 
                         units=float(self.bet_details.get('units_str', 1.0)), bet_id=str(bet_serial), 
                         timestamp=datetime.now(timezone.utc), bet_type="parlay", parlay_legs=legs, is_same_game=is_same_game
                     )
                     self.preview_image_bytes = io.BytesIO()
                     bet_slip_image.save(self.preview_image_bytes, format='PNG')
                     self.preview_image_bytes.seek(0)
                     file_to_send = File(self.preview_image_bytes, filename="parlay_preview.png")
                     self.preview_image_bytes.seek(0) 
                 except Exception as e:
                     logger.exception(f"Failed to generate parlay slip image at step 7: {e}")
                     await self.edit_message_for_current_leg(interaction, content="❌ Failed to generate parlay preview.", view=None); self.stop(); return
                 channels = [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.guild.me).send_messages] if interaction.guild else []
                 if not channels:
                     await self.edit_message_for_current_leg(interaction, content="❌ No writable channels.", view=None); self.stop(); return
                 self.add_item(ChannelSelect(self, channels))
                 self.add_item(CancelButton(self))
                 step_content = f"**Finalize Parlay - Step {self.current_step}**: Review & Select Channel"
                 await self.edit_message_for_current_leg(interaction, content=step_content, view=self, file=file_to_send)
            elif self.current_step == 8: # Confirmation
                 if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units_str', 'total_odds_str', 'legs']):
                     await self.edit_message_for_current_leg(interaction, content="❌ Details incomplete.", view=None); self.stop(); return
                 file_to_send = File(self.preview_image_bytes, filename="parlay_confirm.png") if self.preview_image_bytes else None
                 if file_to_send: self.preview_image_bytes.seek(0)
                 self.add_item(ConfirmButton(self))
                 self.add_item(CancelButton(self))
                 step_content = "**Finalize Parlay - Step {self.current_step}**: Confirm Details"
                 channel_mention = f"<#{self.bet_details['channel_id']}>"
                 leg_summary = "\n".join([f"- {leg['line']} ({leg.get('team','N/A')} vs {leg.get('opponent','N/A')}) @ {leg['odds_str']}" for leg in self.bet_details['legs']])
                 confirmation_text = (f"{step_content}\n\n**Legs ({len(self.bet_details['legs'])}):**\n{leg_summary}\n"
                                      f"**Total Odds:** {self.bet_details['total_odds_str']}\n"
                                      f"**Stake:** {self.bet_details['units_str']} Units\n"
                                      f"**Post to:** {channel_mention}\n\nConfirm to post.")
                 await self.edit_message_for_current_leg(interaction, content=confirmation_text, view=self, file=file_to_send)
            else: 
                logger.error(f"ParlayBetWorkflowView reached unexpected step: {self.current_step}")
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
            bet_details_json = json.dumps({'legs': details.get('legs', [])}) # Ensure legs are in JSON

            update_query = """
                UPDATE bets SET units = %s, odds = %s, channel_id = %s, confirmed = 1, bet_details = %s, legs = %s
                WHERE bet_serial = %s AND confirmed = 0 
            """ # Added bet_details and legs count to update
            rowcount, _ = await self.bot.db_manager.execute(
                update_query, units, total_odds, post_channel_id, bet_details_json, len(details.get('legs',[])), bet_serial
            )
            if rowcount is None or rowcount == 0:
                 existing = await self.bot.db_manager.fetch_one("SELECT confirmed FROM bets WHERE bet_serial = %s", (bet_serial,))
                 if existing and existing['confirmed'] == 1: logger.warning(f"Parlay {bet_serial} already confirmed.")
                 else: raise BetServiceError("Failed to confirm parlay in DB.")
            
            final_image_bytes = self.preview_image_bytes
            if not final_image_bytes: # Regenerate if lost
                 # Simplified regeneration call, ensure all details are present
                 legs = details.get('legs', [])
                 league = legs[0].get('league', 'UNKNOWN_LEAGUE') if legs else 'UNKNOWN_LEAGUE'
                 game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
                 is_same_game = len(game_ids) == 1 and len(legs) > 1
                 bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                     home_team=legs[0].get('team', 'N/A') if legs else 'N/A', 
                     away_team=legs[0].get('opponent', 'N/A') if legs else 'N/A',
                     league=league, line="Parlay", odds=total_odds, units=units, bet_id=str(bet_serial),
                     timestamp=datetime.now(timezone.utc), bet_type="parlay", parlay_legs=legs, is_same_game=is_same_game
                 )
                 final_image_bytes = io.BytesIO(); bet_slip_image.save(final_image_bytes, format='PNG')
            
            final_image_bytes.seek(0)
            discord_file = File(final_image_bytes, filename=f"parlay_slip_{bet_serial}.png")
            
            # Webhook sending logic (condensed for brevity, ensure it's robust)
            role_mention = ""; display_name = interaction.user.display_name; avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            # (Code to fetch settings, capper info, and webhook would go here, similar to straight_betting)
            webhook = await post_channel.create_webhook(name=f"{self.bot.user.name} Parlays"[:100]) # Simplified
            sent_message = await webhook.send(file=discord_file, username=display_name[:80], avatar_url=avatar_url, wait=True)
            await webhook.delete() # Clean up temporary webhook

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

# async def setup(bot: commands.Bot): # This file is not a Cog itself
#     logger.info("ParlayBetWorkflow components loaded.")
