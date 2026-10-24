
"""Magic Cabinet profile command."""

import sqlite3
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import get_connection
from magic_cabinet.data.collections import COLLECTIONS
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS
from magic_cabinet.data.legendary import CARDS as LEGENDARY_CARDS


EMBED_COLOR = discord.Color.from_str("#4E0017")

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261003171807.jpg"
)

DIVIDER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled14_20261003173415.jpg"
)

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

PROFILE_EMOTES = {
    "username": "<:ShinyRed:1555917904128774195>",
    "vaults": "<:emoji_25:1555925927593250857>",
    "glimmers": "<:diamond_red:1555917328070213702>",
    "collections": "<:book2:1555918845666005153>",
    "badges": "<:emoji_24:1555925885301948457>",
    "achievements": "<:emoji_27:1555925990545297478>",
}

VAULT_ORDER = ["BB", "GG", "BG"]

ALL_BASE_CARDS = (
    NORMAL_CARDS
    + RARE_CARDS
    + EPIC_CARDS
    + LIMITED_CARDS
)


def get_connection():
    """Use the same database as the other Cabinet commands."""
    connection = sqlite3.connect(
        str(Path(__file__).resolve().parents[2] / "cabinet.db")
    )
    connection.row_factory = sqlite3.Row
    return connection


def initialize_profile_database():
    """Create profile and Legendary ownership tables."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS player_badges (
                user_id INTEGER NOT NULL,
                badge_id TEXT NOT NULL,
                badge_name TEXT NOT NULL,
                badge_emote TEXT,
                PRIMARY KEY (user_id, badge_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS player_achievements (
                user_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                global_rank INTEGER NOT NULL,
                PRIMARY KEY (user_id, achievement_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS player_legendary (
                user_id INTEGER NOT NULL,
                collection_id TEXT NOT NULL,
                legendary_id TEXT NOT NULL,
                claimed_at TEXT,
                PRIMARY KEY (user_id, collection_id)
            )
            """
        )


def get_player_vaults(user_id: int) -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT vault FROM player_vaults WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    selected = {row["vault"] for row in rows}
    return [vault for vault in VAULT_ORDER if vault in selected]


def get_glimmers(user_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT glimmers FROM balances WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    return int(row["glimmers"]) if row else 0


def get_bag_cards(user_id: int) -> set[int]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT card_id FROM bag
            WHERE user_id = ? AND quantity > 0
            """,
            (user_id,),
        ).fetchall()

    return {int(row["card_id"]) for row in rows}


def get_player_legendary(user_id: int) -> list[tuple[str, str]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT collection_id, legendary_id
            FROM player_legendary
            WHERE user_id = ?
            ORDER BY collection_id
            """,
            (user_id,),
        ).fetchall()

    return [
        (row["collection_id"], row["legendary_id"])
        for row in rows
    ]


def get_completed_collections(user_id: int) -> int:
    """Count collections whose Legendary reward was claimed."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM collection_rewards
            WHERE user_id = ? AND claimed = 1
            """,
            (user_id,),
        ).fetchone()

    return int(row[0]) if row else 0


def get_badges(user_id: int) -> list[tuple[str, str | None]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT badge_name, badge_emote
            FROM player_badges
            WHERE user_id = ?
            ORDER BY badge_id
            """,
            (user_id,),
        ).fetchall()

    return [(row["badge_name"], row["badge_emote"]) for row in rows]


def get_top_achievements(user_id: int) -> list[tuple[str, int]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT achievement_name, global_rank
            FROM player_achievements
            WHERE user_id = ? AND global_rank <= 3
            ORDER BY global_rank ASC
            LIMIT 3
            """,
            (user_id,),
        ).fetchall()

    return [
        (row["achievement_name"], row["global_rank"])
        for row in rows
    ]


def format_vaults(vaults: list[str]) -> str:
    return " • ".join(f"**{vault}**" for vault in vaults) if vaults else "None yet"


def format_badges(badges: list[tuple[str, str | None]]) -> str:
    if not badges:
        return "None yet"

    return "\n".join(
        f"{emote} **{name}**" if emote else f"🏅 **{name}**"
        for name, emote in badges
    )


def format_achievements(achievements: list[tuple[str, int]]) -> str:
    if not achievements:
        return "None yet"

    return "\n".join(
        f"**#{rank}** {name}"
        for name, rank in achievements
    )


def build_profile_content(user: discord.User) -> discord.Embed:
    vaults = get_player_vaults(user.id)
    glimmers = get_glimmers(user.id)
    completed = get_completed_collections(user.id)
    badges = get_badges(user.id)
    achievements = get_top_achievements(user.id)
    legendary = get_player_legendary(user.id)

    description = (
        f"{PROFILE_EMOTES['username']} **Username**\n"
        f"{user.mention}\n\n"
        f"{PROFILE_EMOTES['vaults']} **Vaults**\n"
        f"{format_vaults(vaults)}\n\n"
        f"{PROFILE_EMOTES['glimmers']} **Glimmers**\n"
        f"{glimmers:,} {GLIMMER_EMOTE}\n\n"
        f"{PROFILE_EMOTES['collections']} **Collections Completed**\n"
        f"**{completed}**\n\n"
        f"✨ **Legendary Cards**\n"
    )

    if legendary:
        description += "\n".join(
            f"✦ **{card_id}** · `{collection_id}`"
            for collection_id, card_id in legendary
        )
    else:
        description += "None yet"

    if badges:
        description += (
            f"\n\n{PROFILE_EMOTES['badges']} **Badges**\n"
            f"{format_badges(badges)}"
        )

    if achievements:
        description += (
            f"\n\n{PROFILE_EMOTES['achievements']} **Global Achievements**\n"
            f"{format_achievements(achievements)}"
        )

    embed = discord.Embed(description=description, color=EMBED_COLOR)
    embed.set_author(
        name=f"{user.display_name}'s Profile",
        icon_url=user.display_avatar.url,
    )
    embed.set_footer(text="Yeosang's Magic Cabinet")
    return embed


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_profile_database()

    @app_commands.command(
        name="profile",
        description="View a Magic Cabinet identity card.",
    )
    @app_commands.describe(
        user="The player whose profile you want to view.",
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ):
        target = user or interaction.user

        header = discord.Embed(color=EMBED_COLOR)
        header.set_image(url=HEADER_URL)

        profile = build_profile_content(target)

        divider = discord.Embed(color=EMBED_COLOR)
        divider.set_image(url=DIVIDER_URL)

        await interaction.response.send_message(
            embeds=[header, profile, divider]
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
