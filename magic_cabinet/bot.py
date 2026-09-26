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
    app.run(host="0.0.0.0", port=port)


threading.Thread(
    target=run_health_server,
    daemon=True,
).start()


intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
)


async def setup_hook():
    await bot.load_extension("magic_cabinet.cogs.cabinet")
    await bot.load_extension("magic_cabinet.cogs.drop")
    await bot.load_extension("magic_cabinet.cogs.magic")

    await bot.tree.sync()


bot.setup_hook = setup_hook


@bot.event
async def on_ready():
    print(f"Magic Cabinet is online as {bot.user}")


bot.run(TOKEN)
