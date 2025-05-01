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
    from ..services.bet_service import BetService # Not needed if accessed via bot
    from ..services.game_service import GameService # Not needed if accessed via bot
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
            SelectOption(label="Total", value="total", description="Bet on the total score (Over/Under)"),
            SelectOption(label="Parlay", value="parlay", description="Combine multiple bets") # Example: Add Parlay
            # Add more types like 'Player Prop' if supported
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
        options = [SelectOption(label=league, value=league) for league in leagues[:24]] # Limit options
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
              # Format time better, handle potential None
              if isinstance(start_dt, datetime):
                   # Convert to user's local time? Or keep UTC? Keeping UTC for now.
                   # time_str = discord.utils.format_dt(start_dt, style='t') # Example using format_dt
                   time_str = start_dt.strftime('%m/%d %H:%M %Z') # Basic format
              else:
                   time_str = 'Time N/A'

              label = f"{away} @ {home} ({time_str})"
              # Use API game ID from 'id' key, ensure it's a string for the value
              game_api_id = game.get('id')
              if game_api_id is None:
                   logger.warning(f"Game missing 'id' field: {game}")
                   continue # Skip games without an API ID

              options.append(SelectOption(label=label[:100], value=str(game_api_id)))
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
         # Tell the view to proceed
         await self.view.go_next(interaction)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in ManualGameModal: {error}", exc_info=True)
         # Use followup because original response was likely deferred
         if not interaction.response.is_done():
              await interaction.response.send_message('❌ An error occurred with the manual game modal.', ephemeral=True)
         else:
              await interaction.followup.send('❌ An error occurred with the manual game modal.', ephemeral=True)


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
        await self.view.go_next(interaction)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
         logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
         if not interaction.response.is_done():
              await interaction.response.send_message('❌ An error occurred with the bet details modal.', ephemeral=True)
         else:
              await interaction.followup.send('❌ An error occurred with the bet details modal.', ephemeral=True)


# Define Channel Select
class ChannelSelect(Select):
    def __init__(self, parent_view, channels: List[TextChannel]):
        self.parent_view = parent_view
        options = [
            SelectOption(label=f"#{channel.name}", value=str(channel.id))
            for channel in channels[:25] # Limit to 25 options
        ]
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


# Define the main View managing the betting flow
class BetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600) # 10 minute timeout for the whole flow
        self.original_interaction = interaction # Original interaction
        self.bot = bot
        # Access services via bot instance
        self.bet_service: BetService = bot.bet_service
        self.game_service: GameService = bot.game_service
        self.current_step = 0
        self.bet_details = {} # Dictionary to store collected data
        self.message: Optional[discord.WebhookMessage] = None # To store the message reference for editing

    async def start_flow(self):
        """Sends the initial message and starts the workflow."""
        # Send the initial ephemeral message (or edit if already deferred)
        self.message = await self.original_interaction.followup.send(
             "Starting bet placement...", view=self, ephemeral=True
        )
        await self.go_next(self.original_interaction) # Start step 1

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Ensure only the user who initiated the command can interact
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this bet placement.", ephemeral=True)
            return False
        return True

    async def edit_message(self, interaction: Interaction, content: Optional[str] = None, view: Optional[View] = None, embed: Optional[discord.Embed] = None):
         """Helper to edit the interaction's original response message."""
         # Use the original interaction's followup webhook to edit the message
         try:
              # If interaction is passed from a component callback, use its message attribute if available
              target_message = interaction.message or self.message
              if target_message:
                    await target_message.edit(content=content, embed=embed, view=view)
              else: # Fallback to editing original response if message ref is lost
                   await self.original_interaction.edit_original_response(content=content, embed=embed, view=view)
         except discord.NotFound:
              logger.warning(f"Failed to edit BetWorkflowView message (Interaction: {interaction.id}, Original: {self.original_interaction.id}). Message not found (deleted or timed out?).")
              self.stop() # Stop the view if the message is gone
         except discord.HTTPException as hte:
              logger.error(f"HTTP Error editing BetWorkflowView message: {hte.status} - {hte.text}")
              # Don't stop the view necessarily, maybe the next step can still work?
         except Exception as e:
              logger.exception(f"Unexpected error editing BetWorkflowView message: {e}")
              # Don't stop the view


    async def go_next(self, interaction: Interaction):
        """Progress to the next step in the betting workflow."""
        self.clear_items() # Clear previous components
        self.current_step += 1
        step_content = f"**Step {self.current_step}**"
        embed_to_send = None # Reset embed

        try:
            if self.current_step == 1: # Bet Type
                self.add_item(BetTypeSelect(self))
                step_content += ": Select Bet Type"

            elif self.current_step == 2: # League
                # Fetch allowed leagues dynamically or from config
                # Example static list:
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                self.add_item(LeagueSelect(self, allowed_leagues))
                step_content += ": Select League"

            elif self.current_step == 3: # Game
                league = self.bet_details.get('league')
                if league and league != "Other":
                    # Use GameService (accessed via self.bot)
                    # Determine sport based on league (needs mapping)
                    # TODO: Implement a robust league -> sport mapping (e.g., in GameService or utils)
                    sport = None # Placeholder
                    if league in ["NFL", "NCAAF"]: sport = "american-football"
                    elif league in ["NBA", "NCAAB"]: sport = "basketball"
                    elif league == "MLB": sport = "baseball"
                    elif league == "NHL": sport = "hockey"
                    elif league == "Soccer": sport = "soccer" # Or use specific league name like 'premier-league'
                    elif league == "Tennis": sport = "tennis"
                    # Add more mappings

                    if sport and hasattr(self.game_service, 'get_upcoming_games'):
                        # Assuming get_upcoming_games fetches from DB based on GameService logic
                        # It might internally call API/cache if DB is empty or outdated
                        upcoming_games = await self.game_service.get_upcoming_games(interaction.guild_id, hours=72) # Fetch next 72h from DB
                        # Filter games by the selected league name (case-insensitive) or ID
                        league_games = [g for g in upcoming_games if str(g.get('league_id')) == league or g.get('league_name','').lower() == league.lower()]

                        if league_games:
                            self.add_item(GameSelect(self, league_games))
                            step_content += f": Select Game for {league} (or Other)"
                        else:
                            logger.warning(f"No upcoming games found in DB for league {league}. Proceeding to manual entry.")
                            await self.go_next(interaction) # Skip game select step
                            return # Important: return to prevent editing message below for this skipped step
                    else:
                         logger.warning(f"Sport not determined for league {league} or GameService unavailable. Proceeding to manual entry.")
                         await self.go_next(interaction) # Skip game select step
                         return
                else:
                    # If league is "Other" or not found, go straight to manual entry
                    # Step 4 handles the modal logic
                    await self.go_next(interaction)
                    return

            elif self.current_step == 4: # Bet Details (Selection/Line, Odds, Units) OR Manual Game Entry
                game_id = self.bet_details.get('game_id')
                if game_id == "Other" or 'game_id' not in self.bet_details:
                     # Show manual game modal
                     # Use interaction.response.send_modal for the *first* modal in an interaction
                     # Subsequent modals might need followup? Test this.
                     # Send modal needs the original interaction context usually.
                     modal = ManualGameModal()
                     modal.view = self # Link modal back to the view
                     await interaction.response.send_modal(modal)
                     # We don't edit the message here; the modal callback will call go_next
                     return # Stop processing this step until modal is submitted
                else:
                     # Show regular bet details modal
                     modal = BetDetailsModal()
                     modal.view = self
                     await interaction.response.send_modal(modal)
                     return # Stop processing this step until modal is submitted

            elif self.current_step == 5: # Channel Selection
                 # Get valid text channels where user can send messages
                 valid_channels = sorted(
                      [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.user).send_messages],
                      key=lambda c: c.position
                 )
                 if not valid_channels:
                      await self.edit_message(interaction, content="Error: No text channels found where you can post.", view=None)
                      self.stop()
                      return
                 self.add_item(ChannelSelect(self, valid_channels))
                 step_content += ": Select Channel to Post Bet"

            elif self.current_step == 6: # Confirmation
                 # Validate inputs (odds, units) before showing confirmation
                 try:
                      odds_str = self.bet_details.get('odds_str', '').replace('+','').strip() # Remove + sign, strip whitespace
                      units_str = self.bet_details.get('units_str', '').lower().replace('u','').strip() # Remove 'u', strip whitespace

                      # --- Odds Validation ---
                      try:
                           odds_val = int(odds_str) # American odds are usually integers
                           # Add range check if needed (e.g., from config)
                           MIN_ODDS, MAX_ODDS = -10000, 10000 # Example range
                           if not (MIN_ODDS <= odds_val <= MAX_ODDS):
                                raise ValueError(f"Odds ({odds_val}) out of range [{MIN_ODDS}, {MAX_ODDS}]")
                           # Cannot be exactly 0, usually not between -100 and 100 (excl.)
                           if -100 < odds_val < 100:
                                raise ValueError("Odds cannot be between -99 and 99.")
                           self.bet_details['odds'] = float(odds_val) # Store as float
                      except ValueError as e:
                           logger.warning(f"Invalid odds format '{odds_str}': {e}")
                           raise ValueError(f"Invalid Odds format: '{odds_str}'. Use American odds (e.g., -110, +150).") from e

                      # --- Units Validation ---
                      try:
                           units_val = float(units_str)
                           # Add range check (e.g., from config)
                           MIN_UNITS, MAX_UNITS = 0.1, 10.0 # Example range (allow fractional)
                           if not (MIN_UNITS <= units_val <= MAX_UNITS):
                               raise ValueError(f"Units ({units_val}) out of range [{MIN_UNITS}, {MAX_UNITS}]")
                           self.bet_details['units'] = units_val # Store as float
                      except ValueError as e:
                           logger.warning(f"Invalid units format '{units_str}': {e}")
                           raise ValueError(f"Invalid Units format: '{units_str}'. Use a number (e.g., 1, 1.5, 2).") from e

                 except ValueError as ve: # Catch validation errors
                      logger.error(f"Bet input validation failed: {ve}")
                      await self.edit_message(interaction, content=f"❌ Error: {ve} Please start over.", view=None)
                      self.stop()
                      return

                 # Display confirmation embed
                 embed_to_send = self.create_confirmation_embed()
                 self.add_item(ConfirmButton(self))
                 self.add_item(CancelButton(self))
                 step_content = f"**Step {self.current_step}**: Please Confirm Your Bet" # Override step content

            else: # Should not happen
                 logger.error(f"BetWorkflowView reached unexpected step: {self.current_step}")
                 self.stop()
                 return

            # Edit the message for the current step (unless handled by modal)
            await self.edit_message(interaction, content=step_content, view=self, embed=embed_to_send)

        except Exception as e:
             logger.exception(f"Error in bet workflow step {self.current_step}: {e}")
             try:
                  await self.edit_message(interaction, content="An unexpected error occurred. Please try again.", view=None, embed=None)
             except Exception: # Ignore errors during error reporting
                  pass
             self.stop()

    def create_confirmation_embed(self) -> discord.Embed:
        """Creates the confirmation embed."""
        details = self.bet_details
        embed = discord.Embed(title="📊 Bet Confirmation", color=discord.Color.blue())
        embed.add_field(name="Type", value=details.get('bet_type', 'N/A').title(), inline=True)
        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)

        game_info = "Manual Entry"
        game_id = details.get('game_id')
        if game_id and game_id != 'Other':
             # Try to fetch game details from GameService for a better display
             # This might require an async helper or making GameService accessible here
             # For now, just show ID
             game_info = f"Game ID: {game_id}"
             # Example async fetch (would need modification):
             # game_data = await self.game_service.get_game(int(game_id)) # Fetch from DB
             # if game_data: game_info = f"{game_data.get('away_team_name')} @ {game_data.get('home_team_name')}"
        elif details.get('game_description'):
             game_info = details['game_description'][:100] # Limit length
        embed.add_field(name="Game", value=game_info, inline=True)

        selection = details.get('selection', 'N/A')
        # Ensure selection fits in embed field value (1024 chars)
        embed.add_field(name="Selection", value=f"```{selection[:1000]}```", inline=False)
        odds_value = details.get('odds', 0.0)
        embed.add_field(name="Odds", value=f"{odds_value:+}", inline=True) # Show sign for odds
        units_value = details.get('units', 0.0)
        embed.add_field(name="Units", value=f"{units_value:.2f}u", inline=True)

        channel_id = details.get('channel_id')
        channel = self.bot.get_channel(channel_id) if channel_id else None
        channel_mention = channel.mention if channel else "Invalid Channel"
        embed.add_field(name="Post Channel", value=channel_mention, inline=True)

        # Potential payout calculation (ensure units/odds are floats)
        units = float(details.get('units', 0.0))
        odds = float(details.get('odds', 0.0))
        potential_profit = 0.0
        if units > 0: # Only calculate if units are positive
            if odds > 0:
                potential_profit = units * (odds / 100.0)
            elif odds < 0:
                potential_profit = units * (100.0 / abs(odds))
        potential_payout = units + potential_profit
        embed.add_field(name="To Win", value=f"{potential_profit:.2f}u", inline=True)
        embed.add_field(name="Payout", value=f"{potential_payout:.2f}u", inline=True)

        embed.set_footer(text="Confirm to place and post the bet.")
        return embed


    async def submit_bet(self, interaction: Interaction):
        """Submits the bet to the BetService."""
        details = self.bet_details
        # Edit message to show processing state
        await self.edit_message(interaction, content="Processing and posting bet...", view=None, embed=None)
        sent_message = None # Define outside try block

        try:
            # Call BetService to create the bet
            bet_serial = await self.bet_service.create_bet(
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
                game_id=details.get('game_id'), # Already processed in validation step
                bet_type=details.get('bet_type'),
                selection=details.get('selection'),
                units=details.get('units'), # Already validated float
                odds=details.get('odds'), # Already validated float
                channel_id=details.get('channel_id'),
                # message_id needs to be set *after* the message is sent
            )

            # Post the bet embed to the selected channel
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None

            if post_channel and isinstance(post_channel, TextChannel):
                final_embed = self.create_final_bet_embed(bet_serial)
                # Add reaction buttons for resolution
                # Custom IDs are now static
                view = BetResolutionView(bet_serial) # Pass bet_serial if needed by view logic later
                sent_message = await post_channel.send(embed=final_embed, view=view)

                # Store message_id -> bet_serial mapping for reaction tracking in BetService
                if sent_message:
                    self.bet_service.pending_reactions[sent_message.id] = {
                         'bet_serial': bet_serial,
                         'user_id': interaction.user.id,
                         'guild_id': interaction.guild_id,
                         'channel_id': post_channel_id,
                         'selection': details.get('selection'),
                         'units': details.get('units'),
                         'odds': details.get('odds'),
                         'league': details.get('league'),
                         'bet_type': details.get('bet_type'),
                     }
                    logger.debug(f"Tracking reactions for posted bet message {sent_message.id} (Bet Serial: {bet_serial})")

                # Confirm success to user (edit original ephemeral message)
                success_message = f"✅ Bet placed successfully! (ID: `{bet_serial}`). Posted to {post_channel.mention}."
                await self.edit_message(interaction, content=success_message, view=None, embed=None)

            else:
                 logger.error(f"Could not find channel {post_channel_id} or not a TextChannel to post bet {bet_serial}.")
                 # Bet was created but not posted
                 failure_message = f"⚠️ Bet placed (ID: `{bet_serial}`), but **failed to post** to channel ID {post_channel_id}. Please check permissions or channel existence."
                 await self.edit_message(interaction, content=failure_message, view=None, embed=None)

        except (ValidationError, BetServiceError) as e:
            logger.error(f"Error submitting bet: {e}")
            error_message = f"❌ Error placing bet: {e}"
            await self.edit_message(interaction, content=error_message, view=None, embed=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting bet: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred while placing the bet.", view=None, embed=None)
        finally:
            self.stop() # Stop the view after completion or error


    def create_final_bet_embed(self, bet_serial: int) -> discord.Embed:
        """Creates the embed to be posted in the selected channel."""
        details = self.bet_details
        user = self.original_interaction.user # Use original interaction user

        # Determine Embed Title based on Bet Type
        bet_type_str = details.get('bet_type', 'Bet').title()
        selection_str = details.get('selection', 'N/A')
        embed_title = f"{bet_type_str}: {selection_str}"
        # Check for multi-team parlay based on user's guideline
        # This assumes 'selection' contains multiple lines/teams for a parlay
        # A more robust check might involve looking at bet_type == 'parlay' AND multiple legs stored elsewhere
        is_multi_team_parlay = False
        if bet_type_str == 'Parlay' and isinstance(selection_str, str) and '\n' in selection_str: # Simple check for multi-line selection
            is_multi_team_parlay = True

        # [2025-04-19] Apply user guideline for embed title
        if is_multi_team_parlay:
            embed_title = "Multi-Team Parlay Bet"
            # Optionally include the legs in description or field if title is generic
            # description=f"```{selection_str[:1000]}```" # Example description for legs

        embed = discord.Embed(
            title=embed_title,
            color=discord.Color.gold(), # Default color
            # description=description if is_multi_team_parlay else None # Add description if needed
        )

        # Add capper info
        embed.set_author(name=f"{user.display_name}'s Pick", icon_url=user.display_avatar.url if user.display_avatar else None)
        # Add thumbnail if you have a logo for the user/capper
        # if user_logo_url: embed.set_thumbnail(url=user_logo_url)

        # Add Game/League Info
        game_info = "N/A" # Default
        league_name = details.get('league', 'N/A')
        game_id = details.get('game_id')

        if game_id and game_id != 'Other':
             # TODO: Ideally fetch game details here async if needed for names/time
             # Example placeholder:
             game_info = f"Game ID: {game_id}"
        elif details.get('game_description'):
             game_info = details['game_description'][:100] # Limit length
        else: # If game_id is 'Other' and no description
             game_info = "Manual/Other"

        embed.add_field(name="League", value=league_name, inline=True)
        embed.add_field(name="Game", value=game_info, inline=True)
        embed.add_field(name="\u200B", value="\u200B", inline=True) # Spacer field

        # If it's a generic Parlay title, add the selection legs as a field
        if is_multi_team_parlay:
             embed.add_field(name="Legs", value=f"```{selection_str[:1000]}```", inline=False)

        # Add Odds, Units, Payout
        odds_value = details.get('odds', 0.0)
        units_value = details.get('units', 0.0)
        embed.add_field(name="Odds", value=f"{odds_value:+}", inline=True) # Show sign
        embed.add_field(name="Units", value=f"{units_value:.2f}u", inline=True) # Format units

        # Payout Calculation
        potential_profit = 0.0
        if units_value > 0:
            if odds_value > 0: potential_profit = units_value * (odds_value / 100.0)
            elif odds_value < 0: potential_profit = units_value * (100.0 / abs(odds_value))
        # potential_payout = units_value + potential_profit # Payout isn't usually shown on the card

        embed.add_field(name="To Win", value=f"{potential_profit:.2f}u", inline=True) # Format profit

        embed.set_footer(text=f"Bet Serial: {bet_serial} | Status: Pending")
        embed.timestamp = datetime.now(timezone.utc)
        return embed


# Define Confirmation Buttons
class ConfirmButton(Button):
    def __init__(self, parent_view):
        # Use custom_id tied to the interaction ID to prevent conflicts if multiple users run command
        super().__init__(style=ButtonStyle.green, label="Confirm & Post", custom_id=f"confirm_bet_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        # Disable buttons immediately
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        # Edit the message to show disabled buttons *before* submitting
        await interaction.response.edit_message(view=self.parent_view)
        # Proceed to submit the bet
        await self.parent_view.submit_bet(interaction)

class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.red, label="Cancel", custom_id=f"cancel_bet_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        # Disable buttons and inform user
        for item in self.parent_view.children:
            if isinstance(item, Button):
                item.disabled = True
        await interaction.response.edit_message(content="Bet cancelled.", embed=None, view=self.parent_view)
        self.parent_view.stop() # Stop the view


# View with buttons to add reactions to the bet message
class BetResolutionView(View):
     def __init__(self, bet_serial: int): # bet_serial might not be needed here if not used
          super().__init__(timeout=None) # Make view persistent
          # No need to store bet_serial if buttons just add reactions

     # Make custom_ids static and unique for persistent views
     @discord.ui.button(label="Win", style=discord.ButtonStyle.green, emoji="✅", custom_id="bet_resolve_win")
     async def win_button(self, interaction: Interaction, button: Button):
         # Check permissions or original user if needed here
         # For now, just add reaction
         try:
              await interaction.message.add_reaction("✅")
              await interaction.response.send_message("Added Win reaction.", ephemeral=True)
         except discord.Forbidden:
              await interaction.response.send_message("I don't have permission to add reactions here.", ephemeral=True)
         except Exception as e:
             logger.error(f"Error adding win reaction: {e}")
             await interaction.response.send_message("Could not add reaction.", ephemeral=True)


     @discord.ui.button(label="Loss", style=discord.ButtonStyle.red, emoji="❌", custom_id="bet_resolve_loss")
     async def loss_button(self, interaction: Interaction, button: Button):
         try:
              await interaction.message.add_reaction("❌")
              await interaction.response.send_message("Added Loss reaction.", ephemeral=True)
         except discord.Forbidden:
              await interaction.response.send_message("I don't have permission to add reactions here.", ephemeral=True)
         except Exception as e:
             logger.error(f"Error adding loss reaction: {e}")
             await interaction.response.send_message("Could not add reaction.", ephemeral=True)

     @discord.ui.button(label="Push", style=discord.ButtonStyle.grey, emoji="🅿️", custom_id="bet_resolve_push")
     async def push_button(self, interaction: Interaction, button: Button):
         try:
              await interaction.message.add_reaction("🅿️") # Use a distinct push emoji
              await interaction.response.send_message("Added Push reaction.", ephemeral=True)
         except discord.Forbidden:
              await interaction.response.send_message("I don't have permission to add reactions here.", ephemeral=True)
         except Exception as e:
             logger.error(f"Error adding push reaction: {e}")
             await interaction.response.send_message("Could not add reaction.", ephemeral=True)


# --- Cog Definition ---
class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Access services via self.bot if they are attached in main.py
        self.bet_service: BetService = bot.bet_service
        self.game_service: GameService = bot.game_service

    @app_commands.command(name="bet", description="Place a new bet through a guided workflow.")
    # Add checks decorator if you have specific roles/permissions
    # @app_commands.checks.has_role("CapperRoleNameOrID")
    async def bet_command(self, interaction: Interaction):
        """Starts the interactive betting workflow."""
        logger.info(f"Bet command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            # Ensure services are available
            if not hasattr(self.bot, 'bet_service') or not hasattr(self.bot, 'game_service'):
                logger.error("Betting services not found on bot instance.")
                await interaction.response.send_message("❌ Bot is not properly configured (Service Error).", ephemeral=True)
                return

            # Check if user is authorized using BetService
            # Make sure admin has run /setid for this user first
            is_authorized = await self.bet_service.is_user_authorized(interaction.guild_id, interaction.user.id)
            if not is_authorized:
                await interaction.response.send_message(
                    "❌ You are not authorized to place bets. Please contact an admin if you should be.",
                    ephemeral=True
                )
                return

            # Defer the response ephemerally before starting the view
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Start the interactive workflow view
            view = BetWorkflowView(interaction, self.bot)
            await view.start_flow() # The view now sends/edits the followup message

        except Exception as e:
            logger.exception(f"Error initiating bet command for {interaction.user}: {e}")
            # Use followup if initial response was deferred
            await interaction.followup.send("❌ An error occurred while starting the bet command.", ephemeral=True)

    # Listener for persistent views (needed for BetResolutionView)
    @commands.Cog.listener()
    async def on_ready(self):
        # Re-register persistent views if necessary
        logger.info("BettingCog ready, persistent views should re-register if needed.")
        # Add dummy view instance to register buttons
        self.bot.add_view(BetResolutionView(bet_serial=0))

    # Optional: Cog specific error handler
    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        # Handle errors like MissingRole, CheckFailure, etc.
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("You do not have the required role/permissions for this command.", ephemeral=True)
        else:
            logger.error(f"Error in BettingCog command: {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("An internal error occurred with the betting command.", ephemeral=True)
            else:
                try: 
                    await interaction.followup.send("An internal error occurred.", ephemeral=True)
                except Exception: 
                    pass # Ignore followup errors


# The setup function for the extension
async def setup(bot: commands.Bot):
    """Register the betting command with the bot."""
    # Add the cog to the bot
    await bot.add_cog(BettingCog(bot))
    # Register the command with the command tree
    bot.tree.add_command(BettingCog.bet_command)
    logger.info("BettingCog loaded and command registered")
