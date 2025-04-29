import asyncio
import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Get Discord token from environment
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    print("Error: DISCORD_TOKEN not found in environment variables")
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
        self.initial_extensions = [
            'betting-bot.commands.admin',
            'betting-bot.commands.betting',
            'betting-bot.commands.games',
            'betting-bot.commands.voice',
            'betting-bot.commands.stats',
            'betting-bot.commands.setid'
        ]

    async def setup_hook(self):
        """Load extensions and perform setup tasks"""
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded extension {ext}")
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

    async def on_ready(self):
        """Called when the bot is ready"""
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

async def main():
    """Main function to run the bot"""
    async with BettingBot() as bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main()) 