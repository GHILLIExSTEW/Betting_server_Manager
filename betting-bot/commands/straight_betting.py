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
                    team=team, opponent=opponent, line=line_value, units=1.0,
                    odds=odds_val, channel_id=None, league=self.view.bet_details.get("league", "UNKNOWN")
                )
                if not bet_serial: raise BetServiceError("Failed to create bet record (no serial returned).")

                self.view.bet_details["bet_serial"] = bet_serial
                self.view.home_team = team; self.view.away_team = opponent
                self.view.league = self.view.bet_details.get("league", "UNKNOWN"); self.view.line = line_value
                self.view.odds = odds_val; self.view.bet_id = str(bet_serial)
                logger.debug(f"Bet record {bet_serial} created from modal.")

                try:
                    bet_slip_generator = await self.view.get_bet_slip_generator()

                    # MODIFIED: Added await here
                    bet_slip_image = await bet_slip_generator.generate_bet_slip(
                        home_team=self.view.home_team, away_team=self.view.away_team,
                        league=self.view.league, line=self.view.line, odds=self.view.odds,
                        units=1.0, bet_id=self.view.bet_id, timestamp=datetime.now(timezone.utc),
                        bet_type=self.view.bet_details.get("line_type", "straight")
                    )
                    if bet_slip_image:
                        self.view.preview_image_bytes = io.BytesIO()
                        # MODIFIED: Correctly call save on the Image object
                        bet_slip_image.save(self.view.preview_image_bytes, format='PNG')
                        self.view.preview_image_bytes.seek(0)
                        logger.debug(f"Bet slip image generated for bet {bet_serial}")
                    else:
                        logger.warning(f"Failed to generate bet slip image for bet {bet_serial} in modal on_submit.")
                        self.view.preview_image_bytes = None
                except Exception as img_e:
                    logger.exception(f"Error generating bet slip image in modal: {img_e}")
                    self.view.preview_image_bytes = None

            except BetServiceError as bse:
                logger.exception(f"BetService error creating bet from modal: {bse}")
                await interaction.followup.send(f"❌ Error creating bet record: {bse}", ephemeral=True)
                self.view.stop(); return
            except Exception as e:
                logger.exception(f"Failed to create bet from modal: {e}")
                await interaction.followup.send(f"❌ Error saving bet data: {e}", ephemeral=True)
                self.view.stop(); return

            await self.view.edit_message(content="Bet details entered. Processing...", view=self.view)
            self.view.current_step = 4
            await self.view.go_next(interaction)

        except Exception as e:
            logger.exception(f"Error in BetDetailsModal on_submit (outer try): {e}")
            try: await interaction.followup.send("❌ Error processing details.", ephemeral=True)
            except discord.HTTPException: logger.error("Failed to send followup error in BetDetailsModal.")
            if hasattr(self, "view") and self.view: self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            if not interaction.response.is_done(): await interaction.response.send_message("Modal error.", ephemeral=True)
            else: await interaction.followup.send("Modal error.", ephemeral=True)
        except discord.HTTPException: pass


class UnitsSelect(Select):
    def __init__(self, parent_view: View):
        self.parent_view = parent_view
        options = [
            SelectOption(label="0.5 Units", value="0.5"), SelectOption(label="1 Unit", value="1.0"),
            SelectOption(label="1.5 Units", value="1.5"), SelectOption(label="2 Units", value="2.0"),
            SelectOption(label="2.5 Units", value="2.5"), SelectOption(label="3 Units", value="3.0"),
        ]
        super().__init__(placeholder="Select Units for Bet...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details["units_str"] = self.values[0]
        logger.debug(f"Units selected: {self.values[0]} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer(ephemeral=True)
        await self.parent_view._handle_units_selection(interaction, float(self.values[0]))
        await self.parent_view.go_next(interaction)


class ChannelSelect(Select):
    def __init__(self, parent_view: View, channels: List[TextChannel]):
        self.parent_view = parent_view
        sorted_channels = sorted(channels, key=lambda x: x.name.lower())
        options = [
            SelectOption(label=channel.name, value=str(channel.id), description=f"Channel ID: {channel.id}"[:100])
            for channel in sorted_channels[:24]
        ]
        if len(options) < 25:
            options.append(SelectOption(label="Other Channel", value="other", description="Select a different channel"))
        super().__init__(placeholder="Select channel to post bet...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        channel_id_str = self.values[0]
        if channel_id_str == "other":
            await interaction.response.send_message("Manual channel ID input is not yet implemented. Please select from the list.", ephemeral=True)
            self.disabled = False
            await self.parent_view.edit_message(view=self.parent_view); return

        self.parent_view.bet_details["channel_id"] = int(channel_id_str)
        logger.debug(f"Channel selected: {channel_id_str} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class ConfirmButton(Button):
    def __init__(self, parent_view: View):
        super().__init__(style=ButtonStyle.green, label="Confirm & Post", custom_id=f"straight_confirm_bet_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Confirm button clicked by user {interaction.user.id}")
        for item in self.parent_view.children:
            if isinstance(item, Button): item.disabled = True
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.submit_bet(interaction)


# --- Main Workflow View ---
class StraightBetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot, message_to_control: Optional[discord.InteractionMessage] = None):
        super().__init__(timeout=600)
        self.original_interaction = interaction
        self.bot = bot
        self.current_step = 0
        self.bet_details: Dict[str, Any] = {"bet_type": "straight"}
        self.games: List[Dict] = []
        self.message = message_to_control
        self.is_processing = False
        self.latest_interaction = interaction
        self.bet_slip_generator: Optional[BetSlipGenerator] = None
        self.preview_image_bytes: Optional[io.BytesIO] = None
        self.home_team: Optional[str] = None; self.away_team: Optional[str] = None
        self.league: Optional[str] = None; self.line: Optional[str] = None
        self.odds: Optional[float] = None; self.bet_id: Optional[str] = None

    async def get_bet_slip_generator(self) -> BetSlipGenerator:
        if self.bet_slip_generator is None:
            self.bet_slip_generator = await self.bot.get_bet_slip_generator(self.original_interaction.guild_id)
        return self.bet_slip_generator

    async def _preload_team_logos(self, team1: str, team2: str, league: str): pass

    async def start_flow(self, interaction_that_triggered_workflow_start: Interaction):
        logger.debug(f"Starting straight bet workflow on message ID: {self.message.id if self.message else 'None'}")
        if not self.message:
            logger.error("StraightBetWorkflowView.start_flow called but self.message is None.")
            response_interaction = interaction_that_triggered_workflow_start or self.original_interaction
            try:
                if not response_interaction.response.is_done(): await response_interaction.response.send_message("❌ Workflow error: Message context lost.",ephemeral=True)
                else: await response_interaction.followup.send("❌ Workflow error: Message context lost.",ephemeral=True)
            except discord.HTTPException as http_err: logger.error(f"Failed to send message context lost error: {http_err}")
            self.stop(); return
        try: await self.go_next(interaction_that_triggered_workflow_start)
        except Exception as e:
            logger.exception(f"Failed during initial go_next in StraightBetWorkflow: {e}")
            response_interaction = interaction_that_triggered_workflow_start or self.original_interaction
            try:
                if not response_interaction.response.is_done(): await response_interaction.response.send_message("❌ Failed to start bet workflow.", ephemeral=True)
                else: await response_interaction.followup.send("❌ Failed to start bet workflow.", ephemeral=True)
            except discord.HTTPException as http_err: logger.error(f"Failed to send workflow start error: {http_err}")
            self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this.", ephemeral=True); return False
        self.latest_interaction = interaction; return True

    async def edit_message(self, content: Optional[str]=None, view: Optional[View]=None, embed: Optional[discord.Embed]=None, file: Optional[File]=None):
        logger.debug(f"Attempting to edit message: {self.message.id if self.message else 'None'}")
        attachments = [file] if file else discord.utils.MISSING
        if not self.message: logger.error("Cannot edit message: self.message is None."); return
        try: await self.message.edit(content=content, embed=embed, view=view, attachments=attachments)
        except discord.NotFound: logger.warning(f"Failed to edit message {self.message.id}: Not Found."); self.stop()
        except discord.HTTPException as e: logger.error(f"HTTP error editing message {self.message.id}: {e}", exc_info=True)
        except Exception as e: logger.exception(f"Unexpected error editing message {self.message.id}: {e}")

    async def go_next(self, interaction: Interaction):
        if self.is_processing:
            logger.debug(f"Skipping go_next (step {self.current_step}); already processing.")
            if not interaction.response.is_done():
                try: await interaction.response.defer(ephemeral=True)
                except discord.HTTPException: pass
            return
        self.is_processing = True

        if not interaction.response.is_done():
            try: await interaction.response.defer(ephemeral=True)
            except discord.HTTPException as e: logger.warning(f"Defer in go_next failed: {e}")

        try:
            self.current_step += 1
            logger.debug(f"Processing go_next for StraightBetWorkflow: current_step now {self.current_step} (user {interaction.user.id})")
            self.clear_items()
            content = self.get_content()
            new_view_items = []

            if self.current_step == 1:
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                new_view_items.append(LeagueSelect(self, allowed_leagues))
            elif self.current_step == 2: new_view_items.append(LineTypeSelect(self))
            elif self.current_step == 3:
                league = self.bet_details.get("league")
                if not league: await self.edit_message(content="❌ League not selected.", view=None); self.stop(); return
                self.games = []
                if league != "Other" and hasattr(self.bot, "game_service"):
                    try: self.games = await self.bot.game_service.get_league_games(interaction.guild_id, league, "scheduled", 25)
                    except Exception as e: logger.exception(f"Error fetching games: {e}")
                if self.games: new_view_items.append(GameSelect(self, self.games))
                new_view_items.append(ManualEntryButton(self))
            elif self.current_step == 4:
                line_type = self.bet_details.get("line_type")
                is_manual_modal = self.bet_details.get("game_id") == "Other" or line_type == "player_prop"
                modal = BetDetailsModal(line_type=line_type, is_manual=is_manual_modal)
                modal.view = self
                try:
                    await interaction.response.send_modal(modal)
                    await self.edit_message(content="Please fill in the bet details in the popup form.", view=self)
                except discord.HTTPException as e:
                    logger.error(f"Failed to send BetDetailsModal from go_next: {e}")
                    await self.edit_message(content="❌ Error opening details form.", view=None); self.stop()
                self.is_processing = False; return
            elif self.current_step == 5:
                if "bet_serial" not in self.bet_details: await self.edit_message(content="❌ Bet error.", view=None); self.stop(); return
                new_view_items.append(UnitsSelect(self))
            elif self.current_step == 6:
                if not self.bet_details.get("units_str"): await self.edit_message(content="❌ Units not selected.", view=None); self.stop(); return
                channels = [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.guild.me).send_messages]
                if not channels: await self.edit_message(content="❌ No writable channels.", view=None); self.stop(); return
                new_view_items.append(ChannelSelect(self, channels))
            elif self.current_step == 7:
                if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units_str']):
                    await self.edit_message(content="❌ Details incomplete.", view=None); self.stop(); return
                new_view_items.append(ConfirmButton(self))
            else:
                logger.error(f"Unexpected step: {self.current_step}"); await self.edit_message(content="❌ Workflow error.", view=None); self.stop(); return

            if self.current_step < 8 : new_view_items.append(CancelButton(self))
            for item in new_view_items: self.add_item(item)

            file_to_send = None
            if self.current_step >= 5 and self.preview_image_bytes:
                self.preview_image_bytes.seek(0)
                file_to_send = File(self.preview_image_bytes, filename=f"bet_preview_s{self.current_step}.png")
            await self.edit_message(content=content, view=self, file=file_to_send)
        except Exception as e:
            logger.exception(f"Error in go_next step {self.current_step}: {e}")
            await self.edit_message(content="❌ An error occurred.", view=None); self.stop()
        finally: self.is_processing = False

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        bet_serial = details.get("bet_serial")
        if not bet_serial:
            await self.edit_message(content="❌ Error: Bet ID missing.", view=None)
            self.stop()
            return

        logger.info(f"Submitting bet {bet_serial} by {interaction.user.id}")
        await self.edit_message(content=f"Processing bet `{bet_serial}`...", view=None, file=None)

        try:
            post_channel_id = int(details.get("channel_id"))
            post_channel = self.bot.get_channel(post_channel_id)
            if not post_channel or not isinstance(post_channel, TextChannel):
                raise ValueError(f"Invalid channel ID: {post_channel_id}")

            rowcount, _ = await self.bot.db_manager.execute(
                "UPDATE bets SET confirmed = 1, channel_id = %s, status = %s WHERE bet_serial = %s",
                (post_channel_id, 'confirmed', bet_serial)
            )
            if not rowcount:
                raise BetServiceError("Failed to confirm bet in DB.")

            final_discord_file = None
            if self.preview_image_bytes:
                self.preview_image_bytes.seek(0)
                final_discord_file = discord.File(self.preview_image_bytes, filename=f"bet_slip_{bet_serial}.png")
            else:
                logger.warning(f"Preview missing for bet {bet_serial}. Regenerating.")
                bet_slip_gen = await self.get_bet_slip_generator()
                regen_image = await bet_slip_gen.generate_bet_slip(
                    home_team=details.get('team'), away_team=details.get('opponent'), league=details.get('league'),
                    line=details.get('line'), odds=details.get('odds'), units=float(details.get('units_str', 1.0)),
                    bet_id=str(bet_serial), timestamp=datetime.now(timezone.utc), bet_type=details.get('line_type', 'straight')
                )
                if regen_image:
                    temp_io = io.BytesIO()
                    regen_image.save(temp_io, "PNG")
                    temp_io.seek(0)
                    final_discord_file = discord.File(temp_io, filename=f"bet_slip_{bet_serial}.png")
                else:
                    logger.error(f"Critical failure to regen image for bet {bet_serial}")

            # Fetch capper data
            capper_data = await self.bot.db_manager.fetch_one(
                "SELECT display_name, image_path FROM cappers WHERE guild_id = %s AND user_id = %s",
                (interaction.guild_id, interaction.user.id)
            )

            webhook_username = interaction.user.display_name
            webhook_avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None

            if capper_data:
                webhook_username = capper_data.get('display_name') or webhook_username
                capper_avatar_path = capper_data.get('image_path')
                if capper_avatar_path:
                    # Assuming image_path is a URL. If it's a local path, this needs adjustment.
                    # For local paths, you'd need to read the file, upload to a host, or use data URI.
                    # For simplicity, let's assume it's a direct URL for now.
                    # If it's a relative path like 'static/cappers/avatars/user_id.png',
                    # you'll need to construct the full URL if your bot serves these files,
                    # or read the file data and pass it to the webhook.
                    # For now, we'll just log if it's a local path and not a URL.
                    if capper_avatar_path.startswith(('http://', 'https://')):
                        webhook_avatar_url = capper_avatar_path
                    else:
                        logger.warning(f"Capper avatar path '{capper_avatar_path}' is not a URL. Using Discord avatar.")
                        # If you want to use local files with webhooks, you'd typically read the bytes
                        # and pass them with `avatar=avatar_bytes` to `Webhook.send()`.
                        # However, `avatar_url` takes precedence if both are provided to `Webhook.send()`.
                        # Discord's `Webhook.send` doesn't directly support sending local file bytes as avatar.
                        # A common workaround is to upload the image to Discord (e.g., a hidden channel)
                        # and use its URL, or use a service that hosts the image.
                        # For this implementation, we'll stick to URL or default Discord avatar.


            webhooks = await post_channel.webhooks()
            webhook = discord.utils.find(lambda wh: wh.user == self.bot.user, webhooks)
            if webhook is None:
                webhook = await post_channel.create_webhook(name=f"{self.bot.user.name} Bets")

            content_to_post = f"**New Straight Bet!** (ID: `{bet_serial}`)" # Removed placed by, as webhook shows it

            sent_message = await webhook.send(
                content=content_to_post,
                username=webhook_username,
                avatar_url=webhook_avatar_url,
                file=final_discord_file,
                wait=True
            )

            logger.info(f"Bet {bet_serial} posted to {post_channel.id} (Msg: {sent_message.id}) by webhook.")

            if hasattr(self.bot, 'bet_service') and hasattr(self.bot.bet_service, 'pending_reactions'):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial, 'user_id': interaction.user.id,
                    'guild_id': interaction.guild_id, 'channel_id': post_channel_id,
                    'bet_type': 'straight'
                }
            await self.edit_message(content=f"✅ Bet ID `{bet_serial}` posted to {post_channel.mention}!", view=None)

        except (ValueError, BetServiceError) as err:
            logger.error(f"Error submitting bet {bet_serial}: {err}", exc_info=True)
            await self.edit_message(content=f"❌ Error submitting bet: {err}", view=None)
        except Exception as e:
            logger.exception(f"General error submitting bet {bet_serial}: {e}")
            await self.edit_message(content=f"❌ Unexpected error: {e}", view=None)
        finally:
            if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None
            self.stop()

    async def _handle_units_selection(self, interaction: Interaction, units: float):
        try:
            current_bet_serial = self.bet_details.get('bet_serial')
            if not current_bet_serial:
                logger.error("Cannot handle units: bet_serial missing.")
                await interaction.followup.send("Error: Bet ID missing.", ephemeral=True); self.stop(); return

            await self.bot.db_manager.execute("UPDATE bets SET units = %s WHERE bet_serial = %s",(units, current_bet_serial))
            self.bet_details['units'] = units; self.bet_details['units_str'] = str(units)
            logger.info(f"Units for bet {current_bet_serial} updated to {units}.")

            try:
                bet_query = "SELECT b.bet_serial, b.league, b.bet_type, b.bet_details, b.units, b.odds, b.created_at, g.home_team_name, g.away_team_name FROM bets b LEFT JOIN games g ON b.game_id = g.id WHERE b.bet_serial = %s"
                bet = await self.bot.db_manager.fetch_one(bet_query, (current_bet_serial,))
                if not bet: logger.error(f"Bet {current_bet_serial} not found for preview regen."); return

                bet_details_dict = json.loads(bet['bet_details']) if isinstance(bet.get('bet_details'), str) else bet.get('bet_details', {})
                home_team_name = bet.get('home_team_name') or bet_details_dict.get('team', 'N/A')
                away_team_name = bet.get('away_team_name') or bet_details_dict.get('opponent', 'N/A')
                line_value = bet_details_dict.get('line', 'N/A')

                generator = await self.get_bet_slip_generator()

                # MODIFIED: Removed background_img argument, added await
                bet_slip_image = await generator.generate_bet_slip(
                    home_team=home_team_name, away_team=away_team_name, league=bet['league'],
                    line=line_value, odds=float(bet['odds']), units=float(units),
                    bet_id=str(current_bet_serial), timestamp=bet['created_at'], bet_type=bet['bet_type']
                    # Removed background_img argument
                )

                if bet_slip_image:
                    if self.preview_image_bytes: self.preview_image_bytes.close()
                    self.preview_image_bytes = io.BytesIO()
                    bet_slip_image.save(self.preview_image_bytes, format='PNG')
                    self.preview_image_bytes.seek(0)
                    logger.debug(f"Preview updated for bet {current_bet_serial}, units {units}.")
                else:
                    logger.warning(f"Failed to regen preview for bet {current_bet_serial} (units {units}).")
                    if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None
            except Exception as img_e:
                logger.error(f"Error regen preview in _handle_units_selection: {img_e}", exc_info=True)
                if self.preview_image_bytes: self.preview_image_bytes.close(); self.preview_image_bytes = None
        except Exception as e:
            logger.error(f"Error in _handle_units_selection for bet {self.bet_details.get('bet_serial', 'N/A')}: {e}", exc_info=True)
            try: await interaction.followup.send("Error updating units.", ephemeral=True)
            except discord.HTTPException: pass
            self.stop()

    def get_content(self) -> str:
        step_num = self.current_step
        if step_num == 1: return f"**Step {step_num}**: Select League"
        if step_num == 2: return f"**Step {step_num}**: Select Line Type"
        if step_num == 3: return f"**Step {step_num}**: Select Game or Enter Manually"
        if step_num == 4: return f"**Step {step_num}**: Fill details in the form for your bet."
        if step_num == 5:
            preview_info = "(Preview below)" if self.preview_image_bytes else "(Preview image failed to generate)"
            return f"**Step {step_num}**: Bet details captured {preview_info}. Select Units for your bet."
        if step_num == 6:
            units = self.bet_details.get('units_str', 'N/A')
            preview_info = "(Preview below with updated units)" if self.preview_image_bytes else "(Preview image failed)"
            return f"**Step {step_num}**: Units: `{units}` {preview_info}. Select Channel to post your bet."
        if step_num == 7:
            preview_info = "(Final Preview below)" if self.preview_image_bytes else "(Image generation failed)"
            return f"**Confirm Your Bet** {preview_info}"
        return "Processing your bet request..."
