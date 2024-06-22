import discord
from discord import app_commands
from discord.ext import commands
import logging

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='bothelp', description='Displays a list of available commands.')
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Chuck Norris Bot - Help",
            description="Chuck Norris developed by kaspa and some AI. V1.04\n\nHere are the available commands:",
            color=0x3498db
        )

        embed.add_field(name="/ping", value="Check the bot's responsiveness.", inline=False)
        embed.add_field(name="/time", value="Get the current date/time across various time zones. Also includes the current pilot count of Eve Online--bot count not included.", inline=False)
        embed.add_field(name="/remind <time> <message>", value="Set a reminder with a specified time and message.", inline=False)
        embed.add_field(name="/create_poll <duration> <question> <option1> <option2> [<option3> <option4>]", value="Create a poll with a question and options. Example: `/create_poll 10m \"Your Question?\" \"Option1\" \"Option2\"`", inline=False)
        embed.add_field(name="/jokeschuck", value="Get a random Chuck Norris joke.", inline=False)

        embed.set_footer(text="Chuck Norris Bot by kaspa, AI included.")

        try:
            await interaction.user.send(embed=embed)
            logging.info(f"Help information sent to {interaction.user}.")
        except discord.Forbidden:
            logging.warning(f"Could not send DM to {interaction.user}. They have DMs disabled.")
            if not interaction.response.is_done():
                await interaction.response.send_message("I can't send you DMs. Please enable receiving DMs from server members or check your privacy settings.", ephemeral=True)
            return

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("I've sent you a DM with the help information.", ephemeral=True)
                logging.info(f"Help response sent in channel to {interaction.user}.")
        except discord.errors.NotFound:
            logging.error(f"Interaction with {interaction.user} expired before response could be sent.")
        except Exception as e:
            logging.error(f"An error occurred while sending the help response: {e}")

async def setup(bot):
    await bot.add_cog(HelpCog(bot))