import os

import discord
from discord.ext import commands

from cogs.cabinet import setup as setup_cabinet


intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
)


async def main():
    await setup_cabinet(bot)
    await bot.start(os.environ["DISCORD_TOKEN"])


async def on_ready():
    print(f"Logged in as {bot.user}")


import asyncio

asyncio.run(main())
