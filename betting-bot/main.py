# betting-bot/main.py

import os
import sys
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# Load environment variables from .env file (assuming it's one level up from main.py)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)
# .env is in the SAME directory as main.py, just use: load_dotenv()

# --- Imports (Relative to betting-bot directory) ---
from data.db_manager import DatabaseManager # Corrected import
from services.game_service import GameService # Corrected import
from services.bet_service import BetService # Corrected import
from services.admin_service import AdminService # Corrected import
from services.analytics_service import AnalyticsService # Corrected import
from services.user_service import UserService # Corrected import
from services.voice_service import VoiceService # Corrected import
from services.data_sync_service import DataSyncService # Corrected import
from commands.admin import setup as setup_admin_cmds # Corrected import

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

            # --- Load Commands ---
            # Choose ONE strategy:
            # Option A: CommandManager
            # await self.command_manager.register_commands()
            # Option B: Manual setup (less ideal)
            # await setup_admin_cmds(self.tree) # Example
            # ... load other commands ...
            # Ensure your chosen command loading method (e.g., loading cogs) happens here.
            # Example using load_extension for cogs placed in 'commands' folder:
            commands_dir = "commands" # Assuming commands are cogs
            for filename in os.listdir(f'./{commands_dir}'): # Use relative path
                if filename.endswith('.py') and not filename.startswith('__'):
                    try:
                        await self.load_extension(f'{commands_dir}.{filename[:-3]}')
                        logger.info(f'Loaded command cog: {filename[:-3]}')
                    except Exception as e:
                        logger.error(f'Failed to load command cog {filename[:-3]}: {e}')

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
            # Use create_task to avoid blocking the event loop if reaction handling is slow
            asyncio.create_task(self.bet_service.on_raw_reaction_add(payload))


    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction removal events to BetService."""
        if payload.user_id == self.user.id:
            return
        if hasattr(self.bet_service, 'on_raw_reaction_remove'):
             # Use create_task to avoid blocking the event loop
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
        # Using bot.close() within the main loop's exception handling
        # might be tricky if the loop is already broken.
        # Rely on KeyboardInterrupt or system signals for graceful shutdown via bot.close().
        logger.info("Bot process finished.")


if __name__ == '__main__':
    main()
