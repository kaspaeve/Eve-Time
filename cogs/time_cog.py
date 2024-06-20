import discord
import datetime
import pytz
import logging
import requests 
from discord.ext import commands
from discord import app_commands
from decouple import config

class TimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_channel_id = int(config('ALLOWED_CHANNEL_ID'))

    @app_commands.command(name="time", description="Get the current date/time across various time zones")
    async def time(self, interaction: discord.Interaction):
        current_time_utc = datetime.datetime.utcnow()
        time_format = '%Y-%m-%d %H:%M:%S'

        utc_timezone = pytz.timezone('UTC')
        current_time_utc = utc_timezone.localize(current_time_utc)
        time_str_utc = current_time_utc.strftime(time_format)

        time_zones = {
            'AEST': 'Australia/Sydney',
            'EST': 'America/New_York',
            'CST': 'America/Chicago',
            'MST': 'America/Denver',
            'PST': 'America/Los_Angeles'
        }

        embed = discord.Embed(
            title="Current Date/Time",
            description=f"**Eve Time:** [**{time_str_utc}**](https://time.is/UTC)",
            color=0x3498db
        )

        for zone, tz in time_zones.items():
            other_timezone = pytz.timezone(tz)
            current_time_other_zone = current_time_utc.astimezone(other_timezone)
            time_str_other_zone = current_time_other_zone.strftime(time_format)
            embed.add_field(name=zone, value=time_str_other_zone, inline=False)

        # Fetch and add the number of users online in EVE Online
        users_online = self.fetch_users_online()
        embed.add_field(
            name="EVE Online Users Online",
            value=f"**{users_online}** players",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

        # Log the event
        logging.info(f"Time command used by {interaction.user.name} in server {interaction.guild.name if interaction.guild else 'DM'}")

    def fetch_users_online(self):
        """
        Fetch the number of users currently online in EVE Online.
        """
        try:
            response = requests.get("https://esi.evetech.net/latest/status/")
            if response.status_code == 200:
                data = response.json()
                return data.get('players', 'N/A')
            else:
                logging.error(f"Failed to fetch users online: {response.status_code}")
                return 'N/A'
        except requests.RequestException as e:
            logging.error(f"Error fetching users online: {e}")
            return 'N/A'

async def setup(bot):
    await bot.add_cog(TimeCog(bot))
