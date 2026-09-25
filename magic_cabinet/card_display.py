"""Utilities for displaying multiple Magic Cabinet cards."""

from io import BytesIO

import aiohttp
from PIL import Image


CARD_WIDTH = 400
CARD_HEIGHT = 560
CARD_GAP = 20


async def create_card_strip(cards: list[dict]) -> BytesIO:
    """Download three card images and combine them horizontally."""

    images = []

    async with aiohttp.ClientSession() as session:
        for card in cards:
            async with session.get(card["image"]) as response:
                response.raise_for_status()

                image_data = await response.read()

            image = Image.open(BytesIO(image_data)).convert("RGB")
            image.thumbnail((CARD_WIDTH, CARD_HEIGHT))

            canvas = Image.new(
                "RGB",
                (CARD_WIDTH, CARD_HEIGHT),
                "white",
            )

            x = (CARD_WIDTH - image.width) // 2
            y = (CARD_HEIGHT - image.height) // 2

            canvas.paste(image, (x, y))
            images.append(canvas)

    total_width = (
        CARD_WIDTH * len(images)
        + CARD_GAP * (len(images) - 1)
    )

    strip = Image.new(
        "RGB",
        (total_width, CARD_HEIGHT),
        "white",
    )

    x = 0

    for image in images:
        strip.paste(image, (x, 0))
        x += CARD_WIDTH + CARD_GAP

    output = BytesIO()
    strip.save(output, format="PNG")
    output.seek(0)

    return output
