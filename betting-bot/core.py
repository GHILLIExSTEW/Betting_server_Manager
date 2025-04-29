import discord
from discord import app_commands
from typing import Dict, Callable, List, Tuple, Union, Coroutine, Any
import logging
from bot.data.db_manager import db_manager
from bot.data.cache_manager import cache_manager
from bot.services.game_service import GameService
from bot.services.voice_service import VoiceService
from bot.services.bet_service import BetService
from bot.web.server import setup_server, start_server, stop_server

logger = logging.getLogger(__name__)

GLOBAL_COMMAND_FILES = ["admin", "subscription", "help", "load_logos"]
GUILD_COMMAND_FILES = [
    "betting",
    "stats",
    "leaderboard",
    "profile"
]

class BettingBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.command_tree = app_commands.CommandTree(self)
        self.game_service = GameService(self)
        self.voice_service = VoiceService(self)
        self.bet_service = BetService(self, self.command_tree)
        self.web_app = None
        self.guild_command_setup_functions: Dict[str, Union[Callable, Coroutine]] = {}

    async def load_commands(self):
        """Loads global command modules and stores guild command setup functions"""
        # Load global commands
        for cmd_file in GLOBAL_COMMAND_FILES:
            try:
                module = __import__(f"bot.commands.{cmd_file}", fromlist=["setup"])
                if hasattr(module, "setup"):
                    await module.setup(self.command_tree)
                    logger.info(f"Loaded global command module: {cmd_file}")
            except Exception as e:
                logger.error(f"Failed to load global command module {cmd_file}: {e}")

        # Load guild commands
        for cmd_file in GUILD_COMMAND_FILES:
            try:
                module = __import__(f"bot.commands.{cmd_file}", fromlist=["setup"])
                if hasattr(module, "setup"):
                    self.guild_command_setup_functions[cmd_file] = module.setup
                    logger.info(f"Loaded guild command module: {cmd_file}")
            except Exception as e:
                logger.error(f"Failed to load guild command module {cmd_file}: {e}")

    async def register_guild_commands(self, guild_id: int):
        """Clears and registers commands specific to a given guild"""
        guild = self.get_guild(guild_id)
        if not guild:
            logger.error(f"Guild {guild_id} not found")
            return

        # Clear existing commands
        self.command_tree.clear_commands(guild=guild)

        # Register new commands
        for setup_func in self.guild_command_setup_functions.values():
            try:
                await setup_func(self.command_tree, guild)
            except Exception as e:
                logger.error(f"Failed to register guild commands: {e}")

        # Sync commands
        try:
            await self.command_tree.sync(guild=guild)
            logger.info(f"Synced commands for guild {guild_id}")
        except Exception as e:
            logger.error(f"Failed to sync commands for guild {guild_id}: {e}")

    async def setup_hook(self):
        """Connects to DB/Cache, starts services, runs checks, starts web server"""
        try:
            # Connect to database and cache
            await self.db_manager.connect()
            await self.cache_manager.connect()

            # Start services
            await self.game_service.start()
            await self.voice_service.start()
            await self.bet_service.start()

            # Setup web server
            self.web_app = await setup_server(self, self.db_manager)
            await start_server(self.web_app, self.db_manager)

            logger.info("Bot setup completed successfully")
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            raise

    async def on_ready(self):
        """Called when the bot is ready. Loads commands."""
        logger.info(f"Bot is ready. Logged in as {self.user}")
        await self.load_commands()

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handles raw reaction add events for bet resolution"""
        if payload.user_id == self.user.id:
            return

        try:
            await self.bet_service.handle_final_bet_reaction(payload)
        except Exception as e:
            logger.error(f"Error handling reaction: {e}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handles errors originating from application commands"""
        if isinstance(error, app_commands.CommandNotFound):
            await interaction.response.send_message("Command not found.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Command error: {error}")
            await interaction.response.send_message("An error occurred while executing the command.", ephemeral=True)

    async def close(self):
        """Gracefully shuts down services, connections, and the bot"""
        try:
            # Stop services
            await self.game_service.stop()
            await self.voice_service.stop()
            await self.bet_service.stop()

            # Stop web server
            await stop_server()

            # Close connections
            await self.db_manager.close()
            await self.cache_manager.close()

            logger.info("Bot shutdown completed successfully")
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")
        finally:
            await super().close() 