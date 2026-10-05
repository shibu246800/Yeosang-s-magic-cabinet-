"""Collection 3-book layout test."""

import discord
from discord import app_commands
from discord.ext import commands


COVERS = [
    (
        "𝑹𝒐𝒚𝒂𝒍 𝑪𝒐𝒖𝒓𝒕",
        "BB_1",
        "https://raw.githubusercontent.com/"
        "shibu246800/Yeosang-s-magic-cabinet-/refs/heads/main/"
        "magic_cabinet/collection_covers/grok_1791211167707.jpg",
    ),
    (
        "𝑫𝒂𝒓𝒌 𝑨𝒄𝒂𝒅𝒆𝒎𝒊𝒂",
        "BB_2",
        "https://raw.githubusercontent.com/"
        "shibu246800/Yeosang-s-magic-cabinet-/refs/heads/main/"
        "magic_cabinet/collection_covers/grok_1791211167707.jpg",
    ),
    (
        "𝑴𝒂𝒇𝒊𝒂",
        "BB_3",
        "https://raw.githubusercontent.com/"
        "shibu246800/Yeosang-s-magic-cabinet-/refs/heads/main/"
        "magic_cabinet/collection_covers/grok_1791211167707.jpg",
    ),
]


class Collection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="collection",
        description="Test collection bookshelf.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        view = discord.ui.LayoutView()

        container = discord.ui.Container()

        gallery = discord.ui.MediaGallery(
            discord.MediaGalleryItem(
                COVERS[0][2],
                description=COVERS[0][0],
            ),
            discord.MediaGalleryItem(
                COVERS[1][2],
                description=COVERS[1][0],
            ),
            discord.MediaGalleryItem(
                COVERS[2][2],
                description=COVERS[2][0],
            ),
        )

        container.add_item(gallery)

        buttons = discord.ui.ActionRow()

        for name, collection_id, _ in COVERS:
            button = discord.ui.Button(
                emoji="<a:reddot:1556245637425533048>",
                style=discord.ButtonStyle.secondary,
            )

            async def callback(
                button_interaction: discord.Interaction,
                collection_id=collection_id,
            ):
                await button_interaction.response.send_message(
                    f"Collection `{collection_id}` opened.",
                    ephemeral=True,
                )

            button.callback = callback
            buttons.add_item(button)

        container.add_item(buttons)
        view.add_item(container)

        await interaction.response.send_message(
            view=view
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
