# betting-bot/commands/betting.py

"""Main betting command for placing straight or parlay bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption
from discord.ext import commands
from discord.ui import View, Select, Button
import logging
from typing import Optional

from utils.errors import BetServiceError, ValidationError
try:
    from commands.straight_betting import StraightBetWorkflowView
    from commands.parlay_betting import ParlayBetWorkflowView
except ImportError as e:
    logging.error(f"Failed to import betting workflows: {e}")
    raise

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
        logger.debug(f"Bet Type selected by {interaction.user}: {self.values[0]}")
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True
        try:
            await interaction.response.edit_message(view=self.parent_view)
            await self.parent_view.start_bet_workflow(interaction, self.values[0])
        except Exception as e:
            logger.error(f"Error processing bet type selection: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Failed to process bet type selection: {str(e)}", ephemeral=True
            )

class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.red,
            label="Cancel",
            custom_id=f"cancel_bet_type_{parent_view.original_interaction.id}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(f"Cancel button clicked by {interaction.user} in bet type selection")
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True
        try:
            await interaction.response.edit_message(
                content="Bet workflow cancelled.",
                view=None
            )
        except Exception as e:
            logger.error(f"Error cancelling bet workflow: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ Failed to cancel bet workflow.", ephemeral=True
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
            logger.debug(f"Unauthorized interaction attempt by {interaction.user}")
            await interaction.response.send_message(
                "You cannot interact with this bet placement.",
                ephemeral=True
            )
            return False
        return True

    async def start_bet_workflow(self, interaction: Interaction, bet_type: str):
        logger.debug(f"Starting {bet_type} bet workflow for {interaction.user}")
        try:
            if bet_type == "straight":
                view = StraightBetWorkflowView(self.original_interaction, self.bot)
            else:  # parlay
                view = ParlayBetWorkflowView(self.original_interaction, self.bot)
            await view.start_flow()
        except Exception as e:
            logger.error(f"Failed to start {bet_type} bet workflow: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Failed to start {bet_type} bet workflow: {str(e)}. Please try again.",
                ephemeral=True
            )
        finally:
            self.stop()

class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("Initializing BettingCog")

    @app_commands.command(name="bet", description="Place a new bet (straight or parlay) through a guided workflow.")
    async def bet_command(self, interaction: discord.Interaction):
        logger.info(f"Bet command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            is_auth = True  # Replace with actual authorization check if needed
            if not is_auth:
                logger.warning(f"Unauthorized bet attempt by {interaction.user}")
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
            logger.debug("Bet type selection message sent")
        except Exception as e:
            logger.exception(f"Error initiating bet command for {interaction.user}: {e}")
            error_message = f"❌ An error occurred while starting the betting workflow: {str(e)}"
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(BettingCog(bot))
    logger.info("BettingCog setup completed")
