import discord
import logging
import asyncio
import signal
from discord.ext import commands
from decouple import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

try:
    bot_token = config('BOT_TOKEN')
    guild_id = int(config('GUILD_ID'))
    allowed_channel_id = int(config('ALLOWED_CHANNEL_ID'))
    news_channel_id = int(config('NEWS_CHANNEL_ID'))
except Exception as e:
    logger.error(f"Configuration error: {e}")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True  
intents.guilds = True  
intents.dm_messages = True  

bot = commands.Bot(command_prefix='!', intents=intents)

async def load_cogs():
    await bot.wait_until_ready()
    cogs = [
        'cogs.ping', 
        'cogs.time_cog', 
        'cogs.remind_cog', 
        'cogs.news_cog', 
        'cogs.poll_cog', 
        'cogs.help_cog',
        'cogs.chuck_jokes_cog',
        'cogs.zkillboard_cog', 
        'cogs.confess_cog',
        'cogs.timer_cog'
    ]
    for cog in cogs:
        if cog not in bot.extensions:
            try:
                await bot.load_extension(cog)
                logger.info(f'{cog} loaded')
                print(f'{cog} loaded')
            except Exception as e:
                logger.error(f'Error loading {cog}: {e}')
                print(f'Error loading {cog}: {e}')

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    print(f'Logged in as {bot.user.name}')

    await load_cogs()
    
    ascii_art = """
       _____ _    _ _    _  _____ _  __  _   _  ____  _____  _____  _____  _____ 
      / ____| |  | | |  | |/ ____| |/ / | \\ | |/ __ \\|  __ \\|  __ \\|_   _|/ ____|
     | |    | |__| | |  | | |    | ' /  |  \\| | |  | | |__) | |__) | | | | (___  
     | |    |  __  | |  | | |    |  <   | . ` | |  | |  _  /|  _  /  | |  \\___ \\ 
     | |____| |  | | |__| | |____| . \\  | |\\  | |__| | | \\ \\| | \\ \\ _| |_ ____) |
      \\_____|_|  |_|\\____/ \\_____|_|\\_\\ |_| \\_|\\____/|_|  \\_\\_|  \\_\\_____|_____/ 
                                                                                 
    """
    print(ascii_art)
    print(f'Chuck Norris by kaspa v1.06')
    logger.info("Bot is up and running!")

    try:
        guild = discord.Object(id=guild_id)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"Slash commands registered for server: {guild_id}")
    except Exception as e:
        logger.error(f"Error registering slash commands: {e}")

@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Error in command {ctx.command}: {error}")
    await ctx.send(f"An error occurred: {error}")

async def shutdown():
    logger.info("Shutting down bot...")
    await bot.close()

def handle_shutdown_signal(*args):
    asyncio.get_event_loop().create_task(shutdown())

signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)

bot.run(bot_token)
