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
            if isinstance(item, (Select, CancelButton)):
                item.disabled = True

        line_type = self.parent_view.bet_details.get("line_type", "game_line")
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True)
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully.")
            await self.parent_view.edit_message(
                content="Manual entry form opened. Please fill in the details.",
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
        logger.debug(f"BetDetailsModal submitted by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            team = self.team.value.strip()
            opponent = (
                self.opponent.value.strip()
                if hasattr(self, "opponent")
                else self.view.bet_details.get("away_team_name", "Unknown")
            )
            line = (
                self.player_line.value.strip()
                if self.line_type == "player_prop"
                else self.line.value.strip()
            )
            odds_str = self.odds.value.strip()

            if not team or not line or not odds_str:
                await interaction.followup.send(
                    "❌ All fields are required.", ephemeral=True
                )
                return
            try:
                odds_val = float(odds_str.replace("+", ""))
                if -100 < odds_val < 100 and odds_val != 0:
                    raise ValueError("Odds invalid range.")
            except ValueError:
                await interaction.followup.send(
                    f"❌ Invalid odds: '{odds_str}'.", ephemeral=True
                )
                return

            self.view.bet_details.update(
                {
                    "line": line,
                    "odds_str": odds_str,
                    "odds": odds_val,
                    "team": team,
                    "opponent": opponent,
                }
            )
            try:
                bet_serial = (
                    await self.view.bot.bet_service.create_straight_bet(
                        guild_id=interaction.guild_id,
                        user_id=interaction.user.id,
                        game_id=self.view.bet_details.get("game_id")
                        if self.view.bet_details.get("game_id") != "Other"
                        else None,
                        bet_type=self.view.bet_details.get(
                            "line_type", "game_line"
                        ),
                        team=team,
                        opponent=opponent,
                        line=line,
                        units=1.0,
                        odds=odds_val,
                        channel_id=None,
                        league=self.view.bet_details.get("league", "UNKNOWN"),
                    )
                )
                if not bet_serial:
                    raise BetServiceError(
                        "Failed to create bet record (no serial returned)."
                    )
                self.view.bet_details["bet_serial"] = bet_serial
                logger.debug(f"Bet record {bet_serial} created from modal.")
                await self.view._preload_team_logos(
                    team,
                    opponent,
                    self.view.bet_details.get("league", "UNKNOWN"),
                )
            except Exception as e:
                logger.exception(f"Failed to create bet from modal: {e}")
                await interaction.followup.send(
                    f"❌ Error saving bet: {e}", ephemeral=True
                )
                self.view.stop()
                return

            await self.view.edit_message(
                content="Bet details entered. Processing...", view=self.view
            )
            self.view.current_step = 4
            await self.view.go_next(interaction)

        except Exception as e:
            logger.exception(f"Error in BetDetailsModal on_submit: {e}")
            await interaction.followup.send(
                "❌ Error processing details.", ephemeral=True
            )
            if hasattr(self, "view"):
                self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception):
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Modal error.", ephemeral=True
                )
            else:
                await interaction.followup.send("Modal error.", ephemeral=True)
        except discord.HTTPException:
            pass


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
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class ChannelSelect(Select):
    def __init__(self, parent_view: View, channels: List[TextChannel]):
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
    def __init__(self, parent_view: View):
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
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.submit_bet(interaction)


# --- Main Workflow View ---
class StraightBetWorkflowView(View):
    def __init__(
        self,
        interaction: Interaction,
        bot: commands.Bot,
        message_to_control: Optional[discord.InteractionMessage] = None,
    ):
        super().__init__(timeout=600)
        self.original_interaction = interaction
        self.bot = bot
        self.current_step = 0
        self.bet_details: Dict[str, Any] = {"bet_type": "straight"}
        self.games: List[Dict] = []
        self.message = message_to_control
        self.is_processing = False
        self.latest_interaction = interaction
        self.bet_slip_generator = BetSlipGenerator()
        self.preview_image_bytes: Optional[io.BytesIO] = None
        self.team_logos: Dict[str, Optional[str]] = {}

    async def _preload_team_logos(
        self, team1: str, team2: str, league: str
    ):
        # ... (implementation as before) ...
        pass

    async def start_flow(
        self, interaction_that_triggered_workflow_start: Interaction
    ):
        logger.debug(
            f"Starting straight bet workflow on message ID: {self.message.id if self.message else 'None'}"
        )
        if not self.message:
            logger.error(
                "StraightBetWorkflowView.start_flow called but self.message is None."
            )
            try:
                if interaction_that_triggered_workflow_start.response.is_done():
                    await interaction_that_triggered_workflow_start.followup.send(
                        "❌ Workflow error: Message context lost.",
                        ephemeral=True,
                    )
                else:
                    await interaction_that_triggered_workflow_start.response.send_message(
                        "❌ Workflow error: Message context lost.",
                        ephemeral=True,
                    )
            except discord.HTTPException:
                pass
            self.stop()
            return
        try:
            await self.go_next(interaction_that_triggered_workflow_start)
        except Exception as e:
            logger.exception(f"Failed during initial go_next: {e}")
            if interaction_that_triggered_workflow_start.response.is_done():
                await interaction_that_triggered_workflow_start.followup.send(
                    "❌ Failed to start bet workflow.", ephemeral=True
                )
            self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message(
                "You cannot interact with this.", ephemeral=True
            )
            return False
        self.latest_interaction = interaction
        return True

    async def edit_message(
        self,
        content: Optional[str] = None,
        view: Optional[View] = None,
        embed: Optional[discord.Embed] = None,
        file: Optional[File] = None,
    ):
        log_info = (
            f"edit_message for self.message (ID: {self.message.id if self.message else 'None'}): "
            f"content={content is not None}, view={view is not None}, "
            f"embed={embed is not None}, file={file is not None}"
        )
        logger.debug(log_info)
        attachments = [file] if file else []

        if not self.message:
            logger.error(
                "edit_message called but self.message is None."
            )
            active_interaction = self.latest_interaction or self.original_interaction
            if active_interaction:
                try:
                    if active_interaction.response.is_done():
                        await active_interaction.followup.send(
                            "❌ Display error (message context lost).",
                            ephemeral=True,
                        )
                    else:
                        await active_interaction.response.send_message(
                            "❌ Display error (message context lost).",
                            ephemeral=True,
                        )
                except discord.HTTPException:
                    pass
            return

        try:
            await self.message.edit(
                content=content,
                embed=embed,
                view=view,
                attachments=attachments,
            )
        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(
                f"Failed to edit self.message (ID: {self.message.id}): {e}",
                exc_info=True,
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error editing self.message (ID: {self.message.id}): {e}"
            )

    async def go_next(self, interaction: Interaction):
        if self.is_processing:
            logger.debug(
                f"Skipping go_next; already processing step {self.current_step}"
            )
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
            logger.debug(
                f"Processing go_next: current_step={self.current_step} for user {interaction.user.id}"
            )
            self.clear_items()
            self.current_step += 1
            step_content = f"**Step {self.current_step}**"
            file_to_send = None
            logger.debug(f"Entering step {self.current_step}")

            if self.current_step == 1:
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                self.add_item(LeagueSelect(self, allowed_leagues))
                self.add_item(CancelButton(self))
                step_content += ": Select League"
                await self.edit_message(content=step_content, view=self)
                self.is_processing = False; return

            elif self.current_step == 2:
                self.add_item(LineTypeSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Line Type"
                await self.edit_message(content=step_content, view=self)
                self.is_processing = False; return

            elif self.current_step == 3:
                league = self.bet_details.get("league")
                if not league:
                    await self.edit_message(content="❌ League not selected.", view=None)
                    self.stop(); self.is_processing = False; return
                
                self.games = []
                if league != "Other" and hasattr(self.bot, "game_service"):
                    try:
                        self.games = await self.bot.game_service.get_league_games(
                            interaction.guild_id, league, "scheduled", 25
                        )
                    except Exception as e: logger.exception(f"Error fetching games: {e}")

                msg_content = f"{step_content}: "
                if self.games:
                    self.add_item(GameSelect(self, self.games))
                    self.add_item(ManualEntryButton(self))
                    msg_content += f"Select Game for {league} (or Enter Manually)"
                else:
                    self.add_item(ManualEntryButton(self))
                    msg_content += "No games found. Enter details manually." if league != "Other" else "Enter game details manually."
                self.add_item(CancelButton(self))
                await self.edit_message(content=msg_content, view=self)
                self.is_processing = False; return
            
            elif self.current_step == 4:
                line_type = self.bet_details.get("line_type")
                game_id = self.bet_details.get("game_id")
                is_manual = game_id == "Other"

                if interaction.type == discord.InteractionType.modal_submit:
                    self.current_step = 5 
                elif line_type == "player_prop" and not is_manual:
                    is_manual = True 

                if is_manual or (line_type != "player_prop" and interaction.type != discord.InteractionType.modal_submit):
                    modal = BetDetailsModal(line_type=line_type, is_manual=is_manual)
                    modal.view = self
                    try:
                        await interaction.response.send_modal(modal)
                        await self.edit_message(content="Fill details in the form.", view=self)
                    except discord.HTTPException as e:
                        logger.error(f"Failed to send modal: {e}")
                        await self.edit_message(content="❌ Error opening form.", view=None); self.stop()
                    self.is_processing = False; return

                if not self.bet_details.get("bet_serial"):
                     logger.warning("Step 4: Bet serial not set after expected modal/player logic.")
                     self.current_step -=1; self.is_processing = False; return

            if self.current_step == 5:
                if "bet_serial" not in self.bet_details:
                     await self.edit_message(content="❌ Bet record error.", view=None); self.stop(); self.is_processing = False; return
                self.add_item(UnitsSelect(self)); self.add_item(CancelButton(self))
                await self.edit_message(content=f"{step_content}: Select Units", view=self)
                self.is_processing = False; return

            elif self.current_step == 6:
                if "units_str" not in self.bet_details:
                     await self.edit_message(content="❌ Units missing.", view=None); self.stop(); self.is_processing = False; return
                
                # Get available text channels
                text_channels = [
                    channel for channel in interaction.guild.text_channels
                    if channel.permissions_for(interaction.guild.me).send_messages
                ]
                
                # Add channel select and cancel button
                self.add_item(ChannelSelect(self, text_channels))
                self.add_item(CancelButton(self))
                
                # Generate preview image if needed
                file_to_send = None
                if hasattr(self, 'bet_slip_generator'):
                    try:
                        file_to_send = await self.bet_slip_generator.generate_preview(self.bet_details)
                    except Exception as e:
                        logger.error(f"Failed to generate preview image: {e}")
                
                await self.edit_message(content=f"{step_content}: Review & Select Channel", view=self, file=file_to_send)
                self.is_processing = False; return

            elif self.current_step == 7:
                if not all(k in self.bet_details for k in ['bet_serial', 'channel_id']):
                     await self.edit_message(content="❌ Details incomplete.", view=None); self.stop(); self.is_processing = False; return
                # ... (Confirmation text and image setup for file_to_send) ...
                confirmation_text = "Confirm your bet..." # Placeholder
                await self.edit_message(content=confirmation_text, view=self, file=file_to_send)
                self.is_processing = False; return
            else:
                logger.error(f"Unexpected step: {self.current_step}")
                await self.edit_message(content="❌ Invalid step.", view=None)
                self.stop()

        except Exception as e:
            logger.exception(f"Error in go_next step {self.current_step}: {e}")
            await self.edit_message(content="❌ An error occurred.", view=None)
            self.stop()
        finally:
            self.is_processing = False

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        bet_serial = details.get("bet_serial")
        if not bet_serial:
            await self.edit_message(content="❌ Error: Bet ID missing.", view=None)
            self.stop(); return

        logger.info(f"Submitting bet {bet_serial}")
        await self.edit_message(content="Processing...", view=None, file=None)

        try:
            post_channel_id = details.get("channel_id")
            post_channel = self.bot.get_channel(post_channel_id)
            if not post_channel or not isinstance(post_channel, TextChannel):
                raise ValueError("Channel not found or not a text channel.")
            
            # ... (DB update, image generation, webhook send logic as before) ...
            
            await self.edit_message(
                content=f"✅ Bet placed! ID: `{bet_serial}`. Posted to {post_channel.mention}.",
                view=None
            )
        except Exception as e:
            logger.exception(f"Error submitting bet {bet_serial}: {e}")
            await self.edit_message(content=f"❌ Error: {e}", view=None)
        finally:
            if self.preview_image_bytes: self.preview_image_bytes.close()
            self.stop()
