import discord
import sqlite3
import logging
import re
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
from decouple import config

class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('chuck.db')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
        self._initialize_statistics()

        self.admin_user_id = int(config('ADMIN_USER_ID'))

        logging.info("Connected to the timers database successfully.")

        self.check_timers.start()

    def cog_unload(self):
        self.check_timers.cancel()
        self.conn.close()

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS timers (
                               id INTEGER PRIMARY KEY,
                               user_id INTEGER,
                               channel_id INTEGER,
                               duration INTEGER,
                               start_time DATETIME,
                               end_time DATETIME,
                               label TEXT
                               )''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS timer_statistics (
                               id INTEGER PRIMARY KEY AUTOINCREMENT,
                               created_timers INTEGER DEFAULT 0,
                               processed_timers INTEGER DEFAULT 0
                               )''')
        
        self.conn.commit()

    def _initialize_statistics(self):
        """Initialize statistics in the timer_statistics table if they do not exist."""
        self.cursor.execute('SELECT COUNT(*) FROM timer_statistics')
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute('INSERT INTO timer_statistics (created_timers, processed_timers) VALUES (0, 0)')
            self.conn.commit()

    def _update_statistics(self, column_name):
        """Update the count of timers in the statistics table."""
        self.cursor.execute(f'UPDATE timer_statistics SET {column_name} = {column_name} + 1')
        self.conn.commit()

    @app_commands.command(name="start_timer", description="Starts a timer for the specified duration with a label (e.g., '10s workout').")
    async def start_timer(self, interaction: discord.Interaction, duration: str, label: str):
        delta = self._parse_duration(duration)
        if delta is None:
            embed = discord.Embed(
                title="Invalid Duration Format",
                description="Please use a format like `10s`, `5m`, `1h`, or `2d`.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        start_time = datetime.utcnow()
        end_time = start_time + delta

        timer_id = self._add_timer(interaction.user.id, interaction.channel_id, int(delta.total_seconds()), start_time, end_time, label)
        self._update_statistics('created_timers')
        logging.info(f"Timer set for user {interaction.user.id} with label '{label}' ending at {end_time}")

        embed = discord.Embed(
            title="Timer Set",
            description="Your timer has been set successfully.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Label", value=label, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="End Time", value=end_time.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=False)
        embed.add_field(name="Timer ID", value=str(timer_id), inline=True)
        embed.add_field(name="Delete Timer", value=f"To delete this timer, use: `/cancel_timer {timer_id}`", inline=False)
        embed.set_footer(text="You can cancel the timer anytime using the provided ID.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cancel_timer", description="Cancels a specific timer by its ID.")
    async def cancel_timer(self, interaction: discord.Interaction, timer_id: int):
        timer = self._get_timer_by_id(timer_id)
        if timer is None:
            embed = discord.Embed(
                title="Timer Not Found",
                description=f"No timer found with ID {timer_id}.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if timer['user_id'] != interaction.user.id:
            embed = discord.Embed(
                title="Unauthorized",
                description=f"You do not have permission to delete the timer with ID {timer_id}.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self._delete_timer_by_id(interaction.user.id, timer_id)
        logging.info(f"Canceled timer {timer_id} for user {interaction.user.id}")

        embed = discord.Embed(
            title="Timer Canceled",
            description=f"The timer with ID {timer_id} has been successfully canceled.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="timer_stats", description="View timer statistics (Admin only).")
    async def timer_stats(self, interaction: discord.Interaction):
        if interaction.user.id != self.admin_user_id:
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have the required permissions to view timer statistics.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        self.cursor.execute('SELECT created_timers, processed_timers FROM timer_statistics')
        stats = self.cursor.fetchone()
        created_timers = stats['created_timers']
        processed_timers = stats['processed_timers']
        
        pending_count = self._count_pending_timers()
        
        logging.info(f"Admin {interaction.user.id} requested timer stats.")
        
        embed = discord.Embed(
            title="Timer Statistics",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Created Timers", value=str(created_timers), inline=False)
        embed.add_field(name="Total Processed Timers", value=str(processed_timers), inline=False)
        embed.add_field(name="Pending Timers", value=str(pending_count), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @tasks.loop(seconds=10)
    async def check_timers(self):
        now = datetime.utcnow()
        logging.info(f"Checking for expired timers at {now}")

        due_timers = self._get_due_timers(now)
        logging.info(f"Found {len(due_timers)} timers to notify.")

        for timer in due_timers:
            timer_id = timer['id']
            user_id = timer['user_id']
            label = timer['label']

            logging.info(f"Timer {timer_id} with label '{label}' has expired. Notifying user {user_id}.")
            user = self.bot.get_user(user_id)

            if not user:
                try:
                    user = await self.bot.fetch_user(user_id)
                    logging.info(f"Fetched user {user_id} from API.")
                except discord.NotFound:
                    logging.error(f"User {user_id} not found. Unable to send notification for timer {timer_id} with label '{label}'.")
                    continue
                except discord.HTTPException as e:
                    logging.error(f"Failed to fetch user {user_id}: {e}")
                    continue

            if user:
                await self._notify_user(user, timer_id, label)

            self._delete_timer(timer_id)
            self._update_statistics('processed_timers')

    @check_timers.before_loop
    async def before_check_timers(self):
        await self.bot.wait_until_ready()

    def _parse_duration(self, duration):
        """Parse the duration string into a timedelta object."""
        time_pattern = r'(?P<value>\d+)\s*(?P<unit>s|sec|seconds?|m|min|minutes?|h|hours?|d|days?)'
        matches = re.match(time_pattern, duration, re.IGNORECASE)
        if not matches:
            return None

        value = int(matches.group('value'))
        unit = matches.group('unit').lower()

        if unit in ['s', 'sec', 'second', 'seconds']:
            return timedelta(seconds=value)
        elif unit in ['m', 'min', 'minute', 'minutes']:
            return timedelta(minutes=value)
        elif unit in ['h', 'hour', 'hours']:
            return timedelta(hours=value)
        elif unit in ['d', 'day', 'days']:
            return timedelta(days=value)

        return None

    def _add_timer(self, user_id, channel_id, duration, start_time, end_time, label):
        """Add a timer to the database with a label and return the timer ID."""
        self.cursor.execute('INSERT INTO timers (user_id, channel_id, duration, start_time, end_time, label) VALUES (?, ?, ?, ?, ?, ?)',
                            (user_id, channel_id, duration, start_time, end_time, label))
        self.conn.commit()
        return self.cursor.lastrowid

    def _get_timer_by_id(self, timer_id):
        """Retrieve a timer by its ID."""
        self.cursor.execute('SELECT * FROM timers WHERE id = ?', (timer_id,))
        return self.cursor.fetchone()

    def _delete_timer_by_id(self, user_id, timer_id):
        """Delete a timer by its ID and user ID."""
        self.cursor.execute('DELETE FROM timers WHERE id = ? AND user_id = ?', (timer_id, user_id))
        self.conn.commit()

    def _get_due_timers(self, now):
        """Retrieve all timers that are due."""
        self.cursor.execute('SELECT * FROM timers WHERE end_time <= ?', (now,))
        return self.cursor.fetchall()

    def _count_pending_timers(self):
        """Count all pending timers."""
        now = datetime.utcnow()
        self.cursor.execute('SELECT COUNT(*) FROM timers WHERE end_time > ?', (now,))
        return self.cursor.fetchone()[0]

    async def _notify_user(self, user, timer_id, label):
        """Notify the user via DM that their timer has ended."""
        try:
            embed = discord.Embed(
                title="Timer Ended",
                description="Your timer has ended!",
                color=discord.Color.blue()
            )
            embed.add_field(name="Label", value=f"{label}", inline=False)
            embed.add_field(name="Timer ID", value=str(timer_id), inline=False)
            
            await user.send(embed=embed)
            logging.info(f"Timer {timer_id} notification with label '{label}' sent to user {user.id}.")
        except discord.Forbidden:
            logging.error(f"Cannot send DM to user {user.id}. Permission denied.")
        except discord.HTTPException as e:
            logging.error(f"Failed to send timer notification for timer {timer_id} with label '{label}': {e}")

    def _delete_timer(self, timer_id):
        """Delete a timer from the database."""
        self.cursor.execute('DELETE FROM timers WHERE id = ?', (timer_id,))
        self.conn.commit()

async def setup(bot):
    await bot.add_cog(TimerCog(bot))
