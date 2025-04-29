import os
import sys
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from services.game_service import GameService
from services.bet_service import BetService
from services.admin_service import AdminService
from services.analytics_service import AnalyticsService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class BettingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Initialize services
        self.game_service = GameService(self)
        self.bet_service = BetService(self)
        self.admin_service = AdminService(self)
        self.analytics_service = AnalyticsService(self)
        
        # Load extensions
        self.initial_extensions = [
            'commands.betting',
            'commands.admin',
            'commands.stats'
        ]

    async def setup_hook(self):
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f'Loaded extension {extension}')
            except Exception as e:
                logger.error(f'Failed to load extension {extension}: {e}')

    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        logger.info('------')

def main():
    bot = BettingBot()
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    main() 