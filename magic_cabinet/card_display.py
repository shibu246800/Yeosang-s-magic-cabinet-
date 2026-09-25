"""Utilities for displaying multiple Magic Cabinet cards."""

from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw


# Actual card size
CARD_WIDTH = 450
CARD_HEIGHT = 630

# Slightly larger white template around each card
TEMPLATE_WIDTH = 480
TEMPLATE_HEIGHT = 660

# Wide, clean space between cards
CARD_GAP = 70

# Plain white template
BACKGROUND = (255, 255, 255)

# Metallic-gold decoration
GOLD = (212, 175, 55)
LIGHT_GOLD = (238, 220, 160)


async def create_card_strip(cards: list[dict]) -> BytesIO:
    """Download cards and create a clean card display."""

    images = []

    async with aiohttp.ClientSession() as session:
        for card in cards:
            async with session.get(card["image"]) as response:
                response.raise_for_status()
                image_data = await response.read()

            image = Image.open(
                BytesIO(image_data)
            ).convert("RGB")

            # Keep the original card proportions.
            image.thumbnail(
                (CARD_WIDTH, CARD_HEIGHT)
            )

            # Slightly larger template behind the card.
            canvas = Image.new(
                "RGB",
                (
                    TEMPLATE_WIDTH,
                    TEMPLATE_HEIGHT,
                ),
                BACKGROUND,
            )

            x = (
                TEMPLATE_WIDTH - image.width
            ) // 2

            y = (
                TEMPLATE_HEIGHT - image.height
            ) // 2

            canvas.paste(
                image,
                (x, y),
            )

            images.append(canvas)

    total_width = (
        TEMPLATE_WIDTH * len(images)
        + CARD_GAP * (len(images) - 1)
    )

    strip = Image.new(
        "RGB",
        (
            total_width,
            TEMPLATE_HEIGHT,
        ),
        BACKGROUND,
    )

    draw = ImageDraw.Draw(strip)

    x = 0

    for index, image in enumerate(images):
        strip.paste(
            image,
            (x, 0),
        )

        if index < len(images) - 1:
            ornament_x = (
                x
                + TEMPLATE_WIDTH
                + CARD_GAP // 2
            )

            ornament_y = TEMPLATE_HEIGHT // 2

            # Tiny side dots.
            draw.ellipse(
                (
                    ornament_x - 14,
                    ornament_y - 2,
                    ornament_x - 10,
                    ornament_y + 2,
                ),
                fill=LIGHT_GOLD,
            )

            draw.ellipse(
                (
                    ornament_x + 10,
                    ornament_y - 2,
                    ornament_x + 14,
                    ornament_y + 2,
                ),
                fill=LIGHT_GOLD,
            )

            # Elegant four-point star.
            draw.polygon(
                [
                    (
                        ornament_x,
                        ornament_y - 11,
                    ),
                    (
                        ornament_x + 4,
                        ornament_y - 4,
                    ),
                    (
                        ornament_x + 11,
                        ornament_y,
                    ),
                    (
                        ornament_x + 4,
                        ornament_y + 4,
                    ),
                    (
                        ornament_x,
                        ornament_y + 11,
                    ),
                    (
                        ornament_x - 4,
                        ornament_y + 4,
                    ),
                    (
                        ornament_x - 11,
                        ornament_y,
                    ),
                    (
                        ornament_x - 4,
                        ornament_y - 4,
                    ),
                ],
                fill=GOLD,
            )

        x += (
            TEMPLATE_WIDTH
            + CARD_GAP
        )

    output = BytesIO()

    strip.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)

    return output
