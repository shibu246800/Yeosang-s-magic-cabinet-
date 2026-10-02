"""Magic Cabinet player registration and vault settings."""

import sqlite3
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"

EMBED_COLOR = discord.Color.from_str("#4E0017")

VAULT_NAMES = {
    "BB": "Boy × Boy",
    "GG": "Girl × Girl",
    "BG": "Boy × Girl",
}


def initialize_magic_database():
    """Create the player, vault, and balance tables."""

    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                vault TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS player_vaults (
                user_id INTEGER NOT NULL,
                vault TEXT NOT NULL,
                PRIMARY KEY (user_id, vault)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER PRIMARY KEY,
                glimmers INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        connection.commit()


def get_selected_vaults(user_id: int) -> list[str]:
    """Return all Vaults selected by a player."""

    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT vault
            FROM player_vaults
            WHERE user_id = ?
            ORDER BY
                CASE vault
                    WHEN 'BB' THEN 1
                    WHEN 'GG' THEN 2
                    WHEN 'BG' THEN 3
                END
            """,
            (user_id,),
        ).fetchall()

    return [row[0] for row in rows]


def save_vaults(
    user_id: int,
    vaults: list[str],
):
    """Replace the player's selected Vaults."""

    with sqlite3.connect(DATABASE) as connection:

        connection.execute(
            """
            DELETE FROM player_vaults
            WHERE user_id = ?
            """,
            (user_id,),
        )

        connection.executemany(
            """
            INSERT INTO player_vaults (
                user_id,
                vault
            )
            VALUES (?, ?)
            """,
            [
                (
                    user_id,
                    vault,
                )
                for vault in vaults
            ],
        )

        # Keep the old players.vault field synchronized with
        # the first selected Vault for compatibility with
        # existing parts of the Cabinet.
        connection.execute(
            """
            UPDATE players
            SET vault = ?
            WHERE user_id = ?
            """,
            (
                vaults[0],
                user_id,
            ),
        )

        connection.commit()


def give_starting_glimmers(user_id: int):
    """Give the player their starting 10,000 glimmers."""

    with sqlite3.connect(DATABASE) as connection:
        existing_balance = connection.execute(
            """
            SELECT glimmers
            FROM balances
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if existing_balance is None:
            connection.execute(
                """
                INSERT INTO balances (
                    user_id,
                    glimmers
                )
                VALUES (?, ?)
                """,
                (
                    user_id,
                    10_000,
                ),
            )

        connection.commit()


def format_vaults(vaults: list[str]) -> str:
    """Format selected Vaults for display."""

    return "\n".join(
        f"➤ **{vault}** · {VAULT_NAMES[vault]}"
        for vault in vaults
    )


class VaultSelectionView(discord.ui.View):
    """Multi-select Vault selection view."""

    def __init__(
        self,
        user_id: int,
        selected_vaults: list[str] | None = None,
    ):
        super().__init__(timeout=300)

        self.user_id = user_id
        self.selected_vaults = set(
            selected_vaults or []
        )

        self.update_button_states()

    def update_button_states(self):
        """Update button appearance from current selections."""

        for item in self.children:
            if not isinstance(
                item,
                discord.ui.Button,
            ):
                continue

            if item.custom_id == "magic_vault_bb":
                vault = "BB"
            elif item.custom_id == "magic_vault_gg":
                vault = "GG"
            elif item.custom_id == "magic_vault_bg":
                vault = "BG"
            else:
                continue

            if vault in self.selected_vaults:
                item.style = discord.ButtonStyle.success
            else:
                item.style = discord.ButtonStyle.secondary

    async def toggle_vault(
        self,
        interaction: discord.Interaction,
        vault: str,
    ):
        """Toggle one Vault selection."""

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "These Vaults belong to another player."
                    ),
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

        await interaction.response.edit_message(
            view=self
        )

    @discord.ui.button(
        label="🗝️ BB",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_bb",
        row=0,
    )
    async def bb_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_vault(
            interaction,
            "BB",
        )

    @discord.ui.button(
        label="🗝️ GG",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_gg",
        row=0,
    )
    async def gg_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_vault(
            interaction,
            "GG",
        )

    @discord.ui.button(
        label="🗝️ BG",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_bg",
        row=0,
    )
    async def bg_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_vault(
            interaction,
            "BG",
        )

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
                    description=(
                        "These Vaults belong to another player."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        if not self.selected_vaults:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "✦ Choose at least one Vault before "
                        "sealing your choices."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        vault_order = ["BB", "GG", "BG"]

        selected = [
            vault
            for vault in vault_order
            if vault in self.selected_vaults
        ]

        save_vaults(
            self.user_id,
            selected,
        )

        give_starting_glimmers(
            self.user_id
        )

        selected_text = "\n".join(
            f"➤ **{vault}** · {VAULT_NAMES[vault]}"
            for vault in selected
        )

        embed = discord.Embed(
            description=(
                "╭────────────── ⟡ ──────────────╮\n"
                "                     **VAULTS SEALED!**\n"
                "╰────────────── ⟡ ──────────────╯\n\n"
                "Your choices have been saved.\n"
                "✦ **Selected Vaults**\n"
                f"{selected_text}\n\n"
                "The vaults are now yours to explore! "
                "You have received your starting coins:\n"
                "◈ <:glimmer:1554842064464773172> "
                "**10,000 glimmers**\n\n"
                "Cards are waiting beyond the Cabinet doors. "
                "Your next step: ➤ `/drop`\n\n"
                "You can always change your preferences\n"
                "using `/vault settings`."
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None,
        )


class VaultSettingsView(VaultSelectionView):
    """Multi-select Vault settings view."""

    def __init__(
        self,
        user_id: int,
        selected_vaults: list[str],
    ):
        super().__init__(
            user_id,
            selected_vaults,
        )

        # Use a different custom ID for the settings save button
        # so Discord treats this as a separate interaction view.
        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                if item.custom_id == "magic_vault_save":
                    item.custom_id = "vault_settings_save"

    async def save_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        pass


class Magic(commands.GroupCog, name="magic"):
    """Magic Cabinet player commands."""

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot
        initialize_magic_database()

    @app_commands.command(
        name="awaken",
        description="Awaken your place within the Magic Cabinet.",
    )
    async def awaken(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        with sqlite3.connect(DATABASE) as connection:
            existing_player = connection.execute(
                """
                SELECT user_id
                FROM players
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if existing_player is None:
                connection.execute(
                    """
                    INSERT INTO players (
                        user_id,
                        created_at,
                        vault
                    )
                    VALUES (?, ?, NULL)
                    """,
                    (
                        user_id,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                connection.commit()

        selected_vaults = get_selected_vaults(
            user_id
        )

        if selected_vaults:
            embed = discord.Embed(
                description=(
                    "╭────────────── ✦ ──────────────╮\n"
                    "                     **CABINET AWAKENED**\n"
                    "╰────────────── ✦ ──────────────╯\n\n"
                    "-# The Cabinet already recognizes you.\n"
                    f"-# Your selected Vaults: "
                    f"{', '.join(selected_vaults)}\n\n"
                    "You can change your preferences using "
                    "`/vault settings`."
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
                "**BB** A vault of boy × boy collections.\n"
                "**GG** A vault of girl × girl collections.\n"
                "**BG** A vault of boy × girl collections.\n\n"
                "✦ Choose your vaults below.\n"
                "✦ Your selection can be changed later by "
                "`/vault settings`\n"
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
            view=VaultSelectionView(user_id),
        )

    @app_commands.command(
        name="settings",
        description="Change your Magic Cabinet Vaults.",
    )
    async def settings(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        with sqlite3.connect(DATABASE) as connection:
            player = connection.execute(
                """
                SELECT user_id
                FROM players
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if player is None:
            embed = discord.Embed(
                description=(
                    "🔒 Your Cabinet is not awake yet.\n\n"
                    "Use `/magic awaken` first."
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        current_vaults = get_selected_vaults(
            user_id
        )

        embed = discord.Embed(
            description=(
                "╭────────────── ✦ ──────────────╮\n"
                "              **VAULT SETTINGS**\n"
                "╰────────────── ✦ ──────────────╯\n\n"
                "Your current Vaults:\n"
                + (
                    format_vaults(current_vaults)
                    if current_vaults
                    else "➤ None"
                )
                + "\n\n"
                "Choose the Vaults you want to use.\n"
                "You may choose one, two, or all three."
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
            view=VaultSelectionView(
                user_id,
                current_vaults,
            ),
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Magic(bot)
            )
