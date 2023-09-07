import discord
import datetime
import pytz
import logging
from discord.ext import commands
from decouple import config

# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

bot_token = config('BOT_TOKEN')
allowed_channel_id = int(config('ALLOWED_CHANNEL_ID'))  # Convert to int since channel IDs are integers

intents = discord.Intents.default()
intents.message_content = True  # Allows access to message content
intents.guilds = True  # Allows access to guild information (servers)
intents.dm_messages = False  # Disables access to direct messages

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def time(ctx):
    try:
        if ctx.channel.id == allowed_channel_id:
            current_time_utc = datetime.datetime.utcnow()
            time_format = '%Y-%m-%d %H:%M:%S'

            utc_timezone = pytz.timezone('UTC')
            current_time_utc = utc_timezone.localize(current_time_utc)
            time_str_utc = current_time_utc.strftime(time_format)

            time_zones = {
                'EST': 'America/New_York',
                'CST': 'America/Chicago',
                'MST': 'America/Denver',
                'PST': 'America/Los_Angeles'
            }

            embed = discord.Embed(title="Current Date/Time", description=f"**Eve Time:** **__{time_str_utc}__**", color=0x3498db)

            for zone, tz in time_zones.items():
                other_timezone = pytz.timezone(tz)
                current_time_other_zone = current_time_utc.astimezone(other_timezone)
                time_str_other_zone = current_time_other_zone.strftime(time_format)
                embed.add_field(name=zone, value=time_str_other_zone, inline=False)

            await ctx.send(embed=embed)
            logger.info(f"Chuck Norris sent {ctx.author.name} the current Eve Time in channel {ctx.channel.id}")
            print(f"Chuck Norris sent {ctx.author.name} the current Eve Time")

        else:
            await ctx.send('This command is only allowed in the specified channel.')
            logger.warning(f"{ctx.author.name} tried to get the time in an unauthorized channel: {ctx.channel.id}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
        await ctx.send('An error occurred. Please try again later.')

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    print(f'Logged in as {bot.user.name}')

bot.run(bot_token)
