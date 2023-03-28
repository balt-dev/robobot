import asyncio
from pathlib import Path

from discord.ext import commands

from discord import app_commands, Interaction
from discord.app_commands import Choice

from src.types import Bot
from src.utils import *


class OwnerCog(commands.Cog, name="Owner Only"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command()
    @commands.is_owner()
    async def reload(self, i9n: Interaction):
        async def gather_cogs():
            cogs = [
                ".".join(Path(p).stem for p in path.parts)
                for path in Path(".").glob("src/cogs/*.py")
                if not path.stem.startswith("__")
            ]
            await asyncio.gather(*(self.bot.reload_extension(cog, package="bot") for cog in cogs))
        await gather_cogs()
        await respond(i9n, "Reloaded cogs.", ephemeral=True)

    @app_commands.command()
    @commands.is_owner()
    async def sync(self, i9n: Interaction, everywhere: bool = False):
        await self.bot.tree.sync(guild=None if everywhere else i9n.guild)
        await respond(i9n, "Synced.", ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(OwnerCog(bot))
