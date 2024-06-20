import discord
import feedparser
import sqlite3
import logging
from discord.ext import commands, tasks
from decouple import config
from datetime import datetime

class NewsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.news_channel_id = int(config('NEWS_CHANNEL_ID'))

        try:
            self.conn = sqlite3.connect('chuck.db')
            self.cursor = self.conn.cursor()
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS news (
                                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   title TEXT,
                                   link TEXT,
                                   published DATETIME,
                                   sent BOOLEAN DEFAULT 0,
                                   source TEXT,
                                   UNIQUE(title, link)
                                   )''')
            self.conn.commit()
            logging.info("Connected to the news database successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")

        self.feeds = {
            'patch-notes': 'https://www.eveonline.com/rss/patch-notes',
            'dev-blogs': 'https://www.eveonline.com/rss/dev-blogs',
            'news': 'https://www.eveonline.com/rss/news'
        }

        self.check_news_feed.start()
        self.hourly_log.start()

    def cog_unload(self):
        try:
            self.check_news_feed.cancel()
            self.hourly_log.cancel()
            self.conn.close()
            logging.info("NewsCog unloaded and database connection closed.")
        except Exception as e:
            logging.error(f"Error during cog unload: {e}")

    @tasks.loop(minutes=10)
    async def check_news_feed(self):
        logging.info("Checking for news updates...")
        try:
            for source, url in self.feeds.items():
                logging.info(f"Fetching articles from {source} feed: {url}")
                feed = feedparser.parse(url)
                if feed.bozo:
                    logging.error(f"Failed to parse feed {source}: {feed.bozo_exception}")
                    continue

                self.cursor.execute('SELECT COUNT(*) FROM news')
                if self.cursor.fetchone()[0] == 0:
                    logging.info("Database is empty, fetching the last 5 articles.")
                    for entry in feed.entries[:5]:
                        title = entry.title
                        link = entry.link
                        published = datetime(*entry.published_parsed[:6])
                        try:
                            self.cursor.execute('INSERT INTO news (title, link, published, sent, source) VALUES (?, ?, ?, ?, ?)', (title, link, published, 1, source))
                            self.conn.commit()
                            logging.info(f"Article '{title}' from {source} added to database and sending to channel.")

                            channel = self.bot.get_channel(self.news_channel_id)
                            if channel:
                                embed = discord.Embed(title=title, url=link, description=f"Source: {source.capitalize()}", timestamp=published, color=0x3498db)
                                embed.set_footer(text="EVE Online News")
                                await channel.send(embed=embed)
                                logging.info(f"Article '{title}' sent to channel: {channel.name}")
                            else:
                                logging.warning(f"Channel with ID {self.news_channel_id} not found.")
                        except sqlite3.IntegrityError as e:
                            logging.error(f"Integrity error while inserting news into database: {e}")
                        except Exception as e:
                            logging.error(f"Error while sending or inserting news article: {e}")

                for entry in feed.entries:
                    title = entry.title
                    link = entry.link
                    published = datetime(*entry.published_parsed[:6])

                    self.cursor.execute('SELECT * FROM news WHERE title = ? AND link = ?', (title, link))
                    if not self.cursor.fetchone():
                        try:
                            self.cursor.execute('INSERT INTO news (title, link, published, sent, source) VALUES (?, ?, ?, ?, ?)', (title, link, published, 0, source))
                            self.conn.commit()
                            logging.info(f"New article '{title}' from {source} added to the database.")
                        except sqlite3.IntegrityError as e:
                            logging.error(f"Integrity error while inserting news into database: {e}")
                        except Exception as e:
                            logging.error(f"Error while inserting news into database: {e}")

                    self.cursor.execute('SELECT * FROM news WHERE title = ? AND link = ? AND sent = 0', (title, link))
                    if self.cursor.fetchone():
                        try:
                            channel = self.bot.get_channel(self.news_channel_id)
                            if channel:
                                embed = discord.Embed(title=title, url=link, description=f"Source: {source.capitalize()}", timestamp=published, color=0x3498db)
                                embed.set_footer(text="EVE Online News")
                                await channel.send(embed=embed)
                                logging.info(f"News article '{title}' from {source} sent to channel: {channel.name}")

                                self.cursor.execute('UPDATE news SET sent = 1 WHERE title = ? AND link = ?', (title, link))
                                self.conn.commit()
                            else:
                                logging.warning(f"Channel with ID {self.news_channel_id} not found.")
                        except Exception as e:
                            logging.error(f"Error while sending news article to channel: {e}")
                    else:
                        logging.info(f"Article '{title}' from {source} already sent or exists in the database.")

        except Exception as e:
            logging.error(f"Error during news feed check: {e}")

    @tasks.loop(hours=1)
    async def hourly_log(self):
        logging.info("Hourly check log: Bot is running and checking for news updates.")

    @check_news_feed.before_loop
    async def before_check_news_feed(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(NewsCog(bot))
