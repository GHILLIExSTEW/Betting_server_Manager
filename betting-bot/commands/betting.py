# betting-bot/commands/betting.py

"""Betting command for placing bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union
from datetime import datetime, timezone

try:
    from ..utils.errors import BetServiceError, ValidationError, GameNotFoundError
    # Assuming BetResolutionView is defined elsewhere or removed if not needed here
    # from ..views.bet_resolution import BetResolutionView
    # Placeholder if view is defined elsewhere
    class BetResolutionView(View):
        def __init__(self, bet_serial: int):
            super().__init__(timeout=None)
            self.bet_serial = bet_serial
            # Add dummy buttons if not imported
            # self.add_item(Button(label="Win", custom_id=f"resolve_win_{bet_serial}"))
            # self.add_item(Button(label="Loss", custom_id=f"resolve_loss_{bet_serial}"))
            # self.add_item(Button(label="Push", custom_id=f"resolve_push_{bet_serial}"))

except ImportError:
    from utils.errors import BetServiceError, ValidationError, GameNotFoundError
    # from views.bet_resolution import BetResolutionView # Placeholder
    # Placeholder if view is defined elsewhere
    class BetResolutionView(View):
        def __init__(self, bet_serial: int):
            super().__init__(timeout=None)
            self.bet_serial = bet_serial
            # Add dummy buttons if not imported
            # self.add_item(Button(label="Win", custom_id=f"resolve_win_{bet_serial}"))
            # self.add_item(Button(label="Loss", custom_id=f"resolve_loss_{bet_serial}"))
            # self.add_item(Button(label="Push", custom_id=f"resolve_push_{bet_serial}"))


logger = logging.getLogger(__name__)

# --- UI Component Classes ---
class BetTypeSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="Straight", value="straight", description="Moneyline, over/under, or player prop"),
            SelectOption(label="Parlay", value="parlay", description="Combine multiple bets")
        ]
        super().__init__(placeholder="Select Bet Type...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['bet_type'] = self.values[0]
        logger.debug(f"Bet Type selected: {self.values[0]}")
        self.disabled = True
        # Defer first, then call go_next
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class LeagueSelect(Select):
    def __init__(self, parent_view, leagues: List[str]):
        self.parent_view = parent_view
        options = [SelectOption(label=league, value=league) for league in leagues[:24]]
        options.append(SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select League...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['league'] = self.values[0]
        logger.debug(f"League selected: {self.values[0]}")
        self.disabled = True
        # Defer first, then call go_next
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
        self.parent_view.bet_details['line_type'] = self.values[0]
        logger.debug(f"Line Type selected: {self.values[0]}")
        self.disabled = True
        # Defer first, then call go_next
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class GameSelect(Select):
    def __init__(self, parent_view, games: List[Dict]):
        self.parent_view = parent_view
        options = []
        for game in games[:24]:
            home = game.get('home_team_name', 'Unknown')
            away = game.get('away_team_name', 'Unknown')
            start_dt = game.get('start_time')
            if isinstance(start_dt, datetime):
                # Format datetime safely
                try:
                    # Attempt timezone conversion if aware, otherwise assume UTC or local
                    if start_dt.tzinfo:
                       local_time = start_dt.astimezone() # Convert to local if possible
                       time_str = local_time.strftime('%m/%d %H:%M %Z')
                    else:
                       time_str = start_dt.strftime('%m/%d %H:%M UTC?') # Indicate potentially missing timezone
                except Exception:
                    time_str = str(start_dt) # Fallback
            else:
                time_str = 'Time N/A'
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id')
            if game_api_id is None: continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id)))
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(placeholder="Select Game (or Other)...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        selected_game_id = self.values[0]
        self.parent_view.bet_details['game_id'] = selected_game_id
        self.disabled = True
        line_type = self.parent_view.bet_details.get('line_type')

        if selected_game_id == "Other":
            logger.debug("Game selected: Other (Manual Entry)")
            # Manual entry always requires the modal next
            modal = BetDetailsModal(line_type=line_type, is_manual=True)
            modal.view = self.parent_view # Pass view reference for modal's on_submit
            await interaction.response.send_modal(modal)
            # Do NOT call go_next here; modal submission will handle it
        else:
            game = next((g for g in self.parent_view.games if str(g.get('id')) == selected_game_id), None)
            if game:
                self.parent_view.bet_details['home_team_name'] = game.get('home_team_name', 'Unknown')
                self.parent_view.bet_details['away_team_name'] = game.get('away_team_name', 'Unknown')
            logger.debug(f"Game selected: {selected_game_id}")

            # Decide next step based on line_type
            if line_type == "player_prop":
                # Need to check for players next
                await interaction.response.defer()
                await self.parent_view.go_next(interaction)
            elif line_type == "game_line":
                # Game line details are needed next via modal
                modal = BetDetailsModal(line_type=line_type, is_manual=False)
                modal.view = self.parent_view
                await interaction.response.send_modal(modal)
                # Do NOT call go_next here; modal submission will handle it
            else:
                # Should not happen, but defer and proceed if it does
                logger.warning(f"Unexpected line_type '{line_type}' after game selection.")
                await interaction.response.defer()
                await self.parent_view.go_next(interaction)

class HomePlayerSelect(Select):
    def __init__(self, parent_view, players: List[str], team_name: str):
        self.parent_view = parent_view
        self.team_name = team_name
        options = [SelectOption(label=player, value=f"home_{player}") for player in players[:24]]
        if not options:
            options.append(SelectOption(label="No Players Available", value="none", emoji="❌"))
        super().__init__(placeholder=f"{team_name} Players...", options=options, min_values=0, max_values=1) # Allow zero for deselection?

    async def callback(self, interaction: Interaction):
        # Disable the other player select
        for item in self.parent_view.children:
            if isinstance(item, AwayPlayerSelect):
                item.disabled = True
            if isinstance(item, Select): # Disable self too
                 item.disabled = True

        if self.values and self.values[0] != "none":
            player_name = self.values[0].replace("home_", "")
            self.parent_view.bet_details['player'] = player_name
            logger.debug(f"Home player selected: {player_name}")
            # Player selected, proceed to modal for line/odds/units
            modal = BetDetailsModal(line_type="player_prop", is_manual=False)
            # Pre-fill player if desired, or let user confirm/enter in modal
            # modal.player.default_value = player_name # If TextInput is added
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            # Do NOT call go_next here
        else:
            # No player selected or "None" selected
            self.parent_view.bet_details['player'] = None
            logger.debug("Home player selection: None or deselected")
            # Need to handle this - perhaps re-enable selects or show error?
            # For now, just edit the message. Doesn't proceed.
            await interaction.response.edit_message(content="Please select a player or cancel.", view=self.parent_view)


class AwayPlayerSelect(Select):
    def __init__(self, parent_view, players: List[str], team_name: str):
        self.parent_view = parent_view
        self.team_name = team_name
        options = [SelectOption(label=player, value=f"away_{player}") for player in players[:24]]
        if not options:
            options.append(SelectOption(label="No Players Available", value="none", emoji="❌"))
        super().__init__(placeholder=f"{team_name} Players...", options=options, min_values=0, max_values=1)

    async def callback(self, interaction: Interaction):
        # Disable the other player select
        for item in self.parent_view.children:
            if isinstance(item, HomePlayerSelect):
                item.disabled = True
            if isinstance(item, Select): # Disable self too
                 item.disabled = True

        if self.values and self.values[0] != "none":
            player_name = self.values[0].replace("away_", "")
            self.parent_view.bet_details['player'] = player_name
            logger.debug(f"Away player selected: {player_name}")
            # Player selected, proceed to modal for line/odds/units
            modal = BetDetailsModal(line_type="player_prop", is_manual=False)
            # Pre-fill player if desired
            # modal.player.default_value = player_name # If TextInput is added
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
             # Do NOT call go_next here
        else:
            # No player selected or "None" selected
            self.parent_view.bet_details['player'] = None
            logger.debug("Away player selection: None or deselected")
            # Need to handle this - perhaps re-enable selects or show error?
            # For now, just edit the message. Doesn't proceed.
            await interaction.response.edit_message(content="Please select a player or cancel.", view=self.parent_view)


class ManualEntryButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.green, label="Manual Entry", custom_id=f"manual_entry_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug("Manual Entry button clicked (from no games found)")
        self.parent_view.bet_details['game_id'] = "Other"
        line_type = self.parent_view.bet_details.get('line_type')

        # Send the modal directly
        modal = BetDetailsModal(line_type=line_type, is_manual=True)
        modal.view = self.parent_view # Pass view reference
        await interaction.response.send_modal(modal)
        # Do NOT call go_next here

class ManualPlayerEntryButton(Button):
    """Button shown when player prop is selected but player data is unavailable."""
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.primary, label="Enter Player Details Manually", custom_id=f"manual_player_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug("Manual Player Entry button clicked")
        line_type = self.parent_view.bet_details.get('line_type') # Should be player_prop
        # Send the modal, is_manual=False because game was selected, just no player data
        modal = BetDetailsModal(line_type=line_type, is_manual=False)
        modal.view = self.parent_view # Pass view reference
        await interaction.response.send_modal(modal)
        # Do NOT call go_next here

class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.red, label="Cancel", custom_id=f"cancel_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug("Cancel button clicked")
        self.disabled = True
        # Disable all other components in the view
        for item in self.parent_view.children:
             if hasattr(item, 'disabled'):
                 item.disabled = True
        # Respond to the interaction before stopping the view
        try:
            # Use edit_message if possible, otherwise followup
            if not interaction.response.is_done():
                await interaction.response.edit_message(content="Bet workflow cancelled.", view=None, embed=None)
            else:
                await interaction.followup.send("Bet workflow cancelled.", ephemeral=True)
                # Try to delete the original ephemeral message if possible
                if self.parent_view.message:
                    await self.parent_view.message.delete()

        except discord.HTTPException as e:
             logger.warning(f"Failed to edit/send cancel message: {e}")
        finally:
            self.parent_view.stop() # Stop the view listener


class BetDetailsModal(Modal, title="Enter Bet Details"):
    # Add player TextInput conditional on is_manual=False and line_type=player_prop
    player: TextInput = TextInput(
        label="Player",
        placeholder="Enter player name (e.g., LeBron James)",
        required=False, # Required is handled dynamically
        max_length=100
    )
    team: TextInput = TextInput(
        label="Team",
        placeholder="e.g., Lakers",
        required=False, # Required is handled dynamically
        max_length=100
    )
    opponent: TextInput = TextInput(
        label="Opponent / Info", # Make generic label
        placeholder="e.g., Celtics or Player Name if Prop",
        required=False, # Required is handled dynamically
        max_length=100
    )
    line: TextInput = TextInput(
        label="Line",
        placeholder="e.g., -7.5, Over 220.5, Player Points Over 25.5",
        required=True,
        max_length=100,
        style=discord.TextStyle.short
    )
    odds: TextInput = TextInput(
        label="Odds (American)",
        placeholder="e.g., -110, +150",
        required=True,
        max_length=10
    )
    units: TextInput = TextInput(
        label="Units (e.g., 1, 1.5)",
        placeholder="Enter units to risk (0.1-10.0)",
        required=True,
        max_length=5
    )

    def __init__(self, line_type: str, is_manual: bool = False):
        super().__init__(title="Enter Bet Details")
        self.line_type = line_type
        self.is_manual = is_manual
        # Keep a reference to the parent view
        self.view: Optional[BetWorkflowView] = None

        # --- Clear existing items (important if reusing class instance) ---
        # self.clear_items() # This doesn't exist for Modals, needs manual removal if items were added conditionally before super().__init__

        # --- Conditionally Add Items ---
        if is_manual:
            self.team.required = True
            self.opponent.required = True
            self.opponent.label = "Opponent" if line_type == "game_line" else "Player"
            self.add_item(self.team)
            self.add_item(self.opponent)
        elif line_type == "player_prop":
             # If it's NOT manual entry but IS a player prop, we need player name
            self.player.required = True
            self.add_item(self.player)

        # Always add these
        self.add_item(self.line)
        self.add_item(self.odds)
        self.add_item(self.units)


    async def on_submit(self, interaction: Interaction):
        # Defer immediately to prevent timeout issues if validation is slow
        # We use followup later if needed.
        await interaction.response.defer(ephemeral=True, thinking=True)

        logger.debug(f"BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual}")

        # --- Extract and Validate ---
        try:
            line = self.line.value.strip()
            odds_str = self.odds.value.strip()
            units_str = self.units.value.strip()

            if not line: raise ValidationError("Line cannot be empty.")
            if not odds_str: raise ValidationError("Odds cannot be empty.")
            if not units_str: raise ValidationError("Units cannot be empty.")

            # Validate and Convert Odds
            try:
                odds_str_cleaned = odds_str.replace('+','').strip()
                odds_val = int(odds_str_cleaned)
                if not (-100000 <= odds_val <= 100000): # Wider range
                     raise ValueError("Odds must be a reasonable integer (e.g., -110, +150).")
                if -100 < odds_val < 100:
                     raise ValueError("Odds cannot be between -99 and +99.")
            except ValueError as e:
                 raise ValidationError(f"Invalid Odds: {e}. Use American format (e.g., -110, +150).")

            # Validate and Convert Units
            try:
                units_str_cleaned = units_str.lower().replace('u','').strip()
                units_val = float(units_str_cleaned)
                # Revisit unit limits if necessary
                if not (0.01 <= units_val <= 100.0): # Example: Allow smaller units, larger max?
                    raise ValueError("Units must be between 0.01 and 100.0.")
            except ValueError as e:
                raise ValidationError(f"Invalid Units: {e}. Use a number (e.g., 1, 0.5, 2).")

            # --- Build Leg ---
            leg = {
                'line': line,
                'odds_str': odds_str, # Keep original string for display if needed
                'units_str': units_str, # Keep original string
                'odds': float(odds_val), # Store validated float
                'units': units_val,    # Store validated float
            }

            # Add manual/player details
            if self.is_manual:
                team = self.team.value.strip()
                opponent = self.opponent.value.strip() # Use the generic name from init
                if not team: raise ValidationError("Team cannot be empty for manual entry.")
                if not opponent: raise ValidationError(f"{self.opponent.label} cannot be empty for manual entry.")
                leg['team'] = team
                if self.line_type == "game_line":
                    leg['opponent'] = opponent # Store opponent for game line
                else: # player_prop
                    leg['player'] = opponent # Store player name entered manually
            elif self.line_type == "player_prop":
                # Player name from the dedicated TextInput
                player = self.player.value.strip()
                if not player: raise ValidationError("Player name cannot be empty for player prop.")
                leg['player'] = player
                # Try to associate with team if game was selected
                if self.view and self.view.bet_details.get('game_id') != 'Other':
                     # This requires more complex logic to determine which team the player is on
                     # For now, we might not have a team name readily available here easily
                     # It might be better to add team association during final embed creation or DB storage
                     pass


            # --- Add Leg to View's Details ---
            if not self.view:
                 logger.error("Modal has no reference to parent view.")
                 await interaction.followup.send("❌ Internal error: Modal lost connection to the workflow. Please try again.", ephemeral=True)
                 return

            if 'legs' not in self.view.bet_details:
                self.view.bet_details['legs'] = []

            # For straight bets, replace the leg; for parlays, append
            if self.view.bet_details.get('bet_type') == 'straight':
                 self.view.bet_details['legs'] = [leg] # Overwrite if it exists
            else: # Parlay
                 self.view.bet_details['legs'].append(leg)

            logger.debug(f"Bet leg details processed: {leg}")

            # --- Proceed in Workflow ---
            # Pass the *modal's interaction* to go_next
            await self.view.go_next(interaction)
            # Send a confirmation that modal was processed before go_next edits the message
            # await interaction.followup.send("✅ Details received.", ephemeral=True) # Optional feedback

        except ValidationError as ve:
             logger.warning(f"Modal validation failed: {ve}")
             await interaction.followup.send(f"❌ Validation Error: {ve}", ephemeral=True)
             # Do NOT proceed. The modal stays open for user correction (or they cancel).
        except Exception as e:
            logger.exception(f"Error processing BetDetailsModal submission: {e}")
            await interaction.followup.send("❌ An unexpected error occurred processing the details.", ephemeral=True)
            if self.view:
                self.view.stop() # Stop the workflow on unexpected errors

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            # Use followup as response might be deferred/used
            await interaction.followup.send('❌ An error occurred within the bet details form.', ephemeral=True)
        except discord.HTTPException:
            logger.warning("Could not send error followup for BetDetailsModal.")
        if self.view:
             self.view.stop()


class ChannelSelect(Select):
    def __init__(self, parent_view, channels: List[TextChannel]):
        self.parent_view = parent_view
        options = [SelectOption(label=f"#{channel.name}", value=str(channel.id)) for channel in channels[:25]]
        if not options:
            options.append(SelectOption(label="No Writable Channels Found", value="none", emoji="❌"))
        super().__init__(placeholder="Select Channel to Post Bet...", options=options, min_values=1, max_values=1, disabled=not options or options[0].value == "none")

    async def callback(self, interaction: Interaction):
        selected_value = self.values[0]
        if selected_value == "none":
            await interaction.response.defer() # Acknowledge interaction
            return # Do nothing if no channel selected

        self.parent_view.bet_details['channel_id'] = int(selected_value)
        logger.debug(f"Channel selected: {selected_value}")
        self.disabled = True
        # Defer first, then call go_next
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class AddLegButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.blurple, label="Add Another Leg", custom_id=f"add_leg_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        # Reset workflow to add another leg (e.g., back to league selection)
        self.parent_view.current_step = 1 # Go back to Step 2 (League Select)
        logger.debug("Add Leg button clicked, resetting to step 1 (will increment to 2)")
        await interaction.response.defer()
        await self.parent_view.go_next(interaction) # This will increment step to 2

class ConfirmButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.green, label="Confirm & Post Bet", custom_id=f"confirm_bet_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug("Confirm button clicked")
        # Disable buttons immediately
        for item in self.parent_view.children:
            if isinstance(item, Button): item.disabled = True
        # Edit message to show processing state
        await interaction.response.edit_message(content="Confirming and submitting bet...", view=self.parent_view, embed=None) # Clear embed during processing
        # Call the final submission logic
        await self.parent_view.submit_bet(interaction)


# --- Main Workflow View ---

class BetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600) # 10 minute timeout
        self.original_interaction = interaction
        self.bot = bot
        self.current_step = 0
        # Initialize bet_details safely
        self.bet_details: Dict[str, Union[str, int, float, List[Dict]]] = {'legs': []}
        self.games: List[Dict] = [] # Store games fetched for the league
        self.message: Optional[Union[discord.WebhookMessage, discord.InteractionMessage]] = None
        self.is_processing = False # Lock to prevent race conditions
        self.latest_interaction: Interaction = interaction # Track the interaction for editing messages

    async def start_flow(self):
        logger.debug("Starting bet workflow")
        try:
             # Send the initial message (ephemeral)
            await self.original_interaction.followup.send(
                 "Starting bet placement...", view=self, ephemeral=True
             )
             # Get the message object for later edits
             self.message = await self.original_interaction.original_response()
             # Trigger the first step
             await self.go_next(self.original_interaction) # Pass the original interaction
        except discord.HTTPException as e:
             logger.error(f"Failed to send initial workflow message: {e}")
             try:
                  # Try followup if original response failed or wasn't captured
                  await self.original_interaction.followup.send("❌ Failed to start bet workflow. Please try again.", ephemeral=True)
             except discord.HTTPException:
                  logger.error("Failed even to send error followup.") # Log secondary failure
        except Exception as e:
            logger.exception(f"Unexpected error in start_flow: {e}")
            await self.original_interaction.followup.send("❌ An unexpected error occurred starting the workflow.", ephemeral=True)


    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("⛔ You cannot interact with this betting session.", ephemeral=True)
            return False
        # Update latest interaction for message editing
        self.latest_interaction = interaction
        return True

    async def on_timeout(self):
        logger.info(f"Bet workflow timed out for user {self.original_interaction.user.id}")
        if self.message:
             try:
                  await self.edit_message(content="Bet workflow timed out. Please start again.", view=None, embed=None)
             except (discord.NotFound, discord.HTTPException):
                  logger.warning("Failed to edit message on timeout (message might be deleted).")
        self.stop()

    async def edit_message(self, content: Optional[str] = None, view: Optional[View] = None, embed: Optional[discord.Embed] = None):
        """Helper to edit the workflow message."""
        logger.debug(f"Attempting edit: content={'Yes' if content else 'No'}, view={'Yes' if view else 'No'}, embed={'Yes' if embed else 'No'}")
        target_message = self.message
        if not target_message:
             # Try to fetch the original response if message object was lost
             try:
                  target_message = await self.original_interaction.original_response()
                  self.message = target_message # Store it again
             except (discord.NotFound, discord.HTTPException):
                  logger.warning("Cannot edit message: Original response not found or inaccessible.")
                  # Maybe try sending a followup from the latest interaction?
                  # await self.latest_interaction.followup.send(...) # Be careful with state
                  return # Cannot edit

        try:
             current_view = view if view is not None else self # Keep current view if None is passed unless explicitly clearing
             if view is None and content and "cancelled" in content.lower() or "timed out" in content.lower() or "error" in content.lower() or "submitted" in content.lower():
                  current_view = None # Clear view on final states or errors

             await target_message.edit(content=content, embed=embed, view=current_view)
             logger.debug("Message edit successful.")
        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Failed to edit BetWorkflowView message: {e} (Perhaps message was deleted or interaction expired?)")
            # Consider sending a followup if critical, but might be noisy
            # if self.latest_interaction and not self.latest_interaction.response.is_done():
            #    await self.latest_interaction.followup.send("Error updating workflow message.", ephemeral=True)
        except Exception as e:
            logger.exception(f"Unexpected error editing BetWorkflowView message: {e}")


    async def go_next(self, interaction: Interaction):
        """Advances the workflow to the next step. Called by component callbacks or modal submit."""
        if self.is_processing:
            logger.debug(f"go_next called while already processing step {self.current_step}. Aborting.")
            # If interaction is not deferred, acknowledge it to prevent failure state
            if not interaction.response.is_done():
                await interaction.response.defer()
            return

        self.is_processing = True
        try:
            # The interaction passed here might already be deferred or responded to (e.g., modal submit)
            logger.debug(f"Processing go_next: current_step={self.current_step}, interaction type={type(interaction)}, response_done={interaction.response.is_done()}")

            self.current_step += 1
            step_content = f"**Step {self.current_step}**"
            embed_to_send: Optional[discord.Embed] = None
            next_view = View(timeout=self.timeout) # Create a new view for the next step's components

            logger.debug(f"Advancing to step {self.current_step}")

            # --- Determine components for the new step ---
            if self.current_step == 1:
                next_view.add_item(BetTypeSelect(self))
                step_content += ": Select Bet Type"
            elif self.current_step == 2:
                # Fetch allowed leagues (maybe from config or DB later)
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                next_view.add_item(LeagueSelect(self, allowed_leagues))
                step_content += ": Select League"
            elif self.current_step == 3:
                next_view.add_item(LineTypeSelect(self))
                step_content += ": Select Line Type"
            elif self.current_step == 4:
                # Select Game (or Manual Entry Button if no games)
                league = self.bet_details.get('league')
                self.games = [] # Reset games list
                if league and league != "Other" and hasattr(self.bot, 'game_service'):
                     try:
                          # Fetch games for the selected league
                          # This might need refinement based on how game_service works
                          all_upcoming = await self.bot.game_service.get_upcoming_games(interaction.guild_id, hours=72)
                          # Filter by league name/ID (adjust filtering as needed)
                          self.games = [
                              g for g in all_upcoming
                              if str(g.get('league_id')) == league or g.get('league_name','').lower() == league.lower()
                          ]
                          logger.debug(f"Found {len(self.games)} games for league {league}")
                     except Exception as e:
                          logger.exception(f"Failed to fetch games for league {league}: {e}")
                          self.games = [] # Ensure games is empty on error

                if self.games:
                    next_view.add_item(GameSelect(self, self.games))
                    step_content += f": Select Game for {league}"
                else:
                    step_content = f"⚠️ No upcoming games found for {league} in the next 72 hours."
                    step_content += "\nYou can manually enter the details."
                    next_view.add_item(ManualEntryButton(self)) # Button callback sends modal
                    next_view.add_item(CancelButton(self))
            elif self.current_step == 5:
                # This step is now primarily for Player Selection if needed,
                # as modal submission for manual/game lines skips this.
                line_type = self.bet_details.get('line_type')
                game_id = self.bet_details.get('game_id')
                is_manual = game_id == "Other"

                if line_type == "player_prop" and not is_manual:
                    # This step is reached after selecting a specific game for a player prop
                    logger.debug(f"Fetching players for game {game_id}")
                    players_data = {}
                    home_players, away_players = [], []
                    if hasattr(self.bot, 'game_service'):
                         try:
                              players_data = await self.bot.game_service.get_game_players(game_id)
                              home_players = players_data.get('home_players', [])
                              away_players = players_data.get('away_players', [])
                         except GameNotFoundError:
                              logger.warning(f"Game {game_id} not found when fetching players.")
                         except Exception as e:
                              logger.exception(f"Error fetching players for game {game_id}: {e}")

                    if home_players or away_players:
                        home_team = self.bet_details.get('home_team_name', 'Home Team')
                        away_team = self.bet_details.get('away_team_name', 'Away Team')
                        step_content += f": Select Player ({away_team} @ {home_team})"
                        if home_players:
                            next_view.add_item(HomePlayerSelect(self, home_players, home_team))
                        if away_players:
                            next_view.add_item(AwayPlayerSelect(self, away_players, away_team))
                        next_view.add_item(CancelButton(self)) # Add cancel here too
                    else:
                        logger.warning(f"No player data found for game {game_id}. Prompting manual player entry.")
                        step_content = f"⚠️ Player data not available for the selected game."
                        step_content += "\nYou can manually enter the player and bet details."
                        next_view.add_item(ManualPlayerEntryButton(self)) # Button callback sends modal
                        next_view.add_item(CancelButton(self))
                else:
                     # This step should be skipped if a modal was shown in step 4
                     # Or if it was a player prop where player was selected (modal sent)
                     # If we reach here unexpectedly, log it and maybe cancel.
                     logger.error(f"Reached Step 5 unexpectedly. Details: {self.bet_details}")
                     step_content = "An unexpected error occurred in the workflow. Cancelling."
                     self.stop() # Stop the view
                     next_view = None # Clear view

            elif self.current_step == 6:
                # Channel Selection (Reached after modal submission)
                 if not self.bet_details.get('legs'):
                      logger.error("Reached step 6 (Channel Select) but no bet legs found.")
                      step_content = "❌ Error: No bet details were entered. Cancelling workflow."
                      self.stop()
                      next_view = None
                 else:
                    channels = []
                    guild = interaction.guild # Use the interaction's guild
                    if not guild:
                        logger.error("Cannot get guild from interaction in step 6.")
                        step_content = "❌ Error: Could not identify the server. Cancelling."
                        self.stop()
                        next_view = None
                    else:
                        # Fetch configured channels or scan permissible channels
                        if hasattr(self.bot, 'db_manager'):
                            try:
                                settings = await self.bot.db_manager.fetch_one(
                                    "SELECT embed_channel_1, embed_channel_2 FROM server_settings WHERE guild_id = %s",
                                    (guild.id,)
                                )
                                if settings:
                                    for channel_id_str in [settings.get('embed_channel_1'), settings.get('embed_channel_2')]:
                                        if channel_id_str:
                                            try:
                                                 channel_id = int(channel_id_str)
                                                 channel = guild.get_channel(channel_id)
                                                 if channel and isinstance(channel, TextChannel) and channel.permissions_for(guild.me).send_messages:
                                                     if channel not in channels: # Avoid duplicates
                                                         channels.append(channel)
                                            except (ValueError, TypeError):
                                                 logger.warning(f"Invalid channel ID '{channel_id_str}' in settings for guild {guild.id}")
                            except Exception as e:
                                logger.exception(f"Error fetching channel settings from DB: {e}")

                        # Fallback or supplement with generally available channels if needed/allowed
                        if not channels: # Only scan if no specific channels were found/configured
                            logger.debug("No specific channels configured or found, scanning channels user/bot can write to.")
                            channels = sorted(
                                [ch for ch in guild.text_channels if ch.permissions_for(interaction.user).send_messages and ch.permissions_for(guild.me).send_messages],
                                key=lambda c: c.position
                            )[:25] # Limit results

                        if not channels:
                            step_content = "❌ Error: No suitable text channels found for posting the bet."
                            self.stop()
                            next_view = None
                        else:
                            next_view.add_item(ChannelSelect(self, channels))
                            next_view.add_item(CancelButton(self))
                            embed_to_send = self.create_preview_embed() # Show preview before channel select
                            step_content += ": Select Channel to Post Bet"

            elif self.current_step == 7:
                # Confirmation Step (Reached after channel selection)
                if not self.bet_details.get('legs') or not self.bet_details.get('channel_id'):
                     logger.error(f"Reached step 7 (Confirmation) but missing legs or channel_id. Details: {self.bet_details}")
                     step_content = "❌ Error: Missing bet details or channel selection. Cancelling."
                     self.stop()
                     next_view = None
                else:
                    try:
                         # Final validation (redundant check on odds/units if modal did it, but safe)
                        legs = self.bet_details.get('legs', [])
                        if self.bet_details.get('bet_type') == "parlay" and len(legs) < 2:
                             raise ValidationError("Parlay bets require at least two legs.")
                        # Basic check if odds/units exist from modal processing
                        for i, leg in enumerate(legs):
                            if 'odds' not in leg or 'units' not in leg:
                                raise ValidationError(f"Leg {i+1} is missing processed odds or units.")

                        embed_to_send = self.create_confirmation_embed()
                        next_view.add_item(ConfirmButton(self)) # Confirm -> submit_bet
                        if self.bet_details.get('bet_type') == "parlay":
                             next_view.add_item(AddLegButton(self)) # Add another leg
                        next_view.add_item(CancelButton(self)) # Cancel
                        step_content += ": Please Confirm Your Bet Details"

                    except ValidationError as ve:
                        logger.error(f"Validation failed at confirmation step: {ve}")
                        step_content = f"❌ Error: {ve}. Cancelling workflow."
                        self.stop()
                        next_view = None
                    except Exception as e:
                         logger.exception(f"Unexpected error during confirmation step build: {e}")
                         step_content = "❌ An unexpected error occurred. Cancelling workflow."
                         self.stop()
                         next_view = None

            else:
                # Should not happen - indicates workflow finished or error
                logger.info(f"Bet workflow reached end state or unexpected step > 7. Stopping. Details: {self.bet_details}")
                step_content = "✅ Bet workflow finished or cancelled." # Adjust message as needed
                self.stop()
                next_view = None

            # --- Update the Message ---
            # Use the helper to edit the persistent message
            if not self.is_stopped(): # Don't try to edit if view was stopped
                 await self.edit_message(content=step_content, view=next_view, embed=embed_to_send)

        except Exception as e:
            logger.exception(f"Error processing workflow step {self.current_step}: {e}")
            await self.edit_message(content="❌ An unexpected error occurred. Cancelling workflow.", view=None, embed=None)
            self.stop()
        finally:
            self.is_processing = False # Release the lock

    # --- Embed Creation Methods ---
    # (Keep create_preview_embed, create_confirmation_embed, create_final_bet_embed as they are,
    # but ensure they handle the data structure correctly, especially 'player', 'team', 'opponent' in legs)

    def _get_leg_display_info(self, leg: Dict) -> str:
        """Helper to format leg info for embeds."""
        selection = leg.get('line', 'N/A')
        player = leg.get('player')
        # If player exists, prepend it. Use team/opponent if manual and no specific player.
        if player:
             prefix = f"{player} - "
             # Try to add team context if available (might need refinement)
             # team = leg.get('team')
             # if team: prefix = f"{team} / {prefix}"
        elif leg.get('team'): # Manual entry might have team/opponent instead of player
             prefix = f"{leg['team']} - " # Use team name as prefix? Or Opponent?
             # opponent = leg.get('opponent')
             # if opponent: prefix += f"vs {opponent} - " # Needs better formatting decision
        else:
             prefix = ""

        return f"{prefix}{selection}"

    def create_preview_embed(self) -> discord.Embed:
        details = self.bet_details
        bet_type = details.get('bet_type', 'N/A').title()
        embed = discord.Embed(title=f"📊 Bet Preview ({bet_type})", color=discord.Color.blue())

        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)

        # Game Info
        game_id = details.get('game_id')
        home = details.get('home_team_name')
        away = details.get('away_team_name')
        if game_id and game_id != 'Other' and home and away:
            game_info = f"{away} @ {home}"
        elif game_id == 'Other' and details.get('legs'):
            first_leg = details['legs'][0]
            team = first_leg.get('team')
            opponent = first_leg.get('opponent')
            player = first_leg.get('player')
            if player: # Manual player prop
                 game_info = f"Manual Entry ({player})"
            elif team and opponent : # Manual game line
                 game_info = f"Manual: {team} vs {opponent}"
            elif team:
                 game_info = f"Manual: {team}"
            else:
                 game_info = "Manual Entry"
        else:
             game_info = details.get('league', 'N/A') # Fallback to league

        embed.add_field(name="Matchup / Entry", value=game_info, inline=True)
        embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer

        legs = details.get('legs', [])
        for i, leg in enumerate(legs, 1):
            selection_info = self._get_leg_display_info(leg)
            embed.add_field(
                 name=f"Leg {i} Selection" if len(legs) > 1 else "Selection",
                 value=f"```{selection_info[:1000]}```", # Use helper
                 inline=False
            )
            # Show raw strings entered by user in preview
            embed.add_field(name="Odds", value=f"{leg.get('odds_str', 'N/A')}", inline=True)
            embed.add_field(name="Units", value=f"{leg.get('units_str', 'N/A')}u", inline=True)
            embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer

        embed.set_footer(text="Select a channel below to post the bet.")
        return embed

    def create_confirmation_embed(self) -> discord.Embed:
        details = self.bet_details
        bet_type = details.get('bet_type', 'N/A').title()
        embed = discord.Embed(title=f"✅ Confirm Bet ({bet_type})", color=discord.Color.green())

        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)

        # Game Info (Similar logic to preview)
        game_id = details.get('game_id')
        home = details.get('home_team_name')
        away = details.get('away_team_name')
        if game_id and game_id != 'Other' and home and away:
            game_info = f"{away} @ {home}"
        elif game_id == 'Other' and details.get('legs'):
             first_leg = details['legs'][0]
             team = first_leg.get('team')
             opponent = first_leg.get('opponent')
             player = first_leg.get('player')
             if player: game_info = f"Manual Entry ({player})"
             elif team and opponent : game_info = f"Manual: {team} vs {opponent}"
             elif team: game_info = f"Manual: {team}"
             else: game_info = "Manual Entry"
        else:
             game_info = details.get('league', 'N/A')

        embed.add_field(name="Matchup / Entry", value=game_info, inline=True)

        # Channel Info
        channel_id = details.get('channel_id')
        channel = self.bot.get_channel(channel_id) if channel_id else None
        channel_mention = channel.mention if channel else "Invalid/Not Found"
        embed.add_field(name="Post Channel", value=channel_mention, inline=True)

        legs = details.get('legs', [])
        total_units_risked = 0.0
        # For parlays, calculate combined odds first
        parlay_decimal_odds = 1.0
        parlay_units = 0.0 # Assume parlay units are on the first leg? Or need separate field?
                          # For now, assume units on first leg apply to whole parlay if parlay type

        if bet_type == "Parlay" and legs:
            parlay_units = legs[0].get('units', 0.0) # Use first leg's units for the parlay risk
            total_units_risked = parlay_units
            for leg in legs:
                 odds_value = leg.get('odds', 0.0)
                 if odds_value > 0:
                      decimal = (odds_value / 100.0) + 1.0
                 elif odds_value < 0:
                      decimal = (100.0 / abs(odds_value)) + 1.0
                 else: decimal = 1.0 # Should not happen with validation
                 parlay_decimal_odds *= decimal
            # Convert final decimal back to American odds for display (optional)
            if parlay_decimal_odds >= 2.0:
                 parlay_american_odds = (parlay_decimal_odds - 1.0) * 100.0
            else:
                 parlay_american_odds = -100.0 / (parlay_decimal_odds - 1.0)

        # Display Legs
        for i, leg in enumerate(legs, 1):
            selection_info = self._get_leg_display_info(leg) # Use helper
            embed.add_field(
                 name=f"Leg {i} Selection" if len(legs) > 1 else "Selection",
                 value=f"```{selection_info[:1000]}```",
                 inline=False
            )
            odds_value = leg.get('odds', 0.0)
            units_value = leg.get('units', 0.0)
            # Show processed/validated values
            embed.add_field(name="Odds", value=f"{odds_value:+}", inline=True)
            if bet_type != "Parlay": # Only show units per leg for straights
                 embed.add_field(name="Risk", value=f"{units_value:.2f}u", inline=True)
                 total_units_risked += units_value # Sum units for straights
            else: # For Parlay, show leg odds, but total risk/win is calculated once
                 embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer if not showing units

            embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer


        # Calculate Total Win/Payout based on type
        total_potential_profit = 0.0
        if bet_type == "Parlay" and parlay_units > 0:
             total_potential_profit = parlay_units * (parlay_decimal_odds - 1.0)
             embed.add_field(name="Parlay Odds", value=f"{parlay_american_odds:+.0f}", inline=True)
             embed.add_field(name="Total Risk", value=f"{parlay_units:.2f}u", inline=True)
        elif bet_type == "Straight" and legs:
             # Sum potential profit for each straight leg
             for leg in legs: # Should only be one leg, but loop defensively
                 odds_value = leg.get('odds', 0.0)
                 units_value = leg.get('units', 0.0)
                 if units_value > 0:
                     if odds_value > 0:
                         total_potential_profit += units_value * (odds_value / 100.0)
                     elif odds_value < 0:
                         total_potential_profit += units_value * (100.0 / abs(odds_value))
             embed.add_field(name="Total Risk", value=f"{total_units_risked:.2f}u", inline=True)


        embed.add_field(name="To Win", value=f"{total_potential_profit:.2f}u", inline=True)
        # embed.add_field(name="Total Payout", value=f"{total_units_risked + total_potential_profit:.2f}u", inline=True)

        footer_text = "Click Confirm to place and post the bet."
        if bet_type == "Parlay": footer_text += " Or add another leg."
        embed.set_footer(text=footer_text)
        return embed


    def create_final_bet_embed(self, bet_serial: int) -> discord.Embed:
        details = self.bet_details
        user = self.original_interaction.user
        bet_type = details.get('bet_type', 'Bet').title()

        # Determine Embed Title based on user context
        is_multi_team_parlay = False
        if bet_type == "Parlay":
             teams = set()
             legs = details.get('legs', [])
             if len(legs) > 1:
                  for leg in legs:
                       # Attempt to find a team name associated with the leg
                       team_name = leg.get('team') # Primarily from manual entry
                       if not team_name: # If not manual, try using game context
                            if details.get('game_id') != 'Other':
                                 # This is tricky - need to know if the bet was on home or away
                                 # or which team a player prop belongs to. Requires more context.
                                 # Simplification: Use home/away names if available
                                 if details.get('home_team_name'): teams.add(details['home_team_name'])
                                 if details.get('away_team_name'): teams.add(details['away_team_name'])
                            else: # Manual entry without team? Fallback needed
                                 pass # Cannot determine team easily
                       elif team_name:
                            teams.add(team_name)

                  if len(teams) > 1:
                       is_multi_team_parlay = True

        # Use specific title based on user context
        if is_multi_team_parlay:
             embed_title = "Multi-Team Parlay Bet" # As per user context
        elif bet_type == "Parlay":
             embed_title = "Parlay Bet" # Single game/team parlay
        else:
             embed_title = f"{bet_type} Bet" # Straight Bet

        embed = discord.Embed(title=f"🚨 {embed_title}", color=discord.Color.gold()) # Use gold for pending
        embed.set_author(name=f"{user.display_name}'s Pick", icon_url=user.display_avatar.url if user.display_avatar else None)

        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)

        # Game Info (reuse logic, ensure accuracy)
        game_id = details.get('game_id')
        home = details.get('home_team_name')
        away = details.get('away_team_name')
        if game_id and game_id != 'Other' and home and away:
            game_info = f"{away} @ {home}"
        elif game_id == 'Other' and details.get('legs'):
             first_leg = details['legs'][0]
             team = first_leg.get('team')
             opponent = first_leg.get('opponent')
             player = first_leg.get('player')
             if player: game_info = f"Manual Entry ({player})"
             elif team and opponent : game_info = f"Manual: {team} vs {opponent}"
             elif team: game_info = f"Manual: {team}"
             else: game_info = "Manual Entry"
        else:
             game_info = details.get('league', 'N/A')

        embed.add_field(name="Matchup", value=game_info, inline=True)
        embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer

        # --- Legs & Calculation (Similar to Confirmation Embed) ---
        legs = details.get('legs', [])
        total_units_risked = 0.0
        parlay_decimal_odds = 1.0
        parlay_units = 0.0

        if bet_type == "Parlay" and legs:
            parlay_units = legs[0].get('units', 0.0)
            total_units_risked = parlay_units
            for leg in legs:
                 odds_value = leg.get('odds', 0.0)
                 if odds_value > 0: decimal = (odds_value / 100.0) + 1.0
                 elif odds_value < 0: decimal = (100.0 / abs(odds_value)) + 1.0
                 else: decimal = 1.0
                 parlay_decimal_odds *= decimal
            if parlay_decimal_odds >= 2.0: parlay_american_odds = (parlay_decimal_odds - 1.0) * 100.0
            else: parlay_american_odds = -100.0 / (parlay_decimal_odds - 1.0)

        # Display Legs
        for i, leg in enumerate(legs, 1):
            selection_info = self._get_leg_display_info(leg) # Use helper
            embed.add_field(
                 name=f"Leg {i}" if len(legs) > 1 else "Selection",
                 value=f"```{selection_info[:1000]}```",
                 inline=False
            )
            odds_value = leg.get('odds', 0.0)
            units_value = leg.get('units', 0.0)
            embed.add_field(name="Odds", value=f"{odds_value:+}", inline=True)
            if bet_type != "Parlay":
                 embed.add_field(name="Risk", value=f"{units_value:.2f}u", inline=True)
                 total_units_risked += units_value
                 embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer
            # else: # For Parlay, add spacers if needed to align fields
            #      embed.add_field(name="\u200B", value="\u200B", inline=True)
            #      embed.add_field(name="\u200B", value="\u200B", inline=True)


        # --- Risk/Win ---
        total_potential_profit = 0.0
        if bet_type == "Parlay" and parlay_units > 0:
             total_potential_profit = parlay_units * (parlay_decimal_odds - 1.0)
             embed.add_field(name="Parlay Odds", value=f"{parlay_american_odds:+.0f}", inline=True)
             embed.add_field(name="Total Risk", value=f"{parlay_units:.2f}u", inline=True)
             embed.add_field(name="To Win", value=f"{total_potential_profit:.2f}u", inline=True)

        elif bet_type == "Straight" and legs:
             # Calculate profit per leg (should only be one)
             for leg in legs:
                 odds_value = leg.get('odds', 0.0)
                 units_value = leg.get('units', 0.0)
                 if units_value > 0:
                     if odds_value > 0: total_potential_profit += units_value * (odds_value / 100.0)
                     elif odds_value < 0: total_potential_profit += units_value * (100.0 / abs(odds_value))
             # Risk was already added per leg display
             # embed.add_field(name="Total Risk", value=f"{total_units_risked:.2f}u", inline=True) # Redundant if shown above
             embed.add_field(name="To Win", value=f"{total_potential_profit:.2f}u", inline=True)
             embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer


        embed.set_footer(text=f"Bet ID: {bet_serial} | Status: Pending ⌛")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    async def submit_bet(self, interaction: Interaction):
        """Processes the validated bet_details and sends to the service/DB, then posts."""
        details = self.bet_details
        post_channel_id = details.get('channel_id')
        post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None
        bet_type = details.get('bet_type')
        legs = details.get('legs', [])

        # --- Log Submission Attempt ---
        logger.info(f"Attempting to submit bet. Type: {bet_type}, Legs: {len(legs)}, Channel: {post_channel_id}")

        if not post_channel or not isinstance(post_channel, TextChannel):
            logger.error(f"Invalid post channel ID ({post_channel_id}) or channel not found/not text.")
            await self.edit_message(content=f"❌ Error: Invalid channel selected ({post_channel_id}). Bet not placed.", view=None)
            self.stop()
            return
        if not legs:
             logger.error("Submit bet called with no legs.")
             await self.edit_message(content=f"❌ Error: No bet details found. Bet not placed.", view=None)
             self.stop()
             return
        if not hasattr(self.bot, 'bet_service'):
             logger.error("Bet service is not available on the bot object.")
             await self.edit_message(content=f"❌ Error: Betting service is unavailable. Bet not placed.", view=None)
             self.stop()
             return

        # --- Interact with Bet Service ---
        bet_serial = None
        try:
            if bet_type == "straight":
                if len(legs) != 1:
                    raise BetServiceError(f"Straight bet requires exactly 1 leg, found {len(legs)}.")
                leg = legs[0]
                # Determine detailed type (game vs player) for the service
                detailed_type = "player_prop" if leg.get('player') else "game_line"
                # Determine identifier (team or player depending on type)
                identifier = leg.get('player') if detailed_type == "player_prop" else leg.get('team')
                if not identifier: # Fallback for game lines if team isn't set (e.g., Over/Under)
                     identifier = leg.get('line') # Use the line itself? Needs thought. Or pass structured data.

                bet_serial = await self.bot.bet_service.create_bet(
                    guild_id=interaction.guild_id,
                    user_id=interaction.user.id,
                    # Pass structured leg data instead of individual params if service supports it
                    game_id=details.get('game_id') if details.get('game_id') != 'Other' else None,
                    bet_type=detailed_type, # Pass specific type
                    selection=leg.get('line'), # The actual bet line
                    identifier=identifier, # Team or Player name
                    units=leg.get('units'),
                    odds=leg.get('odds'),
                    channel_id=post_channel_id,
                    # Add other relevant details from `details` or `leg` dict if needed
                    league=details.get('league'),
                    opponent=leg.get('opponent') # If manual game line
                    # player=leg.get('player') # Already passed as identifier if player prop
                )
            elif bet_type == "parlay":
                 # Structure legs for the parlay service call
                 parlay_legs_data = []
                 for leg in legs:
                      detailed_type = "player_prop" if leg.get('player') else "game_line"
                      identifier = leg.get('player') if detailed_type == "player_prop" else leg.get('team')
                      if not identifier: identifier = leg.get('line') # Fallback identifier

                      parlay_legs_data.append({
                           # Pass structured leg data
                           'game_id': details.get('game_id') if details.get('game_id') != 'Other' else None, # Assuming parlay is on same game for now? Needs clarification. If multi-game, need game_id per leg.
                           'bet_type': detailed_type,
                           'selection': leg.get('line'),
                           'identifier': identifier,
                           'units': leg.get('units'), # Units might apply to whole parlay, service needs to handle
                           'odds': leg.get('odds'),
                           'league': details.get('league'), # Assume same league?
                           'opponent': leg.get('opponent'),
                           # player=leg.get('player') # Included in identifier
                      })

                 bet_serial = await self.bot.bet_service.create_parlay_bet(
                     guild_id=interaction.guild_id,
                     user_id=interaction.user.id,
                     legs=parlay_legs_data, # Pass structured legs
                     # Pass overall parlay details if applicable (e.g., total units risked if not per-leg)
                     units=legs[0].get('units'), # Send overall units from first leg?
                     channel_id=post_channel_id,
                     league=details.get('league')
                 )
            else:
                 raise BetServiceError(f"Unknown bet type: {bet_type}")

            if bet_serial is None:
                 raise BetServiceError("Bet service did not return a bet serial.")

            logger.info(f"Bet successfully created with service. Serial: {bet_serial}")

            # --- Post Final Embed to Channel ---
            final_embed = self.create_final_bet_embed(bet_serial)
            # Use a persistent view for resolution buttons if BetResolutionView is correctly set up
            resolution_view = BetResolutionView(bet_serial) # Ensure this view is correctly defined/imported

            sent_message = await post_channel.send(embed=final_embed, view=resolution_view)
            logger.info(f"Bet {bet_serial} posted to channel {post_channel.id}, message {sent_message.id}")

            # Optional: Store message ID with bet serial in DB for later updates
            # await self.bot.bet_service.link_message_to_bet(bet_serial, sent_message.id)

            # --- Send Confirmation to User ---
            success_message = f"✅ Bet placed! (ID: `{bet_serial}`). Posted to {post_channel.mention}."
            await self.edit_message(content=success_message, view=None, embed=None)


        except (ValidationError, BetServiceError, GameNotFoundError) as e:
             logger.error(f"Error submitting bet to service: {e}")
             await self.edit_message(content=f"❌ Error placing bet: {e}", view=None, embed=None)
        except discord.Forbidden:
             logger.error(f"Permission error posting bet {bet_serial} to channel {post_channel_id}.")
             await self.edit_message(content=f"❌ Bet placed (ID: `{bet_serial}`), but I don't have permission to post in {post_channel.mention}.", view=None, embed=None)
        except discord.HTTPException as e:
             logger.error(f"HTTP error posting bet {bet_serial} to channel {post_channel_id}: {e}")
             await self.edit_message(content=f"⚠️ Bet placed (ID: `{bet_serial}`), but failed to post to Discord (Error: {e.code}).", view=None, embed=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting bet: {e}")
            # Try to inform user, even if bet *might* be in DB
            await self.edit_message(content=f"❌ An unexpected error occurred during submission. Bet might have been placed (ID: `{bet_serial}` if generated). Please check.", view=None, embed=None)
        finally:
             self.stop() # Stop the workflow view


# --- Cog Definition ---
class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Ensure dependencies are loaded (optional check)
        if not hasattr(bot, 'bet_service'):
            logger.warning("BettingCog loaded, but bot.bet_service not found. Betting commands may fail.")
        if not hasattr(bot, 'game_service'):
            logger.warning("BettingCog loaded, but bot.game_service not found. Game/Player lookups may fail.")
        # Add view persistence listener if needed
        # bot.add_view(BetResolutionView(bet_serial=-1)) # Need a way to load serials or handle dynamically

    @app_commands.command(name="bet", description="Place a new bet through a guided workflow.")
    @app_commands.checks.has_permissions(send_messages=True) # Basic check
    async def bet_command(self, interaction: Interaction):
        """Starts the interactive betting workflow."""
        logger.info(f"Bet command initiated by {interaction.user} ({interaction.user.id}) in guild {interaction.guild_id}")

        # Defer immediately, making it ephemeral
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except discord.InteractionResponded:
             logger.warning("Interaction already responded to before defer.")
             # Potentially followup if needed, but flow should handle it
             # await interaction.followup.send("Processing...", ephemeral=True)
             # return # Or let it continue if defer isn't strictly needed immediately

        # Add authorization checks here if required
        # is_authorized = await check_user_authorization(interaction.user.id, interaction.guild_id)
        # if not is_authorized:
        #     logger.warning(f"User {interaction.user.id} unauthorized for /bet command.")
        #     await interaction.followup.send("❌ You are not authorized to place bets.", ephemeral=True)
        #     return

        try:
            # Create and start the workflow view
            view = BetWorkflowView(interaction, self.bot)
            await view.start_flow()

        except Exception as e:
            logger.exception(f"Error initiating bet command workflow: {e}")
            error_message = "❌ An error occurred while starting the betting workflow."
            try:
                 # Use followup as the interaction should have been deferred
                 await interaction.followup.send(error_message, ephemeral=True)
            except discord.HTTPException:
                 logger.error("Failed to send error followup for bet command initiation.")


async def setup(bot: commands.Bot):
    await bot.add_cog(BettingCog(bot))
    logger.info("BettingCog loaded")
