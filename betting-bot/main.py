# betting-bot/main.py

import os
import sys
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio # Import asyncio for potential cleanup

# --- Path Setup ---
# Add the current directory's parent to the Python path to find packages
# (Assumes main.py is inside 'betting-bot' and 'betting-bot' is inside your project root)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Get the directory containing 'betting-bot'
sys.path.insert(0, project_root)
# --- End Path Setup ---

# Load environment variables from .env file in the project root FIRST
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))

# --- Imports (After path setup and dotenv) ---
# Import your specific DatabaseManager (assuming the asyncpg version)
from betting_bot.data.db_manager import DatabaseManager # Adjusted import path
# Import Services
from betting_bot.services.game_service import GameService
from betting_bot.services.bet_service import BetService
from betting_bot.services.admin_service import AdminService
from betting_bot.services.analytics_service import AnalyticsService
from betting_bot.services.user_service import UserService
from betting_bot.services.voice_service import VoiceService
from betting_bot.services.data_sync_service import DataSyncService
# Import Command Setup (choose one command loading strategy)
# Option A: If using commands/__init__.py CommandManager
# from betting_bot.commands import CommandManager
# Option B: If using setup functions directly (less organized)
# from betting_bot.commands.admin import setup as setup_admin_cmds # Example

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    # Consider adding file logging from config/settings.py if desired
    # filename=LOG_FILE
)
logger = logging.getLogger(__name__)

# --- Environment Variable Access ---
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
TEST_GUILD_ID_STR = os.getenv('TEST_GUILD_ID') # Get this if you use it for syncing
TEST_GUILD_ID = int(TEST_GUILD_ID_STR) if TEST_GUILD_ID_STR and TEST_GUILD_ID_STR.isdigit() else None

# --- Bot Token Check ---
if not BOT_TOKEN:
    logger.error("FATAL: DISCORD_TOKEN not found in environment variables! Make sure it's in your .env file.")
    sys.exit("Missing DISCORD_TOKEN")

# --- Bot Definition ---
class BettingBot(commands.AutoShardedBot): # Use AutoShardedBot for better scaling
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True # Required for potential message commands/interactions
        intents.members = True # Often needed for user lookups/roles
        intents.reactions = True # Needed for bet resolution via reactions

        # Get prefix from settings or use default
        # from betting_bot.config.settings import COMMAND_PREFIX # Example import
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

            # --- Load Commands ---
            # Choose ONE strategy:
            # Option A: CommandManager
            # await self.command_manager.register_commands()
            # Option B: Manual setup (less ideal)
            # await setup_admin_cmds(self.tree) # Example
            # ... load other commands ...
            # For simplicity, let's assume commands might be loaded via cogs or another method
            # If you use `commands/__init__.py`'s CommandManager, uncomment the line above.
            # Make sure your chosen command loading happens *here*.
            logger.info("Command setup/loading placeholder - ensure your method is called here.")


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
            logger.exception(f"CRITICAL ERROR during setup_hook: {e}") # Use logger.exception to include traceback
            # Ensure pool is closed if setup fails partially
            if self.db_manager:
                await self.db_manager.close()
            # Optionally shutdown the bot process if setup fails critically
            # await self.close()
            # sys.exit("Bot setup failed.")
            raise # Re-raise to indicate critical failure


    async def on_ready(self):
        """Called when the bot is fully connected and ready."""
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        logger.info(f"Connected to {len(self.guilds)} guilds.")
        logger.info('------ Bot is Ready ------')


    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} ({guild.id})")
        # Optionally sync commands to the new guild immediately
        # Or handle setup via an admin command later
        try:
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands for new guild {guild.name}")
        except Exception as e:
            logger.error(f"Error syncing commands for new guild {guild.name}: {e}")
        # Optionally send a welcome message or log guild join to DB


    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction events to BetService."""
        # Ignore reactions from the bot itself
        if payload.user_id == self.user.id:
            return
        # Let BetService handle the logic
        if hasattr(self.bet_service, 'on_raw_reaction_add'):
            await self.bet_service.on_raw_reaction_add(payload)


    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction removal events to BetService."""
         # Ignore reactions from the bot itself
        if payload.user_id == self.user.id:
            return
        # Let BetService handle the logic
        if hasattr(self.bet_service, 'on_raw_reaction_remove'):
            await self.bet_service.on_raw_reaction_remove(payload)


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
        bot.run(BOT_TOKEN, log_handler=None) # Disable default discord.py logging handler if using basicConfig
    except discord.LoginFailure:
        logger.error("Login failed: Invalid Discord token provided in .env file.")
    except Exception as e:
        logger.exception(f"An error occurred while running the bot: {e}")
    finally:
        # Ensure cleanup happens even on unexpected exit, though bot.close() is preferred
        # This might run into issues if the loop isn't running anymore
        # asyncio.run(bot.close()) # May not work reliably here
        logger.info("Bot process finished.")


if __name__ == '__main__':
    main()
