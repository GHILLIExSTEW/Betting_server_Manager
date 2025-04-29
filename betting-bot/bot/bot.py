import discord
from discord.ext import commands
import logging
import asyncio
from bot.services.game_service import GameService
from bot.services.user_service import UserService
from bot.services.bet_service import BetService
from bot.config.settings import TOKEN, PREFIX

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BettingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None
        )
        
        self.game_service = None
        self.user_service = None
        self.bet_service = None

    async def setup_hook(self):
        """Initialize services and load extensions"""
        try:
            # Initialize services
            self.game_service = GameService(self)
            self.user_service = UserService(self)
            self.bet_service = BetService(self, self.tree)
            
            # Start services
            await self.game_service.start()
            await self.user_service.start()
            await self.bet_service.start()
            
            logger.info("Bot setup completed successfully")
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            raise

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def close(self):
        """Clean up resources before shutdown"""
        try:
            if self.game_service:
                await self.game_service.stop()
            if self.user_service:
                await self.user_service.stop()
            if self.bet_service:
                await self.bet_service.stop()
            
            await super().close()
            logger.info("Bot shutdown completed successfully")
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")
            raise

async def main():
    """Main entry point"""
    bot = BettingBot()
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await bot.close()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main()) 