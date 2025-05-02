# betting-bot/commands/betting.py

"""Main betting command for placing straight or parlay bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption
from discord.ext import commands
from discord.ui import View, Select, Button
import logging
from typing import Optional

from utils.errors import BetServiceError, ValidationError
from commands.straight_betting import StraightBetWorkflowView
from commands.parlay_betting import ParlayBetWorkflowView

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
        bet_type = self.values[0]
        logger.debug(f"Bet Type selected: {bet_type}")
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.start_bet_workflow(interaction, bet_type)

class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.red,
            label="Cancel",
            custom_id=f"cancel_bet_type_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug("Cancel button clicked in bet type selection")
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="Bet workflow cancelled.",
            view=None
        )
        self.parent_view.stop()

class BetTypeView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600)
        self.original_interaction = interaction
        self.bot = bot
        self.message: Optional[discord.WebhookMessage | discord.InteractionMessage] = None
        self.add_item(BetTypeSelect(self))
        self.add_item(CancelButton(self))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message(
                "You cannot interact with this bet placement.",
                ephemeral=True
            )
            return False
        return True

    async def start_bet_workflow(self, interaction: Interaction, bet_type: str):
        logger.debug(f"Starting {bet_type} bet workflow")
        try:
            if bet_type == "straight":
                view = StraightBetWorkflowView(self.original_interaction, self.bot)
            else:  # parlay
                view = ParlayBetWorkflowView(self.original_interaction, self.bot)
            await view.start_flow()
        except discord.HTTPException as e:
            logger.error(f"Failed to start {bet_type} bet workflow: {e}")
            await interaction.followup.send(
                f"❌ Failed to start {bet_type} bet workflow. Please try again.",
                ephemeral=True
            )
        finally:
            self.stop()

class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bet", description="Place a new bet (straight or parlay) through a guided workflow.")
    async def bet_command(self, interaction: Interaction):
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
            view = BetTypeView(interaction, self.bot)
            view.message = await interaction.followup.send(
                "Starting bet placement: Please select bet type...", view=view, ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Error initiating bet command: {e}")
            error_message = "❌ An error occurred while starting the betting workflow."
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(BettingCog(bot))
    logger.info("BettingCog loaded")
