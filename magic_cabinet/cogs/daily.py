"""Magic Cabinet daily rewards."""

import random
import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS


DATABASE = "cabinet.db"

EMBED_COLOR = discord.Color.from_str("#4E0017")

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"
BOOSTER_EMOTE = "<a:heartpotion:1556018680972714095>"

DAILY_Glimmers = 1000
DAILY_COOLDOWN = 24 * 60 * 60

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005080545.jpg"
)

DIVIDER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled14_20261003173415.jpg"
)


BOOSTERS = [
    {
        "id": "sunflare",
        "name": "Sunflare",
        "description": "Selling eligible cards gives 2× Glimmers.",
    },
    {
        "id": "moonveil",
        "name": "Moonveil",
        "description": "Next drops cannot give cards you already own.",
    },
    {
        "id": "starbox",
        "name": "Starbox",
        "description": "Choose a Card ID and receive 3 copies for a small Glimmer fee.",
    },
    {
        "id": "glimmerfall",
        "name": "Glimmerfall",
        "description": "Successful card claims give 2× normal /drop Glimmer rewards.",
    },
    {
        "id": "dreamstep",
        "name": "Dreamstep",
        "description": "Your next successful drop gives 1 extra card.",
    },
]


def initialize_daily_database():
    """Create daily reward and booster ticket tables."""

    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_data (
                user_id INTEGER PRIMARY KEY,
                last_claim_at TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS booster_tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                booster_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                activated_at TEXT,
                expires_at TEXT
            )
            """
        )

        connection.commit()


def is_registered(user_id: int) -> bool:
    """Check whether the player has awakened their Cabinet."""

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT user_id
            FROM players
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return row is not None


def get_daily_claim(user_id: int):
    """Return the player's last daily claim."""

    with sqlite3.connect(DATABASE) as connection:
        return connection.execute(
            """
            SELECT last_claim_at
            FROM daily_data
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()


def get_glimmers(user_id: int) -> int:
    """Return the player's current Glimmer balance."""

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


def add_glimmers(user_id: int, amount: int):
    """Add Glimmers to the player's balance."""

    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            INSERT INTO balances (
                user_id,
                glimmers
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                glimmers = glimmers + excluded.glimmers
            """,
            (user_id, amount),
        )

        connection.commit()


def get_card_quantity(
    user_id: int,
    card_id: int,
) -> int:
    """Return the player's current quantity of a card."""

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (user_id, card_id),
        ).fetchone()

    return 0 if row is None else row[0]


def add_card_to_bag(
    user_id: int,
    card_id: int,
) -> tuple[int, bool]:
    """
    Add one card to the player's Bag.

    Returns:
        (new_quantity, was_new_card)
    """

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (user_id, card_id),
        ).fetchone()

        if row is None:
            connection.execute(
                """
                INSERT INTO bag (
                    user_id,
                    card_id,
                    quantity
                )
                VALUES (?, ?, 1)
                """,
                (user_id, card_id),
            )

            connection.commit()
            return 1, True

        new_quantity = row[0] + 1

        connection.execute(
            """
            UPDATE bag
            SET quantity = ?
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                new_quantity,
                user_id,
                card_id,
            ),
        )

        connection.commit()

        return new_quantity, False


def choose_daily_card() -> dict:
    """
    Choose one random card.

    Daily pool:
    Normal + Rare + Epic.

    Limited and Legendary are never included.
    """

    card_pool = (
        NORMAL_CARDS
        + RARE_CARDS
        + EPIC_CARDS
    )

    if not card_pool:
        raise RuntimeError(
            "The daily card pool is empty."
        )

    return random.choice(card_pool)


def choose_booster() -> dict:
    """Choose one random Booster Ticket."""

    return random.choice(BOOSTERS)


def save_daily_claim(
    user_id: int,
    claim_time: datetime,
):
    """Save the player's latest daily claim."""

    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            INSERT INTO daily_data (
                user_id,
                last_claim_at
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                last_claim_at = excluded.last_claim_at
            """,
            (
                user_id,
                claim_time.isoformat(),
            ),
        )

        connection.commit()


def save_booster_ticket(
    user_id: int,
    booster_id: str,
    received_at: datetime,
):
    """Store a Booster Ticket without activating it."""

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
                received_at.isoformat(),
            ),
        )

        connection.commit()


def format_remaining(seconds: int) -> str:
    """Format remaining cooldown time."""

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"


class Daily(commands.Cog):
    """Daily Magic Cabinet rewards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_daily_database()

    @app_commands.command(
        name="daily",
        description="Claim your daily Magic Cabinet rewards.",
    )
    async def daily(
        self,
        interaction: discord.Interaction,
    ):
        """Give the player their daily bundle."""

        user_id = interaction.user.id

        if not is_registered(user_id):
            embed = discord.Embed(
                description=(
                    "╭────────────── ✦ ──────────────╮\n"
                    "              **MAGIC CABINET**\n"
                    "╰────────────── ✦ ──────────────╯\n\n"
                    "You haven't awakened your Cabinet yet.\n\n"
                    "-# ✦ Use `/magic awaken` to begin."
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        now = datetime.now(timezone.utc)
        claim = get_daily_claim(user_id)

        if claim is not None and claim[0]:
            last_claim = datetime.fromisoformat(claim[0])
            next_claim = last_claim + timedelta(
                seconds=DAILY_COOLDOWN
            )

            remaining_seconds = int(
                (next_claim - now).total_seconds()
            )

            if remaining_seconds > 0:
                remaining = format_remaining(
                    remaining_seconds
                )

                embed = discord.Embed(
                    description=(
                        "╭────────────── ✦ ──────────────╮\n"
                        "                **DAILY REWARDS**\n"
                        "╰────────────── ✦ ──────────────╯\n\n"
                        "The Cabinet has already left "
                        "today's gifts.\n\n"
                        "Come back when the next day opens.\n\n"
                        f"-# ✦ Next daily available in **{remaining}**."
                    ),
                    color=EMBED_COLOR,
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                )

                return

        card = choose_daily_card()
        booster = choose_booster()

        previous_quantity = get_card_quantity(
            user_id,
            card["id"],
        )

        new_quantity, was_new = add_card_to_bag(
            user_id,
            card["id"],
        )

        add_glimmers(
            user_id,
            DAILY_Glimmers,
        )

        save_booster_ticket(
            user_id,
            booster["id"],
            now,
        )

        save_daily_claim(
            user_id,
            now,
        )

        new_balance = get_glimmers(user_id)

        if was_new:
            card_status = "You got a new card!"
        else:
            card_status = (
                f"You now have **{new_quantity}** copies!\n"
                "You got a dupie!"
            )

        card_link = card.get("image", "")

        if card_link:
            card_line = f"[View Card]({card_link})"
        else:
            card_line = "Card received"

        success_text = (
            "╭────────────── ✦ ──────────────╮\n"
            "                **DAILY REWARDS**\n"
            "╰────────────── ✦ ──────────────╯\n\n"
            f"🎴 **Daily Card**\n"
            f"{card_line}\n"
            f"-# ☆ Card ID: `{card['id']}` ☆ "
            f"Collection ID: `{card['collection_id']}` ☆ "
            f"{card['stars']}\n"
            f"{card_status}\n\n"
            f"{BOOSTER_EMOTE} **Booster Ticket**\n"
            f"**{booster['name']}**\n"
            f"-# {booster['description']}\n"
            "-# ✦ The booster is not active yet. "
            "Use `/activate boost` when you are ready.\n\n"
            f"{GLIMMER_EMOTE} **Glimmers**\n"
            f"+**{DAILY_Glimmers:,}** {GLIMMER_EMOTE}\n"
            f"**New balance:** {new_balance:,} {GLIMMER_EMOTE}\n\n"
            "-# ✦ Your next `/daily` will be available "
            "after 24 hours."
        )

        header_embed = discord.Embed(
            color=EMBED_COLOR
        )
        header_embed.set_image(
            url=HEADER_URL
        )

        reward_embed = discord.Embed(
            description=success_text,
            color=EMBED_COLOR,
        )

        divider_embed = discord.Embed(
            color=EMBED_COLOR
        )
        divider_embed.set_image(
            url=DIVIDER_URL
        )

        await interaction.response.send_message(
            embeds=[
                header_embed,
                reward_embed,
                divider_embed,
            ]
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Daily(bot)
      )
