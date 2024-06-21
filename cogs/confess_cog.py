import discord
from discord.ext import commands
from discord import app_commands
from decouple import config
import sqlite3
import logging
from datetime import datetime
import traceback

log = logging.getLogger(__name__)

class ConfessCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            # Validate and log environment variable loading
            self.allowed_channel_id = int(config('ALLOWED_CHANNEL_ID'))
            self.admin_user_id = int(config('ADMIN_USER_ID'))
            log.info(f"Allowed Channel ID: {self.allowed_channel_id}")
            log.info(f"Admin User ID: {self.admin_user_id}")

            # Attempt database connection
            self.conn = sqlite3.connect('chuck.db')
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS confessions (
                                   id INTEGER PRIMARY KEY,
                                   username TEXT,
                                   confession TEXT,
                                   submitted_at DATETIME
                                   )''')
            self.conn.commit()
            logging.info("Connected to the confessions database successfully.")
        except ValueError as ve:
            logging.error(f"Configuration error: {ve}")
            logging.error(traceback.format_exc())
            raise ve  # Re-raise the exception to prevent the cog from loading improperly
        except sqlite3.Error as se:
            logging.error(f"Database error: {se}")
            logging.error(traceback.format_exc())
            raise se  # Re-raise the exception to prevent the cog from loading improperly
        except Exception as e:
            logging.error(f"Error during ConfessCog initialization: {e}")
            logging.error(traceback.format_exc())
            raise e  # Re-raise the exception to prevent the cog from loading improperly

    def cog_unload(self):
        if self.conn:
            self.conn.close()

    @app_commands.command(name="confess", description="Submit an anonymous confession")
    async def confess(self, interaction: discord.Interaction, *, message: str):
        username = str(interaction.user)
        submitted_at = datetime.utcnow()

        try:
            self.cursor.execute('INSERT INTO confessions (username, confession, submitted_at) VALUES (?, ?, ?)', 
                                (username, message, submitted_at))
            self.conn.commit()
            log.info(f"Stored confession from {username}")

            channel = self.bot.get_channel(self.allowed_channel_id)
            if channel:
                embed = discord.Embed(
                    title="I Chuck Norris have a confession to make: ",
                    description=f"{message}",
                    color=discord.Color.blue(),
                    timestamp=submitted_at
                )
                embed.set_footer(text="Posted anonymously")

                await channel.send(embed=embed)
                await interaction.response.send_message("Your confession has been posted anonymously.", ephemeral=True)
            else:
                await interaction.response.send_message("Sorry, I couldn't find the confessions channel.", ephemeral=True)
                log.error(f"Channel with ID {self.allowed_channel_id} not found.")

        except sqlite3.Error as e:
            log.error(f"Failed to save confession from {username}: {e}")
            await interaction.response.send_message("An error occurred while processing your confession. Please try again later.", ephemeral=True)

    @app_commands.command(name="view_confessions", description="View all confessions (Admin only)")
    async def slash_view_confessions(self, interaction: discord.Interaction):
        if interaction.user.id != self.admin_user_id:
            await interaction.response.send_message("You do not have permission to view confessions.", ephemeral=True)
            return

        await self.view_confessions(interaction)

    @app_commands.command(name="delete_confession", description="Delete a confession by its ID (Admin only)")
    async def slash_delete_confession(self, interaction: discord.Interaction, confession_id: int):
        if interaction.user.id != self.admin_user_id:
            await interaction.response.send_message("You do not have permission to delete confessions.", ephemeral=True)
            return

        await self.delete_confession(interaction, confession_id)

    async def view_confessions(self, interaction: discord.Interaction):
        try:
            self.cursor.execute('SELECT id, confession, submitted_at FROM confessions ORDER BY submitted_at DESC')
            confessions = self.cursor.fetchall()

            if confessions:
                confessions_list = "\n".join([f"ID: {id}, Confession: {confession}, Time: {submitted_at}" 
                                              for id, confession, submitted_at in confessions])
                await interaction.response.send_message(f"**Confessions:**\n{confessions_list}", ephemeral=True)
            else:
                await interaction.response.send_message("No confessions found.", ephemeral=True)
        
        except sqlite3.Error as e:
            log.error(f"Failed to retrieve confessions: {e}")
            await interaction.response.send_message("An error occurred while fetching confessions.", ephemeral=True)

    async def delete_confession(self, interaction: discord.Interaction, confession_id: int):
        try:
            self.cursor.execute('DELETE FROM confessions WHERE id = ?', (confession_id,))
            self.conn.commit()
            if self.cursor.rowcount > 0:
                log.info(f"Deleted confession ID {confession_id}")
                await interaction.response.send_message(f"Confession ID {confession_id} has been deleted.", ephemeral=True)
            else:
                await interaction.response.send_message(f"No confession found with ID {confession_id}.", ephemeral=True)
        
        except sqlite3.Error as e:
            log.error(f"Failed to delete confession ID {confession_id}: {e}")
            await interaction.response.send_message("An error occurred while deleting the confession. Please try again later.", ephemeral=True)

async def setup(bot):
    try:
        await bot.add_cog(ConfessCog(bot))
        log.info("ConfessCog loaded successfully.")
    except Exception as e:
        log.error(f"Failed to load ConfessCog: {e}")
        log.error(traceback.format_exc())
