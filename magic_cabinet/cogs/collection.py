"""Magic Cabinet collection command."""

import io
import math

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont


EMBED_COLOR = discord.Color.from_str("#4E0017")

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005205021.jpg"
)

# ------------------------------------------------------------------
# COLLECTION DATA
# ------------------------------------------------------------------

COLLECTIONS = [
    {
        "id": "BB_001",
        "name": "Royal Court",
        "vault": "BB",
        "series": "Velvet Moon",
        "cover": (
            "https://raw.githubusercontent.com/"
            "shibu246800/Yeosang-s-magic-cabinet-/"
            "refs/heads/main/magic_cabinet/collection_covers/"
            "grok_1791211167707.jpg"
        ),
    },
]


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def get_vault_name(vault):
    return {
        "BB": "🌙 Velvet Moon",
        "GG": "🌹 Roseglass",
        "BG": "🪡 Golden Thread",
    }.get(vault, vault)


def get_status(collection):
    # Temporary until real inventory data is connected.
    # Royal Court currently displays as unattended.
    return "unattended"


def filtered_collections(vault=None, status=None):
    result = COLLECTIONS

    if vault:
        result = [
            collection
            for collection in result
            if collection["vault"] == vault
        ]

    if status:
        result = [
            collection
            for collection in result
            if get_status(collection) == status
        ]

    return result


def make_cover_board(collections):
    """
    Creates a 3x3 collection cover board.

    Each page always contains nine positions.
    Empty positions remain blank.
    """

    width = 900
    height = 900
    gap = 20
    cell_width = 286
    cell_height = 286

    board = Image.new("RGB", (width, height), "#16070B")

    for index in range(9):
        row = index // 3
        column = index % 3

        x = column * (cell_width + gap)
        y = row * (cell_height + gap)

        if index >= len(collections):
            continue

        collection = collections[index]

        try:
            import requests

            response = requests.get(
                collection["cover"],
                timeout=15,
            )
            response.raise_for_status()

            cover = Image.open(
                io.BytesIO(response.content)
            ).convert("RGB")

            cover.thumbnail(
                (cell_width, cell_height)
            )

            cover_x = x + (
                cell_width - cover.width
            ) // 2

            cover_y = y + (
                cell_height - cover.height
            ) // 2

            board.paste(
                cover,
                (cover_x, cover_y),
            )

        except Exception:
            draw = ImageDraw.Draw(board)

            draw.rectangle(
                (
                    x,
                    y,
                    x + cell_width,
                    y + cell_height,
                ),
                outline="#4E0017",
                width=3,
            )

    output = io.BytesIO()
    board.save(
        output,
        format="PNG",
    )
    output.seek(0)

    return output


# ------------------------------------------------------------------
# COLLECTION SELECT
# ------------------------------------------------------------------

class CollectionSelect(discord.ui.Select):

    def __init__(self, collections):

        options = []

        for collection in collections[:25]:
            options.append(
                discord.SelectOption(
                    label=collection["name"][:100],
                    description=(
                        f'{collection["id"]} • '
                        f'{get_vault_name(collection["vault"])}'
                    )[:100],
                    value=collection["id"],
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No collections found",
                    value="none",
                )
            )

        super().__init__(
            placeholder="Choose a collection...",
            options=options,
            custom_id="collection_select",
        )

    async def callback(self, interaction):

        collection_id = self.values[0]

        if collection_id == "none":
            await interaction.response.send_message(
                "No collections are available here.",
                ephemeral=True,
            )
            return

        collection = next(
            (
                item
                for item in COLLECTIONS
                if item["id"] == collection_id
            ),
            None,
        )

        if collection is None:
            await interaction.response.send_message(
                "That collection could not be found.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=build_collection_board(
                collection,
                interaction.user,
            ),
            ephemeral=True,
        )


# ------------------------------------------------------------------
# SEARCH MODAL
# ------------------------------------------------------------------

class CollectionSearchModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Search Collection"
        )

        self.collection_id = discord.ui.TextInput(
            label="Collection ID",
            placeholder="Example: BB_001",
            required=True,
            max_length=30,
        )

        self.add_item(self.collection_id)

    async def on_submit(self, interaction):

        collection_id = self.collection_id.value.strip().upper()

        collection = next(
            (
                item
                for item in COLLECTIONS
                if item["id"].upper() == collection_id
            ),
            None,
        )

        if collection is None:
            await interaction.response.send_message(
                f"No collection found with ID `{collection_id}`.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=build_collection_board(
                collection,
                interaction.user,
            ),
            ephemeral=True,
        )


# ------------------------------------------------------------------
# COLLECTION BOARD
# ------------------------------------------------------------------

def build_collection_board(collection, user):

    embed = discord.Embed(
        color=EMBED_COLOR,
    )

    embed.title = (
        f'{collection["id"]} • {collection["name"]}'
    )

    embed.description = (
        f'**{get_vault_name(collection["vault"])}**\n'
        f'*{collection["series"]} Series*'
    )

    # Temporary board until the real six-card ownership
    # system is connected.
    embed.add_field(
        name="Collection",
        value=(
            "▣ ▣ ▣\n"
            "▣ ▣ ▣\n"
            "◆"
        ),
        inline=False,
    )

    embed.set_footer(
        text="6 Base Cards • 1 Legendary"
    )

    return embed


# ------------------------------------------------------------------
# MAIN VIEW
# ------------------------------------------------------------------

class CollectionView(discord.ui.View):

    def __init__(
        self,
        author,
        collections,
        page=0,
        vault=None,
        status=None,
    ):
        super().__init__(
            timeout=300
        )

        self.author = author
        self.collections = collections
        self.page = page
        self.vault = vault
        self.status = status

        self.add_item(
            CollectionSelect(
                self.current_page_collections()
            )
        )

    def current_page_collections(self):
        start = self.page * 9
        end = start + 9
        return self.collections[start:end]

    async def refresh(self, interaction):

        await interaction.response.edit_message(
            embeds=await build_gallery_embeds(
                self.current_page_collections()
            ),
            view=self,
        )

    async def interaction_check(self, interaction):

        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "This collection menu belongs to another user.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="🌙 BB",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def bb_button(self, interaction, button):

        self.vault = "BB"
        self.page = 0

        self.collections = filtered_collections(
            vault=self.vault,
            status=self.status,
        )

        self.clear_items()

        self.add_item(
            CollectionSelect(
                self.current_page_collections()
            )
        )

        self.add_controls()

        await self.refresh(interaction)

    @discord.ui.button(
        label="🌹 GG",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def gg_button(self, interaction, button):

        self.vault = "GG"
        self.page = 0

        self.collections = filtered_collections(
            vault=self.vault,
            status=self.status,
        )

        self.clear_items()

        self.add_item(
            CollectionSelect(
                self.current_page_collections()
            )
        )

        self.add_controls()

        await self.refresh(interaction)

    @discord.ui.button(
        label="🪡 BG",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def bg_button(self, interaction, button):

        self.vault = "BG"
        self.page = 0

        self.collections = filtered_collections(
            vault=self.vault,
            status=self.status,
        )

        self.clear_items()

        self.add_item(
            CollectionSelect(
                self.current_page_collections()
            )
        )

        self.add_controls()

        await self.refresh(interaction)

    @discord.ui.button(
        label="🔎 Search ID",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def search_button(self, interaction, button):

        await interaction.response.send_modal(
            CollectionSearchModal()
        )

    @discord.ui.button(
        label="Status",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def status_button(self, interaction, button):

        await interaction.response.send_message(
            "Choose a collection status:",
            view=StatusView(self),
            ephemeral=True,
        )

    def add_controls(self):

        self.add_item(
            PreviousButton(self)
        )

        self.add_item(
            NextButton(self)
        )


class PreviousButton(
    discord.ui.Button
):

    def __init__(self, parent):
        super().__init__(
            label="《",
            style=discord.ButtonStyle.secondary,
            row=2,
        )
        self.parent_view = parent

    async def callback(self, interaction):

        if self.parent_view.page <= 0:
            await interaction.response.send_message(
                "You're already on the first page.",
                ephemeral=True,
            )
            return

        self.parent_view.page -= 1

        self.parent_view.clear_items()

        self.parent_view.add_item(
            CollectionSelect(
                self.parent_view.current_page_collections()
            )
        )

        self.parent_view.add_controls()

        await self.parent_view.refresh(interaction)


class NextButton(
    discord.ui.Button
):

    def __init__(self, parent):
        super().__init__(
            label="》",
            style=discord.ButtonStyle.secondary,
            row=2,
        )
        self.parent_view = parent

    async def callback(self, interaction):

        max_pages = max(
            1,
            math.ceil(
                len(self.parent_view.collections) / 9
            ),
        )

        if self.parent_view.page >= max_pages - 1:
            await interaction.response.send_message(
                "You're already on the last page.",
                ephemeral=True,
            )
            return

        self.parent_view.page += 1

        self.parent_view.clear_items()

        self.parent_view.add_item(
            CollectionSelect(
                self.parent_view.current_page_collections()
            )
        )

        self.parent_view.add_controls()

        await self.parent_view.refresh(interaction)


# ------------------------------------------------------------------
# STATUS FILTER
# ------------------------------------------------------------------

class StatusView(discord.ui.View):

    def __init__(self, parent):
        super().__init__(
            timeout=60
        )
        self.parent_view = parent

    @discord.ui.button(
        label="Completed",
        style=discord.ButtonStyle.success,
    )
    async def completed(self, interaction, button):

        await self.apply_status(
            interaction,
            "completed",
        )

    @discord.ui.button(
        label="Ongoing",
        style=discord.ButtonStyle.primary,
    )
    async def ongoing(self, interaction, button):

        await self.apply_status(
            interaction,
            "ongoing",
        )

    @discord.ui.button(
        label="Unattended",
        style=discord.ButtonStyle.secondary,
    )
    async def unattended(self, interaction, button):

        await self.apply_status(
            interaction,
            "unattended",
        )

    @discord.ui.button(
        label="All",
        style=discord.ButtonStyle.danger,
    )
    async def all_status(self, interaction, button):

        await self.apply_status(
            interaction,
            None,
        )

    async def apply_status(
        self,
        interaction,
        status,
    ):

        self.parent_view.status = status
        self.parent_view.page = 0

        self.parent_view.collections = filtered_collections(
            vault=self.parent_view.vault,
            status=status,
        )

        self.parent_view.clear_items()

        self.parent_view.add_item(
            CollectionSelect(
                self.parent_view.current_page_collections()
            )
        )

        self.parent_view.add_controls()

        await interaction.response.edit_message(
            content=None,
            embeds=await build_gallery_embeds(
                self.parent_view.current_page_collections()
            ),
            view=self.parent_view,
        )


# ------------------------------------------------------------------
# EMBEDS
# ------------------------------------------------------------------

async def build_gallery_embeds(collections):

    board = make_cover_board(
        collections
    )

    file = discord.File(
        board,
        filename="collection_board.png",
    )

    header_embed = discord.Embed(
        color=EMBED_COLOR
    )

    header_embed.set_image(
        url=HEADER_URL
    )

    gallery_embed = discord.Embed(
        color=EMBED_COLOR
    )

    gallery_embed.set_image(
        url="attachment://collection_board.png"
    )

    gallery_embed.set_footer(
        text=(
            "Collections "
            f"• {len(collections)} shown"
        )
    )

    # The attachment must travel with the embed.
    return [
        header_embed,
        gallery_embed,
    ], file


# ------------------------------------------------------------------
# COG
# ------------------------------------------------------------------

class Collection(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="collection",
        description="Browse the Magic Cabinet collections.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):

        collections = filtered_collections()

        embeds, file = await build_gallery_embeds(
            collections[:9]
        )

        view = CollectionView(
            interaction.user,
            collections,
            page=0,
        )

        await interaction.response.send_message(
            embeds=embeds,
            file=file,
            view=view,
        )


async def setup(bot):
    await bot.add_cog(
        Collection(bot)
    )
