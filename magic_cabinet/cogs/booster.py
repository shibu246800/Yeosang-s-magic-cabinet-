"""Magic Cabinet booster shop."""

import sqlite3
from datetime import datetime, timezone

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

BOOSTERS = {
    "sunflare": {
        "name": "Sunflare",
        "emote": "<:sunflare:1556516883707068446>",
        "description": "Selling eligible cards gives 2× Glimmers.",
        "price": 30000,
    },
    "moonveil": {
        "name": "Moonveil",
        "emote": "<:moonveil:1556516914539532288>",
        "description": "Next drops cannot give cards you already own.",
        "price": 25000,
    },
    "starbox": {
        "name": "Starbox",
        "emote": "<:starbox:1556516943232499782>",
        "description": "Choose a Card ID and receive 4 copies for a small Glimmer fee.",
        "price": 40000,
    },
    "glimmerfall": {
        "name": "Glimmerfall",
        "emote": "<:glimmerfall:1556516968306053230>",
        "description": "Successful card claims give 2× normal /drop Glimmer rewards.",
        "price": 35000,
    },
    "dreamstep": {
        "name": "Dreamstep",
        "emote": "<:dreamstep:1556516993803354195>",
        "description": "Your next successful drop gives 1 extra card.",
        "price": 20000,
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

    if row is None:
        return 0

    return row[0]


def add_booster_ticket(
    user_id: int,
    booster_id: str,
):
    now = datetime.now(timezone.utc)

    with sqlite3.connect(DATABASE) as connection:
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


def purchase_booster(
    user_id: int,
    booster_id: str,
    price: int,
) -> bool:
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute(
            """
            UPDATE balances
            SET glimmers = glimmers - ?
            WHERE user_id = ?
            AND glimmers >= ?
            """,
            (
                price,
                user_id,
                price,
            ),
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return False

        now = datetime.now(timezone.utc)

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


class BoosterShopView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.owner_id:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "This Booster Shop belongs to another player.\n\n"
                    "✧ Use `/booster shop` to open your own shop.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return False

        return True


class BuyBoosterView(discord.ui.View):
    def __init__(
        self,
        owner_id: int,
        booster_id: str,
    ):
        super().__init__(timeout=60)

        self.owner_id = owner_id
        self.booster_id = booster_id

    @discord.ui.button(
        label="Confirm Purchase",
        style=discord.ButtonStyle.success,
    )
    async def confirm_purchase(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.owner_id:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "This purchase confirmation belongs to another player.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        booster = BOOSTERS[self.booster_id]
        price = booster["price"]

        current_balance = get_glimmers(
            interaction.user.id
        )

        if current_balance < price:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    f"{booster['emote']} **Not enough Glimmers**\n\n"
                    f"You need **{price:,}** {GLIMMER_EMOTE} "
                    "to purchase this Booster Ticket.\n\n"
                    f"Your purse contains **{current_balance:,}** "
                    f"{GLIMMER_EMOTE}.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None,
            )

            return

        success = purchase_booster(
            interaction.user.id,
            self.booster_id,
            price,
        )

        if not success:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "The purchase could not be completed.\n\n"
                    "✧ Please try again.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None,
            )

            return

        embed = discord.Embed(
            description=(
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                f"{booster['emote']} **{booster['name']}**\n\n"
                f"Your {booster['emote']} **{booster['name']}** "
                "has been successfully bought.\n\n"
                "Use `/activate boost` to use it.\n\n"
                "-# ✧ This Booster Ticket has not been activated yet.\n\n"
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None,
        )


class BoosterBuyButton(discord.ui.Button):
    def __init__(
        self,
        owner_id: int,
        booster_id: str,
    ):
        booster = BOOSTERS[booster_id]

        super().__init__(
            label=f"Buy {booster['name']}",
            style=discord.ButtonStyle.secondary,
        )

        self.owner_id = owner_id
        self.booster_id = booster_id

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != self.owner_id:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "This Booster Shop belongs to another player.\n\n"
                    "✧ Use `/booster shop` to open your own shop.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        booster = BOOSTERS[self.booster_id]
        price = booster["price"]

        embed = discord.Embed(
            description=(
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                f"{booster['emote']} **{booster['name']}**\n\n"
                f"{booster['description']}\n\n"
                f"{GLIMMER_EMOTE} **Price:** "
                f"**{price:,}** {GLIMMER_EMOTE}\n\n"
                "Are you sure you want to purchase "
                "this Booster Ticket?\n\n"
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
            view=BuyBoosterView(
                owner_id=self.owner_id,
                booster_id=self.booster_id,
            ),
            ephemeral=True,
        )


class BoosterShopView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)

        self.owner_id = owner_id

        for booster_id in BOOSTERS:
            self.add_item(
                BoosterBuyButton(
                    owner_id=owner_id,
                    booster_id=booster_id,
                )
            )


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
            "-# ✧ Each ticket activates for 24 hours.\n"
            "-# ✧ A player can activate a maximum of 2 boosters per day.\n"
            "-# ✧ Buying a ticket does not activate it.\n\n"
        )

        for booster in BOOSTERS.values():
            description += (
                f"{booster['emote']} **{booster['name']}**\n"
                f"-# {booster['description']}\n"
                f"{GLIMMER_EMOTE} **{booster['price']:,}**\n\n"
            )

        description += (
            "✦ Choose a Booster Ticket below to purchase it.\n\n"
            "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
        )

        embed = discord.Embed(
            description=description,
            color=EMBED_COLOR,
        )

        header_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        header_embed.set_image(
            url=HEADER_URL
        )

        await interaction.response.send_message(
            embeds=[
                header_embed,
                embed,
            ],
            view=BoosterShopView(
                owner_id=interaction.user.id,
            ),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        Booster(bot)
  )
