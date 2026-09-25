"""Utilities for displaying multiple Magic Cabinet cards."""

from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw


CARD_WIDTH = 400
CARD_HEIGHT = 560

# Wider, airy space between cards
CARD_GAP = 55

# Very light white / pearl-white gap
BACKGROUND = (252, 252, 250)

# Gold decoration
GOLD = (212, 175, 55)
LIGHT_GOLD = (238, 220, 160)


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
                (CARD_WIDTH - 16, CARD_HEIGHT - 16)
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

            # Thin elegant gold frame
            draw.rectangle(
                (2, 2, CARD_WIDTH - 3, CARD_HEIGHT - 3),
                outline=GOLD,
                width=4,
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

    for index, image in enumerate(images):
        strip.paste(image, (x, 0))

        # Decorative typographical ornament
        if index < len(images) - 1:
            ornament_x = (
                x
                + CARD_WIDTH
                + CARD_GAP // 2
            )

            ornament_y = CARD_HEIGHT // 2

            draw = ImageDraw.Draw(strip)

            # Small surrounding dots
            draw.ellipse(
                (
                    ornament_x - 13,
                    ornament_y - 2,
                    ornament_x - 9,
                    ornament_y + 2,
                ),
                fill=LIGHT_GOLD,
            )

            draw.ellipse(
                (
                    ornament_x + 9,
                    ornament_y - 2,
                    ornament_x + 13,
                    ornament_y + 2,
                ),
                fill=LIGHT_GOLD,
            )

            # Four-point star
            draw.polygon(
                [
                    (ornament_x, ornament_y - 10),
                    (ornament_x + 4, ornament_y - 3),
                    (ornament_x + 10, ornament_y),
                    (ornament_x + 4, ornament_y + 3),
                    (ornament_x, ornament_y + 10),
                    (ornament_x - 4, ornament_y + 3),
                    (ornament_x - 10, ornament_y),
                    (ornament_x - 4, ornament_y - 3),
                ],
                fill=GOLD,
            )

        x += CARD_WIDTH + CARD_GAP

    # Elegant outer frame
    draw = ImageDraw.Draw(strip)

    draw.rectangle(
        (0, 0, total_width - 1, CARD_HEIGHT - 1),
        outline=GOLD,
        width=6,
    )

    # Tiny corner sparkles
    sparkle_positions = [
        (18, 18),
        (total_width - 18, 18),
        (18, CARD_HEIGHT - 18),
        (total_width - 18, CARD_HEIGHT - 18),
    ]

    for sparkle_x, sparkle_y in sparkle_positions:
        draw.line(
            (
                sparkle_x - 5,
                sparkle_y,
                sparkle_x + 5,
                sparkle_y,
            ),
            fill=LIGHT_GOLD,
            width=2,
        )

        draw.line(
            (
                sparkle_x,
                sparkle_y - 5,
                sparkle_x,
                sparkle_y + 5,
            ),
            fill=LIGHT_GOLD,
            width=2,
        )

    output = BytesIO()

    strip.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)

    return output
