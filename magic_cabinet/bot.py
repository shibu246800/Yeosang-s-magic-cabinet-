
import os
import asyncio
import threading

import discord
import psycopg
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask

from magic_cabinet.database import (
    get_connection,
    initialize_database,
)


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing.")


# ---------------------------------------------------------
# HEALTH SERVER
# ---------------------------------------------------------

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


EMBED_COLOR = discord.Color.from_str("#4E0017")


# ---------------------------------------------------------
# PRISMA CONNECTION TEST
# ---------------------------------------------------------

async def test_prisma_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("[PRISMA TEST] DATABASE_URL is missing.")
        return

    def check_connection():
        with psycopg.connect(
            database_url,
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0]

    try:
        result = await asyncio.to_thread(check_connection)

        if result == 1:
            print("[PRISMA TEST] CONNECTION SUCCESSFUL!")

    except Exception as error:
        print(
            f"[PRISMA TEST] FAILED: {type(error).__name__}"
        )


# ---------------------------------------------------------
# COMMAND ACCESS CONTROL
# ---------------------------------------------------------

class CabinetCommandTree(app_commands.CommandTree):

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        command = interaction.command

        if command is None:
            return True

        command_name = getattr(
            command,
            "qualified_name",
            command.name,
        )

        # Setup must remain available before the Cabinet is configured.
        if command_name == "cabinet setup":
            return True

        # All other commands require a server.
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "🔒 The Magic Cabinet must be used inside a server.",
                ephemeral=True,
            )
            return False

        try:
            with get_connection() as connection:
                setup_result = connection.execute(
                    """
                    SELECT 1
                    FROM drop_channels
                    WHERE guild_id = ?
                    """,
                    (interaction.guild_id,),
                ).fetchone()

                if setup_result is None:
                    await interaction.response.send_message(
                        "🔒 **The Cabinet is not set up yet.**\n\n"
                        "An administrator must run `/cabinet setup` "
                        "before players can begin.",
                        ephemeral=True,
                    )
                    return False

                # Awakening is the next permitted step.
                if command_name == "magic awaken":
                    return True

                vault_result = connection.execute(
                    """
                    SELECT 1
                    FROM player_vaults
                    WHERE user_id = ?
                    LIMIT 1
                    """,
                    (interaction.user.id,),
                ).fetchone()

            if vault_result is None:
                await interaction.response.send_message(
                    "🔒 **Your Magic Cabinet is still sealed.**\n\n"
                    "Use `/magic awaken` and select your vault "
                    "before using other commands.",
                    ephemeral=True,
                )
                return False

            return True

        except Exception as error:
            print(
                "ERROR: The Cabinet command lock could not "
                f"check the database: {type(error).__name__}"
            )

            await interaction.response.send_message(
                "🔒 The Cabinet could not verify your access "
                "right now. Please try again later.",
                ephemeral=True,
            )
            return False


# ---------------------------------------------------------
# BOT
# ---------------------------------------------------------

intents = discord.Intents.default()


class MagicCabinetBot(commands.Bot):

    async def setup_hook(self):
        print("=== SETUP HOOK STARTED ===")

        # Keep the existing SQLite database active.
        initialize_database()
        print("[SQLITE] Database initialized.")

        # Test Prisma without migrating or changing player data.
        await test_prisma_connection()

        extensions = [
            "magic_cabinet.cogs.cabinet",
            "magic_cabinet.cogs.drop",
            "magic_cabinet.cogs.magic",
            "magic_cabinet.cogs.profile.profile",
            "magic_cabinet.cogs.purse",
            "magic_cabinet.cogs.earn",
            "magic_cabinet.cogs.daily",
            "magic_cabinet.cogs.booster",
            "magic_cabinet.cogs.weekly",
            "magic_cabinet.cogs.rewards",
            "magic_cabinet.cogs.test",
            "magic_cabinet.cogs.bag",
            "magic_cabinet.cogs.collection",
            "magic_cabinet.cogs.wild",
            "magic_cabinet.cogs.album",
        ]

        for extension in extensions:
            await self.load_extension(extension)
            print(f"Loaded: {extension}")

        print("=== ALL EXTENSIONS LOADED ===")

        synced = await self.tree.sync()

        print(
            f"=== SYNCED {len(synced)} APPLICATION COMMANDS ==="
        )


bot = MagicCabinetBot(
    command_prefix="!",
    intents=intents,
    tree_cls=CabinetCommandTree,
)


# ---------------------------------------------------------
# EVENTS
# ---------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Magic Cabinet is online as {bot.user}")


@bot.event
async def on_guild_join(guild):
    arrival_message = """..."""

    try:
        channel = guild.system_channel

        if channel is not None:
            await channel.send(arrival_message)

    except discord.Forbidden:
        pass


bot.run(TOKEN)
