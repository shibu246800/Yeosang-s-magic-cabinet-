"""Magic Cabinet collection command."""

import asyncio
import io
import json
import math
import sqlite3
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageOps


# ============================================================
# CONFIG
# ============================================================

DATABASE = "cabinet.db"

EMBED_COLOR = 0x4E0017

HEADER_URL = (
    "https://raw.githubusercontent.com/shibu246800/"
    "Yeosang-s-magic-cabinet-/refs/heads/main/"
    "magic_cabinet/cogs/profile/"
    "Untitled13_20261005205021.jpg"
)

DIVIDER_URL = (
    "https://raw.githubusercontent.com/shibu246800/"
    "Yeosang-s-magic-cabinet-/refs/heads/main/"
    "magic_cabinet/cogs/profile/"
    "Untitled14_20261003173415.jpg"
)

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "collections.json"
)

PAGE_SIZE = 9

CARD_WIDTH = 832
CARD_HEIGHT = 1247

GALLERY_BG = "white"


# ============================================================
# REAL CARD DATA
# ============================================================

from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS


ALL_CARDS = (
    NORMAL_CARDS
    + RARE_CARDS
    + EPIC_CARDS
    + LIMITED_CARDS
)


# ============================================================
# IMAGE CACHE
# ============================================================

_IMAGE_CACHE = {}

_COLLECTION_BOARD_CACHE = {}

_IMAGE_EXECUTOR = ThreadPoolExecutor(
    max_workers=8,
    thread_name_prefix="cabinet-image",
)


# ============================================================
# COLLECTION DATA
# ============================================================

def load_collections():
    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("collections", [])

    except Exception:
        return []


COLLECTIONS = load_collections()


# ============================================================
# HELPERS
# ============================================================

def get_collection(collection_id):
    for collection in COLLECTIONS:
        if collection.get("id") == collection_id:
            return collection

    return None


def get_collection_cards(collection_id):
    cards = [
        card
        for card in ALL_CARDS
        if card.get("collection_id") == collection_id
    ]

    return sorted(
        cards,
        key=lambda card: int(card.get("id", 0)),
    )


def get_owned_card_ids(user_id):
    connection = sqlite3.connect(DATABASE)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT card_id
            FROM bag
            WHERE user_id = ?
            AND quantity > 0
            """,
            (user_id,),
        )

        return {
            row[0]
            for row in cursor.fetchall()
        }

    finally:
        connection.close()


def get_collection_status(collection_id, owned_ids):
    cards = get_collection_cards(collection_id)

    if not cards:
        return "Unattended", 0

    owned_count = sum(
        1
        for card in cards
        if card.get("id") in owned_ids
    )

    if owned_count == 0:
        return "Unattended", 0

    if owned_count < 6:
        return "Ongoing", owned_count

    return "Completed", owned_count


def status_emoji(status):
    if status == "Completed":
        return "🟢"

    if status == "Ongoing":
        return "🟡"

    return "⚪"


def filtered_collections(vault=None, status=None, user_id=None):
    result = list(COLLECTIONS)

    owned_ids = set()

    if user_id is not None and status:
        owned_ids = get_owned_card_ids(user_id)

    if vault:
        result = [
            collection
            for collection in result
            if collection.get("vault") == vault
        ]

    if status:
        result = [
            collection
            for collection in result
            if get_collection_status(
                collection.get("id"),
                owned_ids,
            )[0] == status
        ]

    return result


# ============================================================
# FAST IMAGE LOADING
# ============================================================

def _download_image(url):
    if not url:
        return None

    if url in _IMAGE_CACHE:
        return _IMAGE_CACHE[url].copy()

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Yeosang-Magic-Cabinet/1.0",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=8,
        ) as response:
            data = response.read()

        image = Image.open(
            io.BytesIO(data)
        ).convert("RGB")

        _IMAGE_CACHE[url] = image.copy()

        return image

    except Exception:
        return None


async def get_image(url):
    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        _IMAGE_EXECUTOR,
        _download_image,
        url,
    )


# ============================================================
# GALLERY IMAGE
# ============================================================

def _build_gallery_sync(collections):
    if not collections:
        image = Image.new(
            "RGB",
            (1200, 600),
            GALLERY_BG,
        )

        draw = ImageDraw.Draw(image)

        draw.text(
            (600, 300),
            "No collections found.",
            fill="#4E0017",
            anchor="mm",
        )

        output = io.BytesIO()

        image.save(
            output,
            format="PNG",
        )

        output.seek(0)

        return output.getvalue()

    count = len(collections)

    if count == 1:
        columns = 1

    elif count <= 4:
        columns = 2

    else:
        columns = 3

    rows = math.ceil(count / columns)

    cell_width = 850
    cell_height = 650

    padding = 45
    gap = 30

    width = (
        padding * 2
        + columns * cell_width
        + (columns - 1) * gap
    )

    height = (
        padding * 2
        + rows * cell_height
        + (rows - 1) * gap
    )

    canvas = Image.new(
        "RGB",
        (width, height),
        GALLERY_BG,
    )

    for index, collection in enumerate(collections):

        cover = _download_image(
            collection.get("cover")
        )

        if cover is None:
            continue

        cover.thumbnail(
            (
                cell_width - 20,
                cell_height - 20,
            ),
            Image.Resampling.LANCZOS,
        )

        x = (
            padding
            + (index % columns)
            * (cell_width + gap)
        )

        y = (
            padding
            + (index // columns)
            * (cell_height + gap)
        )

        paste_x = (
            x
            + (cell_width - cover.width) // 2
        )

        paste_y = (
            y
            + (cell_height - cover.height) // 2
        )

        canvas.paste(
            cover,
            (
                paste_x,
                paste_y,
            ),
        )

    output = io.BytesIO()

    canvas.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)

    return output.getvalue()


async def build_gallery(collections):
    loop = asyncio.get_running_loop()

    urls = [
        collection.get("cover")
        for collection in collections
        if collection.get("cover")
    ]

    await asyncio.gather(
        *(get_image(url) for url in urls)
    )

    return await loop.run_in_executor(
        _IMAGE_EXECUTOR,
        _build_gallery_sync,
        collections,
    )


# ============================================================
# COLLECTION BOARD
# ============================================================

def _build_collection_board_sync(
    collection,
    owned_ids,
):
    cards = get_collection_cards(
        collection.get("id")
    )

    canvas_width = CARD_WIDTH * 3 + 80
    canvas_height = CARD_HEIGHT * 3 + 160

    canvas = Image.new(
        "RGB",
        (
            canvas_width,
            canvas_height,
        ),
        "white",
    )

    draw = ImageDraw.Draw(canvas)

    for index in range(6):

        x = (
            20
            + (index % 3)
            * (CARD_WIDTH + 20)
        )

        y = (
            20
            + (index // 3)
            * (CARD_HEIGHT + 20)
        )

        if index < len(cards):

            card = cards[index]

            card_id = card.get("id")

            image = _download_image(
                card.get("image")
            )

            if image is None:
                image = Image.new(
                    "RGB",
                    (
                        CARD_WIDTH,
                        CARD_HEIGHT,
                    ),
                    "#DDDDDD",
                )

            image = ImageOps.fit(
                image,
                (
                    CARD_WIDTH,
                    CARD_HEIGHT,
                ),
                method=Image.Resampling.LANCZOS,
            )

            if card_id not in owned_ids:
                image = ImageOps.grayscale(
                    image
                ).convert("RGB")

            canvas.paste(
                image,
                (x, y),
            )

        else:
            draw.rectangle(
                (
                    x,
                    y,
                    x + CARD_WIDTH,
                    y + CARD_HEIGHT,
                ),
                fill="#EEEEEE",
                outline="#AAAAAA",
                width=4,
            )

    # Legendary slot
    legendary_x = (
        (canvas_width - CARD_WIDTH) // 2
    )

    legendary_y = (
        20
        + 2 * (CARD_HEIGHT + 20)
    )

    draw.rectangle(
        (
            legendary_x,
            legendary_y,
            legendary_x + CARD_WIDTH,
            legendary_y + CARD_HEIGHT,
        ),
        fill="#111111",
        outline="#4E0017",
        width=8,
    )

    draw.text(
        (
            legendary_x + CARD_WIDTH // 2,
            legendary_y + CARD_HEIGHT // 2,
        ),
        "LEGENDARY",
        fill="#D4AF37",
        anchor="mm",
    )

    # Bottom label
    label = (
        f"{collection.get('id')}  •  "
        f"{collection.get('name', 'Unknown Collection')}"
    )

    draw.rectangle(
        (
            0,
            canvas_height - 80,
            canvas_width,
            canvas_height,
        ),
        fill="white",
    )

    draw.text(
        (
            canvas_width // 2,
            canvas_height - 40,
        ),
        label,
        fill="#4E0017",
        anchor="mm",
    )

    output = io.BytesIO()

    canvas.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)

    return output.getvalue()


async def build_collection_board(
    collection,
    owned_ids,
):
    collection_id = collection.get("id")

    cache_key = (
        collection_id,
        tuple(sorted(owned_ids)),
    )

    cached = _COLLECTION_BOARD_CACHE.get(
        cache_key
    )

    if cached is not None:
        return cached

    loop = asyncio.get_running_loop()

    urls = [
        card.get("image")
        for card in get_collection_cards(
            collection_id
        )
        if card.get("image")
    ]

    await asyncio.gather(
        *(get_image(url) for url in urls)
    )

    image_bytes = await loop.run_in_executor(
        _IMAGE_EXECUTOR,
        _build_collection_board_sync,
        collection,
        owned_ids,
    )

    _COLLECTION_BOARD_CACHE[cache_key] = image_bytes

    return image_bytes


# ============================================================
# MAIN VIEW
# ============================================================

class CollectionView(discord.ui.View):

    def __init__(
        self,
        bot,
        user_id,
        page=0,
        vault=None,
        status=None,
    ):
        super().__init__(
            timeout=None
        )

        self.bot = bot
        self.user_id = user_id
        self.page = page
        self.vault = vault
        self.status = status

        self.current_collections = []

        self.refresh_components()

    # --------------------------------------------------------
    # FILTERED DATA
    # --------------------------------------------------------

    def get_filtered(self):
        return filtered_collections(
            vault=self.vault,
            status=self.status,
            user_id=self.user_id,
        )

    # --------------------------------------------------------
    # PAGE COUNT
    # --------------------------------------------------------

    def page_count(self):
        total = len(self.get_filtered())

        return max(
            1,
            math.ceil(
                total / PAGE_SIZE
            ),
        )

    # --------------------------------------------------------
    # PAGE DATA
    # --------------------------------------------------------

    def get_page_collections(self):
        collections = self.get_filtered()

        total_pages = self.page_count()

        self.page = max(
            0,
            min(
                self.page,
                total_pages - 1,
            ),
        )

        start = self.page * PAGE_SIZE

        return collections[
            start:start + PAGE_SIZE
        ]

    # --------------------------------------------------------
    # COMPONENTS
    # --------------------------------------------------------

    def refresh_components(self):
        self.clear_items()

        page_collections = (
            self.get_page_collections()
        )

        self.current_collections = (
            page_collections
        )

        # Open collection select
        if page_collections:

            options = []

            for collection in page_collections:

                options.append(
                    discord.SelectOption(
                        label=(
                            f"{collection.get('id')} • "
                            f"{collection.get('name', 'Collection')}"
                        )[:100],
                        value=collection.get("id"),
                        description=(
                            f"{collection.get('series', '')} • "
                            f"{collection.get('vault', '')}"
                        )[:100],
                    )
                )

            select = CollectionSelect(
                self,
                options,
            )

            self.add_item(select)

        # Vault buttons
        for vault_code, label in (
            ("BB", "🌙 BB"),
            ("GG", "🌹 GG"),
            ("BG", "🪡 BG"),
        ):

            button = VaultButton(
                self,
                vault_code,
                label,
            )

            if self.vault == vault_code:
                button.style = discord.ButtonStyle.danger

            self.add_item(button)

        # Status
        status_select = StatusSelect(
            self,
            self.status,
        )

        self.add_item(status_select)

        # Previous
        previous = PreviousButton(self)

        previous.disabled = (
            self.page <= 0
        )

        self.add_item(previous)

        # Next
        next_button = NextButton(self)

        next_button.disabled = (
            self.page >= self.page_count() - 1
        )

        self.add_item(next_button)

        # Search
        self.add_item(
            SearchButton(self)
        )

    # --------------------------------------------------------
    # REFRESH
    # --------------------------------------------------------

    async def refresh_message(
        self,
        interaction,
    ):
        self.refresh_components()

        page_collections = (
            self.current_collections
        )

        image_bytes = await build_gallery(
            page_collections
        )

        file = discord.File(
            io.BytesIO(image_bytes),
            filename="collection_gallery.png",
        )

        total = len(
            self.get_filtered()
        )

        if total:
            start = (
                self.page * PAGE_SIZE + 1
            )

            end = min(
                (self.page + 1) * PAGE_SIZE,
                total,
            )

            range_text = (
                f"Collections **{start}–{end}**"
            )

        else:
            range_text = "No collections found."

        embed = discord.Embed(
            title="The Collection",
            description=(
                f"Page **{self.page + 1} / "
                f"{self.page_count()}**\n"
                f"{range_text}"
            ),
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collection_gallery.png"
        )

        embed.set_footer(
            text="Select a collection to open it."
        )

        await interaction.edit_original_response(
            embeds=[
                embed,
            ],
            attachments=[
                file,
            ],
            view=self,
        )


# ============================================================
# OPEN COLLECTION SELECT
# ============================================================

class CollectionSelect(
    discord.ui.Select
):

    def __init__(
        self,
        parent_view,
        options,
    ):
        self.parent_view = parent_view

        super().__init__(
            placeholder="Open Collection",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        collection_id = self.values[0]

        collection = get_collection(
            collection_id
        )

        if collection is None:

            await interaction.followup.send(
                "Collection not found.",
                ephemeral=True,
            )

            return

        owned_ids = await asyncio.to_thread(
            get_owned_card_ids,
            interaction.user.id,
        )

        image_bytes = await build_collection_board(
            collection,
            owned_ids,
        )

        file = discord.File(
            io.BytesIO(image_bytes),
            filename="collection.png",
        )

        status, count = await asyncio.to_thread(
            get_collection_status,
            collection_id,
            owned_ids,
        )

        embed = discord.Embed(
            title=collection.get(
                "name",
                "Collection",
            ),
            description=(
                f"**{collection.get('id')}**\n"
                f"{collection.get('series', '')}\n\n"
                f"{status_emoji(status)} "
                f"**{status}** • "
                f"**{count}/6**"
            ),
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collection.png"
        )

        await interaction.followup.send(
            embeds=[
                embed,
            ],
            files=[
                file,
            ],
            ephemeral=True,
        )


# ============================================================
# VAULT BUTTON
# ============================================================

class VaultButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
        vault_code,
        label,
    ):
        self.parent_view = parent_view
        self.vault_code = vault_code

        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            row=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        if self.parent_view.vault == self.vault_code:
            self.parent_view.vault = None

        else:
            self.parent_view.vault = (
                self.vault_code
            )

        self.parent_view.page = 0

        await self.parent_view.refresh_message(
            interaction
        )


# ============================================================
# STATUS SELECT
# ============================================================

class StatusSelect(
    discord.ui.Select
):

    def __init__(
        self,
        parent_view,
        current_status,
    ):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(
                label="All Collections",
                value="ALL",
                default=current_status is None,
            ),
            discord.SelectOption(
                label="Completed",
                value="Completed",
                default=current_status == "Completed",
            ),
            discord.SelectOption(
                label="Ongoing",
                value="Ongoing",
                default=current_status == "Ongoing",
            ),
            discord.SelectOption(
                label="Unattended",
                value="Unattended",
                default=current_status == "Unattended",
            ),
        ]

        super().__init__(
            placeholder="Filter by Status",
            options=options,
            row=2,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        value = self.values[0]

        if value == "ALL":
            self.parent_view.status = None

        else:
            self.parent_view.status = value

        self.parent_view.page = 0

        await self.parent_view.refresh_message(
            interaction
        )


# ============================================================
# PREVIOUS
# ============================================================

class PreviousButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
    ):
        self.parent_view = parent_view

        super().__init__(
            label="‹ Previous",
            style=discord.ButtonStyle.secondary,
            row=3,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        if self.parent_view.page <= 0:
            return

        self.parent_view.page -= 1

        await self.parent_view.refresh_message(
            interaction
        )


# ============================================================
# NEXT
# ============================================================

class NextButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
    ):
        self.parent_view = parent_view

        super().__init__(
            label="Next ›",
            style=discord.ButtonStyle.secondary,
            row=3,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        if (
            self.parent_view.page
            >= self.parent_view.page_count() - 1
        ):
            return

        self.parent_view.page += 1

        await self.parent_view.refresh_message(
            interaction
        )


# ============================================================
# SEARCH MODAL
# ============================================================

class CollectionSearchModal(
    discord.ui.Modal,
    title="Search Collection",
):

    collection_id = discord.ui.TextInput(
        label="Collection ID",
        placeholder="Example: BB_1",
        required=True,
        max_length=30,
    )

    def __init__(
        self,
        parent_view,
    ):
        super().__init__()

        self.parent_view = parent_view

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        collection_id = (
            str(self.collection_id)
            .strip()
            .upper()
        )

        collection = get_collection(
            collection_id
        )

        if collection is None:

            await interaction.followup.send(
                f"Collection **{collection_id}** was not found.",
                ephemeral=True,
            )

            return

        owned_ids = await asyncio.to_thread(
            get_owned_card_ids,
            interaction.user.id,
        )

        image_bytes = await build_collection_board(
            collection,
            owned_ids,
        )

        file = discord.File(
            io.BytesIO(image_bytes),
            filename="collection.png",
        )

        status, count = await asyncio.to_thread(
            get_collection_status,
            collection_id,
            owned_ids,
        )

        embed = discord.Embed(
            title=collection.get(
                "name",
                "Collection",
            ),
            description=(
                f"**{collection.get('id')}**\n"
                f"{collection.get('series', '')}\n\n"
                f"{status_emoji(status)} "
                f"**{status}** • "
                f"**{count}/6**"
            ),
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collection.png"
        )

        await interaction.followup.send(
            embeds=[
                embed,
            ],
            files=[
                file,
            ],
            ephemeral=True,
        )


# ============================================================
# COLLECTION COG
# ============================================================

class Collection(
    commands.Cog
):

    def __init__(
        self,
        bot,
    ):
        self.bot = bot
        self.active_views = []

    # --------------------------------------------------------
    # /collection
    # --------------------------------------------------------

    @app_commands.command(
        name="collection",
        description="Browse the Magic Cabinet collections.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        view = CollectionView(
            self.bot,
            interaction.user.id,
        )

        # Keep the View alive while the bot is running.
        self.active_views.append(view)

        page_collections = (
            view.get_page_collections()
        )

        image_bytes = await build_gallery(
            page_collections
        )

        file = discord.File(
            io.BytesIO(image_bytes),
            filename="collection_gallery.png",
        )

        total = len(
            view.get_filtered()
        )

        if total:
            start = (
                view.page * PAGE_SIZE + 1
            )

            end = min(
                (view.page + 1) * PAGE_SIZE,
                total,
            )

            range_text = (
                f"Collections **{start}–{end}**"
            )

        else:
            range_text = "No collections found."

        embed = discord.Embed(
            title="The Collection",
            description=(
                f"Page **1 / {view.page_count()}**\n"
                f"{range_text}"
            ),
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collection_gallery.png"
        )

        embed.set_footer(
            text="Select a collection to open it."
        )

        await interaction.followup.send(
            embeds=[
                discord.Embed(
                    color=EMBED_COLOR,
                ).set_image(
                    url=HEADER_URL
                ),
                embed,
                discord.Embed(
                    color=EMBED_COLOR,
                ).set_image(
                    url=DIVIDER_URL
                ),
            ],
            file=file,
            view=view,
        )


# ============================================================
# SEARCH BUTTON
# ============================================================

class SearchButton(
    discord.ui.Button
):

    def __init__(
        self,
        parent_view,
    ):
        self.parent_view = parent_view

        super().__init__(
            label="Search",
            emoji="🔎",
            style=discord.ButtonStyle.secondary,
            row=3,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.send_modal(
            CollectionSearchModal(
                self.parent_view
            )
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(
        Collection(bot)
    )
