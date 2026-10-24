
"""Drop command."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.card_display import create_card_strip
from magic_cabinet.data.collections import COLLECTIONS
from magic_cabinet.data.drop_rates import DROP_RATES
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS
from magic_cabinet.database import get_connection, initialize_database
from magic_cabinet.weekly_tracker import record_weekly_progress


DROP_CARD_COUNT = 3
DROP_DURATION = 20

OWNER_EMOTE = "<:owner_bag:1552939106731032646>"
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

CABINET_COLOR = discord.Color.from_str("#4E0017")
DROP_OWNER_REWARD = 30

POSITION_EMOTES = {
    1: "<:emoji_16:1555890252118368336>",
    2: "<:emoji_17:1555890288667402241>",
    3: "<:emoji_18:1555890318057013248>",
}

RARITY_REWARDS = {
    "★": 50,
    "★★": 80,
    "★★★": 120,
    "★★★★": 180,
}

RARITY_CARDS = {
    "★": NORMAL_CARDS,
    "★★": RARE_CARDS,
    "★★★": EPIC_CARDS,
    "★★★★": LIMITED_CARDS,
}

RARITY_EMOTES = {
    "★": "<:silver_normal:1552761791606689933>",
    "★★": "<:sapphire_rare:1552761835587899513>",
    "★★★": "<:eclipse_epic:1552761873076850758>",
    "★★★★": "<:bloodrose_limited:1552761891472810144>",
    "★★★★★": "<:golden_legendary:1552761908652671056>",
}

VAULT_SERIES = {
    "BB": "Velvet Moon",
    "GG": "Roseglass",
    "BG": "Golden Thread",
}


def initialize_bag_database():
    initialize_database()


def choose_rarity() -> str:
    return random.choices(
        list(DROP_RATES.keys()),
        weights=list(DROP_RATES.values()),
        k=1,
    )[0]


def choose_drop_cards() -> list[dict]:
    all_cards = [
        card
        for cards in RARITY_CARDS.values()
        for card in cards
    ]

    if len(all_cards) < DROP_CARD_COUNT:
        raise RuntimeError("There are not enough cards for this drop.")

    selected_cards = []
    available_cards = all_cards.copy()

    for _ in range(DROP_CARD_COUNT):
        selected_rarity = choose_rarity()
        rarity_cards = [
            card for card in available_cards
            if card["stars"] == selected_rarity
        ]

        selected_card = (
            random.choice(rarity_cards)
            if rarity_cards else random.choice(available_cards)
        )
        selected_cards.append(selected_card)
        available_cards.remove(selected_card)

    return selected_cards


def get_collection(collection_id: str) -> dict:
    return COLLECTIONS.get(
        collection_id,
        {"name": "Unknown Collection", "vault": "BB"},
    )


def get_collection_name(collection_id: str) -> str:
    return get_collection(collection_id).get("name", "Unknown Collection")


def get_series(collection_id: str) -> str:
    collection = get_collection(collection_id)

    if collection.get("series"):
        return collection["series"]

    vault = collection.get("vault", collection_id.split("_")[0])
    return VAULT_SERIES.get(vault, "Unknown Series")


def get_card_name(card: dict) -> str:
    return card.get("name", f"Card {card['id']}")


def get_card_image(card: dict) -> str:
    return card.get("image", "")


def get_card_vault(card: dict) -> str:
    collection_id = card["collection_id"]
    collection = get_collection(collection_id)
    return collection.get("vault", collection_id.split("_")[0])


def get_rarity_reward(card: dict) -> int:
    return RARITY_REWARDS.get(card["stars"], 0)


def get_bag_quantity(user_id: int, card_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT quantity FROM bag
            WHERE user_id = ? AND card_id = ?
            """,
            (user_id, card_id),
        ).fetchone()

    return row["quantity"] if row else 0


def add_to_bag(user_id: int, card_id: int) -> tuple[int, bool]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT quantity FROM bag
            WHERE user_id = ? AND card_id = ?
            """,
            (user_id, card_id),
        ).fetchone()

        if row is None:
            connection.execute(
                """
                INSERT INTO bag (user_id, card_id, quantity)
                VALUES (?, ?, 1)
                """,
                (user_id, card_id),
            )
            return 1, True

        new_quantity = row["quantity"] + 1
        connection.execute(
            """
            UPDATE bag SET quantity = ?
            WHERE user_id = ? AND card_id = ?
            """,
            (new_quantity, user_id, card_id),
        )

        return new_quantity, False


def add_glimmers(user_id: int, amount: int):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO balances (user_id, glimmers)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET glimmers = balances.glimmers + excluded.glimmers
            """,
            (user_id, amount),
        )


def get_player_vaults(user_id: int) -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT vault FROM player_vaults
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    return [
        row["vault"] for row in rows
        if row["vault"] in {"BB", "GG", "BG"}
    ]


def get_saved_drop_channels(guild_id: int) -> list[int]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT channel1_id, channel2_id, channel3_id,
                   channel4_id, channel5_id
            FROM drop_channels
            WHERE guild_id = ?
            """,
            (guild_id,),
        ).fetchone()

    if row is None:
        return []

    return [
        row[f"channel{number}_id"]
        for number in range(1, 6)
        if row[f"channel{number}_id"] is not None
    ]


def format_card(card: dict, owner_id: int, position: int) -> str:
    rarity_emote = RARITY_EMOTES[card["stars"]]
    position_emote = POSITION_EMOTES[position]
    collection_id = card["collection_id"]
    collection = get_collection(collection_id)

    vault = collection.get("vault", collection_id.split("_")[0])
    collection_name = collection.get("name", "Unknown Collection")
    owner_has_card = get_bag_quantity(owner_id, card["id"]) > 0
    owner_marker = f"{OWNER_EMOTE} " if owner_has_card else ""

    return (
        f"{owner_marker}{rarity_emote} ❖ {position_emote} "
        f"`{vault}` • **{collection_name}**"
    )


class CardButton(discord.ui.Button):

    def __init__(
        self,
        card: dict,
        number: int,
        owner_id: int,
        view: "CardDropView",
    ):
        self.card = card
        self.number = number
        self.owner_id = owner_id
        self.card_view = view
        self.claimant: discord.Member | discord.User | None = None

        super().__init__(
            label="0",
            emoji=discord.PartialEmoji.from_str(
                RARITY_EMOTES[card["stars"]]
            ),
            style=discord.ButtonStyle.secondary,
            custom_id=f"cabinet_card_{card['id']}_{number}",
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.card_view
        user_id = interaction.user.id

        async with view.claim_lock:
            if view.expired:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="✦ This drop has already ended.",
                        color=CABINET_COLOR,
                    ),
                    ephemeral=True,
                )
                return

            selected_vaults = get_player_vaults(user_id)
            if not selected_vaults:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=(
                            "🔒 Your Cabinet Vaults are not set yet.\n\n"
                            "Use `/magic awaken` to choose your Vaults first."
                        ),
                        color=CABINET_COLOR,
                    ),
                    ephemeral=True,
                )
                return

            card_vault = get_card_vault(self.card)
            if card_vault not in selected_vaults:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=(
                            f"🔒 This card belongs to the **{card_vault} Vault**.\n\n"
                            "You haven't selected this Vault, so you cannot claim this card.\n\n"
                            "Your selected Vaults:\n"
                            + "\n".join(
                                f"➤ **{vault}**"
                                for vault in selected_vaults
                            )
                        ),
                        color=CABINET_COLOR,
                    ),
                    ephemeral=True,
                )
                return

            is_owner = user_id == view.owner_id
            previous_choice = view.player_choices.get(user_id)

            if not is_owner:
                if previous_choice is not None:
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            description=(
                                "✦ You have already claimed a card from this drop.\n\n"
                                "Only one card may be claimed per player in each drop."
                            ),
                            color=CABINET_COLOR,
                        ),
                        ephemeral=True,
                    )
                    return

                if self.claimant is not None:
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            description="✦ This card has already been claimed.",
                            color=CABINET_COLOR,
                        ),
                        ephemeral=True,
                    )
                    return

                self.claimant = interaction.user
                view.player_choices[user_id] = self.number

            else:
                if previous_choice == self.number:
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            description=(
                                f"{OWNER_EMOTE} You are already claiming this card."
                            ),
                            color=CABINET_COLOR,
                        ),
                        ephemeral=True,
                    )
                    return

                if previous_choice is not None:
                    previous_button = view.get_button(previous_choice)
                    if previous_button is not None:
                        if (
                            previous_button.claimant
                            and previous_button.claimant.id == user_id
                        ):
                            previous_button.claimant = None
                            previous_button.label = "0"

                if (
                    self.claimant is not None
                    and self.claimant.id != user_id
                ):
                    previous_claimant = self.claimant
                    if (
                        view.player_choices.get(previous_claimant.id)
                        == self.number
                    ):
                        del view.player_choices[previous_claimant.id]

                self.claimant = interaction.user
                view.player_choices[user_id] = self.number

            self.label = "1" if self.claimant else "0"

        await interaction.response.defer(ephemeral=True)
        await view.update_buttons()


class CardDropView(discord.ui.View):

    def __init__(self, cards: list[dict], owner_id: int):
        super().__init__(timeout=DROP_DURATION)
        self.cards = cards
        self.owner_id = owner_id
        self.player_choices: dict[int, int] = {}
        self.expired = False
        self.message: discord.Message | None = None
        self.claim_lock = asyncio.Lock()

        for number, card in enumerate(cards, start=1):
            self.add_item(CardButton(card, number, owner_id, self))

    def get_button(self, number: int) -> CardButton | None:
        for item in self.children:
            if isinstance(item, CardButton) and item.number == number:
                return item
        return None

    async def update_buttons(self):
        if self.message is None:
            return

        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

    async def on_timeout(self):
        async with self.claim_lock:
            self.expired = True
            for item in self.children:
                if isinstance(item, CardButton):
                    item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

            await self.send_results()

    async def send_results(self):
        if self.message is None:
            return

        result_lines = []

        for item in self.children:
            if not isinstance(item, CardButton):
                continue

            card = item.card
            card_number = item.number
            image_url = get_card_image(card)
            rarity = card["stars"]
            rarity_reward = get_rarity_reward(card)
            collection_id = card["collection_id"]
            collection = get_collection(collection_id)
            vault = collection.get(
                "vault",
                collection_id.split("_")[0],
            )
            collection_name = collection.get(
                "name",
                "Unknown Collection",
            )
            series_name = get_series(collection_id)
            position_emote = POSITION_EMOTES[card_number]

            if item.claimant is None:
                result_lines.append(
                    f"**{position_emote}**\n"
                    f"No selections\n"
                    f"-# ☆ Card ID: `{card['id']}` ☆ Collection ID: "
                    f"`{collection_id}` ({collection_name}) ☆ "
                    f"Series: {series_name} ({vault})"
                )
                continue

            claimant = item.claimant
            quantity, was_new = add_to_bag(
                claimant.id,
                card["id"],
            )
            add_glimmers(claimant.id, rarity_reward)

            record_weekly_progress(
                claimant.id,
                "drops_claimed",
                1,
            )
            if was_new:
                record_weekly_progress(
                    claimant.id,
                    "new_cards",
                    1,
                )

            status = (
                "You got a new card!"
                if was_new
                else (
                    f"You now have **{quantity}** copies!\n"
                    "You got a dupie! You can either: `/sell` or `/merge`"
                )
            )

            total_reward = rarity_reward
            if claimant.id == self.owner_id:
                add_glimmers(claimant.id, DROP_OWNER_REWARD)
                total_reward += DROP_OWNER_REWARD
                reward_text = (
                    f"-# {rarity} 》 {rarity_reward} + {DROP_OWNER_REWARD} "
                    f"(drop rewards) = {total_reward} {GLIMMER_EMOTE} "
                    "are added to your purse!"
                )
            else:
                reward_text = (
                    f"-# {rarity} 》 {rarity_reward} {GLIMMER_EMOTE} "
                    "of glimmers are added to your purse!"
                )

            view_line = (
                f"[View]({image_url}) {claimant.mention}"
                if image_url
                else claimant.mention
            )

            result_lines.append(
                f"**{position_emote}**\n{view_line}\n"
                f"-# ☆ Card ID: `{card['id']}` ☆ Collection ID: "
                f"`{collection_id}` ({collection_name}) ☆ "
                f"Series: {series_name} ({vault})\n\n"
                f"{status}\n\n{reward_text}"
            )

        result_text = (
            "╭────────────── ✦ ──────────────╮\n"
            "           ✨ CONGRATS! The results are in.\n"
            "╰────────────── ✦ ──────────────╯\n\n"
            + "\n╰─────── ⋆⋅☆⋅⋆ ───────╯\n".join(result_lines)
            + "\n╰─────── ⋆⋅☆⋅⋆ ───────╯"
        )

        await self.message.reply(
            embed=discord.Embed(
                description=result_text,
                color=CABINET_COLOR,
            )
        )


class Drop(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_bag_database()

    @app_commands.command(
        name="drop",
        description="Drop three cards from the Magic Cabinet.",
    )
    async def drop(self, interaction: discord.Interaction):
        cabinet = self.bot.get_cog("cabinet")

        if cabinet is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "The Magic Cabinet setup is currently unavailable."
                    ),
                    color=CABINET_COLOR,
                )
            )
            return

        if interaction.guild_id is None or interaction.guild is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "This command can only be used inside a server."
                    ),
                    color=CABINET_COLOR,
                )
            )
            return

        allowed = cabinet.is_drop_channel(
            interaction.guild_id,
            interaction.channel_id,
        )

        if not allowed:
            channel_mentions = []

            for channel_id in get_saved_drop_channels(
                interaction.guild_id
            ):
                channel = interaction.guild.get_channel(channel_id)
                if channel is not None:
                    channel_mentions.append(channel.mention)

            channel_text = (
                " • ".join(channel_mentions)
                if channel_mentions
                else "No configured Drop channels."
            )

            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "This command can only be used in a configured Drop channel.\n\n"
                        f"➷ {channel_text}"
                    ),
                    color=CABINET_COLOR,
                )
            )
            return

        if not get_player_vaults(interaction.user.id):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "🔒 This vault remains sealed.\n"
                        "You haven't chosen a Vault yet.\n\n"
                        "Use `/magic awaken` to begin your Cabinet journey."
                    ),
                    color=CABINET_COLOR,
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        cards = choose_drop_cards()

        card_information = "\n\n".join(
            format_card(
                card,
                interaction.user.id,
                position,
            )
            for position, card in enumerate(cards, start=1)
        )

        card_strip = await create_card_strip(cards)
        file = discord.File(
            card_strip,
            filename="cabinet_drop.png",
        )

        embed = discord.Embed(
            description=(
                "╭─ ⋆⋅☆⋅⋆ ─╮\n"
                "**This drop is active for 20 seconds.**\n"
                "Unlimited players may participate, but the "
                "drop owner's authority stays put.\n"
                "╰─ ⋆⋅☆⋅⋆ ─╯\n\n"
                "-# ✦ Select a card before the 20 seconds end.\n"
                f"-# {OWNER_EMOTE} = already exist in the drop owner's Bag\n\n"
                f"{card_information}"
            ),
            color=CABINET_COLOR,
        )
        embed.set_image(url="attachment://cabinet_drop.png")

        view = CardDropView(cards, interaction.user.id)
        message = await interaction.followup.send(
            content=(
                f"**Oh {interaction.user.mention} is dropping! Attention!**"
            ),
            embed=embed,
            file=file,
            view=view,
            wait=True,
        )
        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(Drop(bot))
