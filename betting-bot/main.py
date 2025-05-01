# betting-bot/main.py

import os
import sys
import logging
import discord
from discord import app_commands
# Import commands specifically for the Cog type hint if needed elsewhere, but not for loading
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# --- Path Setup ---
# Ensure this runs correctly relative to main.py
# Adjust if your .env file is located elsewhere
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}") # Use print or logger early
else:
    print(f"WARNING: .env file not found at {dotenv_path}")

# --- Imports ---
# Use absolute imports assuming 'betting-bot' is the root package recognised by Python
# If running scripts directly, relative imports might work, but absolute is often safer for projects.
# Add the project root to sys.path if necessary, depending on how you structure/run the bot.
# project_root = os.path.dirname(__file__)
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

try:
    from data.db_manager import DatabaseManager
    from services.game_service import GameService
    from services.bet_service import BetService
    from services.admin_service import AdminService
    from services.analytics_service import AnalyticsService
    from services.user_service import UserService
    from services.voice_service import VoiceService
    from services.data_sync_service import DataSyncService
    # Import config vars directly if needed here, or access through os.getenv later
    # from config.database_mysql import MYSQL_HOST # Example
except ImportError as e:
    print(f"Import Error: {e}. Check that all service/data modules exist and Python can find them.")
    print("Ensure you are running Python from the 'betting-bot' directory or have set up PYTHONPATH.")
    sys.exit(1)

# --- Logging Setup ---
# Set up logging BEFORE initializing services that might log
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
log_format = os.getenv('LOG_FORMAT', '%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log_file = os.getenv('LOG_FILE', 'bot_activity.log') # Get log file from env or default

# Ensure logs directory exists
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout) # Log to console as well
    ]
)
# Configure discord logger level if desired (e.g., reduce noise)
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.WARNING) # Example: Only show warnings and above

logger = logging.getLogger(__name__) # Logger for this file

# --- Environment Variable Access ---
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
TEST_GUILD_ID_STR = os.getenv('TEST_GUILD_ID')
TEST_GUILD_ID = int(TEST_GUILD_ID_STR) if TEST_GUILD_ID_STR and TEST_GUILD_ID_STR.isdigit() else None
# Load other specific IDs if needed for command checks (like load_logos) - already done via load_dotenv

# --- Bot Token Check ---
if not BOT_TOKEN:
    logger.critical("FATAL: DISCORD_TOKEN not found in environment variables! Make sure it's in your .env file.")
    sys.exit("Missing DISCORD_TOKEN")

# --- Bot Definition ---
# Inherit from commands.Bot to easily use Cogs/Extensions
class BettingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True # Required for message content access if needed beyond commands
        intents.members = True # Required for member info (roles, display names) and guild events
        intents.reactions = True # Required for reaction events

        # Pass command_prefix - even for slash commands, it can be useful for hybrid commands or future features
        # Use a mention or a configurable prefix
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=intents)
        # Note: CommandTree is implicitly created and attached as self.tree

        # Initialize Managers and Services - pass self (the bot instance)
        self.db_manager = DatabaseManager()
        self.admin_service = AdminService(self, self.db_manager)
        self.analytics_service = AnalyticsService(self, self.db_manager)
        self.bet_service = BetService(self, self.db_manager) # Pass bot and db_manager
        self.game_service = GameService(self, self.db_manager)
        self.user_service = UserService(self, self.db_manager)
        self.voice_service = VoiceService(self, self.db_manager)
        # data_sync_service needs game_service instance
        self.data_sync_service = DataSyncService(self.game_service, self.db_manager)

        # Add services as attributes for easy access in Cogs (self.bot.<service_name>)
        # This is optional if you prefer passing them explicitly during Cog init,
        # but attaching them here is common practice.
        # (Already done by storing them above, e.g., self.admin_service)

    async def load_extensions(self):
        """Loads all cogs from the commands directory."""
        commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
        logger.info(f"Loading extensions from: {commands_dir}")
        loaded_count = 0
        failed_count = 0
        for filename in os.listdir(commands_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                # Construct the import path relative to the project structure
                # Assuming 'betting-bot' is the root package visible to Python
                extension = f'commands.{filename[:-3]}'
                try:
                    await self.load_extension(extension)
                    logger.info(f'Successfully loaded extension: {extension}')
                    loaded_count += 1
                except commands.ExtensionNotFound:
                    logger.error(f'Extension not found: {extension}. Ensure the file exists and path is correct.')
                    failed_count += 1
                except commands.ExtensionAlreadyLoaded:
                    logger.warning(f'Extension already loaded: {extension}')
                    # Optionally reload if needed during development: await self.reload_extension(extension)
                except commands.NoEntryPointError:
                    logger.error(f'Extension {extension} has no setup function.')
                    failed_count += 1
                except commands.ExtensionFailed as e:
                    # Log the original error that caused the load failure
                    logger.error(f'Extension {extension} failed to load: {e.__cause__}', exc_info=True)
                    failed_count += 1
                except Exception as e:
                    # Catch any other unexpected errors during loading
                    logger.error(f'Failed to load extension {extension}: {e}', exc_info=True)
                    failed_count += 1
        logger.info(f"Extension loading complete. Loaded: {loaded_count}, Failed: {failed_count}")
        if failed_count > 0:
            logger.warning("Some command extensions failed to load. Check logs above.")

    async def setup_hook(self):
        """Connect DB, setup commands via extensions, start services."""
        logger.info("Starting setup_hook...")
        try:
            # Connect DB Pool (Ensure DB is ready before loading commands/services that might use it)
            await self.db_manager.connect()
            if not self.db_manager._pool: # Check if pool connection failed
                 logger.critical("Database connection pool failed to initialize. Bot cannot continue.")
                 # Exit gracefully if DB fails to connect
                 await self.close() # Attempt graceful shutdown
                 sys.exit("Database connection failed.")
            logger.info("Database pool connected and schema initialized/verified.")

            # --- Load Command Extensions ---
            await self.load_extensions()

            # --- Sync Commands ---
            # Syncing here ensures commands are available ASAP after bot starts.
            # Decide strategy: Global only, Guild only (for testing), or Both.
            if TEST_GUILD_ID:
                logger.info(f"Syncing commands ONLY to test guild: {TEST_GUILD_ID}...")
                guild_obj = discord.Object(id=TEST_GUILD_ID)
                self.tree.copy_global_to(guild=guild_obj) # Copy global commands to the test guild
                await self.tree.sync(guild=guild_obj) # Sync specifically to the test guild
                # Optionally clear global commands if you ONLY want guild commands during testing
                # self.tree.clear_commands(guild=None)
                # await self.tree.sync(guild=None)
                logger.info(f"Commands synced to test guild {TEST_GUILD_ID}.")
            else:
                logger.info("Syncing global commands...")
                # Sync global commands. Propagation can take time (up to an hour).
                await self.tree.sync()
                logger.info("Global commands synced.")

            # --- Start Services ---
            # Start services AFTER commands are loaded and synced if services rely on bot being fully ready
            logger.info("Starting services...")
            # Use asyncio.gather for concurrent startup and better error handling
            service_starts = []
            if hasattr(self.game_service, 'start'): service_starts.append(self.game_service.start())
            if hasattr(self.bet_service, 'start'): service_starts.append(self.bet_service.start())
            if hasattr(self.user_service, 'start'): service_starts.append(self.user_service.start())
            if hasattr(self.voice_service, 'start'): service_starts.append(self.voice_service.start())
            if hasattr(self.data_sync_service, 'start'): service_starts.append(self.data_sync_service.start())

            if service_starts:
                 results = await asyncio.gather(*service_starts, return_exceptions=True)
                 for i, result in enumerate(results):
                      if isinstance(result, Exception):
                           # Log which service failed to start
                           logger.error(f"Error starting service {i}: {result}", exc_info=True)
                           # Decide if bot should continue if a service fails
            logger.info("Services startup initiated.")

            logger.info("Bot setup_hook completed successfully.")

        except Exception as e:
            logger.critical(f"CRITICAL ERROR during setup_hook: {e}", exc_info=True)
            # Attempt cleanup before exiting
            if self.db_manager:
                await self.db_manager.close()
            await super().close() # Close the Discord client connection
            sys.exit("Critical error during bot setup.") # Exit if setup fails

    async def on_ready(self):
        """Called when the bot is fully connected and ready."""
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        logger.info(f"discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Connected to {len(self.guilds)} guilds.")
        # Log guild names and IDs for debugging
        for guild in self.guilds:
            logger.debug(f"- {guild.name} ({guild.id})")
        logger.info(f"Latency: {self.latency*1000:.2f} ms")
        logger.info('------ Bot is Ready ------')

    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} ({guild.id})")
        # You might want to trigger command syncing for the new guild here,
        # especially if you are not using global commands primarily.
        # If TEST_GUILD_ID is set, this might only sync commands if it matches.
        # Consider your command deployment strategy.
        # Example:
        # if not TEST_GUILD_ID: # Sync if using global commands
        #     logger.info(f"Syncing commands for newly joined guild: {guild.id}")
        #     await self.tree.sync(guild=guild) # Syncing to one guild is faster

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction events to BetService."""
        # Ignore reactions from the bot itself
        if payload.user_id == self.user.id:
            return
        # Ensure bet_service is initialized before calling its methods
        if hasattr(self, 'bet_service') and hasattr(self.bet_service, 'on_raw_reaction_add'):
            # Run the handler in a separate task to avoid blocking the event loop
            asyncio.create_task(self.bet_service.on_raw_reaction_add(payload))
        else:
            logger.debug("BetService or reaction handler not ready during raw_reaction_add.")

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction removal events to BetService."""
        if payload.user_id == self.user.id:
            return
        if hasattr(self, 'bet_service') and hasattr(self.bet_service, 'on_raw_reaction_remove'):
            asyncio.create_task(self.bet_service.on_raw_reaction_remove(payload))
        else:
            logger.debug("BetService or reaction handler not ready during raw_reaction_remove.")

    async def close(self):
        """Gracefully close services and connections before shutdown."""
        logger.info("Initiating graceful shutdown...")
        try:
            # Stop services concurrently
            logger.info("Stopping services...")
            stop_tasks = []
            if hasattr(self, 'data_sync_service') and hasattr(self.data_sync_service, 'stop'): stop_tasks.append(self.data_sync_service.stop())
            if hasattr(self, 'voice_service') and hasattr(self.voice_service, 'stop'): stop_tasks.append(self.voice_service.stop())
            if hasattr(self, 'bet_service') and hasattr(self.bet_service, 'stop'): stop_tasks.append(self.bet_service.stop())
            if hasattr(self, 'game_service') and hasattr(self.game_service, 'stop'): stop_tasks.append(self.game_service.stop())
            if hasattr(self, 'user_service') and hasattr(self.user_service, 'stop'): stop_tasks.append(self.user_service.stop())

            if stop_tasks:
                results = await asyncio.gather(*stop_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Error stopping service {i}: {result}", exc_info=True) # Log full traceback
            logger.info("Services stopped.")

            # Close database pool
            if hasattr(self, 'db_manager') and self.db_manager:
                logger.info("Closing database connection pool...")
                await self.db_manager.close()
                logger.info("Database connection pool closed.")

        except Exception as e:
            logger.exception(f"Error during service/DB shutdown: {e}")
        finally:
            logger.info("Closing Discord client connection...")
            await super().close() # Call the parent class's close method
            logger.info("Bot shutdown complete.")

# --- Main Execution ---
def main():
    """Main function to create and run the bot."""
    bot = BettingBot()

    try:
        logger.info("Starting bot...")
        # log_handler=None prevents discord.py from configuring logging if we do it manually
        bot.run(BOT_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.critical("Login failed: Invalid Discord token provided in .env file.")
    except discord.PrivilegedIntentsRequired as e:
        logger.critical(f"Privileged Intents ({e.shard_id or 'default'}) are required but not enabled in the Discord Developer Portal for the bot application.")
        logger.critical("Please enable 'Presence Intent', 'Server Members Intent', and potentially 'Message Content Intent' under the 'Privileged Gateway Intents' section of your bot's settings page.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred while running the bot: {e}", exc_info=True)
    finally:
        # This block executes after bot.run() completes (i.e., bot disconnects/stops)
        # Cleanup should ideally be handled within bot.close()
        logger.info("Bot process finished.")
        # Consider if additional cleanup is needed *after* the loop closes


if __name__ == '__main__':
    # Optional: Add setup for UVLoop for potential performance improvements on Linux
    # try:
    #     import uvloop
    #     uvloop.install()
    #     print("Using uvloop for asyncio event loop.")
    # except ImportError:
    #     print("uvloop not installed, using default asyncio event loop.")
    #     pass

    main()
