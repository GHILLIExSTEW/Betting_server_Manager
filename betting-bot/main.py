# betting-bot/main.py

import os
import sys
import logging
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import time

# --- Path Setup ---
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print(f"WARNING: .env file not found at {dotenv_path}")

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
    print(f"Import Error: {e}. Check that all service/data modules exist and Python can find them.")
    print("Ensure you are running Python from the 'betting-bot' directory or have set up PYTHONPATH.")
    sys.exit(1)

# --- Logging Setup ---
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
log_format = os.getenv('LOG_FORMAT', '%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log_file = os.getenv('LOG_FILE', 'bot_activity.log')

os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# --- Environment Variable Access ---
BOT_TOKEN = os.getenv('DISCORD_TOKEN')

# --- Bot Token Check ---
if not BOT_TOKEN:
    logger.critical("FATAL: DISCORD_TOKEN not found in environment variables! Make sure it's in your .env file.")
    sys.exit("Missing DISCORD_TOKEN")

# --- Bot Definition ---
class BettingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True

        super().__init__(command_prefix=commands.when_mentioned_or("/"), intents=intents)
        logger.debug(f"Bot initialized with intents: {intents}")

        self.db_manager = DatabaseManager()
        self.admin_service = AdminService(self, self.db_manager)
        self.analytics_service = AnalyticsService(self, self.db_manager)
        self.bet_service = BetService(self, self.db_manager)
        self.game_service = GameService(self, self.db_manager)
        self.user_service = UserService(self, self.db_manager)
        self.voice_service = VoiceService(self, self.db_manager)
        self.data_sync_service = DataSyncService(self.game_service, self.db_manager)

    async def load_extensions(self):
        """Loads all cogs from the commands directory."""
        commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
        logger.info(f"Loading extensions from: {commands_dir}")
        loaded_count = 0
        failed_count = 0
        for filename in os.listdir(commands_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
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
                except commands.NoEntryPointError:
                    logger.error(f'Extension {extension} has no setup function.')
                    failed_count += 1
                except commands.ExtensionFailed as e:
                    logger.error(f'Extension {extension} failed to load: {e.__cause__}', exc_info=True)
                    failed_count += 1
                except Exception as e:
                    logger.error(f'Failed to load extension {extension}: {e}', exc_info=True)
                    failed_count += 1
        logger.info(f"Extension loading complete. Loaded: {loaded_count}, Failed: {failed_count}")
        if failed_count > 0:
            logger.warning("Some command extensions failed to load. Check logs above.")

    async def sync_commands_with_retry(self, guild: Optional[discord.Guild] = None, retries: int = 3, delay: int = 5):
        """Syncs commands with retries to handle Discord rate limits or network issues."""
        for attempt in range(1, retries + 1):
            try:
                if guild:
                    guild_obj = discord.Object(id=guild.id)
                    self.tree.copy_global_to(guild=guild_obj)
                    synced = await self.tree.sync(guild=guild_obj)
                    logger.info(f"Commands synced to guild {guild.id}: {[cmd.name for cmd in synced]}")
                else:
                    synced = await self.tree.sync()
                    logger.info(f"Global commands synced: {[cmd.name for cmd in synced]}")
                return True
            except Exception as e:
                logger.error(f"Sync attempt {attempt}/{retries} failed: {e}", exc_info=True)
                if attempt < retries:
                    logger.info(f"Retrying sync in {delay} seconds...")
                    await asyncio.sleep(delay)
        logger.error(f"Failed to sync commands after {retries} attempts.")
        return False

    async def setup_hook(self):
        """Connect DB, setup commands via extensions, start services."""
        logger.info("Starting setup_hook...")
        try:
            await self.db_manager.connect()
            if not self.db_manager._pool:
                logger.critical("Database connection pool failed to initialize. Bot cannot continue.")
                await self.close()
                sys.exit("Database connection failed.")
            logger.info("Database pool connected and schema initialized/verified.")

            await self.load_extensions()

            # Log all commands before syncing
            commands = [cmd.name for cmd in self.tree.get_commands()]
            logger.info(f"Registered commands: {commands}")

            # Clear command tree to prevent duplicates
            logger.debug("Clearing command tree before syncing")
            self.tree.clear_commands(guild=None)

            # Sync commands
            try:
                # Wait until bot is fully ready
                await self.wait_until_ready()
                # Sync globally
                await self.sync_commands_with_retry()
                # Sync to each guild
                for guild in self.guilds:
                    await self.sync_commands_with_retry(guild=guild)
            except Exception as e:
                logger.error(f"Failed to sync command tree: {e}", exc_info=True)

            logger.info("Starting services...")
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
                        logger.error(f"Error starting service {i}: {result}", exc_info=True)
            logger.info("Services startup initiated.")

            logger.info("Bot setup_hook completed successfully.")

        except Exception as e:
            logger.critical(f"CRITICAL ERROR during setup_hook: {e}", exc_info=True)
            if self.db_manager:
                await self.db_manager.close()
            await super().close()
            sys.exit("Critical error during bot setup.")

    async def on_ready(self):
        """Called when the bot is fully connected and ready."""
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        logger.info(f"discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Connected to {len(self.guilds)} guilds.")
        for guild in self.guilds:
            logger.debug(f"- {guild.name} ({guild.id})")
        logger.info(f"Latency: {self.latency*1000:.2f} ms")
        logger.info('------ Bot is Ready ------')

    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} ({guild.id})")
        await self.sync_commands_with_retry(guild=guild)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction events to BetService for bot-generated messages only."""
        logger.debug(f"Received raw reaction add: message_id={payload.message_id}, user_id={payload.user_id}")
        if payload.user_id == self.user.id:
            return
        if not hasattr(self, 'bet_service') or not hasattr(self.bet_service, 'pending_reactions'):
            logger.debug("BetService or pending_reactions not ready during raw_reaction_add")
            return
        if payload.message_id not in self.bet_service.pending_reactions:
            logger.debug(f"Ignoring reaction on non-bot message {payload.message_id}")
            return
        logger.debug(
            f"Processing reaction added: {payload.emoji} by user {payload.user_id} on bot message {payload.message_id} "
            f"in channel {payload.channel_id} (guild {payload.guild_id})"
        )
        if hasattr(self.bet_service, 'on_raw_reaction_add'):
            asyncio.create_task(self.bet_service.on_raw_reaction_add(payload))

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Pass raw reaction removal events to BetService for bot-generated messages only."""
        logger.debug(f"Received raw reaction remove: message_id={payload.message_id}, user_id={payload.user_id}")
        if payload.user_id == self.user.id:
            return
        if not hasattr(self, 'bet_service') or not hasattr(self.bet_service, 'pending_reactions'):
            logger.debug("BetService or pending_reactions not ready during raw_reaction_remove")
            return
        if payload.message_id not in self.bet_service.pending_reactions:
            logger.debug(f"Ignoring reaction removal on non-bot message {payload.message_id}")
            return
        logger.debug(
            f"Processing reaction removed: {payload.emoji} by user {payload.user_id} on bot message {payload.message_id} "
            f"in channel {payload.channel_id} (guild {payload.guild_id})"
        )
        if hasattr(self.bet_service, 'on_raw_reaction_remove'):
            asyncio.create_task(self.bet_service.on_raw_reaction_remove(payload))

    async def on_interaction(self, interaction: discord.Interaction):
        """Log all interactions for debugging."""
        logger.debug(
            f"Interaction received: type={interaction.type}, command={interaction.command.name if interaction.command else 'N/A'}, "
            f"user={interaction.user} (ID: {interaction.user.id}), guild={interaction.guild_id}, channel={interaction.channel_id}"
        )
        try:
            # Check permissions
            if interaction.guild:
                guild = interaction.guild
                bot_member = guild.get_member(self.user.id)
                if not bot_member:
                    logger.error(f"Bot not found in guild {guild.id}")
                    await interaction.response.send_message(
                        "❌ Bot is not a member of this guild.", ephemeral=True
                    )
                    return
                perms = interaction.channel.permissions_for(bot_member)
                if not perms.use_application_commands:
                    logger.warning(f"Bot lacks Use Application Commands permission in channel {interaction.channel_id}")
                    await interaction.response.send_message(
                        "❌ Bot lacks permission to use application commands in this channel.", ephemeral=True
                    )
                    return
                if not perms.send_messages:
                    logger.warning(f"Bot lacks Send Messages permission in channel {interaction.channel_id}")
                    await interaction.response.send_message(
                        "❌ Bot lacks permission to send messages in this channel.", ephemeral=True
                    )
                    return
            # Process the interaction
            logger.debug(f"Processing interaction for command: {interaction.command.name if interaction.command else 'N/A'}")
        except Exception as e:
            logger.error(f"Error processing interaction for user {interaction.user}: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred while processing the interaction: {str(e)}",
                    ephemeral=True
                )

    async def close(self):
        """Gracefully close services and connections before shutdown."""
        logger.info("Initiating graceful shutdown...")
        try:
            logger.info("Stopping services...")
            stop_tasks = []
            if hasattr(self, 'data_sync_service') and hasattr(self.data_sync_service, 'stop'): stop_tasks.append(self.data_sync_service.stop())
            if hasattr(self, 'voice_service') and hasattr(self.vice_service, 'stop'): stop_tasks.append(self.voice_service.stop())
            if hasattr(self, 'bet_service') and hasattr(self.bet_service, 'stop'): stop_tasks.append(self.bet_service.stop())
            if hasattr(self, 'game_service') and hasattr(self.game_service, 'stop'): stop_tasks.append(self.game_service.stop())
            if hasattr(self, 'user_service') and hasattr(self.user_service, 'stop'): stop_tasks.append(self.user_service.stop())

            if stop_tasks:
                results = await asyncio.gather(*stop_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Error stopping service {i}: {result}", exc_info=True)
            logger.info("Services stopped.")

            if hasattr(self, 'db_manager') and self.db_manager:
                logger.info("Closing database connection pool...")
                await self.db_manager.close()
                logger.info("Database connection pool closed.")

        except Exception as e:
            logger.exception(f"Error during service/DB shutdown: {e}")
        finally:
            logger.info("Closing Discord client connection...")
            await super().close()
            logger.info("Bot shutdown complete.")

# --- Manual Sync Command ---
class SyncCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Manually sync bot commands (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_command(self, interaction: discord.Interaction):
        logger.info(f"Manual sync initiated by {interaction.user} in guild {interaction.guild_id}")
        try:
            commands = [cmd.name for cmd in self.bot.tree.get_commands()]
            logger.debug(f"Commands to sync: {commands}")
            # Clear command tree
            logger.debug("Clearing command tree for sync")
            self.bot.tree.clear_commands(guild=None)
            for guild in self.bot.guilds:
                self.bot.tree.clear_commands(guild=discord.Object(id=guild.id))
            # Sync globally
            await self.bot.sync_commands_with_retry()
            # Sync to each guild
            for guild in self.bot.guilds:
                await self.bot.sync_commands_with_retry(guild=guild)
            await interaction.response.send_message("Commands synced successfully!", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}", exc_info=True)
            await interaction.response.send_message(f"Failed to sync commands: {e}", ephemeral=True)

async def setup_sync(bot: commands.Bot):
    await bot.add_cog(SyncCog(bot))
    logger.info("SyncCog loaded")

# --- Main Execution ---
def main():
    """Main function to create and run the bot."""
    bot = BettingBot()

    # Add SyncCog manually
    async def setup_bot():
        await setup_sync(bot)
        await bot.start(BOT_TOKEN)

    try:
        logger.info("Starting bot...")
        asyncio.run(setup_bot())
    except discord.LoginFailure:
        logger.critical("Login failed: Invalid Discord token provided in .env file.")
    except discord.PrivilegedIntentsRequired as e:
        logger.critical(f"Privileged Intents ({e.shard_id or 'default'}) are required but not enabled in the Discord Developer Portal for the bot application.")
        logger.critical("Please enable 'Presence Intent', 'Server Members Intent', and potentially 'Message Content Intent' under the 'Privileged Gateway Intents' section of your bot's settings page.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred while running the bot: {e}", exc_info=True)
    finally:
        logger.info("Bot process finished.")

if __name__ == '__main__':
    main()
