import asyncio
import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from betting_bot.services.admin_service import AdminService
from betting_bot.services.bet_service import BetService
from betting_bot.services.game_service import GameService
from betting_bot.services.analytics_service import AnalyticsService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
            'betting_bot.commands.admin',
            'betting_bot.commands.betting',
            'betting_bot.commands.stats',
            'betting_bot.commands.setid'
        ]

    async def setup_hook(self):
        """Load extensions and perform setup tasks"""
        for ext in self.initial_extensions:
            try:
                if ext == 'betting_bot.commands.admin':
                    await self.load_extension(ext)
                elif ext == 'betting_bot.commands.betting':
                    await self.load_extension(ext)
                elif ext == 'betting_bot.commands.stats':
                    await self.load_extension(ext)
                elif ext == 'betting_bot.commands.setid':
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