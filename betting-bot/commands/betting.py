"""Betting command for placing bets."""

import discord
from discord import app_commands, ButtonStyle
import logging
from typing import Optional, List, Dict
from datetime import datetime
import aiosqlite
from services.bet_service import BetService
from discord.ui import View, Select, Modal, TextInput, Button

logger = logging.getLogger(__name__)

class BetTypeSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Moneyline", value="moneyline"),
            discord.SelectOption(label="Spread", value="spread"),
            discord.SelectOption(label="Total", value="total")
        ]
        super().__init__(placeholder="Select Bet Type", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.bet_type = self.values[0]
        await interaction.response.defer()
        self.view.stop()

class LeagueSelect(Select):
    def __init__(self, leagues: List[str]):
        options = [
            discord.SelectOption(label=league, value=league)
            for league in leagues
        ]
        options.append(discord.SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select League", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_league = self.values[0]
        await interaction.response.defer()
        self.view.stop()

class GameSelect(Select):
    def __init__(self, games: List[Dict]):
        options = [
            discord.SelectOption(
                label=f"{game['home_team']} vs {game['away_team']}",
                value=str(game['game_id'])
            )
            for game in games
        ]
        options.append(discord.SelectOption(label="Other", value="Other"))
        super().__init__(placeholder="Select Game", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_game = self.values[0]
        await interaction.response.defer()
        self.view.stop()

class BetDetailsModal(Modal, title="Enter Bet Details"):
    line = TextInput(label="Line", placeholder="Enter line (e.g., -150)")
    odds = TextInput(label="Odds", placeholder="Enter odds (e.g., -150)")

    async def on_submit(self, interaction: discord.Interaction):
        self.view.bet_details = {
            "line": self.line.value,
            "odds": self.odds.value
        }
        await interaction.response.defer()
        self.view.stop()

class UnitsSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=str(i), value=str(i))
            for i in [1, 2, 3]
        ]
        super().__init__(placeholder="Select Units", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_units = int(self.values[0])
        await interaction.response.defer()
        self.view.stop()

class ChannelSelect(Select):
    def __init__(self, channels: List[discord.TextChannel]):
        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id)
            )
            for channel in channels
        ]
        super().__init__(placeholder="Select Channel", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_channel = int(self.values[0])
        await interaction.response.defer()
        self.view.stop()

async def bet(interaction: discord.Interaction):
    """Place a new bet."""
    try:
        # Check if user is authorized
        bet_service = BetService(interaction.client)
        if not await bet_service.is_user_authorized(interaction.guild_id, interaction.user.id):
            await interaction.response.send_message(
                "❌ You are not authorized to place bets. Please contact an admin.",
                ephemeral=True
            )
            return

        # Step 1: Bet Type Selection
        view = View()
        view.add_item(BetTypeSelect())
        await interaction.response.send_message(
            "Select Bet Type:",
            view=view,
            ephemeral=True
        )
        await view.wait()
        if not hasattr(view, 'bet_type'):
            return

        # Step 2: League Selection
        leagues = ["NBA", "NFL", "MLB", "NHL"]
        view = View()
        view.add_item(LeagueSelect(leagues))
        await interaction.followup.send(
            "Select League:",
            view=view,
            ephemeral=True
        )
        await view.wait()
        if not hasattr(view, 'selected_league'):
            return

        # Step 3: Game Selection
        view = View()
        view.add_item(GameSelect([]))  # Empty list since we don't have game service
        await interaction.followup.send(
            "Select Game:",
            view=view,
            ephemeral=True
        )
        await view.wait()
        if not hasattr(view, 'selected_game'):
            return

        # Step 4: Bet Details Entry
        view = View()
        modal = BetDetailsModal()
        view.add_item(modal)
        await interaction.followup.send(
            "Enter Bet Details:",
            view=view,
            ephemeral=True
        )
        await view.wait()
        if not hasattr(view, 'bet_details'):
            return

        # Step 5: Units Selection
        view = View()
        view.add_item(UnitsSelect())
        await interaction.followup.send(
            "Select Units:",
            view=view,
            ephemeral=True
        )
        await view.wait()
        if not hasattr(view, 'selected_units'):
            return

        # Step 6: Channel Selection
        channels = [ch for ch in interaction.guild.text_channels 
                   if ch.permissions_for(interaction.user).send_messages]
        view = View()
        view.add_item(ChannelSelect(channels))
        await interaction.followup.send(
            "Select Channel:",
            view=view,
            ephemeral=True
        )
        await view.wait()
        if not hasattr(view, 'selected_channel'):
            return

        # Create bet
        bet_id = await bet_service.create_bet(
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
            game_id=view.selected_game if hasattr(view, 'selected_game') else None,
            bet_type=view.bet_type,
            selection=view.bet_details['line'],
            units=view.selected_units,
            odds=float(view.bet_details['odds']),
            channel_id=view.selected_channel
        )

        await interaction.followup.send(
            f"✅ Bet placed successfully! Bet ID: {bet_id}",
            ephemeral=True
        )

    except Exception as e:
        logger.error(f"Error in bet command: {str(e)}")
        await interaction.followup.send(
            "❌ An error occurred while placing your bet.",
            ephemeral=True
        )

async def setup(tree: app_commands.CommandTree):
    """Add the betting command to the bot."""
    tree.add_command(
        app_commands.Command(
            name="bet",
            description="Place a new bet",
            callback=bet
        )
    ) 