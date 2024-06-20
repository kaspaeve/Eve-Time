import discord
import sqlite3
import asyncio
import logging
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import re
import pytz

class RemindCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('chuck.db')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (
                               id INTEGER PRIMARY KEY,
                               user_id INTEGER,
                               channel_id INTEGER,
                               message TEXT,
                               remind_time DATETIME,
                               dm BOOLEAN
                               )''')
        self.conn.commit()
        
        logging.info("Connected to the reminders database successfully.")

        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()
        self.conn.close()

    @app_commands.command(name="remind", description="Set a reminder with a specified time and message")
    async def remind(self, interaction: discord.Interaction, time: str, message: str):
        time_pattern = r'(?P<value>\d+)\s*(?P<unit>s|sec|seconds?|m|mn|min|minutes?|h|hr|hrs?|hours?|d|days?|M|months?|y|years?)'
        matches = re.findall(time_pattern, time, re.IGNORECASE)
        if not matches:
            await interaction.response.send_message("Invalid time format. Use numbers followed by s, sec, m, min, h, hr, d, days, M, months, y, years, etc.", ephemeral=True)
            return

        remind_time = datetime.now(pytz.UTC) 
        for value, unit in matches:
            value = int(value)
            unit = unit.lower()
            if unit in ['s', 'sec', 'second', 'seconds']:
                remind_time += timedelta(seconds=value)
            elif unit in ['m', 'mn', 'min', 'minute', 'minutes']:
                remind_time += timedelta(minutes=value)
            elif unit in ['h', 'hr', 'hrs', 'hour', 'hours']:
                remind_time += timedelta(hours=value)
            elif unit in ['d', 'day', 'days']:
                remind_time += timedelta(days=value)
            elif unit in ['M', 'month', 'months']:
                remind_time += timedelta(days=value * 30)
            elif unit in ['y', 'year', 'years']:
                remind_time += timedelta(days=value * 365)

        dm = True
        channel_id = None

        self.cursor.execute('INSERT INTO reminders (user_id, channel_id, message, remind_time, dm) VALUES (?, ?, ?, ?, ?)',
                            (interaction.user.id, channel_id, message, remind_time, dm))
        self.conn.commit()
        logging.info(f"Reminder set for user {interaction.user.id} at {remind_time}")

        response = f"Reminder set for {remind_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        await interaction.response.send_message(response, ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        logging.info("Checking for reminders...")
        now = datetime.now(pytz.UTC)
        logging.info(f"Current time for checking: {now}")

        self.cursor.execute('SELECT * FROM reminders')
        reminders = self.cursor.fetchall()
        logging.info(f"Total reminders in database: {len(reminders)}")

        self.cursor.execute('SELECT id, user_id, message FROM reminders WHERE remind_time <= ?', (now,))
        due_reminders = self.cursor.fetchall()
        logging.info(f"Found {len(due_reminders)} reminders to notify.")

        for reminder in due_reminders:
            reminder_id = reminder['id']
            user_id = reminder['user_id']
            message = reminder['message']

            logging.info(f"Attempting to send reminder {reminder_id} to user {user_id}")
            user = self.bot.get_user(user_id)

            if user is None:
                logging.warning(f"User {user_id} not found in cache. Attempting to fetch from API.")
                try:
                    user = await self.bot.fetch_user(user_id)
                    logging.info(f"User {user_id} successfully fetched from API.")
                except discord.DiscordException as e:
                    logging.error(f"Failed to fetch user {user_id}: {e}")
                    continue

            try:
                if user:
                    await user.send(f"Reminder: {message}")
                    logging.info(f"Reminder {reminder_id} sent to user {user_id} via DM.")
                else:
                    logging.warning(f"Unable to send reminder to user {user_id}, user object is None.")
            except discord.Forbidden:
                logging.error(f"Cannot send DM to user {user_id}. Permission denied.")
            except discord.HTTPException as e:
                logging.error(f"Failed to send reminder {reminder_id} to user {user_id}: {e}")

            self.cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
            self.conn.commit()
            logging.info(f"Reminder {reminder_id} deleted from database.")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RemindCog(bot))
