from discord.ext import commands

from discord import app_commands, Interaction
from discord.app_commands import Choice

from src.types import Bot


class GlobalCog(commands.Cog, name="Global"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command()
    # i9n => interaction same way i18n => internationalization
    async def til(self, i9n: Interaction, *, grid: str, rul: bool = False):
        await self.render_tiles(i9n, grid, rule=rul)

    @til.autocomplete("grid")
    async def grid_autocomplete(self, i9n: Interaction, current: str):
        current_tile = current.split(" ")[-1].split(",")[-1].split("&")[-1]
        print(current_tile)
        return [Choice(name=current_tile, value=current_tile)]

    async def render_tiles(self, i9n: Interaction, grid: str, rule: bool = False):
        assert 0, "Error?"


async def setup(bot: Bot):
    await bot.add_cog(GlobalCog(bot))
