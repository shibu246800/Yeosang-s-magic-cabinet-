"""Magic Cabinet player registration and vault settings."""

import sqlite3
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"


VAULT_NAMES = {
    "BB": "Boy × Boy",
    "GG": "Girl × Girl",
    "BG": "Boy × Girl",
}


class VaultView(discord.ui.View):
    """Vault selection buttons."""

    def __init__(self):
        super().__init__(timeout=300)

    async def choose_vault(
        self,
        interaction: discord.Interaction,
        vault: str,
    ):
        with sqlite3.connect(DATABASE) as connection:
            connection.execute(
                """
                UPDATE players
                SET vault = ?
                WHERE user_id = ?
                """,
                (
                    vault,
                    interaction.user.id,
                ),
            )
            connection.commit()

        await interaction.response.edit_message(
            content=(
                "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "      ✦  𝐕𝐀𝐔𝐋𝐓 𝐀𝐖𝐀𝐊𝐄𝐍𝐄𝐃  ✦\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"✦ **{vault} · {VAULT_NAMES[vault]}**\n\n"
                "Your Vault selection has been recorded.\n"
                "The Cabinet now recognizes your path.\n\n"
                "✦ Your collection journey begins."
            ),
            view=None,
        )

    @discord.ui.button(
        label="BB",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_bb",
    )
    async def bb_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.choose_vault(
            interaction,
            "BB",
        )

    @discord.ui.button(
        label="GG",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_gg",
    )
    async def gg_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.choose_vault(
            interaction,
            "GG",
        )

    @discord.ui.button(
        label="BG",
        style=discord.ButtonStyle.secondary,
        custom_id="magic_vault_bg",
    )
    async def bg_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.choose_vault(
            interaction,
            "BG",
        )


class VaultSettingsView(discord.ui.View):
    """Vault settings buttons."""

    def __init__(self):
        super().__init__(timeout=300)

    async def change_vault(
        self,
        interaction: discord.Interaction,
        vault: str,
    ):
        with sqlite3.connect(DATABASE) as connection:
            connection.execute(
                """
                UPDATE players
                SET vault = ?
                WHERE user_id = ?
                """,
                (
                    vault,
                    interaction.user.id,
                ),
            )
            connection.commit()

        await interaction.response.edit_message(
            content=(
                "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "       ✦  𝐕𝐀𝐔𝐋𝐓 𝐔𝐏𝐃𝐀𝐓𝐄𝐃  ✦\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"Your Vault is now:\n"
                f"✦ **{vault} · {VAULT_NAMES[vault]}**\n\n"
                "Your previous Vault has been sealed.\n"
                "Your collection progress remains safely recorded."
            ),
            view=None,
        )

    @discord.ui.button(
        label="BB",
        style=discord.ButtonStyle.secondary,
        custom_id="vault_settings_bb",
    )
    async def bb_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.change_vault(
            interaction,
            "BB",
        )

    @discord.ui.button(
        label="GG",
        style=discord.ButtonStyle.secondary,
        custom_id="vault_settings_gg",
    )
    async def gg_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.change_vault(
            interaction,
            "GG",
        )

    @discord.ui.button(
        label="BG",
        style=discord.ButtonStyle.secondary,
        custom_id="vault_settings_bg",
    )
    async def bg_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.change_vault(
            interaction,
            "BG",
        )


class Magic(commands.GroupCog, name="magic"):
    """Magic Cabinet player commands."""

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

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
                SELECT vault
                FROM players
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if existing_player is not None:
                if existing_player[0] is not None:
                    await interaction.response.send_message(
                        (
                            "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
                            "      ✦  𝐂𝐀𝐁𝐈𝐍𝐄𝐓 𝐀𝐖𝐀𝐊𝐄  ✦\n"
                            "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                            "Your Cabinet has already been awakened.\n"
                            f"Your Vault: **{existing_player[0]}**\n\n"
                            "Use `/vault settings` if you wish to "
                            "change your Vault."
                        ),
                        ephemeral=True,
                    )
                    return

            else:
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

        await interaction.response.send_message(
            (
                "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "       ✦  𝐓𝐇𝐄 𝐂𝐀𝐁𝐈𝐍𝐄𝐓  ✦\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"**{interaction.user.mention}**\n"
                "the Cabinet has heard your call.\n\n"
                "Your name has been entered into its records.\n"
                "But every awakened player must choose a path.\n\n"
                "╭─〔 𝐂𝐇𝐎𝐎𝐒𝐄 𝐘𝐎𝐔𝐑 𝐕𝐀𝐔𝐋𝐓 〕─╮\n"
                "│\n"
                "│  **BB**  ·  Boy × Boy\n"
                "│  **GG**  ·  Girl × Girl\n"
                "│  **BG**  ·  Boy × Girl\n"
                "│\n"
                "╰──────────────────────╯\n\n"
                "✦ *Choose carefully. Your collection begins here.*"
            ),
            view=VaultView(),
        )

    @app_commands.command(
        name="settings",
        description="Change your Magic Cabinet Vault.",
    )
    async def settings(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        with sqlite3.connect(DATABASE) as connection:
            player = connection.execute(
                """
                SELECT vault
                FROM players
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if player is None:
            await interaction.response.send_message(
                (
                    "🔒 Your Cabinet is not awake yet.\n\n"
                    "Use `/magic awaken` first."
                ),
                ephemeral=True,
            )
            return

        current_vault = player[0]

        await interaction.response.send_message(
            (
                "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "       ✦  𝐕𝐀𝐔𝐋𝐓 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒  ✦\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"Current Vault: **{current_vault or 'None'}**\n\n"
                "Choose the Vault you want to use.\n"
                "Your previous collection progress will remain saved."
            ),
            view=VaultSettingsView(),
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Magic(bot)
    )
