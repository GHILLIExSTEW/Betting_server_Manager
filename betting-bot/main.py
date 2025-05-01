import os
import sys
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# --- Path Setup ---
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')  # .env in same directory as main.py
load_dotenv(dotenv_path=dotenv_path)

# --- Imports ---
try:
    from data.db_manager import DatabaseManager
    from services.game_service import GameService
    from services.bet_service import BetService
    from services.admin_service import AdminService
    from services.analytics_service import AnalyticsService
    from services.user_service import UserService
    from services.voice_service import VoiceService
    from services.data_sync_service import DataSyncService
except ImportError as e:
    print(f"Import Error: {e}. Ensure you are running from the 'betting-bot' directory.")
    sys.exit(1)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
class BettingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        # Initialize Managers and Services
        self.db_manager = DatabaseManager()
        self.game_service = GameService(self, self.db_manager)
        self.bet_service = BetService(self, self.db_manager)
        self.admin_service = AdminService(self, self.db_manager)
        self.analytics_service = AnalyticsService(self, self.db_manager)
        self.user_service = UserService(self, self.db_manager)
        self.voice_service = VoiceService(self, self.db_manager)
        self.data_sync_service = DataSyncService(self.game_service, self.db_manager)

    async def setup_hook(self):
        """Connect DB, setup commands, start services."""
        try:
            # Connect DB Pool
            await self.db_manager.connect()
            logger.info("Database pool connected.")

            # Load Command Cogs
            main_file_dir = os.path.dirname(os.path.abspath(__file__))
            commands_dir_path = os.path.join(main_file_dir, "commands")
            logger.info(f"Attempting to load command cogs from: {commands_dir_path}")

            if not os.path.isdir(commands_dir_path):
                logger.error(f"Commands directory not found at: {commands_dir_path}")
            else:
                for filename in os.listdir(commands_dir_path):
                    if filename.endswith('.py') and not filename.startswith('__'):
                        extension_name = filename[:-3]
                        try:
                            await self.load_extension(f'commands.{extension_name}')
                            logger.info(f'Loaded command cog: {extension_name}')
                        except commands.ExtensionNotFound:
                            logger.error(f'Extension not found: commands.{extension_name}')
                        except commands.ExtensionAlreadyLoaded:
                            logger.warning(f'Extension already loaded: commands.{extension_name}')
                        except commands.NoEntryPointError:
                            logger.error(f'Extension has no setup function: commands.{extension_name}')
                        except commands.ExtensionFailed as ef:
                            logger.error(f'Extension setup failed for commands.{extension_name}: {ef.original}', exc_info=True)
                        except Exception as e:
                            logger.error(f'Failed to load command cog commands.{extension_name}: {e}', exc_info=True)

            logger.info("Command loading process completed.")

            # Start Services
            logger.info("Starting services...")
            if hasattr(self.game_service, 'start'): await self.game_service.start()
            if hasattr(self.bet_service, 'start'): await self.bet_service.start()
            if hasattr(self.user_service, 'start'): await self.user_service.start()
            if hasattr(self.voice_service, 'start'): await self.voice_service.start()
            if hasattr(self.data_sync_service, 'start'): await self.data_sync_service.start()
            logger.info("Services started.")

            # Sync Commands (Test Guild Only)
            if TEST_GUILD_ID:
                try:
                    guild_obj = discord.Object(id=TEST_GUILD_ID)
                    await self.tree.sync(guild=guild_obj)
                    logger.info(f"Commands synced to test guild {TEST_GUILD_ID}")
                except Exception as e:
                    logger.error(f"Test guild command sync failed for ID {TEST_GUILD_ID}: {e}")
            else:
                logger.warning("TEST_GUILD_ID not set, skipping guild command sync.")

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
        # Commands are already synced in setup_hook, no need to sync again

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
            logger.info("Stopping services...")
            if hasattr(self.data_sync_service, 'stop'): await self.data_sync_service.stop()
            if hasattr(self.voice_service, 'stop'): await self.voice_service.stop()
            if hasattr(self.bet_service, 'stop'): await self.bet_service.stop()
            if hasattr(self.game_service, 'stop'): await self.game_service.stop()
            if hasattr(self.user_service, 'stop'): await self.user_service.stop()
            logger.info("Services stopped.")

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
        bot.run(BOT_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("Login failed: Invalid Discord token provided in .env file.")
    except Exception as e:
        logger.exception(f"An error occurred while running the bot: {e}")
    finally:
        logger.info("Bot process finished.")

if __name__ == '__main__':
    main()
