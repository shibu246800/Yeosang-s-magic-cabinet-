"""Magic Cabinet collection command."""

import io
import json
import math
import urllib.request
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageOps


EMBED_COLOR = discord.Color.from_str("#4E0017")

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005205021.jpg"
)

BASE_DIR = Path(__file__).resolve().parent.parent
COLLECTIONS_FILE = BASE_DIR / "data" / "collections.json"


def load_collections():
    if not COLLECTIONS_FILE.exists():
        return []

    try:
        with open(COLLECTIONS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("collections", [])

    except (json.JSONDecodeError, OSError):
        return []


COLLECTIONS = load_collections()


def vault_name(vault):
    names = {
        "BB": "🌙 Velvet Moon",
        "GG": "🌹 Roseglass",
        "BG": "🪡 Golden Thread",
    }

    return names.get(vault, vault)


def collection_status(collection):
    cards = collection.get("cards", [])

    if not cards:
        return "unattended"

    base_cards = [
        card for card in cards
        if not card.get("legendary", False)
    ]

    collected = sum(
        1 for card in base_cards
        if card.get("collected", False)
    )

    if collected == 0:
        return "unattended"

    if collected == len(base_cards):
        legendary = next(
            (
                card for card in cards
                if card.get("legendary", False)
            ),
            None,
        )

        if legendary and legendary.get("collected", False):
            return "completed"

        return "ongoing"

    return "ongoing"


def get_filtered_collections(vault=None, status=None):
    collections = COLLECTIONS

    if vault:
        collections = [
            collection
            for collection in collections
            if collection.get("vault") == vault
        ]

    if status:
        collections = [
            collection
            for collection in collections
            if collection_status(collection) == status
        ]

    return collections


def download_image(url):
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            return Image.open(io.BytesIO(response.read())).convert("RGB")

    except Exception:
        return None


def create_cover_board(collections):
    if not collections:
        return None

    width = 1200
    outer_padding = 70
    gap = 35

    count = len(collections)

    if count == 1:
        columns = 1
    elif count <= 4:
        columns = 2
    else:
        columns = 3

    rows = math.ceil(count / columns)

    usable_width = width - (outer_padding * 2)
    cell_width = (
        usable_width - (gap * (columns - 1))
    ) / columns

    cell_height = cell_width * 1.35

    height = (
        outer_padding * 2
        + (cell_height * rows)
        + (gap * (rows - 1))
    )

    board = Image.new(
        "RGB",
        (width, int(height)),
        "white",
    )

    for index, collection in enumerate(collections):
        cover_url = collection.get("cover")

        if not cover_url:
            continue

        cover = download_image(cover_url)

        if cover is None:
            continue

        cover.thumbnail(
            (
                int(cell_width),
                int(cell_height),
            ),
            Image.Resampling.LANCZOS,
        )

        row = index // columns
        column = index % columns

        x = (
            outer_padding
            + column * (cell_width + gap)
            + (cell_width - cover.width) / 2
        )

        y = (
            outer_padding
            + row * (cell_height + gap)
            + (cell_height - cover.height) / 2
        )

        board.paste(
            cover,
            (int(x), int(y)),
        )

    output = io.BytesIO()
    board.save(output, format="PNG")
    output.seek(0)

    return output


def build_collection_board(collection):
    cards = collection.get("cards", [])

    base_cards = [
        card for card in cards
        if not card.get("legendary", False)
    ]

    legendary_card = next(
        (
            card for card in cards
            if card.get("legendary", False)
        ),
        None,
    )

    while len(base_cards) < 6:
        base_cards.append(None)

    slots = base_cards[:6] + [legendary_card]

    width = 1200
    card_width = 300
    card_height = 400
    gap = 30
    padding = 70

    board_width = width
    board_height = (
        padding
        + card_height * 2
        + gap
        + 170
    )

    board = Image.new(
        "RGB",
        (board_width, board_height),
        "white",
    )

    draw = ImageDraw.Draw(board)

    positions = [
        (padding, padding),
        (padding + card_width + gap, padding),
        (padding + (card_width + gap) * 2, padding),
        (padding, padding + card_height + gap),
        (padding + card_width + gap, padding + card_height + gap),
        (
            padding + (card_width + gap) * 2,
            padding + card_height + gap,
        ),
    ]

    for index, card in enumerate(slots[:6]):
        x, y = positions[index]

        if card and card.get("image"):
            image = download_image(card["image"])

            if image:
                image = ImageOps.fit(
                    image,
                    (card_width, card_height),
                    method=Image.Resampling.LANCZOS,
                )

                if not card.get("collected", False):
                    image = ImageOps.grayscale(image)

                board.paste(image, (x, y))
                continue

        draw.rectangle(
            (x, y, x + card_width, y + card_height),
            outline="#D9D9D9",
            width=3,
        )

    legendary_x = (
        padding
        + card_width
        + gap
    )

    legendary_y = (
        padding
        + card_height
        + gap
    )

    legendary = slots[6]

    if legendary and legendary.get("image"):
        image = download_image(legendary["image"])

        if image:
            image = ImageOps.fit(
                image,
                (card_width, card_height),
                method=Image.Resampling.LANCZOS,
            )

            if not legendary.get("collected", False):
                image = Image.new(
                    "RGB",
                    image.size,
                    "black",
                )

            board.paste(
                image,
                (
                    legendary_x,
                    legendary_y,
                ),
            )

    draw.text(
        (
            padding,
            board_height - 130,
        ),
        f'{collection.get("id", "")} • {collection.get("name", "")}',
        fill="#4E0017",
    )

    draw.text(
        (
            padding,
            board_height - 85,
        ),
        "6 Base Cards • 1 Legendary",
        fill="#555555",
    )

    output = io.BytesIO()
    board.save(output, format="PNG")
    output.seek(0)

    return output


class CollectionSelect(discord.ui.Select):

    def __init__(self, view):
        self.collection_view = view

        options = []

        for collection in view.current_collections:
            options.append(
                discord.SelectOption(
                    label=collection.get("name", "Collection"),
                    value=collection.get("id", ""),
                    description=collection.get("id", ""),
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No collections",
                    value="none",
                )
            )

        super().__init__(
            placeholder="Open Collection",
            options=options[:25],
        )

    async def callback(self, interaction):
        collection_id = self.values[0]

        if collection_id == "none":
            await interaction.response.send_message(
                "No collections are available.",
                ephemeral=True,
            )
            return

        collection = next(
            (
                item
                for item in COLLECTIONS
                if item.get("id") == collection_id
            ),
            None,
        )

        if not collection:
            await interaction.response.send_message(
                "Collection not found.",
                ephemeral=True,
            )
            return

        image = build_collection_board(collection)

        if image is None:
            await interaction.response.send_message(
                "This collection cannot be displayed yet.",
                ephemeral=True,
            )
            return

        file = discord.File(
            image,
            filename="collection.png",
        )

        embed = discord.Embed(
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collection.png"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file,
            ephemeral=True,
        )


class CollectionSearchModal(discord.ui.Modal):
    def __init__(self, collection_view):
        super().__init__(title="Search Collection")

        self.collection_view = collection_view

        self.collection_id = discord.ui.TextInput(
            label="Collection ID",
            placeholder="Example: BB_1",
            required=True,
            max_length=20,
        )

        self.add_item(self.collection_id)

    async def on_submit(self, interaction):
        collection_id = self.collection_id.value.strip().upper()

        collection = next(
            (
                item
                for item in COLLECTIONS
                if item.get("id", "").upper() == collection_id
            ),
            None,
        )

        if not collection:
            await interaction.response.send_message(
                f"Collection `{collection_id}` was not found.",
                ephemeral=True,
            )
            return

        image = build_collection_board(collection)

        if image is None:
            await interaction.response.send_message(
                "This collection cannot be displayed yet.",
                ephemeral=True,
            )
            return

        file = discord.File(
            image,
            filename="collection.png",
        )

        embed = discord.Embed(
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collection.png"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file,
            ephemeral=True,
        )


class StatusSelect(discord.ui.Select):

    def __init__(self, collection_view):
        self.collection_view = collection_view

        options = [
            discord.SelectOption(
                label="All",
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
            placeholder="Filter by Status",
            options=options,
        )

    async def callback(self, interaction):
        value = self.values[0]

        if value == "all":
            self.collection_view.status = None
        else:
            self.collection_view.status = value

        self.collection_view.page = 0

        await self.collection_view.refresh(interaction)


class StatusView(discord.ui.View):

    def __init__(self, collection_view):
        super().__init__(timeout=120)

        self.add_item(
            StatusSelect(collection_view)
        )


class CollectionView(discord.ui.View):

    def __init__(
        self,
        *,
        page=0,
        vault=None,
        status=None,
    ):
        super().__init__(timeout=180)

        self.page = page
        self.vault = vault
        self.status = status

        self.current_collections = []

        self.refresh_buttons()

    def refresh_buttons(self):
        self.clear_items()

        self.current_collections = get_filtered_collections(
            vault=self.vault,
            status=self.status,
        )

        start = self.page * 9
        end = start + 9

        page_collections = self.current_collections[
            start:end
        ]

        self.current_collections = page_collections

        if page_collections:
            self.add_item(
                CollectionSelect(self)
            )

        self.add_item(
            VaultButton("BB", "🌙 BB", self)
        )

        self.add_item(
            VaultButton("GG", "🌹 GG", self)
        )

        self.add_item(
            VaultButton("BG", "🪡 BG", self)
        )

        self.add_item(
            SearchButton(self)
        )

        self.add_item(
            StatusButton(self)
        )

        if self.page > 0:
            self.add_item(
                PreviousButton(self)
            )

        total = len(
            get_filtered_collections(
                vault=self.vault,
                status=self.status,
            )
        )

        if (self.page + 1) * 9 < total:
            self.add_item(
                NextButton(self)
            )

    async def refresh(self, interaction):
        self.refresh_buttons()

        image = create_cover_board(
            self.current_collections
        )

        if image is None:
            embed = discord.Embed(
                description="No collections found.",
                color=EMBED_COLOR,
            )

            await interaction.response.edit_message(
                embeds=[
                    discord.Embed(
                        color=EMBED_COLOR
                    )
                    .set_image(url=HEADER_URL),
                    embed,
                ],
                attachments=[],
                view=self,
            )

            return

        file = discord.File(
            image,
            filename="collection_covers.png",
        )

        header_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        header_embed.set_image(
            url=HEADER_URL
        )

        content_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        content_embed.set_image(
            url="attachment://collection_covers.png"
        )

        await interaction.response.edit_message(
            embeds=[
                header_embed,
                content_embed,
            ],
            attachments=[file],
            view=self,
        )


class VaultButton(discord.ui.Button):

    def __init__(self, vault, label, collection_view):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
        )

        self.vault = vault
        self.collection_view = collection_view

    async def callback(self, interaction):
        self.collection_view.vault = self.vault
        self.collection_view.page = 0

        await self.collection_view.refresh(interaction)


class SearchButton(discord.ui.Button):

    def __init__(self, collection_view):
        super().__init__(
            label="Search",
            style=discord.ButtonStyle.secondary,
        )

        self.collection_view = collection_view

    async def callback(self, interaction):
        await interaction.response.send_modal(
            CollectionSearchModal(
                self.collection_view
            )
        )


class StatusButton(discord.ui.Button):

    def __init__(self, collection_view):
        super().__init__(
            label="Status",
            style=discord.ButtonStyle.secondary,
        )

        self.collection_view = collection_view

    async def callback(self, interaction):
        view = StatusView(
            self.collection_view
        )

        await interaction.response.send_message(
            "Choose a collection status:",
            view=view,
            ephemeral=True,
        )


class PreviousButton(discord.ui.Button):

    def __init__(self, collection_view):
        super().__init__(
            label="Previous",
            style=discord.ButtonStyle.secondary,
        )

        self.collection_view = collection_view

    async def callback(self, interaction):
        self.collection_view.page -= 1

        await self.collection_view.refresh(interaction)


class NextButton(discord.ui.Button):

    def __init__(self, collection_view):
        super().__init__(
            label="Next",
            style=discord.ButtonStyle.secondary,
        )

        self.collection_view = collection_view

    async def callback(self, interaction):
        self.collection_view.page += 1

        await self.collection_view.refresh(interaction)


class Collection(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="collection",
        description="View the Magic Cabinet collection gallery.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        view = CollectionView()

        image = create_cover_board(
            view.current_collections
        )

        if image is None:
            embed = discord.Embed(
                description="No collections are available yet.",
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embeds=[
                    discord.Embed(
                        color=EMBED_COLOR
                    ).set_image(
                        url=HEADER_URL
                    ),
                    embed,
                ],
                view=view,
            )

            return

        file = discord.File(
            image,
            filename="collection_covers.png",
        )

        header_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        header_embed.set_image(
            url=HEADER_URL
        )

        content_embed = discord.Embed(
            color=EMBED_COLOR,
        )

        content_embed.set_image(
            url="attachment://collection_covers.png"
        )

        await interaction.response.send_message(
            embeds=[
                header_embed,
                content_embed,
            ],
            file=file,
            view=view,
        )


async def setup(bot):
    await bot.add_cog(Collection(bot))
