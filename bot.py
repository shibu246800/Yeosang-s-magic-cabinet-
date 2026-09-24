import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Magic Cabinet is online as {bot.user}")


async def load_cogs():
    await bot.load_extension("magic_cabinet.cogs.health")
    await bot.load_extension("magic_cabinet.cogs.cabinet")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(os.getenv("DISCORD_TOKEN"))


import asyncio
asyncio.run(main())
