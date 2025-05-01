# betting-bot/commands/betting.py

"""Betting command for placing bets."""

import discord
from discord import app_commands, ButtonStyle, Interaction, SelectOption, TextChannel
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
import logging
from typing import Optional, List, Dict, Union
from datetime import datetime, timezone

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
            SelectOption(label="Straight", value="straight", description="Moneyline, over/under, or player prop"),
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

class LineTypeSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            SelectOption(label="Game Line", value="game_line", description="Moneyline or game over/under"),
            SelectOption(label="Player Prop", value="player_prop", description="Bet on player performance")
        ]
        super().__init__(placeholder="Select Line Type...", options=options, min_values=1, max_values=1)

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
            if game_api_id is None: continue
            options.append(SelectOption(label=label[:100], value=str(game_api_id)))
        options.append(SelectOption(label="Other (Manual Entry)", value="Other"))
        super().__init__(placeholder="Select Game (or Other)...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        self.parent_view.bet_details['game_id'] = self.values[0]
        if self.values[0] != "Other":
            game = next((g for g in self.parent_view.games if str(g.get('id')) == self.values[0]), None)
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
        super().__init__(placeholder=f"{team_name} Players...", options=options, min_values=0, max_values=1)

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
        super().__init__(placeholder=f"{team_name} Players...", options=options, min_values=0, max_values=1)

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

class BetDetailsModal(Modal, title="Enter Bet Details"):
    def __init__(self, line_type: str, is_manual: bool = False):
        super().__init__(title="Enter Bet Details")
        self.line_type = line_type
        self.is_manual = is_manual
        if is_manual:
            self.team = TextInput(label="Team", placeholder="e.g., Lakers", required=True, max_length=100)
            self.opponent = TextInput(label="Opponent" if line_type == "game_line" else "Player", placeholder="e.g., Celtics or LeBron James", required=True, max_length=100)
            self.add_item(self.team)
            self.add_item(self.opponent)
        self.line = TextInput(label="Line", placeholder="e.g., -7.5, Over 220.5", required=True, max_length=100)
        self.odds = TextInput(label="Odds (American)", placeholder="e.g., -110, +150", required=True, max_length=10)
        self.units = TextInput(label="Units (e.g., 1, 1.5)", placeholder="Enter units to risk", required=True, max_length=5)
        if line_type == "player_prop" and not is_manual:
            self.player = TextInput(label="Player", placeholder="e.g., LeBron James", required=True, max_length=100)
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
                await interaction.response.send_message("Please provide valid team and opponent/player.", ephemeral=True)
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
        if not options:
            options.append(SelectOption(label="No Writable Channels Found", value="none", emoji="❌"))
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

class AddLegButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=ButtonStyle.blurple, label="Add Leg", custom_id=f"add_leg_{parent_view.original_interaction.id}")
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        self.parent_view.current_step = 2  # Reset to league selection for new leg
        await interaction.response.defer()
        await self.parent_view.go_next(interaction)

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

class BetWorkflowView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot):
        super().__init__(timeout=600)
        self.original_interaction = interaction
        self.bot = bot
        self.current_step = 0
        self.bet_details = {'legs': []}
        self.games = []  # Store games for access in GameSelect
        self.message: Optional[discord.WebhookMessage | discord.InteractionMessage] = None
        self.is_processing = False  # Prevent double advancement

    async def start_flow(self):
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
        if self.is_processing:
            logger.debug(f"Skipping go_next call; already processing step {self.current_step}")
            return
        self.is_processing = True
        try:
            self.clear_items()
            self.current_step += 1
            step_content = f"**Step {self.current_step}**"
            embed_to_send = None

            logger.debug(f"Entering step {self.current_step}")

            try:
                if self.current_step == 1:
                    self.add_item(BetTypeSelect(self))
                    step_content += ": Select Bet Type"
                elif self.current_step == 2:
                    allowed_leagues = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Soccer", "Tennis", "UFC/MMA"]
                    self.add_item(LeagueSelect(self, allowed_leagues))
                    step_content += ": Select League"
                elif self.current_step == 3:
                    self.add_item(LineTypeSelect(self))
                    step_content += ": Select Line Type"
                elif self.current_step == 4:
                    league = self.bet_details.get('league')
                    league_games = []
                    if league and league != "Other":
                        sport = None
                        if league in ["NFL", "NCAAF"]: sport = "american-football"
                        elif league in ["NBA", "NCAAB"]: sport = "basketball"
                        elif league == "MLB": sport = "baseball"
                        elif league == "NHL": sport = "hockey"
                        elif league == "Soccer": sport = "soccer"
                        elif league == "Tennis": sport = "tennis"

                        if sport and hasattr(self.bot, 'game_service'):
                            self.games = await self.bot.game_service.get_upcoming_games(interaction.guild_id, hours=72)
                            league_games = [g for g in self.games if str(g.get('league_id')) == league or g.get('league_name','').lower() == league.lower()]

                    if league_games:
                        self.add_item(GameSelect(self, league_games))
                        step_content += f": Select Game for {league} (or Other)"
                    else:
                        logger.warning(f"No upcoming games found for league {league}. Proceeding to manual entry.")
                        self.bet_details['game_id'] = "Other"
                        # Do not call go_next; let current execution advance to step 5
                elif self.current_step == 5:
                    line_type = self.bet_details.get('line_type')
                    game_id = self.bet_details.get('game_id')
                    is_manual = game_id == "Other"

                    logger.debug(f"Step 5: line_type={line_type}, is_manual={is_manual}, game_id={game_id}")

                    if line_type == "player_prop" and not is_manual and hasattr(self.bot, 'game_service'):
                        players_data = await self.bot.game_service.get_game_players(game_id)
                        home_players = players_data.get('home_players', [])
                        away_players = players_data.get('away_players', [])
                        home_team = self.bet_details.get('home_team_name', 'Home Team')
                        away_team = self.bet_details.get('away_team_name', 'Away Team')

                        if home_players or away_players:
                            self.add_item(HomePlayerSelect(self, home_players, home_team))
                            self.add_item(AwayPlayerSelect(self, away_players, away_team))
                            step_content += f": Select a Player from {home_team} or {away_team}"
                        else:
                            logger.warning(f"No players available for game {game_id}. Proceeding to manual player entry.")
                            modal = BetDetailsModal(line_type=line_type, is_manual=False)
                            modal.view = self
                            logger.debug(f"Sending BetDetailsModal for player_prop, is_manual=False")
                            try:
                                await interaction.response.send_modal(modal)
                            except discord.HTTPException as e:
                                logger.error(f"Failed to send BetDetailsModal: {e}")
                                await self.edit_message(interaction, content="❌ Failed to send bet details modal. Please try again.", view=None)
                                self.stop()
                            return
                    else:
                        modal = BetDetailsModal(line_type=line_type, is_manual=is_manual)
                        modal.view = self
                        logger.debug(f"Sending BetDetailsModal for line_type={line_type}, is_manual={is_manual}")
                        try:
                            await interaction.response.send_modal(modal)
                        except discord.HTTPException as e:
                            logger.error(f"Failed to send BetDetailsModal: {e}")
                            await self.edit_message(interaction, content="❌ Failed to send bet details modal. Please try again.", view=None)
                            self.stop()
                        return
                elif self.current_step == 6:
                    if not self.bet_details.get('legs'):
                        logger.error("No bet details provided for channel selection")
                        await self.edit_message(interaction, content="❌ No bet details provided. Please start over.", view=None)
                        self.stop()
                        return

                    channels = []
                    if hasattr(self.bot, 'db_manager'):
                        settings = await self.bot.db_manager.fetch_one(
                            "SELECT embed_channel_1, embed_channel_2 FROM server_settings WHERE guild_id = %s",
                            (interaction.guild_id,)
                        )
                        if settings:
                            for channel_id in [settings['embed_channel_1'], settings['embed_channel_2']]:
                                if channel_id:
                                    channel = interaction.guild.get_channel(int(channel_id))
                                    if channel and isinstance(channel, TextChannel) and channel.permissions_for(interaction.guild.me).send_messages:
                                        channels.append(channel)
                    else:
                        channels = sorted(
                            [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.user).send_messages and ch.permissions_for(interaction.guild.me).send_messages],
                            key=lambda c: c.position
                        )

                    if not channels:
                        await self.edit_message(interaction, content="Error: No text channels found where I can post.", view=None)
                        self.stop()
                        return
                    self.add_item(ChannelSelect(self, channels))
                    embed_to_send = self.create_preview_embed()
                    step_content += ": Select Channel to Post Bet"
                elif self.current_step == 7:
                    try:
                        legs = self.bet_details.get('legs', [])
                        if self.bet_details.get('bet_type') == "parlay" and len(legs) < 2:
                            raise ValueError("Parlay bets require at least two legs")
                        
                        for leg in legs:
                            odds_str = leg.get('odds_str', '').replace('+','').strip()
                            units_str = leg.get('units_str', '').lower().replace('u','').strip()

                            if not odds_str:
                                raise ValueError("Odds cannot be empty")
                            if not units_str:
                                raise ValueError("Units cannot be empty")

                            try:
                                odds_val = int(odds_str)
                            except ValueError:
                                raise ValueError("Odds must be a valid integer (e.g., -110, +150)")
                            if not (-10000 <= odds_val <= 10000):
                                raise ValueError("Odds must be between -10000 and +10000")
                            if -100 < odds_val < 100:
                                raise ValueError("Odds cannot be between -99 and +99")
                            leg['odds'] = float(odds_val)

                            try:
                                units_val = float(units_str)
                            except ValueError:
                                raise ValueError("Units must be a valid number (e.g., 1, 1.5)")
                            if not (0.1 <= units_val <= 10.0):
                                raise ValueError("Units must be between 0.1 and 10.0")
                            leg['units'] = units_val

                        embed_to_send = self.create_confirmation_embed()
                        self.add_item(ConfirmButton(self))
                        self.add_item(CancelButton(self))
                        if self.bet_details.get('bet_type') == "parlay":
                            self.add_item(AddLegButton(self))
                        step_content = f"**Step {self.current_step}**: Please Confirm Your Bet"
                    except ValueError as ve:
                        logger.error(f"Bet input validation failed: {ve}")
                        await self.edit_message(interaction, content=f"❌ Error: {ve} Please start over.", view=None)
                        self.stop()
                        return
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

        finally:
            self.is_processing = False

    def create_preview_embed(self) -> discord.Embed:
        details = self.bet_details
        embed = discord.Embed(title="📊 Bet Preview", color=discord.Color.blue())
        embed.add_field(name="Type", value=details.get('bet_type', 'N/A').title(), inline=True)
        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)
        game_info = "Manual Entry"; game_id = details.get('game_id')
        if game_id and game_id != 'Other': game_info = f"Game ID: {game_id}"
        elif details.get('legs') and details['legs'][0].get('team'):
            game_info = f"{details['legs'][0]['team']} vs {details['legs'][0].get('opponent', 'N/A')}"
        embed.add_field(name="Game", value=game_info, inline=True)
        
        legs = details.get('legs', [])
        for i, leg in enumerate(legs, 1):
            selection = leg.get('line', 'N/A')
            if leg.get('player'):
                selection = f"{leg['player']} - {selection}"
            embed.add_field(
                name=f"Leg {i} Selection" if len(legs) > 1 else "Selection",
                value=f"```{selection[:1000]}```",
                inline=False
            )
            embed.add_field(name="Odds", value=f"{leg.get('odds_str', 'N/A')}", inline=True)
            embed.add_field(name="Units", value=f"{leg.get('units_str', 'N/A')}u", inline=True)
            if leg.get('team'):
                embed.add_field(name="Team", value=leg['team'], inline=True)
        
        embed.set_footer(text="Select a channel to post the bet.")
        return embed

    def create_confirmation_embed(self) -> discord.Embed:
        details = self.bet_details
        embed = discord.Embed(title="📊 Bet Confirmation", color=discord.Color.blue())
        embed.add_field(name="Type", value=details.get('bet_type', 'N/A').title(), inline=True)
        embed.add_field(name="League", value=details.get('league', 'N/A'), inline=True)
        game_info = "Manual Entry"; game_id = details.get('game_id')
        if game_id and game_id != 'Other': game_info = f"Game ID: {game_id}"
        elif details.get('legs') and details['legs'][0].get('team'):
            game_info = f"{details['legs'][0]['team']} vs {details['legs'][0].get('opponent', 'N/A')}"
        embed.add_field(name="Game", value=game_info, inline=True)
        
        legs = details.get('legs', [])
        total_potential_profit = 0.0
        total_units = 0.0
        for i, leg in enumerate(legs, 1):
            selection = leg.get('line', 'N/A')
            if leg.get('player'):
                selection = f"{leg['player']} - {selection}"
            embed.add_field(
                name=f"Leg {i} Selection" if len(legs) > 1 else "Selection",
                value=f"```{selection[:1000]}```",
                inline=False
            )
            odds_value = leg.get('odds', 0.0)
            units_value = leg.get('units', 0.0)
            embed.add_field(name="Odds", value=f"{odds_value:+}", inline=True)
            embed.add_field(name="Units", value=f"{units_value:.2f}u", inline=True)
            if leg.get('team'):
                embed.add_field(name="Team", value=leg['team'], inline=True)
            potential_profit = 0.0
            if units_value > 0:
                if odds_value > 0:
                    potential_profit = units_value * (odds_value / 100.0)
                elif odds_value < 0:
                    potential_profit = units_value * (100.0 / abs(odds_value))
            total_potential_profit += potential_profit
            total_units += units_value
        
        channel_id = details.get('channel_id')
        channel = self.bot.get_channel(channel_id) if channel_id else None
        channel_mention = channel.mention if channel else "Invalid Channel"
        embed.add_field(name="Post Channel", value=channel_mention, inline=True)
        embed.add_field(name="Total To Win", value=f"{total_potential_profit:.2f}u", inline=True)
        embed.add_field(name="Total Payout", value=f"{total_units + total_potential_profit:.2f}u", inline=True)
        embed.set_footer(text="Confirm to place and post the bet.")
        return embed

    async def submit_bet(self, interaction: Interaction):
        details = self.bet_details
        await self.edit_message(interaction, content="Processing and posting bet...", view=None, embed=None)
        sent_message = None

        try:
            legs = details.get('legs', [])
            bet_type = details.get('bet_type')
            post_channel_id = details.get('channel_id')
            post_channel = self.bot.get_channel(post_channel_id) if post_channel_id else None

            if bet_type == "straight":
                leg = legs[0]
                bet_serial = await self.bot.bet_service.create_bet(
                    guild_id=interaction.guild_id,
                    user_id=interaction.user.id,
                    game_id=details.get('game_id') if details.get('game_id') != 'Other' else None,
                    bet_type="player_prop" if leg.get('player') else "game_line",
                    team_name=leg.get('team', leg.get('line')),
                    units=leg.get('units'),
                    odds=leg.get('odds'),
                    channel_id=post_channel_id,
                    player=leg.get('player')
                )
            else:  # Parlay
                bet_serial = await self.bot.bet_service.create_parlay_bet(
                    guild_id=interaction.guild_id,
                    user_id=interaction.user.id,
                    legs=[
                        {
                            'game_id': details.get('game_id') if details.get('game_id') != 'Other' else None,
                            'bet_type': "player_prop" if leg.get('player') else "game_line",
                            'team_name': leg.get('team', leg.get('line')),
                            'units': leg.get('units'),
                            'odds': leg.get('odds'),
                            'player': leg.get('player')
                        } for leg in legs
                    ],
                    channel_id=post_channel_id
                )

            if post_channel and isinstance(post_channel, TextChannel):
                final_embed = self.create_final_bet_embed(bet_serial)
                view = BetResolutionView(bet_serial)
                sent_message = await post_channel.send(embed=final_embed, view=view)

                if sent_message and hasattr(self.bot.bet_service, 'pending_reactions'):
                    self.bot.bet_service.pending_reactions[sent_message.id] = {
                        'bet_serial': bet_serial,
                        'user_id': interaction.user.id,
                        'guild_id': interaction.guild_id,
                        'channel_id': post_channel_id,
                        'legs': details.get('legs'),
                        'league': details.get('league'),
                        'bet_type': bet_type
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
        details = self.bet_details
        user = self.original_interaction.user
        bet_type = details.get('bet_type', 'Bet').title()
        embed_title = f"{bet_type} Bet"
        if bet_type == "Parlay" and len(details.get('legs', [])) > 1:
            embed_title = "Multi-Leg Parlay Bet"
        embed = discord.Embed(title=embed_title, color=discord.Color.gold())
        embed.set_author(name=f"{user.display_name}'s Pick", icon_url=user.display_avatar.url if user.display_avatar else None)
        league_name = details.get('league', 'N/A')
        game_info = "Manual Entry"; game_id = details.get('game_id')
        if game_id and game_id != 'Other': game_info = f"Game ID: {game_id}"
        elif details.get('legs') and details['legs'][0].get('team'):
            game_info = f"{details['legs'][0]['team']} vs {details['legs'][0].get('opponent', 'N/A')}"
        embed.add_field(name="League", value=league_name, inline=True)
        embed.add_field(name="Game", value=game_info, inline=True)
        embed.add_field(name="\u200B", value="\u200B", inline=True)

        legs = details.get('legs', [])
        total_potential_profit = 0.0
        total_units = 0.0
        for i, leg in enumerate(legs, 1):
            selection = leg.get('line', 'N/A')
            if leg.get('player'):
                selection = f"{leg['player']} - {selection}"
            embed.add_field(
                name=f"Leg {i} Selection" if len(legs) > 1 else "Selection",
                value=f"```{selection[:1000]}```",
                inline=False
            )
            odds_value = leg.get('odds', 0.0)
            units_value = leg.get('units', 0.0)
            embed.add_field(name="Odds", value=f"{odds_value:+}", inline=True)
            embed.add_field(name="Units", value=f"{units_value:.2f}u", inline=True)
            if leg.get('team'):
                embed.add_field(name="Team", value=leg['team'], inline=True)
            potential_profit = 0.0
            if units_value > 0:
                if odds_value > 0:
                    potential_profit = units_value * (odds_value / 100.0)
                elif odds_value < 0:
                    potential_profit = units_value * (100.0 / abs(odds_value))
            total_potential_profit += potential_profit
            total_units += units_value

        embed.add_field(name="Total To Win", value=f"{total_potential_profit:.2f}u", inline=True)
        embed.set_footer(text=f"Bet Serial: {bet_serial} | Status: Pending")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

class BetResolutionView(View):
    def __init__(self, bet_serial: int):
        super().__init__(timeout=None)
        self.bet_serial = bet_serial

    @discord.ui.button(label="Win", style=discord.ButtonStyle.green, emoji="✅", custom_id="bet_resolve_win")
    async def win_button(self, interaction: Interaction, button: Button):
        try:
            await interaction.message.add_reaction("✅")
            await interaction.response.send_message("Added Win reaction.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error adding win reaction: {e}")
            await interaction.response.send_message("Could not add reaction.", ephemeral=True)

    @discord.ui.button(label="Loss", style=discord.ButtonStyle.red, emoji="❌", custom_id="bet_resolve_loss")
    async def loss_button(self, interaction: Interaction, button: Button):
        try:
            await interaction.message.add_reaction("❌")
            await interaction.response.send_message("Added Loss reaction.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error adding loss reaction: {e}")
            await interaction.response.send_message("Could not add reaction.", ephemeral=True)

    @discord.ui.button(label="Push", style=discord.ButtonStyle.grey, emoji="🅿️", custom_id="bet_resolve_push")
    async def push_button(self, interaction: Interaction, button: Button):
        try:
            await interaction.message.add_reaction("🅿️")
            await interaction.response.send_message("Added Push reaction.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error adding push reaction: {e}")
            await interaction.response.send_message("Could not add reaction.", ephemeral=True)

class BettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bet", description="Place a new bet through a guided workflow.")
    async def bet_command(self, interaction: Interaction):
        """Starts the interactive betting workflow."""
        logger.info(f"Bet command initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            is_auth = True  # Replace with actual authorization check if needed
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
                try:
                    await interaction.followup.send(error_message, ephemeral=True)
                except discord.HTTPException:
                    pass
            else:
                try:
                    await interaction.response.send_message(error_message, ephemeral=True)
                except discord.HTTPException:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(BettingCog(bot))
    logger.info("BettingCog loaded")
