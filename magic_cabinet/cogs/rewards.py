"""Magic Cabinet reward center."""

import asyncio
import random
from io import BytesIO

import aiohttp
import discord
import psycopg
from PIL import Image, ImageDraw
from discord import app_commands
from discord.ext import commands

from magic_cabinet.postgres_database import (
get_postgres_connection,
initialize_postgres_database,
)
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS

EMBED_COLOR = discord.Color.from_str("#4E0017")
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"
MAGIC_EMOTE = "<a:magic:1556011520012460135>"

WEEKLY_GRAND_GLIMMERS = 25_000

BLIND_BOX_FRAMES = [
"https://raw.githubusercontent.com/shibu246800/Yeosang-s-magic-cabinet-/refs/heads/main/magic_cabinet/cogs/profile/Untitled18_20261005113854.png",
"https://raw.githubusercontent.com/shibu246800/Yeosang-s-magic-cabinet-/refs/heads/main/magic_cabinet/cogs/profile/Untitled18_20261005113858.png",
"https://raw.githubusercontent.com/shibu246800/Yeosang-s-magic-cabinet-/refs/heads/main/magic_cabinet/cogs/profile/Untitled18_20261005113858.png",
"https://raw.githubusercontent.com/shibu246800/Yeosang-s-magic-cabinet-/refs/heads/main/magic_cabinet/cogs/profile/Untitled18_20261005113908.png",
]

CARD_WIDTH = 450
CARD_HEIGHT = 630
TEMPLATE_WIDTH = 480
TEMPLATE_HEIGHT = 660
CARD_GAP = 70
ROW_GAP = 35
BACKGROUND = (0, 0, 0, 0)
GOLD = (212, 175, 55, 255)
LIGHT_GOLD = (238, 220, 160, 255)

def initialize_rewards_database():
initialize_postgres_database()

with get_postgres_connection() as connection:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS blind_boxes (
            user_id BIGINT PRIMARY KEY,
            quantity INTEGER NOT NULL DEFAULT 0
        )
        """
    )

def get_pending_rewards(user_id: int):
with get_postgres_connection() as connection:
return connection.execute(
"""
SELECT reward_id, reward_type, amount, task_id
FROM weekly_pending_rewards
WHERE user_id = %s AND claimed = 0
ORDER BY reward_id ASC
""",
(user_id,),
).fetchall()

def get_blind_box_count(user_id: int) -> int:
with get_postgres_connection() as connection:
row = connection.execute(
"SELECT quantity FROM blind_boxes WHERE user_id = %s",
(user_id,),
).fetchone()

return row["quantity"] if row else 0

def add_blind_boxes(user_id: int, amount: int):
with get_postgres_connection() as connection:
connection.execute(
"""
INSERT INTO blind_boxes (user_id, quantity)
VALUES (%s, %s)
ON CONFLICT(user_id)
DO UPDATE SET quantity = blind_boxes.quantity + EXCLUDED.quantity
""",
(user_id, amount),
)

def remove_blind_box(user_id: int) -> bool:
with get_postgres_connection() as connection:
cursor = connection.execute(
"""
UPDATE blind_boxes
SET quantity = quantity - 1
WHERE user_id = %s AND quantity > 0
""",
(user_id,),
)
return cursor.rowcount > 0

def get_bag_quantity(user_id: int, card_id: int) -> int:
with get_postgres_connection() as connection:
row = connection.execute(
"""
SELECT quantity FROM bag
WHERE user_id = %s AND card_id = %s
""",
(user_id, card_id),
).fetchone()

return row["quantity"] if row else 0

def add_to_bag(user_id: int, card_id: int):
with get_postgres_connection() as connection:
connection.execute(
"""
INSERT INTO bag (user_id, card_id, quantity)
VALUES (%s, %s, 1)
ON CONFLICT(user_id, card_id)
DO UPDATE SET quantity = bag.quantity + 1
""",
(user_id, card_id),
)

    row = connection.execute(
        """
        SELECT quantity FROM bag
        WHERE user_id = %s AND card_id = %s
        """,
        (user_id, card_id),
    ).fetchone()

return row["quantity"], row["quantity"] == 1

def add_glimmers(user_id: int, amount: int):
with get_postgres_connection() as connection:
connection.execute(
"""
INSERT INTO balances (user_id, glimmers)
VALUES (%s, %s)
ON CONFLICT(user_id)
DO UPDATE SET glimmers = balances.glimmers + EXCLUDED.glimmers
""",
(user_id, amount),
)

def choose_new_epic(user_id: int):
available = [
card for card in EPIC_CARDS
if get_bag_quantity(user_id, int(card["id"])) == 0
]
return random.choice(available) if available else None

def choose_blind_box_cards():
return random.choices(RARE_CARDS + EPIC_CARDS, k=5)

def draw_ornament(draw: ImageDraw.ImageDraw, x: int, y: int):
draw.ellipse((x - 14, y - 2, x - 10, y + 2), fill=LIGHT_GOLD)
draw.ellipse((x + 10, y - 2, x + 14, y + 2), fill=LIGHT_GOLD)
draw.polygon(
[
(x, y - 11), (x + 4, y - 4), (x + 11, y),
(x + 4, y + 4), (x, y + 11), (x - 4, y + 4),
(x - 11, y), (x - 4, y - 4),
],
fill=GOLD,
)

async def create_blind_box_display(cards: list[dict]) -> BytesIO:
images = []

async with aiohttp.ClientSession() as session:
    for card in cards:
        async with session.get(card["image"]) as response:
            response.raise_for_status()
            image_data = await response.read()

        image = Image.open(BytesIO(image_data)).convert("RGBA")
        image.thumbnail((CARD_WIDTH, CARD_HEIGHT))

        canvas = Image.new("RGBA", (TEMPLATE_WIDTH, TEMPLATE_HEIGHT), BACKGROUND)
        x = (TEMPLATE_WIDTH - image.width) // 2
        y = (TEMPLATE_HEIGHT - image.height) // 2
        canvas.paste(image, (x, y), image)
        images.append(canvas)

top_width = TEMPLATE_WIDTH * 3 + CARD_GAP * 2
total_height = TEMPLATE_HEIGHT * 2 + ROW_GAP
display = Image.new("RGBA", (top_width, total_height), BACKGROUND)
draw = ImageDraw.Draw(display)

for index in range(3):
    x = index * (TEMPLATE_WIDTH + CARD_GAP)
    display.alpha_composite(images[index], (x, 0))
    if index < 2:
        draw_ornament(draw, x + TEMPLATE_WIDTH + CARD_GAP // 2, TEMPLATE_HEIGHT // 2)

bottom_width = TEMPLATE_WIDTH * 2 + CARD_GAP
bottom_start = (top_width - bottom_width) // 2

for index in range(2):
    x = bottom_start + index * (TEMPLATE_WIDTH + CARD_GAP)
    display.alpha_composite(images[index + 3], (x, TEMPLATE_HEIGHT + ROW_GAP))
    if index == 0:
        draw_ornament(
            draw,
            x + TEMPLATE_WIDTH + CARD_GAP // 2,
            TEMPLATE_HEIGHT + ROW_GAP + TEMPLATE_HEIGHT // 2,
        )

output = BytesIO()
display.save(output, format="PNG", optimize=True)
output.seek(0)
return output

def claim_rewards(user_id: int):
with get_postgres_connection() as connection:
with connection.transaction():
pending = connection.execute(
"""
SELECT reward_id, reward_type, amount, task_id
FROM weekly_pending_rewards
WHERE user_id = %s AND claimed = 0
ORDER BY reward_id ASC
FOR UPDATE
""",
(user_id,),
).fetchall()

        if not pending:
            return None

        task_glimmers = sum(
            reward["amount"]
            for reward in pending
            if reward["reward_type"] == "task_glimmers"
        )
        has_grand = any(
            reward["reward_type"] == "weekly_grand"
            for reward in pending
        )

        epic_card = choose_new_epic(user_id) if has_grand else None
        total_glimmers = task_glimmers + (
            WEEKLY_GRAND_GLIMMERS if has_grand else 0
        )

        if total_glimmers:
            connection.execute(
                """
                INSERT INTO balances (user_id, glimmers)
                VALUES (%s, %s)
                ON CONFLICT(user_id)
                DO UPDATE SET glimmers = balances.glimmers + EXCLUDED.glimmers
                """,
                (user_id, total_glimmers),
            )

        if epic_card is not None:
            connection.execute(
                """
                INSERT INTO bag (user_id, card_id, quantity)
                VALUES (%s, %s, 1)
                ON CONFLICT(user_id, card_id)
                DO UPDATE SET quantity = bag.quantity + 1
                """,
                (user_id, int(epic_card["id"])),
            )

        if has_grand:
            connection.execute(
                """
                INSERT INTO blind_boxes (user_id, quantity)
                VALUES (%s, 1)
                ON CONFLICT(user_id)
                DO UPDATE SET quantity = blind_boxes.quantity + 1
                """,
                (user_id,),
            )

        connection.execute(
            """
            UPDATE weekly_pending_rewards
            SET claimed = 1
            WHERE user_id = %s AND claimed = 0
            """,
            (user_id,),
        )

return {
    "task_glimmers": task_glimmers,
    "grand_glimmers": WEEKLY_GRAND_GLIMMERS if has_grand else 0,
    "total_glimmers": total_glimmers,
    "epic": epic_card,
    "blind_boxes": 1 if has_grand else 0,
}

def build_reward_embed(user: discord.User | discord.Member, pending):
task_total = sum(
reward["amount"] for reward in pending
if reward["reward_type"] == "task_glimmers"
)
has_grand = any(
reward["reward_type"] == "weekly_grand" for reward in pending
)

lines = [
    f"**{user.mention}**", "",
    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦", "",
    "**REWARDS WAITING**", "",
]

if task_total:
    lines.append(f"+ **{task_total:,}** {GLIMMER_EMOTE}")

if has_grand:
    lines.extend([
        "", "**Weekly Grand Reward**",
        f"+ **{WEEKLY_GRAND_GLIMMERS:,}** {GLIMMER_EMOTE}",
        "+ **1 NEW Epic card**", "+ **1 Blind Box**",
    ])

lines.extend([
    "", "✦ ───── ⋆⋅☆⋅⋆ ───── ✦", "",
    "-# ✧ Claim everything waiting for you.",
])

return discord.Embed(description="\n".join(lines), color=EMBED_COLOR)

class RewardsView(discord.ui.View):
def init(self, user_id: int):
super().init(timeout=120)
self.user_id = user_id

@discord.ui.button(label="Claim", emoji="⬇️", style=discord.ButtonStyle.danger)
async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.user.id != self.user_id:
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ These rewards belong to another player.",
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )
        return

    result = claim_rewards(interaction.user.id)

    if result is None:
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ You have no rewards waiting.",
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )
        return

    lines = [
        f"**{interaction.user.mention}**", "",
        "✦ ───── ⋆⋅☆⋅⋆ ───── ✦", "",
        "**REWARDS CLAIMED!** ✦", "",
    ]

    if result["task_glimmers"]:
        lines.append(f"+ **{result['task_glimmers']:,}** {GLIMMER_EMOTE}")
    if result["grand_glimmers"]:
        lines.append(f"+ **{result['grand_glimmers']:,}** {GLIMMER_EMOTE}")
    if result["epic"]:
        lines.append(f"+ **{result['epic']['id']}** `NEW Epic card`")
    if result["blind_boxes"]:
        lines.append("+ **1 Blind Box** 📦")

    lines.extend(["", "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"])
    button.disabled = True

    await interaction.response.edit_message(
        embed=discord.Embed(description="\n".join(lines), color=EMBED_COLOR),
        view=self,
    )

class BlindBoxView(discord.ui.View):
def init(self, user_id: int, cards: list[dict]):
super().init(timeout=120)
self.user_id = user_id
self.cards = cards
self.claimed = False

@discord.ui.button(label="Claim", emoji=MAGIC_EMOTE, style=discord.ButtonStyle.danger)
async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.user.id != self.user_id:
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ This Blind Box belongs to another player.",
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )
        return

    if self.claimed:
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ This Blind Box has already been claimed.",
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )
        return

    self.claimed = True

    with get_postgres_connection() as connection:
        with connection.transaction():
            for card in self.cards:
                connection.execute(
                    """
                    INSERT INTO bag (user_id, card_id, quantity)
                    VALUES (%s, %s, 1)
                    ON CONFLICT(user_id, card_id)
                    DO UPDATE SET quantity = bag.quantity + 1
                    """,
                    (self.user_id, int(card["id"])),
                )

    button.disabled = True
    await interaction.response.edit_message(attachments=[], embeds=[], view=self)
    await interaction.followup.send(
        embed=discord.Embed(
            description="✦ Your 5 Blind Box cards have been added to your Bag.",
            color=EMBED_COLOR,
        ),
        ephemeral=True,
    )

class Rewards(commands.Cog):
def init(self, bot: commands.Bot):
self.bot = bot
initialize_rewards_database()

@app_commands.command(name="rewards", description="View and claim your waiting rewards.")
async def rewards(self, interaction: discord.Interaction):
    pending = get_pending_rewards(interaction.user.id)

    if not pending:
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ You have no rewards waiting right now.",
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        embed=build_reward_embed(interaction.user, pending),
        view=RewardsView(interaction.user.id),
    )

@app_commands.command(name="blindbox", description="Open a Blind Box.")
async def blindbox(self, interaction: discord.Interaction):
    if get_blind_box_count(interaction.user.id) <= 0:
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ You don't have a Blind Box.",
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )
        return

    if not remove_blind_box(interaction.user.id):
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ You don't have a Blind Box.",
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )
        return

    cards = choose_blind_box_cards()
    view = BlindBoxView(interaction.user.id, cards)

    await interaction.response.send_message(
        embed=discord.Embed().set_image(url=BLIND_BOX_FRAMES[0]),
    )
    await asyncio.sleep(5)
    await interaction.edit_original_response(
        embed=discord.Embed().set_image(url=BLIND_BOX_FRAMES[1]),
    )
    await asyncio.sleep(5)
    await interaction.edit_original_response(
        embed=discord.Embed().set_image(url=BLIND_BOX_FRAMES[2]),
    )
    await asyncio.sleep(5)
    await interaction.edit_original_response(
        embed=discord.Embed().set_image(url=BLIND_BOX_FRAMES[3]),
    )
    await asyncio.sleep(5)

    image = await create_blind_box_display(cards)

    await interaction.edit_original_response(
        embed=discord.Embed(color=EMBED_COLOR).set_image(
            url="attachment://blind_box_cards.png"
        ),
        attachments=[discord.File(image, filename="blind_box_cards.png")],
        view=view,
    )

async def setup(bot: commands.Bot):
initialize_rewards_database()
await bot.add_cog(Rewards(bot))
