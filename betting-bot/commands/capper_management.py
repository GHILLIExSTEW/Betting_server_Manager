import discord
from discord import app_commands
import logging
from typing import Optional
import aiosqlite
from utils.errors import AdminServiceError

logger = logging.getLogger(__name__)

class RemoveUserSelect(discord.ui.Select):
    def __init__(self, cappers: list):
        options = [
            discord.SelectOption(
                label=capper[2],  # display_name
                value=str(capper[1]),  # user_id
                description=f"Remove {capper[2]} from cappers"
            ) for capper in cappers
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
                    FROM cappers 
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
                    DELETE FROM cappers 
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
                    FROM cappers 
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

class CapperManagement(discord.app_commands.Group):
    """Group of commands for managing cappers."""
    def __init__(self, bot):
        super().__init__(name="capper", description="Capper management commands")
        self.bot = bot

    @app_commands.command(name="add", description="Add a user as a capper")
    @app_commands.checks.has_permissions(administrator=True)
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        """Add a user as a capper."""
        try:
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO cappers 
                    (guild_id, user_id, username) 
                    VALUES (?, ?, ?)
                    """,
                    (interaction.guild_id, user.id, user.name)
                )
                await db.commit()

            await interaction.response.send_message(
                f"✅ Successfully added {user.mention} as a capper",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error adding capper: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to add capper. Check logs for details.",
                ephemeral=True
            )

    @app_commands.command(name="remove", description="Remove a user as a capper")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        """Remove a user as a capper."""
        try:
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                await db.execute(
                    """
                    DELETE FROM cappers 
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (interaction.guild_id, user.id)
                )
                await db.commit()

            await interaction.response.send_message(
                f"✅ Successfully removed {user.mention} as a capper",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error removing capper: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to remove capper. Check logs for details.",
                ephemeral=True
            )

    @app_commands.command(name="list", description="List all cappers in the server")
    async def list(self, interaction: discord.Interaction):
        """List all cappers in the server."""
        try:
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                async with db.execute(
                    """
                    SELECT user_id, username 
                    FROM cappers 
                    WHERE guild_id = ?
                    ORDER BY username
                    """,
                    (interaction.guild_id,)
                ) as cursor:
                    cappers = await cursor.fetchall()

            if not cappers:
                await interaction.response.send_message(
                    "No cappers found in this server.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Server Cappers",
                description="List of all cappers in this server",
                color=discord.Color.blue()
            )

            for user_id, username in cappers:
                user = interaction.guild.get_member(user_id)
                if user:
                    embed.add_field(
                        name=user.display_name,
                        value=f"ID: {user_id}",
                        inline=False
                    )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error listing cappers: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to list cappers. Check logs for details.",
                ephemeral=True
            )

async def setup(bot):
    """Add the capper management commands to the bot."""
    capper_group = CapperManagement(bot)
    bot.tree.add_command(capper_group)

    @bot.tree.command(
        name="remove_user",
        description="Remove a user from the cappers list"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_user(interaction: discord.Interaction):
        """Remove a user from the cappers list."""
        try:
            # Check if the guild has access to the command
            async with aiosqlite.connect('betting-bot/data/betting.db') as db:
                async with db.execute(
                    """
                    SELECT commands_registered 
                    FROM server_settings 
                    WHERE guild_id = ?
                    """,
                    (interaction.guild_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    if not result or not result[0]:
                        await interaction.response.send_message(
                            "❌ This server does not have access to this command. Please contact an admin.",
                            ephemeral=True
                        )
                        return

            # Show the remove user view
            view = RemoveUserView(interaction.guild_id)
            await view.populate_users(interaction)
        except Exception as e:
            logger.error(f"Error in remove_user command: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while processing the command.",
                ephemeral=True
            )

    @remove_user.error
    async def remove_user_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.",
                ephemeral=True
            )
        else:
            logger.error(f"Error in remove_user command: {str(e)}")
            await interaction.response.send_message(
                "❌ An unexpected error occurred.",
                ephemeral=True
            ) 