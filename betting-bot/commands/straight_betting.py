# betting-bot/commands/straight_betting.py

"""Straight betting workflow for placing single-leg bets."""

import discord
from discord import ButtonStyle, Interaction, SelectOption, TextChannel, File, Embed
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union
from datetime import datetime, timezone
import io
import os

# Use relative imports if possible, otherwise adjust based on project structure
try:
    from ..utils.errors import BetServiceError, ValidationError, GameNotFoundError
    from ..utils.image_generator import BetSlipGenerator
    # Import commands.Cog for bot.add_cog
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
            if isinstance(start_dt_obj, datetime):
                 # Format time nicely, maybe convert to user's timezone if known/possible
                 time_str = start_dt_obj.strftime('%m/%d %H:%M %Z') # Example: 05/06 14:00 UTC
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id') # Assuming 'id' is the API game ID
            if game_api_id is None:
                logger.warning(f"Game missing 'id': {game}")
                continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id))) # Ensure value is string, limit label length
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(
            placeholder="Select Game (or Other)...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        selected_game_id = self.values[0]
        self.parent_view.bet_details['game_id'] = selected_game_id # Store API ID or "Other"
        if selected_game_id != "Other":
            # Find the full game details again to store names
            game = next((g for g in self.parent_view.games if str(g.get('id')) == selected_game_id), None)
            if game:
                self.parent_view.bet_details['home_team_name'] = game.get('home_team_name', 'Unknown')
                self.parent_view.bet_details['away_team_name'] = game.get('away_team_name', 'Unknown')
            else:
                logger.warning(f"Could not find full details for selected game ID {selected_game_id}")
                # Might need manual entry fallback here if game details are lost
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
            min_values=0, # Allow skipping selection if choosing away player
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.bet_details['player'] = self.values[0].replace("home_", "")
            # Disable the other player select if one is chosen
            for item in self.parent_view.children:
                if isinstance(item, AwayPlayerSelect):
                    item.disabled = True
        else:
            # If 'none' or empty selection, ensure player is None if not set by other select
            if not self.parent_view.bet_details.get('player'):
                 self.parent_view.bet_details['player'] = None
        logger.debug(f"Home player selected: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        # Only advance if a player was actually selected (or if both selects are now disabled after one pick)
        # This logic might need refinement depending on desired UX
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
            min_values=0, # Allow skipping selection
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
    # Keep __init__ and callback as they were
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Manual Entry",
            # Use a unique ID tied to the interaction to avoid collisions if multiple views are active
            custom_id=f"straight_manual_entry_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Manual Entry button clicked by user {interaction.user.id}")
        self.parent_view.bet_details['game_id'] = "Other" # Mark as manual entry
        # Disable buttons on the current view
        self.disabled = True
        for item in self.parent_view.children:
            if isinstance(item, CancelButton):
                item.disabled = True # Disable cancel as well

        line_type = self.parent_view.bet_details.get('line_type', 'game_line') # Default if not set
        try:
            # Pass True for is_manual to the modal
            modal = BetDetailsModal(line_type=line_type, is_manual=True)
            modal.view = self.parent_view # Attach view reference to modal
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully")
            # Edit the original message to reflect modal state
            await self.parent_view.edit_message(
                interaction,
                content="Manual entry form opened. Please fill in the details.",
                view=self.parent_view # Keep the (disabled) view for context
            )
            # Let the modal's on_submit handle the next step
            # self.parent_view.current_step = 4 # Modal submit will advance step
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal: {e}")
            try:
                # Edit message indicating failure
                await self.parent_view.edit_message(
                    interaction,
                    content="❌ Failed to open manual entry form. Please restart the /bet command.",
                    view=None # Remove view on failure
                )
            except discord.HTTPException as e2:
                logger.error(f"Failed to edit message after modal error: {e2}")
            self.parent_view.stop() # Stop the view


class CancelButton(Button):
    # Keep __init__ and callback as they were
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
            item.disabled = True # Disable all components

        bet_serial = self.parent_view.bet_details.get('bet_serial')
        if bet_serial:
            try:
                # Ensure bet_service is available on the bot instance
                if hasattr(self.parent_view.bot, 'bet_service'):
                     await self.parent_view.bot.bet_service.delete_bet(bet_serial)
                     logger.info(f"Bet {bet_serial} cancelled and deleted by user {interaction.user.id}.")
                     await interaction.response.edit_message(
                         content=f"Bet `{bet_serial}` cancelled and records deleted.",
                         view=None # Remove view after cancellation
                     )
                else:
                    logger.error("BetService not found on bot instance during cancellation.")
                    await interaction.response.edit_message(
                        content="Cancellation failed (Internal Error).", view=None
                    )
            except Exception as e:
                logger.error(f"Failed to delete bet {bet_serial} during cancellation: {e}")
                # Still edit the message to indicate cancellation attempt
                await interaction.response.edit_message(
                    content=f"Bet `{bet_serial}` cancellation process failed. Please contact admin if needed.",
                    view=None
                )
        else:
             # No bet created yet, just cancel the workflow
             await interaction.response.edit_message(
                 content="Bet workflow cancelled.",
                 view=None
             )
        self.parent_view.stop()


class BetDetailsModal(Modal):
    # Keep __init__ and on_submit as they were, ensuring bet creation happens here
    def __init__(self, line_type: str, is_manual: bool = False):
        title = "Enter Bet Details"
        super().__init__(title=title)
        self.line_type = line_type
        self.is_manual = is_manual # Store if entry is manual

        # --- Dynamically add fields based on context ---

        # Team Name: Always needed for manual entry, often needed for player props too
        # We need team context even if game was selected, for player props
        self.team = TextInput(
            label="Team Bet On",
            required=True,
            max_length=100,
            placeholder="Enter the team name involved in the bet"
        )
        self.add_item(self.team)

        # Opponent Name: Always required for manual entry
        if self.is_manual:
            self.opponent = TextInput(
                label="Opponent",
                required=True,
                max_length=100,
                placeholder="Enter opponent name"
            )
            self.add_item(self.opponent)
        # Else (game selected): opponent name might be pre-filled or not needed directly in modal

        # Player/Line: Depends on line_type
        if line_type == "player_prop":
            self.player_line = TextInput(
                label="Player - Line",
                required=True,
                max_length=100, # Increased length
                placeholder="E.g., Connor McDavid - Shots Over 3.5"
            )
            self.add_item(self.player_line)
        else: # game_line
            self.line = TextInput(
                label="Line",
                required=True,
                max_length=100,
                placeholder="E.g., Moneyline, Spread -7.5, Total Over 6.5"
            )
            self.add_item(self.line)

        # Odds: Always required
        self.odds = TextInput(
            label="Odds",
            required=True,
            max_length=10, # Allow for signs and numbers
            placeholder="Enter American odds (e.g., -110, +200)"
        )
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual} by user {interaction.user.id}")
        # Defer the interaction response immediately
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            # --- Extract data from modal ---
            team = self.team.value.strip()
            # Opponent might not be present if game was selected
            opponent = self.opponent.value.strip() if hasattr(self, 'opponent') else self.view.bet_details.get('away_team_name', 'Unknown') # Fallback if game selected
            if self.line_type == "player_prop":
                line = self.player_line.value.strip()
            else:
                line = self.line.value.strip()
            odds_str = self.odds.value.strip()

            # --- Input Validation ---
            if not team or not line or not odds_str: # Basic check
                await interaction.followup.send("❌ Team, Line, and Odds are required. Please try again.", ephemeral=True)
                return # Don't proceed

            # Validate Odds
            try:
                # Remove '+' if present for parsing, handle empty string
                odds_val_str = odds_str.replace('+', '')
                if not odds_val_str: raise ValueError("Odds cannot be empty.")
                odds_val = float(odds_val_str)
                if -100 < odds_val < 100 and odds_val != 0: # Allow 0 for potential error cases? Usually invalid.
                     raise ValueError("Odds cannot be between -99 and +99 (excluding 0).")
            except ValueError as ve:
                logger.warning(f"Invalid odds entered: {odds_str} - Error: {ve}")
                await interaction.followup.send(f"❌ Invalid odds format: '{odds_str}'. Use American odds (e.g., -110, +150). {ve}", ephemeral=True)
                return

            # If game was selected (not manual), use pre-filled opponent
            if not self.is_manual and 'away_team_name' in self.view.bet_details:
                 opponent = self.view.bet_details['away_team_name']
                 # Also ensure home team matches if needed
                 if 'home_team_name' in self.view.bet_details and team.lower() != self.view.bet_details['home_team_name'].lower():
                     # Decide how to handle mismatch - maybe use the selected game's home team?
                     logger.warning(f"Team entered '{team}' differs from selected game home team '{self.view.bet_details['home_team_name']}'. Using game team.")
                     team = self.view.bet_details['home_team_name']

            # --- Prepare Bet Details for Service ---
            current_leg_details = {
                'game_id': self.view.bet_details.get('game_id') if self.view.bet_details.get('game_id') != 'Other' else None,
                'bet_type': self.line_type, # This is 'game_line' or 'player_prop'
                'team': team,
                'opponent': opponent,
                'line': line,
                # Store odds_str for potential later display, use float for service
                'odds': odds_val,
                'league': self.view.bet_details.get('league', 'NHL') # Get league from parent view
            }

            # --- Create the Bet in DB (THIS IS THE ONLY PLACE IT SHOULD HAPPEN) ---
            try:
                # Assuming units default to 1.0 for now, will be selected later
                bet_serial = await self.view.bot.bet_service.create_straight_bet(
                    guild_id=interaction.guild_id,
                    user_id=interaction.user.id,
                    game_id=current_leg_details['game_id'],
                    bet_type=current_leg_details['bet_type'], # Pass the specific type
                    team=current_leg_details['team'],
                    opponent=current_leg_details['opponent'],
                    line=current_leg_details['line'],
                    units=1.00,  # Default units for now
                    odds=current_leg_details['odds'],
                    channel_id=None,  # Will be set later after channel select
                    league=current_leg_details['league']
                )
                if bet_serial is None or bet_serial == 0:
                     # Handle the case where bet creation failed (e.g., DB error, returned 0/None)
                     logger.error(f"Bet creation failed for user {interaction.user.id}, received bet_serial: {bet_serial}")
                     await interaction.followup.send("❌ Failed to create bet record in the database. Please try again or contact admin.", ephemeral=True)
                     # Potentially stop the view here
                     self.view.stop()
                     return

                # Store the valid bet_serial and other details in the parent view
                self.view.bet_details['bet_serial'] = bet_serial
                self.view.bet_details['line'] = line # Store the specific line chosen
                self.view.bet_details['odds_str'] = odds_str # Store original string if needed
                self.view.bet_details['odds'] = odds_val # Store float value
                self.view.bet_details['team'] = team # Ensure team is stored
                self.view.bet_details['opponent'] = opponent # Ensure opponent is stored
                logger.debug(f"Created straight bet with serial {bet_serial} via modal.")

                # Preload logos based on final team/opponent
                await self.view._preload_team_logos(team, opponent, current_leg_details['league'])

            except Exception as e:
                logger.exception(f"Failed to create straight bet in DB from modal: {e}")
                await interaction.followup.send("❌ Failed to save bet details. Please try again.", ephemeral=True)
                self.view.stop()
                return

            # --- Advance Workflow ---
            # Update step marker in the view
            self.view.current_step = 4 # Mark modal step as complete
            # Edit the original message (followup already handled by defer)
            await self.view.edit_message(
                interaction,
                content="Bet details entered. Processing next step...",
                view=self.view # Keep view active
            )
            # Trigger the next step in the parent view's logic
            await self.view.go_next(interaction)

        except Exception as e:
            logger.exception(f"Error in BetDetailsModal on_submit: {e}")
            # Use followup because the interaction was deferred
            await interaction.followup.send("❌ Failed to process bet details. Please try again.", ephemeral=True)
            self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
         try:
             # Use followup because original response was likely deferred
              if not interaction.response.is_done():
                   # Should ideally not happen if we defer first thing in on_submit
                   await interaction.response.send_message('❌ An error occurred with the bet details modal.', ephemeral=True)
              else:
                   await interaction.followup.send('❌ An error occurred processing the bet details modal.', ephemeral=True)
         except discord.HTTPException:
             logger.warning("Could not send error followup for BetDetailsModal.")
         # Optionally stop the parent view
         if hasattr(self, 'view'):
              self.view.stop()


class UnitsSelect(Select):
    # Keep __init__ and callback as they were
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="1 Unit", value="1.0"),
            SelectOption(label="2 Units", value="2.0"),
            SelectOption(label="3 Units", value="3.0")
            # Add more unit options if needed, up to 25
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
    # Keep __init__ and callback as they were
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
            await interaction.response.defer()
            return # Do nothing if 'none' is selected
        self.parent_view.bet_details['channel_id'] = int(selected_value)
        logger.debug(f"Channel selected: {selected_value} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class ConfirmButton(Button):
    # Keep __init__ and callback as they were
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Confirm & Post",
            custom_id=f"straight_confirm_bet_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Confirm button clicked by user {interaction.user.id}")
        # Disable all buttons on the view
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        # Acknowledge interaction by editing the message (removes components)
        await interaction.response.edit_message(view=self.parent_view) # Keep view to show disabled buttons
        # Proceed to submit the bet
        await self.parent_view.submit_bet(interaction)

# --- Main Workflow View ---
class StraightBetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot): # Added type hint for bot
        super().__init__(timeout=600) # Increased timeout
        self.original_interaction = interaction
        self.bot = bot # Store bot instance
        self.current_step = 0
        self.bet_details: Dict[str, Any] = {'bet_type': 'straight'} # Explicitly type hint
        self.games: List[Dict] = [] # Store fetched games
        self.message: Optional[Union[discord.WebhookMessage, discord.InteractionMessage]] = None # Type hint message
        self.is_processing = False # Lock to prevent race conditions
        self.latest_interaction = interaction # Track latest interaction for editing
        self.bet_slip_generator = BetSlipGenerator() # Initialize image generator
        self.preview_image_bytes: Optional[io.BytesIO] = None # Store generated image bytes
        self.team_logos: Dict[str, Optional[str]] = {} # Cache for logo paths {team_league: path_or_None}


    async def _preload_team_logos(self, team1: str, team2: str, league: str):
        """Preload team logos to check availability and paths."""
        # Ensure generator is available
        if not hasattr(self, 'bet_slip_generator'): return

        keys = [f"{team1}_{league}", f"{team2}_{league}"]
        for key in keys:
            if key not in self.team_logos: # Only load if not already attempted
                 try:
                      # Attempt to load logo using the generator's method
                      # This implicitly checks existence and logs warnings if not found
                      # We don't need the Image object here, just the check/warning
                      _ = self.bet_slip_generator._load_team_logo(key.split('_')[0], league)
                      # Store something to indicate we checked (even if it's None for not found)
                      self.team_logos[key] = "checked" # Or store actual path if needed later
                 except Exception as e:
                      logger.error(f"Error preloading logo for {key}: {e}")
                      self.team_logos[key] = None # Mark as failed/unavailable

    async def start_flow(self):
        logger.debug(f"Starting straight bet workflow for user {self.original_interaction.user} (ID: {self.original_interaction.user.id})")
        try:
            # Initial message should have been sent by the command caller using defer/followup
            # If not, send it here
            if not self.original_interaction.response.is_done():
                 # This shouldn't normally happen if called after deferral
                 await self.original_interaction.response.send_message(
                     "Starting straight bet placement...", view=self, ephemeral=True
                 )
                 self.message = await self.original_interaction.original_response()
            else:
                 # If called via followup, store the message reference
                 if not self.message: # Check if message ref is already set
                      self.message = await self.original_interaction.followup.send(
                           "Starting straight bet placement...", view=self, ephemeral=True
                      )


            # Start the first step
            await self.go_next(self.original_interaction)
        except discord.HTTPException as e:
            logger.error(f"Failed to send initial message/start flow for straight workflow: {e}")
            # Try followup if initial response failed or was already done
            try:
                 await self.original_interaction.followup.send(
                     "❌ Failed to start bet workflow. Please try again.", ephemeral=True
                 )
            except discord.HTTPException: pass # Ignore if followup also fails
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
        interaction: Optional[Interaction] = None, # Interaction that triggered the edit
        content: Optional[str] = None,
        view: Optional[View] = None,
        embed: Optional[discord.Embed] = None,
        file: Optional[File] = None
    ):
        """Helper to edit the original workflow message."""
        # Use the latest interaction if available, otherwise the original one
        target_interaction = interaction or self.latest_interaction or self.original_interaction
        # Fallback to the stored message reference if interaction edit fails
        target_message = self.message

        log_info = f"Editing message: content={content is not None}, view={view is not None}, embed={embed is not None}, file={file is not None}"
        if interaction: log_info += f" triggered by user {interaction.user.id}"
        logger.debug(log_info)

        attachments = [file] if file else []

        try:
            # Prefer editing the original interaction response
            await target_interaction.edit_original_response(
                content=content,
                embed=embed,
                view=view,
                attachments=attachments
            )
            # Update message reference if needed (though usually not necessary after initial send)
            # self.message = await target_interaction.original_response()
        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Failed to edit original interaction response: {e}. Trying stored message reference.")
            # Fallback to editing the message object directly if interaction edit fails
            if target_message and isinstance(target_message, discord.WebhookMessage):
                try:
                    await target_message.edit(
                        content=content,
                        embed=embed,
                        view=view,
                        attachments=attachments
                    )
                except (discord.NotFound, discord.HTTPException) as e2:
                    logger.error(f"Failed to edit StraightBetWorkflowView message (fallback): {e2}")
                    if interaction: # Try to inform the user via followup
                         try:
                             await interaction.followup.send("❌ Failed to update bet workflow display.", ephemeral=True)
                         except discord.HTTPException: pass # Ignore if followup fails
            else:
                logger.error("Failed to edit message: No valid interaction or message reference.")
                if interaction:
                    try:
                        await interaction.followup.send("❌ Failed to update bet workflow display.", ephemeral=True)
                    except discord.HTTPException: pass
        except Exception as e:
            logger.exception(f"Unexpected error editing StraightBetWorkflowView message: {e}")
            if interaction:
                 try:
                     await interaction.followup.send("❌ An unexpected error occurred updating the display.", ephemeral=True)
                 except discord.HTTPException: pass


    async def go_next(self, interaction: Interaction):
        """Handle progression to the next step in the workflow."""
        if self.is_processing:
            logger.debug(f"Skipping go_next call; already processing step {self.current_step} for user {interaction.user.id}")
            return
        self.is_processing = True
        try:
            logger.debug(f"Processing go_next: current_step={self.current_step} for user {interaction.user.id}")
            self.clear_items() # Clear components from previous step
            self.current_step += 1
            step_content = f"**Step {self.current_step}**"
            embed_to_send = None
            file_to_send = None # Reset file

            logger.debug(f"Entering step {self.current_step}")

            # --- Workflow Steps ---
            if self.current_step == 1: # League Selection
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"] # Add more as needed
                self.add_item(LeagueSelect(self, allowed_leagues))
                self.add_item(CancelButton(self))
                step_content += ": Select League"
                await self.edit_message(interaction, content=step_content, view=self)

            elif self.current_step == 2: # Line Type Selection
                self.add_item(LineTypeSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Line Type"
                await self.edit_message(interaction, content=step_content, view=self)

            elif self.current_step == 3: # Game Selection or Manual Entry Prompt
                league = self.bet_details.get('league')
                if not league:
                    logger.error("No league selected for game selection step.")
                    await self.edit_message(interaction, content="❌ No league selected. Please start over.", view=None)
                    self.stop()
                    return

                self.games = [] # Reset games list
                if league != "Other" and hasattr(self.bot, 'game_service'):
                    try:
                        # Fetch upcoming games for the selected league
                        # Determine sport category if needed by game_service
                        sport = self.bet_slip_generator.SPORT_CATEGORY_MAP.get(league.upper()) # Use map from generator
                        if sport:
                             # Assuming get_upcoming_games might need guild_id and potentially sport
                             # Adjust parameters as needed for your game_service implementation
                             self.games = await self.bot.game_service.get_upcoming_games(
                                 guild_id=interaction.guild_id, # Pass guild ID
                                 league=league, # Pass league name/ID
                                 hours=72 # Example timeframe
                             )
                             logger.debug(f"Fetched {len(self.games)} upcoming games for {league}.")
                        else:
                             logger.warning(f"Could not determine sport category for league: {league}")

                    except Exception as e:
                        logger.exception(f"Error fetching games for league {league}: {e}")
                        # Proceed to manual entry on error

                if self.games: # Found games, show GameSelect
                    self.add_item(GameSelect(self, self.games))
                    # Keep Manual Entry as an option even if games are found
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content += f": Select Game for {league} (or Enter Manually)"
                    await self.edit_message(interaction, content=step_content, view=self)
                else: # No games found or league is "Other" or error occurred
                    logger.warning(f"No upcoming games found or error fetching for league {league}. Prompting for manual entry.")
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content = f"No games found for {league}. Please enter details manually." if league != "Other" else "Please enter game details manually."
                    await self.edit_message(interaction, content=step_content, view=self)

            elif self.current_step == 4: # Player Selection (if player prop) or Modal Trigger
                line_type = self.bet_details.get('line_type')
                game_id = self.bet_details.get('game_id') # This is API ID or "Other"
                is_manual = game_id == "Other"

                if line_type == "player_prop":
                     # Try fetching players if game was selected and service available
                     if not is_manual and hasattr(self.bot, 'game_service'):
                          home_players, away_players = [], []
                          try:
                              # Assuming game_service needs API game ID
                              players_data = await self.bot.game_service.get_game_players(game_id) # Adjust call if needed
                              home_players = players_data.get('home_players', [])
                              away_players = players_data.get('away_players', [])
                          except Exception as e:
                              logger.error(f"Failed to fetch players for game {game_id}: {e}")
                              # Fallback to manual entry if player fetch fails

                          home_team = self.bet_details.get('home_team_name', 'Home Team')
                          away_team = self.bet_details.get('away_team_name', 'Away Team')

                          if home_players or away_players: # Show player selects
                              self.add_item(HomePlayerSelect(self, home_players, home_team))
                              self.add_item(AwayPlayerSelect(self, away_players, away_team))
                              self.add_item(CancelButton(self))
                              step_content += f": Select Player for Prop Bet ({home_team} vs {away_team})"
                              await self.edit_message(interaction, content=step_content, view=self)
                              # Stay at step 4, selection callback will trigger go_next
                              self.current_step -= 1 # Decrement step as we wait for player select callback
                              self.is_processing = False # Release lock
                              return # Don't proceed further in go_next yet
                          else:
                              logger.warning(f"No players available/fetched for game {game_id}. Proceeding to manual prop entry.")
                              # Fallthrough to show modal below
                     # else: Fallthrough to show modal (is_manual or no game_service)

                # Show Modal for game_line OR player_prop manual/fallback
                modal = BetDetailsModal(line_type=line_type, is_manual=is_manual)
                modal.view = self # Link modal back to this view
                try:
                    # Check if interaction already responded to (e.g., by a previous step's defer)
                    if interaction.response.is_done():
                         # This should not happen if flow is correct, but handle defensively
                         logger.warning("Interaction already responded to before sending modal. Stopping workflow.")
                         await interaction.followup.send("❌ Workflow error. Please restart the /bet command.", ephemeral=True)
                         self.stop()
                         return
                    await interaction.response.send_modal(modal)
                    # Modal submission will handle the next step via its on_submit
                    # No need to edit message here, modal is separate UI
                except discord.HTTPException as e:
                    logger.error(f"Failed to send BetDetailsModal: {e}")
                    await interaction.followup.send("❌ Failed to open bet details form. Please try again.", ephemeral=True)
                    self.stop()
                # Don't proceed further in go_next, wait for modal submission
                self.is_processing = False # Release lock
                return

            elif self.current_step == 5: # Units Selection (After Modal Submit)
                # Bet should have been created in modal submit and bet_serial stored
                if 'bet_serial' not in self.bet_details or not self.bet_details['bet_serial']:
                     logger.error("Bet serial missing after modal submission step.")
                     await self.edit_message(interaction, content="❌ Error: Bet record not created. Please try again.", view=None)
                     self.stop()
                     return

                self.add_item(UnitsSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Units for Bet"
                await self.edit_message(interaction, content=step_content, view=self)

            elif self.current_step == 6: # Channel Selection & Preview Generation
                 # *** REMOVED REDUNDANT BET CREATION CALL ***

                 # Validate units were selected
                 if 'units_str' not in self.bet_details:
                      logger.error("Units not selected before channel selection step.")
                      await self.edit_message(interaction, content="❌ Error: Units not selected. Please restart.", view=None)
                      self.stop()
                      return

                 # --- Generate Preview Image ---
                 try:
                     # Ensure bet_serial exists from previous step
                     bet_serial = self.bet_details.get('bet_serial')
                     if not bet_serial:
                          raise ValueError("Bet serial is missing.")

                     # Get required details for image generation
                     home_team = self.bet_details.get('team', 'Unknown') # Use 'team' from modal
                     # Get opponent based on manual/game selected
                     is_manual = self.bet_details.get('game_id') == "Other"
                     opponent = self.bet_details.get('opponent', 'Unknown') # From modal
                     if not is_manual and 'away_team_name' in self.bet_details:
                          # If game was selected, override opponent with game data for consistency
                          opponent = self.bet_details.get('away_team_name')
                          # Optionally override home_team too if modal input differed from selected game
                          if 'home_team_name' in self.bet_details and home_team.lower() != self.bet_details['home_team_name'].lower():
                              home_team = self.bet_details['home_team_name']


                     bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                         home_team=home_team,
                         away_team=opponent,
                         league=self.bet_details.get('league', 'NHL'),
                         line=self.bet_details.get('line', 'N/A'), # Line from modal
                         odds=float(self.bet_details.get('odds', 0)), # Odds from modal
                         units=float(self.bet_details.get('units_str', '1.0')), # Units from previous select
                         bet_id=str(bet_serial),
                         timestamp=datetime.now(timezone.utc),
                         bet_type="straight"
                     )

                     # Store image bytes for potential re-use in next step
                     self.preview_image_bytes = io.BytesIO()
                     bet_slip_image.save(self.preview_image_bytes, format='PNG')
                     self.preview_image_bytes.seek(0) # Rewind buffer
                     file_to_send = File(self.preview_image_bytes, filename="bet_slip_preview.png")
                     self.preview_image_bytes.seek(0) # Rewind again after creating File object

                 except (ValueError, KeyError, Exception) as e:
                     logger.exception(f"Failed to generate bet slip image at step 6: {e}")
                     await self.edit_message(interaction, content="❌ Failed to generate bet slip preview. Please try again.", view=None)
                     self.stop()
                     return

                 # --- Get Writable Channels ---
                 channels = []
                 try:
                     # Preferentially use configured embed channels if available
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
                     elif interaction.guild: # Fallback to all writable text channels
                         channels = sorted(
                             [ch for ch in interaction.guild.text_channels
                              if ch.permissions_for(interaction.guild.me).send_messages],
                             key=lambda c: c.position
                         )
                         logger.debug(f"No configured embed channels, using all writable channels.")
                 except Exception as e:
                     logger.error(f"Failed to fetch channels at step 6: {e}", exc_info=True)
                     # Continue without channels, will show error in Select

                 if not channels and interaction.guild: # Check again after potential fetches
                     logger.error("No writable channels found in the guild.")
                     await self.edit_message(interaction, content="❌ No text channels found where I can post the bet slip.", view=None)
                     self.stop()
                     return

                 # --- Update View for Channel Selection ---
                 self.add_item(ChannelSelect(self, channels))
                 self.add_item(CancelButton(self))
                 step_content += ": Review Bet & Select Channel to Post"
                 await self.edit_message(interaction, content=step_content, view=self, file=file_to_send)

            elif self.current_step == 7: # Confirmation Step (After Channel Selected)
                 # Validate essential details exist
                 if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units', 'odds', 'line', 'team', 'league']):
                     logger.error(f"Missing bet details for confirmation: {self.bet_details}")
                     await self.edit_message(interaction, content="❌ Error: Bet details incomplete. Please restart.", view=None)
                     self.stop()
                     return

                 # Re-generate preview if needed (or use cached bytes)
                 file_to_send = None
                 if self.preview_image_bytes:
                     self.preview_image_bytes.seek(0) # Rewind
                     file_to_send = File(self.preview_image_bytes, filename="bet_slip_confirm.png")
                     self.preview_image_bytes.seek(0) # Rewind again
                 else:
                     logger.warning("Preview image bytes were lost before confirmation step. Regenerating.")
                     # Add regeneration logic similar to step 6 if needed, though ideally it shouldn't be lost.
                     pass # For now, proceed without image if lost

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

            else: # Should not happen
                logger.error(f"StraightBetWorkflowView reached unexpected step: {self.current_step}")
                await self.edit_message(interaction, content="❌ Invalid step reached. Please start over.", view=None)
                self.stop()

        except Exception as e:
            logger.exception(f"Error in straight bet workflow step {self.current_step}: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred.", view=None)
            self.stop()
        finally:
            self.is_processing = False # Release lock

    async def submit_bet(self, interaction: Interaction):
        """Submits the finalized bet: updates DB, sends image, confirms."""
        details = self.bet_details
        bet_serial = details.get('bet_serial')
        if not bet_serial:
             logger.error("Attempted to submit bet without a bet_serial.")
             await self.edit_message(interaction, content="❌ Error: Bet ID missing. Cannot submit.", view=None)
             self.stop()
             return

        logger.info(f"Submitting straight bet {bet_serial} for user {interaction.user} (ID: {interaction.user.id})")
        # Show processing message immediately
        await self.edit_message(interaction, content="Processing and posting bet...", view=None, file=None) # Clear previous image/view

        try:
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None
            if not post_channel or not isinstance(post_channel, TextChannel):
                logger.error(f"Invalid or inaccessible channel {post_channel_id} for bet {bet_serial}")
                raise ValueError(f"Could not find text channel <#{post_channel_id}> to post bet.")

            # --- Update Bet Record with Units and Confirmation ---
            # Ensure units and odds are floats
            units = float(details.get('units_str', 1.0))
            odds = float(details.get('odds', 0))

            # Update the bet in the database with selected units and channel_id
            update_query = """
                UPDATE bets
                SET units = %s, odds = %s, channel_id = %s, confirmed = 1
                WHERE bet_serial = %s AND confirmed = 0
            """
            rowcount, _ = await self.bot.db_manager.execute(
                update_query, units, odds, post_channel_id, bet_serial
            )

            if rowcount is None or rowcount == 0:
                 # Check if it was already confirmed by another interaction (race condition?)
                 check_query = "SELECT confirmed, channel_id, units FROM bets WHERE bet_serial = %s"
                 existing_bet = await self.bot.db_manager.fetch_one(check_query, (bet_serial,))
                 if existing_bet and existing_bet['confirmed'] == 1:
                      logger.warning(f"Bet {bet_serial} was already confirmed. Proceeding with posting.")
                      # Use existing channel/units if update failed due to confirmation race
                      post_channel_id = existing_bet['channel_id']
                      post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else post_channel
                      units = float(existing_bet['units'])
                 else:
                      logger.error(f"Failed to update bet {bet_serial} with units/channel. Rowcount: {rowcount}")
                      raise BetServiceError("Failed to confirm bet details in database.")

            # --- Prepare Final Image ---
            # Regenerate image with final units if necessary, or use cached bytes
            final_image_bytes = self.preview_image_bytes
            if not final_image_bytes:
                 logger.warning("Preview image bytes lost before final submission. Regenerating.")
                 # Regeneration logic (ensure details are correct)
                 try:
                     home_team = details.get('team', 'Unknown')
                     opponent = details.get('opponent', 'Unknown') # Use final opponent
                     bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                         home_team=home_team, away_team=opponent,
                         league=details.get('league', 'NHL'), line=details.get('line', 'N/A'),
                         odds=odds, units=units, bet_id=str(bet_serial),
                         timestamp=datetime.now(timezone.utc), bet_type="straight"
                     )
                     final_image_bytes = io.BytesIO()
                     bet_slip_image.save(final_image_bytes, format='PNG')
                 except Exception as img_err:
                     logger.exception(f"Failed to regenerate bet slip image: {img_err}")
                     raise BetServiceError("Failed to generate final bet slip image.") from img_err

            if not final_image_bytes:
                 raise ValueError("Final image data is missing.")

            final_image_bytes.seek(0) # Rewind buffer
            discord_file = File(final_image_bytes, filename=f"bet_slip_{bet_serial}.png")

            # --- Fetch Role Mention and Capper Info ---
            role_mention = ""
            display_name = interaction.user.display_name
            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None # Use display_avatar

            try:
                # Fetch Guild Settings (including roles and maybe masks)
                settings = await self.bot.db_manager.fetch_one(
                    "SELECT authorized_role, member_role, bot_name_mask, bot_image_mask FROM guild_settings WHERE guild_id = %s",
                    (interaction.guild_id,)
                )
                if settings:
                    # Get role mention (use authorized_role or member_role? Check config intent)
                    # Assuming 'authorized_role' is the capper role to mention
                    role_id = settings.get('authorized_role') or settings.get('member_role')
                    if role_id:
                         role = interaction.guild.get_role(int(role_id))
                         if role: role_mention = role.mention
                         else: logger.warning(f"Role ID {role_id} not found in guild {interaction.guild_id}.")

                    # Get bot masks (if applicable, use them for webhook)
                    # bot_name_mask = settings.get('bot_name_mask')
                    # bot_image_mask = settings.get('bot_image_mask')
                    # If masks exist, potentially override display_name/avatar_url here
                    pass # Placeholder for mask logic

                # Fetch Capper Info (overrides default name/avatar if available)
                capper_info = await self.bot.db_manager.fetch_one(
                    "SELECT display_name, image_path FROM cappers WHERE user_id = %s AND guild_id = %s",
                    (interaction.user.id, interaction.guild_id)
                )
                if capper_info:
                    display_name = capper_info['display_name'] or display_name # Use capper name if set
                    avatar_url = capper_info['image_path'] or avatar_url # Use capper image if set

            except Exception as e:
                logger.error(f"Error fetching guild settings or capper info: {e}")
                # Continue with default name/avatar

            # --- Send via Webhook ---
            webhook = None
            try:
                webhooks = await post_channel.webhooks()
                # Reuse existing webhook managed by the bot if possible
                webhook = next((wh for wh in webhooks if wh.user and wh.user.id == self.bot.user.id), None)
                if not webhook:
                    # Create if not found (ensure bot has Manage Webhooks perm)
                    webhook_name = f"{self.bot.user.name} Bets" # Or use bot_name_mask
                    webhook = await post_channel.create_webhook(name=webhook_name[:100]) # Limit name length
                logger.debug(f"Using webhook: {webhook.name} (ID: {webhook.id}) in channel {post_channel_id}")
            except discord.Forbidden:
                logger.error(f"Permission error: Cannot manage webhooks in channel {post_channel_id}.")
                raise ValueError("Bot lacks permission to manage webhooks.")
            except discord.HTTPException as e:
                logger.error(f"HTTP error managing webhook for channel {post_channel_id}: {e}")
                raise ValueError(f"Failed to setup webhook: {e}")

            # Send the message
            content = role_mention if role_mention else "" # Only include content if role exists
            try:
                sent_message = await webhook.send(
                    content=content,
                    file=discord_file,
                    username=display_name[:80], # Limit username length
                    avatar_url=avatar_url, # Can be None
                    wait=True # Wait for message confirmation from Discord
                )
                logger.info(f"Bet slip image sent for bet {bet_serial}, message ID: {sent_message.id}")
            except discord.Forbidden:
                logger.error(f"Webhook send failed due to permissions in channel {post_channel_id}.")
                raise ValueError("Bot lacks permission to send messages via webhook.")
            except discord.HTTPException as e:
                logger.error(f"Webhook send failed for bet {bet_serial}: {e}")
                raise ValueError(f"Failed to send webhook message: {e}")

            # --- Track Message for Reactions ---
            if sent_message and hasattr(self.bot.bet_service, 'pending_reactions'):
                # Store relevant info for reaction handling
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial,
                    'user_id': interaction.user.id,
                    'guild_id': interaction.guild_id,
                    'channel_id': post_channel_id,
                    'line': details.get('line'),
                    'league': details.get('league'),
                    'bet_type': 'straight' # Store bet type
                }
                logger.debug(f"Added message {sent_message.id} to pending_reactions for bet {bet_serial}")

            # --- Final Confirmation Message ---
            # Edit the original interaction followup
            await self.edit_message(
                interaction,
                content=f"✅ Bet placed successfully! (ID: `{bet_serial}`). Posted to {post_channel.mention}.",
                view=None # Remove view
            )

        except (ValidationError, BetServiceError, ValueError) as e:
            logger.error(f"Error submitting bet {bet_serial}: {e}")
            await self.edit_message(interaction, content=f"❌ Error placing bet: {e}", view=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting bet {bet_serial}: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred while posting the bet.", view=None)
        finally:
            # Clean up resources
            if self.preview_image_bytes:
                self.preview_image_bytes.close()
                self.preview_image_bytes = None
            self.stop() # Stop the view

# Setup function for the cog
async def setup(bot: commands.Bot):
    # This file defines Views/Modals used by the 'bet' command in betting.py
    # It doesn't define a Cog itself, so the setup function might not be strictly needed
    # unless you restructure it into a Cog later.
    logger.info("StraightBetWorkflow components loaded (no Cog setup needed here)")
