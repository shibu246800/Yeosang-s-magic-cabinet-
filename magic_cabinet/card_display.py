"""Utilities for displaying multiple Magic Cabinet cards."""

from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw


CARD_WIDTH = 400
CARD_HEIGHT = 560
CARD_GAP = 18

BACKGROUND = (18, 15, 24)
BORDER = (105, 86, 120)


async def create_card_strip(cards: list[dict]) -> BytesIO:
    """Download three card images and create a decorative card strip."""

    images = []

    async with aiohttp.ClientSession() as session:
        for card in cards:
            async with session.get(card["image"]) as response:
                response.raise_for_status()

                image_data = await response.read()

            image = Image.open(BytesIO(image_data)).convert("RGB")

            image.thumbnail(
                (CARD_WIDTH - 12, CARD_HEIGHT - 12)
            )

            canvas = Image.new(
                "RGB",
                (CARD_WIDTH, CARD_HEIGHT),
                BACKGROUND,
            )

            x = (CARD_WIDTH - image.width) // 2
            y = (CARD_HEIGHT - image.height) // 2

            canvas.paste(image, (x, y))

            draw = ImageDraw.Draw(canvas)

            draw.rectangle(
                (2, 2, CARD_WIDTH - 3, CARD_HEIGHT - 3),
                outline=BORDER,
                width=3,
            )

            images.append(canvas)

    total_width = (
        CARD_WIDTH * len(images)
        + CARD_GAP * (len(images) - 1)
    )

    strip = Image.new(
        "RGB",
        (total_width, CARD_HEIGHT),
        BACKGROUND,
    )

    x = 0

    for image in images:
        strip.paste(image, (x, 0))
        x += CARD_WIDTH + CARD_GAP

    output = BytesIO()

    strip.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)

    return output
