import discord
from discord import app_commands
import logging
import aiosqlite
import os
import requests
from io import BytesIO
from PIL import Image
from typing import Optional
from services.admin_service import AdminService
from utils.errors import AdminServiceError

logger = logging.getLogger(__name__)

class CapperModal(discord.ui.Modal, title="Capper Profile Setup"):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__()
        self.guild_id = guild_id
        self.user_id = user_id

    display_name = discord.ui.TextInput(
        label="Display Name",
        placeholder="Enter your display name",
        required=True,
        max_length=32
    )

    banner_color = discord.ui.TextInput(
        label="Banner Color (Hex)",
        placeholder="#RRGGBB",
        required=False,
        max_length=7,
        default="#0096FF"
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate hex color
            if self.banner_color.value and not self.banner_color.value.startswith('#'):
                self.banner_color.value = '#' + self.banner_color.value
            if len(self.banner_color.value) != 7:
                await interaction.response.send_message(
                    "❌ Invalid hex color format. Please use #RRGGBB format.",
                    ephemeral=True
                )
                return

            # Create the capper entry
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                await db.execute(
                    """
                    INSERT INTO cappers (
                        guild_id, 
                        user_id, 
                        display_name, 
                        banner_color, 
                        bet_won, 
                        bet_loss, 
                        updated_at
                    ) VALUES (?, ?, ?, ?, 0, 0, datetime('now'))
                    """,
                    (
                        self.guild_id,
                        self.user_id,
                        self.display_name.value,
                        self.banner_color.value
                    )
                )
                await db.commit()

            await interaction.response.send_message(
                "✅ Profile setup complete! Please upload an image or provide a URL for your profile picture.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in capper modal: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while setting up your profile.",
                ephemeral=True
            )

class ImageUploadView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="Upload Image", style=discord.ButtonStyle.primary)
    async def upload_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Please upload an image file (PNG, JPG, or GIF).",
            ephemeral=True
        )

    @discord.ui.button(label="Provide URL", style=discord.ButtonStyle.secondary)
    async def provide_url(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Please provide a URL to your image.",
            ephemeral=True
        )

class ImageURLModal(discord.ui.Modal, title="Image URL"):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__()
        self.guild_id = guild_id
        self.user_id = user_id

    url = discord.ui.TextInput(
        label="Image URL",
        placeholder="Enter the URL of your image",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Download and validate image
            response = requests.get(self.url.value)
            if response.status_code != 200:
                await interaction.response.send_message(
                    "❌ Failed to download image from URL.",
                    ephemeral=True
                )
                return

            # Validate image format
            try:
                image = Image.open(BytesIO(response.content))
                if image.format not in ['PNG', 'JPEG', 'GIF']:
                    await interaction.response.send_message(
                        "❌ Invalid image format. Please use PNG, JPG, or GIF.",
                        ephemeral=True
                    )
                    return
            except Exception:
                await interaction.response.send_message(
                    "❌ Invalid image file.",
                    ephemeral=True
                )
                return

            # Save image
            image_path = f"betting-bot/assets/logos/{self.guild_id}/{self.user_id}.{image.format.lower()}"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)

            # Update database
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                await db.execute(
                    """
                    UPDATE cappers 
                    SET image_path = ? 
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (image_path, self.guild_id, self.user_id)
                )
                await db.commit()

            await interaction.response.send_message(
                "✅ Profile picture updated successfully!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error processing image URL: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while processing the image.",
                ephemeral=True
            )

async def setup(bot):
    """Add the setid command to the bot."""
    @bot.tree.command(
        name="setid",
        description="Set up a user as a capper"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setid(interaction: discord.Interaction, user: discord.Member):
        """Set up a user as a capper."""
        try:
            # Check if user is already a capper
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                async with db.execute(
                    """
                    SELECT user_id 
                    FROM cappers 
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (interaction.guild_id, user.id)
                ) as cursor:
                    if await cursor.fetchone():
                        await interaction.response.send_message(
                            "❌ This user is already set up as a capper.",
                            ephemeral=True
                        )
                        return

            # Show profile setup modal
            modal = CapperModal(interaction.guild_id, user.id)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error in setid command: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while setting up the user.",
                ephemeral=True
            )