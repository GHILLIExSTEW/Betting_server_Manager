"""Straight betting workflow for placing single-leg bets."""

import discord
from discord import (
    ButtonStyle,
    Interaction,
    SelectOption,
    TextChannel,
    File,
    Embed,
    Webhook,
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
import aiohttp

# Import directly from utils
from utils.errors import (
    BetServiceError,
    ValidationError,
    GameNotFoundError,
)
from utils.image_generator import BetSlipGenerator
from utils.modals import StraightBetDetailsModal # Import the modal
from config.leagues import LEAGUE_CONFIG

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
        if len(options) < 25:  # Max 25 options for a select menu
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
                    await self.parent_view.bot.bet_service.delete_bet(bet_serial)
                await interaction.response.edit_message(content=f"Bet `{bet_serial}` cancelled.", view=None)
            except Exception as e:
                logger.error(f"Failed to delete bet {bet_serial}: {e}")
                await interaction.response.edit_message(content=f"Bet cancellation failed for `{bet_serial}`.", view=None)
        else:
            await interaction.response.edit_message(content="Bet workflow cancelled.", view=None)
        self.parent_view.stop()


class BetDetailsModal(Modal):
    def __init__(self, line_type: str, is_manual: bool = False):
        super().__init__(title="Enter Bet Details")
        self.line_type = line_type
        self.is_manual = is_manual

        self.team = TextInput(label="Team Bet On/Player's Team", required=True, max_length=100, placeholder="Enter team name")
        self.add_item(self.team)

        if self.is_manual:
            self.opponent = TextInput(label="Opponent", required=True, max_length=100, placeholder="Enter opponent name")
            self.add_item(self.opponent)

        if line_type == "player_prop":
            self.player_line = TextInput(label="Player - Line (e.g., Name O/U Points)", required=True, max_length=100, placeholder="E.g., Connor McDavid - Shots Over 3.5")
            self.add_item(self.player_line)
        else:
            self.line = TextInput(label="Line (e.g., Moneyline, Spread -7.5)", required=True, max_length=100, placeholder="E.g., Moneyline, Spread -7.5, Total Over 6.5")
            self.add_item(self.line)

        self.odds = TextInput(label="Odds", required=True, max_length=10, placeholder="Enter American odds (e.g., -110, +200)")
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"BetDetailsModal submitted by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            team_input = self.team.value.strip()
            if self.is_manual:
                opponent_input = self.opponent.value.strip() if hasattr(self, "opponent") else "N/A"
            else:
                opponent_input = self.view.bet_details.get("away_team_name", "N/A")
                if team_input.lower() == self.view.bet_details.get("away_team_name", "").lower():
                    opponent_input = self.view.bet_details.get("home_team_name", "N/A")

            line_value = (self.player_line.value.strip() if self.line_type == "player_prop" else self.line.value.strip())
            odds_str = self.odds.value.strip()

            if not team_input or not line_value or not odds_str:
                await interaction.followup.send("❌ All fields are required in the modal.", ephemeral=True)
                return
            try:
                odds_val = float(odds_str.replace("+", ""))
            except ValueError as ve:
                await interaction.followup.send(f"❌ Invalid odds: '{odds_str}'. {ve}", ephemeral=True)
                return

            self.view.bet_details.update({
                "line": line_value,
                "odds_str": odds_str,
                "odds": odds_val,
                "team": team_input,
                "opponent": opponent_input
            })

            try:
                game_id_for_db = self.view.bet_details.get("game_id")
                if game_id_for_db == "Other":
                    game_id_for_db = None

                self.view.home_team = team_input
                self.view.away_team = opponent_input
                self.view.league = self.view.bet_details.get("league", "UNKNOWN")
                self.view.line = line_value
                self.view.odds = odds_val

                if "bet_serial" not in self.view.bet_details:
                    bet_serial = await self.view.bot.bet_service.create_straight_bet(
                        guild_id=interaction.guild_id,
                        user_id=interaction.user.id,
                        game_id=game_id_for_db,
                        bet_type=self.view.bet_details.get("line_type", "game_line"),
                        team=team_input,
                        opponent=opponent_input,
                        line=line_value,
                        units=1.0,
                        odds=odds_val,
                        channel_id=None,
                        league=self.view.bet_details.get("league", "UNKNOWN")
                    )
                    if not bet_serial:
                        raise BetServiceError("Failed to create bet record (no serial returned).")
                    self.view.bet_details["bet_serial"] = bet_serial
                    self.view.bet_id = str(bet_serial)
                    logger.debug(f"Bet record {bet_serial} created from modal for user {interaction.user.id}.")
                else:
                    logger.warning(f"Bet_serial {self.view.bet_details['bet_serial']} already exists when submitting modal. Check flow.")
                    self.view.bet_id = str(self.view.bet_details['bet_serial'])

                current_units = float(self.view.bet_details.get("units", 1.0))
                try:
                    bet_slip_generator = await self.view.get_bet_slip_generator()
                    bet_slip_image = await bet_slip_generator.generate_bet_slip(
                        home_team=self.view.home_team,
                        away_team=self.view.away_team,
                        league=self.view.league,
                        line=self.view.line,
                        odds=self.view.odds,
                        units=current_units,
                        bet_id=self.view.bet_id,
                        timestamp=datetime.now(timezone.utc),
                        bet_type=self.view.bet_details.get("line_type", "straight")
                    )
                    if bet_slip_image:
                        self.view.preview_image_bytes = io.BytesIO()
                        bet_slip_image.save(self.view.preview_image_bytes, format='PNG')
                        self.view.preview_image_bytes.seek(0)
                        logger.debug(f"Bet slip image (re)generated from modal for bet {self.view.bet_id}")
                    else:
                        logger.warning(f"Failed to generate bet slip image from modal for bet {self.view.bet_id}.")
                        self.view.preview_image_bytes = None
                except Exception as img_e:
                    logger.exception(f"Error generating bet slip image in modal: {img_e}")
                    self.view.preview_image_bytes = None

            except BetServiceError as bse:
                logger.exception(f"BetService error creating/updating bet from modal: {bse}")
                await interaction.followup.send(f"❌ Error saving bet record: {bse}", ephemeral=True)
                self.view.stop()
                return
            except Exception as e:
                logger.exception(f"Failed to save bet details from modal: {e}")
                await interaction.followup.send(f"❌ Error processing bet data: {e}", ephemeral=True)
                self.view.stop()
                return

            await self.view.edit_message(content="Bet details updated. Processing...", view=self.view)
            self.view.current_step = 4
            await self.view.go_next(interaction)

        except Exception as e:
            logger.exception(f"Error in BetDetailsModal on_submit (outer try): {e}")
            try:
                await interaction.followup.send("❌ Error processing details from modal.", ephemeral=True)
            except discord.HTTPException:
                logger.error("Failed to send followup error in BetDetailsModal.")
            if hasattr(self, "view") and self.view:
                self.view.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("Modal error.", ephemeral=True)
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
        await interaction.response.defer(ephemeral=True)
        await self.parent_view._handle_units_selection(interaction, float(self.values[0]))
        await self.parent_view.go_next(interaction)


class ChannelSelect(Select):
    def __init__(self, parent_view: View, channels: List[TextChannel]):
        self.parent_view = parent_view
        sorted_channels = sorted(channels, key=lambda x: x.name.lower())
        options = [
            SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"ID: {channel.id}"[:100]
            )
            for channel in sorted_channels[:24]
        ]
        if not options:
            options.append(SelectOption(label="No channels available", value="none_available", emoji="❌"))

        super().__init__(
            placeholder="Select channel to post bet...",
            options=options,
            min_values=1,
            max_values=1,
            disabled=(not options or options[0].value == "none_available")
        )

    async def callback(self, interaction: Interaction):
        channel_id_str = self.values[0]
        if channel_id_str == "none_available":
            await interaction.response.send_message("No channels available to select.", ephemeral=True)
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
        self.home_team: Optional[str] = None
        self.away_team: Optional[str] = None
        self.league: Optional[str] = None
        self.line: Optional[str] = None
        self.odds: Optional[float] = None
        self.bet_id: Optional[str] = None

    async def get_bet_slip_generator(self) -> BetSlipGenerator:
        if self.bet_slip_generator is None:
            self.bet_slip_generator = await self.bot.get_bet_slip_generator(self.original_interaction.guild_id)
        return self.bet_slip_generator

    async def start_flow(self, interaction_that_triggered_workflow_start: Interaction):
        logger.debug(f"Starting straight bet workflow on message ID: {self.message.id if self.message else 'None'}")
        if not self.message:
            logger.error("StraightBetWorkflowView.start_flow called but self.message is None.")
            response_interaction = interaction_that_triggered_workflow_start or self.original_interaction
            try:
                if not response_interaction.response.is_done():
                    await response_interaction.response.send_message("❌ Workflow error: Message context lost.", ephemeral=True)
                else:
                    await response_interaction.followup.send("❌ Workflow error: Message context lost.", ephemeral=True)
            except discord.HTTPException as http_err:
                logger.error(f"Failed to send message context lost error: {http_err}")
            self.stop()
            return
        try:
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
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message(
                "You cannot interact with this bet placement.", ephemeral=True
            )
            return False
        self.latest_interaction = interaction
        return True

    async def edit_message(self, content: Optional[str]=None, view: Optional[View]=None, embed: Optional[discord.Embed]=None, file: Optional[File]=None):
        logger.debug(f"Attempting to edit message: {self.message.id if self.message else 'None'} with content: '{content}'")
        attachments = [file] if file else discord.utils.MISSING
        if not self.message:
            logger.error("Cannot edit message: self.message is None.")
            if self.latest_interaction and self.latest_interaction.response.is_done():
                try:
                    logger.debug("Self.message is None, trying to send followup via latest_interaction.")
                    await self.latest_interaction.followup.send(content=content or "Updating...", view=view, files=attachments if attachments != discord.utils.MISSING else None, ephemeral=True)
                    self.message = await self.latest_interaction.original_response()
                except Exception as e:
                    logger.error(f"Failed to send followup when self.message was None: {e}")
            return
        try:
            await self.message.edit(content=content, embed=embed, view=view, attachments=attachments)
        except discord.NotFound:
            logger.warning(f"Failed to edit message {self.message.id}: Not Found. Stopping view.")
            self.stop()
        except discord.HTTPException as e:
            logger.error(f"HTTP error editing message {self.message.id}: {e}", exc_info=True)
        except Exception as e:
            logger.exception(f"Unexpected error editing message {self.message.id}: {e}")

    async def go_next(self, interaction: Interaction):
        if self.is_processing:
            logger.debug(f"Skipping go_next (step {self.current_step}); already processing.")
            if not interaction.response.is_done():
                try:
                    await interaction.response.defer(ephemeral=True)
                except discord.HTTPException:
                    pass
            return
        self.is_processing = True

        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.HTTPException as e:
                logger.warning(f"Defer in go_next failed for interaction {interaction.id} (step {self.current_step}): {e}")
                self.is_processing = False
                return

        try:
            self.current_step += 1
            logger.info(f"StraightBetWorkflow: Advancing to step {self.current_step} for user {interaction.user.id}")
            self.clear_items()
            content = self.get_content()
            new_view_items = []

            if self.current_step == 1:
                allowed_leagues = [
                    "NFL",  # American Football
                    "EPL",  # Soccer
                    "NBA",  # Basketball
                    "MLB",  # Baseball
                    "NHL",  # Hockey
                    "La Liga",  # Soccer
                    "NCAA",  # American Football, Basketball
                    "Bundesliga",  # Soccer
                    "Serie A",  # Soccer
                    "Ligue 1",  # Soccer
                    "MLS",  # Soccer
                    "Formula 1",  # Motorsports
                    "Tennis",  # Tennis
                    "UFC/MMA",  # Mixed Martial Arts
                    "WNBA",  # Basketball
                    "CFL",  # American Football
                    "AFL",  # Australian Football
                    "Darts",  # Darts
                    "EuroLeague",  # Basketball
                    "NPB",  # Baseball
                    "KBO",  # Baseball
                    "KHL"  # Hockey
                ]
                new_view_items.append(LeagueSelect(self, allowed_leagues))
            elif self.current_step == 2:
                new_view_items.append(LineTypeSelect(self))
            elif self.current_step == 3:
                league = self.bet_details.get("league")
                if not league:
                    await self.edit_message(content="❌ League not selected. Please restart.", view=None)
                    self.stop()
                    return
                self.games = []
                if league != "Other" and hasattr(self.bot, "game_service"):
                    try:
                        self.games = await self.bot.game_service.get_league_games(interaction.guild_id, league, "scheduled", 25)
                    except Exception as e:
                        logger.exception(f"Error fetching games for {league}: {e}")
                if self.games:
                    new_view_items.append(GameSelect(self, self.games))
                new_view_items.append(ManualEntryButton(self))
            elif self.current_step == 4:
                line_type = self.bet_details.get("line_type")
                is_manual_game = self.bet_details.get("game_id") == "Other"
                is_modal_needed = is_manual_game or line_type == "player_prop"

                if is_modal_needed:
                    modal = BetDetailsModal(line_type=line_type, is_manual=is_manual_game)
                    modal.view = self
                    try:
                        await interaction.response.send_modal(modal)
                        await self.edit_message(content="Please fill in the bet details in the popup form.", view=self)
                    except discord.HTTPException as e:
                        logger.error(f"Failed to send BetDetailsModal (step {self.current_step}): {e}. Interaction ID: {interaction.id}")
                        await self.edit_message(content="❌ Error opening details form. Interaction may have expired. Please restart.", view=None)
                        self.stop()
                    self.is_processing = False
                    return
                else:
                    logger.warning("Step 4 reached with game selected and not player prop - flow might need review.")
                    self.current_step = 4
                    await self.go_next(interaction)
                    self.is_processing = False
                    return
            elif self.current_step == 5:
                if "bet_serial" not in self.bet_details:
                    await self.edit_message(content="❌ Bet details not fully captured or bet not created. Please restart.", view=None)
                    self.stop()
                    return
                new_view_items.append(UnitsSelect(self))
            elif self.current_step == 6:
                if not self.bet_details.get("units_str"):
                    await self.edit_message(content="❌ Units not selected. Please restart.", view=None)
                    self.stop()
                    return

                logger.debug(f"Fetching guild settings for guild_id: {interaction.guild_id} for channel selection.")
                guild_settings = await self.bot.db_manager.fetch_one(
                    "SELECT embed_channel_1, embed_channel_2 FROM guild_settings WHERE guild_id = %s",
                    (interaction.guild_id,)
                )

                configured_channel_objects = []
                if guild_settings:
                    ch_ids_to_fetch = []
                    if guild_settings.get('embed_channel_1'):
                        ch_ids_to_fetch.append(int(guild_settings['embed_channel_1']))
                    if guild_settings.get('embed_channel_2'):
                        ch_ids_to_fetch.append(int(guild_settings['embed_channel_2']))

                    for ch_id in list(set(ch_ids_to_fetch)):
                        try:
                            channel = interaction.guild.get_channel(ch_id)
                            if not channel:
                                channel = await interaction.guild.fetch_channel(ch_id)
                            if channel and isinstance(channel, TextChannel) and channel.permissions_for(interaction.guild.me).send_messages:
                                configured_channel_objects.append(channel)
                            elif channel:
                                logger.warning(f"Configured embed_channel ({ch_id}) is not a TextChannel or bot lacks send permissions.")
                            else:
                                logger.warning(f"Configured embed_channel ({ch_id}) not found in guild even after fetch attempt.")
                        except ValueError:
                            logger.error(f"Invalid embed_channel ID in database: {ch_id}")
                        except discord.NotFound:
                            logger.warning(f"Configured embed_channel ({ch_id}) not found via fetch.")
                        except discord.Forbidden:
                            logger.warning(f"Forbidden to fetch configured embed_channel ({ch_id}).")
                        except Exception as e:
                            logger.error(f"Error processing channel ID {ch_id}: {e}")
                else:
                    logger.warning(f"No guild settings found for guild {interaction.guild_id} when selecting embed channels.")

                if not configured_channel_objects:
                    content = "❌ No configured embed channels found for this server, or the bot lacks permissions to send messages in them. Please ask an admin to set them up using `/setup`."
                    await self.edit_message(content=content, view=None)
                    self.stop()
                    return

                new_view_items.append(ChannelSelect(self, configured_channel_objects))
            elif self.current_step == 7:
                if not all(k in self.bet_details for k in ['bet_serial', 'channel_id', 'units_str']):
                    await self.edit_message(content="❌ Bet details incomplete. Please restart.", view=None)
                    self.stop()
                    return
                new_view_items.append(ConfirmButton(self))
            else:
                logger.error(f"Unexpected step in StraightBetWorkflow: {self.current_step}")
                await self.edit_message(content="❌ An unexpected error occurred in the workflow.", view=None)
                self.stop()
                return

            if self.current_step < 8:
                new_view_items.append(CancelButton(self))

            for item in new_view_items:
                self.add_item(item)

            file_to_send = None
            if self.current_step >= 5 and self.preview_image_bytes:
                self.preview_image_bytes.seek(0)
                file_to_send = File(self.preview_image_bytes, filename=f"bet_preview_s{self.current_step}.png")

            await self.edit_message(content=content, view=self, file=file_to_send)

        except Exception as e:
            logger.exception(f"Error in go_next (step {self.current_step}): {e}")
            await self.edit_message(content="❌ An error occurred. Please try again or cancel.", view=None)
            self.stop()
        finally:
            self.is_processing = False

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        bet_serial = details.get("bet_serial")

        if not bet_serial:
            await self.edit_message(content="❌ Error: Bet ID missing. Cannot submit.", view=None)
            self.stop()
            return

        logger.info(f"Submitting bet {bet_serial} by user {interaction.user.id}")
        await self.edit_message(content=f"Processing bet `{bet_serial}`...", view=None, file=None)

        try:
            post_channel_id = int(details.get("channel_id"))
            post_channel = self.bot.get_channel(post_channel_id)
            if not post_channel:
                try:
                    post_channel = await self.bot.fetch_channel(post_channel_id)
                except discord.NotFound:
                    raise ValueError(f"Channel ID {post_channel_id} not found.")
                except discord.Forbidden:
                    raise ValueError(f"No permission to fetch channel {post_channel_id}.")
            if not isinstance(post_channel, TextChannel):
                raise ValueError(f"Channel ID {post_channel_id} is not a text channel.")

            rowcount, _ = await self.bot.db_manager.execute(
                "UPDATE bets SET confirmed = 1, channel_id = %s, status = %s WHERE bet_serial = %s",
                (post_channel_id, 'pending', bet_serial)
            )
            if not rowcount:
                logger.warning(f"Failed to confirm bet {bet_serial} in DB or already confirmed/deleted.")
                current_bet_status = await self.bot.db_manager.fetch_one(
                    "SELECT confirmed, channel_id FROM bets WHERE bet_serial = %s",
                    (bet_serial,)
                )
                if not (current_bet_status and current_bet_status['confirmed'] == 1 and current_bet_status['channel_id'] == post_channel_id):
                    raise BetServiceError("Failed to confirm bet in DB and not already in desired state.")

            final_discord_file = None
            if self.preview_image_bytes:
                self.preview_image_bytes.seek(0)
                final_discord_file = discord.File(self.preview_image_bytes, filename=f"bet_slip_{bet_serial}.png")
            else:
                logger.warning(f"Preview image bytes not available for bet {bet_serial} at submission. Attempting regeneration.")
                bet_slip_gen = await self.get_bet_slip_generator()
                home_team_for_regen = self.home_team if self.home_team else details.get('team', "N/A")
                away_team_for_regen = self.away_team if self.away_team else details.get('opponent', "N/A")
                league_for_regen = self.league if self.league else details.get('league', "N/A")
                line_for_regen = self.line if self.line else details.get('line', "N/A")
                odds_for_regen = self.odds if self.odds is not None else details.get('odds')
                units_for_regen = float(details.get('units_str', 1.0))
                bet_type_for_regen = details.get('line_type', 'straight')

                if not all([home_team_for_regen, league_for_regen, line_for_regen, odds_for_regen is not None]):
                    logger.error(f"Cannot regenerate image for bet {bet_serial}: Missing crucial details.")
                else:
                    regen_image = await bet_slip_gen.generate_bet_slip(
                        home_team=home_team_for_regen,
                        away_team=away_team_for_regen,
                        league=league_for_regen,
                        line=line_for_regen,
                        odds=odds_for_regen,
                        units=units_for_regen,
                        bet_id=str(bet_serial),
                        timestamp=datetime.now(timezone.utc),
                        bet_type=bet_type_for_regen
                    )
                    if regen_image:
                        temp_io = io.BytesIO()
                        regen_image.save(temp_io, "PNG")
                        temp_io.seek(0)
                        final_discord_file = discord.File(temp_io, filename=f"bet_slip_{bet_serial}.png")
                    else:
                        logger.error(f"Critical failure to regenerate image for bet {bet_serial}. Posting without image.")

            capper_data = await self.bot.db_manager.fetch_one(
                "SELECT display_name, image_path FROM cappers WHERE guild_id = %s AND user_id = %s",
                (interaction.guild_id, interaction.user.id)
            )

            webhook_username = interaction.user.display_name
            webhook_avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None

            if capper_data:
                if capper_data.get('display_name'):
                    webhook_username = capper_data['display_name']
                if capper_data.get('image_path'):
                    custom_avatar_url = capper_data['image_path']
                    if custom_avatar_url.startswith(('http://', 'https://')):
                        webhook_avatar_url = custom_avatar_url
                    else:
                        logger.warning(f"Capper avatar path '{custom_avatar_url}' for user {interaction.user.id} is not a direct URL. Using Discord avatar.")

            # Fetch member_role from guild_settings
            guild_settings = await self.bot.db_manager.fetch_one(
                "SELECT member_role FROM guild_settings WHERE guild_id = %s",
                (interaction.guild_id,)
            )
            
            member_role_mention = ""
            if guild_settings and guild_settings.get('member_role'):
                member_role_mention = f"<@&{guild_settings['member_role']}> "

            webhooks = await post_channel.webhooks()
            webhook = discord.utils.find(lambda wh: wh.user and wh.user.id == self.bot.user.id, webhooks)
            if webhook is None:
                webhook = await post_channel.create_webhook(name=f"{self.bot.user.name} Bets")

            sent_message = await webhook.send(
                content=member_role_mention,
                username=webhook_username,
                avatar_url=webhook_avatar_url,
                file=final_discord_file,
                wait=True
            )
            logger.info(f"Bet {bet_serial} posted to channel {post_channel.id} (Message ID: {sent_message.id}) via webhook by {webhook_username}.")

            if hasattr(self.bot, 'bet_service') and hasattr(self.bot.bet_service, 'pending_reactions'):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial,
                    'user_id': interaction.user.id,
                    'guild_id': interaction.guild_id,
                    'channel_id': post_channel_id,
                    'bet_type': details.get('line_type', 'straight')
                }

            await self.edit_message(content=f"✅ Bet ID `{bet_serial}` posted to {post_channel.mention}!", view=None)

        except (ValueError, BetServiceError) as err:
            logger.error(f"Error submitting bet {bet_serial}: {err}", exc_info=True)
            await self.edit_message(content=f"❌ Error submitting bet: {err}", view=None)
        except Exception as e:
            logger.exception(f"General error submitting bet {bet_serial}: {e}")
            await self.edit_message(content=f"❌ An unexpected error occurred: {e}", view=None)
        finally:
            if self.preview_image_bytes:
                self.preview_image_bytes.close()
                self.preview_image_bytes = None
            self.stop()

    async def _handle_units_selection(self, interaction: Interaction, units: float):
        try:
            current_bet_serial = self.bet_details.get('bet_serial')
            if not current_bet_serial:
                logger.error("Cannot handle units selection: bet_serial is missing from bet_details.")
                await interaction.followup.send("Error: Bet ID missing. Cannot update units.", ephemeral=True)
                self.stop()
                return

            # First verify the bet exists and get current units
            current_units = await self.bot.db_manager.fetchval(
                "SELECT units FROM bets WHERE bet_serial = %s",
                (current_bet_serial,)
            )
            
            if current_units is None:
                logger.error(f"Bet {current_bet_serial} not found in database.")
                await interaction.followup.send("Error: Bet not found in database.", ephemeral=True)
                self.stop()
                return

            # Only update if units have changed
            if current_units != units:
                rowcount, _ = await self.bot.db_manager.execute(
                    "UPDATE bets SET units = %s WHERE bet_serial = %s",
                    (units, current_bet_serial)
                )
                
                if rowcount == 0:
                    logger.error(f"Failed to update units for bet {current_bet_serial} in DB.")
                    await interaction.followup.send("Error: Could not update units for the bet.", ephemeral=True)
                    self.stop()
                    return
            else:
                logger.debug(f"Units unchanged for bet {current_bet_serial} ({units}). Skipping update.")

            self.bet_details['units'] = units
            self.bet_details['units_str'] = str(units)
            logger.info(f"Units for bet {current_bet_serial} updated to {units} in DB.")

            try:
                home_team_for_regen = self.home_team if self.home_team else self.bet_details.get('team', 'N/A')
                away_team_for_regen = self.away_team if self.away_team else self.bet_details.get('opponent', 'N/A')
                league_for_regen = self.league if self.league else self.bet_details.get('league', 'N/A')
                line_for_regen = self.line if self.line else self.bet_details.get('line', 'N/A')
                odds_for_regen = self.odds if self.odds is not None else self.bet_details.get('odds')
                bet_id_for_regen = self.bet_id if self.bet_id else str(current_bet_serial)
                bet_type_for_regen = self.bet_details.get('line_type', 'straight')

                if not all([home_team_for_regen != 'N/A', league_for_regen != 'N/A', line_for_regen != 'N/A', odds_for_regen is not None]):
                    logger.error(f"Cannot regenerate image for bet {current_bet_serial} after units update: Missing crucial details.")
                    if self.preview_image_bytes:
                        self.preview_image_bytes.close()
                        self.preview_image_bytes = None
                    return

                generator = await self.get_bet_slip_generator()
                bet_slip_image = await generator.generate_bet_slip(
                    home_team=home_team_for_regen,
                    away_team=away_team_for_regen,
                    league=league_for_regen,
                    line=line_for_regen,
                    odds=float(odds_for_regen),
                    units=float(units),
                    bet_id=bet_id_for_regen,
                    timestamp=datetime.now(timezone.utc),
                    bet_type=bet_type_for_regen
                )

                if bet_slip_image:
                    if self.preview_image_bytes:
                        self.preview_image_bytes.close()
                    self.preview_image_bytes = io.BytesIO()
                    bet_slip_image.save(self.preview_image_bytes, format='PNG')
                    self.preview_image_bytes.seek(0)
                    logger.debug(f"Bet slip preview image updated for bet {current_bet_serial} with units {units}.")
                else:
                    logger.warning(f"Failed to regenerate bet slip preview for bet {current_bet_serial} (units {units}).")
                    if self.preview_image_bytes:
                        self.preview_image_bytes.close()
                        self.preview_image_bytes = None
            except Exception as img_e:
                logger.error(f"Error regenerating bet slip preview in _handle_units_selection for bet {current_bet_serial}: {img_e}", exc_info=True)
                if self.preview_image_bytes:
                    self.preview_image_bytes.close()
                    self.preview_image_bytes = None

        except Exception as e:
            logger.error(f"Error in _handle_units_selection for bet {self.bet_details.get('bet_serial', 'N/A')}: {e}", exc_info=True)
            try:
                await interaction.followup.send("Error updating units. Please try again.", ephemeral=True)
            except discord.HTTPException:
                pass
            self.stop()

    def get_content(self) -> str:
        step_num = self.current_step
        if step_num == 1:
            return f"**Step {step_num}**: Select League"
        if step_num == 2:
            return f"**Step {step_num}**: Select Line Type"
        if step_num == 3:
            return f"**Step {step_num}**: Select Game or Enter Manually"
        if step_num == 4:
            return "Please fill in the bet details in the popup form."
        if step_num == 5:
            preview_info = "(Preview below)" if self.preview_image_bytes else "(Generating preview...)"
            return f"**Step {step_num}**: Bet details captured {preview_info}. Select Units for your bet."
        if step_num == 6:
            units = self.bet_details.get('units_str', 'N/A')
            preview_info = "(Preview below with updated units)" if self.preview_image_bytes else "(Preview image failed)"
            return f"**Step {step_num}**: Units: `{units}` {preview_info}. Select Channel to post your bet."
        if step_num == 7:
            preview_info = "(Final Preview below)" if self.preview_image_bytes else "(Image generation failed)"
            return f"**Confirm Your Bet** {preview_info}"
        return "Processing your bet request..."

    async def on_timeout(self):
        if self.message:
            await self.edit_message(content="❌ Bet workflow timed out.", view=None)
        self.stop()
