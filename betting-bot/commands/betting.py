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
            modal = BetDetailsModal(line_type=line_type, is_manual=True)
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
            if isinstance(item, ManualEntryButton):
                item.disabled = True
        await interaction.response.edit_message(content="Bet workflow cancelled.", view=None)
        self.parent_view.stop()


class BetDetailsModal(Modal, title="Enter Bet Details"):
    def __init__(self, line_type: str, is_manual: bool = False):
        super().__init__(title="Enter Bet Details")
        self.line_type = line_type
        self.is_manual = is_manual
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
        self.units = TextInput(
            label="Units (e.g., 1, 1.5)",
            placeholder="Enter units to risk",
            required=True,
            max_length=5
        )
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
        self.add_item(self.units)

    async def on_submit(self, interaction: Interaction):
        logger.debug(f"BetDetailsModal submitted: line_type={self.line_type}, is_manual={self.is_manual}")
        line = self.line.value.strip()
        odds = self.odds.value.strip()
        units = self.units.value.strip()

        if not all([line, odds, units]):
            logger.warning("Modal submission failed: Missing required fields")
            await interaction.response.send_message("Please fill in all required fields.", ephemeral=True)
            return

        leg = {
            'line': line,
            'odds_str': odds,
            'units_str': units
        }
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
        self.view.current_step = 5
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
