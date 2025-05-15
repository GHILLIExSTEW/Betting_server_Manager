# betting-bot/commands/straight_betting.py

"""Straight betting workflow for placing single-leg bets."""

import discord
from discord import (
    ButtonStyle,
    Interaction,
    SelectOption,
    TextChannel,
    File,
    Embed,
    Webhook, # Added Webhook
)
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union, Any
from datetime import datetime, timezone
import io
import os
from discord.ext import commands
from io import BytesIO
import traceback
import json
import aiohttp # Added for fetching avatar image

# Import directly from utils
from utils.errors import (
    BetServiceError,
    ValidationError,
    GameNotFoundError,
)
from utils.image_generator import BetSlipGenerator

logger = logging.getLogger(__name__)


# --- UI Component Classes ---
# (LeagueSelect, LineTypeSelect, GameSelect, HomePlayerSelect, AwayPlayerSelect, ManualEntryButton, CancelButton remain the same as you provided)
class LeagueSelect(Select):
    def __init__(self, parent_view: View, leagues: List[str]):
        self.parent_view = parent_view
        options = [
            SelectOption(label=league, value=league)
            for league in leagues[:24]
        ]
        options.append(SelectOption(label="Other", value="Other"))
        super().__init__(
            placeholder="Select League...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details["league"] = self.values[0]
        logger.debug(
            f"League selected: {self.values[0]} by user {interaction.user.id}"
        )
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class LineTypeSelect(Select):
    def __init__(self, parent_view: View):
        self.parent_view = parent_view
        options = [
            SelectOption(
                label="Game Line",
                value="game_line",
                description="Moneyline or game over/under",
            ),
            SelectOption(
                label="Player Prop",
                value="player_prop",
                description="Bet on player performance",
            ),
        ]
        super().__init__(
            placeholder="Select Line Type...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details["line_type"] = self.values[0]
        logger.debug(
            f"Line Type selected: {self.values[0]} by user {interaction.user.id}"
        )
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class GameSelect(Select):
    def __init__(self, parent_view: View, games: List[Dict]):
        self.parent_view = parent_view
        options = []
        for game in games[:24]:
            home = game.get("home_team_name", "Unknown Home")
            away = game.get("away_team_name", "Unknown Away")
            start_dt_obj = game.get("start_time")
            time_str = "Time N/A"

            if isinstance(start_dt_obj, str):
                try:
                    start_dt_obj = datetime.fromisoformat(
                        start_dt_obj.replace("Z", "+00:00")
                    )
                except ValueError:
                    logger.warning(
                        f"Could not parse game start_time: {start_dt_obj}"
                    )
                    start_dt_obj = None

            if isinstance(start_dt_obj, datetime):
                time_str = start_dt_obj.strftime("%m/%d %H:%M %Z")
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get("id")
            if game_api_id is None:
                logger.warning(f"Game missing 'id': {game}")
                continue
            options.append(
                SelectOption(label=label[:100], value=str(game_api_id))
            )
        if len(options) < 25:
            options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(
            placeholder="Select Game (or Other)...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        selected_game_id = self.values[0]
        self.parent_view.bet_details["game_id"] = selected_game_id
        if selected_game_id != "Other":
            game = next(
                (
                    g
                    for g in self.parent_view.games
                    if str(g.get("id")) == selected_game_id
                ),
                None,
            )
            if game:
                self.parent_view.bet_details["home_team_name"] = game.get(
                    "home_team_name", "Unknown"
                )
                self.parent_view.bet_details["away_team_name"] = game.get(
                    "away_team_name", "Unknown"
                )
        logger.debug(
            f"Game selected: {selected_game_id} by user {interaction.user.id}"
        )
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class HomePlayerSelect(Select):
    def __init__(
        self, parent_view: View, players: List[str], team_name: str
    ):
        self.parent_view = parent_view
        self.team_name = team_name
        options = [
            SelectOption(label=player, value=f"home_{player}")
            for player in players[:24]
        ]
        if not options:
            options.append(
                SelectOption(
                    label="No Players Available", value="none", emoji="❌"
                )
            )
        super().__init__(
            placeholder=f"{team_name} Players...",
            options=options,
            min_values=0,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.bet_details["player"] = self.values[0].replace(
                "home_", ""
            )
            for item in self.parent_view.children:
                if isinstance(item, AwayPlayerSelect):
                    item.disabled = True
        else:
            if not self.parent_view.bet_details.get("player"):
                self.parent_view.bet_details["player"] = None
        logger.debug(
            f"Home player selected: {self.values[0] if self.values else 'None'} by user {interaction.user.id}"
        )
        await interaction.response.defer()
        if self.parent_view.bet_details.get(
            "player"
        ) or all(
            isinstance(i, Select) and i.disabled
            for i in self.parent_view.children
            if isinstance(i, (HomePlayerSelect, AwayPlayerSelect))
        ):
            await self.parent_view.go_next(interaction)


class AwayPlayerSelect(Select):
    def __init__(
        self, parent_view: View, players: List[str], team_name: str
    ):
        self.parent_view = parent_view
        self.team_name = team_name
        options = [
            SelectOption(label=player, value=f"away_{player}")
            for player in players[:24]
        ]
        if not options:
            options.append(
                SelectOption(
                    label="No Players Available", value="none", emoji="❌"
                )
            )
        super().__init__(
            placeholder=f"{team_name} Players...",
            options=options,
            min_values=0,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.bet_details["player"] = self.values[0].replace(
                "away_", ""
            )
            for item in self.parent_view.children:
                if isinstance(item, HomePlayerSelect):
                    item.disabled = True
        else:
            if not self.parent_view.bet_details.get("player"):
                self.parent_view.bet_details["player"] = None
        logger.debug(
            f"Away player selected: {self.values[0] if self.values else 'None'} by user {interaction.user.id}"
        )
        await interaction.response.defer()
        if self.parent_view.bet_details.get(
            "player"
        ) or all(
            isinstance(i, Select) and i.disabled
            for i in self.parent_view.children
            if isinstance(i, (HomePlayerSelect, AwayPlayerSelect))
        ):
            await self.parent_view.go_next(interaction)


class ManualEntryButton(Button):
    def __init__(self, parent_view: View):
        super().__init__(
            style=ButtonStyle.green,
            label="Manual Entry",
            custom_id=f"straight_manual_entry_{parent_view.original_interaction.id}",
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(
            f"Manual Entry button clicked by user {interaction.user.id}"
        )
        self.parent_view.bet_details["game_id"] = "Other"
        self.disabled = True
        for item in self.parent_view.children:
            if isinstance(item, (Select, Button)):
                item.disabled = True

        line_type = self.parent_view.bet_details.get("line_type", "game_line")
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True)
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully.")
            await self.parent_view.edit_message(
                content="Manual entry form opened. Please fill in the details in the popup.",
                view=self.parent_view,
            )
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal: {e}")
            await self.parent_view.edit_message(
                content="❌ Failed to open form. Please restart.", view=None
            )
            self.parent_view.stop()


class CancelButton(Button):
    def __init__(self, parent_view: View):
        super().__init__(
            style=ButtonStyle.red,
            label="Cancel",
            custom_id=f"straight_cancel_{parent_view.original_interaction.id}",
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Cancel button clicked by user {interaction.user.id}")
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True

        bet_serial = self.parent_view.bet_details.get("bet_serial")
        if bet_serial:
            try:
                if hasattr(self.parent_view.bot, "bet_service"):
                    await self.parent_view.bot.bet_service.delete_bet(
                        bet_serial
                    )
                await interaction.response.edit_message(
                    content=f"Bet `{bet_serial}` cancelled.", view=None
                )
            except Exception as e:
                logger.error(f"Failed to delete bet {bet_serial}: {e}")
                await interaction.response.edit_message(
                    content=f"Bet cancellation failed for `{bet_serial}`.",
                    view=None,
                )
        else:
            await interaction.response.edit_message(
                content="Bet workflow cancelled.", view=None
            )
        self.parent_view.stop()


class BetDetailsModal(Modal):
    def __init__(self, line_type: str, is_manual: bool = False):
        super().__init__(title="Enter Bet Details")
        self.line_type = line_type
        self.is_manual = is_manual

        self.team = TextInput(label="Team Bet On", required=True, max_length=100, placeholder="Enter the team name involved in the bet")
        self.add_item(self.team)

        if self.is_manual:
            self.opponent = TextInput(label="Opponent", required=True, max_length=100, placeholder="Enter opponent name")
            self.add_item(self.opponent)

        if line_type == "player_prop":
            self.player_line = TextInput(label="Player - Line", required=True, max_length=100, placeholder="E.g., Connor McDavid - Shots Over 3.5")
            self.add_item(self.player_line)
        else:
            self.line = TextInput(label="Line", required=True, max_length=100, placeholder="E.g., Moneyline, Spread -7.5, Total Over 6.5")
            self.add_item(self.line)

        self.odds = TextInput(label="Odds", required=True, max_length=10, placeholder="Enter American odds (e.g., -110, +200)")
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"BetDetailsModal submitted by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            team = self.team.value.strip()
            opponent = (
                self.opponent.value.strip() if hasattr(self, "opponent")
                else self.view.bet_details.get("away_team_name", "Unknown")
            )
            line_value = (self.player_line.value.strip() if self.line_type == "player_prop" else self.line.value.strip())
            odds_str = self.odds.value.strip()

            if not team or not line_value or not odds_str:
                await interaction.followup.send("❌ All fields are required.", ephemeral=True); return
            try:
                odds_val = float(odds_str.replace("+", ""))
            except ValueError as ve:
                await interaction.followup.send(f"❌ Invalid odds: '{odds_str}'. {ve}", ephemeral=True); return

            self.view.bet_details.update({"line": line_value, "odds_str": odds_str, "odds": odds_val, "team": team, "opponent": opponent})

            try:
                bet_serial = await self.view.bot.bet_service.create_straight_bet(
                    guild_id=interaction.guild_id, user_id=interaction.user.id,
                    game_id=self.view.bet_details.get("game_id") if self.view.bet_details.get("game_id") != "Other" else None,
                    bet_type=self.view.bet_details.get("line_type", "game_line"),
                    team=team, opponent=opponent, line=line_value, units=1.0, # Default units, will be updated
                    odds=odds_val, channel_id=None, league=self.view.bet_details.get("league", "UNKNOWN")
                )
                if not bet_serial: raise BetServiceError("Failed to create bet record (no serial returned).")

                self.view.bet_details["bet_serial"] = bet_serial
                # Store values needed for image generation directly in the view
                self.view.home_team = team 
                self.view.away_team = opponent
                self.view.league = self.view.bet_details.get("league", "UNKNOWN")
                self.view.line = line_value
                self.view.odds = odds_val
                self.view.bet_id = str(bet_serial) # For footer
                logger.debug(f"Bet record {bet_serial} created from modal.")

                # Generate initial preview image (with default units)
                try:
                    bet_slip_generator = await self.view.get_bet_slip_generator()
                    bet_slip_image = await bet_slip_generator.generate_bet_slip(
                        home_team=self.view.home_team,
                        away_team=self.view.away_team,
                        league=self.view.league,
                        line=self.view.line,
                        odds=self.view.odds,
                        units=1.0,  # Default units for initial preview
                        bet_id=self.view.bet_id,
                        timestamp=datetime.now(timezone.utc),
                        bet_type=self.view.bet_details.get("line_type", "straight")
                    )
                    if bet_slip_image:
                        self.view.preview_image_bytes = io.BytesIO()
                        bet_slip_image.save(self.view.preview_image_bytes, format='PNG')
                        self.view.preview_image_bytes.seek(0)
                        logger.debug(f"Initial bet slip image generated for bet {bet_serial}")
                    else:
                        logger.warning(f"Failed to generate initial bet slip image for bet {bet_serial} in modal on_submit.")
                        self.view.preview_image_bytes = None
                except Exception as img_e:
                    logger.exception(f"Error generating initial bet slip image in modal: {img_e}")
                    self.view.preview_image_bytes = None


            except BetServiceError as bse:
                logger.exception(f"BetService error creating bet from modal: {bse}")
                await interaction.followup.send(f"❌ Error creating bet record: {bse}", ephemeral=True)
                self.view.stop(); return
            except Exception as e: # Catch any other errors during bet creation
                logger.exception(f"Failed to create bet from modal: {e}")
                await interaction.followup.send(f"❌ Error saving bet data: {e}", ephemeral=True)
                self.view.stop(); return

            # Modal submission successful, edit the original message and proceed
            await self.view.edit_message(content="Bet details entered. Processing...", view=self.view) # Pass self.view here
            self.view.current_step = 4 # Increment step as modal is considered a step
            await self.view.go_next(interaction) # Pass the modal's interaction

        except Exception as e:
            logger.exception(f"Error in BetDetailsModal on_submit (outer try): {e}")
            # Ensure we use followup if the interaction was already responded to (deferred)
            try:
                await interaction.followup.send("❌ Error processing details.", ephemeral=True)
            except discord.HTTPException: # If followup also fails
                logger.error("Failed to send followup error in BetDetailsModal.")
            if hasattr(self, "view") and self.view: # Ensure view exists
                self.view.stop()


    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("Modal error.", ephemeral=True)
            else:
                await interaction.followup.send("Modal error.", ephemeral=True)
        except discord.HTTPException:
            pass # Avoid erroring further if sending error message fails


class UnitsSelect(Select):
    def __init__(self, parent_view: View):
        self.parent_view = parent_view
        options = [
            SelectOption(label="0.5 Units", value="0.5"),
            SelectOption(label="1 Unit", value="1.0"),
            SelectOption(label="1.5 Units", value="1.5"),
            SelectOption(label="2 Units", value="2.0"),
            SelectOption(label="2.5 Units", value="2.5"),
            SelectOption(label="3 Units", value="3.0"),
        ]
        super().__init__(
            placeholder="Select Units for Bet...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details["units_str"] = self.values[0]
        logger.debug(
            f"Units selected: {self.values[0]} by user {interaction.user.id}"
        )
        self.disabled = True
        # Defer immediately, as image generation and DB update can take time
        await interaction.response.defer(ephemeral=True) # Keep ephemeral if original was

        # Call the handler that now includes image regeneration
        await self.parent_view._handle_units_selection(interaction, float(self.values[0]))
        # _handle_units_selection will update self.parent_view.preview_image_bytes

        # Proceed to next step in the workflow
        await self.parent_view.go_next(interaction)


class ChannelSelect(Select):
    def __init__(self, parent_view: View, channels: List[TextChannel]):
        self.parent_view = parent_view
        # Sort channels alphabetically by name for better UX
        sorted_channels = sorted(channels, key=lambda x: x.name.lower())
        options = [
            SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"Channel ID: {channel.id}"[:100] # Ensure description is not too long
            )
            for channel in sorted_channels[:24] # Max 25 options, leave one for "Other" if needed
        ]
        # Example: Add an "Other" option if you plan to implement manual ID input
        if len(options) < 25: # Only add if space allows
             options.append(SelectOption(label="Other Channel", value="other", description="Select a different channel"))

        super().__init__(
            placeholder="Select channel to post bet...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        channel_id_str = self.values[0]

        if channel_id_str == "other":
            # Handle "Other" selection - e.g., prompt for manual ID input or show error
            await interaction.response.send_message(
                "Manual channel ID input is not yet implemented. Please select from the list.",
                ephemeral=True
            )
            self.disabled = False # Re-enable select for another choice
            await self.parent_view.edit_message(view=self.parent_view) # Update message with re-enabled select
            return

        self.parent_view.bet_details["channel_id"] = int(channel_id_str)
        logger.debug(
            f"Channel selected: {channel_id_str} by user {interaction.user.id}"
        )
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class ConfirmButton(Button):
    def __init__(self, parent_view: View):
        super().__init__(
            style=ButtonStyle.green,
            label="Confirm & Post", # Changed label for clarity
            custom_id=f"straight_confirm_bet_{parent_view.original_interaction.id}",
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Confirm button clicked by user {interaction.user.id}")
        # Disable all buttons in the view to prevent multiple clicks
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        # Edit the message to show buttons are disabled before processing
        await interaction.response.edit_message(view=self.parent_view)
        # Now, proceed to submit the bet
        await self.parent_view.submit_bet(interaction)


# --- Main Workflow View ---
class StraightBetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot, message_to_control: Optional[discord.InteractionMessage] = None):
        super().__init__(timeout=600)  # Extended timeout
        self.original_interaction = interaction # The interaction that started the /bet command
        self.bot = bot
        self.current_step = 0
        self.bet_details: Dict[str, Any] = {"bet_type": "straight"} # Initialize common bet details
        self.games: List[Dict] = [] # To store fetched games for GameSelect
        self.message = message_to_control # The ephemeral message this view controls
        self.is_processing = False # Flag to prevent concurrent processing
        self.latest_interaction = interaction # Keep track of the latest interaction for responses
        self.bet_slip_generator: Optional[BetSlipGenerator] = None
        self.preview_image_bytes: Optional[io.BytesIO] = None

        # Specific attributes for bet slip generation (will be populated during the flow)
        self.home_team: Optional[str] = None
        self.away_team: Optional[str] = None
        self.league: Optional[str] = None
        self.line: Optional[str] = None
        self.odds: Optional[float] = None
        self.bet_id: Optional[str] = None # From bet_serial


    async def get_bet_slip_generator(self) -> BetSlipGenerator:
        """Lazily initialize and return the BetSlipGenerator for the guild."""
        if self.bet_slip_generator is None:
            # Assuming self.bot has a method to get guild-specific generator
            # or a global one if settings are not per-guild for the generator.
            # This needs to be implemented in your BettingBot class.
            self.bet_slip_generator = await self.bot.get_bet_slip_generator(self.original_interaction.guild_id)
        return self.bet_slip_generator

    async def _preload_team_logos(self, team1: str, team2: str, league: str):
        # This is a placeholder. Actual logo loading should happen in BetSlipGenerator
        # or be handled by it managing its own cache.
        pass

    async def start_flow(self, interaction_that_triggered_workflow_start: Interaction):
        """
        Starts the betting workflow.
        `interaction_that_triggered_workflow_start` is the interaction from the
        component (e.g., BetTypeSelect) that initiated this specific workflow.
        """
        logger.debug(f"Starting straight bet workflow on message ID: {self.message.id if self.message else 'None'}")
        if not self.message:
            logger.error("StraightBetWorkflowView.start_flow called but self.message is None.")
            # Respond to the interaction that tried to start this flow
            response_interaction = interaction_that_triggered_workflow_start or self.original_interaction
            try:
                if not response_interaction.response.is_done():
                    await response_interaction.response.send_message("❌ Workflow error: Message context lost.",ephemeral=True)
                else:
                    await response_interaction.followup.send("❌ Workflow error: Message context lost.",ephemeral=True)
            except discord.HTTPException as http_err:
                logger.error(f"Failed to send message context lost error: {http_err}")
            self.stop()
            return
        try:
            # Use the interaction that triggered this flow (e.g., from BetTypeSelect)
            # to make the first call to go_next.
            await self.go_next(interaction_that_triggered_workflow_start)
        except Exception as e:
            logger.exception(f"Failed during initial go_next in StraightBetWorkflow: {e}")
            response_interaction = interaction_that_triggered_workflow_start or self.original_interaction
            try:
                if not response_interaction.response.is_done():
                    await response_interaction.response.send_message("❌ Failed to start bet workflow.", ephemeral=True)
                else:
                    await response_interaction.followup.send("❌ Failed to start bet workflow.", ephemeral=True)
            except discord.HTTPException as http_err:
                logger.error(f"Failed to send workflow start error: {http_err}")
            self.stop()


    async def interaction_check(self, interaction: Interaction) -> bool:
        # Ensure only the original user can interact with this view
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message(
                "You cannot interact with this bet placement.", ephemeral=True
            )
            return False
        self.latest_interaction = interaction # Update latest interaction
        return True

    async def edit_message(self, content: Optional[str]=None, view: Optional[View]=None, embed: Optional[discord.Embed]=None, file: Optional[File]=None):
        """Helper to edit the message this view controls."""
        logger.debug(f"Attempting to edit message: {self.message.id if self.message else 'None'}")
        attachments = [file] if file else discord.utils.MISSING # Use MISSING for no attachments
        if not self.message:
            logger.error("Cannot edit message: self.message is None.")
            return
        try:
            await self.message.edit(content=content, embed=embed, view=view, attachments=attachments)
        except discord.NotFound:
            logger.warning(f"Failed to edit message {self.message.id}: Not Found (likely deleted or timed out). Stopping view.")
            self.stop()
        except discord.HTTPException as e:
            logger.error(f"HTTP error editing message {self.message.id}: {e}", exc_info=True)
            # Consider stopping the view on HTTP errors too, as it might be unrecoverable
        except Exception as e: # Catch any other unexpected errors
            logger.exception(f"Unexpected error editing message {self.message.id}: {e}")


    async def go_next(self, interaction: Interaction):
        """Advance to the next step in the betting workflow."""
        if self.is_processing: # Prevent re-entry if already processing a step
            logger.debug(f"Skipping go_next (step {self.current_step}); already processing.")
            if not interaction.response.is_done(): # Acknowledge if not already done
                try: await interaction.response.defer(ephemeral=True)
                except discord.HTTPException: pass # Ignore if already responded
            return
        self.is_processing = True

        # Defer the interaction if it hasn't been responded to yet
        # This is crucial for long-running operations like API calls or modals
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=True) # Keep ephemeral if original was
            except discord.HTTPException as e:
                logger.warning(f"Defer in go_next failed (interaction ID: {interaction.id}): {e}")
                # If defer fails, we might not be ableto proceed reliably.
                # self.is_processing = False; return # Or try to recover / stop

        try:
            self.current_step += 1
            logger.debug(f"Processing go_next for StraightBetWorkflow: current_step now {self.current_step} (user {interaction.user.id})")
            self.clear_items() # Clear previous UI components
            content = self.get_content() # Get text content for the current step
            new_view_items = [] # List to hold new UI components

            if self.current_step == 1: # League Selection
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"] # Example
                new_view_items.append(LeagueSelect(self, allowed_leagues))
            elif self.current_step == 2: # Line Type Selection
                new_view_items.append(LineTypeSelect(self))
            elif self.current_step == 3: # Game Selection
                league = self.bet_details.get("league")
                if not league:
                    await self.edit_message(content="❌ League not selected. Please restart.", view=None); self.stop(); return
                self.games = [] # Reset games list
                if league != "Other" and hasattr(self.bot, "game_service"): # Check for game_service
                    try:
                        self.games = await self.bot.game_service.get_league_games(interaction.guild_id, league, "scheduled", 25)
                    except Exception as e:
                        logger.exception(f"Error fetching games for {league}: {e}")
                if self.games:
                    new_view_items.append(GameSelect(self, self.games))
                new_view_items.append(ManualEntryButton(self)) # Always allow manual entry
            elif self.current_step == 4: # Bet Details Modal
                line_type = self.bet_details.get("line_type")
                is_manual_modal = self.bet_details.get("game_id") == "Other" or line_type == "player_prop"

                modal = BetDetailsModal(line_type=line_type, is_manual=is_manual_modal)
                modal.view = self # Pass reference to this view for the modal to call back
                try:
                    # The interaction here is the one from the *previous* step's component.
                    # We need to send the modal in response to *that* interaction.
                    await interaction.response.send_modal(modal)
                    # The original message (self.message) should indicate that a modal was opened.
                    await self.edit_message(content="Please fill in the bet details in the popup form.", view=self)
                except discord.HTTPException as e:
                    logger.error(f"Failed to send BetDetailsModal from go_next: {e}")
                    await self.edit_message(content="❌ Error opening details form. Please restart.", view=None)
                    self.stop()
                self.is_processing = False # Release processing lock
                return # Modal submission will trigger the next step via its on_submit
            elif self.current_step == 5: # Units Selection
                if "bet_serial" not in self.bet_details: # Ensure bet was created
                    await self.edit_message(content="❌ Bet creation failed. Please restart.", view=None); self.stop(); return
                new_view_items.append(UnitsSelect(self))
            elif self.current_step == 6: # Channel Selection
                if not self.bet_details.get("units_str"): # Ensure units were selected
                    await self.edit_message(content="❌ Units not selected. Please restart.", view=None); self.stop(); return
                channels = [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.guild.me).send_messages]
                if not channels:
                    await self.edit_message(content="❌ No writable text channels found in this server.", view=None); self.stop(); return
                new_view_items.append(ChannelSelect(self, channels))
            elif self.current_step == 7: # Confirmation
                # Ensure all necessary details are present
                if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units_str']):
                    await self.edit_message(content="❌ Bet details incomplete. Please restart.", view=None); self.stop(); return
                new_view_items.append(ConfirmButton(self))
            else: # Should not happen
                logger.error(f"Unexpected step in StraightBetWorkflow: {self.current_step}")
                await self.edit_message(content="❌ An unexpected error occurred in the workflow.", view=None); self.stop(); return

            # Add cancel button to all steps (except possibly after confirmation)
            if self.current_step < 8 : # Example: don't add cancel after confirm step (step 7 is confirm)
                 new_view_items.append(CancelButton(self))

            for item in new_view_items: self.add_item(item)

            # Handle image preview display
            file_to_send = None
            if self.current_step >= 5 and self.preview_image_bytes: # Show preview from units step onwards
                self.preview_image_bytes.seek(0) # Reset buffer position
                file_to_send = File(self.preview_image_bytes, filename=f"bet_preview_s{self.current_step}.png")

            await self.edit_message(content=content, view=self, file=file_to_send)
        except Exception as e:
            logger.exception(f"Error in go_next (step {self.current_step}): {e}")
            await self.edit_message(content="❌ An error occurred. Please try again or cancel.", view=None) # Simplified error
            self.stop()
        finally:
            self.is_processing = False # Release processing lock


    async def submit_bet(self, interaction: Interaction):
        """Submits the confirmed bet."""
        details = self.bet_details
        bet_serial = details.get("bet_serial") # Already an int if set correctly

        if not bet_serial:
            await self.edit_message(content="❌ Error: Bet ID missing. Cannot submit.", view=None)
            self.stop(); return

        logger.info(f"Submitting bet {bet_serial} by user {interaction.user.id}")
        # Update the ephemeral message to show processing
        await self.edit_message(content=f"Processing bet `{bet_serial}`...", view=None, file=None) # Clear existing file

        try:
            post_channel_id = int(details.get("channel_id"))
            post_channel = self.bot.get_channel(post_channel_id) # Try to get from cache
            if not post_channel: # If not in cache, fetch
                try: post_channel = await self.bot.fetch_channel(post_channel_id)
                except discord.NotFound: raise ValueError(f"Channel ID {post_channel_id} not found.")
                except discord.Forbidden: raise ValueError(f"No permission to fetch channel {post_channel_id}.")
            if not isinstance(post_channel, TextChannel): # Should be TextChannel
                raise ValueError(f"Channel ID {post_channel_id} is not a text channel.")

            # Confirm the bet in the database (mark as confirmed and set channel_id)
            # Assuming db_manager.execute returns rowcount as first element of tuple
            rowcount, _ = await self.bot.db_manager.execute(
                "UPDATE bets SET confirmed = 1, channel_id = %s, status = %s WHERE bet_serial = %s", # Added status
                (post_channel_id, 'pending', bet_serial) # Set initial status to pending upon confirmation
            )
            if not rowcount: # Check if the update was successful
                # It might be that the bet was already confirmed or deleted, log a warning
                logger.warning(f"Failed to confirm bet {bet_serial} in DB or already confirmed/deleted.")
                # Check current status from DB
                current_bet_status = await self.bot.db_manager.fetch_one("SELECT confirmed, channel_id FROM bets WHERE bet_serial = %s", (bet_serial,))
                if not (current_bet_status and current_bet_status['confirmed'] == 1 and current_bet_status['channel_id'] == post_channel_id):
                    raise BetServiceError("Failed to confirm bet in DB and not already in desired state.")
                # If already confirmed to the same channel, we can proceed

            # Prepare the final image for posting
            final_discord_file = None
            if self.preview_image_bytes: # Use the last generated preview
                self.preview_image_bytes.seek(0)
                final_discord_file = discord.File(self.preview_image_bytes, filename=f"bet_slip_{bet_serial}.png")
            else: # Fallback: try to regenerate if preview_image_bytes is None (should not happen if flow is correct)
                logger.warning(f"Preview image bytes not available for bet {bet_serial} at submission. Attempting regeneration.")
                bet_slip_gen = await self.get_bet_slip_generator()
                # Ensure all necessary details for regeneration are available
                regen_image = await bet_slip_gen.generate_bet_slip(
                    home_team=details.get('team'), # Or use self.home_team if populated
                    away_team=details.get('opponent'), # Or use self.away_team
                    league=details.get('league'), # Or use self.league
                    line=details.get('line'), # Or use self.line
                    odds=details.get('odds'), # Or use self.odds
                    units=float(details.get('units_str', 1.0)),
                    bet_id=str(bet_serial),
                    timestamp=datetime.now(timezone.utc), # Use current time for regen
                    bet_type=details.get('line_type', 'straight')
                )
                if regen_image:
                    temp_io = io.BytesIO()
                    regen_image.save(temp_io, "PNG")
                    temp_io.seek(0)
                    final_discord_file = discord.File(temp_io, filename=f"bet_slip_{bet_serial}.png")
                else:
                    logger.error(f"Critical failure to regenerate image for bet {bet_serial}. Posting without image.")

            # --- Webhook Customization ---
            # Fetch capper data for display_name and image_path
            capper_data = await self.bot.db_manager.fetch_one(
                "SELECT display_name, image_path FROM cappers WHERE guild_id = %s AND user_id = %s",
                (interaction.guild_id, interaction.user.id)
            )

            webhook_username = interaction.user.display_name # Default to Discord display name
            webhook_avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None # Default to Discord avatar

            if capper_data:
                if capper_data.get('display_name'):
                    webhook_username = capper_data['display_name']
                if capper_data.get('image_path'):
                    # Assuming image_path is a publicly accessible URL
                    # If it's a relative path, you'd need to construct the full URL
                    # or handle local file uploading if your webhook setup supports it.
                    # For simplicity, assuming it's a direct URL for now.
                    custom_avatar_url = capper_data['image_path']
                    if custom_avatar_url.startswith(('http://', 'https://')):
                        webhook_avatar_url = custom_avatar_url
                    else:
                        # This case needs careful handling depending on where `image_path` points.
                        # If it's a path on the bot's server, the webhook can't directly use it unless it's served.
                        # For now, we'll log and use the Discord avatar as fallback.
                        logger.warning(f"Capper avatar path '{custom_avatar_url}' for user {interaction.user.id} is not a direct URL. Using Discord avatar.")


            # Get or create webhook
            webhooks = await post_channel.webhooks()
            webhook = discord.utils.find(lambda wh: wh.user == self.bot.user, webhooks) # Find a webhook owned by the bot
            if webhook is None:
                webhook = await post_channel.create_webhook(name=f"{self.bot.user.name} Bets") # Create one if none found

            # Send the message via webhook
            # The text "New Straight Bet...etc" is removed by not providing content here.
            # If you want some text, you would add a `content="Your text here"` parameter.
            sent_message = await webhook.send(
                username=webhook_username,
                avatar_url=webhook_avatar_url,
                file=final_discord_file, # Send the image file
                wait=True # Wait for the message to be sent to get the message object
            )
            logger.info(f"Bet {bet_serial} posted to channel {post_channel.id} (Message ID: {sent_message.id}) via webhook by {webhook_username}.")

            # Add to pending reactions if your bot uses reaction-based resolution
            if hasattr(self.bot, 'bet_service') and hasattr(self.bot.bet_service, 'pending_reactions'):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial,
                    'user_id': interaction.user.id,
                    'guild_id': interaction.guild_id,
                    'channel_id': post_channel_id,
                    'bet_type': 'straight' # Or details.get('line_type')
                }

            # Confirm to the user (ephemerally) that the bet was posted
            await self.edit_message(content=f"✅ Bet ID `{bet_serial}` posted to {post_channel.mention}!", view=None)

        except (ValueError, BetServiceError) as err: # Catch specific, known errors
            logger.error(f"Error submitting bet {bet_serial}: {err}", exc_info=True)
            await self.edit_message(content=f"❌ Error submitting bet: {err}", view=None)
        except Exception as e: # Catch any other unexpected errors
            logger.exception(f"General error submitting bet {bet_serial}: {e}")
            await self.edit_message(content=f"❌ An unexpected error occurred: {e}", view=None)
        finally:
            if self.preview_image_bytes: # Clean up the image buffer
                self.preview_image_bytes.close()
                self.preview_image_bytes = None
            self.stop() # Stop the view as the workflow is complete

    async def _handle_units_selection(self, interaction: Interaction, units: float):
        """Handles units selection, updates the DB, and regenerates the preview image."""
        try:
            current_bet_serial = self.bet_details.get('bet_serial')
            if not current_bet_serial:
                logger.error("Cannot handle units selection: bet_serial is missing from bet_details.")
                await interaction.followup.send("Error: Bet ID missing. Cannot update units.", ephemeral=True)
                self.stop()
                return

            # Update units in the database for the existing bet record
            # Assuming db_manager.execute returns a tuple (rowcount, last_id) or similar
            rowcount, _ = await self.bot.db_manager.execute(
                "UPDATE bets SET units = %s WHERE bet_serial = %s",
                (units, current_bet_serial)
            )
            if not rowcount: # If update failed (e.g., bet_serial not found)
                logger.error(f"Failed to update units for bet {current_bet_serial} in DB. Bet might not exist.")
                await interaction.followup.send("Error: Could not update units for the bet.", ephemeral=True)
                self.stop()
                return

            self.bet_details['units'] = units # Update in-memory details as well
            self.bet_details['units_str'] = str(units) # Keep the string version if used elsewhere
            logger.info(f"Units for bet {current_bet_serial} updated to {units} in DB.")

            # Regenerate the bet slip image with the new units
            try:
                # Fetch necessary details for image regeneration if not stored in self
                # For straight bets, these were stored in self.home_team, self.away_team etc.
                # Ensure these are correctly populated before this step.
                if not all([self.home_team, self.league, self.line, self.odds is not None, self.bet_id]):
                    # Attempt to fetch from bet_details if view attributes are not set
                    # This part might need more robust fetching from DB if attributes are missing
                    logger.warning(f"Missing some view attributes for image regen, trying bet_details for bet {current_bet_serial}")
                    db_bet_data = await self.bot.db_manager.fetch_one(
                        "SELECT league, bet_details, odds, created_at, bet_type FROM bets WHERE bet_serial = %s",
                        (current_bet_serial,)
                    )
                    if not db_bet_data:
                        logger.error(f"Bet {current_bet_serial} not found in DB for preview regeneration.")
                        self.preview_image_bytes = None; return

                    b_details = json.loads(db_bet_data['bet_details']) if isinstance(db_bet_data.get('bet_details'), str) else db_bet_data.get('bet_details', {})
                    self.home_team = b_details.get('team', 'N/A')
                    self.away_team = b_details.get('opponent', 'N/A')
                    self.league = db_bet_data['league']
                    self.line = b_details.get('line', 'N/A')
                    self.odds = float(db_bet_data['odds'])
                    self.bet_id = str(current_bet_serial)
                    timestamp_for_image = db_bet_data['created_at'] # Use created_at from DB
                    bet_type_for_image = db_bet_data['bet_type']

                else: # Use existing view attributes
                    timestamp_for_image = datetime.now(timezone.utc) # Or fetch created_at if important
                    bet_type_for_image = self.bet_details.get('line_type', 'straight')


                generator = await self.get_bet_slip_generator()
                bet_slip_image = await generator.generate_bet_slip(
                    home_team=self.home_team,
                    away_team=self.away_team,
                    league=self.league,
                    line=self.line,
                    odds=self.odds,
                    units=float(units), # Use the newly selected units
                    bet_id=self.bet_id,
                    timestamp=timestamp_for_image,
                    bet_type=bet_type_for_image
                )

                if bet_slip_image:
                    if self.preview_image_bytes: self.preview_image_bytes.close() # Close old buffer
                    self.preview_image_bytes = io.BytesIO()
                    bet_slip_image.save(self.preview_image_bytes, format='PNG')
                    self.preview_image_bytes.seek(0) # Reset buffer pointer for next read
                    logger.debug(f"Bet slip preview image updated for bet {current_bet_serial} with units {units}.")
                else:
                    logger.warning(f"Failed to regenerate bet slip preview for bet {current_bet_serial} (units {units}).")
                    if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None # Clear if failed
            except Exception as img_e:
                logger.error(f"Error regenerating bet slip preview in _handle_units_selection for bet {current_bet_serial}: {img_e}", exc_info=True)
                if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None # Clear on error

        except Exception as e:
            logger.error(f"Error in _handle_units_selection for bet {self.bet_details.get('bet_serial', 'N/A')}: {e}", exc_info=True)
            # Send ephemeral error to user who interacted
            try:
                await interaction.followup.send("Error updating units. Please try again.", ephemeral=True)
            except discord.HTTPException: # If followup also fails
                pass
            self.stop() # Stop the view on critical error

    def get_content(self) -> str:
        """Get display content for the current step of the workflow."""
        step_num = self.current_step
        # Basic content, can be enhanced with more details from self.bet_details
        if step_num == 1: return f"**Step {step_num}**: Select League"
        if step_num == 2: return f"**Step {step_num}**: Select Line Type"
        if step_num == 3: return f"**Step {step_num}**: Select Game or Enter Manually"
        if step_num == 4: return f"**Step {step_num}**: Fill details in the form for your bet." # After modal
        if step_num == 5: # Units selection
            preview_info = "(Preview below)" if self.preview_image_bytes else "(Preview image failed to generate)"
            return f"**Step {step_num}**: Bet details captured {preview_info}. Select Units for your bet."
        if step_num == 6: # Channel selection
            units = self.bet_details.get('units_str', 'N/A')
            preview_info = "(Preview below with updated units)" if self.preview_image_bytes else "(Preview image failed)"
            return f"**Step {step_num}**: Units: `{units}` {preview_info}. Select Channel to post your bet."
        if step_num == 7: # Confirmation
            preview_info = "(Final Preview below)" if self.preview_image_bytes else "(Image generation failed)"
            return f"**Confirm Your Bet** {preview_info}"
        return "Processing your bet request..."
