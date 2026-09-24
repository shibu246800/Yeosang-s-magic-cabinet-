import discord
from discord.ext import commands


class Cabinet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="cabinet")
    async def cabinet(self, ctx):
        await ctx.send("🗝️ The Magic Cabinet is open.")


async def setup(bot):
    await bot.add_cog(Cabinet(bot))
