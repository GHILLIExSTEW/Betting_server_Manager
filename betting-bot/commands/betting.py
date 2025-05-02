# betting-bot/commands/betting.py

"""Betting command for placing bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel, File
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union
from datetime import datetime, timezone
import io

try:
    from ..utils.errors import BetServiceError, ValidationError, GameNotFoundError
    from ..utils.image_generator import BetSlipGenerator
except ImportError:
    from utils.errors import BetServiceError, ValidationError, GameNotFoundError
    from utils.image_generator import BetSlipGenerator

logger = logging.getLogger(__name__)

# --- UI Component Classes ---
class BetTypeSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(
                label="Straight",
                value="straight",
                description="Moneyline, over/under, or player prop"
            ),
            SelectOption(
                label="Parlay",
                value="parlay",
                description="Combine multiple bets"
            )
        ]
        super().__init__(
            placeholder="Select Bet Type...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['bet_type'] = self.values[0]
        logger.debug(f"Bet Type selected: {self.values[0]}")
        await interaction.response.defer()
        self.disabled = True
        await self.parent_view.go_next(interaction)


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
        logger.debug(f"League selected: {self.values[0]}")
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
                description="Moneyline or game over/under"
            ),
            SelectOption(
                label="Player Prop",
                value="player_prop",
                description="Bet on player performance"
            )
        ]
        super().__init__(
            placeholder="Select Line Type...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['line_type'] = self.values[0]
        logger.debug(f"Line Type selected: {self.values[0]}")
        self.disabled = True
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
                time_str = start_dt.strftime('%m/%d %H:%M %Z')
            else:
                time_str = 'Time N/A'
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id')
            if game_api_id is None:
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
        self.parent_view.bet_details['game_id'] = self.values[0]
        if self.values[0] != "Other":
            game = next(
                (g for g in self.parent_view.games if str(g.get('id')) == self.values[0]),
                None
            )
            if game:
                self.parent_view.bet_details['home_team_name'] = game.get('home_team_name', 'Unknown')
                self.parent_view.bet_details['away_team_name'] = game.get('away_team_name', 'Unknown')
        logger.debug(f"Game selected: {self.values[0]}")
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
            self.parent_view.bet_details['player'] = None
        logger.debug(f"Home player selected: {self.values[0] if self.values else 'None'}")
        await interaction.response.defer()
        if self.parent_view.bet_details.get('player'):
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
            self.parent_view.bet_details['player'] = None
        logger.debug(f"Away player selected: {self.values[0] if self.values else 'None'}")
        await interaction.response.defer()
        if self.parent_view.bet_details.get('player'):
            await self.parent_view.go_next(interaction)


class ManualEntryButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Manual Entry",
            custom_id=f"manual_entry_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug("Manual Entry button clicked (from no games found)")
        self.parent_view.bet_details['game_id'] = "Other"
        self.disabled = True
        for item in self.parent_view.children:
            if isinstance(item, CancelButton):
                item.disabled = True
        line_type = self.parent_view.bet_details.get('line_type')
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True, is_first_leg=len(self.parent_view.bet_details.get('legs', [])) == 0)
            modal.view = self.parent_view
            await interaction.response.send_modal(modal)
            logger.debug("Manual entry modal sent successfully")
            await self.parent_view.edit_message(
                interaction,
                content="Manual entry form opened.",
                view=self.parent_view
            )
            self.parent_view.current_step = 4
        except discord.HTTPException as e:
            logger.error(f"Failed to send manual entry modal: {e}")
            await interaction.followup.send(
                "❌ Failed to open manual entry form. Please restart the /bet command.",
                ephemeral=True
            )
            self.parent_view.stop()


class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.red,
            label="Cancel",
            custom_id=f"cancel_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug("Cancel button clicked")
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True
        # Check if a bet was created and delete it
        bet_serial = self.parent_view.bet_details.get('bet_serial')
        if bet_serial:
            try:
                await self.parent_view.bot.bet_service.delete_bet(bet_serial)
                await interaction.response.edit_message(
                    content=f"Bet `{bet_serial}` canceled and records deleted.",
                    view=None
                )
            except Exception as e:
                logger.error(f"Failed to delete bet {bet_serial}: {e}")
                await interaction.response.edit_message(
                    content=f"Bet `{bet_serial}` cancellation failed: {e}",
                    view=None
                )
        else:
            await interaction.response.edit_message(
                content="Bet workflow cancelled.",
                view=None
            )
        self.parent_view.stop()


class BetDetailsModal(Modal, title="Enter Bet Details"):
    def __init__(self, line_type: str, is_manual: bool = False, is_first_leg: bool = False):
        super().__init__(title="Enter Bet Details")
        self.line_type = line_type
        self.is_manual = is_manual
        self.is_first_leg = is_first_leg  # Flag to determine if this is the first leg of a parlay

        if is_manual:
            self.team = TextInput(
                label="Team",
                placeholder="e.g., Lakers",
                required=True,
                max_length=100
            )
            self.opponent = TextInput(
                label="Opponent" if line_type == "game_line" else "Player",
                placeholder="e.g., Celtics or LeBron James",
                required=True,
                max_length=100
            )
            self.add_item(self.team)
            self.add_item(self.opponent)

        self.line = TextInput(
            label="Line",
            placeholder="e.g., -7.5, Over 220.5",
            required=True,
            max_length=100
        )
        self.odds = TextInput(
            label="Odds (American)",
            placeholder="e.g., -110, +150",
            required=True,
            max_length=10
        )

        # Include units input for all legs after the first leg of a parlay
        if not (self.is_first_leg and self.view.bet_details.get('bet_type') == "parlay"):
            self.units = TextInput(
                label="Units (e.g., 1, 1.5)",
                placeholder="Enter units to risk",
                required=True,
                max_length=5
            )
            self.add_item(self.units)

        if line_type == "player_prop" and not is_manual:
            self.player = TextInput(
                label="Player",
                placeholder="e.g., LeBron James",
                required=True,
                max_length=100
            )
            self.add_item(self.player)

        self.add_item(self.line)
        self.add_item(self.odds)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual}, is_first_leg={self.is_first_leg}")
        line = self.line.value.strip()
        odds = self.odds.value.strip()

        if not all([line, odds]):
            logger.warning("Modal submission failed: Missing required fields")
            await interaction.response.send_message("Please fill in all required fields.", ephemeral=True)
            return

        leg = {
            'line': line,
            'odds_str': odds,
        }

        # Set units if the field was present (not the first leg of a parlay)
        if hasattr(self, 'units'):
            units = self.units.value.strip()
            if not units:
                logger.warning("Modal submission failed: Missing units")
                await interaction.response.send_message("Please provide valid units.", ephemeral=True)
                return
            leg['units_str'] = units

        if self.is_manual:
            team = self.team.value.strip()
            opponent = self.opponent.value.strip()
            if not all([team, opponent]):
                logger.warning("Modal submission failed: Missing team or opponent/player")
                await interaction.response.send_message(
                    "Please provide valid team and opponent/player.",
                    ephemeral=True
                )
                return
            leg['team'] = team
            if self.line_type == "game_line":
                leg['opponent'] = opponent
            else:  # player_prop
                leg['player'] = opponent
        elif self.line_type == "player_prop":
            player = self.player.value.strip()
            if not player:
                logger.warning("Modal submission failed: Missing player")
                await interaction.response.send_message("Please provide a valid player.", ephemeral=True)
                return
            leg['player'] = player

        if 'legs' not in self.view.bet_details:
            self.view.bet_details['legs'] = []
        self.view.bet_details['legs'].append(leg)
        logger.debug(f"Bet details entered: {leg}")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        # If this is a parlay, redirect to add another leg or proceed to confirmation
        if self.view.bet_details.get('bet_type') == "parlay":
            # After adding the first leg, redirect to league selection for the next leg
            if len(self.view.bet_details['legs']) < 2:
                self.view.current_step = 2  # Redirect to league selection for the next leg
            else:
                # After adding the second or subsequent leg, proceed to confirmation
                self.view.current_step = 5  # Proceed to confirmation (step 7)
        else:
            self.view.current_step = 5  # Proceed to channel selection for straight bets

        await self.view.go_next(interaction)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            await interaction.followup.send(
                '❌ An error occurred with the bet details modal.',
                ephemeral=True
            )
        except discord.HTTPException:
            logger.warning("Could not send error followup for BetDetailsModal.")


class UnitsModal(Modal, title="Enter Parlay Units"):
    def __init__(self):
        super().__init__(title="Enter Parlay Units")
        self.units = TextInput(
            label="Units (e.g., 1, 1.5)",
            placeholder="Enter units to risk for the parlay",
            required=True,
            max_length=5
        )
        self.add_item(self.units)

    async def on_submit(self, interaction: Interaction):
        logger.debug("UnitsModal submitted")
        units = self.units.value.strip()

        if not units:
            logger.warning("UnitsModal submission failed: Missing units")
            await interaction.response.send_message("Please provide valid units.", ephemeral=True)
            return

        # Apply the units to all legs in the parlay
        for leg in self.view.bet_details['legs']:
            leg['units_str'] = units

        logger.debug(f"Parlay units set: {units}")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        self.view.current_step = 5  # Proceed to channel selection
        await self.view.go_next(interaction)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in UnitsModal: {error}", exc_info=True)
        try:
            await interaction.followup.send(
                '❌ An error occurred with the units modal.',
                ephemeral=True
            )
        except discord.HTTPException:
            logger.warning("Could not send error followup for UnitsModal.")


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
            await interaction.response.defer()
            return
        self.parent_view.bet_details['channel_id'] = int(selected_value)
        logger.debug(f"Channel selected: {selected_value}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class AddLegButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.blurple,
            label="Add Leg",
            custom_id=f"add_leg_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        self.parent_view.current_step = 2  # Reset to league selection for new leg
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


class NextLegButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Next Leg",
            custom_id=f"next_leg_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        self.parent_view.current_step = 2  # Redirect to league selection for the next leg
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.go_next(interaction)


class ConfirmButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Confirm & Post",
            custom_id=f"confirm_bet_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.submit_bet(interaction)


class BetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600)
        self.original_interaction = interaction
        self.bot = bot
        self.current_step = 0
        self.bet_details = {'legs': []}
        self.games = []
        self.message: Optional[discord.WebhookMessage | discord.InteractionMessage] = None
        self.is_processing = False
        self.latest_interaction = interaction
        self.bet_slip_generator = BetSlipGenerator()
        self.preview_image_bytes = None

    async def start_flow(self):
        logger.debug("Starting bet workflow")
        try:
            self.message = await self.original_interaction.followup.send(
                "Starting bet placement...", view=self, ephemeral=True
            )
            await self.go_next(self.original_interaction)
        except discord.HTTPException as e:
            logger.error(f"Failed to send initial message: {e}")
            await self.original_interaction.followup.send(
                "❌ Failed to start bet workflow. Please try again.",
                ephemeral=True
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message(
                "You cannot interact with this bet placement.",
                ephemeral=True
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
        file: Optional[File] = None
    ):
        logger.debug(
            f"Editing message: content={content}, view={view is not None}, "
            f"embed={embed is not None}, file={file is not None}"
        )
        target_message = self.message
        try:
            if target_message:
                if isinstance(target_message, discord.InteractionMessage):
                    await target_message.edit(
                        content=content,
                        embed=embed,
                        view=view,
                        attachments=[file] if file else []
                    )
                elif isinstance(target_message, discord.WebhookMessage):
                    await target_message.edit(
                        content=content,
                        embed=embed,
                        view=view,
                        attachments=[file] if file else []
                    )
                else:
                    await self.original_interaction.edit_original_response(
                        content=content,
                        embed=embed,
                        view=view,
                        attachments=[file] if file else []
                    )
            else:
                await self.original_interaction.edit_original_response(
                    content=content,
                    embed=embed,
                    view=view,
                    attachments=[file] if file else []
                )
        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Failed to edit BetWorkflowView message: {e}")
            if interaction:
                await interaction.followup.send(
                    "❌ Failed to update bet workflow. Please try again.",
                    ephemeral=True
                )
        except Exception as e:
            logger.exception(f"Unexpected error editing BetWorkflowView message: {e}")
            if interaction:
                await interaction.followup.send(
                    "❌ An unexpected error occurred. Please try again.",
                    ephemeral=True
                )

    async def go_next(self, interaction: Interaction):
        if self.is_processing:
            logger.debug(f"Skipping go_next call; already processing step {self.current_step}")
            return
        self.is_processing = True
        try:
            logger.debug(
                f"Processing go_next: current_step={self.current_step}, "
                f"interaction_done={interaction.response.is_done()}"
            )
            self.clear_items()
            self.current_step += 1
            step_content = f"**Step {self.current_step}**"
            embed_to_send = None
            file_to_send = None

            logger.debug(f"Entering step {self.current_step}")

            try:
                if self.current_step == 1:
                    self.add_item(BetTypeSelect(self))
                    self.add_item(CancelButton(self))
                    step_content += ": Select Bet Type"
                    await self.edit_message(
                        interaction,
                        content=step_content,
                        view=self,
                        embed=embed_to_send
                    )
                elif self.current_step == 2:
                    allowed_leagues = [
                        "NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF",
                        "Soccer", "Tennis", "UFC/MMA"
                    ]
                    self.add_item(LeagueSelect(self, allowed_leagues))
                    self.add_item(CancelButton(self))
                    step_content += ": Select League"
                    await self.edit_message(
                        interaction,
                        content=step_content,
                        view=self,
                        embed=embed_to_send
                    )
                elif self.current_step == 3:
                    self.add_item(LineTypeSelect(self))
                    self.add_item(CancelButton(self))
                    step_content += ": Select Line Type"
                    await self.edit_message(
                        interaction,
                        content=step_content,
                        view=self,
                        embed=embed_to_send
                    )
                elif self.current_step == 4:
                    league = self.bet_details.get('league')
                    league_games = []
                    if league and league != "Other":
                        sport = None
                        if league in ["NFL", "NCAAF"]:
                            sport = "american-football"
                        elif league in ["NBA", "NCAAB"]:
                            sport = "basketball"
                        elif league == "MLB":
                            sport = "baseball"
                        elif league == "NHL":
                            sport = "hockey"
                        elif league == "Soccer":
                            sport = "soccer"
                        elif league == "Tennis":
                            sport = "tennis"

                        if sport and hasattr(self.bot, 'game_service'):
                            self.games = await self.bot.game_service.get_upcoming_games(
                                interaction.guild_id,
                                hours=72
                            )
                            league_games = [
                                g for g in self.games
                                if str(g.get('league_id')) == league or
                                g.get('league_name', '').lower() == league.lower()
                            ]

                    if league_games:
                        self.add_item(GameSelect(self, league_games))
                        self.add_item(CancelButton(self))
                        step_content += f": Select Game for {league} (or Other)"
                        logger.debug(f"Showing game selection for {league}")
                        await self.edit_message(
                            interaction,
                            content=step_content,
                            view=self,
                            embed=embed_to_send
                        )
                    else:
                        logger.warning(
                            f"No upcoming games found for league {league}. Prompting for manual entry."
                        )
                        self.add_item(ManualEntryButton(self))
                        self.add_item(CancelButton(self))
                        step_content = (
                            f"No games scheduled for {league}. "
                            "Would you like to manually enter game data?"
                        )
                        logger.debug(f"Sending manual entry prompt for {league}")
                        await self.edit_message(
                            interaction,
                            content=step_content,
                            view=self,
                            embed=embed_to_send
                        )
                elif self.current_step == 5:
                    line_type = self.bet_details.get('line_type')
                    game_id = self.bet_details.get('game_id')
                    is_manual = game_id == "Other"

                    logger.debug(
                        f"Step 5: line_type={line_type}, is_manual={is_manual}, "
                        f"game_id={game_id}, interaction_done={interaction.response.is_done()}"
                    )

                    if line_type == "player_prop" and not is_manual and hasattr(self.bot, 'game_service'):
                        players_data = await self.bot.game_service.get_game_players(game_id)
                        home_players = players_data.get('home_players', [])
                        away_players = players_data.get('away_players', [])
                        home_team = self.bet_details.get('home_team_name', 'Home Team')
                        away_team = self.bet_details.get('away_team_name', 'Away Team')

                        if home_players or away_players:
                            self.add_item(HomePlayerSelect(self, home_players, home_team))
                            self.add_item(AwayPlayerSelect(self, away_players, away_team))
                            self.add_item(CancelButton(self))
                            step_content += f": Select a Player from {home_team} or {away_team}"
                            logger.debug(f"Showing player dropdowns for {home_team} and {away_team}")
                            await self.edit_message(
                                interaction,
                                content=step_content,
                                view=self,
                                embed=embed_to_send
                            )
                        else:
                            logger.warning(
                                f"No players available for game {game_id}. Proceeding to manual player entry."
                            )
                            modal = BetDetailsModal(line_type=line_type, is_manual=False, is_first_leg=len(self.bet_details.get('legs', [])) == 0)
                            modal.view = self
                            logger.debug(f"Sending BetDetailsModal for player_prop, is_manual=False")
                            try:
                                if interaction.response.is_done():
                                    logger.warning("Interaction response already used; cannot send modal")
                                    await interaction.followup.send(
                                        "❌ Please restart the /bet command to enter details.",
                                        ephemeral=True
                                    )
                                    self.stop()
                                    return
                                await interaction.response.send_modal(modal)
                            except discord.HTTPException as e:
                                logger.error(f"Failed to send BetDetailsModal: {e}")
                                await interaction.followup.send(
                                    "❌ Failed to send bet details modal. Please try again.",
                                    ephemeral=True
                                )
                                self.stop()
                            return
                    else:
                        logger.debug("Skipping modal in step 5 for manual entry; advancing to step 6")
                        self.current_step = 5
                        await self.go_next(interaction)
                        return
                elif self.current_step == 6:
                    if not self.bet_details.get('legs'):
                        logger.error("No bet details provided for channel selection")
                        await self.edit_message(
                            interaction,
                            content="❌ No bet details provided. Please start over.",
                            view=None
                        )
                        self.stop()
                        return

                    channels = []
                    if hasattr(self.bot, 'db_manager'):
                        settings = await self.bot.db_manager.fetch_one(
                            "SELECT embed_channel_1, embed_channel_2 FROM server_settings WHERE guild_id = %s",
                            (interaction.guild_id,)
                        )
                        if settings:
                            for channel_id in [settings['embed_channel_1'], settings['embed_channel_2']]:
                                if channel_id:
                                    channel = interaction.guild.get_channel(int(channel_id))
                                    if channel and isinstance(channel, TextChannel) and channel.permissions_for(interaction.guild.me).send_messages:
                                        channels.append(channel)
                    else:
                        channels = sorted(
                            [
                                ch for ch in interaction.guild.text_channels
                                if ch.permissions_for(interaction.user).send_messages and
                                ch.permissions_for(interaction.guild.me).send_messages
                            ],
                            key=lambda c: c.position
                        )

                    if not channels:
                        await self.edit_message(
                            interaction,
                            content="Error: No text channels found where I can post.",
                            view=None
                        )
                        self.stop()
                        return

                    # Generate the bet serial number by creating the bet
                    legs = self.bet_details.get('legs', [])
                    if not legs:
                        await self.edit_message(
                            interaction,
                            content="❌ No bet details provided. Please start over.",
                            view=None
                        )
                        self.stop()
                        return

                    bet_type = self.bet_details.get('bet_type')
                    league = self.bet_details.get('league')
                    bet_serial = None
                    if bet_type == "straight":
                        leg = legs[0]
                        bet_serial = await self.bot.bet_service.create_bet(
                            guild_id=interaction.guild_id,
                            user_id=interaction.user.id,
                            game_id=self.bet_details.get('game_id') if self.bet_details.get('game_id') != 'Other' else None,
                            bet_type="player_prop" if leg.get('player') else "game_line",
                            team=leg.get('team', leg.get('line')),
                            opponent=leg.get('opponent'),
                            line=leg.get('line'),
                            units=float(leg.get('units_str', '1.00')),
                            odds=float(leg.get('odds_str', '-110')),
                            channel_id=None,
                            league=league
                        )
                    else:  # Parlay
                        bet_serial = await self.bot.bet_service.create_parlay_bet(
                            guild_id=interaction.guild_id,
                            user_id=interaction.user.id,
                            legs=[
                                {
                                    'game_id': self.bet_details.get('game_id') if self.bet_details.get('game_id') != 'Other' else None,
                                    'bet_type': "player_prop" if leg.get('player') else "game_line",
                                    'team': leg.get('team', leg.get('line')),
                                    'opponent': leg.get('opponent'),
                                    'line': leg.get('line'),
                                    'units': float(leg.get('units_str', '1.00')),
                                    'odds': float(leg.get('odds_str', '-110')),
                                } for leg in legs
                            ],
                            channel_id=None,
                            league=league
                        )

                    self.bet_details['bet_serial'] = bet_serial

                    # Generate the preview image
                    leg = legs[0]  # Use first leg for basic info if straight bet
                    home_team = self.bet_details.get('home_team_name', leg.get('team', 'Unknown'))
                    away_team = self.bet_details.get('away_team_name', leg.get('opponent', 'Unknown'))
                    league = self.bet_details.get('league', 'NHL')
                    timestamp = datetime.now(timezone.utc)

                    if bet_type == "parlay":
                        # Check if all legs share the same game_id for same-game parlay
                        game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
                        is_same_game = len(game_ids) == 1
                        parlay_legs = [
                            {
                                'home_team': leg.get('team', 'Unknown'),
                                'away_team': leg.get('opponent', 'Unknown'),
                                'line': leg.get('line', 'ML'),
                                'odds': float(leg.get('odds_str', '-110')),
                                'units': float(leg.get('units_str', '1.00'))
                            } for leg in legs
                        ]
                        bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                            home_team=home_team,
                            away_team=away_team,
                            league=league,
                            line=legs[0].get('line', 'ML'),  # Fallback for straight bet compatibility
                            odds=float(legs[0].get('odds_str', '-110')),
                            units=float(legs[0].get('units_str', '1.00')),
                            bet_id=str(bet_serial),
                            timestamp=timestamp,
                            bet_type="parlay",
                            parlay_legs=parlay_legs,
                            is_same_game=is_same_game
                        )
                    else:
                        bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                            home_team=home_team,
                            away_team=away_team,
                            league=league,
                            line=leg.get('line', 'ML'),
                            odds=float(leg.get('odds_str', '-110')),
                            units=float(leg.get('units_str', '1.00')),
                            bet_id=str(bet_serial),
                            timestamp=timestamp,
                            bet_type="straight"
                        )

                    # Save the image to a BytesIO object
                    self.preview_image_bytes = io.BytesIO()
                    bet_slip_image.save(self.preview_image_bytes, 'PNG')
                    self.preview_image_bytes.seek(0)

                    # Create a Discord file for the preview
                    file_to_send = File(self.preview_image_bytes, filename="bet_slip_preview.png")
                    self.preview_image_bytes.seek(0)

                    self.add_item(ChannelSelect(self, channels))
                    self.add_item(CancelButton(self))
                    step_content += ": Select Channel to Post Bet"
                    logger.debug(f"Showing channel selection for step 6")
                    await self.edit_message(interaction, content=step_content, view=self, file=file_to_send)
                elif self.current_step == 7:
                    try:
                        legs = self.bet_details.get('legs', [])
                        if self.bet_details.get('bet_type') == "parlay" and len(legs) < 2:
                            raise ValueError("Parlay bets require at least two legs")

                        for leg in legs:
                            odds_str = leg.get('odds_str', '').replace('+','').strip()
                            units_str = leg.get('units_str', '').lower().replace('u','').strip()

                            if not odds_str:
                                raise ValueError("Odds cannot be empty")
                            if not units_str:
                                raise ValueError("Units cannot be empty")

                            try:
                                odds_val = int(odds_str)
                            except ValueError:
                                raise ValueError("Odds must be a valid integer (e.g., -110, +150)")
                            if not (-10000 <= odds_val <= 10000):
                                raise ValueError("Odds must be between -10000 and +10000")
                            if -100 < odds_val < 100:
                                raise ValueError("Odds cannot be between -99 and +99")
                            leg['odds'] = float(odds_val)

                            try:
                                units_val = float(units_str)
                            except ValueError:
                                raise ValueError("Units must be a valid number (e.g., 1, 1.5)")
                            if not (0.1 <= units_val <= 10.0):
                                raise ValueError("Units must be between 0.1 and 10.0")
                            leg['units'] = units_val

                        # Reuse the preview image
                        if self.preview_image_bytes:
                            file_to_send = File(self.preview_image_bytes, filename="bet_slip_preview.png")
                            self.preview_image_bytes.seek(0)  # Reset pointer for reuse
                        else:
                            # Generate the image if it doesn't exist (e.g., after adding more legs)
                            bet_type = self.bet_details.get('bet_type')
                            league = self.bet_details.get('league', 'NHL')
                            timestamp = datetime.now(timezone.utc)
                            legs = self.bet_details.get('legs', [])
                            leg = legs[0]
                            home_team = self.bet_details.get('home_team_name', leg.get('team', 'Unknown'))
                            away_team = self.bet_details.get('away_team_name', leg.get('opponent', 'Unknown'))
                            bet_serial = self.bet_details.get('bet_serial', 'Unknown')

                            if bet_type == "parlay":
                                game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
                                is_same_game = len(game_ids) == 1
                                parlay_legs = [
                                    {
                                        'home_team': leg.get('team', 'Unknown'),
                                        'away_team': leg.get('opponent', 'Unknown'),
                                        'line': leg.get('line', 'ML'),
                                        'odds': float(leg.get('odds_str', '-110')),
                                        'units': float(leg.get('units_str', '1.00'))
                                    } for leg in legs
                                ]
                                bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                                    home_team=home_team,
                                    away_team=away_team,
                                    league=league,
                                    line=legs[0].get('line', 'ML'),
                                    odds=float(legs[0].get('odds_str', '-110')),
                                    units=float(legs[0].get('units_str', '1.00')),
                                    bet_id=str(bet_serial),
                                    timestamp=timestamp,
                                    bet_type="parlay",
                                    parlay_legs=parlay_legs,
                                    is_same_game=is_same_game
                                )
                            else:
                                bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                                    home_team=home_team,
                                    away_team=away_team,
                                    league=league,
                                    line=leg.get('line', 'ML'),
                                    odds=float(leg.get('odds_str', '-110')),
                                    units=float(leg.get('units_str', '1.00')),
                                    bet_id=str(bet_serial),
                                    timestamp=timestamp,
                                    bet_type="straight"
                                )

                            self.preview_image_bytes = io.BytesIO()
                            bet_slip_image.save(self.preview_image_bytes, 'PNG')
                            self.preview_image_bytes.seek(0)
                            file_to_send = File(self.preview_image_bytes, filename="bet_slip_preview.png")
                            self.preview_image_bytes.seek(0)

                        # Add buttons based on bet type and number of legs
                        if self.bet_details.get('bet_type') == "parlay":
                            self.add_item(ConfirmButton(self))  # Always show "Confirm & Post"
                            self.add_item(NextLegButton(self))  # Always show "Next Leg" for parlays
                            self.add_item(CancelButton(self))
                        else:
                            self.add_item(ConfirmButton(self))  # Straight bet: only "Confirm & Post"
                            self.add_item(CancelButton(self))

                        step_content = f"**Step {self.current_step}**: Please Confirm Your Bet"
                        logger.debug(f"Showing confirmation for step 7")
                        await self.edit_message(interaction, content=step_content, view=self, file=file_to_send)
                    except ValueError as ve:
                        logger.error(f"Bet input validation failed: {ve}")
                        await self.edit_message(
                            interaction,
                            content=f"❌ Error: {ve} Please start over.",
                            view=None
                        )
                        self.stop()
                        return
                else:
                    logger.error(f"BetWorkflowView reached unexpected step: {self.current_step}")
                    await self.edit_message(
                        interaction,
                        content="❌ Invalid step reached. Please start over.",
                        view=None
                    )
                    self.stop()
                    return

            except Exception as e:
                logger.exception(f"Error in bet workflow step {self.current_step}: {e}")
                try:
                    await self.edit_message(interaction, content="An unexpected error occurred.", view=None, embed=None)
                except Exception:
                    logger.error("Failed to send error message to user")
                self.stop()

        finally:
            self.is_processing = False

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        await self.edit_message(interaction, content="Processing and posting bet...", view=None, embed=None)
        sent_message = None

        try:
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None

            if post_channel and isinstance(post_channel, TextChannel):
                # Update the bet with the selected channel
                bet_serial = details.get('bet_serial')
                if not bet_serial:
                    raise ValueError("Bet serial not found. Please start over.")

                # Update the bet with the channel_id (since it was created with channel_id=None)
                if details.get('bet_type') == "straight":
                    await self.bot.bet_service.update_bet_channel(
                        bet_serial=bet_serial,
                        channel_id=post_channel_id
                    )
                else:  # Parlay
                    await self.bot.bet_service.update_parlay_bet_channel(
                        bet_serial=bet_serial,
                        channel_id=post_channel_id
                    )

                # Reuse the preview image
                if self.preview_image_bytes:
                    discord_file = File(self.preview_image_bytes, filename=f"bet_slip_{bet_serial}.png")
                else:
                    raise ValueError("Preview image not found. Please start over.")

                view = BetResolutionView(bet_serial)
                sent_message = await post_channel.send(file=discord_file, view=view)

                if sent_message and hasattr(self.bot.bet_service, 'pending_reactions'):
                    self.bot.bet_service.pending_reactions[sent_message.id] = {
                        'bet_serial': bet_serial,
                        'user_id': interaction.user.id,
                        'guild_id': interaction.guild_id,
                        'channel_id': post_channel_id,
                        'legs': details.get('legs'),
                        'league': details.get('league'),
                        'bet_type': details.get('bet_type')
                    }
                    logger.debug(f"Tracking reactions for msg {sent_message.id} (Bet: {bet_serial})")

                success_message = f"✅ Bet placed successfully! (ID: `{bet_serial}`). Posted to {post_channel.mention}."
                await self.edit_message(interaction, content=success_message, view=None, embed=None)
            else:
                logger.error(f"Could not find channel {post_channel_id} to post bet {bet_serial}.")
                failure_message = f"⚠️ Bet placed (ID: `{bet_serial}`), but failed to post."
                await self.edit_message(interaction, content=failure_message, view=None, embed=None)

        except (ValidationError, BetServiceError) as e:
            logger.error(f"Error submitting bet: {e}")
            await self.edit_message(interaction, content=f"❌ Error placing bet: {e}", view=None, embed=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting bet: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred.", view=None, embed=None)
        finally:
            self.preview_image_bytes = None  # Clear the stored image
            self.stop()


class BetResolutionView(View):
    def __init__(self, bet_serial: int):
        super().__init__(timeout=None)
        self.bet_serial = bet_serial

    @discord.ui.button(label="Win", style=discord.ButtonStyle.green, emoji="✅", custom_id="bet_resolve_win")
    async def win_button(self, interaction: Interaction, button: Button):
        try:
            await interaction.message.add_reaction("✅")
            await interaction.response.send_message("Added Win reaction.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error adding win reaction: {e}")
            await interaction.response.send_message("Could not add reaction.", ephemeral=True)

    @discord.ui.button(label="Loss", style=discord.ButtonStyle.red, emoji="❌", custom_id="bet_resolve_loss")
    async def loss_button(self, interaction: Interaction, button: Button):
        try:
            await interaction.message.add_reaction("❌")
            await interaction.response.send_message("Added Loss reaction.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error adding loss reaction: {e}")
            await interaction.response.send_message("Could not add reaction.", ephemeral=True)

    @discord.ui.button(label="Push", style=discord.ButtonStyle.grey, emoji="🅿️", custom_id="bet_resolve_push")
    async def push_button(self, interaction: Interaction, button: Button):
        try:
            await interaction.message.add_reaction("🅿️")
            await interaction.response.send_message("Added Push reaction.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error adding push reaction: {e}")
            await interaction.response.send_message("Could not add reaction.", ephemeral=True)


class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bet", description="Place a new bet through a guided workflow.")
    async def bet_command(self, interaction: Interaction):
        """Starts the interactive betting workflow."""
        logger.info(f"Bet command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            is_auth = True  # Replace with actual authorization check if needed
            if not is_auth:
                await interaction.response.send_message(
                    "❌ You are not authorized to place bets.",
                    ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True, thinking=True)
            view = BetWorkflowView(interaction, self.bot)
            await view.start_flow()

        except Exception as e:
            logger.exception(f"Error initiating bet command: {e}")
            error_message = "❌ An error occurred while starting the betting workflow."
            if interaction.response.is_done():
                try:
                    await interaction.followup.send(error_message, ephemeral=True)
                except discord.HTTPException:
                    pass
            else:
                try:
                    await interaction.response.send_message(error_message, ephemeral=True)
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(BettingCog(bot))
    logger.info("BettingCog loaded")
