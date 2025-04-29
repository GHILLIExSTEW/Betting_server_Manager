import discord
from discord import app_commands
import os
import logging
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

# Configuration
TEST_GUILD_ID = 123456789  # Replace with your test guild ID
AUTHORIZED_USER_ID = 987654321  # Replace with your user ID

async def setup(tree: app_commands.CommandTree):
    """Setup function for the load_logos command."""
    @tree.command(
        name="load_logos",
        description="Load team and league logos (Admin only)",
        guild=discord.Object(id=TEST_GUILD_ID)
    )
    async def load_logos(
        interaction: discord.Interaction,
        team_name: str,
        logo_file: discord.Attachment,
        is_league: bool = False
    ):
        """Load a logo for a team or league."""
        try:
            # Check if user is authorized
            if interaction.user.id != AUTHORIZED_USER_ID:
                await interaction.response.send_message(
                    "You are not authorized to use this command.",
                    ephemeral=True
                )
                return

            # Validate file type
            if not logo_file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                await interaction.response.send_message(
                    "Only PNG, JPG, and JPEG files are supported.",
                    ephemeral=True
                )
                return

            # Create directories if they don't exist
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if is_league:
                target_dir = os.path.join(base_dir, 'utils', 'assets', 'leagues')
            else:
                target_dir = os.path.join(base_dir, 'utils', 'assets', 'logos')
            
            os.makedirs(target_dir, exist_ok=True)

            # Download and process the image
            await logo_file.save(os.path.join(target_dir, f"{team_name.lower()}.png"))
            
            # Optimize the image
            image_path = os.path.join(target_dir, f"{team_name.lower()}.png")
            with Image.open(image_path) as img:
                # Convert to PNG if not already
                if img.format != 'PNG':
                    img = img.convert('RGBA')
                
                # Resize if needed (maintain aspect ratio)
                max_size = (200, 200)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(image_path, 'PNG', optimize=True)

            await interaction.response.send_message(
                f"Successfully loaded {'league' if is_league else 'team'} logo for {team_name}.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error loading logo: {str(e)}")
            await interaction.response.send_message(
                "An error occurred while loading the logo.",
                ephemeral=True
            ) 