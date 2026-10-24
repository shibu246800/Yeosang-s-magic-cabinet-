
"""Magic Cabinet player registration and vault settings."""

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import (
    get_connection,
    initialize_database,
)


EMBED_COLOR = discord.Color.from_str("#4E0017")

VAULT_NAMES = {
    "BB": "Boy × Boy",
    "GG": "Girl × Girl",
    "BG": "Boy × Girl",
}

VAULT_ORDER = ["BB", "GG", "BG"]
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"


def initialize_magic_database():
    initialize_database()


def ensure_player(user_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO players (user_id, created_at, vault)
            VALUES (?, ?, NULL)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, datetime.now(timezone.utc).isoformat()),
        )


def get_selected_vaults(user_id: int) -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT vault
            FROM player_vaults
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    selected = {row["vault"] for row in rows}

    return [vault for vault in VAULT_ORDER if vault in selected]


def save_vaults(user_id: int, vaults: list[str]):
    ordered_vaults = [vault for vault in VAULT_ORDER if vault in vaults]

    if not ordered_vaults:
        return

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO players (user_id, created_at, vault)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET vault = excluded.vault
            """,
            (
                user_id,
                datetime.now(timezone.utc).isoformat(),
                ordered_vaults[0],
            ),
        )

        connection.execute(
            "DELETE FROM player_vaults WHERE user_id = ?",
            (user_id,),
        )

        for vault in ordered_vaults:
            connection.execute(
                """
                INSERT INTO player_vaults (user_id, vault)
                VALUES (?, ?)
                """,
                (user_id, vault),
            )


def give_starting_glimmers(user_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO balances (user_id, glimmers)
            VALUES (?, 10000)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )


def format_selected_vaults(vaults: list[str]) -> str:
    return "\n".join(
        f"➤ **{vault}** · {VAULT_NAMES[vault]}"
        for vault in vaults
    )


class VaultSelectionView(discord.ui.View):

    def __init__(
        self,
        user_id: int,
        selected_vaults: list[str] | None = None,
        is_settings: bool = False,
    ):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.is_settings = is_settings
        self.selected_vaults = set(selected_vaults or [])
        self.update_button_states()

    def update_button_states(self):
        custom_ids = {
            "magic_vault_bb": "BB",
            "magic_vault_gg": "GG",
            "magic_vault_bg": "BG",
        }

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                vault = custom_ids.get(item.custom_id)
                if vault:
                    item.style = (
                        discord.ButtonStyle.success
                        if vault in self.selected_vaults
                        else discord.ButtonStyle.secondary
                    )

    async def toggle_vault(
        self,
        interaction: discord.Interaction,
        vault: str,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="These Vaults belong to another player.",
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        if vault in self.selected_vaults:
            self.selected_vaults.remove(vault)
        else:
            self.selected_vaults.add(vault)

        self.update_button_states()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="BB",
        emoji="🗝️",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_bb",
        row=0,
    )
    async def bb_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_vault(interaction, "BB")

    @discord.ui.button(
        label="GG",
        emoji="🗝️",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_gg",
        row=0,
    )
    async def gg_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_vault(interaction, "GG")

    @discord.ui.button(
        label="BG",
        emoji="🗝️",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_bg",
        row=0,
    )
    async def bg_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_vault(interaction, "BG")

    @discord.ui.button(
        label="Save Vaults",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="magic_vault_save",
        row=1,
    )
    async def save_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="These Vaults belong to another player.",
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        if not self.selected_vaults:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "✦ Choose at least one Vault before sealing your choices."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        selected = [
            vault for vault in VAULT_ORDER
            if vault in self.selected_vaults
        ]

        save_vaults(self.user_id, selected)

        if not self.is_settings:
            give_starting_glimmers(self.user_id)

            embed = discord.Embed(
                description=(
                    "╭────────────── ⟡ ──────────────╮\n"
                    "                          **VAULTS SEALED!**\n"
                    "╰────────────── ⟡ ──────────────╯\n\n"
                    "Your choices have been saved.\n"
                    "✦ **Selected Vaults**\n"
                    f"{format_selected_vaults(selected)}\n\n"
                    "The vaults are now yours to explore! "
                    "You have received your starting coins:\n"
                    f"◈ {GLIMMER_EMOTE} **10,000 glimmers**\n\n"
                    "Cards are waiting beyond the Cabinet doors. "
                    "Your next step: ➤ `/drop`\n\n"
                    "You can always change your preferences\n"
                    "using `/vault settings`."
                ),
                color=EMBED_COLOR,
            )
        else:
            embed = discord.Embed(
                description=(
                    "╭────────────── ⟡ ──────────────╮\n"
                    "                    **VAULTS UPDATED!**\n"
                    "╰────────────── ⟡ ──────────────╯\n\n"
                    "Your Vault preferences have been saved.\n"
                    "✦ **Selected Vaults**\n"
                    f"{format_selected_vaults(selected)}\n\n"
                    "Your Cabinet will use these Vaults "
                    "for your future collection journey."
                ),
                color=EMBED_COLOR,
            )

        await interaction.response.edit_message(embed=embed, view=None)


class Magic(commands.GroupCog, name="magic"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_magic_database()

    @app_commands.command(
        name="awaken",
        description="Awaken your place within the Magic Cabinet.",
    )
    async def awaken(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        ensure_player(user_id)
        existing_vaults = get_selected_vaults(user_id)

        if existing_vaults:
            embed = discord.Embed(
                description=(
                    "╭────────────── ✦ ──────────────╮\n"
                    "                     **CABINET AWAKENED**\n"
                    "╰────────────── ✦ ──────────────╯\n\n"
                    "-# The Cabinet already recognizes you.\n\n"
                    "✦ **Selected Vaults**\n"
                    f"{format_selected_vaults(existing_vaults)}\n\n"
                    "You can always change your preferences\n"
                    "using `/vault settings`."
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            description=(
                "╭────────────── ✦ ──────────────╮\n"
                "                     **CABINET AWAKENED**\n"
                "╰────────────── ✦ ──────────────╯\n"
                "-# The key turns. The Cabinet recognizes you.\n"
                "-# Your personal vaults are ready to be chosen.\n\n"
                "╭────────────── ✦ ──────────────╮\n"
                "                 **CHOOSE YOUR VAULTS**\n"
                "╰────────────── ✦ ──────────────╯\n"
                "                Three vaults lie before you.\n"
                "-# ✦ You may choose one, two, or all three.\n"
                "-# Your choices will shape which collections "
                "you encounter within the Cabinet.\n\n"
                " **BB** A vault of boy × boy collections.\n"
                " **GG** A vault of girl × girl collections.\n"
                " **BG** A vault of boy × girl collections.\n\n"
                "✦ Choose your vaults below.\n"
                "✦ Your selection can be changed later by "
                "`/vault settings`"
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
            view=VaultSelectionView(user_id=user_id),
        )


class Vault(commands.GroupCog, name="vault"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_magic_database()

    @app_commands.command(
        name="settings",
        description="Change your Magic Cabinet Vaults.",
    )
    async def settings(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        with get_connection() as connection:
            player = connection.execute(
                "SELECT user_id FROM players WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if player is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "🔒 Your Cabinet is not awake yet.\n\n"
                        "Use `/magic awaken` first."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        current_vaults = get_selected_vaults(user_id)

        embed = discord.Embed(
            description=(
                "╭────────────── ✦ ──────────────╮\n"
                "              **VAULT SETTINGS**\n"
                "╰────────────── ✦ ──────────────╯\n\n"
                "Your current Vaults:\n"
                + (
                    format_selected_vaults(current_vaults)
                    if current_vaults else "➤ None"
                )
                + "\n\nChoose the Vaults you want to use.\n"
                "You may choose one, two, or all three."
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
            view=VaultSelectionView(
                user_id=user_id,
                selected_vaults=current_vaults,
                is_settings=True,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Magic(bot))
    await bot.add_cog(Vault(bot))
