
"""Magic Cabinet profile command."""

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import get_connection


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


def get_profile_data(user_id: int) -> dict:
    """Fetch all profile information using one database connection."""

    with get_connection() as connection:
        vault_rows = connection.execute(
            """
            SELECT vault
            FROM player_vaults
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

        glimmer_row = connection.execute(
            """
            SELECT glimmers
            FROM balances
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        completed_row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM collection_rewards
            WHERE user_id = ? AND claimed = 1
            """,
            (user_id,),
        ).fetchone()

        legendary_rows = connection.execute(
            """
            SELECT collection_id, legendary_id
            FROM player_legendary
            WHERE user_id = ?
            ORDER BY collection_id
            """,
            (user_id,),
        ).fetchall()

        badge_rows = connection.execute(
            """
            SELECT badge_name, badge_emote
            FROM player_badges
            WHERE user_id = ?
            ORDER BY badge_id
            """,
            (user_id,),
        ).fetchall()

        achievement_rows = connection.execute(
            """
            SELECT achievement_name, global_rank
            FROM player_achievements
            WHERE user_id = ? AND global_rank <= 3
            ORDER BY global_rank
            LIMIT 3
            """,
            (user_id,),
        ).fetchall()

    selected_vaults = {
        row["vault"] for row in vault_rows
    }

    return {
        "vaults": [
            vault for vault in VAULT_ORDER
            if vault in selected_vaults
        ],
        "glimmers": int(glimmer_row["glimmers"]) if glimmer_row else 0,
        "completed": int(completed_row["total"]) if completed_row else 0,
        "legendary": [
            (row["collection_id"], row["legendary_id"])
            for row in legendary_rows
        ],
        "badges": [
            (row["badge_name"], row["badge_emote"])
            for row in badge_rows
        ],
        "achievements": [
            (row["achievement_name"], row["global_rank"])
            for row in achievement_rows
        ],
    }


def format_vaults(vaults: list[str]) -> str:
    return (
        " • ".join(f"**{vault}**" for vault in vaults)
        if vaults
        else "None yet"
    )


def format_badges(badges: list[tuple[str, str | None]]) -> str:
    if not badges:
        return "None yet"

    return "\n".join(
        f"{emote} **{name}**"
        if emote
        else f"🏅 **{name}**"
        for name, emote in badges
    )


def format_achievements(
    achievements: list[tuple[str, int]],
) -> str:
    if not achievements:
        return "None yet"

    return "\n".join(
        f"**#{rank}** {name}"
        for name, rank in achievements
    )


def build_profile_content(
    user: discord.User,
    data: dict,
) -> discord.Embed:
    """Build the profile embed using already-fetched data."""

    vaults = data["vaults"]
    glimmers = data["glimmers"]
    completed = data["completed"]
    legendary = data["legendary"]
    badges = data["badges"]
    achievements = data["achievements"]

    description = (
        f"{PROFILE_EMOTES['username']} **Username**\n"
        f"{user.mention}\n\n"
        f"{PROFILE_EMOTES['vaults']} **Vaults**\n"
        f"{format_vaults(vaults)}\n\n"
        f"{PROFILE_EMOTES['glimmers']} **Glimmers**\n"
        f"{glimmers:,} {GLIMMER_EMOTE}\n\n"
        f"{PROFILE_EMOTES['collections']} **Collections Completed**\n"
        f"**{completed}**\n\n"
        "✨ **Legendary Cards**\n"
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
            f"\n\n{PROFILE_EMOTES['achievements']} "
            "**Global Achievements**\n"
            f"{format_achievements(achievements)}"
        )

    embed = discord.Embed(
        description=description,
        color=EMBED_COLOR,
    )

    embed.set_author(
        name=f"{user.display_name}'s Profile",
        icon_url=user.display_avatar.url,
    )

    embed.set_footer(text="Yeosang's Magic Cabinet")

    return embed


class Profile(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="profile",
        description="View a Magic Cabinet identity card.",
    )
    @app_commands.describe(
        user="The player whose profile you want to view."
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ):
        await interaction.response.defer(thinking=True)

        target = user or interaction.user

        try:
            profile_data = await asyncio.to_thread(
                get_profile_data,
                target.id,
            )

            header = discord.Embed(color=EMBED_COLOR)
            header.set_image(url=HEADER_URL)

            profile_embed = build_profile_content(
                target,
                profile_data,
            )

            divider = discord.Embed(color=EMBED_COLOR)
            divider.set_image(url=DIVIDER_URL)

            await interaction.followup.send(
                embeds=[header, profile_embed, divider]
            )

        except Exception as error:
            print(f"[PROFILE DATABASE/COMMAND ERROR] {error!r}")

            await interaction.followup.send(
                "The profile could not be displayed. "
                "Please check the bot logs.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
