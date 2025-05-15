# betting-bot/commands/betting.py

"""Main betting command for placing straight or parlay bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption
from discord.ext import commands
from discord.ui import View, Select, Button
import logging
from typing import Optional

# Import from same directory
from .straight_betting import StraightBetWorkflowView
from .parlay_betting import ParlayBetWorkflowView

logger = logging.getLogger(__name__)

# --- Authorization Check Function ---
async def is_allowed_command_channel(interaction: Interaction) -> bool:
    """Checks if the command is used in a configured command channel."""
    if not interaction.guild_id:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return False

    # Assuming bot.db_manager is accessible
    db_manager = interaction.client.db_manager # type: ignore
    if not db_manager:
        logger.error("Database manager not found on bot client for command channel check.")
        await interaction.response.send_message("Bot configuration error. Cannot verify command channel.", ephemeral=True)
        return False

    settings = await db_manager.fetch_one(
        "SELECT command_channel_1, command_channel_2 FROM guild_settings WHERE guild_id = %s",
        (interaction.guild_id,)
    )

    if not settings:
        await interaction.response.send_message(
            "Command channels are not configured for this server. Please ask an admin to set them up using `/setup`.",
            ephemeral=True
        )
        return False

    command_channel_1_id = settings.get('command_channel_1')
    command_channel_2_id = settings.get('command_channel_2')

    allowed_channel_ids = []
    if command_channel_1_id:
        allowed_channel_ids.append(int(command_channel_1_id))
    if command_channel_2_id:
        allowed_channel_ids.append(int(command_channel_2_id))

    if not allowed_channel_ids:
        await interaction.response.send_message(
            "No command channels are configured for betting. Please ask an admin to set them up.",
            ephemeral=True
        )
        return False

    if interaction.channel_id not in allowed_channel_ids:
        channel_mentions = []
        for ch_id in allowed_channel_ids:
            channel = interaction.guild.get_channel(ch_id)
            if channel:
                channel_mentions.append(channel.mention)
            else:
                channel_mentions.append(f"`Channel ID: {ch_id}` (not found)")
        
        await interaction.response.send_message(
            f"This command can only be used in the designated command channel(s): {', '.join(channel_mentions)}",
            ephemeral=True
        )
        return False
    
    return True

# --- UI Component Classes ---
class BetTypeSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(
                label="Straight",
                value="straight",
                description="Moneyline, over/under, or player prop",
            ),
            SelectOption(
                label="Parlay",
                value="parlay",
                description="Combine multiple bets",
            ),
        ]
        super().__init__(
            placeholder="Select Bet Type...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        logger.debug(
            f"Bet Type selected by {interaction.user} (ID: {interaction.user.id}): {self.values[0]} in guild {interaction.guild_id}"
        )
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True
        try:
            # Edit the current message (BetTypeView's message) to reflect the disabled state
            await interaction.response.edit_message(view=self.parent_view)
            logger.debug(f"Starting bet workflow for type: {self.values[0]}")
            # Pass the current interaction (from this Select menu) to start_bet_workflow
            await self.parent_view.start_bet_workflow(
                interaction, self.values[0]
            )
        except Exception as e:
            logger.error(
                f"Error processing bet type selection for user {interaction.user}: {e}",
                exc_info=True,
            )
            # Since we already responded with edit_message, use followup for error
            await interaction.followup.send(
                f"❌ Failed to process bet type selection: {str(e)}",
                ephemeral=True,
            )


class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(
            style=ButtonStyle.red,
            label="Cancel",
            custom_id=f"cancel_bet_type_{parent_view.original_interaction.id}",
        )
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        logger.debug(
            f"Cancel button clicked by {interaction.user} (ID: {interaction.user.id}) in bet type selection"
        )
        self.disabled = True
        for item in self.parent_view.children:
            item.disabled = True
        try:
            await interaction.response.edit_message(
                content="Bet workflow cancelled.", view=None
            )
        except Exception as e:
            logger.error(
                f"Error cancelling bet workflow for user {interaction.user}: {e}",
                exc_info=True,
            )
            # await interaction.followup.send( # This would fail if edit_message failed due to original interaction being done
            #     "❌ Failed to cancel bet workflow.", ephemeral=True
            # )
        self.parent_view.stop()


class BetTypeView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600)
        self.original_interaction = interaction  # This is the /bet command interaction
        self.bot = bot
        self.message: Optional[
            discord.WebhookMessage | discord.InteractionMessage
        ] = None
        self.add_item(BetTypeSelect(self))
        self.add_item(CancelButton(self))
        logger.debug(
            f"BetTypeView initialized for user {interaction.user} (ID: {interaction.user.id})"
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            logger.debug(
                f"Unauthorized interaction attempt by {interaction.user} (ID: {interaction.user.id})"
            )
            await interaction.response.send_message(
                "You cannot interact with this bet placement.", ephemeral=True
            )
            return False
        logger.debug(
            f"Interaction check passed for user {interaction.user} (ID: {interaction.user.id})"
        )
        return True

    async def start_bet_workflow(
        self, interaction_from_select: Interaction, bet_type: str
    ):
        # interaction_from_select is the Interaction from the BetTypeSelect callback
        logger.debug(
            f"Starting {bet_type} bet workflow for user {interaction_from_select.user} (ID: {interaction_from_select.user.id})"
        )
        try:
            if bet_type == "straight":
                logger.debug("Initializing StraightBetWorkflowView")
                view = StraightBetWorkflowView(
                    self.original_interaction, # Pass the original /bet command interaction
                    self.bot,
                    message_to_control=self.message, # Pass the message this view is controlling
                )
            else:  # parlay
                logger.debug("Initializing ParlayBetWorkflowView")
                view = ParlayBetWorkflowView(
                    self.original_interaction, # Pass the original /bet command interaction
                    self.bot,
                    message_to_control=self.message, # Pass the message this view is controlling
                )
            # Start the new view's flow, passing the component interaction that triggered it
            await view.start_flow(interaction_from_select)
            logger.debug(f"{bet_type} bet workflow started successfully")
        except Exception as e:
            logger.error(
                f"Failed to start {bet_type} bet workflow for user {interaction_from_select.user}: {e}",
                exc_info=True,
            )
            # Use followup on the component interaction as it was already responded to
            await interaction_from_select.followup.send(
                f"❌ Failed to start {bet_type} bet workflow: {str(e)}. Please try again.",
                ephemeral=True,
            )
        finally:
            # Stop BetTypeView as its job is done.
            # StraightBetWorkflowView or ParlayBetWorkflowView will manage the message now.
            self.stop()


class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("Initializing BettingCog")

    @app_commands.command(
        name="bet",
        description="Place a new bet (straight or parlay) through a guided workflow.",
    )
    @app_commands.check(is_allowed_command_channel)
    async def bet_command(self, interaction: discord.Interaction):
        logger.info(
            f"Bet command initiated by {interaction.user} (ID: {interaction.user.id}) in guild {interaction.guild_id}, channel {interaction.channel_id}"
        )
        try:
            # Authorization for placing bets (e.g., role-based) can be added here if needed
            # is_auth = True # Replace with actual authorization check
            # if not is_auth:
            #     logger.warning(
            #         f"Unauthorized bet attempt by {interaction.user} (ID: {interaction.user.id})"
            #     )
            #     await interaction.response.send_message(
            #         "❌ You are not authorized to place bets.", ephemeral=True
            #     )
            #     return
            
            logger.debug("Deferring response for bet command")
            # No need to defer if the check function already sends a response on failure.
            # If the check passes, we will send a message with the view.
            # await interaction.response.defer(ephemeral=True, thinking=True) # Removed defer here

            view = BetTypeView(interaction, self.bot)
            logger.debug("Sending bet type selection message")
            
            # Send the initial message. If is_allowed_command_channel failed, this won't execute.
            await interaction.response.send_message(
                "Starting bet placement: Please select bet type...",
                view=view,
                ephemeral=True,
            )
            view.message = await interaction.original_response() # Get the message we just sent
            logger.debug("Bet type selection message sent successfully")

        except app_commands.CheckFailure as e:
            logger.warning(f"Bet command check failed for {interaction.user.id} in channel {interaction.channel_id}: {e}")
            # The check function `is_allowed_command_channel` handles sending the response.
        except Exception as e:
            logger.exception(
                f"Error initiating bet command for user {interaction.user} (ID: {interaction.user.id}): {e}"
            )
            error_message = f"❌ An error occurred while starting the betting workflow: {str(e)}"
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                try:
                    await interaction.followup.send(error_message, ephemeral=True)
                except discord.HTTPException: # Fallback if followup fails
                    logger.error("Failed to send followup error message for bet command.")


async def setup(bot: commands.Bot):
    """Adds the betting cog to the bot."""
    try:
        cog = BettingCog(bot)
        await bot.add_cog(cog)
        logger.info("BettingCog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load BettingCog: {e}")
        raise
