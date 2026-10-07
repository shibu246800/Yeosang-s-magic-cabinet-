"""Magic Cabinet collection command."""

import io
import json
import math
import sqlite3
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
DATABASE = "cabinet.db"


# ============================================================
# DATA
# ============================================================

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


def get_collection_cards(collection_id):
    """Return the six base cards for a collection."""

    for collection in COLLECTIONS:
        if collection.get("id") == collection_id:
            cards = collection.get("cards", [])

            base_cards = [
                card for card in cards
                if not card.get("legendary", False)
            ]

            return sorted(
                base_cards,
                key=lambda card: int(card.get("id", 0))
                if str(card.get("id", "")).isdigit()
                else 999999,
            )

    return []


def get_legendary_card(collection_id):
    """Return the legendary card if it exists."""

    for collection in COLLECTIONS:
        if collection.get("id") == collection_id:
            for card in collection.get("cards", []):
                if card.get("legendary", False):
                    return card

    return None


def get_owned_card_ids(user_id):
    """Return all card IDs currently owned by a player."""

    try:
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

        return {int(row[0]) for row in rows}

    except sqlite3.Error:
        return set()


def collection_status(collection, user_id):
    """Return a player's collection status."""

    cards = get_collection_cards(collection.get("id"))

    if not cards:
        return "Unattended"

    owned_ids = get_owned_card_ids(user_id)

    owned_base = sum(
        1 for card in cards
        if str(card.get("id")) in {
            str(card_id) for card_id in owned_ids
        }
    )

    if owned_base == 0:
        return "Unattended"

    if owned_base < len(cards):
        return "Ongoing"

    legendary = get_legendary_card(collection.get("id"))

    if legendary:
        legendary_id = legendary.get("id")

        if str(legendary_id).isdigit():
            if int(legendary_id) in owned_ids:
                return "Completed"

        elif str(legendary_id) in {
            str(card_id) for card_id in owned_ids
        }:
            return "Completed"

        return "Ongoing"

    return "Completed"


def get_filtered_collections(vault=None, status=None, user_id=None):
    """Filter collections for the gallery."""

    collections = COLLECTIONS[:]

    if vault:
        collections = [
            collection
            for collection in collections
            if collection.get("vault", "").upper() == vault.upper()
        ]

    if status and user_id is not None:
        collections = [
            collection
            for collection in collections
            if collection_status(collection, user_id) == status
        ]

    return collections


# ============================================================
# IMAGE HELPERS
# ============================================================

def download_image(url):
    """Download an image from GitHub/raw URL."""

    if not url:
        return None

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read()

        return Image.open(io.BytesIO(data)).convert("RGB")

    except Exception:
        return None


def create_cover_board(collections):
    """Create the collection cover gallery."""

    if not collections:
        image = Image.new("RGB", (1200, 400), "white")
        draw = ImageDraw.Draw(image)

        draw.text(
            (600, 200),
            "No collections found.",
            fill="#4E0017",
            anchor="mm",
        )

        output = io.BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return output

    count = len(collections)

    if count == 1:
        columns = 1
    elif count <= 4:
        columns = 2
    else:
        columns = 3

    rows = math.ceil(count / columns)

    board_width = 1200
    outer_padding = 70
    gap = 35

    usable_width = (
        board_width
        - (outer_padding * 2)
        - (gap * (columns - 1))
    )

    cell_width = usable_width // columns
    cover_width = cell_width
    cover_height = int(cover_width * 1.4)

    board_height = (
        outer_padding * 2
        + (cover_height * rows)
        + (gap * (rows - 1))
    )

    board = Image.new(
        "RGB",
        (board_width, board_height),
        "white",
    )

    for index, collection in enumerate(collections):

        cover = download_image(collection.get("cover"))

        if cover is None:
            continue

        cover = ImageOps.fit(
            cover,
            (cover_width, cover_height),
            method=Image.Resampling.LANCZOS,
        )

        row = index // columns
        column = index % columns

        x = outer_padding + column * (cell_width + gap)
        y = outer_padding + row * (cover_height + gap)

        board.paste(cover, (x, y))

    output = io.BytesIO()
    board.save(output, format="PNG")
    output.seek(0)

    return output


def build_collection_board(collection, user_id):
    """Create the seven-card collection board."""

    collection_id = collection.get("id", "")
    collection_name = collection.get("name", "")

    base_cards = get_collection_cards(collection_id)
    legendary = get_legendary_card(collection_id)

    owned_ids = get_owned_card_ids(user_id)

    # --------------------------------------------------------
    # BOARD SETTINGS
    # --------------------------------------------------------

    board_width = 1200
    padding = 70
    gap = 35

    columns = 3

    card_width = (
        board_width
        - (padding * 2)
        - (gap * 2)
    ) // columns

    card_height = int(card_width * 1.4)

    row_height = card_height + gap

    board_height = (
        padding
        + (row_height * 3)
        + 100
    )

    board = Image.new(
        "RGB",
        (board_width, board_height),
        "white",
    )

    draw = ImageDraw.Draw(board)

    # --------------------------------------------------------
    # SIX BASE CARDS
    # --------------------------------------------------------

    for index in range(6):

        x = padding + (index % 3) * (card_width + gap)
        y = padding + (index // 3) * row_height

        # No card data yet
        if index >= len(base_cards):
            draw.rectangle(
                [x, y, x + card_width, y + card_height],
                fill="#E8E8E8",
                outline="#4E0017",
                width=3,
            )
            continue

        card = base_cards[index]
        card_id = card.get("id")
        image_url = card.get("image", "")

        card_image = download_image(image_url)

        # Missing image
        if card_image is None:
            draw.rectangle(
                [x, y, x + card_width, y + card_height],
                fill="#E8E8E8",
                outline="#4E0017",
                width=3,
            )
            continue

        card_image = ImageOps.fit(
            card_image,
            (card_width, card_height),
            method=Image.Resampling.LANCZOS,
        )

        # ----------------------------------------------------
        # OWNED = FULL COLOR
        # NOT OWNED = GRAYSCALE
        # ----------------------------------------------------

        try:
            numeric_id = int(card_id)

            if numeric_id not in owned_ids:
                card_image = ImageOps.grayscale(card_image)
                card_image = card_image.convert("RGB")

        except (TypeError, ValueError):
            pass

        board.paste(card_image, (x, y))

    # --------------------------------------------------------
    # LEGENDARY
    # --------------------------------------------------------

    legendary_x = padding + (card_width + gap)
    legendary_y = padding + (row_height * 2)

    legendary_owned = False

    if legendary:
        legendary_id = legendary.get("id")

        try:
            legendary_owned = int(legendary_id) in owned_ids
        except (TypeError, ValueError):
            legendary_owned = str(legendary_id) in {
                str(card_id) for card_id in owned_ids
            }

    if legendary_owned and legendary.get("image"):
        legendary_image = download_image(
            legendary.get("image")
        )

        if legendary_image:
            legendary_image = ImageOps.fit(
                legendary_image,
                (card_width, card_height),
                method=Image.Resampling.LANCZOS,
            )

            board.paste(
                legendary_image,
                (legendary_x, legendary_y),
            )
        else:
            draw.rectangle(
                [
                    legendary_x,
                    legendary_y,
                    legendary_x + card_width,
                    legendary_y + card_height,
                ],
                fill="black",
            )

    else:
        # Legendary stays completely black
        draw.rectangle(
            [
                legendary_x,
                legendary_y,
                legendary_x + card_width,
                legendary_y + card_height,
            ],
            fill="black",
        )

    # --------------------------------------------------------
    # COLLECTION INFO
    # --------------------------------------------------------

    info_y = board_height - 45

    draw.text(
        (board_width // 2, info_y),
        f"{collection_id}  •  {collection_name}",
        fill="#4E0017",
        anchor="mm",
    )

    output = io.BytesIO()
    board.save(output, format="PNG")
    output.seek(0)

    return output


# ============================================================
# COLLECTION SELECT
# ============================================================

class CollectionSelect(discord.ui.Select):

    def __init__(self, collection_view):

        self.collection_view = collection_view

        options = []

        for collection in collection_view.current_collections:

            options.append(
                discord.SelectOption(
                    label=collection.get("name", "Collection")[:100],
                    description=(
                        f"{collection.get('id', '')} • "
                        f"{collection.get('series', '')}"
                    )[:100],
                    value=collection.get("id", ""),
                )
            )

        if not options:
            options = [
                discord.SelectOption(
                    label="No collections available",
                    value="none",
                )
            ]

        super().__init__(
            placeholder="Open Collection",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
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

        image = build_collection_board(
            collection,
            interaction.user.id,
        )

        file = discord.File(
            image,
            filename="collection.png",
        )

        embed = discord.Embed(
            color=EMBED_COLOR,
        )

        embed.set_image(url="attachment://collection.png")

        await interaction.response.send_message(
            embed=embed,
            file=file,
            ephemeral=True,
        )


# ============================================================
# SEARCH
# ============================================================

class CollectionSearchModal(discord.ui.Modal, title="Search Collection"):

    collection_id = discord.ui.TextInput(
        label="Collection ID",
        placeholder="Example: BB_1",
        required=True,
        max_length=30,
    )

    def __init__(self, collection_view):
        super().__init__()
        self.collection_view = collection_view

    async def on_submit(self, interaction):

        search_id = self.collection_id.value.strip().upper()

        collection = next(
            (
                item
                for item in COLLECTIONS
                if item.get("id", "").upper() == search_id
            ),
            None,
        )

        if not collection:
            await interaction.response.send_message(
                f"Collection `{search_id}` was not found.",
                ephemeral=True,
            )
            return

        image = build_collection_board(
            collection,
            interaction.user.id,
        )

        file = discord.File(
            image,
            filename="collection.png",
        )

        embed = discord.Embed(
            color=EMBED_COLOR,
        )

        embed.set_image(url="attachment://collection.png")

        await interaction.response.send_message(
            embed=embed,
            file=file,
            ephemeral=True,
        )


# ============================================================
# STATUS
# ============================================================

class StatusSelect(discord.ui.Select):

    def __init__(self, collection_view):

        self.collection_view = collection_view

        options = [
            discord.SelectOption(
                label="Completed",
                value="Completed",
            ),
            discord.SelectOption(
                label="Ongoing",
                value="Ongoing",
            ),
            discord.SelectOption(
                label="Unattended",
                value="Unattended",
            ),
        ]

        super().__init__(
            placeholder="Choose Status",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction):

        self.collection_view.status = self.values[0]
        self.collection_view.current_page = 0

        await self.collection_view.refresh(interaction)


class StatusView(discord.ui.View):

    def __init__(self, collection_view):

        super().__init__(timeout=60)

        self.add_item(
            StatusSelect(collection_view)
        )


# ============================================================
# MAIN COLLECTION VIEW
# ============================================================

class CollectionView(discord.ui.View):

    def __init__(
        self,
        user_id,
        vault=None,
        status=None,
        current_page=0,
    ):

        super().__init__(timeout=300)

        self.user_id = user_id
        self.vault = vault
        self.status = status
        self.current_page = current_page

        self.current_collections = []

        self.refresh_buttons()

    def refresh_buttons(self):

        self.clear_items()

        filtered = get_filtered_collections(
            vault=self.vault,
            status=self.status,
            user_id=self.user_id,
        )

        start = self.current_page * 9
        end = start + 9

        self.current_collections = filtered[start:end]

        # Open collection dropdown
        self.add_item(
            CollectionSelect(self)
        )

        # Vault buttons
        self.add_item(
            VaultButton(self, "BB", "🌙 BB")
        )

        self.add_item(
            VaultButton(self, "GG", "🌹 GG")
        )

        self.add_item(
            VaultButton(self, "BG", "🪡 BG")
        )

        # Search
        self.add_item(
            SearchButton(self)
        )

        # Status
        self.add_item(
            StatusButton(self)
        )

        # Previous
        if self.current_page > 0:
            self.add_item(
                PreviousButton(self)
            )

        # Next
        total_pages = max(
            1,
            math.ceil(len(filtered) / 9),
        )

        if self.current_page < total_pages - 1:
            self.add_item(
                NextButton(self)
            )

    async def refresh(self, interaction):

        filtered = get_filtered_collections(
            vault=self.vault,
            status=self.status,
            user_id=self.user_id,
        )

        total_pages = max(
            1,
            math.ceil(len(filtered) / 9),
        )

        if self.current_page >= total_pages:
            self.current_page = total_pages - 1

        start = self.current_page * 9
        end = start + 9

        self.current_collections = filtered[start:end]

        self.refresh_buttons()

        image = create_cover_board(
            self.current_collections
        )

        file = discord.File(
            image,
            filename="collections.png",
        )

        embed = discord.Embed(
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collections.png"
        )

        embed.set_footer(
            text=(
                f"Page {self.current_page + 1} / "
                f"{total_pages}"
            )
        )

        await interaction.response.edit_message(
            embed=embed,
            attachments=[file],
            view=self,
        )


# ============================================================
# BUTTONS
# ============================================================

class VaultButton(discord.ui.Button):

    def __init__(self, collection_view, vault, label):

        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            row=1,
        )

        self.collection_view = collection_view
        self.vault = vault

    async def callback(self, interaction):

        if self.collection_view.vault == self.vault:
            self.collection_view.vault = None
        else:
            self.collection_view.vault = self.vault

        self.collection_view.current_page = 0
        self.collection_view.status = None

        await self.collection_view.refresh(interaction)


class SearchButton(discord.ui.Button):

    def __init__(self, collection_view):

        super().__init__(
            label="Search",
            style=discord.ButtonStyle.secondary,
            row=1,
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
            row=1,
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
            row=2,
        )

        self.collection_view = collection_view

    async def callback(self, interaction):

        self.collection_view.current_page -= 1

        await self.collection_view.refresh(
            interaction
        )


class NextButton(discord.ui.Button):

    def __init__(self, collection_view):

        super().__init__(
            label="Next",
            style=discord.ButtonStyle.secondary,
            row=2,
        )

        self.collection_view = collection_view

    async def callback(self, interaction):

        self.collection_view.current_page += 1

        await self.collection_view.refresh(
            interaction
        )


# ============================================================
# COG
# ============================================================

class Collection(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @app_commands.command(
        name="collection",
        description="View your Magic Cabinet collections.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):

        view = CollectionView(
            user_id=interaction.user.id
        )

        image = create_cover_board(
            view.current_collections
        )

        file = discord.File(
            image,
            filename="collections.png",
        )

        embed = discord.Embed(
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collections.png"
        )

        total_pages = max(
            1,
            math.ceil(len(COLLECTIONS) / 9),
        )

        embed.set_footer(
            text=f"Page 1 / {total_pages}"
        )

        header_embed = discord.Embed(
            color=EMBED_COLOR
        )

        header_embed.set_image(
            url=HEADER_URL
        )

        await interaction.response.send_message(
            embeds=[
                header_embed,
                embed,
            ],
            file=file,
            view=view,
        )


async def setup(bot):

    await bot.add_cog(
        Collection(bot)
        )
