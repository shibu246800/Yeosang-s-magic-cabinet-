"""Magic Cabinet collection command."""

import io
import math
import urllib.request

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw


EMBED_COLOR = discord.Color.from_str("#4E0017")

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005205021.jpg"
)

# ------------------------------------------------------------
# COLLECTION DATA
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# BASIC HELPERS
# ------------------------------------------------------------

def vault_name(vault):
    return {
        "BB": "🌙 Velvet Moon",
        "GG": "🌹 Roseglass",
        "BG": "🪡 Golden Thread",
    }.get(vault, vault)


def collection_status(collection):
    # Temporary until the real card ownership/database system
    # is connected.
    return "unattended"


def get_filtered_collections(
    vault=None,
    status=None,
):
    result = COLLECTIONS.copy()

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
            if collection_status(collection) == status
        ]

    return result


# ------------------------------------------------------------
# COVER BOARD
# ------------------------------------------------------------

def download_image(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=15,
    ) as response:
        return response.read()


def create_cover_board(collections):
    """Create a 3x3 collection cover board."""

    board_size = 900
    gap = 18
    cell_size = 288

    board = Image.new(
        "RGB",
        (board_size, board_size),
        "#16070B",
    )

    for index in range(9):

        row = index // 3
        column = index % 3

        x = column * (cell_size + gap)
        y = row * (cell_size + gap)

        if index >= len(collections):
            continue

        collection = collections[index]

        try:
            image_data = download_image(
                collection["cover"]
            )

            cover = Image.open(
                io.BytesIO(image_data)
            ).convert("RGB")

            cover.thumbnail(
                (cell_size, cell_size)
            )

            cover_x = x + (
                cell_size - cover.width
            ) // 2

            cover_y = y + (
                cell_size - cover.height
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
                    x + cell_size,
                    y + cell_size,
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


# ------------------------------------------------------------
# COLLECTION BOARD
# ------------------------------------------------------------

def build_collection_board(
    collection,
    user,
):
    embed = discord.Embed(
        color=EMBED_COLOR,
    )

    embed.title = (
        f'{collection["name"]} • {collection["id"]}'
    )

    embed.description = (
        f'{vault_name(collection["vault"])}\n'
        f'*{collection["series"]} Series*'
    )

    # Temporary visual board.
    # Real card ownership will be connected later.
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


# ------------------------------------------------------------
# COLLECTION SELECT MENU
# ------------------------------------------------------------

class CollectionSelect(discord.ui.Select):

    def __init__(
        self,
        collections,
    ):
        self.available_collections = collections

        options = []

        for collection in collections[:25]:
            options.append(
                discord.SelectOption(
                    label=collection["name"][:100],
                    description=(
                        f'{collection["id"]} • '
                        f'{vault_name(collection["vault"])}'
                    )[:100],
                    value=collection["id"],
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No collections found",
                    description="There are no collections here.",
                    value="NONE",
                )
            )

        super().__init__(
            placeholder="Open Collection",
            options=options,
            row=0,
        )

    async def callback(
        self,
        interaction,
    ):
        selected_id = self.values[0]

        if selected_id == "NONE":
            await interaction.response.send_message(
                "No collections are available here.",
                ephemeral=True,
            )
            return

        collection = next(
            (
                item
                for item in COLLECTIONS
                if item["id"] == selected_id
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


# ------------------------------------------------------------
# SEARCH MODAL
# ------------------------------------------------------------

class CollectionSearchModal(
    discord.ui.Modal,
    title="Search Collection",
):

    collection_id = discord.ui.TextInput(
        label="Collection ID",
        placeholder="Example: BB_001",
        required=True,
        max_length=30,
    )

    async def on_submit(
        self,
        interaction,
    ):
        collection_id = (
            self.collection_id.value
            .strip()
            .upper()
        )

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


# ------------------------------------------------------------
# STATUS MENU
# ------------------------------------------------------------

class StatusSelect(
    discord.ui.Select
):

    def __init__(
        self,
        parent_view,
    ):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(
                label="All Collections",
                value="all",
            ),
            discord.SelectOption(
                label="Completed",
                value="completed",
            ),
            discord.SelectOption(
                label="Ongoing",
                value="ongoing",
            ),
            discord.SelectOption(
                label="Unattended",
                value="unattended",
            ),
        ]

        super().__init__(
            placeholder="Show Collections By",
            options=options,
        )

    async def callback(
        self,
        interaction,
    ):
        selected = self.values[0]

        if selected == "all":
            status = None
        else:
            status = selected

        self.parent_view.status = status
        self.parent_view.page = 0

        self.parent_view.collections = (
            get_filtered_collections(
                vault=self.parent_view.vault,
                status=status,
            )
        )

        await self.parent_view.update_message(
            interaction
        )


class StatusView(
    discord.ui.View
):

    def __init__(
        self,
        parent_view,
    ):
        super().__init__(
            timeout=60
        )

        self.add_item(
            StatusSelect(parent_view)
        )


# ------------------------------------------------------------
# MAIN COLLECTION VIEW
# ------------------------------------------------------------

class CollectionView(
    discord.ui.View
):

    def __init__(
        self,
        author,
        collections,
        page=0,
        vault=None,
        status=None,
    ):
        super().__init__(
            timeout=600
        )

        self.author = author
        self.collections = collections
        self.page = page
        self.vault = vault
        self.status = status

        self.rebuild()

    # --------------------------------------------------------
    # PAGE
    # --------------------------------------------------------

    @property
    def max_pages(self):
        return max(
            1,
            math.ceil(
                len(self.collections) / 9
            ),
        )

    @property
    def current_page(self):
        start = self.page * 9
        end = start + 9

        return self.collections[start:end]

    # --------------------------------------------------------
    # VIEW BUILD
    # --------------------------------------------------------

    def rebuild(self):

        self.clear_items()

        # Open Collection dropdown
        self.add_item(
            CollectionSelect(
                self.current_page
            )
        )

        # Vault buttons
        self.add_item(
            VaultButton(
                self,
                "🌙 BB",
                "BB",
            )
        )

        self.add_item(
            VaultButton(
                self,
                "🌹 GG",
                "GG",
            )
        )

        self.add_item(
            VaultButton(
                self,
                "🪡 BG",
                "BG",
            )
        )

        # Search
        self.add_item(
            SearchButton(self)
        )

        # Status
        self.add_item(
            StatusButton(self)
        )

        # Previous / next
        self.add_item(
            PreviousButton(self)
        )

        self.add_item(
            NextButton(self)
        )

    # --------------------------------------------------------
    # MESSAGE UPDATE
    # --------------------------------------------------------

    async def update_message(
        self,
        interaction,
    ):
        self.rebuild()

        board = create_cover_board(
            self.current_page
        )

        file = discord.File(
            board,
            filename="collection_board.png",
        )

        header_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        header_embed.set_image(
            url=HEADER_URL
        )

        gallery_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        gallery_embed.set_image(
            url="attachment://collection_board.png"
        )

        gallery_embed.set_footer(
            text=(
                f"Collections {self.page * 9 + 1}"
                f"–"
                f"{self.page * 9 + len(self.current_page)}"
                f" • Page {self.page + 1}/{self.max_pages}"
            )
        )

        await interaction.response.edit_message(
            embeds=[
                header_embed,
                gallery_embed,
            ],
            attachments=[
                file,
            ],
            view=self,
        )

    # --------------------------------------------------------
    # USER CHECK
    # --------------------------------------------------------

    async def interaction_check(
        self,
        interaction,
    ):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "This collection menu belongs to another user.",
                ephemeral=True,
            )
            return False

        return True


# ------------------------------------------------------------
# VAULT BUTTON
# ------------------------------------------------------------

class VaultButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
        label,
        vault,
    ):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            row=1,
        )

        self.parent_view = parent_view
        self.vault = vault

    async def callback(
        self,
        interaction,
    ):
        self.parent_view.vault = self.vault
        self.parent_view.page = 0

        self.parent_view.collections = (
            get_filtered_collections(
                vault=self.vault,
                status=self.parent_view.status,
            )
        )

        await self.parent_view.update_message(
            interaction
        )


# ------------------------------------------------------------
# SEARCH BUTTON
# ------------------------------------------------------------

class SearchButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
    ):
        super().__init__(
            label="🔎 Search ID",
            style=discord.ButtonStyle.primary,
            row=1,
        )

        self.parent_view = parent_view

    async def callback(
        self,
        interaction,
    ):
        await interaction.response.send_modal(
            CollectionSearchModal()
        )


# ------------------------------------------------------------
# STATUS BUTTON
# ------------------------------------------------------------

class StatusButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
    ):
        super().__init__(
            label="Status",
            style=discord.ButtonStyle.secondary,
            row=1,
        )

        self.parent_view = parent_view

    async def callback(
        self,
        interaction,
    ):
        await interaction.response.send_message(
            view=StatusView(
                self.parent_view
            ),
            ephemeral=True,
        )


# ------------------------------------------------------------
# PREVIOUS
# ------------------------------------------------------------

class PreviousButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
    ):
        super().__init__(
            label="《",
            style=discord.ButtonStyle.secondary,
            row=2,
        )

        self.parent_view = parent_view

    async def callback(
        self,
        interaction,
    ):
        if self.parent_view.page <= 0:
            await interaction.response.send_message(
                "You're already on the first page.",
                ephemeral=True,
            )
            return

        self.parent_view.page -= 1

        await self.parent_view.update_message(
            interaction
        )


# ------------------------------------------------------------
# NEXT
# ------------------------------------------------------------

class NextButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
    ):
        super().__init__(
            label="》",
            style=discord.ButtonStyle.secondary,
            row=2,
        )

        self.parent_view = parent_view

    async def callback(
        self,
        interaction,
    ):
        if (
            self.parent_view.page
            >= self.parent_view.max_pages - 1
        ):
            await interaction.response.send_message(
                "You're already on the last page.",
                ephemeral=True,
            )
            return

        self.parent_view.page += 1

        await self.parent_view.update_message(
            interaction
        )


# ------------------------------------------------------------
# COG
# ------------------------------------------------------------

class Collection(
    commands.Cog
):

    def __init__(
        self,
        bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="collection",
        description="Browse Magic Cabinet collections.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        collections = get_filtered_collections()

        board = create_cover_board(
            collections[:9]
        )

        file = discord.File(
            board,
            filename="collection_board.png",
        )

        header_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        header_embed.set_image(
            url=HEADER_URL
        )

        gallery_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        gallery_embed.set_image(
            url="attachment://collection_board.png"
        )

        view = CollectionView(
            author=interaction.user,
            collections=collections,
            page=0,
        )

        gallery_embed.set_footer(
            text=(
                f"Collections 1–{min(9, len(collections))}"
                f" • Page 1/{view.max_pages}"
            )
        )

        await interaction.response.send_message(
            embeds=[
                header_embed,
                gallery_embed,
            ],
            file=file,
            view=view,
        )


async def setup(bot):
    await bot.add_cog(
        Collection(bot)
            )
