import discord
from discord import app_commands
import logging
import aiosqlite

logger = logging.getLogger(__name__)

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

@app_commands.checks.has_permissions(administrator=True)
async def remove_user(interaction: discord.Interaction):
    """Remove a user from the server."""
    view = RemoveUserView(interaction.guild_id)
    await view.populate_users(interaction)

async def setup(bot):
    """Add the remove_user command to the bot."""
    bot.tree.add_command(
        app_commands.Command(
            name="remove_user",
            description="Remove a user from the server",
            callback=remove_user
        )
    ) 