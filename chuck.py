import discord
import datetime
import pytz
from discord.ext import commands


bot_token = 'MjgyNjU2NjY1NzUxMjU3MDg4.Gxyg1w.7rnJJjHUZOfcHp1mKJjA16wstcGodsGmYWkJqo'
allowed_channel_id = 463535782750060544  # Replace with the ID of the allowed channel

intents = discord.Intents.default()
intents.message_content = True  # Allows access to message content
intents.guilds = True  # Allows access to guild information (servers)
intents.dm_messages = False  # Disables access to direct messages

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def time(ctx):
    if ctx.channel.id == allowed_channel_id:
        current_time_utc = datetime.datetime.utcnow()
        time_format = '%Y-%m-%d %H:%M:%S'

        utc_timezone = pytz.timezone('UTC')
        current_time_utc = utc_timezone.localize(current_time_utc)
        time_str_utc = current_time_utc.strftime(time_format)

        time_zones = {
            'CST': 'America/Chicago',
            'EST': 'America/New_York',
            'PST': 'America/Los_Angeles',
            'MST': 'America/Denver'
        }

        time_str_other_zones = ''
        for zone, tz in time_zones.items():
            other_timezone = pytz.timezone(tz)
            current_time_other_zone = current_time_utc.astimezone(other_timezone)
            time_str_other_zone = current_time_other_zone.strftime(time_format)
            time_str_other_zones += f'\n{zone}: {time_str_other_zone}'

        await ctx.send(f'Current Date/Time:\nEve Time: {time_str_utc}\n{time_str_other_zones}')
    else:
        await ctx.send('This command is only allowed in the specified channel.')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

bot.run(bot_token)
