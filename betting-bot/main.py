import os
import sys
import logging
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio
from typing import Optional
from data.db_manager import DatabaseManager
from services.admin_service import AdminService
from services.analytics_service import AnalyticsService
from services.bet_service import BetService
from services.game_service import GameService
from services.user_service import UserService
from services.voice_service import VoiceService
from services.data_sync_service import DataSyncService
from utils.image_generator import BetSlipGenerator
from commands.sync_cog import setup_sync_cog

# --- Path Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
    print(f"Loaded environment variables from: {DOTENV_PATH}")
else:
    PARENT_DOTENV_PATH = os.path.join(os.path.dirname(BASE_DIR), '.env')
    if os.path.exists(PARENT_DOTENV_PATH):
        load_dotenv(dotenv_path=PARENT_DOTENV_PATH)
        print(f"Loaded environment variables from: {PARENT_DOTENV_PATH}")
    else:
        print(f"WARNING: .env file not found at {DOTENV_PATH} or {PARENT_DOTENV_PATH}")

# --- Logging Setup ---
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
log_format = os.getenv('LOG_FORMAT', '%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log_file_path = os.getenv('LOG_FILE', 'bot_activity.log')

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
discord_logger.setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Environment Variable Access ---
BOT_TOKEN = os.getenv('DISCORD_TOKEN')

if not BOT_TOKEN:
    logger.critical("FATAL: DISCORD_TOKEN not found in environment variables!")
    sys.exit("Missing DISCORD_TOKEN")

# --- Bot Definition ---
class BettingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix=commands.when_mentioned_or("/"), intents=intents)
        self.db_manager = DatabaseManager()
        self.admin_service = AdminService(self, self.db_manager)
        self.analytics_service = AnalyticsService(self, self.db_manager)
        self.bet_service = BetService(self, self.db_manager)
        self.game_service = GameService(self, self.db_manager)
        self.user_service = UserService(self, self.db_manager)
        self.voice_service = VoiceService(self, self.db_manager)
        self.data_sync_service = DataSyncService(self.game_service, self.db_manager)
        self.bet_slip_generators = {}

    async def get_bet_slip_generator(self, guild_id: int) -> BetSlipGenerator:
        if guild_id not in self.bet_slip_generators:
            self.bet_slip_generators[guild_id] = BetSlipGenerator(guild_id=guild_id)
        return self.bet_slip_generators[guild_id]

    async def load_extensions(self):
        commands_dir = os.path.join(BASE_DIR, 'commands')
        cog_files = [
            'admin.py',
            'betting.py',
            'remove_user.py',
            'setid.py',
            'stats.py',
        ]
        loaded_commands = []
        for filename in cog_files:
            file_path = os.path.join(commands_dir, filename)
            if os.path.exists(file_path):
                extension = f'commands.{filename[:-3]}'
                try:
                    await self.load_extension(extension)
                    loaded_commands.append(extension)
                    logger.info('Successfully loaded extension: %s', extension)
                except Exception as e:
                    logger.error("Failed to load extension %s: %s", extension, e, exc_info=True)
            else:
                logger.warning("Command file not found: %s", file_path)
        
        logger.info("Total loaded extensions: %s", loaded_commands)
        # Verify commands after loading
        commands_list = [cmd.name for cmd in self.tree.get_commands()]
        logger.info("Available commands after loading: %s", commands_list)

    async def sync_commands_with_retry(self, guild: Optional[discord.Guild] = None, retries: int = 3, delay: int = 5):
        for attempt in range(1, retries + 1):
            try:
                if guild:
                    guild_obj = discord.Object(id=guild.id)
                    self.tree.copy_global_to(guild=guild_obj)
                    synced = await self.tree.sync(guild=guild_obj)
                    logger.info("Commands synced to guild %s: %s", guild.id, [cmd.name for cmd in synced])
                else:
                    synced = await self.tree.sync()
                    logger.info("Global commands synced: %s", [cmd.name for cmd in synced])
                return True
            except discord.HTTPException as e:
                logger.error("Sync attempt %d/%d failed: %s", attempt, retries, e, exc_info=True)
                if attempt < retries:
                    await asyncio.sleep(delay)
        logger.error("Failed to sync commands after %d attempts.", retries)
        return False

    async def setup_hook(self):
        logger.info("Starting setup_hook...")
        await self.db_manager.connect()
        if not self.db_manager._pool:
            logger.critical("Database connection pool failed to initialize. Bot cannot continue.")
            await self.close()
            sys.exit("Database connection failed.")
        await self.load_extensions()
        commands_list = [cmd.name for cmd in self.tree.get_commands()]
        logger.info("Registered commands before syncing: %s", commands_list)
        logger.info("Starting services...")
        service_starts = [
            self.admin_service.start(),
            self.analytics_service.start(),
            self.bet_service.start(),
            self.game_service.start(),
            self.user_service.start(),
            self.voice_service.start(),
            self.data_sync_service.start(),
        ]
        results = await asyncio.gather(*service_starts, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_name = service_starts[i].__self__.__class__.__name__ if hasattr(service_starts[i], '__self__') else f"Service {i}"
                logger.error("Error starting %s: %s", service_name, result, exc_info=True)
        logger.info("Services startup initiated.")
        logger.info("Bot setup_hook completed successfully.")

    async def on_ready(self):
        logger.info('Logged in as %s (%s)', self.user.name, self.user.id)
        logger.info("discord.py API version: %s", discord.__version__)
        logger.info("Python version: %s", sys.version)
        logger.info("Connected to %d guilds.", len(self.guilds))
        for guild in self.guilds:
            logger.debug("- %s (%s)", guild.name, guild.id)
        logger.info("Latency: %.2f ms", self.latency * 1000)
        try:
            # Get current commands before clearing
            current_commands = [cmd.name for cmd in self.tree.get_commands()]
            logger.info("Current commands before sync: %s", current_commands)
            
            # Clear existing commands
            self.tree.clear_commands(guild=None)
            logger.info("Cleared existing global commands")
            
            # Clear guild-specific commands
            cookin_books_guild = discord.Object(id=1328126227013439601)
            self.tree.clear_commands(guild=cookin_books_guild)
            logger.info("Cleared existing guild commands")
            
            # Reload all commands
            await self.load_extensions()
            
            # Verify commands are loaded
            loaded_commands = [cmd.name for cmd in self.tree.get_commands()]
            logger.info("Commands after reloading: %s", loaded_commands)
            
            if not loaded_commands:
                logger.error("No commands loaded after reloading extensions!")
                return
            
            # Sync global commands
            synced = await self.tree.sync()
            logger.info("Global commands synced: %s", [cmd.name for cmd in synced])
            
            # Sync to Cookin' Books guild
            try:
                # Copy global commands to guild
                self.tree.copy_global_to(guild=cookin_books_guild)
                # Sync guild commands
                guild_synced = await self.tree.sync(guild=cookin_books_guild)
                logger.info("Guild commands synced for Cookin' Books: %s", [cmd.name for cmd in guild_synced])
            except Exception as e:
                logger.error("Failed to sync guild commands: %s", e)
                # Try alternative sync method
                try:
                    guild_synced = await self.tree.sync(guild=cookin_books_guild)
                    logger.info("Alternative guild sync successful: %s", [cmd.name for cmd in guild_synced])
                except Exception as e:
                    logger.error("Alternative guild sync failed: %s", e)
            
            # Final verification
            global_commands = [cmd.name for cmd in self.tree.get_commands()]
            guild_commands = [cmd.name for cmd in self.tree.get_commands(guild=cookin_books_guild)]
            logger.info("Final global commands: %s", global_commands)
            logger.info("Final guild commands for Cookin' Books: %s", guild_commands)
            
            if not guild_commands:
                logger.error("No commands found for Cookin' Books guild after syncing!")
        except Exception as e:
            logger.error("Failed to sync command tree: %s", e, exc_info=True)
        logger.info('------ Bot is Ready ------')

    async def on_guild_join(self, guild: discord.Guild):
        logger.info("Joined new guild: %s (%s)", guild.name, guild.id)
        if guild.id == 1328126227013439601:
            await self.sync_commands_with_retry(guild=guild)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.user.id:
            return
        if payload.message_id in self.bet_service.pending_reactions:
            logger.debug("Processing reaction add: %s by %s on bot message %s", payload.emoji, payload.user_id, payload.message_id)
            asyncio.create_task(self.bet_service.on_raw_reaction_add(payload))

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.user.id:
            return
        if payload.message_id in self.bet_service.pending_reactions:
            logger.debug("Processing reaction remove: %s by %s on bot message %s", payload.emoji, payload.user_id, payload.message_id)
            asyncio.create_task(self.bet_service.on_raw_reaction_remove(payload))

    async def on_interaction(self, interaction: discord.Interaction):
        command_name = interaction.command.name if interaction.command else 'N/A'
        logger.debug("Interaction: type=%s, cmd=%s, user=%s(ID:%s), guild=%s, ch=%s", interaction.type, command_name, interaction.user, interaction.user.id, interaction.guild_id, interaction.channel_id)

    async def close(self):
        logger.info("Initiating graceful shutdown...")
        try:
            logger.info("Stopping services...")
            stop_tasks = [
                self.data_sync_service.stop(),
                self.voice_service.stop(),
                self.bet_service.stop(),
                self.game_service.stop(),
                self.user_service.stop(),
                self.admin_service.stop()
            ]
            results = await asyncio.gather(*stop_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    service_name = stop_tasks[i].__self__.__class__.__name__ if hasattr(stop_tasks[i], '__self__') else f"Service {i}"
                    logger.error("Error stopping %s: %s", service_name, result, exc_info=True)
            logger.info("Services stopped.")
            if self.db_manager:
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
    def __init__(self, bot: BettingBot):
        self.bot = bot

    @app_commands.command(name="sync", description="Manually sync bot commands (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_command(self, interaction: discord.Interaction):
        logger.info("Manual sync initiated by %s in guild %s", interaction.user, interaction.guild_id)
        try:
            await interaction.response.defer(ephemeral=True)
            commands_list = [cmd.name for cmd in self.bot.tree.get_commands()]
            logger.debug("Commands to sync: %s", commands_list)
            await self.bot.sync_commands_with_retry()
            if interaction.guild_id == 1328126227013439601:
                await self.bot.sync_commands_with_retry(guild=interaction.guild)
            await interaction.followup.send("Commands synced successfully!", ephemeral=True)
        except Exception as e:
            logger.error("Failed to sync commands: %s", e, exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Failed to sync commands: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Failed to sync commands: {e}", ephemeral=True)

async def setup_sync_cog(bot: BettingBot):
    await bot.add_cog(SyncCog(bot))
    logger.info("SyncCog loaded")

# --- Main Execution ---
def main():
    bot = BettingBot()
    async def run_bot():
        await setup_sync_cog(bot)
        await bot.start(BOT_TOKEN)
    try:
        logger.info("Starting bot...")
        asyncio.run(run_bot())
    except discord.LoginFailure:
        logger.critical("Login failed: Invalid Discord token provided in .env file.")
    except discord.PrivilegedIntentsRequired as e:
        shard_id_info = f" (Shard ID: {e.shard_id})" if e.shard_id else ""
        logger.critical("Privileged Intents%s are required but not enabled in the Discord Developer Portal.", shard_id_info)
        logger.critical("Enable 'Presence Intent', 'Server Members Intent', and 'Message Content Intent'.")
    except Exception as e:
        logger.critical("An unexpected error occurred while running the bot: %s", e, exc_info=True)
    finally:
        logger.info("Bot process finished.")

if __name__ == '__main__':
    main()
