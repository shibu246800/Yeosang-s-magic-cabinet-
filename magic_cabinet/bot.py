
import os
import asyncio
import threading

import discord
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
    app.run(host="0.0.0.0", port=port)


threading.Thread(
    target=run_health_server,
    daemon=True,
).start()

EMBED_COLOR = discord.Color.from_str("#4E0017")


# ---------------------------------------------------------
# TURSO CONNECTION TEST
# ---------------------------------------------------------

def test_turso_connection():
    """Verify that Magic Cabinet can access Turso Cloud."""

    with get_connection() as connection:
        result = connection.execute(
            "SELECT 1"
        ).fetchone()

        return result[0] == 1


# ---------------------------------------------------------
# COMMAND ACCESS CONTROL
# ---------------------------------------------------------

def check_command_access(guild_id: int, user_id: int, command_name: str):
    """Run all synchronous access-control database queries."""

    with get_connection() as connection:
        setup_result = connection.execute(
            """
            SELECT 1
            FROM drop_channels
            WHERE guild_id = ?
            """,
            (guild_id,),
        ).fetchone()

        if setup_result is None:
            return "not_setup"

        if command_name == "magic awaken":
            return "allowed"

        vault_result = connection.execute(
            """
            SELECT 1
            FROM player_vaults
            WHERE user_id = ?
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

    if vault_result is None:
        return "vault_missing"

    return "allowed"


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

        if command_name == "cabinet setup":
            return True

        if interaction.guild_id is None:
            await interaction.response.send_message(
                "🔒 The Magic Cabinet must be used inside a server.",
                ephemeral=True,
            )
            return False

        try:
            access_status = await asyncio.to_thread(
                check_command_access,
                interaction.guild_id,
                interaction.user.id,
                command_name,
            )

            if access_status == "not_setup":
                await interaction.response.send_message(
                    "🔒 **The Cabinet is not set up yet.**\n\n"
                    "An administrator must run `/cabinet setup` "
                    "before players can begin.",
                    ephemeral=True,
                )
                return False

            if access_status == "vault_missing":
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
                f"check the database: {type(error).__name__}: {error}"
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

        # Initialize Turso database.
        try:
            await asyncio.to_thread(initialize_database)
            print("[TURSO] Database initialized.")

            connected = await asyncio.to_thread(
                test_turso_connection
            )

            if not connected:
                raise RuntimeError(
                    "Turso connection test returned an unexpected result."
                )

            print("[TURSO] CONNECTION SUCCESSFUL!")

        except Exception as error:
            print(
                "[TURSO] DATABASE INITIALIZATION FAILED: "
                f"{type(error).__name__}: {error}"
            )
            raise

        # Load bot extensions.
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
            "magic_cabinet.cogs.merge",
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
