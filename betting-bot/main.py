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
from commands import setup as setup_commands

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

    async def setup_hook(self):
        """Setup function that runs before the bot starts."""
        try:
            # Setup all commands
            await setup_commands(self)
            logger.info("Successfully set up all commands")
            
            # Start services
            await self.game_service.start()
            await self.bet_service.start()
            logger.info("Successfully started all services")
            
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            raise

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        logger.info('------')

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild."""
        try:
            # Register commands for the new guild
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands for guild {guild.name} ({guild.id})")
        except Exception as e:
            logger.error(f"Error syncing commands for guild {guild.name}: {e}")

def main():
    bot = BettingBot()
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    main() 