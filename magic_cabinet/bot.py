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
    print("=== SETUP HOOK STARTED ===")

    await bot.load_extension("magic_cabinet.cogs.cabinet")
    await bot.load_extension("magic_cabinet.cogs.drop")
    await bot.load_extension("magic_cabinet.cogs.magic")
    await bot.load_extension("magic_cabinet.cogs.profile.profile")
    await bot.load_extension("magic_cabinet.cogs.purse")

    synced = await bot.tree.sync()

    print(f"Synced {len(synced)} application commands.")


bot.setup_hook = setup_hook


@bot.event
async def on_ready():
    print(f"Magic Cabinet is online as {bot.user}")


@bot.event
async def on_guild_join(guild):
    arrival_message = """╭─────────────── ✦ ───────────────╮
　　　𓆩 THE CABINET HAS ARRIVED 𓆪
╰─────────────── ✦ ───────────────╯
𓂃 ࣪˖ ִֶָ𐀔  _ Somewhere between a forgotten page and a door that was never meant to open... a key has appeared._
_-# Behind an unseen door, something stirs.
-# Drawers whisper, Pages turn, Locks click. -# And somewhere in the darkness... a single golden lock begins to glow._　　　　　　✦　⋆　✧　⋆　✦
-# ***__The Cabinet has chosen this place.__***
-# Whether it was waiting for you...
-# or you were waiting for it...
-# that remains a secret._
╰─────────────── ⋆⋅☆⋅⋆ ───────────────╯
-# 𓆩 ✦ 𓆪 TO BEGIN YOUR JOURNEY~
__【 FOR SERVER STAFF 】__
-# Before the Cabinet can awaken, its resting place must be chosen.
### ☆A server administrator or authorized staff member must configure the cabinet's Drop channel(s) first.
«𓂃 Configure the Cabinet:
➤ `/cabinet setup` »

__Next step:   FOR PLAYERS 】__
«𓆩 🗝️ 𓆪 Awaken the Cabinet
➤ `/magic awaken`»
-# The drawers are waiting.
　　　　　　𓂃𓈒𓏸 ✧ 𓏸𓈒𓂃
-# ✦ Need guidance?
-# Type `yhelp` anytime to explore the Cabinet's commands.
　　         𓆩 THE KEY HAS TURNED 𓆪
　　　         Now... open the door.
╰─────────────── ✦ ───────────────╯"""

    embed = discord.Embed(
        description=arrival_message,
        color=discord.Color.from_str("#4E0017"),
    )

    for channel in guild.text_channels:
        permissions = channel.permissions_for(guild.me)

        if (
            permissions.view_channel
            and permissions.send_messages
            and permissions.embed_links
        ):
            try:
                await channel.send(embed=embed)
                print(
                    f"Arrival message sent in #{channel.name} "
                    f"in {guild.name}"
                )
                break
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                continue


bot.run(TOKEN)
