"""Magic Cabinet booster system."""

import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"
EMBED_COLOR = discord.Color.from_str("#4E0017")

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005093624.jpg"
)

BOOSTER_DURATION = timedelta(hours=24)
MAX_DAILY_ACTIVATIONS = 2

BOOSTERS = {
    "sunflare": {
        "name": "Sunflare",
        "emote": "<:sunflare:1556516883707068446>",
        "description": "Selling eligible cards gives 2× Glimmers.",
        "price": 30000,
        "uses": None,
    },
    "moonveil": {
        "name": "Moonveil",
        "emote": "<:moonveil:1556516914539532288>",
        "description": "Next drops cannot give cards you already own.",
        "price": 25000,
        "uses": 10,
    },
    "starbox": {
        "name": "Starbox",
        "emote": "<:starbox:1556516943232499782>",
        "description": "Choose a Card ID and receive 4 copies for a small Glimmer fee.",
        "price": 40000,
        "uses": 1,
    },
    "glimmerfall": {
        "name": "Glimmerfall",
        "emote": "<:glimmerfall:1556516968306053230>",
        "description": "Successful card claims give 2× normal /drop Glimmer rewards.",
        "price": 35000,
        "uses": None,
    },
    "dreamstep": {
        "name": "Dreamstep",
        "emote": "<:dreamstep:1556516993803354195>",
        "description": "Your next successful drop gives 1 extra card.",
        "price": 20000,
        "uses": 1,
    },
}


def initialize_booster_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS booster_tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                booster_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                activated_at TEXT,
                expires_at TEXT,
                uses_remaining INTEGER
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS booster_activation_log (
                activation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticket_id INTEGER NOT NULL,
                booster_id TEXT NOT NULL,
                activated_at TEXT NOT NULL
            )
            """
        )

        connection.commit()


def get_glimmers(user_id: int) -> int:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT glimmers
            FROM balances
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return 0 if row is None else row[0]


def purchase_booster(
    user_id: int,
    booster_id: str,
    price: int,
) -> bool:
    now = datetime.now(timezone.utc)

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute(
            """
            UPDATE balances
            SET glimmers = glimmers - ?
            WHERE user_id = ?
            AND glimmers >= ?
            """,
            (price, user_id, price),
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return False

        connection.execute(
            """
            INSERT INTO booster_tickets (
                user_id,
                booster_id,
                received_at
            )
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                booster_id,
                now.isoformat(),
            ),
        )

        connection.commit()

    return True


def get_available_tickets(user_id: int):
    with sqlite3.connect(DATABASE) as connection:
        return connection.execute(
            """
            SELECT ticket_id, booster_id
            FROM booster_tickets
            WHERE user_id = ?
            AND activated_at IS NULL
            ORDER BY ticket_id ASC
            """,
            (user_id,),
        ).fetchall()


def get_active_boosters(user_id: int):
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE) as connection:
        return connection.execute(
            """
            SELECT ticket_id, booster_id, expires_at, uses_remaining
            FROM booster_tickets
            WHERE user_id = ?
            AND activated_at IS NOT NULL
            AND expires_at > ?
            ORDER BY activated_at ASC
            """,
            (user_id, now),
        ).fetchall()


def get_daily_activation_count(user_id: int) -> int:
    today = datetime.now(timezone.utc).date().isoformat()

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM booster_activation_log
            WHERE user_id = ?
            AND substr(activated_at, 1, 10) = ?
            """,
            (user_id, today),
        ).fetchone()

    return 0 if row is None else row[0]


def activate_ticket(
    ticket_id: int,
    user_id: int,
    booster_id: str,
):
    now = datetime.now(timezone.utc)
    expires_at = now + BOOSTER_DURATION
    uses = BOOSTERS[booster_id]["uses"]

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute(
            """
            UPDATE booster_tickets
            SET activated_at = ?,
                expires_at = ?,
                uses_remaining = ?
            WHERE ticket_id = ?
            AND user_id = ?
            AND booster_id = ?
            AND activated_at IS NULL
            """,
            (
                now.isoformat(),
                expires_at.isoformat(),
                uses,
                ticket_id,
                user_id,
                booster_id,
            ),
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return None

        connection.execute(
            """
            INSERT INTO booster_activation_log (
                user_id,
                ticket_id,
                booster_id,
                activated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                ticket_id,
                booster_id,
                now.isoformat(),
            ),
        )

        connection.commit()

    return expires_at


class ConfirmPurchaseView(discord.ui.View):
    def __init__(
        self,
        user_id: int,
        booster_id: str,
    ):
        super().__init__(timeout=60)

        self.user_id = user_id
        self.booster_id = booster_id

    @discord.ui.button(
        label="Confirm Purchase",
        style=discord.ButtonStyle.success,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            return

        booster = BOOSTERS[self.booster_id]

        if get_glimmers(self.user_id) < booster["price"]:
            embed = discord.Embed(
                description=(
                    f"{booster['emote']} **Not enough Glimmers**\n\n"
                    f"You need **{booster['price']:,}** "
                    f"{GLIMMER_EMOTE}."
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None,
            )
            return

        success = purchase_booster(
            self.user_id,
            self.booster_id,
            booster["price"],
        )

        if not success:
            return

        embed = discord.Embed(
            description=(
                f"{booster['emote']} **{booster['name']}**\n\n"
                f"Your {booster['emote']} **{booster['name']}** "
                "has been successfully bought.\n\n"
                "Use `/activate boost` to use it."
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None,
        )


class ShopButton(discord.ui.Button):
    def __init__(
        self,
        user_id: int,
        booster_id: str,
    ):
        booster = BOOSTERS[booster_id]

        super().__init__(
            label=f"Buy {booster['name']}",
            style=discord.ButtonStyle.secondary,
        )

        self.user_id = user_id
        self.booster_id = booster_id

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != self.user_id:
            return

        booster = BOOSTERS[self.booster_id]

        embed = discord.Embed(
            description=(
                f"{booster['emote']} **{booster['name']}**\n\n"
                f"{booster['description']}\n\n"
                f"{GLIMMER_EMOTE} **Price:** "
                f"**{booster['price']:,}**\n\n"
                "Are you sure you want to purchase "
                "this Booster Ticket?"
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
            view=ConfirmPurchaseView(
                self.user_id,
                self.booster_id,
            ),
            ephemeral=True,
        )


class ShopView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)

        for booster_id in BOOSTERS:
            self.add_item(
                ShopButton(
                    user_id,
                    booster_id,
                )
            )


class ActivateView(discord.ui.View):
    def __init__(self, user_id: int, tickets: list):
        super().__init__(timeout=60)

        for ticket_id, booster_id in tickets:
            booster = BOOSTERS.get(booster_id)

            if booster is None:
                continue

            button = discord.ui.Button(
                label=booster["name"],
                style=discord.ButtonStyle.secondary,
                emoji=booster["emote"],
            )

            async def callback(
                interaction: discord.Interaction,
                ticket_id=ticket_id,
                booster_id=booster_id,
            ):
                if interaction.user.id != user_id:
                    return

                daily_count = get_daily_activation_count(
                    user_id
                )

                if daily_count >= MAX_DAILY_ACTIVATIONS:
                    embed = discord.Embed(
                        description=(
                            "✦ **Daily Booster Limit Reached**\n\n"
                            "You can activate a maximum of "
                            "**2 boosters per day**."
                        ),
                        color=EMBED_COLOR,
                    )

                    await interaction.response.edit_message(
                        embed=embed,
                        view=None,
                    )
                    return

                active = get_active_boosters(user_id)

                if active:
                    embed = discord.Embed(
                        description=(
                            "✦ **Booster Already Active**\n\n"
                            "You already have an active booster."
                        ),
                        color=EMBED_COLOR,
                    )

                    await interaction.response.edit_message(
                        embed=embed,
                        view=None,
                    )
                    return

                expires_at = activate_ticket(
                    ticket_id,
                    user_id,
                    booster_id,
                )

                if expires_at is None:
                    return

                booster = BOOSTERS[booster_id]

                embed = discord.Embed(
                    description=(
                        f"{booster['emote']} "
                        f"**{booster['name']} ACTIVATED**\n\n"
                        f"{booster['description']}\n\n"
                        "✦ Active for **24 hours**.\n\n"
                        f"✦ Daily activations: "
                        f"**{daily_count + 1}/2**"
                    ),
                    color=EMBED_COLOR,
                )

                await interaction.response.edit_message(
                    embed=embed,
                    view=None,
                )

            button.callback = callback
            self.add_item(button)


class Booster(commands.GroupCog, name="booster"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_booster_database()

    @app_commands.command(
        name="shop",
        description="Browse and purchase Booster Tickets.",
    )
    async def shop(
        self,
        interaction: discord.Interaction,
    ):
        description = (
            "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
            "**Booster Tickets**\n\n"
            "-# ✧ Each booster activates for 24 hours.\n"
            "-# ✧ You can activate **2 boosters per day**.\n"
            "-# ✧ Buying a ticket does not activate it.\n\n"
        )

        for booster in BOOSTERS.values():
            description += (
                f"{booster['emote']} **{booster['name']}**\n"
                f"-# {booster['description']}\n"
                f"{GLIMMER_EMOTE} **{booster['price']:,}**\n\n"
            )

        embed = discord.Embed(
            description=description,
            color=EMBED_COLOR,
        )

        header = discord.Embed(
            color=EMBED_COLOR,
        )
        header.set_image(url=HEADER_URL)

        await interaction.response.send_message(
            embeds=[header, embed],
            view=ShopView(interaction.user.id),
        )

    @app_commands.command(
        name="activate",
        description="Activate one of your Booster Tickets.",
    )
    async def activate(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        daily_count = get_daily_activation_count(user_id)

        if daily_count >= MAX_DAILY_ACTIVATIONS:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "**Daily Booster Limit Reached**\n\n"
                    "You have already activated "
                    "**2 boosters today**.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        active = get_active_boosters(user_id)

        if active:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "**Booster Already Active**\n\n"
                    "You already have an active booster.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        tickets = get_available_tickets(user_id)

        if not tickets:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    f"{GLIMMER_EMOTE} **No Booster Tickets**\n\n"
                    "You don't have a Booster Ticket waiting.\n\n"
                    "✧ Use `/daily` or visit `/booster shop`.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            description=(
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                "**Choose a Booster**\n\n"
                "Select the Booster Ticket you want to activate.\n\n"
                f"✦ Daily activations: "
                f"**{daily_count}/2**\n\n"
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
            view=ActivateView(
                user_id,
                tickets,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        Booster(bot)
    )
