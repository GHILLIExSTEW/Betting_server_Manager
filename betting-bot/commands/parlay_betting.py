# betting-bot/commands/parlay_betting.py

"""Parlay betting workflow for placing multi-leg bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel, File, Embed
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union, Any
from datetime import datetime, timezone
import io
import uuid

try:
    from utils.errors import BetServiceError, ValidationError, GameNotFoundError
    from utils.image_generator import BetSlipGenerator
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
        for game in games[:24]:
            home = game.get('home_team_name', 'Unknown')
            away = game.get('away_team_name', 'Unknown')
            start_dt = game.get('start_time')
            time_str = start_dt.strftime('%m/%d %H:%M %Z') if isinstance(start_dt, datetime) else 'Time N/A'
            label = f"{away} @ {home} ({time_str})"
            game_api_id = game.get('id')
            if game_api_id is None:
                continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id)))
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(placeholder="Select Game (or Other)...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['game_id'] = self.values[0]
        if self.values[0] != "Other":
            game = next((g for g in self.parent_view.games if str(g.get('id')) == self.values[0]), None)
            if game:
                self.parent_view.bet_details['home_team_name'] = game.get('home_team_name', 'Unknown')
                self.parent_view.bet_details['away_team_name'] = game.get('away_team_name', 'Unknown')
        logger.debug(f"Game selected: {self.values[0]} by user {interaction.user.id}")
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
            self.parent_view.bet_details['player'] = None
        logger.debug(f"Home player selected: {self.values[0] if self.values else 'None'} by user {interaction.user.id}")
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
        super().__init__(placeholder=f"{team_name} Players...", options=options, min_values=0, max_values=1)

    async def callback(self, interaction: Interaction):
        if self.values and self.values[0] != "none":
            self.parent_view.bet_details['player'] = self.values[0].replace("away_", "")
            for item in self.parent_view.children:
                if isinstance(item, HomePlayerSelect):
                    item.disabled = True
        else:
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
            custom_id=f"manual_entry_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Manual Entry button clicked by user {interaction.user.id}")
        self.parent_view.bet_details['game_id'] = "Other"
        self.disabled = True
        for item in self.parent_view.children:
            if isinstance(item, CancelButton):
                item.disabled = True
        line_type = self.parent_view.bet_details.get('line_type')
        leg_number = len(self.parent_view.bet_details.get('legs', [])) + 1
        try:
            modal = BetDetailsModal(line_type=line_type, is_manual=True, leg_number=leg_number)
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
            try:
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
            custom_id=f"cancel_{parent_view.original_interaction.id}"
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

class BetDetailsModal(Modal):
    def __init__(self, line_type: str, is_manual: bool = False, leg_number: int = 1):
        title = f"Leg {leg_number}: Enter Bet Details"
        super().__init__(title=title[:45])
        self.line_type = line_type
        self.is_manual = is_manual
        self.leg_number = leg_number

        if is_manual:
            self.team = TextInput(label="Team", required=True, max_length=100)
            self.opponent = TextInput(
                label="Opponent" if line_type == "game_line" else "Player",
                required=True,
                max_length=100
            )
            self.add_item(self.team)
            self.add_item(self.opponent)

        if line_type == "player_prop" and not is_manual:
            self.player = TextInput(label="Player", required=True, max_length=100)
            self.add_item(self.player)

        self.line = TextInput(label="Line", required=True, max_length=100)
        self.add_item(self.line)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual}, leg_number={self.leg_number} by user {interaction.user.id}")
        line = self.line.value.strip()

        if not line:
            logger.warning("Modal submission failed: Missing required fields")
            await interaction.response.send_message("Please fill in all required fields.", ephemeral=True)
            return

        leg = {'line': line, 'odds_str': '-110'}  # Default odds for individual leg

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
            else:
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

        self.view.current_step = 4  # Leg decision step
        self.view.bet_details.pop('game_id', None)
        self.view.bet_details.pop('home_team_name', None)
        self.view.bet_details.pop('away_team_name', None)
        self.view.bet_details.pop('line_type', None)
        self.view.bet_details.pop('player', None)
        await self.view.go_next(interaction)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            await interaction.followup.send('❌ An error occurred with the bet details modal.', ephemeral=True)
        except discord.HTTPException:
            logger.warning("Could not send error followup for BetDetailsModal.")

class UnitsSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="1 Unit", value="1.0"),
            SelectOption(label="2 Units", value="2.0"),
            SelectOption(label="3 Units", value="3.0")
        ]
        super().__init__(placeholder="Select Units for Parlay...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        units = self.values[0]
        logger.debug(f"Units selected: {units} by user {interaction.user.id}")
        for leg in self.parent_view.bet_details['legs']:
            leg['units_str'] = units
        self.disabled = True
        await interaction.response.defer()
        self.parent_view.current_step = 6  # Proceed to Channel selection
        await self.parent_view.go_next(interaction)

class UnitsView(View):
    def __init__(self, parent_view):
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.add_item(UnitsSelect(self.parent_view))
        self.add_item(CancelButton(self.parent_view))

class AddLegButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.green,
            label="Add Leg?",
            custom_id=f"add_leg_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Add Leg button clicked by user {interaction.user.id}")
        self.parent_view.current_step = 0  # Return to League selection
        self.parent_view.bet_details.pop('game_id', None)
        self.parent_view.bet_details.pop('home_team_name', None)
        self.parent_view.bet_details.pop('away_team_name', None)
        self.parent_view.bet_details.pop('line_type', None)
        self.parent_view.bet_details.pop('player', None)
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.go_next(interaction)

class FinalizeButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.blurple,
            label="Finalize",
            custom_id=f"finalize_{parent_view.original_interaction.id}",
            disabled=len(parent_view.bet_details.get('legs', [])) < 2
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Finalize button clicked by user {interaction.user.id}")
        # Show final odds modal first
        final_odds_modal = FinalOddsModal()
        await interaction.response.send_modal(final_odds_modal)
        await final_odds_modal.wait()

        if not final_odds_modal.odds_value:
            return

        # Update bet details with final odds
        self.parent_view.bet_details['total_odds_str'] = final_odds_modal.odds_value
        
        # Proceed to units selection
        self.parent_view.current_step = 5
        await self.parent_view.go_next(interaction)

class LegDecisionView(View):
    def __init__(self, parent_view):
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.add_item(AddLegButton(self.parent_view))
        self.add_item(FinalizeButton(self))
        self.add_item(CancelButton(self))

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
        logger.debug(f"Channel selected: {selected_value} by user {interaction.user.id}")
        self.disabled = True
        await interaction.response.defer()
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
        logger.debug(f"Confirm button clicked by user {interaction.user.id}")
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.submit_bet(interaction)

class FinalOddsModal(Modal):
    def __init__(self):
        super().__init__(title="Enter Final Parlay Odds")
        self.odds = TextInput(
            label="Final Odds",
            placeholder="Enter the final odds (e.g., -110, +150)",
            required=True,
            max_length=10
        )

    async def on_submit(self, interaction: Interaction):
        try:
            # Validate odds format
            odds_str = self.odds.value.strip()
            if not odds_str.startswith(('-', '+')):
                odds_str = f"+{odds_str}"
            float(odds_str)  # Validate it's a number
            await interaction.response.defer()
            self.odds_value = odds_str
        except ValueError:
            await interaction.response.send_message("❌ Invalid odds format. Please use American odds format (e.g., -110, +150)", ephemeral=True)
            self.odds_value = None

class ParlayBetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot):
        super().__init__(timeout=600)
        self.original_interaction = interaction
        self.bot = bot
        self.current_step = 0
        self.bet_details = {'legs': [], 'bet_type': 'parlay'}
        self.games = []
        self.message: Optional[discord.WebhookMessage | discord.InteractionMessage] = None
        self.is_processing = False
        self.latest_interaction = interaction
        self.bet_slip_generator = BetSlipGenerator()
        self.preview_image_bytes = None
        self.team_logos = {}  # Store team logos for each leg

    async def finalize_bet(self, interaction: Interaction):
        """Handle the finalization of the parlay bet."""
        try:
            # Show final odds modal
            final_odds_modal = FinalOddsModal()
            await interaction.response.send_modal(final_odds_modal)
            await final_odds_modal.wait()

            if not final_odds_modal.odds_value:
                return

            # Update bet details with final odds
            self.bet_details['total_odds_str'] = final_odds_modal.odds_value

            # Generate preview
            try:
                bet_serial = str(uuid.uuid4())  # Temporary ID for preview
                self.bet_details['bet_serial'] = bet_serial
                
                legs = self.bet_details.get('legs', [])
                if not legs:
                    await interaction.followup.send("❌ No bet legs found. Please start over.", ephemeral=True)
                    self.stop()
                    return

                leg = legs[0]
                home_team = self.bet_details.get('home_team_name', leg.get('team', 'Unknown'))
                away_team = self.bet_details.get('away_team_name', leg.get('opponent', 'Unknown'))
                league = self.bet_details.get('league', 'NHL')
                timestamp = datetime.now(timezone.utc)

                # Prepare parlay legs with stored logos
                parlay_legs = []
                for leg in legs:
                    leg_dict = {
                        'home_team': leg.get('team', 'Unknown'),
                        'away_team': leg.get('opponent', 'Unknown'),
                        'line': leg.get('line', 'ML'),
                        'odds': float(final_odds_modal.odds_value),
                        'units': float(leg.get('units_str', '1.00'))
                    }
                    parlay_legs.append(leg_dict)

                # Generate preview image
                bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    line=legs[0].get('line', 'ML'),
                    odds=float(final_odds_modal.odds_value),
                    units=float(legs[0].get('units_str', '1.00')),
                    bet_id=bet_serial,
                    timestamp=timestamp,
                    bet_type="parlay",
                    parlay_legs=parlay_legs
                )

                # Save preview image
                self.preview_image_bytes = io.BytesIO()
                bet_slip_image.save(self.preview_image_bytes, format='PNG')
                self.preview_image_bytes.seek(0)

                # Get available channels
                channels = []
                if interaction.guild:
                    for channel in interaction.guild.text_channels:
                        if channel.permissions_for(interaction.guild.me).send_messages:
                            channels.append(channel)

                # Show preview with channel selection
                file_to_send = File(self.preview_image_bytes, filename="bet_slip_preview.png")
                self.preview_image_bytes.seek(0)

                # Clear existing items and add channel selection
                self.clear_items()
                self.add_item(ChannelSelect(self, channels))
                self.add_item(CancelButton(self))

                await interaction.followup.send(
                    "Please review your bet and select a channel to post it:",
                    view=self,
                    file=file_to_send,
                    ephemeral=True
                )

            except Exception as e:
                logger.error(f"Error generating preview: {e}", exc_info=True)
                await interaction.followup.send(
                    "❌ Error generating bet preview. Please try again.",
                    ephemeral=True
                )
                self.stop()

        except Exception as e:
            logger.error(f"Error in finalize_bet: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ Error finalizing bet. Please try again.",
                ephemeral=True
            )
            self.stop()

    async def add_leg(self, interaction: Interaction, leg_details: Dict[str, Any]):
        """Add a leg to the parlay bet."""
        try:
            # Remove odds input from leg details
            leg_details.pop('odds_str', None)  # We'll get final odds at the end
            self.bet_details['legs'].append(leg_details)

            # Store team logos for this leg
            home_team = leg_details.get('team', 'Unknown')
            away_team = leg_details.get('opponent', 'Unknown')
            league = leg_details.get('league', 'NHL')
            
            # Add teams to the stored logos dict
            self.team_logos[f"{home_team}_{league}"] = None  # Will be populated when generating image
            self.team_logos[f"{away_team}_{league}"] = None

            leg_count = len(self.bet_details['legs'])
            await interaction.response.send_message(
                f"✅ Added leg {leg_count} to parlay. Would you like to add another leg or finalize the bet?",
                view=self,
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error adding leg: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Error adding leg to parlay. Please try again.",
                ephemeral=True
            )
            self.stop()

    async def start_flow(self):
        logger.debug(f"Starting parlay bet workflow for user {self.original_interaction.user} (ID: {self.original_interaction.user.id})")
        try:
            self.message = await self.original_interaction.followup.send(
                "Starting parlay bet placement...", view=self, ephemeral=True
            )
            await self.go_next(self.original_interaction)
        except discord.HTTPException as e:
            logger.error(f"Failed to send initial message for parlay workflow: {e}")
            await self.original_interaction.followup.send(
                "❌ Failed to start bet workflow. Please try again.", ephemeral=True
            )
            self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            logger.debug(f"Unauthorized interaction attempt by {interaction.user} (ID: {interaction.user.id})")
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
        file: Optional[File] = None
    ):
        logger.debug(
            f"Editing message: content={content}, view={view is not None}, "
            f"embed={embed is not None}, file={file is not None} by user {interaction.user.id if interaction else 'N/A'}"
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
            logger.warning(f"Failed to edit ParlayBetWorkflowView message: {e}")
            if interaction:
                await interaction.followup.send(
                    "❌ Failed to update bet workflow. Please try again.", ephemeral=True
                )
        except Exception as e:
            logger.exception(f"Unexpected error editing ParlayBetWorkflowView message: {e}")
            if interaction:
                await interaction.followup.send(
                    "❌ An unexpected error occurred. Please try again.", ephemeral=True
                )

    async def go_next(self, interaction: Interaction):
        """Handle progression to the next step in the workflow."""
        if self.is_processing:
            return

        self.is_processing = True
        try:
            step_content = f"**Step {self.current_step + 1}**"
            self.clear_items()

            if self.current_step == 0:
                # League selection
                leagues = ["NHL", "NFL", "NBA", "MLB", "NCAAB", "NCAAF", "UFC", "Soccer"]
                self.add_item(LeagueSelect(self, leagues))
                self.add_item(CancelButton(self))
                step_content += ": Select League"
                await self.edit_message(interaction, content=step_content, view=self)
            elif self.current_step == 1:
                # Line type selection
                self.add_item(LineTypeSelect(self))
                self.add_item(CancelButton(self))
                step_content += ": Select Line Type"
                await self.edit_message(interaction, content=step_content, view=self)
            elif self.current_step == 2:
                # Game selection
                if hasattr(self.bot, 'game_service'):
                    try:
                        league = self.bet_details.get('league', 'NHL')
                        self.games = await self.bot.game_service.get_upcoming_games(league)
                        if self.games:
                            self.add_item(GameSelect(self, self.games))
                            self.add_item(ManualEntryButton(self))
                            self.add_item(CancelButton(self))
                            step_content += ": Select Game or Enter Manually"
                            await self.edit_message(interaction, content=step_content, view=self)
                        else:
                            logger.warning(f"No upcoming games found for league {league}. Prompting for manual entry.")
                            self.add_item(ManualEntryButton(self))
                            self.add_item(CancelButton(self))
                            step_content = f"No games scheduled for {league}. Would you like to manually enter game data?"
                            await self.edit_message(interaction, content=step_content, view=self)
                    except Exception as e:
                        logger.error(f"Error fetching games: {e}")
                        self.add_item(ManualEntryButton(self))
                        self.add_item(CancelButton(self))
                        step_content = "Error fetching games. Would you like to manually enter game data?"
                        await self.edit_message(interaction, content=step_content, view=self)
                else:
                    self.add_item(ManualEntryButton(self))
                    self.add_item(CancelButton(self))
                    step_content = "Game service not available. Please enter game details manually."
                    await self.edit_message(interaction, content=step_content, view=self)
            elif self.current_step == 3:
                # Bet details entry
                line_type = self.bet_details.get('line_type')
                game_id = self.bet_details.get('game_id')
                is_manual = game_id == "Other"
                leg_number = len(self.bet_details.get('legs', [])) + 1
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
                        await self.edit_message(interaction, content=step_content, view=self)
                    else:
                        logger.warning(f"No players available for game {game_id}. Proceeding to manual player entry.")
                        modal = BetDetailsModal(line_type=line_type, is_manual=False, leg_number=leg_number)
                        modal.view = self
                        try:
                            if interaction.response.is_done():
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
                    modal = BetDetailsModal(line_type=line_type, is_manual=is_manual, leg_number=leg_number)
                    modal.view = self
                    try:
                        if interaction.response.is_done():
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
            elif self.current_step == 4:
                # After bet details are entered
                leg_count = len(self.bet_details.get('legs', []))
                step_content = f"Leg {leg_count} added successfully. Add another leg or finalize the parlay?"
                self.add_item(AddLegButton(self))
                self.add_item(FinalizeButton(self))
                self.add_item(CancelButton(self))
                await self.edit_message(interaction, content=step_content, view=self)
            elif self.current_step == 5:
                # Units selection
                step_content = "Select units for the parlay"
                view = UnitsView(self)
                await self.edit_message(interaction, content=step_content, view=view)
            elif self.current_step == 6:
                # Generate preview and show channel selection
                try:
                    # Get available channels
                    channels = []
                    if interaction.guild:
                        for channel in interaction.guild.text_channels:
                            if channel.permissions_for(interaction.guild.me).send_messages:
                                channels.append(channel)

                    if not channels:
                        logger.error("No writable channels found")
                        await self.edit_message(
                            interaction,
                            content="❌ No text channels found where I can post.",
                            view=None
                        )
                        self.stop()
                        return

                    # Generate preview image
                    legs = self.bet_details.get('legs', [])
                    leg = legs[0]
                    home_team = self.bet_details.get('home_team_name', leg.get('team', 'Unknown'))
                    away_team = self.bet_details.get('away_team_name', leg.get('opponent', 'Unknown'))
                    league = self.bet_details.get('league', 'NHL')
                    timestamp = datetime.now(timezone.utc)
                    game_ids = {leg.get('game_id') for leg in legs if leg.get('game_id') and leg.get('game_id') != 'Other'}
                    is_same_game = len(game_ids) == 1
                    parlay_legs = [
                        {
                            'home_team': leg.get('team', 'Unknown'),
                            'away_team': leg.get('opponent', 'Unknown'),
                            'line': leg.get('line', 'ML'),
                            'odds': float(self.bet_details.get('total_odds_str', '-110')),
                            'units': float(leg.get('units_str', '1.00'))
                        } for leg in legs
                    ]

                    bet_slip_image = self.bet_slip_generator.generate_bet_slip(
                        home_team=home_team,
                        away_team=away_team,
                        league=league,
                        line=legs[0].get('line', 'ML'),
                        odds=float(self.bet_details.get('total_odds_str', '-110')),
                        units=float(legs[0].get('units_str', '1.00')),
                        bet_id=str(uuid.uuid4()),  # Temporary ID for preview
                        timestamp=timestamp,
                        bet_type="parlay",
                        parlay_legs=parlay_legs,
                        is_same_game=is_same_game
                    )

                    self.preview_image_bytes = io.BytesIO()
                    bet_slip_image.save(self.preview_image_bytes, format='PNG')
                    self.preview_image_bytes.seek(0)
                    file_to_send = File(self.preview_image_bytes, filename="bet_slip_preview.png")
                    self.preview_image_bytes.seek(0)

                    # Show preview with channel selection
                    self.clear_items()
                    self.add_item(ChannelSelect(self, channels))
                    self.add_item(CancelButton(self))
                    step_content = "Please review your bet and select a channel to post it:"
                    await self.edit_message(interaction, content=step_content, view=self, file=file_to_send)

                except Exception as e:
                    logger.error(f"Error generating preview: {e}", exc_info=True)
                    await self.edit_message(
                        interaction,
                        content="❌ Error generating bet preview. Please try again.",
                        view=None
                    )
                    self.stop()
            else:
                logger.error(f"ParlayBetWorkflowView reached unexpected step: {self.current_step}")
                await self.edit_message(interaction, content="❌ Invalid step reached. Please start over.", view=None)
                self.stop()
                return

        except Exception as e:
            logger.exception(f"Error in parlay bet workflow step {self.current_step}: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred.", view=None)
            self.stop()

        finally:
            self.is_processing = False

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        logger.debug(f"Submitting parlay bet for user {interaction.user} (ID: {interaction.user.id}), bet_serial={details.get('bet_serial')}")
        await self.edit_message(interaction, content="Processing and posting bet...", view=None)
        try:
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None
            if not post_channel or not isinstance(post_channel, TextChannel):
                logger.error(f"Invalid or inaccessible channel {post_channel_id} for bet {details.get('bet_serial')}")
                raise ValueError(f"Could not find text channel {post_channel_id} to post bet.")

            bet_serial = details.get('bet_serial')
            if not bet_serial:
                logger.error("Bet serial not found in bet details")
                raise ValueError("Bet serial not found. Please start over.")
            await self.bot.bet_service.update_parlay_bet_channel(bet_serial=bet_serial, channel_id=post_channel_id)

            if not self.preview_image_bytes:
                logger.error(f"Preview image bytes not found for bet {bet_serial}")
                raise ValueError("Preview image not found. Please start over.")

            # Fetch the member_role for mentioning
            role_mention = ""
            try:
                settings = await self.bot.db_manager.fetch_one(
                    "SELECT member_role FROM guild_settings WHERE guild_id = %s",
                    (interaction.guild_id,)
                )
                if settings and settings.get('member_role'):
                    role_id = int(settings['member_role'])
                    role = interaction.guild.get_role(role_id)
                    if role:
                        role_mention = role.mention
                    else:
                        logger.warning(f"Role ID {role_id} not found in guild {interaction.guild_id}.")
            except Exception as e:
                logger.error(f"Error fetching member_role for guild {interaction.guild_id}: {e}")

            # Fetch capper info for display name and avatar
            display_name = interaction.user.display_name
            avatar_url = interaction.user.avatar.url if interaction.user.avatar else None
            try:
                capper_info = await self.bot.db_manager.fetch_one(
                    "SELECT display_name, image_path FROM cappers WHERE user_id = %s AND guild_id = %s",
                    (interaction.user.id, interaction.guild_id)
                )
                if capper_info:
                    display_name = capper_info['display_name'] if capper_info['display_name'] else display_name
                    avatar_url = capper_info['image_path'] if capper_info['image_path'] else avatar_url
            except Exception as e:
                logger.error(f"Error fetching capper info for user {interaction.user.id} in guild {interaction.guild_id}: {e}")

            # Create or fetch webhook to set username and avatar
            webhook = None
            try:
                webhooks = await post_channel.webhooks()
                for wh in webhooks:
                    if wh.user.id == self.bot.user.id:
                        webhook = wh
                        break
                if not webhook:
                    webhook = await post_channel.create_webhook(name="Bet Embed Webhook")
                logger.debug(f"Using webhook: {webhook.name} (ID: {webhook.id})")
            except discord.Forbidden as e:
                logger.error(f"Failed to create or fetch webhook in channel {post_channel_id}: {e}")
                raise ValueError("Bot lacks permission to manage webhooks.")
            except discord.HTTPException as e:
                logger.error(f"HTTP error creating webhook for channel {post_channel_id}: {e}")
                raise ValueError(f"Failed to create webhook: {e}")

            # Send the image as an attachment via the webhook
            logger.debug(f"Sending bet slip image for bet {bet_serial} to channel {post_channel_id}")
            self.preview_image_bytes.seek(0)  # Reset the BytesIO pointer
            discord_file = File(self.preview_image_bytes, filename=f"bet_slip_{bet_serial}.png")
            content = role_mention if role_mention else ""
            try:
                sent_message = await webhook.send(
                    content=content,
                    file=discord_file,
                    username=display_name,
                    avatar_url=avatar_url,
                    wait=True
                )
                logger.debug(f"Bet slip image sent successfully for bet {bet_serial}, message ID: {sent_message.id}")
            except discord.Forbidden as e:
                logger.error(f"Webhook send failed due to permissions in channel {post_channel_id}: {e}")
                raise ValueError("Bot lacks permission to send messages via webhook.")
            except discord.HTTPException as e:
                logger.error(f"Webhook send failed for bet {bet_serial}: {e}")
                raise ValueError(f"Failed to send webhook message: {e}")

            # Track the message for reaction monitoring
            if sent_message and hasattr(self.bot.bet_service, 'pending_reactions'):
                self.bot.bet_service.pending_reactions[sent_message.id] = {
                    'bet_serial': bet_serial,
                    'user_id': interaction.user.id,
                    'guild_id': interaction.guild_id,
                    'channel_id': post_channel_id,
                    'legs': details.get('legs'),
                    'league': details.get('league'),
                    'bet_type': 'parlay'
                }
                logger.debug(f"Added message {sent_message.id} to pending_reactions for bet {bet_serial}")

            await self.edit_message(
                interaction,
                content=f"✅ Bet placed successfully! (ID: `{bet_serial}`). Posted to {post_channel.mention}.",
                view=None
            )
        except (ValidationError, BetServiceError) as e:
            logger.error(f"Error submitting bet {details.get('bet_serial')}: {e}")
            await self.edit_message(interaction, content=f"❌ Error placing bet: {e}", view=None)
        except ValueError as e:
            logger.error(f"Error submitting bet {details.get('bet_serial')}: {e}")
            await self.edit_message(interaction, content=f"❌ Error placing bet: {e}", view=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting bet {details.get('bet_serial')}: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred while posting the bet.", view=None)
        finally:
            self.preview_image_bytes = None
            self.stop()

async def setup(bot):
    """Setup function to register the ParlayBetWorkflowView as a cog."""
    logger.info("ParlayBetWorkflowView setup completed")
