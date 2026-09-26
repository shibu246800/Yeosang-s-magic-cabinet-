import sqlite3
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"


class VaultView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    async def choose_vault(
        self,
        interaction: discord.Interaction,
        vault: str,
        vault_name: str,
    ):
        with sqlite3.connect(DATABASE) as connection:
            connection.execute(
                """
                UPDATE players
                SET vault = ?
                WHERE user_id = ?
                """,
                (vault, interaction.user.id),
            )
            connection.commit()

        await interaction.response.edit_message(
            content=(
                "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "      ✦  𝐌𝐀𝐆𝐈𝐂 𝐂𝐀𝐁𝐈𝐍𝐄𝐓  ✦\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"╭─〔 𝐕𝐀𝐔𝐋𝐓 𝐀𝐖𝐀𝐊𝐄𝐍𝐄𝐃 〕─╮\n"
                f"   ✦ {vault}  ·  **{vault_name}**\n"
                "╰──────────────────────╯\n\n"
                "Your place has been recorded.\n"
                "The Cabinet now recognizes you.\n\n"
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
            "Boy × Boy",
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
            "Girl × Girl",
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
            "Boy × Girl",
        )


class Magic(commands.GroupCog, name="magic"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="awaken",
        description="Awaken your place within the Magic Cabinet.",
    )
    async def awaken(self, interaction: discord.Interaction):

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
                        "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
                        "      ✦  𝐂𝐀𝐁𝐈𝐍𝐄𝐓 𝐀𝐖𝐀𝐊𝐄 ✦\n"
                        "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                        "Your Cabinet has already been awakened.\n"
                        f"Your vault: **{existing_player[0]}**",
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

        view = VaultView()

        await interaction.response.send_message(
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
            "✦ *Choose carefully. Your collection begins here.*",
            view=view,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Magic(bot))
