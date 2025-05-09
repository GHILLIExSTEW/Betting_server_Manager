# betting-bot/main.py

import os
import sys
import logging
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio
from typing import Optional

# --- Path Setup ---
# Determine the directory where main.py is located
# This assumes main.py is in the 'betting-bot' root directory.
# If it's nested (e.g., in a 'src' folder), this path needs adjustment.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
    print(f"Loaded environment variables from: {DOTENV_PATH}")
else:
    # Attempt to load from one level up if .env is in the parent of betting-bot
    PARENT_DOTENV_PATH = os.path.join(os.path.dirname(BASE_DIR), '.env')
    if os.path.exists(PARENT_DOTENV_PATH):
        load_dotenv(dotenv_path=PARENT_DOTENV_PATH)
        print(f"Loaded environment variables from: {PARENT_DOTENV_PATH}")
    else:
        print(f"WARNING: .env file not found at {DOTENV_PATH} or {PARENT_DOTENV_PATH}")


# --- Imports ---
# Ensure these imports match your project structure
# If 'data' and 'services' are subdirectories of 'betting-bot',
# and 'main.py' is in 'betting-bot', then direct imports should work if
# 'betting-bot' is in PYTHONPATH or you're running from 'betting-bot's parent.
# For more robust imports within a package, consider using relative imports
# if main.py is part of the 'betting_bot' package itself.
try:
    from data.db_manager import DatabaseManager
    from services.game_service import GameService
    from services.bet_service import BetService
    from services.admin_service import AdminService
    from services.analytics_service import AnalyticsService
    from services.user_service import UserService
    from services.voice_service import VoiceService
    from services.data_sync_service import DataSyncService
    # Ensure commands also has an __init__.py to be a package
    # Cogs will be loaded by name e.g., 'commands.admin'
except ImportError as e:
    print(f"Import Error: {e}. Check module paths and __init__.py files.")
    print(
        "Ensure you are running Python from the directory containing 'betting-bot' "
        "or have set up PYTHONPATH correctly."
    )
    sys.exit(1)

# --- Logging Setup ---
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
log_format = os.getenv(
    'LOG_FORMAT', '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
log_file_path = os.getenv('LOG_FILE', 'bot_activity.log')

# Ensure log directory exists if LOG_FILE includes a path
log_dir = os.path.dirname(log_file_path)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.WARNING) # Reduce discord.py's own verbosity

logger = logging.getLogger(__name__)

# --- Environment Variable Access ---
BOT_TOKEN = os.getenv('DISCORD_TOKEN')

# --- Bot Token Check ---
if not BOT_TOKEN:
    logger.critical(
        "FATAL: DISCORD_TOKEN not found in environment variables! "
        "Make sure it's in your .env file."
    )
    sys.exit("Missing DISCORD_TOKEN")

# --- Bot Definition ---
class BettingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True # Needed for on_raw_reaction_add/remove

        super().__init__(
            command_prefix=commands.when_mentioned_or("/"), intents=intents
        )
        logger.debug("Bot initialized with intents: %s", intents)

        # Initialize managers and services
        self.db_manager = DatabaseManager()
        self.admin_service = AdminService(self, self.db_manager)
        self.analytics_service = AnalyticsService(self, self.db_manager)
        self.bet_service = BetService(self, self.db_manager)
        self.game_service = GameService(self, self.db_manager)
        self.user_service = UserService(self, self.db_manager)
        self.voice_service = VoiceService(self, self.db_manager)
        self.data_sync_service = DataSyncService(
            self.game_service, self.db_manager
        )

    async def load_extensions(self):
        """Loads all cogs from the commands directory."""
        # Assuming 'commands' is a sub-directory of where main.py is
        commands_dir = os.path.join(BASE_DIR, 'commands')
        logger.info("Loading extensions from: %s", commands_dir)
        loaded_count = 0
        failed_count = 0

        # List of actual cog files (those containing a setup function)
        # Exclude utility modules like straight_betting.py or parlay_betting.py
        # if they don't have their own setup() for cogs.
        cog_files = [
            'admin.py',
            'betting.py', # This is the main cog for betting commands
            'load_logos.py',
            'remove_user.py',
            'setid.py',
            'stats.py',
            # Add other actual cog files here
        ]

        for filename in cog_files:
            # Check if file exists, then try to load
            if os.path.exists(os.path.join(commands_dir, filename)):
                extension = f'commands.{filename[:-3]}'
                try:
                    await self.load_extension(extension)
                    logger.info('Successfully loaded extension: %s', extension)
                    loaded_count += 1
                except commands.ExtensionNotFound:
                    logger.error(
                        "Extension not found: %s. Check path/name.", extension
                    )
                    failed_count += 1
                except commands.ExtensionAlreadyLoaded:
                    logger.warning("Extension already loaded: %s", extension)
                except commands.NoEntryPointError:
                    logger.error("Extension %s has no setup function.", extension)
                    failed_count += 1
                except commands.ExtensionFailed as e:
                    logger.error(
                        "Extension %s failed to load: %s", extension, e.__cause__,
                        exc_info=True
                    )
                    failed_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to load extension %s: %s", extension, e,
                        exc_info=True
                    )
                    failed_count += 1
            else:
                logger.warning("Cog file %s not found in %s, skipping.", filename, commands_dir)


        logger.info(
            "Extension loading complete. Loaded: %d, Failed: %d",
            loaded_count, failed_count
        )
        if failed_count > 0:
            logger.warning("Some command extensions failed to load. Check logs.")

    async def sync_commands_with_retry(
        self, guild: Optional[discord.Guild] = None,
        retries: int = 3, delay: int = 5
    ):
        """Syncs commands with retries."""
        for attempt in range(1, retries + 1):
            try:
                if guild:
                    guild_obj = discord.Object(id=guild.id)
                    self.tree.copy_global_to(guild=guild_obj)
                    synced = await self.tree.sync(guild=guild_obj)
                    logger.info(
                        "Commands synced to guild %s: %s",
                        guild.id, [cmd.name for cmd in synced]
                    )
                else:
                    synced = await self.tree.sync()
                    logger.info(
                        "Global commands synced: %s", [cmd.name for cmd in synced]
                    )
                return True
            except discord.HTTPException as e:
                logger.error(
                    "Sync attempt %d/%d failed: %s", attempt, retries, e,
                    exc_info=True
                )
                if attempt < retries:
                    logger.info("Retrying sync in %d seconds...", delay)
                    await asyncio.sleep(delay)
        logger.error("Failed to sync commands after %d attempts.", retries)
        return False

    async def setup_hook(self):
        """Connect DB, setup commands via extensions, start services."""
        logger.info("Starting setup_hook...")
        try:
            await self.db_manager.connect()
            if not self.db_manager._pool: # pylint: disable=protected-access
                logger.critical(
                    "Database connection pool failed to initialize. Bot cannot continue."
                )
                await self.close()
                sys.exit("Database connection failed.")
            logger.info("DB pool connected and schema initialized/verified.")

            await self.load_extensions()

            commands_list = [cmd.name for cmd in self.tree.get_commands()]
            logger.info("Registered commands before syncing: %s", commands_list)

            logger.info("Starting services...")
            service_starts = [
                self.admin_service.start(),
                self.analytics_service.start(), # Added analytics service start
                self.bet_service.start(),
                self.game_service.start(),
                self.user_service.start(),
                self.voice_service.start(),
                self.data_sync_service.start(),
            ]

            results = await asyncio.gather(*service_starts, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Log which service failed if possible, by correlating index with service_starts order
                    service_name = service_starts[i].__self__.__class__.__name__ if hasattr(service_starts[i], '__self__') else f"Service {i}"
                    logger.error(
                        "Error starting %s: %s", service_name, result, exc_info=True
                    )
            logger.info("Services startup initiated.")
            logger.info("Bot setup_hook completed successfully.")

        except Exception as e:
            logger.critical("CRITICAL ERROR during setup_hook: %s", e, exc_info=True)
            if self.db_manager:
                await self.db_manager.close()
            await super().close() # Call parent's close
            sys.exit("Critical error during bot setup.")

    async def on_ready(self):
        """Called when the bot is fully connected and ready."""
        logger.info('Logged in as %s (%s)', self.user.name, self.user.id)
        logger.info("discord.py API version: %s", discord.__version__)
        logger.info("Python version: %s", sys.version)
        logger.info("Connected to %d guilds.", len(self.guilds))
        for guild in self.guilds:
            logger.debug("- %s (%s)", guild.name, guild.id)
        logger.info("Latency: %.2f ms", self.latency * 1000)

        try:
            await self.sync_commands_with_retry() # Sync globally first
            # Sync to each guild with a small delay
            for guild in self.guilds:
                await self.sync_commands_with_retry(guild=guild)
                await asyncio.sleep(1) # Rate limit prevention
            commands_list = [cmd.name for cmd in self.tree.get_commands()]
            logger.info("Commands available after sync: %s", commands_list)
        except Exception as e:
            logger.error("Failed to sync command tree: %s", e, exc_info=True)

        logger.info('------ Bot is Ready ------')

    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info("Joined new guild: %s (%s)", guild.name, guild.id)
        await self.sync_commands_with_retry(guild=guild)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction events to BetService."""
        if payload.user_id == self.user.id:
            return
        if hasattr(self, 'bet_service') and \
           hasattr(self.bet_service, 'pending_reactions') and \
           payload.message_id in self.bet_service.pending_reactions:
            logger.debug(
                "Processing reaction add: %s by %s on bot message %s in channel %s (guild %s)",
                payload.emoji, payload.user_id, payload.message_id,
                payload.channel_id, payload.guild_id
            )
            if hasattr(self.bet_service, 'on_raw_reaction_add'):
                asyncio.create_task(self.bet_service.on_raw_reaction_add(payload))
        # else:
            # logger.debug("Ignoring reaction on non-tracked message %s", payload.message_id)


    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction removal events to BetService."""
        if payload.user_id == self.user.id:
            return
        if hasattr(self, 'bet_service') and \
           hasattr(self.bet_service, 'pending_reactions') and \
           payload.message_id in self.bet_service.pending_reactions:
            logger.debug(
                "Processing reaction remove: %s by %s on bot message %s",
                payload.emoji, payload.user_id, payload.message_id
            )
            if hasattr(self.bet_service, 'on_raw_reaction_remove'):
                asyncio.create_task(self.bet_service.on_raw_reaction_remove(payload))

    async def on_interaction(self, interaction: discord.Interaction):
        """Log all interactions."""
        command_name = interaction.command.name if interaction.command else 'N/A'
        logger.debug(
            "Interaction: type=%s, cmd=%s, user=%s(ID:%s), guild=%s, ch=%s",
            interaction.type, command_name, interaction.user,
            interaction.user.id, interaction.guild_id, interaction.channel_id
        )
        # Default interaction processing is handled by the library
        # await self.process_application_commands(interaction) # This is done by the lib

    async def close(self):
        """Gracefully close services and connections before shutdown."""
        logger.info("Initiating graceful shutdown...")
        try:
            logger.info("Stopping services...")
            stop_tasks = [
                self.data_sync_service.stop(),
                self.voice_service.stop(),
                self.bet_service.stop(),
                self.game_service.stop(),
                self.user_service.stop(),
                self.admin_service.stop() # Ensure admin service also has stop
            ]
            results = await asyncio.gather(*stop_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    service_name = stop_tasks[i].__self__.__class__.__name__ if hasattr(stop_tasks[i], '__self__') else f"Service {i}"
                    logger.error(
                        "Error stopping %s: %s", service_name, result, exc_info=True
                    )
            logger.info("Services stopped.")

            if hasattr(self, 'db_manager') and self.db_manager:
                logger.info("Closing database connection pool...")
                await self.db_manager.close()
                logger.info("Database connection pool closed.")

        except Exception as e:
            logger.exception("Error during service/DB shutdown: %s", e)
        finally:
            logger.info("Closing Discord client connection...")
            await super().close()
            logger.info("Bot shutdown complete.")


# --- Manual Sync Command (as a Cog) ---
class SyncCog(commands.Cog):
    def __init__(self, bot: BettingBot): # Type hint bot as BettingBot
        self.bot = bot

    @app_commands.command(
        name="sync", description="Manually sync bot commands (admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_command(self, interaction: discord.Interaction):
        logger.info(
            "Manual sync initiated by %s in guild %s",
            interaction.user, interaction.guild_id
        )
        try:
            await interaction.response.defer(ephemeral=True)
            commands_list = [cmd.name for cmd in self.bot.tree.get_commands()]
            logger.debug("Commands to sync: %s", commands_list)

            await self.bot.sync_commands_with_retry() # Global sync
            for guild in self.bot.guilds: # Sync to all guilds
                await self.bot.sync_commands_with_retry(guild=guild)
                await asyncio.sleep(0.5) # Small delay

            await interaction.followup.send(
                "Commands synced successfully!", ephemeral=True
            )
        except Exception as e:
            logger.error("Failed to sync commands: %s", e, exc_info=True)
            if not interaction.response.is_done():
                 await interaction.response.send_message(f"Failed to sync commands: {e}",ephemeral=True)
            else:
                 await interaction.followup.send(f"Failed to sync commands: {e}",ephemeral=True)


async def setup_sync_cog(bot: BettingBot): # Type hint bot
    """Setup function to register the SyncCog."""
    await bot.add_cog(SyncCog(bot))
    logger.info("SyncCog loaded")


# --- Main Execution ---
def main():
    """Main function to create and run the bot."""
    bot = BettingBot()

    async def run_bot():
        await setup_sync_cog(bot) # Load the SyncCog
        await bot.start(BOT_TOKEN)

    try:
        logger.info("Starting bot...")
        asyncio.run(run_bot())
    except discord.LoginFailure:
        logger.critical(
            "Login failed: Invalid Discord token provided in .env file."
        )
    except discord.PrivilegedIntentsRequired as e:
        shard_id_info = f" (Shard ID: {e.shard_id})" if e.shard_id else ""
        logger.critical(
            "Privileged Intents%s are required but not enabled in the Discord Developer Portal.",
            shard_id_info
        )
        logger.critical(
            "Enable 'Presence Intent', 'Server Members Intent', and 'Message Content Intent'."
        )
    except Exception as e:
        logger.critical(
            "An unexpected error occurred while running the bot: %s", e,
            exc_info=True
        )
    finally:
        logger.info("Bot process finished.")


if __name__ == '__main__':
    main()
