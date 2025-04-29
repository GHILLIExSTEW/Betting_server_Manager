# betting-bot/main.py

import os
import sys
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# --- Path Setup ---
# Removed sys.path manipulation as relative imports from main.py should work
# when run from within the betting-bot directory.
# --- End Path Setup ---

# Load environment variables from .env file (assuming it's one level up from main.py)
# If .env is in the same directory as main.py, use: load_dotenv()
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)


# --- Imports (Relative to betting-bot directory) ---
try:
    from data.db_manager import DatabaseManager
    from services.game_service import GameService
    from services.bet_service import BetService
    from services.admin_service import AdminService
    from services.analytics_service import AnalyticsService
    from services.user_service import UserService
    from services.voice_service import VoiceService
    from services.data_sync_service import DataSyncService
    # Import Command Setup (Choose ONE loading strategy)
    # from commands import CommandManager
except ImportError as e:
     print(f"Import Error: {e}. Ensure you are running from the 'betting-bot' directory "
           "or the parent directory, and all necessary __init__.py files exist.")
     sys.exit(1)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    # filename='logs/betting_bot.log' # Uncomment to log to file
)
logger = logging.getLogger(__name__)

# --- Environment Variable Access ---
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
TEST_GUILD_ID_STR = os.getenv('TEST_GUILD_ID')
TEST_GUILD_ID = int(TEST_GUILD_ID_STR) if TEST_GUILD_ID_STR and TEST_GUILD_ID_STR.isdigit() else None

# --- Bot Token Check ---
if not BOT_TOKEN:
    logger.error("FATAL: DISCORD_TOKEN not found in environment variables! Make sure it's in your .env file.")
    sys.exit("Missing DISCORD_TOKEN")

# --- Bot Definition ---
class BettingBot(commands.AutoShardedBot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True

        # Get prefix from settings or use default
        # from config.settings import COMMAND_PREFIX # Example import
        super().__init__(
            command_prefix='!', # Replace with COMMAND_PREFIX if loaded
            intents=intents,
            help_command=None # Disable default help command
        )

        # --- Initialize Managers and Services ---
        self.db_manager = DatabaseManager() # Instantiate ONCE

        # Pass self (bot instance) and db_manager to services
        self.game_service = GameService(self, self.db_manager)
        self.bet_service = BetService(self, self.db_manager)
        self.admin_service = AdminService(self, self.db_manager)
        self.analytics_service = AnalyticsService(self, self.db_manager)
        self.user_service = UserService(self, self.db_manager)
        self.voice_service = VoiceService(self, self.db_manager)
        # DataSyncService needs GameService instance too
        self.data_sync_service = DataSyncService(self.game_service, self.db_manager)

        # If using CommandManager approach:
        # self.command_manager = CommandManager(self)


    async def setup_hook(self):
        """Connect DB, setup commands, start services."""
        try:
            # Connect DB Pool
            await self.db_manager.connect()
            logger.info("Database pool connected.")

            # --- Load Command Cogs ---
            # Construct absolute path to the commands directory
            main_file_dir = os.path.dirname(os.path.abspath(__file__))
            # Assumes 'commands' directory is in the same directory as main.py
            commands_dir_path = os.path.join(main_file_dir, "commands")

            logger.info(f"Attempting to load command cogs from: {commands_dir_path}")

            if not os.path.isdir(commands_dir_path):
                 logger.error(f"Commands directory not found at: {commands_dir_path}")
                 # Consider raising an error if commands are essential for startup
                 # raise FileNotFoundError(f"Commands directory not found at: {commands_dir_path}")
            else:
                # Iterate through files in the determined commands directory
                for filename in os.listdir(commands_dir_path):
                    if filename.endswith('.py') and not filename.startswith('__'):
                        extension_name = filename[:-3]
                        try:
                            # Use the package notation 'commands.filename' for loading
                            # Assumes 'commands' is a package relative to where main.py is
                            await self.load_extension(f'commands.{extension_name}')
                            logger.info(f'Loaded command cog: {extension_name}')
                        # Catch specific extension errors for better debugging
                        except commands.ExtensionNotFound:
                            logger.error(f'Extension not found: commands.{extension_name}')
                        except commands.ExtensionAlreadyLoaded:
                            logger.warning(f'Extension already loaded: commands.{extension_name}')
                        except commands.NoEntryPointError:
                            logger.error(f'Extension has no setup function: commands.{extension_name}')
                        except commands.ExtensionFailed as ef:
                             logger.error(f'Extension setup failed for commands.{extension_name}: {ef.original}', exc_info=True)
                        except Exception as e:
                            logger.error(f'Failed to load command cog commands.{extension_name}: {e}', exc_info=True) # Log full traceback

            logger.info("Command loading process completed.")


            # Start services AFTER DB is connected
            logger.info("Starting services...")
            if hasattr(self.game_service, 'start'): await self.game_service.start()
            if hasattr(self.bet_service, 'start'): await self.bet_service.start()
            if hasattr(self.user_service, 'start'): await self.user_service.start()
            if hasattr(self.voice_service, 'start'): await self.voice_service.start()
            if hasattr(self.data_sync_service, 'start'): await self.data_sync_service.start()
            # Add start calls for AdminService, AnalyticsService if they have start methods
            logger.info("Services started.")

            # --- Initial Command Sync ---
            # Sync global commands first
            try:
                 synced_global = await self.tree.sync()
                 logger.info(f"Synced {len(synced_global)} global command(s).")
            except Exception as e:
                 logger.error(f"Global command sync failed: {e}")

            # Sync test guild commands if ID is set
            if TEST_GUILD_ID:
                try:
                    guild_obj = discord.Object(id=TEST_GUILD_ID)
                    await self.tree.sync(guild=guild_obj)
                    logger.info(f"Commands synced to test guild {TEST_GUILD_ID}")
                except Exception as e:
                    logger.error(f"Test guild command sync failed for ID {TEST_GUILD_ID}: {e}")
            # --- End Initial Command Sync ---


            logger.info("Bot setup hook completed successfully.")

        except Exception as e:
            logger.exception(f"CRITICAL ERROR during setup_hook: {e}")
            if self.db_manager:
                await self.db_manager.close()
            raise


    async def on_ready(self):
        """Called when the bot is fully connected and ready."""
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        logger.info(f"Connected to {len(self.guilds)} guilds.")
        logger.info('------ Bot is Ready ------')


    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} ({guild.id})")
        try:
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands for new guild {guild.name}")
        except Exception as e:
            logger.error(f"Error syncing commands for new guild {guild.name}: {e}")


    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction events to BetService."""
        if payload.user_id == self.user.id:
            return
        if hasattr(self.bet_service, 'on_raw_reaction_add'):
            asyncio.create_task(self.bet_service.on_raw_reaction_add(payload))


    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction removal events to BetService."""
        if payload.user_id == self.user.id:
            return
        if hasattr(self.bet_service, 'on_raw_reaction_remove'):
             asyncio.create_task(self.bet_service.on_raw_reaction_remove(payload))


    async def close(self):
        """Gracefully close services and connections before shutdown."""
        logger.info("Shutting down bot...")
        try:
            # Stop services first
            logger.info("Stopping services...")
            if hasattr(self.data_sync_service, 'stop'): await self.data_sync_service.stop()
            if hasattr(self.voice_service, 'stop'): await self.voice_service.stop()
            if hasattr(self.bet_service, 'stop'): await self.bet_service.stop()
            if hasattr(self.game_service, 'stop'): await self.game_service.stop()
            if hasattr(self.user_service, 'stop'): await self.user_service.stop()
            # Add stop calls for AdminService, AnalyticsService if they have stop methods
            logger.info("Services stopped.")

            # Close DB pool
            if self.db_manager:
                logger.info("Closing database connection pool...")
                await self.db_manager.close()
                logger.info("Database connection pool closed.")

        except Exception as e:
            logger.exception(f"Error during service/DB shutdown: {e}")
        finally:
            logger.info("Closing Discord client connection...")
            await super().close()
            logger.info("Bot shutdown complete.")

# --- Main Execution ---
def main():
    """Main function to run the bot."""
    bot = BettingBot()

    try:
        logger.info("Starting bot...")
        # Run the bot using the token from environment variables
        bot.run(BOT_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("Login failed: Invalid Discord token provided in .env file.")
    except Exception as e:
        logger.exception(f"An error occurred while running the bot: {e}")
    finally:
        # Ensure cleanup happens even on unexpected exit
        logger.info("Bot process finished.")


if __name__ == '__main__':
    main()
