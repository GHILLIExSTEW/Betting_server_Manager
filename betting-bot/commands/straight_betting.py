# betting-bot/commands/straight_betting.py

"""Straight betting workflow for placing single-leg bets."""

import discord
from discord import ButtonStyle, Interaction, SelectOption, TextChannel, File, Embed
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union, Any
from datetime import datetime, timezone
import io
import os

# Use relative imports
try:
    from ..utils.errors import BetServiceError, ValidationError, GameNotFoundError
    from ..utils.image_generator import BetSlipGenerator
    # SPORT_CATEGORY_MAP from image_generator is not directly needed here if GameService handles league details
    from discord.ext import commands
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
        super().__init__(
            placeholder="Select League...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['league'] = self.values[0]
        logger.debug(f"League selected: {self.values[0]} by user {interaction.user.id}")
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
        super().__init__(
            placeholder="Select Line Type...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['line_type'] = self.values[0]
        logger.debug(f"Line Type selected: {self.values[0]} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class GameSelect(Select):
    def __init__(self, parent_view, games: List[Dict]):
        self.parent_view = parent_view
        options = []
        for game in games[:24]: # Limit to 24 options for discord limits
            home = game.get('home_team_name', 'Unknown Home')
            away = game.get('away_team_name', 'Unknown Away')
            start_dt_obj = game.get('start_time')
            time_str = "Time N/A"

            if isinstance(start_dt_obj, str): # Handle if start_time is string from DB
                try:
                    # Attempt to parse if it's a common ISO format, adjust as needed
                    start_dt_obj = datetime.fromisoformat(start_dt_obj.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Could not parse game start_time string: {start_dt_obj}")
                    start_dt_obj = None # Could not parse
            
            if isinstance(start_dt_obj, datetime):
                 time_str = start_dt_obj.strftime('%m/%d %H:%M %Z')
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id') # Assuming 'id' is the API game ID or DB game ID
            if game_api_id is None:
                logger.warning(f"Game missing 'id': {game}")
                continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id)))
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(
            placeholder="Select Game (or Other)...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        selected_game_id = self.values[0]
        self.parent_view.bet_details['game_id'] = selected_game_id
        if selected_game_id != "Other":
            game = next((g for g in self.parent_view.games if str(g.get('id')) == selected_game_id), None)
            if game:
                self.parent_view.bet_details['home_team_name'] = game.get('home_team_name', 'Unknown')
                self.parent_view.bet_details['away_team_name'] = game.get('away_team_name', 'Unknown')
            else:
                logger.warning(f"Could not find full details for selected game ID {selected_game_id}")
        logger.debug(f"Game selected: {selected_game_id} by user {interaction.user.id}")
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
        super().__init__(
            placeholder=f"{team_name} Players...",
            options=options,
            min_values=0,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.bet_details['player'] = self.values[0].replace("home_", "")
            for item in self.parent_view.children:
                if isinstance(item, AwayPlayerSelect):
                    item.disabled = True
        else:
            if not self.parent_view.bet_details.get('player'):
                 self.parent_view.bet_details['player'] = None
        logger.debug(f"Home player selected: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        if self.parent_view.bet_details.get('player') or all(isinstance(i, Select) and i.disabled for i in self.parent_view.children if isinstance(i, (HomePlayerSelect, AwayPlayerSelect))):
            await self.parent_view.go_next(interaction)


class AwayPlayerSelect(Select):
    def __init__(self, parent_view, players: List[str], team_name: str):
        self.parent_view = parent_view
        self.team_name = team_name
        options = [SelectOption(label=player, value=f"away_{player}") for player in players[:24]]
        if not options:
            options.append(SelectOption(label="No Players Available", value="none", emoji="❌"))
        super().__init__(
            placeholder=f"{team_name} Players...",
            options=options,
            min_values=0,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.bet_details['player'] = self.values[0].replace("away_", "")
            for item in self.parent_view.children:
                if isinstance(item, HomePlayerSelect):
                    item.disabled = True
        else:
             if not self.parent_view.bet_details.get('player'):
                 self.parent_view.bet_details['player'] = None
        logger.debug(f"Away player selected: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        if self.parent_view.bet_details.get('player') or all(isinstance(i, Select) and i.disabled for i in self.parent_view.children if isinstance(i, (HomePlayerSelect, AwayPlayerSelect))):
            await self.parent_view.go_next(interaction)

class ManualEntryButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Manual Entry",
            custom_id=f"straight_manual_entry_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Manual Entry button clicked by user {interaction.user.id}")
        self.parent_view.bet_details['game_id'] = "Other"
        self.disabled = True
        for item in self.parent_view.children:
            if isinstance(item, CancelButton): # Also disable cancel on this view
                item.disabled = True

        line_type = self.parent_view.bet_details.get('line_type', 'game_line')
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True)
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully")
            # The original message (that the button was on) should be updated.
            # The edit_message call will use interaction.edit_original_response() due to send_modal.
            await self.parent_view.edit_message(
                interaction, # Pass the button's interaction
                content="Manual entry form opened. Please fill in the details.",
                view=self.parent_view
            )
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal: {e}")
            try:
                # Attempt to edit the original message via the button's interaction
                await self.parent_view.edit_message(
                    interaction,
                    content="❌ Failed to open manual entry form. Please restart the /bet command.",
                    view=None
                )
            except discord.HTTPException as e2:
                logger.error(f"Failed to edit message after modal error: {e2}")
            self.parent_view.stop()


class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.red,
            label="Cancel",
            custom_id=f"straight_cancel_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Cancel button clicked by user {interaction.user.id}")
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True

        bet_serial = self.parent_view.bet_details.get('bet_serial')
        if bet_serial:
            try:
                if hasattr(self.parent_view.bot, 'bet_service'):
                     await self.parent_view.bot.bet_service.delete_bet(bet_serial)
                     logger.info(f"Bet {bet_serial} cancelled and deleted by user {interaction.user.id}.")
                     await interaction.response.edit_message(
                         content=f"Bet `{bet_serial}` cancelled and records deleted.",
                         view=None
                     )
                else:
                    logger.error("BetService not found on bot instance during cancellation.")
                    await interaction.response.edit_message(
                        content="Cancellation failed (Internal Error).", view=None
                    )
            except Exception as e:
                logger.error(f"Failed to delete bet {bet_serial} during cancellation: {e}")
                await interaction.response.edit_message(
                    content=f"Bet `{bet_serial}` cancellation process failed. Please contact admin if needed.",
                    view=None
                )
        else:
             await interaction.response.edit_message(
                 content="Bet workflow cancelled.",
                 view=None
             )
        self.parent_view.stop()


class BetDetailsModal(Modal):
    def __init__(self, line_type: str, is_manual: bool = False):
        title = "Enter Bet Details"
        super().__init__(title=title)
        self.line_type = line_type
        self.is_manual = is_manual

        self.team = TextInput(
            label="Team Bet On",
            required=True,
            max_length=100,
            placeholder="Enter the team name involved in the bet"
        )
        self.add_item(self.team)

        if self.is_manual:
            self.opponent = TextInput(
                label="Opponent",
                required=True,
                max_length=100,
                placeholder="Enter opponent name"
            )
            self.add_item(self.opponent)

        if line_type == "player_prop":
            self.player_line = TextInput(
                label="Player - Line",
                required=True,
                max_length=100,
                placeholder="E.g., Connor McDavid - Shots Over 3.5"
            )
            self.add_item(self.player_line)
        else:
            self.line = TextInput(
                label="Line",
                required=True,
                max_length=100,
                placeholder="E.g., Moneyline, Spread -7.5, Total Over 6.5"
            )
            self.add_item(self.line)

        self.odds = TextInput(
            label="Odds",
            required=True,
            max_length=10,
            placeholder="Enter American odds (e.g., -110, +200)"
        )
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual} by user {interaction.user.id}")
        # Defer the modal's interaction (typically ephemeral)
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            team = self.team.value.strip()
            opponent = self.opponent.value.strip() if hasattr(self, 'opponent') else self.view.bet_details.get('away_team_name', 'Unknown')
            if self.line_type == "player_prop":
                line = self.player_line.value.strip()
            else:
                line = self.line.value.strip()
            odds_str = self.odds.value.strip()

            if not team or not line or not odds_str:
                await interaction.followup.send("❌ Team, Line, and Odds are required. Please try again.", ephemeral=True)
                return

            try:
                odds_val_str = odds_str.replace('+', '')
                if not odds_val_str: raise ValueError("Odds cannot be empty.")
                odds_val = float(odds_val_str)
                if -100 < odds_val < 100 and odds_val != 0:
                     raise ValueError("Odds cannot be between -99 and +99 (excluding 0).")
            except ValueError as ve:
                logger.warning(f"Invalid odds entered: {odds_str} - Error: {ve}")
                await interaction.followup.send(f"❌ Invalid odds format: '{odds_str}'. Use American odds (e.g., -110, +150). {ve}", ephemeral=True)
                return

            if not self.is_manual and 'away_team_name' in self.view.bet_details:
                 opponent = self.view.bet_details['away_team_name']
                 if 'home_team_name' in self.view.bet_details and team.lower() != self.view.bet_details['home_team_name'].lower():
                     logger.warning(f"Team entered '{team}' differs from selected game home team '{self.view.bet_details['home_team_name']}'. Using game team.")
                     team = self.view.bet_details['home_team_name']

            current_leg_details = {
                'game_id': self.view.bet_details.get('game_id') if self.view.bet_details.get('game_id') != 'Other' else None,
                'bet_type': self.line_type,
                'team': team,
                'opponent': opponent,
                'line': line,
                'odds': odds_val,
                'league': self.view.bet_details.get('league', 'NHL')
            }
            try:
                bet_serial = await self.view.bot.bet_service.create_straight_bet(
                    guild_id=interaction.guild_id,
                    user_id=interaction.user.id,
                    game_id=current_leg_details['game_id'],
                    bet_type=current_leg_details['bet_type'],
                    team=current_leg_details['team'],
                    opponent=current_leg_details['opponent'],
                    line=current_leg_details['line'],
                    units=1.00, # Placeholder, will be updated later
                    odds=current_leg_details['odds'],
                    channel_id=None, # Placeholder
                    league=current_leg_details['league']
                )
                if bet_serial is None or bet_serial == 0:
                     logger.error(f"Bet creation failed for user {interaction.user.id}, received bet_serial: {bet_serial}")
                     await interaction.followup.send("❌ Failed to create bet record in the database. Please try again or contact admin.", ephemeral=True)
                     self.view.stop()
                     return

                self.view.bet_details['bet_serial'] = bet_serial
                self.view.bet_details['line'] = line
                self.view.bet_details['odds_str'] = odds_str
                self.view.bet_details['odds'] = odds_val
                self.view.bet_details['team'] = team
                self.view.bet_details['opponent'] = opponent
                logger.debug(f"Created straight bet with serial {bet_serial} via modal.")
                await self.view._preload_team_logos(team, opponent, current_leg_details['league'])
            except Exception as e:
                logger.exception(f"Failed to create straight bet in DB from modal: {e}")
                await interaction.followup.send("❌ Failed to save bet details. Please try again.", ephemeral=True)
                self.view.stop()
                return
            
            self.view.current_step = 4 # Should align with go_next logic or be handled by go_next
            # Edit the main view message, not the modal's ephemeral response.
            # The 'interaction' here is the modal's interaction.
            # self.view.edit_message will use self.view.message.edit()
            await self.view.edit_message(
                interaction=None, # Pass None to indicate this is not a direct component response for editing self.message
                content="Bet details entered. Processing next step...",
                view=self.view
            )
            # Pass the modal's interaction to go_next if it's needed for context,
            # but go_next should be careful about how it uses this interaction's response.
            await self.view.go_next(interaction) # The modal's interaction is passed here
        except Exception as e:
            logger.exception(f"Error in BetDetailsModal on_submit: {e}")
            await interaction.followup.send("❌ Failed to process bet details. Please try again.", ephemeral=True)
            if hasattr(self, 'view') and self.view: self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
         try:
              if not interaction.response.is_done():
                   await interaction.response.send_message('❌ An error occurred with the bet details modal.', ephemeral=True)
              else:
                   await interaction.followup.send('❌ An error occurred processing the bet details modal.', ephemeral=True)
         except discord.HTTPException:
             logger.warning("Could not send error followup for BetDetailsModal.")
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
        super().__init__(
            placeholder="Select Units for Bet...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['units_str'] = self.values[0]
        logger.debug(f"Units selected: {self.values[0]} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class ChannelSelect(Select):
    def __init__(self, parent_view, channels: List[TextChannel]):
        self.parent_view = parent_view
        options = [SelectOption(label=f"#{channel.name}", value=str(channel.id)) for channel in channels[:25]]
        if not options:
            options.append(SelectOption(label="No Writable Channels Found", value="none", emoji="❌"))
        super().__init__(
            placeholder="Select Channel to Post Bet...",
            options=options,
            min_values=1,
            max_values=1,
            disabled=not options or options[0].value == "none"
        )

    async def callback(self, interaction: Interaction):
        selected_value = self.values[0]
        if selected_value == "none":
            await interaction.response.defer() # Still defer to acknowledge
            return
        self.parent_view.bet_details['channel_id'] = int(selected_value)
        logger.debug(f"Channel selected: {selected_value} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class ConfirmButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Confirm & Post",
            custom_id=f"straight_confirm_bet_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Confirm button clicked by user {interaction.user.id}")
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        # Defer or edit the response to the confirm button itself
        await interaction.response.edit_message(view=self.parent_view) # Disables buttons on the current message
        await self.parent_view.submit_bet(interaction) # submit_bet will then send final messages

# --- Main Workflow View ---
class StraightBetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600)
        self.original_interaction = interaction # The interaction that started the command
        self.bot = bot
        self.current_step = 0
        self.bet_details: Dict[str, Any] = {'bet_type': 'straight'}
        self.games: List[Dict] = []
        self.message: Optional[Union[discord.WebhookMessage, discord.InteractionMessage]] = None
        self.is_processing = False
        self.latest_interaction = interaction # Stores the most recent interaction (component, modal submit)
        self.bet_slip_generator = BetSlipGenerator()
        self.preview_image_bytes: Optional[io.BytesIO] = None
        self.team_logos: Dict[str, Optional[str]] = {}

    async def _preload_team_logos(self, team1: str, team2: str, league: str):
        if not hasattr(self, 'bet_slip_generator'): return
        keys = [f"{team1}_{league}", f"{team2}_{league}"]
        for key in keys:
            if key not in self.team_logos:
                 try:
                      _ = self.bet_slip_generator._load_team_logo(key.split('_')[0], league)
                      self.team_logos[key] = "checked"
                 except Exception as e:
                      logger.error(f"Error preloading logo for {key}: {e}")
                      self.team_logos[key] = None

    async def start_flow(self):
        logger.debug(f"Starting straight bet workflow for user {self.original_interaction.user} (ID: {self.original_interaction.user.id})")
        try:
            # Initial message sending logic
            # If the original command interaction was deferred, we must use followup.
            # Otherwise, we can send a new response.
            if self.original_interaction.response.is_done():
                self.message = await self.original_interaction.followup.send(
                    "Starting straight bet placement...", view=self, ephemeral=True
                )
            else:
                await self.original_interaction.response.send_message(
                    "Starting straight bet placement...", view=self, ephemeral=True
                )
                self.message = await self.original_interaction.original_response()
            
            await self.go_next(self.original_interaction) # Initial step
        except discord.HTTPException as e:
            logger.error(f"Failed to send initial message/start flow for straight workflow: {e}")
            try:
                 # Ensure followup if original_interaction is already responded to
                 if self.original_interaction.response.is_done():
                    await self.original_interaction.followup.send(
                        "❌ Failed to start bet workflow. Please try again.", ephemeral=True
                    )
                 else: # This case should ideally not happen if the above logic is correct
                    await self.original_interaction.response.send_message(
                        "❌ Failed to start bet workflow. Please try again.", ephemeral=True
                    )
            except discord.HTTPException: pass
            self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            logger.debug(f"Unauthorized interaction attempt by {interaction.user} (ID: {interaction.user.id})")
            await interaction.response.send_message(
                "You cannot interact with this bet placement.", ephemeral=True
            )
            return False
        self.latest_interaction = interaction # Update latest interaction
        return True

    async def edit_message(
        self,
        interaction: Optional[Interaction] = None, # The interaction that triggered this edit (if any)
        content: Optional[str] = None,
        view: Optional[View] = None,
        embed: Optional[discord.Embed] = None,
        file: Optional[File] = None
    ):
        log_info = f"edit_message called: content={content is not None}, view={view is not None}, embed={embed is not None}, file={file is not None}"
        if interaction: log_info += f" triggered by interaction {interaction.id} (type: {interaction.type})"
        else: log_info += " (internal call)"
        logger.debug(log_info)
        
        attachments = [file] if file else []

        try:
            if interaction:
                # This interaction is the one from a component callback or modal submit.
                # It should be used to edit the message it's attached to or its original response.
                if interaction.response.is_done():
                    # If deferred or already responded (e.g., send_modal), use edit_original_response.
                    # This edits the message the component was on, or the modal's ack message.
                    logger.debug(f"Editing original response for done interaction {interaction.id}")
                    await interaction.edit_original_response(content=content, embed=embed, view=view, attachments=attachments)
                else:
                    # This is the first response to this specific interaction.
                    logger.debug(f"Editing message for new interaction {interaction.id}")
                    await interaction.response.edit_message(content=content, embed=embed, view=view, attachments=attachments)
                
                # Update self.message to the message that was just edited, if applicable for view tracking
                if view is not None and self.message: # Only if we are updating the main view message
                    try:
                        # original_response() should give the message that was just acted upon by the interaction.
                        # This is important if the interaction was for the main message.
                        edited_msg = await interaction.original_response()
                        if self.message.id == edited_msg.id: # Ensure we're updating the correct message instance
                             self.message = edited_msg
                        else:
                             # This can happen if interaction was for an ephemeral msg, or if original_interaction was used
                             logger.debug(f"Interaction {interaction.id} edited a different message ({edited_msg.id}) than self.message ({self.message.id}). Not updating self.message from this interaction.")
                    except discord.NotFound:
                        logger.warning(f"Could not get original_response to update self.message after editing with interaction {interaction.id}")

            elif self.message: # No specific interaction, edit the view's tracked message
                logger.debug(f"Editing self.message (ID: {self.message.id})")
                await self.message.edit(content=content, embed=embed, view=view, attachments=attachments)
            else: # Fallback, should ideally not be reached if self.message is always set
                logger.warning("edit_message called with no interaction and no self.message. Using original_interaction.")
                if self.original_interaction.response.is_done():
                    await self.original_interaction.edit_original_response(content=content, embed=embed, view=view, attachments=attachments)
                else: # Should have been responded to in start_flow
                    await self.original_interaction.response.send_message(content=content, embed=embed, view=view, files=attachments, ephemeral=True)


        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Failed to edit message: {e}. Interaction: {interaction.id if interaction else 'N/A'}")
            # Fallback to followup if primary edit fails and we have an interaction
            if interaction and interaction.response.is_done():
                try:
                    followup_content = content if content else "Updating display..."
                    logger.debug(f"Attempting followup for interaction {interaction.id} after edit failure.")
                    await interaction.followup.send(followup_content, ephemeral=True, view=view, files=attachments if attachments else None)
                    # If this followup created a new primary message for the view, self.message might need an update.
                    # This part is tricky and depends on view logic.
                except discord.HTTPException as fe:
                    logger.error(f"Failed to send followup after message edit error for interaction {interaction.id}: {fe}")
            elif not interaction and not self.message:
                 logger.error("Failed to edit message: No valid interaction or message reference for edit/followup.")

        except Exception as e:
            logger.exception(f"Unexpected error editing StraightBetWorkflowView message: {e}")
            error_interaction = interaction or self.latest_interaction or self.original_interaction
            if error_interaction and error_interaction.response.is_done():
                 try: await error_interaction.followup.send("❌ An unexpected error occurred updating the display.", ephemeral=True)
                 except discord.HTTPException: pass
            elif error_interaction and not error_interaction.response.is_done(): # Should not happen
                 try: await error_interaction.response.send_message("❌ An unexpected error occurred updating the display.", ephemeral=True)
                 except discord.HTTPException: pass


    async def go_next(self, interaction: Interaction): # interaction is the one that triggered this step
        if self.is_processing:
            logger.debug(f"Skipping go_next call; already processing step {self.current_step} for user {interaction.user.id}")
            # If the interaction hasn't been responded to (e.g. deferred), it needs an ack
            if not interaction.response.is_done():
                try: await interaction.response.defer()
                except discord.HTTPException: pass # Already responded
            return
        self.is_processing = True
        
        # Ensure the incoming interaction is deferred if it's not the original one from start_flow
        # and hasn't been handled by a component's defer() or modal's defer().
        # Most component callbacks in this file *do* defer. Modals also defer.
        # This is a safeguard.
        if interaction != self.original_interaction and not interaction.response.is_done():
            try:
                logger.debug(f"Deferring interaction {interaction.id} at the start of go_next as it was not done.")
                await interaction.response.defer()
            except discord.HTTPException as e:
                 logger.warning(f"Tried to defer interaction {interaction.id} in go_next but failed (likely already responded): {e}")


        try:
            logger.debug(f"Processing go_next: current_step={self.current_step} for user {interaction.user.id} (interaction {interaction.id})")
            self.clear_items()
            self.current_step += 1
            step_content = f"**Step {self.current_step}**"
            embed_to_send = None
            file_to_send = None
            logger.debug(f"Entering step {self.current_step}")

            if self.current_step == 1:
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                self.add_item(LeagueSelect(self, allowed_leagues))
                self.add_item(CancelButton(self))
                step_content += ": Select League"
                # 'interaction' here is self.original_interaction from start_flow
                await self.edit_message(interaction, content=step_content, view=self)
            elif self.current_step == 2:
                self.add_item(LineTypeSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Line Type"
                # 'interaction' here is from LeagueSelect callback
                await self.edit_message(interaction, content=step_content, view=self)
            elif self.current_step == 3:
                league = self.bet_details.get('league')
                if not league:
                    logger.error("No league selected for game selection step.")
                    await self.edit_message(interaction, content="❌ No league selected. Please start over.", view=None)
                    self.stop()
                    return
                self.games = []
                if league != "Other" and hasattr(self.bot, 'game_service'):
                    try:
                        logger.debug(f"Fetching scheduled games for league: {league}, guild: {interaction.guild_id}")
                        self.games = await self.bot.game_service.get_league_games(
                            guild_id=interaction.guild_id,
                            league=league,
                            status='scheduled',
                            limit=25
                        )
                        logger.debug(f"Fetched {len(self.games)} upcoming scheduled games for {league}.")
                    except Exception as e:
                        logger.exception(f"Error fetching games for league {league} using get_league_games: {e}")
                if self.games:
                    self.add_item(GameSelect(self, self.games))
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content += f": Select Game for {league} (or Enter Manually)"
                    await self.edit_message(interaction, content=step_content, view=self)
                else:
                    logger.warning(f"No upcoming games found or error fetching for league {league}. Prompting for manual entry.")
                    self.add_item(ManualEntryButton(self)) # Button to open modal
                    self.add_item(CancelButton(self))
                    msg_content = f"No games found for {league}. Please enter details manually." if league != "Other" else "Please enter game details manually."
                    await self.edit_message(interaction, content=msg_content, view=self)
            elif self.current_step == 4: # This step is now primarily for modal submission handling or player props
                line_type = self.bet_details.get('line_type')
                game_id = self.bet_details.get('game_id')
                is_manual = game_id == "Other" # True if "Manual Entry" button or "Other" game selected

                # If coming from a modal, bet_details should be populated by modal's on_submit.
                # If game_id is "Other" OR if it's a player prop and we need player selection / manual prop entry.
                
                if interaction.type == discord.InteractionType.modal_submit:
                    logger.debug("go_next called after modal submission. Bet details should be populated.")
                    # Modal's on_submit should have set current_step correctly or called go_next appropriately.
                    # We expect bet_details (serial, line, odds etc.) to be set from the modal.
                    # Proceed to step 5 (UnitsSelect)
                    self.current_step = 5 # Force to next logical step after modal
                    # Fall through to current_step == 5 logic below
                elif line_type == "player_prop" and not is_manual: # Game selected, need player selection
                     home_players, away_players = [], []
                     try:
                         if hasattr(self.bot.game_service, 'get_game_players'):
                             players_data = await self.bot.game_service.get_game_players(game_id)
                             home_players = players_data.get('home_players', [])
                             away_players = players_data.get('away_players', [])
                         else:
                             logger.warning("GameService does not have 'get_game_players' method.")
                     except Exception as e:
                         logger.error(f"Failed to fetch players for game {game_id}: {e}")
                     
                     home_team = self.bet_details.get('home_team_name', 'Home Team')
                     away_team = self.bet_details.get('away_team_name', 'Away Team')
                     if home_players or away_players:
                         self.add_item(HomePlayerSelect(self, home_players, home_team))
                         self.add_item(AwayPlayerSelect(self, away_players, away_team))
                         self.add_item(CancelButton(self))
                         step_content += f": Select Player for Prop Bet ({home_team} vs {away_team})"
                         await self.edit_message(interaction, content=step_content, view=self)
                         # current_step remains 4 for player selection, go_next will be called by player select
                         self.is_processing = False
                         return # Wait for player selection
                     else: # No players fetched, proceed to manual modal for player prop
                         logger.warning(f"No players available/fetched for game {game_id}. Opening manual prop modal.")
                         is_manual = True # Force manual entry for player prop

                # If is_manual (either from game selection or forced for player prop) or line_type is not player_prop
                # and we haven't handled a modal submission yet for this step:
                if is_manual or (line_type != "player_prop" and interaction.type != discord.InteractionType.modal_submit):
                    modal = BetDetailsModal(line_type=line_type, is_manual=is_manual)
                    modal.view = self # Link modal back to this view
                    try:
                        # The 'interaction' here is from the component that led to this step
                        # (e.g., GameSelect, LineTypeSelect, or ManualEntryButton)
                        await interaction.response.send_modal(modal)
                        # After send_modal, the original interaction is responded to.
                        # We might want to update the original message content.
                        # edit_message with the same interaction will use interaction.edit_original_response()
                        await self.edit_message(interaction, content="Please fill out the bet details in the form above.", view=self)
                    except discord.HTTPException as e:
                        logger.error(f"Failed to send BetDetailsModal: {e}. Interaction state: {interaction.response.is_done()}")
                        await self.edit_message(interaction, content="❌ Failed to open bet details form. Please try again.", view=None)
                        self.stop()
                    self.is_processing = False # Waiting for modal submission
                    return # Exit go_next, modal will trigger next actions

                # If we fell through here, it implies modal was handled, and we might be ready for step 5
                # This path might need adjustment if modal on_submit doesn't set current_step correctly
                if not (self.bet_details.get('bet_serial')): # Check if modal actually processed
                    logger.warning("Step 4 reached without bet_serial after expected modal interaction. Re-evaluating.")
                    # This might indicate logic error or user cancelling modal.
                    # For now, let's assume if bet_serial isn't there, something went wrong before unit selection.
                    # Or, player prop selection is pending if not manual.
                    # This branch of step 4 is complex. If issues persist, it needs careful state checking.
                    if line_type == "player_prop" and not is_manual: # Player selection was supposed to happen
                        logger.debug("Player prop selection was expected. Staying on step 4 (effectively).")
                        self.current_step -=1 # revert step increment, wait for player select
                        self.is_processing = False
                        return


            if self.current_step == 5: # Renumbered from original due to modal logic
                if 'bet_serial' not in self.bet_details or not self.bet_details['bet_serial']:
                     logger.error("Bet serial missing before unit selection step.")
                     await self.edit_message(interaction, content="❌ Error: Bet record not created. Please try again.", view=None)
                     self.stop()
                     return
                self.add_item(UnitsSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Units for Bet"
                await self.edit_message(interaction, content=step_content, view=self)
            elif self.current_step == 6:
                 if 'units_str' not in self.bet_details:
                      logger.error("Units not selected before channel selection step.")
                      await self.edit_message(interaction, content="❌ Error: Units not selected. Please restart.", view=None)
                      self.stop()
                      return
                 try:
                     bet_serial = self.bet_details.get('bet_serial')
                     if not bet_serial:
                          raise ValueError("Bet serial is missing.")
                     home_team = self.bet_details.get('team', 'Unknown')
                     is_manual = self.bet_details.get('game_id') == "Other"
                     opponent = self.bet_details.get('opponent', 'Unknown')
                     if not is_manual and 'away_team_name' in self.bet_details: # From GameSelect
                          opponent = self.bet_details.get('away_team_name')
                          if 'home_team_name' in self.bet_details and home_team.lower() != self.bet_details['home_team_name'].lower():
                              home_team = self.bet_details['home_team_name'] # Ensure 'team' is consistent with game data

                     bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                         home_team=home_team,
                         away_team=opponent,
                         league=self.bet_details.get('league', 'NHL'),
                         line=self.bet_details.get('line', 'N/A'),
                         odds=float(self.bet_details.get('odds', 0)),
                         units=float(self.bet_details.get('units_str', '1.0')),
                         bet_id=str(bet_serial),
                         timestamp=datetime.now(timezone.utc),
                         bet_type="straight"
                     )
                     self.preview_image_bytes = io.BytesIO()
                     bet_slip_image.save(self.preview_image_bytes, format='PNG')
                     self.preview_image_bytes.seek(0)
                     file_to_send = File(self.preview_image_bytes, filename="bet_slip_preview.png")
                     self.preview_image_bytes.seek(0) # Reset for potential reuse
                 except (ValueError, KeyError, Exception) as e:
                     logger.exception(f"Failed to generate bet slip image at step 6: {e}")
                     await self.edit_message(interaction, content="❌ Failed to generate bet slip preview. Please try again.", view=None)
                     self.stop()
                     return
                 channels = []
                 try:
                     configured_channels = []
                     if hasattr(self.bot, 'db_manager') and interaction.guild_id:
                         settings = await self.bot.db_manager.fetch_one(
                             "SELECT embed_channel_1, embed_channel_2 FROM guild_settings WHERE guild_id = %s",
                             (interaction.guild_id,)
                         )
                         if settings:
                             for key in ['embed_channel_1', 'embed_channel_2']:
                                 ch_id = settings.get(key)
                                 if ch_id:
                                      channel = interaction.guild.get_channel(int(ch_id))
                                      if channel and isinstance(channel, TextChannel) and channel.permissions_for(interaction.guild.me).send_messages:
                                           configured_channels.append(channel)
                                           logger.debug(f"Found configured embed channel: {channel.id} ({channel.name})")
                     if configured_channels:
                         channels = configured_channels
                     elif interaction.guild:
                         channels = sorted(
                             [ch for ch in interaction.guild.text_channels
                              if ch.permissions_for(interaction.guild.me).send_messages],
                             key=lambda c: c.position
                         )[:25] # Limit to 25 for Select options
                         logger.debug(f"No configured embed channels, using all writable channels.")
                 except Exception as e:
                     logger.error(f"Failed to fetch channels at step 6: {e}", exc_info=True)

                 if not channels and interaction.guild:
                     logger.error("No writable channels found in the guild.")
                     await self.edit_message(interaction, content="❌ No text channels found where I can post the bet slip.", view=None)
                     self.stop()
                     return
                 self.add_item(ChannelSelect(self, channels))
                 self.add_item(CancelButton(self))
                 step_content += ": Review Bet & Select Channel to Post"
                 await self.edit_message(interaction, content=step_content, view=self, file=file_to_send)
            elif self.current_step == 7:
                 if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units_str', 'odds_str', 'line', 'team', 'league']):
                     logger.error(f"Missing bet details for confirmation: {self.bet_details}")
                     await self.edit_message(interaction, content="❌ Error: Bet details incomplete. Please restart.", view=None)
                     self.stop()
                     return
                 file_to_send = None
                 if self.preview_image_bytes:
                     self.preview_image_bytes.seek(0)
                     file_to_send = File(self.preview_image_bytes, filename="bet_slip_confirm.png")
                     self.preview_image_bytes.seek(0) # Keep for submit_bet
                 else:
                     logger.warning("Preview image bytes were lost before confirmation step. Will attempt regeneration.")
                 self.add_item(ConfirmButton(self))
                 self.add_item(CancelButton(self))
                 step_content = "**Final Step**: Confirm Bet Details"
                 channel_mention = f"<#{self.bet_details['channel_id']}>"
                 confirmation_text = (
                      f"{step_content}\n\n"
                      f"**League:** {self.bet_details['league']}\n"
                      f"**Bet:** {self.bet_details['line']} ({self.bet_details.get('team','')} vs {self.bet_details.get('opponent','')})\n"
                      f"**Odds:** {self.bet_details['odds_str']}\n"
                      f"**Units:** {self.bet_details['units_str']}\n"
                      f"**Post to:** {channel_mention}\n\n"
                      "Click 'Confirm & Post' to place the bet."
                 )
                 await self.edit_message(interaction, content=confirmation_text, view=self, file=file_to_send)
            else:
                logger.error(f"StraightBetWorkflowView reached unexpected step: {self.current_step}")
                await self.edit_message(interaction, content="❌ Invalid step reached. Please start over.", view=None)
                self.stop()
        except Exception as e:
            logger.exception(f"Error in straight bet workflow step {self.current_step} (interaction {interaction.id}): {e}")
            # Use the interaction that caused this go_next, or fallback if needed
            error_target_interaction = interaction or self.latest_interaction or self.original_interaction
            await self.edit_message(error_target_interaction, content="❌ An unexpected error occurred.", view=None)
            self.stop()
        finally:
            self.is_processing = False

    async def submit_bet(self, interaction: Interaction): # interaction is from ConfirmButton
        details = self.bet_details
        bet_serial = details.get('bet_serial')
        if not bet_serial:
             logger.error("Attempted to submit bet without a bet_serial.")
             # Edit the message associated with the ConfirmButton's interaction
             await self.edit_message(interaction, content="❌ Error: Bet ID missing. Cannot submit.", view=None)
             self.stop()
             return

        logger.info(f"Submitting straight bet {bet_serial} for user {interaction.user} (ID: {interaction.user.id})")
        # Update the message (from ConfirmButton) to "Processing..."
        # The ConfirmButton callback already did an edit_message to disable buttons.
        # We can edit it again if interaction is the same, or use self.message
        await self.edit_message(interaction, content="Processing and posting bet...", view=None, file=None)

        try:
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None
            if not post_channel or not isinstance(post_channel, TextChannel):
                logger.error(f"Invalid or inaccessible channel {post_channel_id} for bet {bet_serial}")
                raise ValueError(f"Could not find text channel <#{post_channel_id}> to post bet.")

            units = float(details.get('units_str', 1.0))
            odds = float(details.get('odds', 0)) # Should be stored as float from modal

            update_query = """
                UPDATE bets
                SET units = %s, odds = %s, channel_id = %s, confirmed = 1, status = 'pending'
                WHERE bet_serial = %s AND (confirmed = 0 OR confirmed IS NULL)
            """ # Added status = 'pending'
            rowcount, _ = await self.bot.db_manager.execute(
                update_query, units, odds, post_channel_id, bet_serial
            )

            if rowcount is None or rowcount == 0:
                 check_query = "SELECT confirmed, channel_id, units, status FROM bets WHERE bet_serial = %s"
                 existing_bet = await self.bot.db_manager.fetch_one(check_query, (bet_serial,))
                 if existing_bet and existing_bet['confirmed'] == 1:
                      logger.warning(f"Bet {bet_serial} was already confirmed. Status: {existing_bet['status']}. Proceeding with posting if not already posted.")
                      # Potentially re-use existing details if needed, though current logic regenerates image.
                      post_channel_id = existing_bet['channel_id'] # Ensure correct channel
                      post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else post_channel
                      units = float(existing_bet['units'])
                 else:
                      logger.error(f"Failed to update bet {bet_serial} to confirmed. Rowcount: {rowcount}. Existing: {existing_bet}")
                      raise BetServiceError("Failed to confirm bet details in database.")

            final_image_bytes = self.preview_image_bytes # Use stored bytes
            if not final_image_bytes:
                 logger.warning(f"Preview image bytes lost before final submission for bet {bet_serial}. Regenerating.")
                 try:
                     home_team = details.get('team', 'Unknown')
                     opponent = details.get('opponent', 'Unknown')
                     bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                         home_team=home_team, away_team=opponent,
                         league=details.get('league', 'NHL'), line=details.get('line', 'N/A'),
                         odds=odds, units=units, bet_id=str(bet_serial),
                         timestamp=datetime.now(timezone.utc), bet_type="straight"
                     )
                     final_image_bytes = io.BytesIO()
                     bet_slip_image.save(final_image_bytes, format='PNG')
                 except Exception as img_err:
                     logger.exception(f"Failed to regenerate bet slip image for {bet_serial}: {img_err}")
                     raise BetServiceError("Failed to generate final bet slip image.") from img_err

            if not final_image_bytes: # Should not happen if regeneration worked
                 raise ValueError(f"Final image data is missing for bet {bet_serial}.")

            final_image_bytes.seek(0)
            discord_file = File(final_image_bytes, filename=f"bet_slip_{bet_serial}.png")

            role_mention = ""
            display_name = interaction.user.display_name
            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            try: # Guild specific settings for posting
                settings = await self.bot.db_manager.fetch_one(
                    "SELECT authorized_role, member_role FROM guild_settings WHERE guild_id = %s",
                    (interaction.guild_id,)
                )
                if settings:
                    role_id = settings.get('authorized_role') or settings.get('member_role')
                    if role_id:
                         role = interaction.guild.get_role(int(role_id))
                         if role: role_mention = role.mention
                         else: logger.warning(f"Role ID {role_id} not found in guild {interaction.guild_id}.")
                
                capper_info = await self.bot.db_manager.fetch_one(
                    "SELECT display_name, image_path FROM cappers WHERE user_id = %s AND guild_id = %s",
                    (interaction.user.id, interaction.guild_id)
                )
                if capper_info:
                    display_name = capper_info['display_name'] or display_name
                    avatar_url = capper_info['image_path'] or avatar_url
            except Exception as e:
                logger.error(f"Error fetching guild settings or capper info for bet {bet_serial}: {e}")

            webhook = None
            try: # Webhook logic
                webhooks = await post_channel.webhooks()
                webhook_name_target = f"{self.bot.user.name} Bets" # Consistent webhook name
                webhook = next((wh for wh in webhooks if wh.user and wh.user.id == self.bot.user.id and wh.name == webhook_name_target), None)
                if not webhook: # Try finding any bot-owned webhook as fallback
                     webhook = next((wh for wh in webhooks if wh.user and wh.user.id == self.bot.user.id), None)
                if not webhook:
                    webhook = await post_channel.create_webhook(name=webhook_name_target)
                logger.debug(f"Using webhook: {webhook.name} (ID: {webhook.id}) in channel {post_channel_id} for bet {bet_serial}")
            except discord.Forbidden:
                logger.error(f"Permission error: Cannot manage webhooks in channel {post_channel_id} for bet {bet_serial}.")
                raise ValueError("Bot lacks permission to manage webhooks.")
            except discord.HTTPException as e:
                logger.error(f"HTTP error managing webhook for channel {post_channel_id} (bet {bet_serial}): {e}")
                raise ValueError(f"Failed to setup webhook: {e}")

            content_msg = role_mention if role_mention else ""
            sent_message = await webhook.send(
                content=content_msg,
                file=discord_file,
                username=display_name[:80], # Ensure username is within Discord's limits
                avatar_url=avatar_url,
                wait=True # Wait for message to be sent to get its ID
            )
            logger.info(f"Bet slip image sent for bet {bet_serial}, message ID: {sent_message.id}")

            # Add to pending reactions if service exists
            if hasattr(self.bot, 'bet_service') and hasattr(self.bot.bet_service, 'pending_reactions'):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial, 'user_id': interaction.user.id,
                    'guild_id': interaction.guild_id, 'channel_id': post_channel_id,
                    'line': details.get('line'), 'league': details.get('league'),
                    'bet_type': 'straight'
                }
                logger.debug(f"Added message {sent_message.id} to pending_reactions for bet {bet_serial}")

            await self.edit_message( # Update the ephemeral message from the ConfirmButton interaction
                interaction,
                content=f"✅ Bet placed successfully! (ID: `{bet_serial}`). Posted to {post_channel.mention}.",
                view=None
            )
        except (ValidationError, BetServiceError, ValueError) as e:
            logger.error(f"Error submitting bet {bet_serial}: {e}")
            await self.edit_message(interaction, content=f"❌ Error placing bet: {e}", view=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting bet {bet_serial}: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred while posting the bet.", view=None)
        finally:
            if self.preview_image_bytes:
                self.preview_image_bytes.close()
                self.preview_image_bytes = None
            self.stop()

# async def setup(bot: commands.Bot):
#     logger.info("StraightBetWorkflow components loaded (no Cog setup needed here)")
