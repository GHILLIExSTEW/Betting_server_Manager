import discord
from discord import app_commands
import logging
from typing import Optional, List, Dict
from datetime import datetime
import aiosqlite
from services.bet_service import BetService
from services.game_service import GameService
from discord.ui import View, Select, Modal, TextInput, Button, ButtonStyle

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

class OtherGameModal(Modal, title="Enter Game Details"):
    team = TextInput(label="Team", placeholder="Enter team name")
    opponent = TextInput(label="Opponent", placeholder="Enter opponent name")
    game_time = TextInput(label="Game Time", placeholder="Enter game time (e.g., 7:30 PM EST)")

    async def on_submit(self, interaction: discord.Interaction):
        self.view.game_details = {
            "team": self.team.value,
            "opponent": self.opponent.value,
            "game_time": self.game_time.value
        }
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

async def setup(tree: app_commands.CommandTree, bot):
    """Setup function for betting commands."""
    bet_service = BetService(bot)
    game_service = GameService(bot)
    
    @tree.command(
        name="bet",
        description="Start the bet placement flow"
    )
    async def bet(interaction: discord.Interaction):
        """Start the bet placement flow."""
        try:
            # Check if user is authorized to bet
            async with aiosqlite.connect('betting_bot/data/betting.db') as db:
                async with db.execute(
                    """
                    SELECT user_id 
                    FROM cappers 
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (interaction.guild_id, interaction.user.id)
                ) as cursor:
                    if not await cursor.fetchone():
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
            if view.selected_league != "Other":
                games = await game_service.get_league_games(interaction.guild_id, view.selected_league)
                view = View()
                view.add_item(GameSelect(games))
                await interaction.followup.send(
                    "Select Game:",
                    view=view,
                    ephemeral=True
                )
                await view.wait()
                if not hasattr(view, 'selected_game'):
                    return

                if view.selected_game == "Other":
                    view = View()
                    modal = OtherGameModal()
                    view.add_item(modal)
                    await interaction.followup.send(
                        "Enter Game Details:",
                        view=view,
                        ephemeral=True
                    )
                    await view.wait()
                    if not hasattr(view, 'game_details'):
                        return
            else:
                view = View()
                modal = OtherGameModal()
                view.add_item(modal)
                await interaction.followup.send(
                    "Enter Game Details:",
                    view=view,
                    ephemeral=True
                )
                await view.wait()
                if not hasattr(view, 'game_details'):
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

    @bet.error
    async def bet_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        logger.error(f"Error in bet command: {str(error)}")
        await interaction.response.send_message(
            "❌ An unexpected error occurred.",
            ephemeral=True
        ) 