import discord
from discord import app_commands
import logging
import aiosqlite
import os
import requests
from io import BytesIO
from PIL import Image
import uuid

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
            async with aiosqlite.connect('bot/data/betting.db') as db:
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
            image_path = f"bot/assets/logos/{self.guild_id}/{self.user_id}.{image.format.lower()}"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)

            # Update database
            async with aiosqlite.connect('bot/data/betting.db') as db:
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

async def setup(tree: app_commands.CommandTree):
    """Setup function for the setid command."""
    
    @tree.command(
        name="setid",
        description="Set up your capper profile"
    )
    async def setid(interaction: discord.Interaction):
        """Set up your capper profile."""
        try:
            # Check if user is already a capper
            async with aiosqlite.connect('bot/data/betting.db') as db:
                async with db.execute(
                    """
                    SELECT user_id 
                    FROM cappers 
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (interaction.guild_id, interaction.user.id)
                ) as cursor:
                    if await cursor.fetchone():
                        await interaction.response.send_message(
                            "❌ You are already set up as a capper in this server.",
                            ephemeral=True
                        )
                        return

                # Check if server has paid subscription
                async with db.execute(
                    """
                    SELECT is_paid 
                    FROM server_settings 
                    WHERE guild_id = ?
                    """,
                    (interaction.guild_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    is_paid = result and result[0] if result else False

            if is_paid:
                # Show modal for paid tier
                modal = CapperModal(interaction.guild_id, interaction.user.id)
                await interaction.response.send_modal(modal)

                # Show image upload view after modal submission
                view = ImageUploadView(interaction.guild_id, interaction.user.id)
                await interaction.followup.send(
                    "Please choose how you want to set your profile picture:",
                    view=view,
                    ephemeral=True
                )
            else:
                # Free tier - just create basic entry
                async with aiosqlite.connect('bot/data/betting.db') as db:
                    await db.execute(
                        """
                        INSERT INTO cappers (
                            guild_id, 
                            user_id, 
                            display_name, 
                            bet_won, 
                            bet_loss, 
                            updated_at
                        ) VALUES (?, ?, ?, 0, 0, datetime('now'))
                        """,
                        (
                            interaction.guild_id,
                            interaction.user.id,
                            interaction.user.display_name
                        )
                    )
                    await db.commit()

                await interaction.response.send_message(
                    "✅ You have been set up as a capper!",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in setid command: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while setting up your profile.",
                ephemeral=True
            )

    @setid.error
    async def setid_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        logger.error(f"Error in setid command: {str(error)}")
        await interaction.response.send_message(
            "❌ An unexpected error occurred.",
            ephemeral=True
        )

    # Handle image uploads
    @tree.listen('on_message')
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        # Check if this is a response to the image upload prompt
        if not message.reference:
            return

        try:
            # Get the referenced message
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            if not referenced_message.content == "Please upload an image file (PNG, JPG, or GIF).":
                return

            # Check if user is a capper
            async with aiosqlite.connect('bot/data/betting.db') as db:
                async with db.execute(
                    """
                    SELECT guild_id, user_id 
                    FROM cappers 
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (message.guild.id, message.author.id)
                ) as cursor:
                    if not await cursor.fetchone():
                        return

            # Process attachments
            if not message.attachments:
                await message.reply("❌ No image file found in your message.", ephemeral=True)
                return

            attachment = message.attachments[0]
            if not attachment.content_type.startswith('image/'):
                await message.reply("❌ Please upload an image file (PNG, JPG, or GIF).", ephemeral=True)
                return

            # Download and validate image
            response = requests.get(attachment.url)
            if response.status_code != 200:
                await message.reply("❌ Failed to download image.", ephemeral=True)
                return

            try:
                image = Image.open(BytesIO(response.content))
                if image.format not in ['PNG', 'JPEG', 'GIF']:
                    await message.reply("❌ Invalid image format. Please use PNG, JPG, or GIF.", ephemeral=True)
                    return
            except Exception:
                await message.reply("❌ Invalid image file.", ephemeral=True)
                return

            # Save image
            image_path = f"bot/assets/logos/{message.guild.id}/{message.author.id}.{image.format.lower()}"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)

            # Update database
            async with aiosqlite.connect('bot/data/betting.db') as db:
                await db.execute(
                    """
                    UPDATE cappers 
                    SET image_path = ? 
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (image_path, message.guild.id, message.author.id)
                )
                await db.commit()

            await message.reply("✅ Profile picture updated successfully!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error processing image upload: {str(e)}")
            await message.reply("❌ An error occurred while processing the image.", ephemeral=True) 