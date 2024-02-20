import discord
from discord.ext import commands
from decouple import config
import logging
import datetime
import pytz
import feedparser
import asyncio
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
import aiohttp

# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Discord Bot Setup
bot_token = config('BOT_TOKEN')
allowed_channel_id = int(config('ALLOWED_CHANNEL_ID'))
feed_channel_id = int(config('FEED_CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.dm_messages = False

bot = commands.Bot(command_prefix='!', intents=intents)

# Database Setup
Base = declarative_base()

class LastUpdate(Base):
    __tablename__ = 'last_update'
    id = Column(String, primary_key=True, default='eve_online_patch_notes')
    last_published = Column(DateTime)

engine = create_engine('sqlite:///rss_feed.db')
Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()

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
                'AEST': 'Australia/Sydney', 
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
async def check_rss_feed():
    feed_url = 'https://www.eveonline.com/rss/patch-notes'
    try:
        feed = feedparser.parse(feed_url)
        
        # Query the last update from the database
        try:
            last_update = session.query(LastUpdate).filter_by(id='eve_online_patch_notes').first()
        except NoResultFound:
            last_update = None
        
        if feed.entries:
            for entry in reversed(feed.entries):  # Check from oldest to newest
                published = datetime.datetime(*entry.published_parsed[:6])
                if last_update is None or last_update.last_published is None or published > last_update.last_published:
                    channel = bot.get_channel(feed_channel_id)
                    if channel:  # Check if the channel was found
                        embed = discord.Embed(title=entry.title, url=entry.link, description="New EVE Online patch notes available!", color=0x3498db)
                        await channel.send(embed=embed)
                        if last_update:
                            last_update.last_published = published
                        else:
                            last_update = LastUpdate(id='eve_online_patch_notes', last_published=published)
                            session.add(last_update)
                        session.commit()
                    else:
                        logger.error(f"Channel with ID {feed_channel_id} not found.")
            logger.info("RSS feed checked successfully.")
    except Exception as e:
        logger.error(f"An error occurred while checking the RSS feed: {e}")

async def rss_feed_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await check_rss_feed()
        # Adjust sleep time as needed; here it's set to 1800 seconds (30 minutes)
        await asyncio.sleep(3600)  # Check every 30 minutes
    logger.info("Bot is closed, stopping the RSS feed task.")
async def fetch_eve_online_status():
    """Fetches EVE Online server status."""
    url = "https://esi.evetech.net/latest/status/?datasource=tranquility"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                status = 'Online'
                player_count = data.get('players', 'N/A')
            else:
                status = 'Offline'
                player_count = 'N/A'
    return status, player_count

@bot.command(name='status', aliases=['tq', 'eve'])
async def eve_status(ctx):
    """Shows the current status of EVE Online's Tranquility server."""
    status, player_count = await fetch_eve_online_status()

    embed = discord.Embed(title="EVE Online Status", color=0x3498db)
    embed.set_footer(text="I'll be the Chuck to your Norris.")
    embed.set_thumbnail(url="https://image.eveonline.com/Alliance/434243723_64.png")
    embed.add_field(name="Server State", value=status, inline=True)
    embed.add_field(name="Player Count", value=player_count, inline=True)

    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    print(f'Logged in as {bot.user.name}')
    bot.loop.create_task(rss_feed_task())

bot.run(bot_token)

