"""Magic Cabinet profile command."""

import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.data.collections import COLLECTIONS
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.legendary import CARDS as LEGENDARY_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS


DATABASE = "cabinet.db"

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

VAULT_NAMES = {
    "BB": "Boy × Boy",
    "GG": "Girl × Girl",
    "BG": "Boy × Girl",
}

VAULT_ORDER = ["BB", "GG", "BG"]

ALL_CARDS = (
    NORMAL_CARDS
    + RARE_CARDS
    + EPIC_CARDS
    + LIMITED_CARDS
    + LEGENDARY_CARDS
)


def initialize_profile_database():
    """Create profile-related tables."""

    with sqlite3.connect(DATABASE) as connection:

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

        connection.commit()


def get_player_vaults(
    user_id: int,
) -> list[str]:
    """Return the player's selected Vaults."""

    with sqlite3.connect(DATABASE) as connection:

        rows = connection.execute(
            """
            SELECT vault
            FROM player_vaults
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    selected = {
        row[0]
        for row in rows
        if row[0] in VAULT_ORDER
    }

    return [
        vault
        for vault in VAULT_ORDER
        if vault in selected
    ]


def get_glimmers(
    user_id: int,
) -> int:
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

    if row is None:
        return 0

    return row[0]


def get_bag_cards(
    user_id: int,
) -> set[int]:
    """Return all card IDs currently owned by the player."""

    with sqlite3.connect(DATABASE) as connection:

        rows = connection.execute(
            """
            SELECT card_id
            FROM bag
            WHERE user_id = ?
            AND quantity > 0
            """,
            (user_id,),
        ).fetchall()

    return {
        row[0]
        for row in rows
    }


def get_completed_collections(
    user_id: int,
) -> int:
    """
    Count fully completed collections.

    A collection requires all six base cards plus
    its Legendary card.
    """

    owned_cards = get_bag_cards(
        user_id
    )

    completed = 0

    for collection_id in COLLECTIONS:

        collection_cards = [
            card
            for card in ALL_CARDS
            if card["collection_id"] == collection_id
        ]

        if not collection_cards:
            continue

        base_cards = [
            card
            for card in collection_cards
            if card["stars"] != "★★★★★"
        ]

        legendary_cards = [
            card
            for card in collection_cards
            if card["stars"] == "★★★★★"
        ]

        base_complete = all(
            card["id"] in owned_cards
            for card in base_cards
        )

        legendary_complete = bool(
            legendary_cards
        ) and all(
            card["id"] in owned_cards
            for card in legendary_cards
        )

        if base_complete and legendary_complete:
            completed += 1

    return completed


def get_badges(
    user_id: int,
) -> list[tuple[str, str | None]]:
    """Return earned badges."""

    with sqlite3.connect(DATABASE) as connection:

        rows = connection.execute(
            """
            SELECT badge_name, badge_emote
            FROM player_badges
            WHERE user_id = ?
            ORDER BY badge_id
            """,
            (user_id,),
        ).fetchall()

    return rows


def get_top_achievements(
    user_id: int,
) -> list[tuple[str, int]]:
    """Return the player's global Top 3 achievements."""

    with sqlite3.connect(DATABASE) as connection:

        rows = connection.execute(
            """
            SELECT achievement_name, global_rank
            FROM player_achievements
            WHERE user_id = ?
            AND global_rank <= 3
            ORDER BY global_rank ASC
            LIMIT 3
            """,
            (user_id,),
        ).fetchall()

    return rows


def format_vaults(
    vaults: list[str],
) -> str:
    """Format selected Vaults."""

    if not vaults:
        return "None yet"

    return " • ".join(
        f"**{vault}**"
        for vault in vaults
    )


def format_badges(
    badges: list[tuple[str, str | None]],
) -> str:
    """Format earned badges."""

    if not badges:
        return "None yet"

    lines = []

    for badge_name, badge_emote in badges:

        if badge_emote:
            lines.append(
                f"{badge_emote} **{badge_name}**"
            )

        else:
            lines.append(
                f"🏅 **{badge_name}**"
            )

    return "\n".join(lines)


def format_achievements(
    achievements: list[tuple[str, int]],
) -> str:
    """Format Top 3 global achievements."""

    if not achievements:
        return "None yet"

    lines = []

    for achievement_name, rank in achievements:

        lines.append(
            f"**#{rank}** {achievement_name}"
        )

    return "\n".join(lines)


def build_profile_embed(
    user: discord.User,
) -> discord.Embed:
    """Build the live profile embed."""

    vaults = get_player_vaults(
        user.id
    )

    glimmers = get_glimmers(
        user.id
    )

    completed_collections = (
        get_completed_collections(
            user.id
        )
    )

    badges = get_badges(
        user.id
    )

    achievements = get_top_achievements(
        user.id
    )

    description = (
        f"{PROFILE_EMOTES['username']} "
        f"**Username**\n"
        f"{user.mention}\n\n"
        f"{PROFILE_EMOTES['vaults']} "
        f"**Vaults**\n"
        f"{format_vaults(vaults)}\n\n"
        f"{PROFILE_EMOTES['glimmers']} "
        f"**Glimmers**\n"
        f"{glimmers:,} {GLIMMER_EMOTE}\n\n"
        f"{PROFILE_EMOTES['collections']} "
        f"**Collections Completed**\n"
        f"**{completed_collections}**\n"
    )

    if badges:

        description += (
            f"\n"
            f"{PROFILE_EMOTES['badges']} "
            f"**Badges**\n"
            f"{format_badges(badges)}\n"
        )

    if achievements:

        description += (
            f"\n"
            f"{PROFILE_EMOTES['achievements']} "
            f"**Global Achievements**\n"
            f"{format_achievements(achievements)}\n"
        )

    embed = discord.Embed(
        description=description,
        color=EMBED_COLOR,
    )

    embed.set_author(
        name=f"{user.display_name}'s Profile",
        icon_url=user.display_avatar.url,
    )

    embed.set_image(
        url=HEADER_URL
    )

    embed.set_thumbnail(
        url=DIVIDER_URL
    )

    embed.set_footer(
        text="Yeosang's Magic Cabinet"
    )

    return embed


class Profile(commands.Cog):
    """Magic Cabinet profile commands."""

    def __init__(
        self,
        bot: commands.Bot,
    ):
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
        """Show a player's live profile."""

        target = user or interaction.user

        embed = build_profile_embed(
            target
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Profile(bot)
  )
