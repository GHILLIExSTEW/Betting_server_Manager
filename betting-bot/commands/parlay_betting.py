# betting-bot/commands/parlay_betting.py

"""Parlay betting workflow for placing multi-leg bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel, File, Embed
# Need to import commands for Cog base class
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union, Any
from datetime import datetime, timezone
import io
import uuid
import os

# Use relative imports
try:
    from ..utils.errors import BetServiceError, ValidationError, GameNotFoundError
    from ..utils.image_generator import BetSlipGenerator
except ImportError:
    from utils.errors import BetServiceError, ValidationError, GameNotFoundError
    from utils.image_generator import BetSlipGenerator

logger = logging.getLogger(__name__)

# --- UI Component Classes ---
class LeagueSelect(Select):
    def __init__(self, parent_view, leagues: List[str]):
        self.parent_view = parent_view
        options = [SelectOption(label=league, value=league) for league in leagues[:24]]
        options.append(SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select League...", options=options, min_values=1, max_values=1)

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
        super().__init__(placeholder="Select Line Type...", options=options, min_values=1, max_values=1)

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
        for game in games[:24]: # Discord limit
            home = game.get('home_team_name', 'Unknown Home')
            away = game.get('away_team_name', 'Unknown Away')
            start_dt = game.get('start_time')
            time_str = "Time N/A"
            if isinstance(start_dt, datetime):
                # Format time nicely, maybe convert to user's timezone if known/possible
                time_str = start_dt.strftime('%m/%d %H:%M %Z') # Example: 05/06 14:00 UTC
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id') # Assuming 'id' is the API game ID
            if game_api_id is None:
                logger.warning(f"Game missing 'id': {game}")
                continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id))) # Ensure value is string, limit label length
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(placeholder="Select Game (or Other)...", options=options, min_values=1, max_values=1)

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
        super().__init__(placeholder=f"{team_name} Players...", options=options, min_values=0, max_values=1)

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.bet_details['player'] = self.values[0].replace("home_", "")
            for item in self.parent_view.children:
                if isinstance(item, AwayPlayerSelect):
                    item.disabled = True
        else:
            # If 'none' or empty selection, ensure player is None if not set by other select
            if not self.parent_view.bet_details.get('player'):
                 self.parent_view.bet_details['player'] = None
        logger.debug(f"Home player selected: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        # Only advance if a player was actually selected
        if self.parent_view.bet_details.get('player'):
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
            self.parent_view.bet_details['player'] = self.values[0].replace("away_", "")
            for item in self.parent_view.children:
                if isinstance(item, HomePlayerSelect):
                    item.disabled = True
        else:
             if not self.parent_view.bet_details.get('player'):
                 self.parent_view.bet_details['player'] = None
        logger.debug(f"Away player selected: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
        await interaction.response.defer()
        if self.parent_view.bet_details.get('player'):
            await self.parent_view.go_next(interaction)

class ManualEntryButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Manual Entry",
            # Use interaction ID for uniqueness
            custom_id=f"parlay_manual_entry_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Manual Entry button clicked by user {interaction.user.id}")
        self.parent_view.bet_details['game_id'] = "Other" # Mark leg as manual game
        self.disabled = True
        for item in self.parent_view.children:
            if isinstance(item, CancelButton):
                item.disabled = True
        line_type = self.parent_view.bet_details.get('line_type') # Use current leg's line type
        leg_number = len(self.parent_view.bet_details.get('legs', [])) + 1
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True, leg_number=leg_number)
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully")
            await self.parent_view.edit_message(
                interaction,
                content="Manual entry form opened. Fill in details for the leg.",
                view=self.parent_view # Keep disabled view for context
            )
            # Modal submission will handle next step via its on_submit
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal: {e}")
            try:
                await self.parent_view.edit_message(
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
            # Use interaction ID for uniqueness
            custom_id=f"parlay_cancel_{parent_view.original_interaction.id}"
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
                # Use bot's bet_service
                if hasattr(self.parent_view.bot, 'bet_service'):
                     await self.parent_view.bot.bet_service.delete_bet(bet_serial)
                     logger.info(f"Parlay bet {bet_serial} cancelled and deleted by user {interaction.user.id}.")
                     await interaction.response.edit_message(
                         content=f"Parlay `{bet_serial}` cancelled and records deleted.",
                         view=None # Remove view
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
             # No bet created yet, just cancel workflow
             await interaction.response.edit_message(content="Parlay workflow cancelled.", view=None)
        self.parent_view.stop()

class BetDetailsModal(Modal):
    def __init__(self, line_type: str, is_manual: bool = False, leg_number: int = 1):
        title = f"Leg {leg_number}: Enter Bet Details"
        super().__init__(title=title[:45]) # Title limit is 45 chars
        self.line_type = line_type
        self.is_manual = is_manual
        self.leg_number = leg_number

        # --- Dynamic Fields ---
        # Always need Team for player props or manual game lines
        if self.is_manual or self.line_type == "player_prop":
            self.team = TextInput(
                label="Team Involved",
                required=True,
                max_length=100,
                placeholder="Enter team name"
            )
            self.add_item(self.team)
        # Else (game selected, game line): Team info is implicitly known from game selection

        # Always need Opponent for manual game lines
        if self.is_manual:
             self.opponent = TextInput(
                 label="Opponent",
                 required=True,
                 max_length=100,
                 placeholder="Enter opponent name"
             )
             self.add_item(self.opponent)
        # Else (game selected): Opponent info is known

        # Line or Player+Line
        if line_type == "player_prop":
            self.player_line = TextInput(
                label="Player - Line",
                required=True,
                max_length=100,
                placeholder="E.g., LeBron James - Points Over 25.5"
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

        # Odds
        self.odds = TextInput(
            label="Leg Odds",
            required=True,
            max_length=10,
            placeholder="American odds (e.g., -110, +200)"
        )
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"Parlay BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual}, leg_number={self.leg_number} by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True) # Defer immediately

        try:
            # --- Extract Data ---
            team = self.team.value.strip() if hasattr(self, 'team') else self.view.bet_details.get('home_team_name') # Fallback to game selection
            opponent = self.opponent.value.strip() if hasattr(self, 'opponent') else self.view.bet_details.get('away_team_name') # Fallback to game selection

            if self.line_type == "player_prop":
                line = self.player_line.value.strip()
            else:
                line = self.line.value.strip()
            odds_str = self.odds.value.strip()

            # --- Validation ---
            if not line or not odds_str:
                await interaction.followup.send("❌ Line and Odds are required.", ephemeral=True)
                return
            # More robust validation for team/opponent needed if they were optional
            if self.is_manual and (not team or not opponent):
                await interaction.followup.send("❌ Team and Opponent are required for manual entry.", ephemeral=True)
                return

            # Validate Odds
            try:
                odds_val_str = odds_str.replace('+', '')
                if not odds_val_str: raise ValueError("Odds cannot be empty.")
                odds_val = float(odds_val_str)
                if -100 < odds_val < 100 and odds_val != 0:
                     raise ValueError("Odds cannot be between -99 and +99 (excluding 0).")
            except ValueError as ve:
                logger.warning(f"Invalid odds entered: {odds_str} - Error: {ve}")
                await interaction.followup.send(f"❌ Invalid odds format: '{odds_str}'. Use American odds. {ve}", ephemeral=True)
                return

            # --- Prepare Leg Details ---
            leg = {
                'game_id': self.view.bet_details.get('game_id') if not self.is_manual else None,
                'team': team,
                'opponent': opponent,
                'line': line,
                'odds': odds_val, # Store float odds
                'odds_str': odds_str, # Store original string for display
                'bet_type': self.line_type,
                'league': self.view.bet_details.get('league', 'NHL') # Get league from main view state
            }

            # --- Add Leg to Parent View State ---
            if not hasattr(self.view, 'add_leg'):
                 logger.error("Parent view missing add_leg method")
                 await interaction.followup.send("❌ Internal error: Could not add leg.", ephemeral=True)
                 return

            await self.view.add_leg(interaction, leg) # Pass full leg details to parent
            # Parent view's add_leg will handle sending the next message (add more / finalize)

        except Exception as e:
            logger.exception(f"Error in Parlay BetDetailsModal on_submit: {e}")
            await interaction.followup.send("❌ Failed to process leg details. Please try again.", ephemeral=True)
            # Consider stopping the parent view self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in Parlay BetDetailsModal: {error}", exc_info=True)
        try:
            await interaction.followup.send('❌ An error occurred with the bet details modal.', ephemeral=True)
        except discord.HTTPException:
            logger.warning("Could not send error followup for Parlay BetDetailsModal.")


class UnitsSelect(Select):
    # This remains the same as in straight_betting.py
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="1 Unit", value="1.0"),
            SelectOption(label="2 Units", value="2.0"),
            SelectOption(label="3 Units", value="3.0")
            # Add more if needed
        ]
        super().__init__(placeholder="Select Units for Parlay...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        units = self.values[0]
        self.parent_view.bet_details['units_str'] = units # Store overall units
        logger.debug(f"Units selected for parlay: {units} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction) # Proceed to Channel selection


class AddLegButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Add Another Leg",
            # Use interaction ID for uniqueness
            custom_id=f"parlay_add_leg_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Add Leg button clicked by user {interaction.user.id}")
        self.parent_view.current_step = 0  # Reset to league selection for the new leg
        # Clear previous leg's game/player details, keep league potentially?
        self.parent_view.bet_details.pop('game_id', None)
        self.parent_view.bet_details.pop('home_team_name', None)
        self.parent_view.bet_details.pop('away_team_name', None)
        self.parent_view.bet_details.pop('line_type', None)
        self.parent_view.bet_details.pop('player', None)
        # Keep 'legs' array and 'bet_serial' if already created

        # Edit message to show processing before calling go_next
        await interaction.response.edit_message(content="Starting next leg...", view=None) # Clear buttons while processing
        await self.parent_view.go_next(interaction)

class FinalizeButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.blurple,
            label="Finalize Parlay",
            # Use interaction ID for uniqueness
            custom_id=f"parlay_finalize_{parent_view.original_interaction.id}",
            # Enable only if 2 or more legs are present
            disabled=len(parent_view.bet_details.get('legs', [])) < 2
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Finalize button clicked by user {interaction.user.id}")
        # Show final odds modal first
        # final_odds_modal = FinalOddsModal() # Modal removed, calculate odds internally
        # await interaction.response.send_modal(final_odds_modal)
        # await final_odds_modal.wait()

        # if not final_odds_modal.odds_value:
        #     return # User cancelled modal or entered invalid odds

        # Calculate total odds internally
        total_odds = self.parent_view._calculate_parlay_odds(self.parent_view.bet_details.get('legs', []))

        # Update bet details with final calculated odds
        self.parent_view.bet_details['total_odds'] = total_odds # Store float
        self.parent_view.bet_details['total_odds_str'] = self.parent_view._format_odds_with_sign(total_odds) # Store formatted string

        # Disable buttons while proceeding
        for item in self.parent_view.children:
            item.disabled = True
        await interaction.response.edit_message(content="Finalizing parlay...", view=self.parent_view) # Keep view to show disabled state

        # Proceed to units selection
        self.parent_view.current_step = 5 # Skip to units step
        await self.parent_view.go_next(interaction)


class LegDecisionView(View):
    """View shown after a leg is added, asking to add more or finalize."""
    def __init__(self, parent_view):
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.add_item(AddLegButton(self.parent_view))
        self.add_item(FinalizeButton(self)) # Finalize button is enabled/disabled based on leg count
        self.add_item(CancelButton(self.parent_view))

class ChannelSelect(Select):
    # This remains the same as in straight_betting.py
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
        logger.debug(f"Channel selected: {selected_value} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class ConfirmButton(Button):
    # This remains the same as in straight_betting.py
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Confirm & Post",
            # Use interaction ID for uniqueness
            custom_id=f"parlay_confirm_bet_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Confirm button clicked by user {interaction.user.id}")
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        await interaction.response.edit_message(view=self.parent_view) # Keep view disabled
        await self.parent_view.submit_bet(interaction)

# Removed FinalOddsModal as odds are calculated internally now

# --- Main Workflow View ---
class ParlayBetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot): # Added bot type hint
        super().__init__(timeout=600) # Increased timeout
        self.original_interaction = interaction
        self.bot = bot # Store bot instance
        self.current_step = 0
        # Initialize legs as empty list, store bet type
        self.bet_details: Dict[str, Any] = {'legs': [], 'bet_type': 'parlay'}
        self.games: List[Dict] = [] # Store fetched games for selection
        self.message: Optional[Union[discord.WebhookMessage, discord.InteractionMessage]] = None # Type hint message
        self.is_processing = False # Lock
        self.latest_interaction = interaction # Track latest interaction
        self.bet_slip_generator = BetSlipGenerator() # Initialize image generator
        self.preview_image_bytes: Optional[io.BytesIO] = None # Store generated image bytes
        # No longer need team_logos cache here? generate_bet_slip handles it.


    async def _preload_team_logos(self, team1: str, team2: str, league: str):
        """Preload team logos to check availability and paths."""
        # Now handled within generate_bet_slip, this method might not be needed here
        pass

    # Helper to format odds
    def _format_odds_with_sign(self, odds: Optional[float]) -> str:
        """Formats odds, adding a '+' for positive values. Handles None/non-numeric."""
        if odds is None: return "N/A"
        try:
            odds_num = int(float(odds)) # Attempt conversion
            if odds_num > 0: return f"+{odds_num}"
            return str(odds_num)
        except (ValueError, TypeError):
            logger.warning(f"Could not format odds, invalid value: {odds}")
            return "N/A"

    def _calculate_parlay_odds(self, legs: List[Dict[str, Any]]) -> float:
        """Calculate the total American odds for a parlay from its legs."""
        if not legs:
            return 0.0

        total_decimal_odds = 1.0
        try:
            for leg in legs:
                odds = float(leg.get('odds', 0)) # Use the float odds stored
                if odds == 0: continue # Skip potentially invalid legs

                if odds > 0:
                    decimal_leg = (odds / 100.0) + 1.0
                else: # Negative odds
                    decimal_leg = (100.0 / abs(odds)) + 1.0
                total_decimal_odds *= decimal_leg

            if total_decimal_odds <= 1.0: # Includes cases where calculation failed or only invalid legs
                return 0.0 # Or handle as error

            # Convert back to American odds
            if total_decimal_odds >= 2.0:
                american_odds = (total_decimal_odds - 1.0) * 100.0
            else:
                american_odds = -100.0 / (total_decimal_odds - 1.0)

            return round(american_odds) # Return rounded integer American odds

        except (ValueError, TypeError, KeyError) as e:
             logger.error(f"Error calculating parlay odds from legs: {legs}. Error: {e}")
             return 0.0 # Indicate error

    async def add_leg(self, interaction: Interaction, leg_details: Dict[str, Any]):
        """Add a leg to the parlay bet details and prompt for next action."""
        # Ensure 'legs' list exists
        if 'legs' not in self.bet_details:
            self.bet_details['legs'] = []

        # Validate leg_details structure if needed
        required_keys = ['team', 'opponent', 'line', 'odds', 'odds_str', 'bet_type', 'league']
        if not all(key in leg_details for key in required_keys):
             logger.error(f"Attempted to add invalid leg: {leg_details}")
             await interaction.followup.send("❌ Internal error: Leg details incomplete.", ephemeral=True)
             self.stop()
             return

        self.bet_details['legs'].append(leg_details)
        leg_count = len(self.bet_details['legs'])
        logger.info(f"Leg {leg_count} added to parlay by user {interaction.user.id}")

        # --- Create or Update Bet Record ---
        # If first leg, create the bet record. If subsequent leg, update details.
        bet_serial = self.bet_details.get('bet_serial')
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        legs_data = self.bet_details['legs']
        overall_league = legs_data[0].get('league', 'NHL') # Use first leg's league for now

        try:
             if bet_serial: # Update existing bet
                 # Recalculate odds for display/update if needed
                 total_odds = self._calculate_parlay_odds(legs_data)
                 bet_details_json = json.dumps({'legs': legs_data})
                 update_query = """
                     UPDATE bets
                     SET bet_details = %s, legs = %s, odds = %s, updated_at = %s
                     WHERE bet_serial = %s
                 """
                 await self.bot.db_manager.execute(
                     update_query, bet_details_json, len(legs_data), total_odds, datetime.now(timezone.utc), bet_serial
                 )
                 logger.debug(f"Updated parlay bet {bet_serial} with {len(legs_data)} legs.")
             else: # Create new bet (should only happen for first leg ideally)
                 total_odds = self._calculate_parlay_odds(legs_data)
                 bet_details_json = json.dumps({'legs': legs_data})
                 # Use create_parlay_bet service method
                 new_bet_serial = await self.bot.bet_service.create_parlay_bet(
                     guild_id=guild_id,
                     user_id=user_id,
                     legs=legs_data, # Pass leg details
                     channel_id=None,
                     league=overall_league,
                     # Pass calculated odds and units (assuming 1 unit stake initially)
                     # total_odds=total_odds, # create_parlay_bet calculates this
                     # total_units=1.0
                 )
                 if not new_bet_serial:
                      raise BetServiceError("Failed to create initial parlay bet record.")
                 self.bet_details['bet_serial'] = new_bet_serial
                 logger.debug(f"Created initial parlay bet record {new_bet_serial} with first leg.")

        except Exception as e:
             logger.exception(f"Error creating/updating parlay bet record for user {user_id}: {e}")
             await interaction.followup.send("❌ Failed to save bet leg data. Please try again.", ephemeral=True)
             self.stop()
             return


        # --- Update Message ---
        # Show summary of added legs
        summary_lines = [f"**Parlay Legs ({leg_count}):**"]
        for i, leg in enumerate(legs_data):
            summary_lines.append(f"{i+1}. {leg['league']}: {leg['line']} ({leg.get('team','?')} vs {leg.get('opponent','?')}) @ {leg['odds_str']}")
        summary_text = "\n".join(summary_lines)

        decision_view = LegDecisionView(self)
        # Edit the message (use followup because modal submit deferred)
        await interaction.followup.send(
             f"{summary_text}\n\nAdd another leg or finalize?",
             view=decision_view,
             ephemeral=True
        )
        # Update the main message reference
        self.message = await interaction.original_response()

    async def start_flow(self):
        logger.debug(f"Starting parlay bet workflow for user {self.original_interaction.user} (ID: {self.original_interaction.user.id})")
        try:
            # Message sent by caller using followup
            self.message = await self.original_interaction.original_response()
            await self.go_next(self.original_interaction) # Start first step
        except discord.HTTPException as e:
            logger.error(f"Failed to send initial message/start flow for parlay workflow: {e}")
            try:
                 await self.original_interaction.followup.send("❌ Failed to start parlay workflow. Please try again.", ephemeral=True)
            except discord.HTTPException: pass
            self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            logger.debug(f"Unauthorized parlay interaction attempt by {interaction.user} (ID: {interaction.user.id})")
            await interaction.response.send_message(
                "You cannot interact with this parlay placement.", ephemeral=True
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
        target_interaction = interaction or self.latest_interaction or self.original_interaction
        target_message = self.message
        log_info = f"Editing parlay message: content={content is not None}, view={view is not None}, embed={embed is not None}, file={file is not None}"
        if interaction: log_info += f" triggered by user {interaction.user.id}"
        logger.debug(log_info)
        attachments = [file] if file else []
        try:
            await target_interaction.edit_original_response(
                content=content, embed=embed, view=view, attachments=attachments
            )
        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Failed to edit original interaction response: {e}. Trying stored message reference.")
            if target_message and isinstance(target_message, discord.WebhookMessage):
                try:
                    await target_message.edit(content=content, embed=embed, view=view, attachments=attachments)
                except (discord.NotFound, discord.HTTPException) as e2:
                    logger.error(f"Failed to edit ParlayBetWorkflowView message (fallback): {e2}")
                    # Inform user via followup if possible
                    if interaction:
                        try: await interaction.followup.send("❌ Failed to update parlay workflow display.", ephemeral=True)
                        except discord.HTTPException: pass
            else:
                logger.error("Failed to edit message: No valid interaction or message reference.")
                if interaction:
                    try: await interaction.followup.send("❌ Failed to update parlay workflow display.", ephemeral=True)
                    except discord.HTTPException: pass
        except Exception as e:
            logger.exception(f"Unexpected error editing ParlayBetWorkflowView message: {e}")
            if interaction:
                 try: await interaction.followup.send("❌ An unexpected error occurred updating the display.", ephemeral=True)
                 except discord.HTTPException: pass


    async def go_next(self, interaction: Interaction):
        """Handle progression to the next step in the parlay workflow."""
        if self.is_processing:
            logger.debug(f"Skipping parlay go_next call; already processing step {self.current_step} for user {interaction.user.id}")
            return
        self.is_processing = True
        try:
            logger.debug(f"Processing parlay go_next: current_step={self.current_step} for user {interaction.user.id}")
            # Only increment step if not coming from Add Leg button (which resets step)
            if not (interaction.data and interaction.data.get('custom_id', '').startswith('parlay_add_leg')):
                self.current_step += 1

            step_content = f"**Leg {len(self.bet_details.get('legs', [])) + 1} - Step {self.current_step}**"
            self.clear_items() # Clear components from previous step

            logger.debug(f"Entering parlay step {self.current_step}")

            # --- Workflow Steps ---
            if self.current_step == 1: # League Selection (for this leg)
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                self.add_item(LeagueSelect(self, allowed_leagues))
                self.add_item(CancelButton(self))
                step_content += ": Select League for Leg"
                await self.edit_message(interaction, content=step_content, view=self)

            elif self.current_step == 2: # Line Type Selection (for this leg)
                self.add_item(LineTypeSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Line Type for Leg"
                await self.edit_message(interaction, content=step_content, view=self)

            elif self.current_step == 3: # Game Selection or Manual Entry (for this leg)
                league = self.bet_details.get('league') # League selected for current leg
                if not league:
                    logger.error("No league selected for game selection step.")
                    await self.edit_message(interaction, content="❌ No league selected for this leg. Please start over.", view=None)
                    self.stop()
                    return

                self.games = [] # Reset games list for this leg
                if league != "Other" and hasattr(self.bot, 'game_service'):
                    try:
                        # Fetch upcoming games for the selected league
                        # Using get_league_games with status='scheduled'
                        self.games = await self.bot.game_service.get_league_games(
                            guild_id=interaction.guild_id,
                            league=league,
                            status='scheduled', # Fetch scheduled games
                            limit=20 # Limit results
                        )
                        logger.debug(f"Fetched {len(self.games)} upcoming scheduled games for {league}.")
                    except Exception as e:
                        logger.exception(f"Error fetching games for league {league}: {e}")
                        # Proceed to manual entry on error

                if self.games: # Found games, show GameSelect
                    self.add_item(GameSelect(self, self.games))
                    self.add_item(ManualEntryButton(self)) # Still allow manual entry
                    self.add_item(CancelButton(self))
                    step_content += f": Select Game for {league} Leg (or Enter Manually)"
                    await self.edit_message(interaction, content=step_content, view=self)
                else: # No games found or league is "Other" or error occurred
                    logger.warning(f"No upcoming games found or error fetching for league {league}. Prompting for manual entry.")
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content = f"No games found for {league}. Please enter details manually." if league != "Other" else "Please enter game details manually."
                    await self.edit_message(interaction, content=step_content, view=self)

            elif self.current_step == 4: # Player Selection (if player prop) or Modal Trigger (for this leg)
                line_type = self.bet_details.get('line_type')
                game_id = self.bet_details.get('game_id') # For current leg
                is_manual = game_id == "Other"
                leg_number = len(self.bet_details.get('legs', [])) + 1

                if line_type == "player_prop" and not is_manual and hasattr(self.bot, 'game_service'):
                     # Fetch players logic (similar to straight bet)
                     home_players, away_players = [], []
                     try:
                         players_data = await self.bot.game_service.get_game_players(game_id)
                         home_players = players_data.get('home_players', [])
                         away_players = players_data.get('away_players', [])
                     except Exception as e:
                         logger.error(f"Failed to fetch players for game {game_id}: {e}")
                     home_team = self.bet_details.get('home_team_name', 'Home Team')
                     away_team = self.bet_details.get('away_team_name', 'Away Team')
                     if home_players or away_players:
                         self.add_item(HomePlayerSelect(self, home_players, home_team))
                         self.add_item(AwayPlayerSelect(self, away_players, away_team))
                         self.add_item(CancelButton(self))
                         step_content += f": Select Player for Leg {leg_number} Prop Bet"
                         await self.edit_message(interaction, content=step_content, view=self)
                         self.current_step -= 1 # Wait for player selection
                         self.is_processing = False
                         return
                     else:
                         logger.warning(f"No players available for game {game_id}. Proceeding to manual prop entry.")
                         # Fallthrough to modal

                # Show Modal for game_line OR player_prop manual/fallback
                modal = BetDetailsModal(line_type=line_type, is_manual=is_manual, leg_number=leg_number)
                modal.view = self
                try:
                    await interaction.response.send_modal(modal) # Modal submit calls add_leg
                except discord.HTTPException as e:
                    logger.error(f"Failed to send Parlay BetDetailsModal: {e}")
                    await interaction.followup.send("❌ Failed to open bet details form.", ephemeral=True)
                    self.stop()
                self.is_processing = False # Release lock, wait for modal
                return

            # Step 5 is handled by add_leg method which shows LegDecisionView

            elif self.current_step == 6: # Units Selection (Triggered by FinalizeButton)
                self.add_item(UnitsSelect(self))
                self.add_item(CancelButton(self))
                step_content = f"**Final Step**: Select Total Units for Parlay (Total Odds: {self.bet_details.get('total_odds_str', 'N/A')})"
                await self.edit_message(interaction, content=step_content, view=self)

            elif self.current_step == 7: # Channel Selection & Preview (After Units Selected)
                 if 'units_str' not in self.bet_details:
                      logger.error("Units not selected before channel selection step.")
                      await self.edit_message(interaction, content="❌ Error: Units not selected. Please restart.", view=None)
                      self.stop()
                      return
                 if 'bet_serial' not in self.bet_details:
                      logger.error("Bet serial missing before channel selection step.")
                      await self.edit_message(interaction, content="❌ Error: Bet record not created. Please restart.", view=None)
                      self.stop()
                      return

                 # --- Generate Preview Image ---
                 try:
                     bet_serial = self.bet_details['bet_serial']
                     legs = self.bet_details.get('legs', [])
                     if not legs: raise ValueError("No legs found for preview.")

                     # Determine if same game/league for header
                     league = legs[0].get('league', 'NHL') # Use first leg's league as primary
                     game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
                     is_same_game = len(game_ids) == 1
                     all_legs_same_league = all(leg.get('league', league) == league for leg in legs)
                     display_league = league if (is_same_game or all_legs_same_league) else None

                     # Use first leg's teams for generator params (logos handled internally)
                     first_leg = legs[0]
                     home_team = first_leg.get('team', 'Unknown')
                     away_team = first_leg.get('opponent', 'Unknown')

                     # Ensure total odds and units are available
                     total_odds = self.bet_details.get('total_odds', 0.0)
                     total_units = float(self.bet_details.get('units_str', 1.0))

                     bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                         home_team=home_team, # Placeholder, generator uses legs
                         away_team=away_team, # Placeholder
                         league=display_league,
                         line="Parlay", # Placeholder line for parlay slip
                         odds=total_odds, # Total calculated odds
                         units=total_units, # Total stake
                         bet_id=str(bet_serial),
                         timestamp=datetime.now(timezone.utc),
                         bet_type="parlay",
                         parlay_legs=legs, # Pass actual legs
                         is_same_game=is_same_game
                     )

                     self.preview_image_bytes = io.BytesIO()
                     bet_slip_image.save(self.preview_image_bytes, format='PNG')
                     self.preview_image_bytes.seek(0)
                     file_to_send = File(self.preview_image_bytes, filename="parlay_preview.png")
                     self.preview_image_bytes.seek(0)

                 except Exception as e:
                     logger.exception(f"Failed to generate parlay slip image at step 7: {e}")
                     await self.edit_message(interaction, content="❌ Failed to generate parlay preview.", view=None)
                     self.stop()
                     return

                 # --- Get Writable Channels ---
                 channels = []
                 try:
                     if interaction.guild:
                          channels = sorted([ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.guild.me).send_messages], key=lambda c: c.position)
                 except Exception as e:
                     logger.error(f"Failed to fetch channels at step 7: {e}")

                 if not channels:
                     logger.error("No writable channels found in the guild.")
                     await self.edit_message(interaction, content="❌ No text channels found where I can post the parlay.", view=None)
                     self.stop()
                     return

                 # --- Update View for Channel Selection ---
                 self.add_item(ChannelSelect(self, channels))
                 self.add_item(CancelButton(self))
                 step_content = f"**Step {self.current_step}**: Review Parlay & Select Channel"
                 await self.edit_message(interaction, content=step_content, view=self, file=file_to_send)

            elif self.current_step == 8: # Confirmation Step (After Channel Selected)
                 if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units_str', 'total_odds_str', 'legs']):
                     logger.error(f"Missing parlay details for confirmation: {self.bet_details}")
                     await self.edit_message(interaction, content="❌ Error: Parlay details incomplete.", view=None)
                     self.stop()
                     return

                 # Re-use preview image
                 file_to_send = None
                 if self.preview_image_bytes:
                     self.preview_image_bytes.seek(0)
                     file_to_send = File(self.preview_image_bytes, filename="parlay_confirm.png")
                     self.preview_image_bytes.seek(0)

                 self.add_item(ConfirmButton(self))
                 self.add_item(CancelButton(self))
                 step_content = "**Final Step**: Confirm Parlay Details"
                 channel_mention = f"<#{self.bet_details['channel_id']}>"
                 leg_summary = "\n".join([f"- {leg['line']} ({leg.get('team','?')} vs {leg.get('opponent','?')}) @ {leg['odds_str']}" for leg in self.bet_details['legs']])
                 confirmation_text = (
                      f"{step_content}\n\n"
                      f"**Legs:**\n{leg_summary}\n"
                      f"**Total Odds:** {self.bet_details['total_odds_str']}\n"
                      f"**Total Units:** {self.bet_details['units_str']}\n"
                      f"**Post to:** {channel_mention}\n\n"
                      "Click 'Confirm & Post' to place the parlay."
                 )
                 await self.edit_message(interaction, content=confirmation_text, view=self, file=file_to_send)

            else: # Should not happen
                logger.error(f"ParlayBetWorkflowView reached unexpected step: {self.current_step}")
                await self.edit_message(interaction, content="❌ Invalid step reached.", view=None)
                self.stop()

        except Exception as e:
            logger.exception(f"Error in parlay bet workflow step {self.current_step}: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred.", view=None)
            self.stop()
        finally:
            self.is_processing = False # Release lock

    async def submit_bet(self, interaction: Interaction):
        """Submits the finalized parlay: updates DB, sends image, confirms."""
        details = self.bet_details
        bet_serial = details.get('bet_serial')
        if not bet_serial:
             logger.error("Attempted to submit parlay without a bet_serial.")
             await self.edit_message(interaction, content="❌ Error: Bet ID missing.", view=None)
             self.stop()
             return

        logger.info(f"Submitting parlay bet {bet_serial} for user {interaction.user} (ID: {interaction.user.id})")
        await self.edit_message(interaction, content="Processing and posting parlay...", view=None, file=None) # Clear previous

        try:
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None
            if not post_channel or not isinstance(post_channel, TextChannel):
                logger.error(f"Invalid or inaccessible channel {post_channel_id} for parlay {bet_serial}")
                raise ValueError(f"Could not find text channel <#{post_channel_id}>.")

            # --- Update Bet Record with Units and Final Odds ---
            units = float(details.get('units_str', 1.0))
            total_odds = float(details.get('total_odds', 0.0)) # Use calculated float odds

            # Update the main bet record
            update_query = """
                UPDATE bets
                SET units = %s, odds = %s, channel_id = %s, confirmed = 1
                WHERE bet_serial = %s AND confirmed = 0
            """
            rowcount, _ = await self.bot.db_manager.execute(
                update_query, units, total_odds, post_channel_id, bet_serial
            )

            if rowcount is None or rowcount == 0:
                 # Check if already confirmed
                 check_query = "SELECT confirmed, channel_id, units, odds FROM bets WHERE bet_serial = %s"
                 existing_bet = await self.bot.db_manager.fetch_one(check_query, (bet_serial,))
                 if existing_bet and existing_bet['confirmed'] == 1:
                      logger.warning(f"Parlay {bet_serial} was already confirmed. Proceeding.")
                      post_channel_id = existing_bet['channel_id']
                      post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else post_channel
                      units = float(existing_bet['units'])
                      total_odds = float(existing_bet['odds'])
                 else:
                      logger.error(f"Failed to update parlay bet {bet_serial} with units/channel. Rowcount: {rowcount}")
                      raise BetServiceError("Failed to confirm parlay details in database.")

            # --- Prepare Final Image ---
            final_image_bytes = self.preview_image_bytes
            if not final_image_bytes:
                 logger.warning("Preview image bytes lost before final parlay submission. Regenerating.")
                 # Regeneration logic... (ensure details are correct)
                 try:
                     legs = details.get('legs', [])
                     league = legs[0].get('league', 'NHL')
                     game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
                     is_same_game = len(game_ids) == 1
                     all_legs_same_league = all(leg.get('league', league) == league for leg in legs)
                     display_league = league if (is_same_game or all_legs_same_league) else None
                     first_leg = legs[0]
                     home_team = first_leg.get('team', 'Unknown')
                     away_team = first_leg.get('opponent', 'Unknown')

                     bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                         home_team=home_team, away_team=away_team,
                         league=display_league, line="Parlay", odds=total_odds, units=units,
                         bet_id=str(bet_serial), timestamp=datetime.now(timezone.utc),
                         bet_type="parlay", parlay_legs=legs, is_same_game=is_same_game
                     )
                     final_image_bytes = io.BytesIO()
                     bet_slip_image.save(final_image_bytes, format='PNG')
                 except Exception as img_err:
                     logger.exception(f"Failed to regenerate parlay slip image: {img_err}")
                     raise BetServiceError("Failed to generate final parlay slip image.") from img_err

            if not final_image_bytes: raise ValueError("Final image data missing.")
            final_image_bytes.seek(0)
            discord_file = File(final_image_bytes, filename=f"parlay_slip_{bet_serial}.png")

            # --- Fetch Role Mention and Capper Info (Same as straight bet) ---
            role_mention = ""
            display_name = interaction.user.display_name
            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            try:
                settings = await self.bot.db_manager.fetch_one(
                    "SELECT authorized_role, member_role, bot_name_mask, bot_image_mask FROM guild_settings WHERE guild_id = %s",
                    (interaction.guild_id,)
                )
                if settings:
                    role_id = settings.get('authorized_role') or settings.get('member_role')
                    if role_id:
                         role = interaction.guild.get_role(int(role_id))
                         if role: role_mention = role.mention
                capper_info = await self.bot.db_manager.fetch_one(
                    "SELECT display_name, image_path FROM cappers WHERE user_id = %s AND guild_id = %s",
                    (interaction.user.id, interaction.guild_id)
                )
                if capper_info:
                    display_name = capper_info.get('display_name') or display_name
                    avatar_url = capper_info.get('image_path') or avatar_url
            except Exception as e:
                logger.error(f"Error fetching guild settings or capper info for parlay: {e}")

            # --- Send via Webhook (Same as straight bet) ---
            webhook = None
            try:
                webhooks = await post_channel.webhooks()
                webhook = next((wh for wh in webhooks if wh.user and wh.user.id == self.bot.user.id), None)
                if not webhook:
                    webhook = await post_channel.create_webhook(name=f"{self.bot.user.name} Parlays"[:100])
            except discord.Forbidden:
                raise ValueError("Bot lacks permission to manage webhooks.")
            except discord.HTTPException as e:
                raise ValueError(f"Failed to setup webhook: {e}")

            content = role_mention if role_mention else ""
            try:
                sent_message = await webhook.send(
                    content=content, file=discord_file,
                    username=display_name[:80], avatar_url=avatar_url, wait=True
                )
                logger.info(f"Parlay slip image sent for bet {bet_serial}, message ID: {sent_message.id}")
            except Exception as e:
                logger.error(f"Webhook send failed for parlay {bet_serial}: {e}")
                raise ValueError(f"Failed to send webhook message: {e}")

            # --- Track Message for Reactions (Same as straight bet) ---
            if sent_message and hasattr(self.bot.bet_service, 'pending_reactions'):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial,
                    'user_id': interaction.user.id,
                    'guild_id': interaction.guild_id,
                    'channel_id': post_channel_id,
                    'legs': details.get('legs'),
                    'league': details.get('league'), # Store primary league maybe?
                    'bet_type': 'parlay'
                }
                logger.debug(f"Added message {sent_message.id} to pending_reactions for parlay {bet_serial}")

            # --- Final Confirmation Message ---
            await self.edit_message(
                interaction,
                content=f"✅ Parlay placed successfully! (ID: `{bet_serial}`). Posted to {post_channel.mention}.",
                view=None
            )

        except (ValidationError, BetServiceError, ValueError) as e:
            logger.error(f"Error submitting parlay {bet_serial}: {e}")
            await self.edit_message(interaction, content=f"❌ Error placing parlay: {e}", view=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting parlay {bet_serial}: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred while posting the parlay.", view=None)
        finally:
            if self.preview_image_bytes:
                self.preview_image_bytes.close()
                self.preview_image_bytes = None
            self.stop()

# Setup function for the cog
async def setup(bot: commands.Bot):
    # This file defines Views/Modals used by the 'bet' command in betting.py
    # It doesn't define a Cog itself.
    logger.info("ParlayBetWorkflow components loaded (no Cog setup needed here)")
