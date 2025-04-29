# betting-bot/commands/betting.py

"""Betting command for placing bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel
from discord.ext import commands # Import commands for Cog
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union
from datetime import datetime, timezone

# Use relative imports assuming commands/ is sibling to services/, utils/, etc.
try:
    # Import necessary services and errors
    # Services will be accessed via self.bot.<service_name>
    # from ..services.bet_service import BetService # Not needed if accessed via bot
    # from ..services.game_service import GameService # Not needed if accessed via bot
    from ..utils.errors import BetServiceError, ValidationError, GameNotFoundError # Add GameNotFoundError
    # Import config if needed for validation limits etc.
    # from ..config.settings import ALLOWED_LEAGUES, MIN_ODDS, MAX_ODDS, MIN_UNITS, MAX_UNITS
except ImportError:
    # Fallbacks
    from services.bet_service import BetService
    from services.game_service import GameService
    from utils.errors import BetServiceError, ValidationError, GameNotFoundError
    # from config.settings import ALLOWED_LEAGUES, MIN_ODDS, MAX_ODDS, MIN_UNITS, MAX_UNITS


logger = logging.getLogger(__name__)

# --- Define UI Components used by this command ---

# Define BetType Select (can be defined here or imported)
class BetTypeSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="Moneyline", value="moneyline", description="Bet on who will win"),
            SelectOption(label="Spread", value="spread", description="Bet on the margin of victory"),
            SelectOption(label="Total", value="total", description="Bet on the total score (Over/Under)")
            # Add more types like 'Parlay', 'Player Prop' if supported
        ]
        super().__init__(placeholder="Select Bet Type...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['bet_type'] = self.values[0]
        logger.debug(f"Bet Type selected: {self.values[0]}")
        await interaction.response.defer()
        # Disable this select and move to the next step
        self.disabled = True
        await self.parent_view.go_next(interaction)

# Define League Select
class LeagueSelect(Select):
    def __init__(self, parent_view, leagues: List[str]):
        self.parent_view = parent_view
        options = [SelectOption(label=league, value=league) for league in leagues]
        options.append(SelectOption(label="Other", value="Other")) # Allow manual entry
        super().__init__(placeholder="Select League...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['league'] = self.values[0]
        logger.debug(f"League selected: {self.values[0]}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

# Define Game Select
class GameSelect(Select):
     def __init__(self, parent_view, games: List[Dict]):
         self.parent_view = parent_view
         options = []
         # Limit number of options in select menu (max 25)
         for game in games[:24]: # Show max 24 games + Other
              # Ensure keys exist safely
              home = game.get('home_team_name', 'Unknown')
              away = game.get('away_team_name', 'Unknown')
              start_dt = game.get('start_time')
              time_str = start_dt.strftime('%H:%M %Z') if isinstance(start_dt, datetime) else 'Time N/A'
              label = f"{away} @ {home} ({time_str})"
              options.append(SelectOption(label=label[:100], value=str(game.get('id')))) # Use API game ID
         options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
         super().__init__(placeholder="Select Game (or Other)...", options=options, min_values=1, max_values=1)

     async def callback(self, interaction: Interaction):
         self.parent_view.bet_details['game_id'] = self.values[0]
         logger.debug(f"Game selected: {self.values[0]}")
         self.disabled = True
         await interaction.response.defer()
         await self.parent_view.go_next(interaction)

# Define Modal for Manual Game Entry
class ManualGameModal(Modal, title="Enter Manual Game Details"):
    manual_selection = TextInput(
         label="Your Bet Selection",
         placeholder="e.g., Team Name -3.5, Player Over 10.5 Pts",
         required=True,
         max_length=150
    )
    game_description = TextInput(
         label="Game Description (Optional)",
         placeholder="e.g., Team A vs Team B - 7:00 PM",
         required=False,
         style=discord.TextStyle.short,
         max_length=100
    )

    async def on_submit(self, interaction: Interaction):
         # Store manual details; selection is the primary info here
         self.view.bet_details['selection'] = self.manual_selection.value
         self.view.bet_details['game_description'] = self.game_description.value # Optional context
         logger.debug(f"Manual game/selection entered: {self.manual_selection.value}")
         await interaction.response.defer() # Defer response since view handles next step
         # No need to call view.stop() here, the view's next step logic handles it


# Define Modal for Bet Details (Line/Odds/Units)
class BetDetailsModal(Modal, title="Enter Bet Details"):
    line_or_selection = TextInput(
        label="Selection / Line",
        placeholder="e.g., -7.5, Over 220.5, Team Moneyline",
        required=True,
        max_length=100
    )
    odds = TextInput(
        label="Odds (American)",
        placeholder="e.g., -110, +150, 210",
        required=True,
        max_length=10
    )
    units = TextInput(
        label="Units (e.g., 1, 1.5, 2, 2.5, 3)",
        placeholder="Enter units to risk (usually 1-3)",
        required=True,
        max_length=5
    )

    async def on_submit(self, interaction: Interaction):
        # Store details from modal
        self.view.bet_details['selection'] = self.line_or_selection.value
        self.view.bet_details['odds_str'] = self.odds.value
        self.view.bet_details['units_str'] = self.units.value
        logger.debug(f"Bet details entered: Line '{self.line_or_selection.value}', Odds '{self.odds.value}', Units '{self.units.value}'")
        await interaction.response.defer() # Defer response, view handles next step


# Define Channel Select
class ChannelSelect(Select):
    def __init__(self, parent_view, channels: List[TextChannel]):
        self.parent_view = parent_view
        options = [
            SelectOption(label=f"#{channel.name}", value=str(channel.id))
            for channel in channels[:25] # Limit to 25 options
        ]
        super().__init__(placeholder="Select Channel to Post Bet...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['channel_id'] = int(self.values[0])
        logger.debug(f"Channel selected: {self.values[0]}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)


# Define the main View managing the betting flow
class BetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600) # 10 minute timeout for the whole flow
        self.interaction = interaction # Original interaction
        self.bot = bot
        # Access services via bot instance
        self.bet_service: BetService = bot.bet_service
        self.game_service: GameService = bot.game_service
        self.current_step = 0
        self.bet_details = {} # Dictionary to store collected data
        self.message: Optional[discord.WebhookMessage] = None # To edit the interaction message

    async def start_flow(self):
        """Start the first step"""
        await self.go_next(self.interaction)

    async def go_next(self, interaction: Interaction):
        """Progress to the next step in the betting workflow."""
        self.clear_items() # Clear previous components
        self.current_step += 1
        step_content = f"**Step {self.current_step}**"
        edit_func = interaction.edit_original_response # Function to edit the message

        try:
            if self.current_step == 1: # Bet Type
                self.add_item(BetTypeSelect(self))
                await edit_func(content=f"{step_content}: Select Bet Type", view=self)

            elif self.current_step == 2: # League
                # Fetch allowed leagues (example, replace with actual logic/config)
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis"]
                self.add_item(LeagueSelect(self, allowed_leagues))
                await edit_func(content=f"{step_content}: Select League", view=self)

            elif self.current_step == 3: # Game
                league = self.bet_details.get('league')
                if league and league != "Other":
                    # Fetch upcoming games for the selected league
                    # Use GameService (accessed via self.bot)
                    upcoming_games = await self.game_service.get_upcoming_games(interaction.guild_id, hours=48) # Get games for next 48h
                    # Filter by selected league (case-insensitive)
                    league_games = [g for g in upcoming_games if g.get('league_name', '').lower() == league.lower() or str(g.get('league_id')) == league]
                    if league_games:
                         self.add_item(GameSelect(self, league_games))
                         await edit_func(content=f"{step_content}: Select Game for {league} (or Other)", view=self)
                    else:
                         logger.warning(f"No upcoming games found for league {league}. Proceeding to manual entry.")
                         # Skip game select, go directly to manual modal in next step
                         await self.go_next(interaction)
                else:
                    # If league is "Other" or not found, go straight to manual entry
                    await self.go_next(interaction)

            elif self.current_step == 4: # Bet Details (or Manual Game)
                game_id = self.bet_details.get('game_id')
                if game_id == "Other" or 'game_id' not in self.bet_details:
                     # Show manual game modal
                     modal = ManualGameModal()
                     modal.view = self # Link modal back to the view
                     await interaction.response.send_modal(modal)
                     # Wait for modal submission - timeout handled by main view timeout
                     # Submission callback in modal will store details and call go_next
                else:
                     # Show regular bet details modal
                     modal = BetDetailsModal()
                     modal.view = self # Link modal back to the view
                     await interaction.response.send_modal(modal)
                     # Wait for modal submission

            elif self.current_step == 5: # Channel Selection
                 # Get valid text channels where user can send messages
                 valid_channels = [
                      ch for ch in interaction.guild.text_channels
                      if ch.permissions_for(interaction.user).send_messages
                 ]
                 if not valid_channels:
                      await edit_func(content="Error: No text channels found where you can post.", view=None)
                      self.stop()
                      return
                 self.add_item(ChannelSelect(self, valid_channels))
                 await edit_func(content=f"{step_content}: Select Channel to Post Bet", view=self)

            elif self.current_step == 6: # Confirmation
                 # Validate inputs (odds, units) before showing confirmation
                 try:
                      odds_str = self.bet_details.get('odds_str', '')
                      units_str = self.bet_details.get('units_str', '')
                      self.bet_details['odds'] = float(odds_str) # Convert odds
                      self.bet_details['units'] = float(units_str) # Convert units (allow float?)

                      # Add validation for odds/units range if needed
                      # from config.settings import MIN_ODDS, MAX_ODDS, MIN_UNITS, MAX_UNITS
                      # if not (MIN_ODDS <= self.bet_details['odds'] <= MAX_ODDS): raise ValueError("Invalid Odds")
                      # if not (MIN_UNITS <= self.bet_details['units'] <= MAX_UNITS): raise ValueError("Invalid Units")

                 except ValueError as ve:
                      logger.error(f"Invalid bet input: Odds='{odds_str}', Units='{units_str}'. Error: {ve}")
                      await edit_func(content=f"❌ Error: Invalid input for Odds or Units. Please use numbers (e.g., -110, +150 for odds; 1, 1.5, 2 for units).", view=None)
                      self.stop()
                      return

                 # Display confirmation embed
                 embed = self.create_confirmation_embed()
                 self.add_item(ConfirmButton(self))
                 self.add_item(CancelButton(self))
                 await edit_func(content=f"**Step {self.current_step}**: Please Confirm Your Bet", embed=embed, view=self)

            else: # Should not happen
                 self.stop()

        except Exception as e:
             logger.exception(f"Error in bet workflow step {self.current_step}: {e}")
             await edit_func(content="An unexpected error occurred. Please try again.", view=None)
             self.stop()

    def create_confirmation_embed(self) -> discord.Embed:
        """Creates the confirmation embed."""
        details = self.bet_details
        embed = discord.Embed(title="Bet Confirmation", color=discord.Color.blue())
        embed.add_field(name="Type", value=details.get('bet_type', 'N/A'), inline=True)
        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)

        game_info = "Manual Entry"
        if details.get('game_id') and details['game_id'] != 'Other':
             game_info = f"Game ID: {details['game_id']}" # TODO: Fetch game name here if possible
        elif details.get('game_description'):
             game_info = details['game_description']
        embed.add_field(name="Game", value=game_info, inline=True)

        embed.add_field(name="Selection", value=f"`{details.get('selection', 'N/A')}`", inline=False)
        embed.add_field(name="Odds", value=f"{details.get('odds', 0.0):+}", inline=True) # Show sign for odds
        embed.add_field(name="Units", value=str(details.get('units', 0.0)), inline=True)

        channel_id = details.get('channel_id')
        channel = self.bot.get_channel(channel_id) if channel_id else None
        channel_mention = channel.mention if channel else "Invalid Channel"
        embed.add_field(name="Post Channel", value=channel_mention, inline=True)

        # Potential payout calculation (example for American odds)
        units = details.get('units', 0.0)
        odds = details.get('odds', 0.0)
        potential_profit = 0.0
        if odds > 0:
            potential_profit = units * (odds / 100.0)
        elif odds < 0:
            potential_profit = units * (100.0 / abs(odds))
        potential_payout = units + potential_profit
        embed.add_field(name="To Win (Profit)", value=f"{potential_profit:.2f} units", inline=True)
        embed.add_field(name="Payout (Risk+Win)", value=f"{potential_payout:.2f} units", inline=True)


        embed.set_footer(text="Confirm to place and post the bet.")
        return embed


    async def submit_bet(self, interaction: Interaction):
        """Submits the bet to the BetService."""
        details = self.bet_details
        try:
            # Call BetService to create the bet
            bet_id = await self.bet_service.create_bet(
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
                game_id=details.get('game_id'),
                bet_type=details.get('bet_type'),
                selection=details.get('selection'),
                units=details.get('units'),
                odds=details.get('odds'),
                channel_id=details.get('channel_id'),
                # message_id=self.message.id if self.message else None # Pass message ID for reaction tracking
            )

            # Post the bet embed to the selected channel
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None

            if post_channel and isinstance(post_channel, TextChannel):
                final_embed = self.create_final_bet_embed(bet_id)
                # Add reaction buttons for resolution
                # Using custom IDs requires the View to persist or storing state elsewhere
                view = BetResolutionView(bet_id) # Simple view example
                sent_message = await post_channel.send(embed=final_embed, view=view)
                # Store message_id for reaction tracking in BetService
                self.bet_service.pending_reactions[sent_message.id] = {
                     'bet_id': bet_id,
                     'user_id': interaction.user.id,
                     'guild_id': interaction.guild_id,
                     'channel_id': post_channel_id,
                     # Add other details if needed for notifications
                     'selection': details.get('selection'),
                     'units': details.get('units'),
                     'odds': details.get('odds'),
                     'league': details.get('league'),
                     'bet_type': details.get('bet_type'),
                 }
                logger.debug(f"Tracking reactions for posted bet message {sent_message.id}")

                # Confirm success to user
                await interaction.edit_original_response(content=f"✅ Bet placed successfully! (ID: `{bet_id}`). Posted to {post_channel.mention}.", embed=None, view=None)

            else:
                 logger.error(f"Could not find channel {post_channel_id} to post bet {bet_id}.")
                 await interaction.edit_original_response(content=f"✅ Bet placed (ID: `{bet_id}`), but failed to post to the selected channel.", embed=None, view=None)

        except (ValidationError, BetServiceError) as e:
            logger.error(f"Error submitting bet: {e}")
            await interaction.edit_original_response(content=f"❌ Error placing bet: {e}", embed=None, view=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting bet: {e}")
            await interaction.edit_original_response(content="❌ An unexpected error occurred while placing the bet.", embed=None, view=None)
        finally:
            self.stop() # Stop the view after completion or error


    def create_final_bet_embed(self, bet_id: int) -> discord.Embed:
        """Creates the embed to be posted in the selected channel."""
        details = self.bet_details
        # Fetch user object to get display name/avatar
        user = self.interaction.user

        embed = discord.Embed(
            title=f"{details.get('bet_type', 'Bet')}: {details.get('selection', 'N/A')}",
            color=discord.Color.gold() # Or based on team/capper color?
        )
        if user.display_avatar:
             embed.set_thumbnail(url=user.display_avatar.url)

        embed.set_author(name=f"{user.display_name}'s Bet", icon_url=user.display_avatar.url if user.display_avatar else None)

        game_info = "Manual Entry"
        if details.get('game_id') and details['game_id'] != 'Other':
             game_info = f"Game ID: {details['game_id']}" # TODO: Enhance with game name
        elif details.get('game_description'):
             game_info = details['game_description']

        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)
        embed.add_field(name="Game", value=game_info, inline=True)
        embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer

        embed.add_field(name="Odds", value=f"{details.get('odds', 0.0):+}", inline=True) # Show sign
        embed.add_field(name="Units", value=f"{details.get('units', 0.0):.1f}u", inline=True) # Show units with 'u'

        # Potential Payout Calculation (copied from confirmation)
        units = details.get('units', 0.0)
        odds = details.get('odds', 0.0)
        potential_profit = 0.0
        if odds > 0: potential_profit = units * (odds / 100.0)
        elif odds < 0: potential_profit = units * (100.0 / abs(odds))
        potential_payout = units + potential_profit

        embed.add_field(name="To Win", value=f"{potential_profit:.2f}u", inline=True)

        embed.set_footer(text=f"Bet ID: {bet_id} | Status: Pending")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

# Define Confirmation Buttons
class ConfirmButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.green, label="Confirm & Post", custom_id=f"confirm_bet_{parent_view.interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        # Disable buttons
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        await interaction.response.edit_message(view=self.parent_view) # Update message to show disabled buttons
        # Proceed to submit
        await self.parent_view.submit_bet(interaction)

class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.red, label="Cancel", custom_id=f"cancel_bet_{parent_view.interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        # Disable buttons and inform user
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        await interaction.response.edit_message(content="Bet cancelled.", embed=None, view=self.parent_view)
        self.parent_view.stop() # Stop the view

# Simple View for adding resolution reactions (could be more complex)
class BetResolutionView(View):
     def __init__(self, bet_id: int):
          super().__init__(timeout=None) # Persist indefinitely
          self.bet_id = bet_id
          # Note: Buttons here won't directly trigger resolution logic in the service
          # They act more as hints. The reaction handling in BetService does the work.
          # You could add buttons that just add the reaction for the user, but it's optional.

     # Example: Add buttons that simply add the reaction when clicked
     @discord.ui.button(label="Win", style=discord.ButtonStyle.green, emoji="✅", custom_id=f"bet_win_{bet_id}")
     async def win_button(self, interaction: Interaction, button: Button):
         # Check if reactor is authorized (e.g., original better or admin)
         # bet_info = interaction.client.bet_service.pending_reactions.get(interaction.message.id) # Get info if needed
         # if bet_info and interaction.user.id == bet_info['user_id']:
         try:
              await interaction.message.add_reaction("✅")
              await interaction.response.send_message("Marked as Won (Reaction Added).", ephemeral=True)
         except discord.Forbidden:
              await interaction.response.send_message("I don't have permission to add reactions.", ephemeral=True)
         # else: await interaction.response.send_message("Only the capper can mark this.", ephemeral=True)


     @discord.ui.button(label="Loss", style=discord.ButtonStyle.red, emoji="❌", custom_id=f"bet_loss_{bet_id}")
     async def loss_button(self, interaction: Interaction, button: Button):
         try:
              await interaction.message.add_reaction("❌")
              await interaction.response.send_message("Marked as Loss (Reaction Added).", ephemeral=True)
         except discord.Forbidden:
              await interaction.response.send_message("I don't have permission to add reactions.", ephemeral=True)

     @discord.ui.button(label="Push", style=discord.ButtonStyle.grey, emoji="🅿️", custom_id=f"bet_push_{bet_id}")
     async def push_button(self, interaction: Interaction, button: Button):
         try:
              await interaction.message.add_reaction("🅿️") # Use a distinct push emoji
              await interaction.response.send_message("Marked as Push (Reaction Added).", ephemeral=True)
         except discord.Forbidden:
              await interaction.response.send_message("I don't have permission to add reactions.", ephemeral=True)

# --- Cog Definition ---
class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Access services via self.bot
        self.bet_service: BetService = bot.bet_service
        self.game_service: GameService = bot.game_service # If needed for game lookups

    @app_commands.command(name="bet", description="Place a new bet through a guided workflow.")
    # @app_commands.checks.has_role("YOUR_CAPPER_ROLE_NAME_OR_ID") # Add role check if needed
    async def bet(self, interaction: Interaction):
        """Starts the interactive betting workflow."""
        logger.info(f"Bet command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            # Check if user is authorized using BetService
            is_authorized = await self.bet_service.is_user_authorized(interaction.guild_id, interaction.user.id)
            if not is_authorized:
                await interaction.response.send_message(
                    "❌ You are not authorized to place bets. Please contact an admin.",
                    ephemeral=True
                )
                return

            # Start the interactive workflow view
            view = BetWorkflowView(interaction, self.bot)
            # Send the initial message (will be edited by the view)
            await interaction.response.send_message("Starting bet placement...", view=view, ephemeral=True)
            # The view will handle the rest of the interaction flow via go_next()
            # await view.start_flow() # View starts itself via button clicks/selects

        except Exception as e:
            logger.exception(f"Error initiating bet command for {interaction.user}: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while starting the bet command.", ephemeral=True)
            else:
                 await interaction.followup.send("❌ An error occurred while starting the bet command.", ephemeral=True)

    # Add other betting-related commands here if needed (e.g., view bets, cancel bet)

# The setup function for the extension
async def setup(bot: commands.Bot):
    await bot.add_cog(BettingCog(bot))
    logger.info("BettingCog loaded")
