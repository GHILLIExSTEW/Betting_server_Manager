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
)
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union, Any
from datetime import datetime, timezone
import io
import os

# Use relative imports
try:
    from ..utils.errors import (
        BetServiceError,
        ValidationError,
        GameNotFoundError,
    )
    from ..utils.image_generator import BetSlipGenerator
    from discord.ext import commands
except ImportError:
    # Fallback for running script directly or different structure
    from utils.errors import (
        BetServiceError,
        ValidationError,
        GameNotFoundError,
    )
    from utils.image_generator import BetSlipGenerator
    from discord.ext import commands

logger = logging.getLogger(__name__)


# --- UI Component Classes ---
class LeagueSelect(Select):
    def __init__(self, parent_view, leagues: List[str]):
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
    def __init__(self, parent_view):
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
    def __init__(self, parent_view, games: List[Dict]):
        self.parent_view = parent_view
        options = []
        for game in games[:24]:  # Limit to 24 options for discord limits
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
                        f"Could not parse game start_time string: {start_dt_obj}"
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
            else:
                logger.warning(
                    f"Could not find full details for selected game ID {selected_game_id}"
                )
        logger.debug(
            f"Game selected: {selected_game_id} by user {interaction.user.id}"
        )
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class HomePlayerSelect(Select):
    def __init__(self, parent_view, players: List[str], team_name: str):
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
    def __init__(self, parent_view, players: List[str], team_name: str):
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
    def __init__(self, parent_view):
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
        # Also disable other interactive elements on this view before modal
        for item in self.parent_view.children:
            if isinstance(item, (Select, CancelButton)):
                item.disabled = True

        line_type = self.parent_view.bet_details.get("line_type", "game_line")
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True)
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully")
            # Update the message the button was on (self.parent_view.message)
            # The interaction from send_modal can't be used to edit the original message directly.
            # We must rely on self.parent_view.edit_message and ensure it targets self.parent_view.message
            await self.parent_view.edit_message(
                interaction=interaction, # Pass button interaction
                content="Manual entry form opened. Please fill in the details.",
                view=self.parent_view, # Keep the (now disabled) view
            )
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal: {e}")
            try:
                await self.parent_view.edit_message(
                    interaction=interaction, # Use button interaction for this edit
                    content="❌ Failed to open manual entry form. Please restart the /bet command.",
                    view=None,
                )
            except discord.HTTPException as e2:
                logger.error(f"Failed to edit message after modal error: {e2}")
            self.parent_view.stop()


class CancelButton(Button):
    def __init__(self, parent_view):
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
                    logger.info(
                        f"Bet {bet_serial} cancelled and deleted by user {interaction.user.id}."
                    )
                    await interaction.response.edit_message(
                        content=f"Bet `{bet_serial}` cancelled and records deleted.",
                        view=None,
                    )
                else:
                    logger.error(
                        "BetService not found on bot instance during cancellation."
                    )
                    await interaction.response.edit_message(
                        content="Cancellation failed (Internal Error).",
                        view=None,
                    )
            except Exception as e:
                logger.error(
                    f"Failed to delete bet {bet_serial} during cancellation: {e}"
                )
                await interaction.response.edit_message(
                    content=f"Bet `{bet_serial}` cancellation process failed. Please contact admin if needed.",
                    view=None,
                )
        else:
            await interaction.response.edit_message(
                content="Bet workflow cancelled.", view=None
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
            placeholder="Enter the team name involved in the bet",
        )
        self.add_item(self.team)

        if self.is_manual:
            self.opponent = TextInput(
                label="Opponent",
                required=True,
                max_length=100,
                placeholder="Enter opponent name",
            )
            self.add_item(self.opponent)

        if line_type == "player_prop":
            self.player_line = TextInput(
                label="Player - Line",
                required=True,
                max_length=100,
                placeholder="E.g., Connor McDavid - Shots Over 3.5",
            )
            self.add_item(self.player_line)
        else:
            self.line = TextInput(
                label="Line",
                required=True,
                max_length=100,
                placeholder="E.g., Moneyline, Spread -7.5, Total Over 6.5",
            )
            self.add_item(self.line)

        self.odds = TextInput(
            label="Odds",
            required=True,
            max_length=10,
            placeholder="Enter American odds (e.g., -110, +200)",
        )
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(
            f"BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual} by user {interaction.user.id}"
        )
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            team = self.team.value.strip()
            opponent = (
                self.opponent.value.strip()
                if hasattr(self, "opponent")
                else self.view.bet_details.get("away_team_name", "Unknown")
            )
            if self.line_type == "player_prop":
                line = self.player_line.value.strip()
            else:
                line = self.line.value.strip()
            odds_str = self.odds.value.strip()

            if not team or not line or not odds_str:
                await interaction.followup.send(
                    "❌ Team, Line, and Odds are required. Please try again.",
                    ephemeral=True,
                )
                return

            try:
                odds_val_str = odds_str.replace("+", "")
                if not odds_val_str:
                    raise ValueError("Odds cannot be empty.")
                odds_val = float(odds_val_str)
                if -100 < odds_val < 100 and odds_val != 0:
                    raise ValueError(
                        "Odds cannot be between -99 and +99 (excluding 0)."
                    )
            except ValueError as ve:
                logger.warning(
                    f"Invalid odds entered: {odds_str} - Error: {ve}"
                )
                await interaction.followup.send(
                    f"❌ Invalid odds format: '{odds_str}'. Use American odds (e.g., -110, +150). {ve}",
                    ephemeral=True,
                )
                return

            if not self.is_manual and "away_team_name" in self.view.bet_details:
                opponent = self.view.bet_details["away_team_name"]
                if "home_team_name" in self.view.bet_details and team.lower() != self.view.bet_details["home_team_name"].lower():
                    # This case is tricky: user typed a team different from game context.
                    # Decide how to handle: prioritize modal input or game context?
                    # For now, if it's not manual and game details exist, we assume the modal 'team' is primary.
                    # If game context should override, then 'team' should be set to home_team_name or away_team_name based on user intent.
                    pass # Using modal 'team' for now.

            current_bet_details = { # Changed variable name for clarity
                "game_id": (
                    self.view.bet_details.get("game_id")
                    if self.view.bet_details.get("game_id") != "Other"
                    else None
                ),
                "bet_type": self.line_type,
                "team": team,
                "opponent": opponent,
                "line": line,
                "odds": odds_val,
                "league": self.view.bet_details.get("league", "NHL"),
            }
            try:
                bet_serial = (
                    await self.view.bot.bet_service.create_straight_bet(
                        guild_id=interaction.guild_id,
                        user_id=interaction.user.id,
                        game_id=current_bet_details["game_id"],
                        bet_type=current_bet_details["bet_type"],
                        team=current_bet_details["team"],
                        opponent=current_bet_details["opponent"],
                        line=current_bet_details["line"],
                        units=1.00,  # Placeholder, updated later
                        odds=current_bet_details["odds"],
                        channel_id=None,  # Set later
                        league=current_bet_details["league"],
                    )
                )
                if bet_serial is None or bet_serial == 0:
                    logger.error(
                        f"Bet creation failed for user {interaction.user.id}, received bet_serial: {bet_serial}"
                    )
                    await interaction.followup.send(
                        "❌ Failed to create bet record. Please try again or contact admin.",
                        ephemeral=True,
                    )
                    self.view.stop()
                    return

                # Store crucial details from modal/processing into the view's main bet_details
                self.view.bet_details["bet_serial"] = bet_serial
                self.view.bet_details["line"] = line
                self.view.bet_details["odds_str"] = odds_str
                self.view.bet_details["odds"] = odds_val
                self.view.bet_details["team"] = team
                self.view.bet_details["opponent"] = opponent
                # 'league' and 'game_id' should already be in self.view.bet_details
                logger.debug(
                    f"Created straight bet with serial {bet_serial} via modal."
                )
                await self.view._preload_team_logos(
                    team, opponent, current_bet_details["league"]
                )
            except Exception as e:
                logger.exception(
                    f"Failed to create straight bet in DB from modal: {e}"
                )
                await interaction.followup.send(
                    "❌ Failed to save bet details. Please try again.",
                    ephemeral=True,
                )
                self.view.stop()
                return

            self.view.current_step = 4 # Ensure go_next proceeds from here
            # Edit the main view message, not the modal's ephemeral followup
            await self.view.edit_message(
                interaction=None, # Indicates an internal update to self.message
                content="Bet details entered. Processing next step...",
                view=self.view,
            )
            # Pass the modal's interaction to go_next so it can use it to edit its original response (the ack)
            await self.view.go_next(interaction)
        except Exception as e:
            logger.exception(f"Error in BetDetailsModal on_submit: {e}")
            await interaction.followup.send(
                "❌ Failed to process bet details. Please try again.",
                ephemeral=True,
            )
            if hasattr(self, "view") and self.view:
                self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred with the bet details modal.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred processing the bet details modal.",
                    ephemeral=True,
                )
        except discord.HTTPException:
            logger.warning("Could not send error followup for BetDetailsModal.")
        if hasattr(self, "view") and self.view:
            self.view.stop()


class UnitsSelect(Select):
    def __init__(self, parent_view):
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
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class ChannelSelect(Select):
    def __init__(self, parent_view, channels: List[TextChannel]):
        self.parent_view = parent_view
        options = [
            SelectOption(label=f"#{channel.name}", value=str(channel.id))
            for channel in channels[:25]
        ]
        if not options:
            options.append(
                SelectOption(
                    label="No Writable Channels Found", value="none", emoji="❌"
                )
            )
        super().__init__(
            placeholder="Select Channel to Post Bet...",
            options=options,
            min_values=1,
            max_values=1,
            disabled=not options or options[0].value == "none",
        )

    async def callback(self, interaction: Interaction):
        selected_value = self.values[0]
        if selected_value == "none":
            await interaction.response.defer()
            return
        self.parent_view.bet_details["channel_id"] = int(selected_value)
        logger.debug(
            f"Channel selected: {selected_value} by user {interaction.user.id}"
        )
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class ConfirmButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Confirm & Post",
            custom_id=f"straight_confirm_bet_{parent_view.original_interaction.id}",
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Confirm button clicked by user {interaction.user.id}")
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        # Edit the message the button is on.
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.submit_bet(interaction)


# --- Main Workflow View ---
class StraightBetWorkflowView(View):
    def __init__(
        self,
        interaction: Interaction, # The original /bet command interaction
        bot: commands.Bot,
        message_to_control: Optional[discord.InteractionMessage] = None,
    ):
        super().__init__(timeout=600) # Increased timeout
        self.original_interaction = interaction
        self.bot = bot
        self.current_step = 0
        self.bet_details: Dict[str, Any] = {"bet_type": "straight"}
        self.games: List[Dict] = []
        self.message = message_to_control # The message this view will manage
        self.is_processing = False
        # latest_interaction tracks the interaction from the most recent component/modal
        self.latest_interaction = interaction
        self.bet_slip_generator = BetSlipGenerator()
        self.preview_image_bytes: Optional[io.BytesIO] = None
        self.team_logos: Dict[str, Optional[str]] = {}

    async def _preload_team_logos(
        self, team1: str, team2: str, league: str
    ):
        if not hasattr(self, "bet_slip_generator"):
            return
        keys = [f"{team1}_{league}", f"{team2}_{league}"]
        for key in keys:
            if key not in self.team_logos:
                try:
                    _ = self.bet_slip_generator._load_team_logo(
                        key.split("_")[0], league
                    )
                    self.team_logos[key] = "checked"
                except Exception as e:
                    logger.error(f"Error preloading logo for {key}: {e}")
                    self.team_logos[key] = None

    async def start_flow(self, interaction_that_triggered_workflow_start: Interaction):
        # interaction_that_triggered_workflow_start is the component interaction from BetTypeSelect
        logger.debug(
            f"Starting straight bet workflow for user {self.original_interaction.user} (ID: {self.original_interaction.user.id})"
        )
        if not self.message:
            logger.error(
                "StraightBetWorkflowView.start_flow called but self.message is None."
            )
            if interaction_that_triggered_workflow_start.response.is_done():
                await interaction_that_triggered_workflow_start.followup.send(
                    "❌ Workflow error: Message context lost.", ephemeral=True
                )
            else: # Should have been responded to by component callback
                await interaction_that_triggered_workflow_start.response.send_message(
                    "❌ Workflow error: Message context lost.", ephemeral=True
                )
            self.stop()
            return

        try:
            # The first call to go_next uses the component interaction from BetTypeSelect.
            # This interaction was already used to edit BetTypeView's message.
            # edit_message in go_next will use interaction.edit_original_response()
            # which will correctly target self.message.
            await self.go_next(interaction_that_triggered_workflow_start)
        except discord.HTTPException as e:
            logger.error(
                f"Failed during initial go_next in StraightBetWorkflowView: {e}"
            )
            if interaction_that_triggered_workflow_start.response.is_done():
                await interaction_that_triggered_workflow_start.followup.send(
                    "❌ Failed to start bet workflow. Please try again.",
                    ephemeral=True,
                )
            self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            logger.debug(
                f"Unauthorized interaction attempt by {interaction.user} (ID: {interaction.user.id})"
            )
            await interaction.response.send_message(
                "You cannot interact with this bet placement.", ephemeral=True
            )
            return False
        self.latest_interaction = interaction
        return True

    async def edit_message(
        self,
        interaction: Optional[Interaction] = None,
        content: Optional[str] = None,
        view: Optional[View] = None,
        embed: Optional[discord.Embed] = None,
        file: Optional[File] = None,
    ):
        log_info = (
            f"edit_message called: content={content is not None}, "
            f"view={view is not None}, embed={embed is not None}, "
            f"file={file is not None}"
        )
        if interaction:
            log_info += (
                f" triggered by interaction {interaction.id} "
                f"(type: {interaction.type})"
            )
        else:
            log_info += " (internal call)"
        logger.debug(log_info)

        attachments = [file] if file else []

        try:
            if self.message:
                if interaction and interaction.type == discord.InteractionType.modal_submit:
                    logger.debug(f"Modal submission interaction {interaction.id}. Editing self.message (ID: {self.message.id}) directly.")
                    await self.message.edit(content=content, embed=embed, view=view, attachments=attachments)
                    # Acknowledge the modal interaction separately if it wasn't deferred in on_submit
                    if not interaction.response.is_done():
                        await interaction.response.defer(ephemeral=True) # Should be done in modal on_submit
                elif interaction: # Component interaction (button, select)
                    logger.debug(
                        f"Component interaction {interaction.id} (type {interaction.type}). "
                        f"Is done? {interaction.response.is_done()}. Using edit_original_response to edit message."
                    )
                    # This interaction should have been deferred in its callback.
                    # edit_original_response will edit the message the component was on (i.e., self.message).
                    await interaction.edit_original_response(
                        content=content, embed=embed, view=view, attachments=attachments
                    )
                    # Refresh self.message instance if it was successfully edited
                    try:
                        self.message = await interaction.original_response()
                    except discord.NotFound:
                        logger.warning(f"Original response for interaction {interaction.id} not found when trying to refresh self.message.")

                else: # No interaction provided, internal call
                    logger.debug(f"Internal call to edit_message. Editing self.message (ID: {self.message.id}) directly.")
                    await self.message.edit(
                        content=content, embed=embed, view=view, attachments=attachments
                    )
            else: # self.message is None
                logger.error("edit_message called but self.message is None. Attempting to use interaction if available.")
                if interaction:
                    if interaction.response.is_done():
                        await interaction.edit_original_response(content=content, embed=embed, view=view, attachments=attachments)
                        self.message = await interaction.original_response() # Try to capture the message
                    else:
                        await interaction.response.send_message(content=content, embed=embed, view=view, files=attachments, ephemeral=True)
                        self.message = await interaction.original_response()
                else:
                    logger.error("Cannot edit message: No self.message and no interaction provided.")


        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(
                f"Failed to edit message: {e}. Interaction: {interaction.id if interaction else 'N/A'}",
                exc_info=True,
            )
            error_interaction_for_followup = interaction or self.latest_interaction
            if (
                error_interaction_for_followup
                and error_interaction_for_followup.response.is_done()
            ):
                try:
                    followup_content = content or "Updating display..."
                    await error_interaction_for_followup.followup.send(
                        followup_content,
                        ephemeral=True,
                        view=view if view and isinstance(view, View) else None,
                        files=attachments or [],
                    )
                except discord.HTTPException as fe:
                    logger.error(
                        f"Failed to send followup after message edit error for {error_interaction_for_followup.id}: {fe}",
                        exc_info=True,
                    )

        except Exception as e:
            logger.exception(
                f"Unexpected error editing StraightBetWorkflowView message: {e}"
            )
            error_interaction_for_response = (
                interaction or self.latest_interaction or self.original_interaction
            )
            try:
                if (
                    error_interaction_for_response
                    and error_interaction_for_response.response.is_done()
                ):
                    await error_interaction_for_response.followup.send(
                        "❌ An unexpected error occurred updating the display.",
                        ephemeral=True,
                    )
                elif (
                    error_interaction_for_response
                    and not error_interaction_for_response.response.is_done()
                ):
                    await error_interaction_for_response.response.send_message(
                        "❌ An unexpected error occurred updating the display.",
                        ephemeral=True,
                    )
            except discord.HTTPException:
                logger.error(
                    "Failed to send error message to user after unexpected edit error."
                )

    async def go_next(self, interaction: Interaction):
        if self.is_processing:
            logger.debug(
                f"Skipping go_next call; already processing step {self.current_step} for user {interaction.user.id}"
            )
            if not interaction.response.is_done():
                try:
                    await interaction.response.defer()
                except discord.HTTPException:
                    pass
            return
        self.is_processing = True

        if not interaction.response.is_done():
            try:
                logger.debug(
                    f"Deferring interaction {interaction.id} at start of go_next as it wasn't done."
                )
                await interaction.response.defer()
            except discord.HTTPException as e:
                logger.warning(
                    f"Failed to defer interaction {interaction.id} in go_next (may have been responded to): {e}"
                )

        try:
            logger.debug(
                f"Processing go_next: current_step={self.current_step} for user {interaction.user.id} (interaction {interaction.id})"
            )
            self.clear_items()
            self.current_step += 1
            step_content = f"**Step {self.current_step}**"
            file_to_send = None
            logger.debug(f"Entering step {self.current_step}")

            if self.current_step == 1:
                allowed_leagues = [
                    "NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF",
                    "Soccer", "Tennis", "UFC/MMA",
                ]
                self.add_item(LeagueSelect(self, allowed_leagues))
                self.add_item(CancelButton(self))
                step_content += ": Select League"
                await self.edit_message(
                    interaction, content=step_content, view=self
                )
                self.is_processing = False
                return
            elif self.current_step == 2:
                self.add_item(LineTypeSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Line Type"
                await self.edit_message(
                    interaction, content=step_content, view=self
                )
                self.is_processing = False
                return
            elif self.current_step == 3:
                league = self.bet_details.get("league")
                if not league:
                    logger.error("No league selected for game selection step.")
                    await self.edit_message(
                        interaction,
                        content="❌ No league selected. Please start over.",
                        view=None,
                    )
                    self.stop()
                    self.is_processing = False
                    return

                self.games = []
                if league != "Other" and hasattr(self.bot, "game_service"):
                    try:
                        self.games = await self.bot.game_service.get_league_games(
                            guild_id=interaction.guild_id,
                            league=league,
                            status="scheduled",
                            limit=25,
                        )
                    except Exception as e:
                        logger.exception(
                            f"Error fetching games for league {league}: {e}"
                        )

                if self.games:
                    self.add_item(GameSelect(self, self.games))
                    self.add_item(ManualEntryButton(self))
                else:
                    self.add_item(ManualEntryButton(self))

                self.add_item(CancelButton(self))
                msg_content = (
                    f"{step_content}: Select Game for {league} (or Enter Manually)"
                    if self.games
                    else f"{step_content}: No games for {league}. Enter details manually."
                    if league != "Other"
                    else f"{step_content}: Enter game details manually."
                )
                await self.edit_message(
                    interaction, content=msg_content, view=self
                )
                self.is_processing = False
                return

            elif self.current_step == 4:
                line_type = self.bet_details.get("line_type")
                game_id = self.bet_details.get("game_id")
                is_manual = game_id == "Other"

                if interaction.type == discord.InteractionType.modal_submit:
                    logger.debug(
                        "go_next called after modal submission. Advancing to step 5."
                    )
                    self.current_step = 5
                    # Fall through to the self.current_step == 5 block
                
                elif line_type == "player_prop" and not is_manual:
                    # Player prop logic
                    home_players, away_players = [], [] # Placeholder
                    # ... fetch players ...
                    if home_players or away_players:
                        # ... add player selects ...
                        await self.edit_message(interaction, content="Select Player for Prop...", view=self)
                        self.is_processing = False
                        return # Wait for player selection
                    else:
                        is_manual = True # Force manual if no players

                if is_manual or (line_type != "player_prop" and interaction.type != discord.InteractionType.modal_submit):
                    modal = BetDetailsModal(
                        line_type=line_type, is_manual=is_manual
                    )
                    modal.view = self
                    try:
                        await interaction.response.send_modal(modal)
                        # Update the main message (self.message) after modal is sent
                        await self.edit_message(
                            interaction, # This interaction's original_response is the component message
                            content="Please fill out the bet details in the form above.",
                            view=self
                        )
                    except discord.HTTPException as e:
                        logger.error(f"Failed to send BetDetailsModal: {e}")
                        await self.edit_message(interaction, content="❌ Failed to open details form.", view=None)
                        self.stop()
                    self.is_processing = False
                    return # Wait for modal

                # If modal was submitted and auto-advanced step in on_submit,
                # this 'if' might now be for step 5. Or if it's player_prop and we selected a player.
                if not self.bet_details.get("bet_serial"):
                    logger.warning("Step 4: Bet serial not set. Modal/player prop might not have completed.")
                    self.current_step -= 1 # Stay on current effective step
                    self.is_processing = False
                    return

            # Explicit check for step 5 after potential modifications in step 4
            if self.current_step == 5:
                if "bet_serial" not in self.bet_details or not self.bet_details["bet_serial"]:
                    logger.error("Bet serial missing before unit selection step.")
                    await self.edit_message(
                        interaction,
                        content="❌ Error: Bet record not created. Please restart.",
                        view=None,
                    )
                    self.stop()
                    self.is_processing = False
                    return
                self.add_item(UnitsSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Units for Bet"
                await self.edit_message(
                    interaction, content=step_content, view=self
                )
                self.is_processing = False
                return
            elif self.current_step == 6:
                # ... (Preview and Channel Select logic as before) ...
                if "units_str" not in self.bet_details: # Guard
                    await self.edit_message(interaction, content="❌ Units missing.", view=None); self.stop(); self.is_processing = False; return
                # ... (image generation) ...
                await self.edit_message(
                    interaction, content=step_content, view=self, file=file_to_send
                )
                self.is_processing = False
                return
            elif self.current_step == 7:
                # ... (Confirmation logic as before) ...
                if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units_str', 'odds_str', 'line', 'team', 'league']): #Guard
                     await self.edit_message(interaction, content="❌ Details incomplete.", view=None); self.stop(); self.is_processing = False; return
                # ... (text and image setup) ...
                await self.edit_message(
                    interaction, content=confirmation_text, view=self, file=file_to_send
                )
                self.is_processing = False
                return
            else:
                logger.error(
                    f"StraightBetWorkflowView reached unexpected step: {self.current_step}"
                )
                await self.edit_message(
                    interaction,
                    content="❌ Invalid step reached. Please start over.",
                    view=None,
                )
                self.stop()
                # self.is_processing will be set to False in finally

        except Exception as e:
            logger.exception(
                f"Error in straight bet workflow step {self.current_step} (interaction {interaction.id}): {e}"
            )
            error_target_interaction = (
                interaction or self.latest_interaction or self.original_interaction
            )
            await self.edit_message(
                error_target_interaction,
                content="❌ An unexpected error occurred.",
                view=None,
            )
            self.stop()
        finally:
            self.is_processing = False

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        bet_serial = details.get("bet_serial")
        if not bet_serial:
            logger.error("Attempted to submit bet without a bet_serial.")
            await self.edit_message(
                interaction,
                content="❌ Error: Bet ID missing. Cannot submit.",
                view=None,
            )
            self.stop()
            return

        logger.info(
            f"Submitting straight bet {bet_serial} for user {interaction.user} (ID: {interaction.user.id})"
        )
        # The interaction here is from the ConfirmButton.
        # Its original_response is self.message. Edit it.
        await self.edit_message(
            interaction, # This will use interaction.edit_original_response()
            content="Processing and posting bet...",
            view=None,
            file=None,
        )

        try:
            post_channel_id = details.get("channel_id")
            post_channel = (
                self.bot.get_channel(post_channel_id) if post_channel_id else None
            )
            if not post_channel or not isinstance(post_channel, TextChannel):
                logger.error(
                    f"Invalid or inaccessible channel {post_channel_id} for bet {bet_serial}"
                )
                raise ValueError(
                    f"Could not find text channel <#{post_channel_id}> to post bet."
                )

            units = float(details.get("units_str", 1.0))
            odds = float(details.get("odds", 0))

            update_query = """
                UPDATE bets
                SET units = %s, odds = %s, channel_id = %s, confirmed = 1, status = 'pending'
                WHERE bet_serial = %s AND (confirmed = 0 OR confirmed IS NULL)
            """
            rowcount, _ = await self.bot.db_manager.execute(
                update_query, units, odds, post_channel_id, bet_serial
            )

            if rowcount is None or rowcount == 0:
                check_query = "SELECT confirmed, channel_id, units, status FROM bets WHERE bet_serial = %s"
                existing_bet = await self.bot.db_manager.fetch_one(
                    check_query, (bet_serial,)
                )
                if existing_bet and existing_bet["confirmed"] == 1:
                    logger.warning(
                        f"Bet {bet_serial} was already confirmed. Status: {existing_bet['status']}. Proceeding with posting."
                    )
                    post_channel_id = existing_bet["channel_id"]
                    post_channel = (
                        self.bot.get_channel(post_channel_id)
                        if post_channel_id
                        else post_channel
                    )
                    units = float(existing_bet["units"]) 
                else:
                    logger.error(
                        f"Failed to update bet {bet_serial} to confirmed. Rowcount: {rowcount}. Existing: {existing_bet}"
                    )
                    raise BetServiceError(
                        "Failed to confirm bet details in database."
                    )
            
            final_image_bytes = self.preview_image_bytes
            if not final_image_bytes:
                logger.warning(f"Preview image for {bet_serial} lost. Regenerating.")
                try:
                    home_team = details.get("team", "Unknown")
                    opponent = details.get("opponent", "Unknown")
                    bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                        home_team=home_team, away_team=opponent,
                        league=details.get("league", "NHL"), line=details.get("line", "N/A"),
                        odds=odds, units=units, bet_id=str(bet_serial),
                        timestamp=datetime.now(timezone.utc), bet_type="straight"
                    )
                    final_image_bytes = io.BytesIO()
                    bet_slip_image.save(final_image_bytes, format="PNG")
                except Exception as img_err:
                    logger.exception(f"Failed to regenerate bet slip image for {bet_serial}: {img_err}")
                    raise BetServiceError("Failed to generate final bet slip image.") from img_err

            if not final_image_bytes:
                 raise ValueError(f"Final image data is missing for bet {bet_serial}.")

            final_image_bytes.seek(0)
            discord_file = File(
                final_image_bytes, filename=f"bet_slip_{bet_serial}.png"
            )

            role_mention = ""
            display_name = interaction.user.display_name
            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            try:
                settings = await self.bot.db_manager.fetch_one(
                    "SELECT authorized_role, member_role FROM guild_settings WHERE guild_id = %s",
                    (interaction.guild_id,),
                )
                if settings:
                    role_id = settings.get("authorized_role") or settings.get("member_role")
                    if role_id:
                        role = interaction.guild.get_role(int(role_id))
                        if role: role_mention = role.mention
            except Exception as e:
                logger.error(f"Error fetching roles for bet {bet_serial}: {e}")

            webhook = None
            try:
                webhooks = await post_channel.webhooks()
                webhook_name_target = f"{self.bot.user.name} Bets"
                webhook = next((wh for wh in webhooks if wh.user and wh.user.id == self.bot.user.id and wh.name == webhook_name_target), None) \
                       or next((wh for wh in webhooks if wh.user and wh.user.id == self.bot.user.id), None) \
                       or await post_channel.create_webhook(name=webhook_name_target)
            except Exception as e:
                logger.error(f"Webhook error for bet {bet_serial}: {e}")
                raise ValueError(f"Webhook setup failed: {e}")

            content_msg = role_mention if role_mention else "" # Ensure content is not None
            sent_message = await webhook.send(
                content=content_msg,
                file=discord_file,
                username=display_name[:80],
                avatar_url=avatar_url,
                wait=True,
            )
            logger.info(
                f"Bet slip image sent for bet {bet_serial}, message ID: {sent_message.id}"
            )

            if hasattr(self.bot, "bet_service") and hasattr(self.bot.bet_service, "pending_reactions"):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    "bet_serial": bet_serial, "user_id": interaction.user.id,
                    "guild_id": interaction.guild_id, "channel_id": post_channel_id,
                    "line": details.get("line"), "league": details.get("league"),
                    "bet_type": "straight"
                }

            # Edit the ephemeral message associated with the ConfirmButton's interaction
            await self.edit_message(
                interaction,
                content=f"✅ Bet placed successfully! (ID: `{bet_serial}`). Posted to {post_channel.mention}.",
                view=None
            )
        except (ValidationError, BetServiceError, ValueError) as e:
            logger.error(f"Error submitting bet {bet_serial}: {e}", exc_info=True)
            await self.edit_message(interaction, content=f"❌ Error placing bet: {e}", view=None)
        except Exception as e:
            logger.exception(
                f"Unexpected error submitting bet {bet_serial}: {e}"
            )
            await self.edit_message(interaction, content="❌ An unexpected error occurred while posting the bet.", view=None)
        finally:
            if self.preview_image_bytes:
                self.preview_image_bytes.close()
                self.preview_image_bytes = None
            self.stop()
