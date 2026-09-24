import discord
from discord.ext import commands

TOKEN = "YOUR_BOT_TOKEN_HERE"

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Magic Cabinet is online as {bot.user}")


bot.run(TOKEN)
