# betting-bot/commands/betting.py

"""Betting command for placing bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union
from datetime import datetime, timezone

# Use relative imports (assuming commands/ is sibling to services/, utils/)
try:
    from ..utils.errors import BetServiceError, ValidationError, GameNotFoundError
except ImportError:
    from utils.errors import BetServiceError, ValidationError, GameNotFoundError

logger = logging.getLogger(__name__)

# --- UI Component Classes ---
class BetTypeSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="Moneyline", value="moneyline", description="Bet on who will win"),
            SelectOption(label="Spread", value="spread", description="Bet on the margin of victory"),
            SelectOption(label="Total", value="total", description="Bet on the total score (Over/Under)"),
            SelectOption(label="Parlay", value="parlay", description="Combine multiple bets")
        ]
        super().__init__(placeholder="Select Bet Type...", options=options, min_values=1, max_values=1)

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
        super().__init__(placeholder="Select League...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['league'] = self.values[0]
        logger.debug(f"League selected: {self.values[0]}")
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
            if game_api_id is None: continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id)))
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(placeholder="Select Game (or Other)...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['game_id'] = self.values[0]
        logger.debug(f"Game selected: {self.values[0]}")
        self.disabled = True
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

class ManualGameModal(Modal, title="Enter Manual Game Details"):
    manual_selection = TextInput(label="Your Bet Selection", placeholder="e.g., Team Name -3.5", required=True, max_length=150)
    game_description = TextInput(label="Game Description (Optional)", placeholder="e.g., Team A vs Team B", required=False, style=discord.TextStyle.short, max_length=100)

    async def on_submit(self, interaction: Interaction):
        self.view.bet_details['selection'] = self.manual_selection.value.strip()
        self.view.bet_details['game_description'] = self.game_description.value.strip()
        logger.debug(f"Manual game/selection entered: {self.manual_selection.value}")
        if not interaction.response.is_done():
            await interaction.response.defer()
        await self.view.go_next(interaction)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in ManualGameModal: {error}", exc_info=True)
        try:
            await interaction.followup.send('❌ An error occurred with the manual game modal.', ephemeral=True)
        except discord.HTTPException:
            logger.warning("Could not send error followup for ManualGameModal.")

class BetDetailsModal(Modal, title="Enter Bet Details"):
    line_or_selection = TextInput(label="Selection / Line", placeholder="e.g., -7.5, Over 220.5", required=True, max_length=100)
    odds = TextInput(label="Odds (American)", placeholder="e.g., -110, +150", required=True, max_length=10)
    units = TextInput(label="Units (e.g., 1, 1.5)", placeholder="Enter units to risk", required=True, max_length=5)

    async def on_submit(self, interaction: Interaction):
        # Validate inputs before storing
        line_str = self.line_or_selection.value.strip()
        odds_str = self.odds.value.strip()
        units_str = self.units.value.strip()

        # Check for empty inputs
        if not line_str:
            await interaction.response.send_message("Please provide a valid selection/line (e.g., -7.5, Over 220.5).", ephemeral=True)
            return
        if not odds_str:
            await interaction.response.send_message("Please provide a valid odds value (e.g., -110, +150).", ephemeral=True)
            return
        if not units_str:
            await interaction.response.send_message("Please provide a valid units value (e.g., 1, 1.5).", ephemeral=True)
            return

        # Store validated inputs
        self.view.bet_details['selection'] = line_str
        self.view.bet_details['odds_str'] = odds_str
        self.view.bet_details['units_str'] = units_str
        logger.debug(f"Bet details entered: Line '{line_str}', Odds '{odds_str}', Units '{units_str}'")
        if not interaction.response.is_done():
            await interaction.response.defer()
        await self.view.go_next(interaction)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(f"Error in BetDetailsModal: {error}", exc_info=True)
        try:
            await interaction.followup.send('❌ An error occurred with the bet details modal.', ephemeral=True)
        except discord.HTTPException:
            logger.warning("Could not send error followup for BetDetailsModal.")

class ChannelSelect(Select):
    def __init__(self, parent_view, channels: List[TextChannel]):
        self.parent_view = parent_view
        options = [SelectOption(label=f"#{channel.name}", value=str(channel.id)) for channel in channels[:25]]
        if not options: options.append(SelectOption(label="No Writable Channels Found", value="none", emoji="❌"))
        super().__init__(placeholder="Select Channel to Post Bet...", options=options, min_values=1, max_values=1, disabled=not options or options[0].value == "none")

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

class BetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600)
        self.original_interaction = interaction
        self.bot = bot
        self.current_step = 0
        self.bet_details = {}
        self.message: Optional[discord.WebhookMessage | discord.InteractionMessage] = None

    async def start_flow(self):
        """Sends the initial message and starts the workflow."""
        self.message = await self.original_interaction.followup.send(
            "Starting bet placement...", view=self, ephemeral=True
        )
        await self.go_next(self.original_interaction)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this bet placement.", ephemeral=True)
            return False
        return True

    async def edit_message(self, interaction: Optional[Interaction] = None, content: Optional[str] = None, view: Optional[View] = None, embed: Optional[discord.Embed] = None):
        """Helper to edit the interaction's message."""
        target_message = self.message
        try:
            if target_message:
                if isinstance(target_message, discord.InteractionMessage):
                    await target_message.edit(content=content, embed=embed, view=view)
                elif isinstance(target_message, discord.WebhookMessage):
                    await target_message.edit(content=content, embed=embed, view=view)
                else:
                    await self.original_interaction.edit_original_response(content=content, embed=embed, view=view)
            else:
                await self.original_interaction.edit_original_response(content=content, embed=embed, view=view)
        except (discord.NotFound, discord.HTTPException) as e:
            logger.warning(f"Failed to edit BetWorkflowView message: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error editing BetWorkflowView message: {e}")

    async def go_next(self, interaction: Interaction):
        """Progress to the next step in the betting workflow."""
        self.clear_items()
        self.current_step += 1
        step_content = f"**Step {self.current_step}**"
        embed_to_send = None

        try:
            if self.current_step == 1:
                self.add_item(BetTypeSelect(self))
                step_content += ": Select Bet Type"
            elif self.current_step == 2:
                allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                self.add_item(LeagueSelect(self, allowed_leagues))
                step_content += ": Select League"
            elif self.current_step == 3:
                league = self.bet_details.get('league')
                if league and league != "Other":
                    sport = None
                    if league in ["NFL", "NCAAF"]: sport = "american-football"
                    elif league in ["NBA", "NCAAB"]: sport = "basketball"
                    elif league == "MLB": sport = "baseball"
                    elif league == "NHL": sport = "hockey"
                    elif league == "Soccer": sport = "soccer"
                    elif league == "Tennis": sport = "tennis"

                    if sport and hasattr(self.bot, 'game_service'):
                        upcoming_games = await self.bot.game_service.get_upcoming_games(interaction.guild_id, hours=72)
                        league_games = [g for g in upcoming_games if str(g.get('league_id')) == league or g.get('league_name','').lower() == league.lower()]

                        if league_games:
                            self.add_item(GameSelect(self, league_games))
                            step_content += f": Select Game for {league} (or Other)"
                        else:
                            logger.warning(f"No upcoming games found for league {league}. Skipping to manual entry.")
                            self.current_step += 1
                            await self.go_next(interaction)
                            return
                    else:
                        logger.warning(f"Sport/GameService unavailable for league {league}. Skipping to manual entry.")
                        self.current_step += 1
                        await self.go_next(interaction)
                        return
                else:
                    self.current_step += 1
                    await self.go_next(interaction)
                    return
            elif self.current_step == 4:
                game_id = self.bet_details.get('game_id')
                is_manual = game_id == "Other" or 'game_id' not in self.bet_details

                if is_manual:
                    modal = ManualGameModal()
                    modal.view = self
                    await interaction.response.send_modal(modal)
                else:
                    modal = BetDetailsModal()
                    modal.view = self
                    await interaction.response.send_modal(modal)
                return

            elif self.current_step == 5:
                valid_channels = sorted([ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.user).send_messages and ch.permissions_for(interaction.guild.me).send_messages], key=lambda c: c.position)
                if not valid_channels:
                    await self.edit_message(interaction, content="Error: No text channels found where I can post.", view=None)
                    self.stop()
                    return
                self.add_item(ChannelSelect(self, valid_channels))
                step_content += ": Select Channel to Post Bet"

            elif self.current_step == 6:
                try:
                    odds_str = self.bet_details.get('odds_str', '').replace('+','').strip()
                    units_str = self.bet_details.get('units_str', '').lower().replace('u','').strip()

                    # Validate non-empty inputs
                    if not odds_str:
                        raise ValueError("Odds cannot be empty")
                    if not units_str:
                        raise ValueError("Units cannot be empty")

                    # Validate odds
                    try:
                        odds_val = int(odds_str)
                    except ValueError:
                        raise ValueError("Odds must be a valid integer (e.g., -110, +150)")
                    if not (-10000 <= odds_val <= 10000):
                        raise ValueError("Odds must be between -10000 and +10000")
                    if -100 < odds_val < 100:
                        raise ValueError("Odds cannot be between -99 and +99")
                    self.bet_details['odds'] = float(odds_val)

                    # Validate units
                    try:
                        units_val = float(units_str)
                    except ValueError:
                        raise ValueError("Units must be a valid number (e.g., 1, 1.5)")
                    if not (0.1 <= units_val <= 10.0):
                        raise ValueError("Units must be between 0.1 and 10.0")
                    self.bet_details['units'] = units_val

                except ValueError as ve:
                    logger.error(f"Bet input validation failed: {ve}")
                    await self.edit_message(interaction, content=f"❌ Error: {ve} Please start over.", view=None)
                    self.stop()
                    return

                embed_to_send = self.create_confirmation_embed()
                self.add_item(ConfirmButton(self))
                self.add_item(CancelButton(self))
                step_content = f"**Step {self.current_step}**: Please Confirm Your Bet"
            else:
                logger.error(f"BetWorkflowView reached unexpected step: {self.current_step}")
                self.stop()
                return

            await self.edit_message(interaction, content=step_content, view=self, embed=embed_to_send)

        except Exception as e:
            logger.exception(f"Error in bet workflow step {self.current_step}: {e}")
            try:
                await self.edit_message(interaction, content="An unexpected error occurred.", view=None, embed=None)
            except Exception:
                pass
            self.stop()

    def create_confirmation_embed(self) -> discord.Embed:
        details = self.bet_details
        embed = discord.Embed(title="📊 Bet Confirmation", color=discord.Color.blue())
        embed.add_field(name="Type", value=details.get('bet_type', 'N/A').title(), inline=True)
        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)
        game_info = "Manual Entry"; game_id = details.get('game_id')
        if game_id and game_id != 'Other': game_info = f"Game ID: {game_id}"
        elif details.get('game_description'): game_info = details['game_description'][:100]
        embed.add_field(name="Game", value=game_info, inline=True)
        selection = details.get('selection', 'N/A')
        embed.add_field(name="Selection", value=f"```{selection[:1000]}```", inline=False)
        odds_value = details.get('odds', 0.0); units_value = details.get('units', 0.0)
        embed.add_field(name="Odds", value=f"{odds_value:+}", inline=True)
        embed.add_field(name="Units", value=f"{units_value:.2f}u", inline=True)
        channel_id = details.get('channel_id'); channel = self.bot.get_channel(channel_id) if channel_id else None
        channel_mention = channel.mention if channel else "Invalid Channel"
        embed.add_field(name="Post Channel", value=channel_mention, inline=True)
        potential_profit = 0.0
        if units_value > 0:
            if odds_value > 0: potential_profit = units_value * (odds_value / 100.0)
            elif odds_value < 0: potential_profit = units_value * (100.0 / abs(odds_value))
        potential_payout = units_value + potential_profit
        embed.add_field(name="To Win", value=f"{potential_profit:.2f}u", inline=True)
        embed.add_field(name="Payout", value=f"{potential_payout:.2f}u", inline=True)
        embed.set_footer(text="Confirm to place and post the bet.")
        return embed

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        await self.edit_message(interaction, content="Processing and posting bet...", view=None, embed=None)
        sent_message = None

        try:
            bet_serial = await self.bot.bet_service.create_bet(
                guild_id=interaction.guild_id, user_id=interaction.user.id,
                game_id=details.get('game_id') if details.get('game_id') != 'Other' else None,
                bet_type=details.get('bet_type'), team_name=details.get('selection'),
                units=details.get('units'), odds=details.get('odds'),
                channel_id=details.get('channel_id'),
            )

            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None

            if post_channel and isinstance(post_channel, TextChannel):
                final_embed = self.create_final_bet_embed(bet_serial)
                view = BetResolutionView(bet_serial)
                sent_message = await post_channel.send(embed=final_embed, view=view)

                if sent_message and hasattr(self.bot.bet_service, 'pending_reactions'):
                    self.bot.bet_service.pending_reactions[sent_message.id] = {
                        'bet_serial': bet_serial, 'user_id': interaction.user.id,
                        'guild_id': interaction.guild_id, 'channel_id': post_channel_id,
                        'selection': details.get('selection'), 'units': details.get('units'),
                        'odds': details.get('odds'), 'league': details.get('league'),
                        'bet_type': details.get('bet_type'),
                    }
                    logger.debug(f"Tracking reactions for msg {sent_message.id} (Bet: {bet_serial})")

                success_message = f"✅ Bet placed successfully! (ID: `{bet_serial}`). Posted to {post_channel.mention}."
                await self.edit_message(interaction, content=success_message, view=None, embed=None)
            else:
                logger.error(f"Could not find channel {post_channel_id} to post bet {bet_serial}.")
                failure_message = f"⚠️ Bet placed (ID: `{bet_serial}`), but failed to post."
                await self.edit_message(interaction, content=failure_message, view=None, embed=None)

        except (ValidationError, BetServiceError) as e:
            logger.error(f"Error submitting bet: {e}")
            await self.edit_message(interaction, content=f"❌ Error placing bet: {e}", view=None, embed=None)
        except Exception as e:
            logger.exception(f"Unexpected error submitting bet: {e}")
            await self.edit_message(interaction, content="❌ An unexpected error occurred.", view=None, embed=None)
        finally:
            self.stop()

    def create_final_bet_embed(self, bet_serial: int) -> discord.Embed:
        details = self.bet_details; user = self.original_interaction.user
        bet_type_str = details.get('bet_type', 'Bet').title()
        selection_str = details.get('selection', 'N/A')
        embed_title = f"{bet_type_str}: {selection_str}"; is_multi_team_parlay = False
        if bet_type_str == 'Parlay' and isinstance(selection_str, str) and '\n' in selection_str: is_multi_team_parlay = True
        if is_multi_team_parlay: embed_title = "Multi-Team Parlay Bet"
        embed = discord.Embed(title=embed_title, color=discord.Color.gold())
        embed.set_author(name=f"{user.display_name}'s Pick", icon_url=user.display_avatar.url if user.display_avatar else None)
        game_info = "N/A"; league_name = details.get('league', 'N/A'); game_id = details.get('game_id')
        if game_id and game_id != 'Other': game_info = f"Game ID: {game_id}"
        elif details.get('game_description'): game_info = details['game_description'][:100]
        else: game_info = "Manual/Other"
        embed.add_field(name="League", value=league_name, inline=True)
        embed.add_field(name="Game", value=game_info, inline=True)
        embed.add_field(name="\u200B", value="\u200B", inline=True)
        if is_multi_team_parlay: embed.add_field(name="Legs", value=f"```{selection_str[:1000]}```", inline=False)
        odds_value = details.get('odds', 0.0); units_value = details.get('units', 0.0)
        embed.add_field(name="Odds", value=f"{odds_value:+}", inline=True)
        embed.add_field(name="Units", value=f"{units_value:.2f}u", inline=True)
        potential_profit = 0.0
        if units_value > 0:
            if odds_value > 0: potential_profit = units_value * (odds_value / 100.0)
            elif odds_value < 0: potential_profit = units_value * (100.0 / abs(odds_value))
        embed.add_field(name="To Win", value=f"{potential_profit:.2f}u", inline=True)
        embed.set_footer(text=f"Bet Serial: {bet_serial} | Status: Pending")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

class ConfirmButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.green, label="Confirm & Post", custom_id=f"confirm_bet_{parent_view.original_interaction.id}")
        self.parent_view = parent_view
    async def callback(self, interaction: Interaction):
        for item in self.parent_view.children:
            if isinstance(item, Button): item.disabled = True
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view.submit_bet(interaction)

class CancelButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.red, label="Cancel", custom_id=f"cancel_bet_{parent_view.original_interaction.id}")
        self.parent_view = parent_view
    async def callback(self, interaction: Interaction):
        for item in self.parent_view.children:
            if isinstance(item, Button): item.disabled = True
        await interaction.response.edit_message(content="Bet cancelled.", embed=None, view=self.parent_view)
        self.parent_view.stop()

class BetResolutionView(View):
    def __init__(self, bet_serial: int): super().__init__(timeout=None)
    @discord.ui.button(label="Win", style=discord.ButtonStyle.green, emoji="✅", custom_id="bet_resolve_win")
    async def win_button(self, interaction: Interaction, button: Button):
        try: await interaction.message.add_reaction("✅"); await interaction.response.send_message("Added Win reaction.", ephemeral=True)
        except Exception as e: logger.error(f"Error adding win reaction: {e}"); await interaction.response.send_message("Could not add reaction.", ephemeral=True)
    @discord.ui.button(label="Loss", style=discord.ButtonStyle.red, emoji="❌", custom_id="bet_resolve_loss")
    async def loss_button(self, interaction: Interaction, button: Button):
        try: await interaction.message.add_reaction("❌"); await interaction.response.send_message("Added Loss reaction.", ephemeral=True)
        except Exception as e: logger.error(f"Error adding loss reaction: {e}"); await interaction.response.send_message("Could not add reaction.", ephemeral=True)
    @discord.ui.button(label="Push", style=discord.ButtonStyle.grey, emoji="🅿️", custom_id="bet_resolve_push")
    async def push_button(self, interaction: Interaction, button: Button):
        try: await interaction.message.add_reaction("🅿️"); await interaction.response.send_message("Added Push reaction.", ephemeral=True)
        except Exception as e: logger.error(f"Error adding push reaction: {e}"); await interaction.response.send_message("Could not add reaction.", ephemeral=True)

class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bet", description="Place a new bet through a guided workflow.")
    async def bet_command(self, interaction: Interaction):
        """Starts the interactive betting workflow."""
        logger.info(f"Bet command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            is_auth = True
            if not is_auth:
                await interaction.response.send_message("❌ You are not authorized to place bets.", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True, thinking=True)
            view = BetWorkflowView(interaction, self.bot)
            await view.start_flow()

        except Exception as e:
            logger.exception(f"Error initiating bet command: {e}")
            error_message = "❌ An error occurred while starting the betting workflow."
            if interaction.response.is_done():
                try: await interaction.followup.send(error_message, ephemeral=True)
                except discord.HTTPException: pass
            else:
                try: await interaction.response.send_message(error_message, ephemeral=True)
                except discord.HTTPException: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(BettingCog(bot))
    logger.info("BettingCog loaded")
