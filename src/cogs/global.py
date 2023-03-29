import re

from discord.ext import commands

from discord import app_commands, Interaction
from discord.app_commands import Choice

from src.types import Bot, TileSkeleton
from src.utils import respond


class GlobalCog(commands.Cog, name="Global"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command()
    async def til(self, interaction: Interaction, *, grid: str, rul: bool = False, ephemeral: bool = False):
        await self.render_tiles(interaction, grid, rule=rul)

    @til.autocomplete("grid")
    async def complete_tile(self, interaction: Interaction, value: str):
        current_tile = re.split(r"(?<!\\)&", re.split(r"(?<!\\),", re.split(r"(?<!\\) ", value)[-1])[-1])[-1]
        tile = TileSkeleton.parse(current_tile, (0, 0), 0)
        if len(tile.variants):
            return []  # [Choice(name=variant.name, value=variant.name) for variant in self.bot.variants if variant.startswith(tile.name)]
        else:
            return [Choice(name=name, value=name) for name in self.bot.db.tiles if name.startswith(tile.name)][:5]

    async def parse_grid(self, grid, rule: bool = False):
        for y, row in enumerate(re.split(r"(?<!\\) ", grid)):
            for x, cell in enumerate(re.split(r"(?<!\\),", row)):
                for z, tile in enumerate(re.split(r"(?<!\\)&", cell)):
                    yield TileSkeleton.parse(tile, (x, y), z)

    async def render_tiles(self, interaction: Interaction, grid: str, rule: bool = False, ephemeral: bool = False):
        # TODO: REMEMBER TO re.split(r"(?<!\\) ") INSTEAD OF .split(" ") AND SUCH
        # TODO: TILE RENDERING AND SPLITTING INTO A GRID
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)
        tiles = [tile async for tile in self.parse_grid(grid, rule=rule)]
        await respond(interaction, str(tiles), ephemeral=ephemeral)


async def setup(bot: Bot):
    await bot.add_cog(GlobalCog(bot))
