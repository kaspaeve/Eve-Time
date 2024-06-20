import discord
import sqlite3
import logging
from discord.ext import commands
from discord import app_commands

class ChuckJokesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.jokes_db = 'chuck_norris_jokes.db'  # Jokes database
        self.stats_db = 'chuck.db'  # Statistics database

        # Connect to the jokes database
        try:
            self.conn_jokes = sqlite3.connect(self.jokes_db)
            self.cursor_jokes = self.conn_jokes.cursor()
            logging.info("Connected to the Chuck Norris jokes database successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database connection error (jokes): {e}")

        # Connect to the statistics database
        try:
            self.conn_stats = sqlite3.connect(self.stats_db)
            self.cursor_stats = self.conn_stats.cursor()

            # Create joke_requests table if it doesn't exist
            self.cursor_stats.execute('''
                CREATE TABLE IF NOT EXISTS joke_requests (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    request_count INTEGER DEFAULT 0
                )
            ''')
            self.conn_stats.commit()
            logging.info("Connected to the statistics database successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database connection error (stats): {e}")

    def cog_unload(self):
        try:
            self.conn_jokes.close()
            self.conn_stats.close()
            logging.info("Database connections closed.")
        except Exception as e:
            logging.error(f"Error during database connection close: {e}")

    @app_commands.command(name="jokeschuck", description="Get a random Chuck Norris joke.")
    async def jokes_chuck(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        username = str(interaction.user) 

        try:
            # Fetch a random joke from the jokes database
            self.cursor_jokes.execute('SELECT joke FROM jokes ORDER BY RANDOM() LIMIT 1')
            joke_row = self.cursor_jokes.fetchone()

            if joke_row:
                joke = joke_row[0]
                embed = discord.Embed(
                    description=joke,
                    color=0x3498db
                )

                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=embed)
                        logging.info(f"Chuck Norris joke sent successfully to {username}.")
                except discord.errors.NotFound:
                    logging.warning(f"Interaction expired before sending the response for user {username}.")
                    return

                # Update or insert the user's joke request count in the statistics database
                self.cursor_stats.execute('SELECT request_count FROM joke_requests WHERE user_id = ?', (user_id,))
                user_request = self.cursor_stats.fetchone()

                if user_request:
                    new_count = user_request[0] + 1
                    self.cursor_stats.execute('UPDATE joke_requests SET request_count = ?, username = ? WHERE user_id = ?', (new_count, username, user_id))
                    logging.info(f"Updated joke request count for {username}: new count is {new_count}.")
                else:
                    self.cursor_stats.execute('INSERT INTO joke_requests (user_id, username, request_count) VALUES (?, ?, ?)', (user_id, username, 1))
                    logging.info(f"Inserted new joke request record for {username} with count 1.")

                self.conn_stats.commit()
                logging.info(f"Joke request recorded successfully for {username}.")
            else:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Sorry, no jokes found in the database.", ephemeral=True)
                logging.warning("No jokes found in the database.")

        except sqlite3.Error as e:
            logging.error(f"Database query error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred while fetching a joke. Please try again later.", ephemeral=True)

    @app_commands.command(name="jokestats", description="Show the number of joke requests.")
    async def joke_stats(self, interaction: discord.Interaction):
        try:
            self.cursor_stats.execute('SELECT COUNT(*) FROM joke_requests')
            total_requests = self.cursor_stats.fetchone()[0]

            user_id = interaction.user.id
            self.cursor_stats.execute('SELECT username, request_count FROM joke_requests WHERE user_id = ?', (user_id,))
            user_request = self.cursor_stats.fetchone()
            user_requests = user_request[1] if user_request else 0
            username = user_request[0] if user_request else "Unknown User"

            stats_message = (f"Total Chuck Norris jokes requested: {total_requests}\n")
                           

            if not interaction.response.is_done():
                await interaction.response.send_message(stats_message, ephemeral=True)
            logging.info(f"Displayed joke stats for user {username}.")

        except sqlite3.Error as e:
            logging.error(f"Database query error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred while fetching the joke stats. Please try again later.", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("ChuckJokesCog is ready.")

# Remove the add_joke and list_jokes commands
# @app_commands.command(name="addjoke", description="Add a new Chuck Norris joke to the database.")
# @app_commands.describe(joke="The joke to add to the database")
# async def add_joke(self, interaction: discord.Interaction, joke: str):
#     try:
#         self.cursor_jokes.execute('INSERT INTO jokes (joke) VALUES (?)', (joke,))
#         self.conn_jokes.commit()
#         if not interaction.response.is_done():
#             await interaction.response.send_message("Joke added successfully.", ephemeral=True)
#         logging.info(f"Added new joke to the database: {joke}")

#     except sqlite3.Error as e:
#         logging.error(f"Database insert error: {e}")
#         if not interaction.response.is_done():
#             await interaction.response.send_message("An error occurred while adding the joke. Please try again later.", ephemeral=True)

# @app_commands.command(name="listjokes", description="List all Chuck Norris jokes in the database.")
# async def list_jokes(self, interaction: discord.Interaction):
#     try:
#         self.cursor_jokes.execute('SELECT joke FROM jokes')
#         jokes = self.cursor_jokes.fetchall()

#         if jokes:
#             joke_list = "\n".join([joke[0] for joke in jokes])
#             embed = discord.Embed(
#                 title="All Chuck Norris Jokes",
#                 description=joke_list,
#                 color=0x3498db
#             )

#             if not interaction.response.is_done():
#                 await interaction.response.send_message(embed=embed)
#             logging.info("Listed all Chuck Norris jokes successfully.")
#         else:
#             if not interaction.response.is_done():
#                 await interaction.response.send_message("No jokes found in the database.", ephemeral=True)
#             logging.warning("No jokes found to list.")

#     except sqlite3.Error as e:
#         logging.error(f"Database query error: {e}")
#         if not interaction.response.is_done():
#             await interaction.response.send_message("An error occurred while listing the jokes. Please try again later.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChuckJokesCog(bot))
