import discord
from discord.ext import commands
import logging
import asyncio
from bot.services.game_service import GameService
from bot.services.user_service import UserService
from bot.services.bet_service import BetService
from bot.config.settings import TOKEN, PREFIX
from utils.db_manager import DatabaseManager
from utils.image_generator import BetSlipGenerator
from utils.cleanup import CleanupTasks

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
        self.db_manager = DatabaseManager()
        self.bet_slip_generator = BetSlipGenerator()
        self.cleanup_tasks = CleanupTasks(self.db_manager)

    async def setup_hook(self):
        """Setup hook that runs when the bot starts."""
        try:
            # Initialize services
            self.game_service = GameService(self)
            self.user_service = UserService(self)
            self.bet_service = BetService(self, self.tree)
            
            # Initialize database connection
            await self.db_manager.initialize()
            logger.info("Database connection initialized")

            # Start services
            await self.game_service.start()
            await self.user_service.start()
            await self.bet_service.start()

            # Start cleanup tasks
            await self.cleanup_tasks.start_cleanup_tasks()
            logger.info("Cleanup tasks started")

            # Load cogs
            for extension in ['commands.straight_betting', 'commands.parlay_betting']:
                try:
                    await self.load_extension(extension)
                    logger.info(f"Loaded extension: {extension}")
                except Exception as e:
                    logger.error(f"Failed to load extension {extension}: {e}")
            
            logger.info("Bot setup completed successfully")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
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
        """Cleanup when the bot is shutting down."""
        try:
            if self.game_service:
                await self.game_service.stop()
            if self.user_service:
                await self.user_service.stop()
            if self.bet_service:
                await self.bet_service.stop()
            
            # Stop cleanup tasks
            await self.cleanup_tasks.stop_cleanup_tasks()
            logger.info("Cleanup tasks stopped")

            # Close database connection
            await self.db_manager.close()
            logger.info("Database connection closed")

        except Exception as e:
            logger.error(f"Error in close: {e}")
        finally:
            await super().close()
            logger.info("Bot shutdown completed successfully")

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