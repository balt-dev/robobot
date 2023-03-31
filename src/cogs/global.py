import re
from io import BytesIO

import discord
from discord.ext import commands

from discord import app_commands, Interaction
from discord.app_commands import Choice

from src import constants
from src.types import Bot, TileSkeleton, RenderingContext, Tile#, Test
from src.utils import respond


class GlobalCog(commands.Cog, name="Global"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command()
    async def til(
            self,
            interaction: Interaction,
            grid: str, *,
            # Yes, it has to be this way. :/
            ephemeral: bool = False,
            spacing: int = constants.TILE_SIZE,
            upscale: int = 2
    ):
        # TODO: REMEMBER TO re.split(r"(?<!\\) ") INSTEAD OF .split(" ") AND SUCH
        # TODO: TILE RENDERING AND SPLITTING INTO A GRID
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)
        ctx = RenderingContext(spacing, upscale)
        tiles = list(self.parse_grid(grid))
        # TODO: POST-PARSE SHIT
        tiles = [Tile.build(skel, self.bot.db.tiles[skel.name]) for skel in tiles if
                 skel is not None and skel.name in self.bot.db.tiles]
        buf = BytesIO()
        assert len(tiles), "wher til"
        tiles = self.bot.renderer.process(tiles, ctx)
        await self.bot.renderer.render(tiles, buf, ctx)
        return await respond(interaction, content=None, file=discord.File(buf, filename="render.png"))

    @til.autocomplete("grid")
    async def complete_tile(self, interaction: Interaction, value: str):
        current_tile = re.split(r"(?<!\\)&", re.split(r"(?<!\\),", re.split(r"(?<!\\) ", value)[-1])[-1])[-1]
        tile = TileSkeleton.parse(current_tile, (0, 0), 0)
        if len(tile.variants): return []
        return [Choice(name=name, value=name) for name in self.bot.db.tiles if name.startswith(tile.name)][:5]

    def parse_grid(self, grid):
        for y, row in enumerate(re.split(r"(?<!\\) ", grid)):
            for x, cell in enumerate(re.split(r"(?<!\\),", row)):
                for z, tile in enumerate(re.split(r"(?<!\\)&", cell)):
                    yield TileSkeleton.parse(tile, (x, y), z, self.bot.variants)


async def setup(bot: Bot):
    await bot.add_cog(GlobalCog(bot))