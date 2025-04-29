import asyncio
import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from services.admin_service import AdminService
from services.bet_service import BetService
from services.game_service import GameService
from services.analytics_service import AnalyticsService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Load environment variables
load_dotenv()

# Get Discord token from environment
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN not found in environment variables")
    sys.exit(1)

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

class BettingBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        # Initialize services
        self.admin_service = AdminService()
        self.bet_service = BetService()
        self.game_service = GameService()
        self.analytics_service = AnalyticsService()
        
        self.initial_extensions = [
            'commands.admin',
            'commands.betting',
            'commands.stats',
            'commands.setid'
        ]

    async def setup_hook(self):
        """Load extensions and perform setup tasks"""
        for ext in self.initial_extensions:
            try:
                if ext == 'commands.admin':
                    await self.load_extension(ext)
                elif ext == 'commands.betting':
                    await self.load_extension(ext)
                elif ext == 'commands.stats':
                    await self.load_extension(ext)
                elif ext == 'commands.setid':
                    await self.load_extension(ext)
                logger.info(f"Loaded extension {ext}")
            except Exception as e:
                logger.error(f"Failed to load extension {ext}: {e}")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

async def main():
    """Main function to run the bot"""
    async with BettingBot() as bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main()) 