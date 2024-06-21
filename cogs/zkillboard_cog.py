import discord
from discord.ext import commands
from decouple import config
import aiohttp
import asyncio
import sqlite3
import logging
import json
from datetime import datetime

log = logging.getLogger(__name__)

class ZKillboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.region_ids = list(map(int, config('REGION_ID').split(',')))  # Region IDs from .env, comma-separated
        self.min_value = int(config('MIN_VALUE'))  # Minimum ISK value to consider as a valuable kill
        self.kills_channel_id = int(config('KILLS_CHANNEL_ID'))

        self.kills_processed = set()

        try:
            self.conn = sqlite3.connect('chuck.db')
            self.cursor = self.conn.cursor()
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS processed_kills (
                                   kill_id INTEGER PRIMARY KEY,
                                   processed_at DATETIME
                                   )''')
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS metadata (
                                   key TEXT PRIMARY KEY,
                                   value TEXT
                                   )''')

            self.cursor.execute('SELECT value FROM metadata WHERE key = "last_processed_time"')
            row = self.cursor.fetchone()
            self.last_processed_time = row[0] if row else None

            self.conn.commit()
            log.info(f"Connected to the kills database successfully. Last processed killmail time: {self.last_processed_time}")
        except sqlite3.Error as e:
            log.error(f"Database connection error: {e}")

        self.listen_for_kills_task = self.bot.loop.create_task(self.listen_for_kills())

    async def listen_for_kills(self):
        log.debug("Starting to listen for killmails.")
        while True:
            try:
                log.info("Starting a new cycle of killmail checks.")
                await self.get_new_killmails()
                log.info("Completed a cycle of killmail checks.")
                await asyncio.sleep(60)
            except (json.JSONDecodeError, KeyError) as e:
                log.exception("Error in killmail data structure: %s", e)
                await asyncio.sleep(10)
            except aiohttp.ClientError as e:
                log.exception("Network error when requesting new mails: %s", e)
                await asyncio.sleep(10)
            except Exception as e:
                log.exception("Unexpected error: %s", e)
                await asyncio.sleep(10)

    async def get_new_killmails(self):
        for region_id in self.region_ids:
            log.info(f"Processing region ID: {region_id}")
            url = f"https://zkillboard.com/api/kills/regionID/{region_id}/"
            log.info(f"Fetching killmails from URL: {url}")
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as resp:
                        content_type = resp.headers.get('Content-Type', '').lower()

                        if 'application/json' not in content_type:
                            log.error(f"Unexpected Content-Type {content_type} from URL {url}")
                            content = await resp.text()
                            log.debug(f"Response content: {content[:500]}")
                            continue

                        if resp.status != 200:
                            log.error(f"Failed to fetch killmails for region {region_id}: HTTP {resp.status}")
                            continue

                        try:
                            data = await resp.json()
                            log.debug(f"Fetched data: {json.dumps(data, indent=4)}")

                            processed_count = 0

                            for package in data:
                                killmail_id = package.get('killmail_id')
                                zkb = package.get('zkb', {})
                                hash_value = zkb.get('hash')

                                if not killmail_id or not hash_value:
                                    log.warning(f"Missing or invalid killmail ID or hash for package: {json.dumps(package)}")
                                    continue

                                self.cursor.execute('SELECT * FROM processed_kills WHERE kill_id = ?', (killmail_id,))
                                if self.cursor.fetchone():
                                    log.info(f"Killmail ID {killmail_id} already processed, stopping further checks for region {region_id}.")
                                    break

                                detailed_killmail = await self.fetch_killmail_details(killmail_id, hash_value)
                                if not detailed_killmail:
                                    continue

                                killmail_time = detailed_killmail.get('killmail_time')
                                if not killmail_time:
                                    log.warning(f"Missing killmail_time for detailed killmail ID {killmail_id}")
                                    continue

                                killmail_time_dt = datetime.strptime(killmail_time, "%Y-%m-%dT%H:%M:%SZ")

                                if self.last_processed_time:
                                    last_processed_dt = datetime.strptime(self.last_processed_time, "%Y-%m-%dT%H:%M:%SZ")
                                    if killmail_time_dt <= last_processed_dt:
                                        log.info(f"Skipping old killmail ID {killmail_id} with timestamp {killmail_time}, stopping further checks for region {region_id}.")
                                        break

                                if processed_count < 50:
                                    await self.process_killmail(detailed_killmail, zkb, killmail_time_dt)
                                    processed_count += 1

                            log.info(f"Processed {processed_count} killmails for region {region_id}")
                        except json.JSONDecodeError as e:
                            log.error(f"JSON decode error for URL {url}: {e}")
                except Exception as e:
                    log.exception(f"Unexpected error fetching killmails: {e}")

    async def fetch_killmail_details(self, killmail_id, hash_value):
        url = f"https://esi.evetech.net/latest/killmails/{killmail_id}/{hash_value}/"
        log.info(f"Fetching detailed killmail data from URL: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch killmail details for {killmail_id}: HTTP {resp.status}")
                    return None
                data = await resp.json()
                log.info(f"Fetched details for killmail {killmail_id}")
                return data

    async def process_killmail(self, detailed_killmail, zkb, killmail_time_dt):
        killmail_id = detailed_killmail.get('killmail_id')
        system_id = detailed_killmail['solar_system_id']
        total_value = zkb.get('totalValue')

        try:
            region_id = await self.fetch_region_id(system_id)

            if region_id in self.region_ids and total_value >= self.min_value:
                self.cursor.execute('SELECT * FROM processed_kills WHERE kill_id = ?', (killmail_id,))
                if not self.cursor.fetchone():
                    self.cursor.execute('INSERT INTO processed_kills (kill_id, processed_at) VALUES (?, ?)', (killmail_id, datetime.utcnow()))
                    self.conn.commit()
                    await self.send_kill_notification(detailed_killmail, zkb, region_id)

                    killmail_time = detailed_killmail['killmail_time']
                    await self.update_last_processed_time(killmail_time)
                    return False
                else:
                    log.debug(f"Killmail {killmail_id} already processed.")
                    return True
            else:
                log.debug(f"Killmail {killmail_id} does not match any of the specified regions or value threshold.")
                return False
        except Exception as e:
            log.exception(f"Unexpected error during killmail processing: {e}")
            return False

    async def fetch_region_id(self, solar_system_id):
        url = f"https://esi.evetech.net/latest/universe/systems/{solar_system_id}/"
        log.info(f"Fetching region ID for solar system {solar_system_id} from URL: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch region data for system {solar_system_id}: HTTP {resp.status}")
                    return None
                data = await resp.json()
                constellation_id = data.get('constellation_id')
                if not constellation_id:
                    log.error(f"Constellation ID not found for solar system {solar_system_id}")
                    return None

                constellation_url = f"https://esi.evetech.net/latest/universe/constellations/{constellation_id}/"
                async with session.get(constellation_url) as const_resp:
                    if const_resp.status != 200:
                        log.error(f"Failed to fetch constellation data for {constellation_id}: HTTP {const_resp.status}")
                        return None
                    constellation_data = await const_resp.json()
                    region_id = constellation_data.get('region_id')
                    log.info(f"Fetched region ID {region_id} for solar system {solar_system_id}")
                    return region_id

    async def send_kill_notification(self, killmail, zkb, region_id):
        channel = self.bot.get_channel(self.kills_channel_id)
        if not channel:
            log.error(f"Channel with ID {self.kills_channel_id} not found.")
            return

        try:
            kill_id = killmail['killmail_id']
            total_value = zkb.get('totalValue')
            link = f"https://zkillboard.com/kill/{kill_id}/"

            victim_info = killmail['victim']
            ship_type_id = victim_info['ship_type_id']
            character_id = victim_info.get('character_id')
            corporation_id = victim_info.get('corporation_id')
            alliance_id = victim_info.get('alliance_id')
            solar_system_id = killmail['solar_system_id']
            killmail_time = killmail['killmail_time']

            ship_name = await self.fetch_name('type', ship_type_id)
            character_name = await self.fetch_name('character', character_id) if character_id else 'Unknown'
            corporation_name = await self.fetch_name('corporation', corporation_id) if corporation_id else 'Unknown'
            alliance_name = await self.fetch_name('alliance', alliance_id) if alliance_id else 'None'
            solar_system_name = await self.fetch_name('system', solar_system_id)
            region_name = await self.fetch_name('region', region_id)

            character_link = f"[{character_name}](https://zkillboard.com/character/{character_id}/)" if character_id else 'Unknown'
            corporation_link = f"[{corporation_name}](https://zkillboard.com/corporation/{corporation_id}/)" if corporation_id else 'Unknown'
            alliance_link = f"[{alliance_name}](https://zkillboard.com/alliance/{alliance_id}/)" if alliance_id else 'None'
            location_link = f"[{solar_system_name}](https://evemaps.dotlan.net/system/{solar_system_name})"
            region_link = f"[{region_name}](https://evemaps.dotlan.net/map/{region_name.replace(' ', '_')})"

            # Fetching the icon URL for the victim's ship
            ship_icon_url = f"https://images.evetech.net/types/{ship_type_id}/render"

            # Fetch the killer's information
            attackers = killmail.get('attackers', [])
            total_attackers = len(attackers)
            final_blow = None

            for attacker in attackers:
                if attacker.get('final_blow'):
                    final_blow = attacker
                    break

            if final_blow:
                killer_name = await self.fetch_name('character', final_blow['character_id']) if final_blow.get('character_id') else 'Unknown'
                killer_corp_name = await self.fetch_name('corporation', final_blow['corporation_id']) if final_blow.get('corporation_id') else 'Unknown'
                killer_alliance_name = await self.fetch_name('alliance', final_blow['alliance_id']) if final_blow.get('alliance_id') else 'None'
                killer_ship_name = await self.fetch_name('type', final_blow['ship_type_id']) if final_blow.get('ship_type_id') else 'Unknown'
                killer_link = f"[{killer_name}](https://zkillboard.com/character/{final_blow['character_id']}/)" if final_blow.get('character_id') else 'Unknown'
                killer_corp_link = f"[{killer_corp_name}](https://zkillboard.com/corporation/{final_blow['corporation_id']}/)" if final_blow.get('corporation_id') else 'Unknown'
                killer_alliance_link = f"[{killer_alliance_name}](https://zkillboard.com/alliance/{final_blow['alliance_id']}/)" if final_blow.get('alliance_id') else 'None'
            else:
                killer_link = killer_corp_link = killer_alliance_link = killer_ship_name = 'Unknown'

            log.debug(f"Kill ID: {kill_id}, Total Value: {total_value:,} ISK")
            log.debug(f"Ship: {ship_name}, Character: {character_name}, Corporation: {corporation_name}, Alliance: {alliance_name}")
            log.debug(f"Killer: {killer_name}, Killer Ship: {killer_ship_name}, Killer Corporation: {killer_corp_name}, Killer Alliance: {killer_alliance_name}")
            log.debug(f"Location: {solar_system_name}, Region: {region_name}, Time: {killmail_time}")

            embed = discord.Embed(
                title="Valuable Kill Detected!",
                description=f"[Killmail {kill_id}]({link})\nValue: {total_value:,} ISK",
                color=0xFF0000,
                timestamp=datetime.strptime(killmail_time, "%Y-%m-%dT%H:%M:%SZ")  # Use killmail time from the data
            )
            embed.add_field(name="Victim's Ship", value=ship_name, inline=True)
            embed.add_field(name="Victim's Character", value=character_link, inline=True)
            embed.add_field(name="Victim's Corporation", value=corporation_link, inline=True)
            embed.add_field(name="Victim's Alliance", value=alliance_link, inline=True)
            embed.add_field(name="Location", value=location_link, inline=True)
            embed.add_field(name="Region", value=region_link, inline=True)
            embed.add_field(name="Kill Time", value=killmail_time, inline=True)
            embed.add_field(name="Killer's Name", value=killer_link, inline=True)
            embed.add_field(name="Killer's Corporation", value=killer_corp_link, inline=True)
            embed.add_field(name="Killer's Alliance", value=killer_alliance_link, inline=True)
            embed.add_field(name="Killer's Ship", value=killer_ship_name, inline=True)
            embed.add_field(name="Total Attackers", value=str(total_attackers), inline=True)
            embed.set_thumbnail(url=ship_icon_url)  # Add the ship icon as a thumbnail
            embed.set_footer(text="Reported by Chuck Norris Bot")

            await channel.send(embed=embed)
            log.info(f"Sent kill notification for kill ID {kill_id} with value {total_value:,} ISK.")
        except Exception as e:
            log.error(f"Failed to send kill notification: {e}")

    async def fetch_name(self, category, id):
        url_map = {
            'type': f"https://esi.evetech.net/latest/universe/types/{id}/",
            'character': f"https://esi.evetech.net/latest/characters/{id}/",
            'corporation': f"https://esi.evetech.net/latest/corporations/{id}/",
            'alliance': f"https://esi.evetech.net/latest/alliances/{id}/",
            'system': f"https://esi.evetech.net/latest/universe/systems/{id}/",
            'region': f"https://esi.evetech.net/latest/universe/regions/{id}/"
        }
        url = url_map.get(category)
        if not url:
            log.error(f"Unknown category {category} for fetching name.")
            return 'Unknown'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch {category} name for ID {id}: {resp.status}")
                    return 'Unknown'
                data = await resp.json()
                return data.get('name', 'Unknown')

    async def update_last_processed_time(self, killmail_time):
        try:
            self.cursor.execute('REPLACE INTO metadata (key, value) VALUES (?, ?)', ('last_processed_time', killmail_time))
            self.conn.commit()
            log.info(f"Updated last processed killmail time to {killmail_time}")
        except sqlite3.Error as e:
            log.error(f"Failed to update last processed killmail time: {e}")

    def cog_unload(self):
        if self.listen_for_kills_task:
            self.listen_for_kills_task.cancel()
        if self.conn:
            self.conn.close()

async def setup(bot):
    await bot.add_cog(ZKillboardCog(bot))
