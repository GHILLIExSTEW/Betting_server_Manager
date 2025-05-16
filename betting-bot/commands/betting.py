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
from config.leagues import LEAGUE_IDS 

logger = logging.getLogger(__name__)

# --- Authorization Check Function ---
async def is_allowed_command_channel(interaction: Interaction) -> bool:
    """Checks if the command is used in a configured command channel."""
    if not interaction.guild_id:
        if not interaction.response.is_done():
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        else:
            # This case is less likely for a primary command check but good for robustness
            try: await interaction.followup.send("This command must be used in a server.", ephemeral=True)
            except discord.HTTPException: pass # Ignore if followup fails (e.g. original interaction deleted)
        return False

    if not hasattr(interaction.client, 'db_manager') or not interaction.client.db_manager: # type: ignore
        logger.error("Database manager not found on bot client for command channel check.")
        msg = "Bot configuration error (DBM). Cannot verify command channel."
        if not interaction.response.is_done(): await interaction.response.send_message(msg, ephemeral=True)
        else: 
            try: await interaction.followup.send(msg, ephemeral=True)
            except discord.HTTPException: pass
        return False
    
    db_manager = interaction.client.db_manager # type: ignore

    settings = await db_manager.fetch_one(
        "SELECT command_channel_1, command_channel_2 FROM guild_settings WHERE guild_id = %s",
        (interaction.guild_id,)
    )

    if not settings:
        msg = "Command channels are not configured for this server. Please ask an admin to set them up using `/setup` or a relevant admin command."
        if not interaction.response.is_done(): await interaction.response.send_message(msg, ephemeral=True)
        else: 
            try: await interaction.followup.send(msg, ephemeral=True)
            except discord.HTTPException: pass
        return False

    command_channel_1_id = settings.get('command_channel_1')
    command_channel_2_id = settings.get('command_channel_2')

    allowed_channel_ids = []
    if command_channel_1_id:
        try: allowed_channel_ids.append(int(command_channel_1_id))
        except (ValueError, TypeError): logger.error(f"Invalid command_channel_1 ID in DB for guild {interaction.guild_id}: {command_channel_1_id}")
    if command_channel_2_id:
        try: allowed_channel_ids.append(int(command_channel_2_id))
        except (ValueError, TypeError): logger.error(f"Invalid command_channel_2 ID in DB for guild {interaction.guild_id}: {command_channel_2_id}")

    if not allowed_channel_ids:
        msg = "No command channels are configured for betting. Please ask an admin to set them up."
        if not interaction.response.is_done(): await interaction.response.send_message(msg, ephemeral=True)
        else: 
            try: await interaction.followup.send(msg, ephemeral=True)
            except discord.HTTPException: pass
        return False

    if interaction.channel_id not in allowed_channel_ids:
        channel_mentions = []
        guild = interaction.guild # Cache guild attribute
        if guild:
            for ch_id in allowed_channel_ids:
                channel = guild.get_channel(ch_id)
                if channel: channel_mentions.append(channel.mention)
                else: channel_mentions.append(f"`Channel ID: {ch_id}` (not found/accessible)")
        else: # Should not happen for a guild command
             channel_mentions = [f"`Channel ID: {ch_id}`" for ch_id in allowed_channel_ids]

        
        msg = f"This command can only be used in the designated command channel(s): {', '.join(channel_mentions) if channel_mentions else 'None Configured'}"
        if not interaction.response.is_done(): await interaction.response.send_message(msg, ephemeral=True)
        else: 
            try: await interaction.followup.send(msg, ephemeral=True)
            except discord.HTTPException: pass
        return False
    
    return True

# --- UI Component Classes ---
class BetTypeSelect(Select):
    def __init__(self, parent_view: 'BetTypeView'): # Added type hint for parent_view
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
            item.disabled = True # type: ignore
        try:
            await interaction.response.edit_message(view=self.parent_view)
            logger.debug(f"Starting bet workflow for type: {self.values[0]}")
            await self.parent_view.start_bet_workflow(
                interaction, self.values[0]
            )
        except Exception as e:
            logger.error(
                f"Error processing bet type selection for user {interaction.user}: {e}",
                exc_info=True,
            )
            try:
                await interaction.followup.send(
                    f"❌ Failed to process bet type selection: {str(e)}",
                    ephemeral=True,
                )
            except discord.HTTPException:
                 logger.error("Failed to send followup after bet type selection error.")


class CancelButton(Button):
    def __init__(self, parent_view: 'BetTypeView'): # Added type hint
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
            item.disabled = True # type: ignore
        try:
            await interaction.response.edit_message(
                content="Bet workflow cancelled.", view=None
            )
        except Exception as e:
            logger.error(
                f"Error cancelling bet workflow for user {interaction.user}: {e}",
                exc_info=True,
            )
        self.parent_view.stop()


class BetTypeView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600)
        self.original_interaction = interaction 
        self.bot = bot
        self.message: Optional[
            Union[discord.WebhookMessage, discord.InteractionMessage]
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
        logger.debug(
            f"Starting {bet_type} bet workflow for user {interaction_from_select.user} (ID: {interaction_from_select.user.id})"
        )
        try:
            if bet_type == "straight":
                logger.debug("Initializing StraightBetWorkflowView")
                view = StraightBetWorkflowView(
                    self.original_interaction, 
                    self.bot,
                    message_to_control=self.message, 
                )
                if not view.message: 
                    logger.error("StraightBetWorkflowView initiated without a message to control.")
                    await interaction_from_select.followup.send("Error: Could not initiate straight bet workflow (message context).", ephemeral=True)
                    self.stop()
                    return
                await view.start_flow(interaction_from_select) # Pass the component interaction
            else:  # parlay
                logger.debug("Initializing ParlayBetWorkflowView")
                view = ParlayBetWorkflowView( 
                    self.original_interaction, 
                    self.bot
                    # ParlayBetWorkflowView's start_flow will handle sending its own initial message
                    # using self.original_interaction (the /bet command interaction)
                )
                await view.start_flow() # Parlay's start_flow doesn't need interaction_from_select here

            logger.debug(f"{bet_type} bet workflow started successfully")
        except Exception as e:
            logger.error(
                f"Failed to start {bet_type} bet workflow for user {interaction_from_select.user}: {e}",
                exc_info=True,
            )
            try:
                await interaction_from_select.followup.send(
                    f"❌ Failed to start {bet_type} bet workflow: {str(e)}. Please try again.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                logger.error(f"Failed to send followup for {bet_type} workflow start error.")
        finally:
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
            f"/bet command initiated by {interaction.user} (ID: {interaction.user.id}) in guild {interaction.guild_id}, channel {interaction.channel_id}"
        )
        try:
            # The check is_allowed_command_channel runs before this.
            # If it fails, it sends a response and this function isn't called.
            view = BetTypeView(interaction, self.bot)
            
            # Send the initial response for the /bet command.
            # Since the check passed, we can proceed to send this message.
            await interaction.response.send_message(
                "Starting bet placement: Please select bet type...",
                view=view,
                ephemeral=True,
            )
            # Store the message object so the view can control it
            view.message = await interaction.original_response() 
            logger.debug(f"Bet type selection message sent successfully (ID: {view.message.id})")

        except app_commands.CheckFailure:
            # This block is hit if is_allowed_command_channel returns False AND
            # if, for some reason, it didn't send its own response (our current implementation does).
            # It's good for robustness.
            logger.warning(f"/bet command check failed for {interaction.user.id} in channel {interaction.channel_id}. The check function should have responded.")
            if not interaction.response.is_done():
                 await interaction.response.send_message("You cannot use this command in this channel.", ephemeral=True)
        except Exception as e:
            logger.exception(
                f"Error in /bet command for user {interaction.user} (ID: {interaction.user.id}): {e}"
            )
            error_message = f"❌ An error occurred while starting the betting workflow: {str(e)}"
            # Check if an initial response has been sent before trying to send/followup
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                try:
                    await interaction.followup.send(error_message, ephemeral=True)
                except discord.HTTPException: # Fallback if followup fails
                    logger.error("Failed to send followup error message for /bet command after initial response.")


async def setup(bot: commands.Bot):
    """Adds the betting cog to the bot."""
    try:
        cog = BettingCog(bot)
        await bot.add_cog(cog)
        logger.info("BettingCog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load BettingCog: {e}")
        raise
