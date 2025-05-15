# betting-bot/main.py

import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import asyncpg
import json

from data.db_manager import DatabaseManager
from services.admin_service import AdminService
from services.analytics_service import AnalyticsService
from services.bet_service import BetService
from services.game_service import GameService
from services.user_service import UserService
from services.voice_service import VoiceService
from services.data_sync_service import DataSyncService
from utils.image_generator import BetSlipGenerator

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/{discord.utils.utcnow().strftime("%Y-%m-%d_%H-%M-%S")}.txt')
    ]
)
logger = logging.getLogger(__name__)

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix='/', intents=intents)
        self.db_manager = DatabaseManager()
        self.admin_service = AdminService(self, self.db_manager)
        self.analytics_service = AnalyticsService(self, self.db_manager)
        self.bet_service = BetService(self, self.db_manager)
        self.game_service = GameService(self, self.db_manager)
        self.user_service = UserService(self, self.db_manager)
        self.voice_service = VoiceService(self, self.db_manager)
        self.data_sync_service = DataSyncService(self, self.db_manager)
        self.bet_slip_generators = {}

    async def get_bet_slip_generator(self, guild_id: int) -> BetSlipGenerator:
        if guild_id not in self.bet_slip_generators:
            self.bet_slip_generators[guild_id] = BetSlipGenerator(guild_id)
        return self.bet_slip_generators[guild_id]

    async def setup_hook(self):
        logger.info("Starting setup_hook...")
        await self.db_manager.connect()

        extensions = [
            'commands.admin',
            'commands.betting',
            'commands.load_logos',
            'commands.remove_user',
            'commands.setid',
            'commands.stats',
            'commands.sync'
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Successfully loaded extension: {ext}")
            except Exception as e:
                logger.error(f"Failed to load extension {ext}: {e}", exc_info=True)

        logger.info(f"Extension loading complete. Loaded: {len(self.extensions)}, Failed: 0")
        logger.info(f"Registered commands before syncing: {[c.name for c in self.tree.get_commands()]}")

        logger.info("Starting services...")
        await asyncio.gather(
            self.admin_service.start(),
            self.analytics_service.start(),
            self.bet_service.start(),
            self.game_service.start(),
            self.user_service.start(),
            self.voice_service.start(),
            self.data_sync_service.start()
        )
        logger.info("Services startup initiated.")

        try:
            self.tree.clear_commands(guild=None)
            logger.info("Cleared global commands.")

            global_commands = ['sync', 'setup', 'setchannel', 'bet', 'remove_user', 'setid', 'stats']
            await self.tree.sync()
            logger.info(f"Global commands synced: {global_commands}")

            for guild in self.guilds:
                guild_commands = global_commands.copy()
                if guild.id == 1328126227013439601:
                    guild_commands.append('load_logos')
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Commands synced to guild {guild.id}: {guild_commands}")
        except Exception as e:
            logger.error(f"Error syncing commands: {e}", exc_info=True)

        logger.info(f"Commands available after sync: {[c.name for c in self.tree.get_commands()]}")
        logger.info("------ Bot is Ready ------")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} ({self.user.id})")
        logger.info(f"discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {os.sys.version}")
        logger.info(f"Connected to {len(self.guilds)} guilds.")
        for guild in self.guilds:
            logger.debug(f"- {guild.name} ({guild.id})")
        logger.info(f"Latency: {self.latency * 1000:.2f} ms")

    async def on_message(self, message):
        if message.author.id != self.user.id:
            return
        await self.process_commands(message)

async def main():
    load_dotenv()
    logger.info(f"Loaded environment variables from: {os.path.abspath('.env')}")
    bot = Bot()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN not found in .env file.")
        return
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
