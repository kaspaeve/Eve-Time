import discord
from discord.ext import commands
from decouple import config
import logging
import datetime
import pytz
import feedparser
import asyncio
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import declarative_base
import aiohttp
import re

# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Discord Bot Setup
bot_token = config('BOT_TOKEN')
allowed_channel_id = int(config('ALLOWED_CHANNEL_ID'))
feed_channel_id = int(config('FEED_CHANNEL_ID'))
version = 'v1.04'

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.dm_messages = False

bot = commands.Bot(command_prefix='!', intents=intents)

# Database Setup
engine = create_engine('sqlite:///chuck.db')  # New database file
Base = declarative_base()

class LastUpdate(Base):
    __tablename__ = 'last_update'
    id = Column(String, primary_key=True, unique=True, default='eve_online_patch_notes')
    last_published = Column(DateTime)

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    reminder_time = Column(DateTime, nullable=False)
    reminder_message = Column(String, nullable=False)
    sent = Column(Boolean, default=False, nullable=False)

# Create all tables in the database
Base.metadata.create_all(engine)

# Setup session factory
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

@bot.command(name='remindme') 
async def remindme(ctx, time_string: str, *, reminder: str = "Reminder!"):
    """Set a reminder. Example usage: !remindme 10m Check the oven."""
    # Parsing time_string to determine reminder time
    delta = None
    match = re.match(r"(\d+)([smhd])", time_string)
    if match:
        amount, unit = match.groups()
        amount = int(amount)
        if unit == 's':
            delta = datetime.timedelta(seconds=amount)
        elif unit == 'm':
            delta = datetime.timedelta(minutes=amount)
        elif unit == 'h':
            delta = datetime.timedelta(hours=amount)
        elif unit == 'd':
            delta = datetime.timedelta(days=amount)
    else:
        await ctx.send("Sorry, I couldn't understand the time. Please use [number][s/m/h/d].")
        return

    reminder_time = datetime.datetime.utcnow() + delta
    session = DBSession()
    new_reminder = Reminder(user_id=str(ctx.author.id),
                            reminder_time=reminder_time,
                            reminder_message=reminder,
                            sent=False)
    session.add(new_reminder)
    session.commit()
    session.close()
    
    await ctx.send(f"Got it! I'll remind you about '{reminder}' at {reminder_time.strftime('%Y-%m-%d %H:%M:%S UTC')}.")
    logger.info(f"RemindMe command called by {ctx.author} with time_string: {time_string} and reminder: {reminder}.")

async def check_reminders():
    """Check for due reminders and send them."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.datetime.utcnow()
        session = DBSession()
        due_reminders = session.query(Reminder).filter(Reminder.reminder_time <= now, Reminder.sent == False).all()
        logger.info(f"Checking for due reminders at {now}, found {len(due_reminders)} due reminders.")
        
        for reminder in due_reminders:
            try:
                user = await bot.fetch_user(int(reminder.user_id))  # Changed to fetch_user for reliability
                if user:
                    await user.send(f"Here's your reminder: {reminder.reminder_message}")
                    reminder.sent = True  # Mark as sent
                    logger.info(f"Sent reminder to {user.name} (ID: {user.id}).")
                else:
                    logger.warning(f"Could not find user ID {reminder.user_id}.")
            except discord.Forbidden:
                logger.info(f"Cannot send DM to {user.name} (ID: {user.id}).")
            except Exception as e:
                logger.error(f"Error sending reminder to {user.name} (ID: {user.id}): {e}", exc_info=True)
        
        session.commit()  # Commit all changes
        session.close()
        await asyncio.sleep(60)  # Check every 60 seconds

def log_error_with_art(message):
    art = r"""
    /~`|_     _|   |\ | _  _ _. _
    \_,| ||_|(_|<  | \|(_)| | |_\ 
                                  """
    logger.error(f"{message}\n{art}")

@bot.event
async def on_ready():
    log_error_with_art(f"")
    logger.info(f'Chuck Norris is running {version} by kaspa')
    logger.info(f'Logged in as {bot.user.name}')

    bot.loop.create_task(check_reminders())
    bot.loop.create_task(rss_feed_task())

bot.run(bot_token)

