import re
from io import BytesIO

import discord
from discord.ext import commands

from discord import app_commands, Interaction
from discord.app_commands import Choice

from src import constants
from src.types import Bot, TileSkeleton, RenderingContext, Tile
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
            upscale: int = 2,
            rul: bool = False,
            bg: str = None,
            palette: str = "default",
            file: discord.Attachment | None = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)
        ctx = RenderingContext(spacing, upscale, palette, (0, 0, 0, 0), 0, 0, rul)
        assert palette in self.bot.db.palettes, f"idk where `{palette}` is ask ur gps"
        ctx.palette = palette
        if bg is not None:
            if match := re.fullmatch(r"#([\da-fA-F]{8})", bg):
                rgb = int(match.group(1), base=16)
                bg = (rgb >> 24), (rgb & 0xFF0000) >> 16, (rgb & 0xFF00) >> 8, rgb & 0xFF
            elif match := re.fullmatch(r"(\d)/(\d)", bg):
                x, y = int(match.group(1)), int(match.group(2))
                try:
                    bg = self.bot.db.palettes[palette][y, x]
                except IndexError:
                    raise AssertionError(f"thers not a colr at `{x}, {y}`!!")
            else:
                raise AssertionError(f"{bg} isnt a colr??? _(try `#RRGGBBAA` or `x/y`)_")
            ctx.bg = bg
        if file is not None:
            grid = str(await file.read(), "utf-8")
        raw_tiles = list(self.parse_grid(grid, rul))
        # TODO: POST-PARSE SHIT
        tiles = await Tile.build_tiles(raw_tiles, ctx, self.bot)
        buf = BytesIO()
        assert len(tiles), "wher tils"
        tiles = await self.bot.renderer.process(tiles, ctx)
        await self.bot.renderer.render(tiles, buf, ctx)
        return await respond(interaction, content=None, file=discord.File(buf, filename="render.png"))

    @til.autocomplete("grid")
    async def complete_tile(self, interaction: Interaction, value: str):
        current_tile = re.split(r"(?<!\\)\+", re.split(r"(?<!\\),", re.split(r"(?<!\\) ", value)[-1])[-1])[-1]
        tile = TileSkeleton.parse(current_tile, (0, 0), 0, self.bot.variants)
        if len(tile.variants): return []
        return [Choice(name=name, value=name) for name in self.bot.db.tiles if name.startswith(tile.name)][:25]

    def parse_grid(self, grid, rule: bool = False):
        for y, row in enumerate(re.split(r"(?<!\\) ", grid)):
            for x, cell in enumerate(re.split(r"(?<!\\),", row)):
                for z, tile in enumerate(re.split(r"(?<!\\)\+", cell)):
                    yield TileSkeleton.parse(tile, (x, y), self.bot.variants, layer=z)


async def setup(bot: Bot):
    await bot.add_cog(GlobalCog(bot))
