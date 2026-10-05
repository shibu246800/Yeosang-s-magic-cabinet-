import os
import threading

import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing.")


app = Flask(__name__)


@app.route("/")
def health_check():
    return "Magic Cabinet is running!", 200


def run_health_server():
    port = int(os.getenv("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port,
    )


threading.Thread(
    target=run_health_server,
    daemon=True,
).start()


intents = discord.Intents.default()


class MagicCabinetBot(commands.Bot):
    async def setup_hook(self):
        print("=== SETUP HOOK STARTED ===")

        await self.load_extension(
            "magic_cabinet.cogs.cabinet"
        )

        await self.load_extension(
            "magic_cabinet.cogs.drop"
        )

        await self.load_extension(
            "magic_cabinet.cogs.magic"
        )

        await self.load_extension(
            "magic_cabinet.cogs.profile.profile"
        )

        await self.load_extension(
            "magic_cabinet.cogs.purse"
        )

        await self.load_extension(
            "magic_cabinet.cogs.earn"
        )

        await self.load_extension(
            "magic_cabinet.cogs.daily"
        )

        await self.load_extension(
            "magic_cabinet.cogs.booster"
        )

        await self.load_extension(
            "magic_cabinet.cogs.weekly"
        )

        await self.load_extension(
            "magic_cabinet.cogs.rewards"
        )

        await self.load_extension(
    "magic_cabinet.cogs.test"
        )
        
        print("=== ALL EXTENSIONS LOADED ===")

        synced = await self.tree.sync()

        print(
            f"=== SYNCED {len(synced)} APPLICATION COMMANDS ==="
        )


bot = MagicCabinetBot(
    command_prefix="!",
    intents=intents,
)


@bot.event
async def on_ready():
    print(
        f"Magic Cabinet is online as {bot.user}"
    )


@bot.event
async def on_guild_join(guild):
    arrival_message = """..."""

    try:
        channel = guild.system_channel

        if channel is not None:
            await channel.send(
                arrival_message
            )

    except discord.Forbidden:
        pass


bot.run(TOKEN)
