import discord
from discord import app_commands
import logging
import aiosqlite
import os
import requests
from io import BytesIO
from PIL import Image
import uuid
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
            image_path = f"bot/assets/logos/{self.guild_id}/{self.user_id}.{image.format.lower()}"
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

class RemoveUserSelect(discord.ui.Select):
    def __init__(self, users: list):
        options = [
            discord.SelectOption(
                label=user[2],  # display_name
                value=str(user[1]),  # user_id
                description=f"Remove {user[2]} from users"
            ) for user in users
        ]
        super().__init__(
            placeholder="Select a user to remove",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            user_id = int(self.values[0])
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                # Get display_name before deleting
                async with db.execute(
                    """
                    SELECT display_name 
                    FROM users 
                    WHERE user_id = ? AND guild_id = ?
                    """,
                    (user_id, interaction.guild_id)
                ) as cursor:
                    result = await cursor.fetchone()
                    if not result:
                        await interaction.response.send_message(
                            "❌ User not found.",
                            ephemeral=True
                        )
                        return
                    display_name = result[0]

                # Delete the user
                await db.execute(
                    """
                    DELETE FROM users 
                    WHERE user_id = ? AND guild_id = ?
                    """,
                    (user_id, interaction.guild_id)
                )
                await db.commit()

                await interaction.response.send_message(
                    f"✅ Successfully removed user '{display_name}'",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error removing user: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while removing the user.",
                ephemeral=True
            )

class RemoveUserView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.guild_id = guild_id

    async def populate_users(self, interaction: discord.Interaction):
        try:
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                # Get all users from the guild
                async with db.execute(
                    """
                    SELECT guild_id, user_id, display_name 
                    FROM users 
                    WHERE guild_id = ?
                    ORDER BY display_name
                    """,
                    (self.guild_id,)
                ) as cursor:
                    users = await cursor.fetchall()

                if not users:
                    await interaction.response.send_message(
                        "❌ No users found in this server.",
                        ephemeral=True
                    )
                    return

                # Add select menu
                self.add_item(RemoveUserSelect(users))
                await interaction.response.send_message(
                    "Select a user to remove:",
                    view=self,
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error populating users: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching users.",
                ephemeral=True
            )

async def setup(bot):
    """Add the setid command to the bot."""
    @bot.tree.command(
        name="setid",
        description="Set user ID for the server"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setid(interaction: discord.Interaction, user: discord.Member):
        """Set user ID for the server."""
        try:
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO users 
                    (guild_id, user_id, username) 
                    VALUES (?, ?, ?)
                    """,
                    (interaction.guild_id, user.id, user.name)
                )
                await db.commit()

            await interaction.response.send_message(
                f"✅ Successfully set {user.mention} as a user",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting user: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to set user. Check logs for details.",
                ephemeral=True
            )

    # Handle image uploads
    @bot.tree.listen('on_message')
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
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
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
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
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