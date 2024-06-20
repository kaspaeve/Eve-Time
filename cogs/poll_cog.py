import discord
import sqlite3
import logging
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import re
import pytz

class PollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        try:
            self.conn = sqlite3.connect('chuck.db')
            self.conn.row_factory = sqlite3.Row  
            self.cursor = self.conn.cursor()
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS polls (
                                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   creator_id INTEGER,
                                   question TEXT,
                                   options TEXT,
                                   created_at DATETIME,
                                   expires_at DATETIME,
                                   message_id INTEGER,
                                   channel_id INTEGER
                                   )''')
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS votes (
                                   poll_id INTEGER,
                                   user_id INTEGER,
                                   option TEXT,
                                   UNIQUE(poll_id, user_id),
                                   FOREIGN KEY(poll_id) REFERENCES polls(id)
                                   )''')
            self.conn.commit()
            logging.info("Connected to the polls database successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")

        self.check_expired_polls.start()

    def cog_unload(self):
        try:
            self.check_expired_polls.cancel()
            self.conn.close()
            logging.info("PollCog unloaded and database connection closed.")
        except Exception as e:
            logging.error(f"Error during cog unload: {e}")

    @app_commands.command(name="create_poll", description="Create a poll with a question and options.")
    @app_commands.describe(duration="Duration for the poll (e.g., 10m for 10 minutes, 2h for 2 hours)",
                           question="The question for the poll",
                           option1="First option for the poll",
                           option2="Second option for the poll",
                           option3="Third option for the poll (optional)",
                           option4="Fourth option for the poll (optional)")
    async def create_poll(self, interaction: discord.Interaction, duration: str, question: str, option1: str, option2: str, option3: str = None, option4: str = None):
        await interaction.response.defer(ephemeral=True)

        options = [option for option in [option1, option2, option3, option4] if option]

        if len(options) < 2 or len(options) > 10:
            await interaction.followup.send("You must provide between 2 and 10 options for the poll.", ephemeral=True)
            return

        try:
            duration_delta, duration_str = self.parse_duration(duration)
        except ValueError as e:
            await interaction.followup.send(f"Invalid duration format: {e}", ephemeral=True)
            return

        created_at = datetime.utcnow()
        expires_at = created_at + duration_delta

        user_timezone = pytz.timezone('UTC')
        user_time = expires_at.replace(tzinfo=pytz.utc).astimezone(user_timezone)
        expiration_str = user_time.strftime('%I:%M %p %Z')

        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        poll_options = {emojis[i]: options[i] for i in range(len(options))}

        embed = discord.Embed(
            title="Chuck Norris has a new idea to vote on!",
            description=f"**{question}**\n\n" + "\n".join([f"{emoji} {option}" for emoji, option in poll_options.items()]),
            color=0x3498db,
            timestamp=user_time
        )
        embed.add_field(
            name=f"Poll will run for {duration_str}.",
            value=f"Thanks to {interaction.user.display_name}, we have a new poll!\n"
                  f"Vote wisely, as Chuck Norris is always watching!",
            inline=False
        )
        embed.set_footer(text=f"Poll ends • {expiration_str}")

        message = await interaction.channel.send(embed=embed)
        for emoji in poll_options.keys():
            await message.add_reaction(emoji)

        self.cursor.execute('''INSERT INTO polls (creator_id, question, options, created_at, expires_at, message_id, channel_id)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (interaction.user.id, question, str(poll_options), created_at, expires_at, message.id, interaction.channel.id))
        self.conn.commit()

        logging.info(f"Poll created by {interaction.user.id}: {question}")
        await interaction.followup.send("Poll created successfully.", ephemeral=True)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        message_id = reaction.message.id
        emoji = str(reaction.emoji)

        self.cursor.execute('SELECT * FROM polls WHERE message_id = ?', (message_id,))
        poll = self.cursor.fetchone()
        if poll:
            poll_id = poll['id']
            options = eval(poll['options'])

            if emoji in options:
                self.cursor.execute('SELECT * FROM votes WHERE poll_id = ? AND user_id = ?', (poll_id, user.id))
                existing_vote = self.cursor.fetchone()

                if existing_vote:
                   
                    poll_message = await reaction.message.channel.fetch_message(message_id)
                    for reaction_item in poll_message.reactions:
                        async for reacted_user in reaction_item.users():
                            if reacted_user == user and reaction_item.emoji != emoji:
                                await reaction_item.remove(user)
                    
                    self.cursor.execute('''UPDATE votes SET option = ? WHERE poll_id = ? AND user_id = ?''', (options[emoji], poll_id, user.id))
                    logging.info(f"User {user.id} changed their vote in poll {poll_id} to {options[emoji]}")
                else:
                    
                    self.cursor.execute('''INSERT INTO votes (poll_id, user_id, option)
                                           VALUES (?, ?, ?)''', (poll_id, user.id, options[emoji]))
                    logging.info(f"Vote recorded for poll {poll_id} by user {user.id}")

                self.conn.commit()

    @tasks.loop(minutes=1)
    async def check_expired_polls(self):
        now = datetime.utcnow()
        self.cursor.execute('SELECT * FROM polls WHERE expires_at <= ?', (now,))
        expired_polls = self.cursor.fetchall()

        for poll in expired_polls:
            poll_id = poll['id']
            channel_id = poll['channel_id']
            message_id = poll['message_id']
            question = poll['question']

            self.cursor.execute('SELECT option, COUNT(*) as votes FROM votes WHERE poll_id = ? GROUP BY option ORDER BY votes DESC', (poll_id,))
            results = self.cursor.fetchall()

            embed = discord.Embed(
                title="Poll Results",
                description=f"**Chuck Norris's wisdom has spoken! The results are in for the question:**\n\n**{question}**",
                color=0x3498db
            )

            if results:
                for result in results:
                    embed.add_field(name=result['option'], value=f"{result['votes']} votes", inline=False)
            else:
                embed.add_field(name="No Votes", value="Unfortunately, no one dared to vote.", inline=False)

            embed.set_footer(text="Chuck Norris had the poll and associated votes deleted from the database.")

            channel = self.bot.get_channel(channel_id)
            if channel:
                try:
                    poll_message = await channel.fetch_message(message_id)
                    await poll_message.reply(embed=embed)
                    logging.info(f"Poll results for poll {poll_id} sent to channel {channel_id}.")
                except discord.HTTPException as e:
                    logging.error(f"Failed to send poll results for poll {poll_id} to channel {channel_id}: {e}")

            self.cursor.execute('DELETE FROM polls WHERE id = ?', (poll_id,))
            self.cursor.execute('DELETE FROM votes WHERE poll_id = ?', (poll_id,))
            self.conn.commit()
            logging.info(f"Poll {poll_id} and associated votes deleted from the database.")

    @check_expired_polls.before_loop
    async def before_check_expired_polls(self):
        await self.bot.wait_until_ready()

    def parse_duration(self, duration_str):
        duration_regex = r'(?P<value>\d+)\s*(?P<unit>[a-zA-Z]+)'
        matches = re.findall(duration_regex, duration_str)

        if not matches:
            raise ValueError("No valid duration units found.")

        total_duration = timedelta()
        duration_components = []

        for value, unit in matches:
            value = int(value)
            unit = unit.lower()
            if unit in ['s', 'sec', 'second', 'seconds']:
                total_duration += timedelta(seconds=value)
                duration_components.append(f"{value} Second{'s' if value > 1 else ''}")
            elif unit in ['m', 'min', 'minute', 'minutes']:
                total_duration += timedelta(minutes=value)
                duration_components.append(f"{value} Minute{'s' if value > 1 else ''}")
            elif unit in ['h', 'hr', 'hour', 'hours']:
                total_duration += timedelta(hours=value)
                duration_components.append(f"{value} Hour{'s' if value > 1 else ''}")
            elif unit in ['d', 'day', 'days']:
                total_duration += timedelta(days=value)
                duration_components.append(f"{value} Day{'s' if value > 1 else ''}")
            elif unit in ['w', 'week', 'weeks']:
                total_duration += timedelta(weeks=value)
                duration_components.append(f"{value} Week{'s' if value > 1 else ''}")
            elif unit in ['mo', 'month', 'months']:
                total_duration += timedelta(days=value * 30)  
                duration_components.append(f"{value} Month{'s' if value > 1 else ''}")
            elif unit in ['y', 'yr', 'year', 'years']:
                total_duration += timedelta(days=value * 365)  
                duration_components.append(f"{value} Year{'s' if value > 1 else ''}")
            else:
                raise ValueError(f"Unknown time unit: {unit}")

        duration_str = " ".join(duration_components)
        return total_duration, duration_str

async def setup(bot):
    await bot.add_cog(PollCog(bot))
