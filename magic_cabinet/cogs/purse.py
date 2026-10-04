"""Magic Cabinet purse command."""

import sqlite3

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"

EMBED_COLOR = discord.Color.from_str("#4E0017")

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

PURSE_HEADER = (
    "✦ . 　<a:001_purse:1556371245002658032>  　 . ✦ . 　"
    "<a:001_purse:1556371245002658032>  　 .✦. 　"
    "<a:001_purse:1556371245002658032>  　 . ✦ . 　"
    "<a:001_purse:1556371245002658032>  　 . ✦"
)

DIVIDER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled14_20261003173415.jpg"
)


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


class Purse(commands.Cog):
    """Magic Cabinet purse commands."""

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="purse",
        description="View your current Glimmer balance.",
    )
    async def purse(
        self,
        interaction: discord.Interaction,
    ):
        """Show the player's current Glimmers."""

        glimmers = get_glimmers(
            interaction.user.id
        )

        header_embed = discord.Embed(
            description=PURSE_HEADER,
            color=EMBED_COLOR,
        )

        profile_embed = discord.Embed(
            description=(
                "╭────────────── ✦ ──────────────╮\n"
                "                  **YOUR PURSE**\n"
                "╰────────────── ✦ ──────────────╯\n\n"
                f"{GLIMMER_EMOTE} **Glimmers**\n"
                f"**{glimmers:,}** {GLIMMER_EMOTE}"
            ),
            color=EMBED_COLOR,
        )

        divider_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        divider_embed.set_image(
            url=DIVIDER_URL
        )

        await interaction.response.send_message(
            embeds=[
                header_embed,
                profile_embed,
                divider_embed,
            ]
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Purse(bot)
)
