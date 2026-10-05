"""Magic Cabinet reward center."""

import random
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.data.epic import CARDS as EPIC_CARDS

DATABASE = "cabinet.db"
EMBED_COLOR = discord.Color.from_str("#4E0017")
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"
WEEKLY_GRAND_GLIMMERS = 25_000


def initialize_rewards_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS blind_boxes (
                user_id INTEGER PRIMARY KEY,
                quantity INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        connection.commit()


def get_pending_rewards(user_id: int):
    with sqlite3.connect(DATABASE) as connection:
        return connection.execute(
            """
            SELECT
                reward_id,
                reward_type,
                amount,
                task_id
            FROM weekly_pending_rewards
            WHERE user_id = ?
            AND claimed = 0
            ORDER BY reward_id ASC
            """,
            (user_id,),
        ).fetchall()


def get_blind_box_count(user_id: int) -> int:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM blind_boxes
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return row[0] if row else 0


def add_blind_boxes(user_id: int, amount: int):
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            INSERT INTO blind_boxes (
                user_id,
                quantity
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                quantity = quantity + excluded.quantity
            """,
            (
                user_id,
                amount,
            ),
        )

        connection.commit()


def get_bag_quantity(
    user_id: int,
    card_id: int,
) -> int:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                user_id,
                card_id,
            ),
        ).fetchone()

    return row[0] if row else 0


def add_to_bag(
    user_id: int,
    card_id: int,
):
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                user_id,
                card_id,
            ),
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
                (
                    user_id,
                    card_id,
                ),
            )

            connection.commit()
            return 1, True

        quantity = row[0] + 1

        connection.execute(
            """
            UPDATE bag
            SET quantity = ?
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                quantity,
                user_id,
                card_id,
            ),
        )

        connection.commit()
        return quantity, False


def add_glimmers(
    user_id: int,
    amount: int,
):
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
            (
                user_id,
                amount,
            ),
        )

        connection.commit()


def choose_new_epic(user_id: int):
    available = []

    for card in EPIC_CARDS:
        card_id = int(card["id"])

        if get_bag_quantity(user_id, card_id) == 0:
            available.append(card)

    if not available:
        return None

    return random.choice(available)


def claim_rewards(user_id: int):
    pending = get_pending_rewards(user_id)

    if not pending:
        return None

    task_glimmers = 0
    has_grand = False

    for _, reward_type, amount, _ in pending:
        if reward_type == "task_glimmers":
            task_glimmers += amount

        elif reward_type == "weekly_grand":
            has_grand = True

    epic_card = None

    if has_grand:
        epic_card = choose_new_epic(user_id)

    total_glimmers = task_glimmers

    if has_grand:
        total_glimmers += WEEKLY_GRAND_GLIMMERS

    if total_glimmers:
        add_glimmers(
            user_id,
            total_glimmers,
        )

    if epic_card is not None:
        add_to_bag(
            user_id,
            int(epic_card["id"]),
        )

    if has_grand:
        add_blind_boxes(
            user_id,
            1,
        )

    reward_ids = [
        row[0]
        for row in pending
    ]

    with sqlite3.connect(DATABASE) as connection:
        placeholders = ",".join(
            "?"
            for _ in reward_ids
        )

        connection.execute(
            f"""
            UPDATE weekly_pending_rewards
            SET claimed = 1
            WHERE reward_id IN ({placeholders})
            """,
            reward_ids,
        )

        connection.commit()

    return {
        "task_glimmers": task_glimmers,
        "grand_glimmers": (
            WEEKLY_GRAND_GLIMMERS
            if has_grand
            else 0
        ),
        "total_glimmers": total_glimmers,
        "epic": epic_card,
        "blind_boxes": 1 if has_grand else 0,
    }


def build_reward_embed(
    user: discord.User | discord.Member,
    pending,
):
    task_total = sum(
        row[2]
        for row in pending
        if row[1] == "task_glimmers"
    )

    has_grand = any(
        row[1] == "weekly_grand"
        for row in pending
    )

    lines = [
        f"**{user.mention}**",
        "",
        "✦ ───── ⋆⋅☆⋅⋆ ───── ✦",
        "",
        "**REWARDS WAITING**",
        "",
    ]

    if task_total:
        lines.append(
            f"+ **{task_total:,}** {GLIMMER_EMOTE}"
        )

    if has_grand:
        lines.extend(
            [
                "",
                "**Weekly Grand Reward**",
                f"+ **{WEEKLY_GRAND_GLIMMERS:,}** "
                f"{GLIMMER_EMOTE}",
                "+ **1 NEW Epic card**",
                "+ **1 Blind Box**",
            ]
        )

    lines.extend(
        [
            "",
            "✦ ───── ⋆⋅☆⋅⋆ ───── ✦",
            "",
            "-# ✧ Claim everything waiting for you.",
        ]
    )

    return discord.Embed(
        description="\n".join(lines),
        color=EMBED_COLOR,
    )


class RewardsView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    @discord.ui.button(
        label="Claim",
        emoji="⬇️",
        style=discord.ButtonStyle.danger,
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="✦ These rewards belong to another player.",
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        result = claim_rewards(
            interaction.user.id
        )

        if result is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="✦ You have no rewards waiting.",
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        lines = [
            f"**{interaction.user.mention}**",
            "",
            "✦ ───── ⋆⋅☆⋅⋆ ───── ✦",
            "",
            "**REWARDS CLAIMED!** ✦",
            "",
        ]

        if result["task_glimmers"]:
            lines.append(
                f"+ **{result['task_glimmers']:,}** "
                f"{GLIMMER_EMOTE}"
            )

        if result["grand_glimmers"]:
            lines.append(
                f"+ **{result['grand_glimmers']:,}** "
                f"{GLIMMER_EMOTE}"
            )

        if result["epic"]:
            lines.append(
                f"+ **{result['epic']['name']}** "
                "`NEW Epic card`"
            )

        if result["blind_boxes"]:
            lines.append(
                "+ **1 Blind Box** 📦"
            )

        lines.extend(
            [
                "",
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦",
            ]
        )

        button.disabled = True

        await interaction.response.edit_message(
            embed=discord.Embed(
                description="\n".join(lines),
                color=EMBED_COLOR,
            ),
            view=self,
        )


class Rewards(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="rewards",
        description="View and claim your waiting rewards.",
    )
    async def rewards(
        self,
        interaction: discord.Interaction,
    ):
        pending = get_pending_rewards(
            interaction.user.id
        )

        if not pending:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "✦ You have no rewards waiting right now."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=build_reward_embed(
                interaction.user,
                pending,
            ),
            view=RewardsView(
                interaction.user.id
            ),
        )


async def setup(bot: commands.Bot):
    initialize_rewards_database()
    await bot.add_cog(
        Rewards(bot)
        )
